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


def group_processes(pgid, *, include_zombies=False):
    result = []
    for entry in Path('/proc').iterdir():
        if not entry.name.isdigit():
            continue
        try:
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
            if int(fields[2]) == pgid and (include_zombies or fields[0] != 'Z'):
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


class HelperFailure(RuntimeError):
    def __init__(self, failure):
        self.failure = failure
        self.kind = 'helper_failure'
        self.stop_required = True
        super().__init__(f"{failure['error_class']}: {failure['message']}")


class HelperCleanupFailure(HelperFailure):
    def __init__(self, phase, lifecycle):
        super().__init__(dict(error_class='HelperCleanupUncertain',
            message='helper cleanup not confirmed', phase=phase,
            ownership=lifecycle.ownership(), secondary=list(lifecycle.errors)))
        self.kind = 'cleanup'
        self.lifecycle = lifecycle


class _Helper:
    """Spawn only importable operations; retain ownership until confirmed reaped."""
    def __init__(self, operation):
        import multiprocessing
        from .s1_cpu_helper import entry
        self.process = self.connection = None
        self.pid = None
        self.closed = False
        self.signaled = False
        self.phase = operation.get('operation', 'startup')
        context = multiprocessing.get_context('spawn')
        self.connection, child = context.Pipe(duplex=False)
        self.process = context.Process(target=entry, args=(child, operation))
        try:
            self.process.start()
            self.pid = self.process.pid
        except BaseException as exc:
            self.pid = self.process.pid
            raise self.failure(exc, 'startup') from exc
        finally:
            child.close()

    def failure(self, exc, phase=None):
        return HelperFailure(dict(error_class=type(exc).__name__, message=str(exc),
            phase=phase or self.phase, ownership=dict(pid=self.pid)))

    def poll(self):
        try:
            if not self.connection.poll():
                if not self.process.is_alive():
                    raise EOFError('helper died without evidence')
                return False, None
            ok, value = self.connection.recv()
        except (EOFError, OSError, ValueError) as exc:
            raise self.failure(exc, 'transport') from exc
        if not ok:
            value['ownership'] = dict(pid=self.pid)
            raise HelperFailure(value)
        return True, value

    def close(self):
        if self.closed:
            return True
        if self.process is None or self.process.pid is None:
            if self.connection is not None:
                self.connection.close()
            self.closed = True
            return True
        # The unreaped leader pins the process-group identity. Do not reap it
        # before checking descendants; zombies cannot execute and are not survivors.
        members = group_processes(self.pid)
        sig = signal.SIGKILL if self.signaled else signal.SIGTERM
        if members:
            try:
                os.killpg(self.pid, sig)
            except ProcessLookupError:
                pass
        elif self.process.exitcode is None:
            try:
                os.kill(self.pid, sig)
            except ProcessLookupError:
                pass
        self.signaled = True
        survivors = group_processes(self.pid)
        if survivors:
            return False
        self.process.join(timeout=0)
        if self.process.is_alive():
            return False
        self.connection.close()
        self.process.close()
        self.closed = True
        return True


class HelperLifecycle:
    """Shared monitor/supervisor ownership, including failed constructors."""
    def __init__(self):
        self.helpers = []
        self.errors = []

    def start(self, operation):
        helper = _Helper.__new__(_Helper)
        self.helpers.append(helper)
        helper.__init__(operation)
        return helper

    def ownership(self):
        return [dict(pid=getattr(h, 'pid', None), phase=getattr(h, 'phase', 'startup'))
                for h in self.helpers]

    def reap(self, deadline):
        while self.helpers:
            for helper in list(self.helpers):
                try:
                    confirmed = helper.close() is True
                except BaseException as exc:
                    observation = dict(error_class=type(exc).__name__, message=str(exc),
                                       phase='helper_cleanup', pid=getattr(helper, 'pid', None))
                    if observation not in self.errors:
                        self.errors.append(observation)
                    confirmed = False
                if confirmed:
                    self.helpers.remove(helper)
            if not self.helpers or time.monotonic() >= deadline:
                break
            time.sleep(min(.005, max(0., deadline-time.monotonic())))
        return not self.helpers

    def settle(self, helper, deadline, phase):
        # Only one retired helper is settled here; active helpers remain owned.
        retired = HelperLifecycle()
        retired.helpers = [helper]
        confirmed = retired.reap(deadline)
        self.errors.extend(e for e in retired.errors if e not in self.errors)
        if confirmed:
            self.helpers.remove(helper)
        else:
            raise HelperCleanupFailure(phase, self)


