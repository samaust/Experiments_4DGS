"""Serial process-group supervisor with deadlines that include cleanup."""
import os
from pathlib import Path
import signal
import subprocess
import time

from .files import file_record, read_json, safe_path


class SupervisionFailure(RuntimeError):
    def __init__(self, message, *, kind, stop_required):
        super().__init__(message)
        self.kind = kind
        self.stop_required = stop_required


def group_processes(pgid):
    result = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid and fields[0] != 'Z':
                result.append(int(entry.name))
        except (FileNotFoundError, ProcessLookupError):
            continue
    return sorted(result)


def stop_group(process, deadline):
    if process is None:
        return []
    pgid = process.pid
    try:
        os.killpg(pgid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    grace = min(time.monotonic() + 2., deadline - .1)
    while group_processes(pgid) and time.monotonic() < grace:
        time.sleep(.02)
    try:
        os.killpg(pgid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    while group_processes(pgid) and time.monotonic() < deadline:
        time.sleep(.01)
    process.wait(timeout=max(.01, deadline - time.monotonic()))
    return group_processes(pgid)


def gpu_reading():
    """Caller must apply repository permission retry/stop rules to probe failure."""
    def query(*args):
        return subprocess.check_output(['nvidia-smi', *args], text=True, timeout=5)
    devices = query('--query-gpu=uuid,name,memory.used', '--format=csv,noheader,nounits').strip().splitlines()
    if len(devices) != 1:
        raise ValueError('exactly one RTX 4090 device is required')
    uuid, name, memory = [v.strip() for v in devices[0].split(',')]
    if 'RTX 4090' not in name:
        raise ValueError('runtime is not the prescribed RTX 4090')
    processes = query('--query-compute-apps=gpu_uuid,pid', '--format=csv,noheader,nounits').strip().splitlines()
    pids = [int(row.split(',')[1]) for row in processes if row.strip() and row.split(',')[0].strip() == uuid]
    return dict(device_bytes=int(float(memory) * 2**20), gpu_pids=pids, device_uuid=uuid)


def directory_bytes(root):
    from .budgets import directory_bytes as counted_bytes
    return counted_bytes(root)


def supervise(ledger, job_id, command, output, *, evidence, sample_resources=None,
              validate_result=None, poll_seconds=.1, seconds_limit=None,
              checkpoint=False, resume_checkpoint=False):
    """The worker owns a fresh output directory; logs are siblings, not results.

    Resource injection is for disposable CPU tests. Real GPU dispatch always
    supplies gpu_reading plus the experiment storage/download monitor.
    """
    output = safe_path(output)
    if output.exists() or output.with_suffix('.log').exists():
        raise ValueError('refusing to overwrite incomplete or previous output')
    output.parent.mkdir(parents=True, exist_ok=True)
    spec = ledger.jobs[job_id]
    if spec['resource'] == 'gpu' and sample_resources is None:
        raise ValueError('GPU dispatch requires exclusive-device and resource readings')
    sampler = sample_resources or (lambda: {})
    initial = sampler()
    if initial.get('gpu_pids'):
        raise ValueError('GPU is already in use; no attempt dispatched')
    for field, key in [('device_bytes', 'gpu_peak_device_gib_limit'),
                       ('artifact_bytes', 'new_artifact_disk_gib_limit'),
                       ('download_bytes', 'new_download_gib_limit')]:
        if initial.get(field, 0) >= ledger.config[key] * 2**30:
            raise ValueError(f'{field} allowance already exhausted; no attempt dispatched')
    if (checkpoint or resume_checkpoint) and job_id != 'aggregate':
        raise ValueError('only aggregation may pause or resume stage checkpoints')
    reserve = ledger.resume_checkpoint if resume_checkpoint else ledger.reserve
    reservation = reserve(job_id, command, evidence, seconds_limit=seconds_limit)
    start = reservation['monotonic_start']
    deadline = start + reservation['seconds']
    cleanup_reserve = min(30., reservation['seconds'] / 4)
    run_deadline = deadline - cleanup_reserve
    process, stopped, error = None, [], None
    failure_kind, stop_required = 'supervisor', True
    peak = dict(device_bytes=0, artifact_bytes=0, download_bytes=0)
    result_record = None
    old_handlers = {}
    def interrupted(signum, _):
        raise InterruptedError(f'supervisor received signal {signum}')
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            old_handlers[sig] = signal.signal(sig, interrupted)
        env = dict(os.environ, OMP_NUM_THREADS='8', OPENBLAS_NUM_THREADS='8',
                   HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        temporary = output.with_name(output.name + '-temporary')
        temporary.mkdir(exist_ok=False)
        env['TMPDIR'] = str(temporary)
        ledger.note('temporary_directory', job_id=job_id, path=str(temporary))
        with output.with_suffix('.log').open('x') as log:
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, env=env)
            ledger.note('started', job_id=job_id, pid=process.pid, pgid=process.pid)
            while True:
                reading = sampler()
                for key in peak:
                    peak[key] = max(peak[key], reading.get(key, 0))
                if peak['device_bytes'] > ledger.config['gpu_peak_device_gib_limit'] * 2**30:
                    failure_kind = 'device_memory'
                    raise RuntimeError('total device memory ceiling exceeded')
                if peak['artifact_bytes'] > ledger.config['new_artifact_disk_gib_limit'] * 2**30:
                    failure_kind = 'artifact_budget'
                    raise RuntimeError('new artifact storage ceiling exceeded')
                if peak['download_bytes'] > ledger.config['new_download_gib_limit'] * 2**30:
                    failure_kind = 'download_budget'
                    raise RuntimeError('new download ceiling exceeded')
                owned = set(group_processes(process.pid))
                if any(pid not in owned for pid in reading.get('gpu_pids', [])):
                    failure_kind = 'gpu_exclusivity'
                    raise RuntimeError('exclusive GPU access lost')
                if time.monotonic() >= run_deadline:
                    failure_kind, stop_required = 'job_deadline', False
                    raise TimeoutError('worker deadline reached; remaining allocation reserved for cleanup')
                if process.poll() is not None:
                    if process.returncode:
                        failure_kind, stop_required = 'worker_failure', False
                        raise RuntimeError(f'worker exited {process.returncode}')
                    # Child survival after the parent exits invalidates the result.
                    if group_processes(process.pid):
                        failure_kind = 'child_survival'
                        raise RuntimeError('worker left a live child process')
                    if validate_result is None:
                        raise ValueError('result contract validator is required')
                    failure_kind, stop_required = 'result_contract', False
                    validate_result(output)
                    result_record = file_record(output / 'result.json')
                    break
                time.sleep(min(poll_seconds, max(0., run_deadline - time.monotonic())))
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, InterruptedError)):
            failure_kind, stop_required = 'interrupted', True
        elif isinstance(exc, (PermissionError, ConnectionError)):
            failure_kind, stop_required = 'permission_or_access', True
        error = f'{type(exc).__name__}: {exc}'
    finally:
        # A second Ctrl-C must not interrupt process cleanup.
        for sig in old_handlers:
            signal.signal(sig, signal.SIG_IGN)
        try:
            stopped = stop_group(process, deadline)
        except BaseException as exc:
            failure_kind, stop_required = 'cleanup', True
            stopped = group_processes(process.pid) if process else []
            error = (error or '') + f'; cleanup failed: {type(exc).__name__}: {exc}'
        for sig, handler in old_handlers.items():
            signal.signal(sig, handler)
        if stopped:
            failure_kind, stop_required = 'cleanup', True
            error = (error or '') + f'; processes not confirmed stopped: {stopped}'
        elapsed = time.monotonic() - start
        if elapsed > reservation['seconds']:
            failure_kind, stop_required = 'cleanup_deadline', True
            error = (error or '') + '; total deadline exceeded'
        evidence = dict(error=error, result=result_record, peak=peak, surviving_pids=stopped,
                        cleanup_confirmed=not stopped, failure_kind=failure_kind if error else None,
                        stop_required=stop_required if error else False)
        if checkpoint and not error:
            ledger.checkpoint(job_id, elapsed, **evidence)
        else:
            ledger.finish(job_id, 'failed' if error else 'complete', elapsed, **evidence)
    if error:
        raise SupervisionFailure(error, kind=failure_kind, stop_required=stop_required)
    return read_json(result_record['path'])
