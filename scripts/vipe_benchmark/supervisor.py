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


from .s1_helper_session import Session


class HelperLifecycle:
    """A supervise call owns one persistent session; standalone calls retire it."""
    def __init__(self, *, retain=False, session_factory=None):
        self.helpers = []
        self.errors = []
        self.retain = retain
        self.session_factory = session_factory
        self.poisoned = False

    def acquire(self):
        if self.poisoned:
            raise HelperFailure(dict(error_class='SessionPoisoned', message='helper session permanently failed', phase='startup'))
        if not self.helpers:
            factory = self.session_factory or Session
            helper = factory.__new__(factory)
            self.helpers.append(helper)
            try:
                helper.__init__()
            except BaseException as exc:
                self.poisoned = True
                raise HelperFailure(dict(error_class=type(exc).__name__, message=str(exc), phase='startup')) from exc
        return self.helpers[0]

    def ownership(self):
        return [record for helper in self.helpers for record in helper.ownership()]

    def reap(self, deadline):
        while self.helpers:
            for helper in list(self.helpers):
                try:
                    confirmed = helper.close(deadline) is True
                except BaseException as exc:
                    observation = dict(error_class=type(exc).__name__, message=str(exc), phase='helper_cleanup')
                    if observation not in self.errors:
                        self.errors.append(observation)
                    confirmed = False
                self.errors.extend(e for e in helper.owner.errors if e not in self.errors)
                if confirmed:
                    self.helpers.remove(helper)
            if not self.helpers or time.monotonic() >= deadline:
                break
            time.sleep(min(.005, max(0., deadline-time.monotonic())))
        return not self.helpers


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
    """Reuse fixed roles; release work only after a newly acquired sample."""
    lifecycle = lifecycle if lifecycle is not None else HelperLifecycle()
    primary = None
    session = None
    try:
        session = lifecycle.acquire()
        # Idle time between supervised phases is not an active monitor tick.
        if session.ready:
            session.events.append(dict(event='monitor_resume', monotonic=time.monotonic()))
            session.ticks.append(time.monotonic())
        session.await_ready()
        if phase == 'initial_sample':
            deadline = min(deadline, session.setup_deadline)
        sample_only = function is sampler or function == sampler
        session.submit('sample', sampler, deadline)
        task_dispatched = False
        completed = None
        result = None
        while True:
            responses = session.tick(deadline)
            for role, value, received, dispatch in responses:
                if role == 'work':
                    completed, result = received, value
                    continue
                validate_sample(value)
                for field, key in [('device_bytes','gpu_peak_device_gib_limit'),
                                   ('artifact_bytes','new_artifact_disk_gib_limit'),
                                   ('download_bytes','new_download_gib_limit')]:
                    peak[field] = max(peak.get(field, 0), value[field])
                    if peak[field] > config[key]*2**30:
                        raise RuntimeError('S1 resource ceiling exceeded: ' + field)
                owned = set(session.owner.groups.get(worker.pid, ())) if worker else set()
                foreign = sorted(set(value['gpu_pids']) - owned)
                if foreign:
                    raise HelperFailure(dict(error_class='GPUOwnershipError', message='exclusive GPU access lost during ' + phase + ': ' + str(foreign), phase=phase, ownership=dict(owned=sorted(owned), foreign=foreign)))
                if sample_only or (completed is not None and dispatch >= completed):
                    if time.monotonic() >= deadline:
                        raise TimeoutError('S1 return deadline reached')
                    return value if sample_only else result
                if not task_dispatched:
                    session.submit('work', function, deadline)
                    task_dispatched = True
            if session.requests['sample'] is None:
                session.submit('sample', sampler, deadline)
            time.sleep(min(.005, max(0., deadline-time.monotonic())))
    except BaseException as exc:
        lifecycle.poisoned = True
        primary = exc
        if (isinstance(exc, (EOFError, OSError)) and not isinstance(exc, TimeoutError)) or (session is not None and not session.ready and not isinstance(exc, TimeoutError)):
            primary = HelperFailure(dict(error_class=type(exc).__name__, message=str(exc),
                phase='startup' if session is None or len(session.ready) != 2 else 'transport',
                ownership=dict(pid=getattr(exc, 'helper_pid', None))))
            raise primary from exc
        raise
    finally:
        if primary is not None or not lifecycle.retain:
            cleanup_deadline = deadline
            if phase == 'initial_sample' and session is not None:
                cleanup_deadline = session.cleanup_deadline
            if not lifecycle.reap(cleanup_deadline):
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
    lifecycle = HelperLifecycle(retain=is_s1)
    peak = dict(device_bytes=0, artifact_bytes=0, download_bytes=0)
    try:
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
    except BaseException as exc:
        if is_s1 and lifecycle.helpers:
            cleanup_end = lifecycle.helpers[0].cleanup_deadline
            if not lifecycle.reap(cleanup_end):
                exc.cleanup_uncertain = True
                exc.add_note('pre-reservation helper cleanup not confirmed')
        raise
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
        env = dict(os.environ, VIPE_RESERVATION_START=str(start), OMP_NUM_THREADS='1' if is_s1 else '8', OPENBLAS_NUM_THREADS='1' if is_s1 else '8',
                   HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1')
        if is_s1:
            env.update(MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
            import json
            from .s1_clock import ReservationClock
            env['VIPE_S1_RESERVATION_CLOCK'] = json.dumps(ReservationClock.from_reservation(reservation).mapping(), allow_nan=False)
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
                    local=str(ledger.path.parent), config=ledger.config, reservation=reservation,
                    outcome=dict(error=error, result=result_record, acceptance=acceptance), deadline=run_deadline)),
                    run_deadline, sampler, ledger.config, peak, worker=process, phase='reconciliation', lifecycle=lifecycle)
            except Exception as exc:
                error = (error or '') + f'; reconciliation failed: {type(exc).__name__}: {exc}'
                failure_kind, stop_required = 'evidence_reconciliation', True
        # A second Ctrl-C must not interrupt process cleanup.
        for sig in old_handlers:
            signal.signal(sig, signal.SIG_IGN)
        cleanup_uncertain = False if is_s1 else not lifecycle.reap(deadline)
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
                            acceptance=acceptance, evidence_summary_record=evidence_summary)
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