def validate_sample(reading):
    import math
    if not isinstance(reading, dict):
        raise ValueError('invalid S1 resource sample mapping')
    for key in ('device_bytes', 'artifact_bytes', 'download_bytes'):
        value = reading.get(key)
        if type(value) not in (int, float) or not math.isfinite(value) or value < 0:
            raise ValueError('invalid S1 resource sample: ' + key)
    pids = reading.get('gpu_pids')
    if (not isinstance(pids, list) or any(type(pid) is not int or pid <= 0 for pid in pids)
            or len(pids) != len(set(pids))):
        raise ValueError('invalid S1 resource sample: gpu_pids')
    return reading


def monitored_call(function, deadline, sampler, config, peak, *, worker=None,
                   phase='acceptance', ledger=None, job_id=None, lifecycle=None):
    """Monitor never hashes/parses/writes or invokes the sampler itself.

    Exactly one sample is in flight. Both CPU helpers are independently
    terminable even when native code or I/O blocks. No signal callback reentry.
    """
    lifecycle = lifecycle if lifecycle is not None else HelperLifecycle()
    primary = None
    task = sample = None
    pending = False
    result = None
    try:
        while True:
            now = time.monotonic()
            if now >= deadline:
                raise TimeoutError('S1 ' + phase + ' deadline reached')
            if sample is None:
                sample = lifecycle.start(sampler)
                sample_deadline = min(deadline, now + 1.)
            ready, reading = sample.poll()
            if ready:
                lifecycle.settle(sample, deadline, phase); sample = None
                validate_sample(reading)
                for field, key in [('device_bytes','gpu_peak_device_gib_limit'),
                                   ('artifact_bytes','new_artifact_disk_gib_limit'),
                                   ('download_bytes','new_download_gib_limit')]:
                    peak[field] = max(peak.get(field, 0), reading.get(field, 0))
                    if peak[field] > config[key]*2**30:
                        raise RuntimeError('S1 resource ceiling exceeded: ' + field)
                owned = set(group_processes(worker.pid, include_zombies=True)) if worker else set()
                foreign = sorted(set(reading.get('gpu_pids', [])) - owned)
                if foreign:
                    raise HelperFailure(dict(error_class='GPUOwnershipError', message='exclusive GPU access lost during ' + phase + ': ' + str(foreign), phase=phase, ownership=dict(owned=sorted(owned), foreign=foreign)))
                if pending:
                    return result
                if task is None:
                    task = lifecycle.start(function)
            elif now >= sample_deadline:
                raise TimeoutError('S1 resource sample timeout during ' + phase)
            if task is not None and not pending:
                pending, result = task.poll()
                if pending:
                    lifecycle.settle(task, deadline, phase); task = None
                    # Require a sample taken after work, not just before it.
                    if sample:
                        lifecycle.settle(sample, deadline, phase); sample = None
            time.sleep(min(.02, max(0., deadline - time.monotonic())))
    except BaseException as exc:
        primary = exc
        raise
    finally:
        if not lifecycle.reap(deadline):
            cleanup = HelperCleanupFailure(phase, lifecycle)
            if primary is None:
                raise cleanup
            primary.cleanup_uncertain = True
            primary.lifecycle = lifecycle
            primary.add_note(str(cleanup))
        if primary is not None:
            primary.helper_cleanup_errors = list(lifecycle.errors)


