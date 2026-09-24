from .s1_progress import checked_clock_reservation
"""Serial process-group supervisor with deadlines that include cleanup."""
import os
from pathlib import Path
import signal
import subprocess
import time

from .files import file_record, read_json, safe_path


class SupervisionFailure(RuntimeError):
    def __init__(self, message, *, kind, stop_required, verified_progress_reference=None):
        super().__init__(message)
        self.kind = kind
        self.stop_required = stop_required
        self.verified_progress_reference = verified_progress_reference


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
    job_token=None;pin_state=None;waited_root=False
    if os.environ.get('S1_JOB_LEDGER'):
        from .s1_helper_session import JOB_HANDLES,JOB_OWNERS,_job_state,job_ledger_events,stable_process_identity,retire_job_descendant_pidfd,register_job_pidfd_pin,signal_job_pidfd,close_job_pidfd
        state=_job_state(job_ledger_events())
        matches=[(token,row) for token,row in state['roots'].items()
            if row.get('role')=='B' and row.get('identity',{}).get('pid')==process.pid
            and row.get('handle',{}).get('object_id')==id(process) and JOB_HANDLES.get(token) is process]
        if len(matches)!=1:raise ValueError('stop_group exact retained B handle/root')
        job_token,root=matches[0]
        bound=root['identity']
        if root['state']=='retired':
            if any(child['root']==job_token and child['state']!='retired' for child in state['descendants'].values()):
                raise ValueError('repeat stop_group tree unresolved')
            if any(value['kind']=='pin' and value['owner'].get('root_token')==job_token and value['state']!='closed' for value in state['operations'].values()):
                raise ValueError('repeat stop_group pin close receipt unresolved')
            if Path('/proc',str(process.pid)).exists():
                observed=stable_process_identity(process.pid)
                if any(observed[key]!=bound[key] for key in ('boot_id','pid','start_ticks','pgid')):
                    raise ValueError('repeat stop_group PID/group reuse')
            if group_processes(pgid):raise ValueError('repeat stop_group foreign group')
            process.wait(timeout=max(.01, deadline - time.monotonic()))
            pins=getattr(stop_group,'_pinned',{}).get(job_token)
            if pins is not None:del stop_group._pinned[job_token]
            from .s1_helper_session import JOB_PROCESSES
            if JOB_PROCESSES.get(process.pid)==(job_token,process):del JOB_PROCESSES[process.pid]
            return group_processes(pgid)
        if root['state'] not in ('live','waited'):raise ValueError('stop_group unresolved root state')
        waited_root=root['state']=='waited'
        if waited_root:
            if process.returncode is None or root.get('terminal')!=dict(method='matching child wait',pid=process.pid,returncode=process.returncode):
                raise ValueError('waited stop_group matching Popen wait')
            if any(child['root']==job_token and child['state'] not in ('retired','waited') for child in state['descendants'].values()):
                raise ValueError('waited stop_group descendants unresolved')
            remaining=group_processes(pgid)
            if remaining:return remaining
        if Path('/proc',str(process.pid)).exists():
            observed=stable_process_identity(process.pid)
            if any(observed[key]!=bound[key] for key in ('boot_id','pid','ppid','pgid','start_ticks')):
                raise ValueError('stop_group root identity changed')
        elif not waited_root:
            prior=getattr(stop_group,'_pinned',{}).get(job_token)
            if prior is None or prior['signals']!='complete' or process.returncode is None:
                raise ValueError('stop_group unobserved root exit before safe signal phase')
        if not hasattr(stop_group,'_pinned'):stop_group._pinned={}
        pin_state=stop_group._pinned.get(job_token)
        expected={token:child for token,child in state['descendants'].items() if child['root']==job_token}
        if pin_state is None:
            pin_state=dict(pins={},root_pin=None,signals='complete' if waited_root else 'unstarted')
            stop_group._pinned[job_token]=pin_state
        for (target_token,descriptor),pin in JOB_OWNERS[job_token].get('pidfds',{}).items():
            selected=dict(token=target_token,root=job_token,identity=pin['identity'])
            pin_state['pins'].setdefault((target_token,descriptor),(selected,descriptor))
        for (target_token,descriptor),(selected,_) in pin_state['pins'].items():
            child=expected.get(target_token)
            if target_token==job_token:
                if selected['identity']!=bound:raise ValueError('repeat stop_group root pidfd identity changed')
                pin_state['root_pin']=(selected,descriptor)
            elif child is None or selected['root']!=job_token or selected['identity']!=child.get('identity'):
                raise ValueError('repeat stop_group descendant pidfd identity changed')
            os.fstat(descriptor)
        if not waited_root and pin_state['root_pin'] is None:
            before=stable_process_identity(process.pid)
            if any(before[key]!=bound[key] for key in ('boot_id','pid','ppid','pgid','start_ticks')):raise ValueError('stop_group root pin census changed')
            descriptor=os.pidfd_open(process.pid,0);pin_state['root_pin']=(dict(token=job_token,root=job_token,identity=bound),descriptor)
            after=stable_process_identity(process.pid)
            if any(after[key]!=bound[key] for key in ('boot_id','pid','start_ticks','pgid')):raise ValueError('stop_group root pidfd identity changed')
            register_job_pidfd_pin(job_token,job_token,bound,descriptor)
        for token,child in expected.items():
            if any(key[0]==token for key in pin_state['pins']) or child['state']=='retired':continue
            if child['state']!='live' or not child.get('creator_acknowledged'):
                raise ValueError('stop_group descendant creation not acknowledged')
            identity_value=child['identity'];pid=identity_value['pid'];before=stable_process_identity(pid)
            if any(before[key]!=identity_value[key] for key in ('boot_id','pid','start_ticks','pgid')):raise ValueError('stop_group descendant census changed')
            descriptor=os.pidfd_open(pid,0);selected=dict(token=token,root=job_token,identity=identity_value)
            pin_state['pins'][(token,descriptor)]=(selected,descriptor)
            after=stable_process_identity(pid)
            if any(after[key]!=identity_value[key] for key in ('boot_id','pid','start_ticks','pgid')):raise ValueError('stop_group pidfd identity changed')
            register_job_pidfd_pin(job_token,token,identity_value,descriptor)
    if waited_root:
        pass  # A recorded matching wait forbids any further group signal.
    elif job_token is not None and pin_state is not None and pin_state['signals']=='unstarted':
        targets=[]
        if pin_state['root_pin'] is not None:targets.append(pin_state['root_pin'])
        targets.extend(value for value in pin_state['pins'].values() if value[0]['token'] in expected and expected[value[0]['token']]['state']=='live')
        for selected,descriptor in targets:signal_job_pidfd(job_token,selected['token'],selected['identity'],descriptor,signal.SIGTERM,deadline)
        grace = min(time.monotonic() + 2., deadline - .1)
        while group_processes(pgid) and time.monotonic() < grace:
            time.sleep(.02)
        for selected,descriptor in targets:signal_job_pidfd(job_token,selected['token'],selected['identity'],descriptor,signal.SIGKILL,deadline)
        pin_state['signals']='complete'
    elif job_token is None and (pin_state is None or pin_state['signals']=='unstarted'):
        try:os.killpg(pgid, signal.SIGTERM)
        except ProcessLookupError:pass
        grace=min(time.monotonic()+2.,deadline-.1)
        while group_processes(pgid) and time.monotonic()<grace:time.sleep(.02)
        try:os.killpg(pgid,signal.SIGKILL)
        except ProcessLookupError:pass
    elif pin_state['signals']!='complete':
        raise ValueError('stop_group uncertain partial signal phase')
    while group_processes(pgid) and time.monotonic() < deadline:
        time.sleep(.01)
    process.wait(timeout=max(.01, deadline - time.monotonic()))
    remaining=group_processes(pgid) if job_token is not None else None
    if job_token is not None and remaining:
        # Unknown or surviving group members keep this tree and its pidfds charged.
        return remaining
    from .s1_helper_session import retire_owned
    if job_token is not None:
        from .s1_helper_session import retire_job_descendant_pidfd
        for (token,descriptor),(selected,_) in list(pin_state['pins'].items()):
            retire_job_descendant_pidfd(selected,descriptor,deadline)
        remaining=group_processes(pgid)
        if remaining:return remaining
        if pin_state['root_pin'] is not None:
            selected,descriptor=pin_state['root_pin']
            close_job_pidfd(job_token,job_token,selected['identity'],descriptor)
        if waited_root:
            from .s1_helper_session import finalize_waited_job_root
            finalize_waited_job_root(job_token,process,process.pid)
        else:retire_owned(process.pid,handle=process)
        if _job_state(job_ledger_events())['roots'][job_token]['state']!='retired':
            raise ValueError('stop_group root tree retirement not durable')
        del stop_group._pinned[job_token]
    else:retire_owned(process.pid)
    return remaining if job_token is not None else group_processes(pgid)


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