def supervise(ledger, job_id, command, output, *, evidence, sample_resources=None,
              validate_result=None, poll_seconds=.1, seconds_limit=None,
              checkpoint=False, resume_checkpoint=False, terminal_publisher=None, terminal_docs=None):
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
    is_s1 = job_id == 'S1-calibration-recovery-001'
    lifecycle = HelperLifecycle()
    peak = dict(device_bytes=0, artifact_bytes=0, download_bytes=0)
    initial = (monitored_call(sampler, time.monotonic()+2., sampler, ledger.config, peak,
                              lifecycle=lifecycle, phase='initial_sample') if is_s1 else sampler())
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
    result_record = None
    acceptance = None
    old_handlers = {}
    def interrupted(signum, _):
        raise InterruptedError(f'supervisor received signal {signum}')
    try:
        for sig in (signal.SIGTERM, signal.SIGINT):
            old_handlers[sig] = signal.signal(sig, interrupted)
        env = dict(os.environ, VIPE_RESERVATION_START=str(start), OMP_NUM_THREADS='4' if is_s1 else '8', OPENBLAS_NUM_THREADS='4' if is_s1 else '8',
                   HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        temporary = output.with_name(output.name + '-temporary')
        temporary.mkdir(exist_ok=False)
        env['TMPDIR'] = str(temporary)
        # Native Triton kernels compile even when model compilation is off.
        # Retain their caches inside the monitored run, separately per attempt.
        caches = {name: str((temporary / folder).absolute()) for name, folder in (
            ('TRITON_HOME', 'triton-home'), ('TRITON_CACHE_DIR', 'triton-cache'),
            ('TRITON_DUMP_DIR', 'triton-dump'), ('TRITON_OVERRIDE_DIR', 'triton-override'),
            ('TORCHINDUCTOR_CACHE_DIR', 'torchinductor-cache'), ('CUDA_CACHE_PATH', 'cuda-cache'))}
        env.update(caches)
        ledger.note('temporary_directory', job_id=job_id, path=str(temporary), native_caches=caches)
        with output.with_suffix('.log').open('x') as log:
            if is_s1:
                monitored_call(dict(operation='prelaunch', args=dict(local=str(ledger.path.parent),
                    config=ledger.config, reservation=reservation, command=command)),
                    run_deadline, sampler, ledger.config, peak, phase='prelaunch', lifecycle=lifecycle)
                if time.monotonic() >= run_deadline:
                    raise TimeoutError('S1 prelaunch deadline exhausted')
            process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, env=env)
            ledger.note('started', job_id=job_id, pid=process.pid, pgid=process.pid)
            while True:
                reading = (monitored_call(sampler, min(run_deadline, time.monotonic()+1.), sampler,
                    ledger.config, peak, worker=process, phase='worker_sample', lifecycle=lifecycle) if is_s1 else sampler())
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
                # The unreaped worker can exit after nvidia-smi samples its PID.
                # Zombies retain their real PGID and cannot execute or reuse
                # that PID; count them for ownership, never for live cleanup.
                owned = set(group_processes(process.pid, include_zombies=True))
                foreign = sorted(set(reading.get('gpu_pids', [])) - owned)
                if foreign:
                    ledger.note('gpu_ownership_failure', job_id=job_id,
                        phase='worker', sampled_gpu_pids=reading.get('gpu_pids', []), owned_pids=sorted(owned),
                        foreign_pids=foreign, worker_pid=process.pid)
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
                    def accept():
                        accepted = validate_result(output)
                        return file_record(output / 'result.json'), accepted
                    if is_s1:
                        result_record, acceptance = monitored_call(dict(operation='accept', args=dict(
                            local=str(ledger.path.parent), config=ledger.config, reservation=reservation,
                            command=command, output=str(output))), run_deadline, sampler,
                            ledger.config, peak, worker=process, phase='acceptance', lifecycle=lifecycle)
                    else:
                        result_record, acceptance = accept()
                    break
                time.sleep(min(poll_seconds, max(0., run_deadline - time.monotonic())))
    except BaseException as exc:
        if isinstance(exc, (KeyboardInterrupt, InterruptedError)):
            failure_kind, stop_required = 'interrupted', True
        elif isinstance(exc, TimeoutError):
            failure_kind, stop_required = 'job_deadline', True
        elif 'exclusive GPU access lost' in str(exc):
            failure_kind, stop_required = 'gpu_exclusivity', True
        elif isinstance(exc, (PermissionError, ConnectionError)):
            failure_kind, stop_required = 'permission_or_access', True
        elif isinstance(exc, HelperFailure):
            failure_kind, stop_required = exc.kind, True
        error = f'{type(exc).__name__}: {exc}'
    finally:
        evidence_summary = None
        if is_s1 and time.monotonic() < run_deadline:
            from .s1_recovery import prepare_terminal_evidence
            try:
                evidence_summary = monitored_call(dict(operation='reconcile', args=dict(
                    local=str(ledger.path.parent), reservation=reservation,
                    outcome=dict(error=error, result=result_record, acceptance=acceptance), deadline=run_deadline)),
                    run_deadline, sampler, ledger.config, peak, worker=process, phase='reconciliation', lifecycle=lifecycle)
            except Exception as exc:
                error = (error or '') + f'; reconciliation failed: {type(exc).__name__}: {exc}'
                failure_kind, stop_required = 'evidence_reconciliation', True
        # A second Ctrl-C must not interrupt process cleanup.
        for sig in old_handlers:
            signal.signal(sig, signal.SIG_IGN)
        cleanup_uncertain = not lifecycle.reap(deadline)
        if cleanup_uncertain:
            failure_kind, stop_required = 'cleanup', True
            error = (error or '') + '; helper cleanup not confirmed'
        try:
            stopped = stop_group(process, deadline)
        except BaseException as exc:
            failure_kind, stop_required = 'cleanup', True
            cleanup_uncertain = True
            try:
                stopped = group_processes(process.pid) if process else []
            except Exception:
                stopped = []
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
                        cleanup_confirmed=not stopped and not cleanup_uncertain, cleanup_uncertain=cleanup_uncertain, failure_kind=failure_kind if error else None,
                        stop_required=stop_required if error else False)
        if is_s1:
            evidence.update(reservation={k:reservation[k] for k in ('sequence','event_sha256')},
                            acceptance=acceptance, evidence_summary=evidence_summary)
            try:
                if terminal_publisher is None:
                    raise ValueError('S1 charged terminal publisher required')
                evidence['terminal_receipt'] = monitored_call(
                    dict(operation='publish', args=dict(local=str(ledger.path.parent), docs=str(terminal_docs),
                        config=ledger.config, reservation=reservation, outcome=evidence)),
                    deadline - min(.1, cleanup_reserve / 10), sampler, ledger.config, peak,
                    worker=process, phase='publication', lifecycle=lifecycle)
            except BaseException as exc:
                error = (error or '') + f'; evidence publication failed: {exc}'
                failure_kind, stop_required = 'evidence_publication', True
                evidence.update(error=error, stop_required=True, failure_kind=failure_kind)
            elapsed = time.monotonic() - start
            if elapsed >= reservation['seconds']:
                error = (error or '') + '; total deadline exceeded'
                failure_kind, stop_required = 'cleanup_deadline', True
                evidence.update(error=error, stop_required=True, failure_kind=failure_kind)
        # Publication can introduce new unsettled helpers after worker cleanup.
        if not lifecycle.reap(deadline):
            error = (error or '') + '; helper cleanup not confirmed after publication'
            failure_kind, stop_required = 'cleanup', True
            evidence.update(error=error, failure_kind=failure_kind, stop_required=True,
                            cleanup_confirmed=False, cleanup_uncertain=True)
        evidence.update(helper_ownership=lifecycle.ownership(), helper_cleanup_errors=lifecycle.errors)
        if checkpoint and not error:
            ledger.checkpoint(job_id, elapsed, **evidence)
        else:
            ledger.finish(job_id, 'failed' if error else 'complete', elapsed, **evidence)
    if error:
        raise SupervisionFailure(error, kind=failure_kind, stop_required=stop_required)
    return read_json(result_record['path'])