from .s1_helper_session import Session, Trace, GPUOwnershipError


class HelperLifecycle:
    """A supervise call owns one persistent session; standalone calls retire it."""
    def __init__(self, *, retain=False, session_factory=None):
        self.helpers = []
        self.errors = Trace(32, errors=True)
        self.retain = retain
        self.session_factory = session_factory
        self.poisoned = False
        from .s1_progress import RetainedProgress
        self.progress = RetainedProgress()

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
                raise HelperFailure(dict(error_class=type(exc).__name__, message=str(exc)[:1024], phase='startup', cause=None if exc.__cause__ is None else dict(error_class=type(exc.__cause__).__name__,message=str(exc.__cause__)[:1024]))) from exc
        helper=self.helpers[0]
        if hasattr(helper, 'progress_cache'): self.progress=helper.progress_cache
        return helper

    def ownership(self):
        return [record for helper in self.helpers for record in helper.ownership()]

    def reap(self, deadline):
        self.progress.freeze('helper retirement')
        while self.helpers:
            for helper in list(self.helpers):
                try:
                    confirmed = helper.close(deadline) is True
                except BaseException as exc:
                    observation = dict(error_class=type(exc).__name__, message=str(exc), phase='helper_cleanup')
                    if observation not in self.errors:
                        self.errors.append(observation)
                    confirmed = False
                owner = getattr(helper, 'owner', None)
                self.errors.extend(e for e in getattr(owner, 'errors', ()) if e not in self.errors)
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
            or len(pids)>64 or len(pids) != len(set(pids))):
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
            session.resume()
        if session.ready.keys() != {'work','sample'}:
            session.await_ready()
        session.set_worker(worker)
        if phase == 'initial_sample':
            deadline = min(deadline, session.setup_deadline)
        sample_only = function is sampler or function == sampler
        session.submit('sample', sampler, deadline)
        task_dispatched = False
        completed = None
        result = None
        while True:
            responses = session.tick(deadline)
            if lifecycle.progress.integrity:
                raise ValueError('progress integrity failure: '+lifecycle.progress.integrity)
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
                if sample_only or (completed is not None and dispatch >= completed):
                    if time.monotonic() >= deadline:
                        raise TimeoutError('S1 return deadline reached')
                    if phase == 'initial_sample': session.accepted_initial = True
                    return value if sample_only else result
                if not task_dispatched:
                    session.submit('work', function, deadline)
                    task_dispatched = True
            if session.requests['sample'] is None:
                session.submit('sample', sampler, deadline)
            time.sleep(min(.005, max(0., deadline-time.monotonic())))
    except BaseException as exc:
        record_progress_failure(lifecycle,exc,phase)
        primary = exc
        if isinstance(exc, GPUOwnershipError):
            primary = HelperFailure(dict(error_class='GPUOwnershipError', message=str(exc), phase=phase))
            primary.verified_progress_reference = lifecycle.progress.reference()
            raise primary from exc
        if (isinstance(exc, (EOFError, OSError)) and not isinstance(exc, TimeoutError)) or (session is not None and not session.ready and not isinstance(exc, TimeoutError)):
            primary = HelperFailure(dict(error_class=type(exc).__name__, message=str(exc),
                phase='startup' if session is None or len(session.ready) != 2 else 'transport',
                ownership=dict(pid=getattr(exc, 'helper_pid', None))))
            primary.verified_progress_reference = lifecycle.progress.reference()
            raise primary from exc
        raise
    finally:
        if primary is not None or not lifecycle.retain:
            cleanup_deadline = deadline
            if phase == 'initial_sample' and session is not None:
                cleanup_deadline = getattr(session, 'cleanup_deadline', deadline)
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
        if is_s1:
            if lifecycle.poisoned or not lifecycle.helpers: raise ValueError('S1 admission session unavailable')
            lifecycle.helpers[0].admission_guard()
        reservation = reserve(job_id, command, evidence, seconds_limit=seconds_limit)
    except BaseException as exc:
        try:
            if is_s1 and lifecycle.helpers:
                cleanup_end = getattr(lifecycle.helpers[0], 'cleanup_deadline', time.monotonic())
                if not lifecycle.reap(cleanup_end):
                    exc.cleanup_uncertain = True
                    exc.add_note('pre-reservation helper cleanup not confirmed')
        except BaseException as cleanup:
            exc.cleanup_uncertain=True
            exc.add_note('pre-reservation helper cleanup: '+repr(cleanup))
            exc.pre_reservation_cleanup_error=cleanup
        raise
    start = reservation['monotonic_start']
    deadline = start + reservation['seconds']
    cleanup_reserve = min(30., reservation['seconds'] / 4)
    run_deadline = deadline - cleanup_reserve
    process, stopped, error = None, [], None
    primary_failure=None;primary_exception=None;secondary_failures=[]
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
            env.update(MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1', OPENCV_FOR_THREADS_NUM='1')
            import json
            from .s1_clock import ReservationClock
            env['VIPE_S1_RESERVATION_CLOCK'] = json.dumps(checked_clock_reservation(reservation).mapping(), allow_nan=False)
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
                progress_context = monitored_call(dict(operation='prelaunch', args=dict(local=str(ledger.path.parent),
                    config=ledger.config, reservation=reservation, command=command)),
                    run_deadline, sampler, ledger.config, peak, phase='prelaunch', lifecycle=lifecycle)
                if time.monotonic() >= run_deadline:
                    raise TimeoutError('S1 prelaunch deadline exhausted')
                lifecycle.helpers[0].install_progress(progress_context,run_deadline)
                if time.monotonic()>=run_deadline:raise TimeoutError('S1 original work deadline immediately before worker launch (after progress installation)')
                env['VIPE_S1_PROGRESS_CONTEXT'] = json.dumps(progress_context,allow_nan=False)
            if is_s1 and os.environ.get('S1_OWNED_ROOT_NOTE'):
                from .s1_helper_session import predispatch_owned
                if time.monotonic()>=run_deadline:raise TimeoutError('S1 original work deadline before ownership admission')
                owned=predispatch_owned('supervisor worker')
            if is_s1 and time.monotonic() >= run_deadline:
                raise TimeoutError('S1 original work deadline immediately before worker launch')
            from .s1_helper_session import create_owned_process
            process = create_owned_process('supervisor worker',subprocess.Popen,command, deadline=run_deadline if is_s1 else None, stdout=log, stderr=subprocess.STDOUT,
                                       start_new_session=True, env=env)
            from .s1_helper_session import register_owned
            register_owned(process.pid,'supervisor worker')
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
                owned = ({row.pid for row in lifecycle.helpers[0].last_sample['post'].rows} if is_s1
                         else set(group_processes(process.pid, include_zombies=True)))
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
                exit_code = lifecycle.helpers[0].worker_exit() if is_s1 else process.poll()
                if exit_code is not None:
                    if exit_code:
                        failure_kind, stop_required = 'worker_failure', False
                        raise RuntimeError(f'worker exited {exit_code}')
                    # Child survival after the parent exits invalidates the result.
                    if not is_s1 and group_processes(process.pid):
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
        primary_exception=exc
        primary_failure=dict(error_class=type(exc).__name__,message=str(exc),kind=failure_kind,
            phase=getattr(exc,'failure',{}).get('phase',getattr(exc,'s1_phase','supervisor')),
            observed=getattr(exc,'s1_first_observed',time.monotonic()),stop_required=stop_required)
    finally:
        evidence_summary=None;cleanup_uncertain=False;helper_errors=[]
        def final_step(phase,operation,default=None):
            # Every fallible finalization edge uses the same primary-preserving
            # closure. A first cleanup error is itself a failure, never success.
            nonlocal primary_exception,primary_failure,error,failure_kind,stop_required,cleanup_uncertain
            try:return operation()
            except BaseException as exc:
                observed=time.monotonic()
                item=dict(error_class=type(exc).__name__,message=str(exc),phase=phase,observed=observed)
                secondary_failures.append(item)
                if primary_exception is None:
                    primary_exception=exc
                    primary_failure=dict(item,kind=phase,stop_required=True)
                else:primary_exception.add_note(phase+': '+type(exc).__name__+': '+str(exc))
                error=(error or '')+'; '+phase.replace('_',' ')+' failed: '+type(exc).__name__+': '+str(exc)
                failure_kind=phase;stop_required=True
                if phase in ('cleanup','final_cleanup','ownership','signal_restore'):cleanup_uncertain=True
                return default
        def reconcile():
            if is_s1 and not lifecycle.poisoned and time.monotonic()<run_deadline:
                return monitored_call(dict(operation='reconcile',args=dict(local=str(ledger.path.parent),
                    config=ledger.config,reservation=reservation,outcome=dict(error=error,result=result_record,acceptance=acceptance),deadline=run_deadline)),
                    run_deadline,sampler,ledger.config,peak,worker=process,phase='reconciliation',lifecycle=lifecycle)
        evidence_summary=final_step('evidence_reconciliation',reconcile)
        for sig in old_handlers:final_step('signal_ignore',lambda sig=sig:signal.signal(sig,signal.SIG_IGN))
        def reap_helpers():
            if not lifecycle.reap(deadline):raise RuntimeError('helper cleanup not confirmed')
        if not is_s1:final_step('cleanup',reap_helpers)
        def retire_worker():
            if is_s1 and lifecycle.helpers:lifecycle.helpers[0].retire_worker()
        final_step('cleanup',retire_worker)
        stopped=final_step('cleanup',lambda:stop_group(process,deadline),[])
        for sig,handler in old_handlers.items():final_step('signal_restore',lambda sig=sig,handler=handler:signal.signal(sig,handler))
        def check_stopped():
            if stopped:raise RuntimeError('processes not confirmed stopped: '+str(stopped))
        final_step('cleanup',check_stopped)
        elapsed=time.monotonic()-start
        def check_total():
            if time.monotonic()-start>=reservation['seconds']:raise TimeoutError('total deadline exceeded')
        final_step('cleanup_deadline',check_total)
        evidence=dict(error=error,result=result_record,peak=peak,surviving_pids=stopped,
            cleanup_confirmed=not stopped and not cleanup_uncertain,cleanup_uncertain=cleanup_uncertain,
            failure_kind=failure_kind if error else None,stop_required=stop_required if error else False,
            primary_failure=primary_failure,secondary_failures=secondary_failures,secondary_outcome_kind=None)
        if is_s1:
            def progress_fields():
                evidence.update(reservation={k:reservation[k] for k in ('sequence','event_sha256')},acceptance=acceptance,
                    evidence_summary_record=evidence_summary,verified_progress_reference=lifecycle.progress.reference(),
                    terminal_receipt=None,terminal_publication_status='unavailable')
            final_step('progress_reference',progress_fields)
            def publish():
                if lifecycle.poisoned or lifecycle.progress.integrity or time.monotonic()>=deadline-min(.1,cleanup_reserve/10):
                    raise RuntimeError('retained helper unavailable for terminal publication')
                if terminal_publisher is None:raise ValueError('S1 charged terminal publisher required')
                evidence['terminal_receipt']=monitored_call(dict(operation='publish',args=dict(local=str(ledger.path.parent),
                    docs=str(terminal_docs),config=ledger.config,reservation=reservation,outcome=evidence)),
                    deadline-min(.1,cleanup_reserve/10),sampler,ledger.config,peak,worker=None,phase='publication',lifecycle=lifecycle)
                evidence['terminal_publication_status']='published'
            final_step('evidence_publication',publish)
            final_step('publication_deadline',check_total)
        final_step('final_cleanup',reap_helpers)
        if is_s1:
            reference=final_step('progress_reference',lambda:lifecycle.progress.reference())
            if reference is not None:evidence['verified_progress_reference']=reference
        evidence['helper_ownership']=final_step('ownership',lifecycle.ownership,[])
        helper_errors=final_step('ownership',lambda:list(lifecycle.errors),[])
        evidence['helper_cleanup_errors']=helper_errors
        def refresh_evidence():
            evidence.update(error=error,primary_failure=primary_failure,secondary_failures=secondary_failures,
                failure_kind=primary_failure['kind'] if primary_failure else (failure_kind if error else None),
                secondary_outcome_kind=failure_kind if primary_failure and failure_kind!=primary_failure['kind'] else None,
                stop_required=stop_required if error else False,cleanup_uncertain=cleanup_uncertain,
                cleanup_confirmed=not stopped and not cleanup_uncertain)
        refresh_evidence()
        elapsed=time.monotonic()-start
        def finalize_ledger():
            if checkpoint and not error:ledger.checkpoint(job_id,elapsed,**evidence)
            else:ledger.finish(job_id,'failed' if error else 'complete',elapsed,**evidence)
        final_step('ledger_finalization',finalize_ledger)
        refresh_evidence()
        if primary_failure is not None:failure_kind=primary_failure['kind']
    if error:
        failure=SupervisionFailure(error,kind=failure_kind,stop_required=stop_required,verified_progress_reference=evidence.get('verified_progress_reference'))
        failure.primary_failure=primary_failure;failure.primary_exception=primary_exception
        failure.secondary_failures=list(secondary_failures);failure.helper_cleanup_errors=helper_errors
        failure.final_evidence=evidence
        raise failure from primary_exception
    return read_json(result_record['path'])



def record_progress_failure(lifecycle,error,phase):
    """The same owner transition handles local and transported integrity failure."""
    from .s1_progress import ProgressIntegrityError
    lifecycle.progress.freeze(error,integrity=isinstance(error,ProgressIntegrityError) or getattr(error,'failure',{}).get('error_class')=='ProgressIntegrityError')
    error.verified_progress_reference=lifecycle.progress.reference()
    lifecycle.poisoned=True
    error.s1_phase=phase
    if not hasattr(error,'s1_first_observed'):error.s1_first_observed=time.monotonic()
    return error.verified_progress_reference
