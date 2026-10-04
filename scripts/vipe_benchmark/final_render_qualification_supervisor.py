"""Supervise an existing qualification reservation through bounded fixed operations.

No reservation, native callback or authority is manufactured here. The immutable
qualification invocation controls the worker and the release handshake binds its live PID.
"""
import math
import os
from pathlib import Path
import subprocess
import time

from .files import file_record, safe_path, write_json
from .final_render_qualification_control import ControlFailure, bounded_json, cpu_environment, exited, run_control
from .supervisor import stop_group


class QualificationSupervisionFailure(RuntimeError):
    def __init__(self, message, evidence):
        self.evidence = evidence
        super().__init__(message)


def _check_sample(sample, request, config):
    for key in ('artifact_bytes','download_bytes','device_bytes','cpu_workers_used','free_disk_bytes'):
        if type(sample.get(key)) is not int or sample[key] < 0:
            raise ValueError('invalid live resource sample: '+key)
    if sample['device_bytes'] > min(request['device_bytes_limit'],config['gpu_peak_device_gib_limit']*2**30):
        raise ValueError('device memory ceiling exceeded')
    if sample['cpu_workers_used'] > min(request['cpu_workers_limit'], config['cpu_max_workers']):
        raise ValueError('CPU worker ceiling exceeded')
    if type(sample.get('phase_artifact_bytes')) is not int or not 0 <= sample['phase_artifact_bytes'] <= request['artifact_bytes_limit']:
        raise ValueError('phase artifact ceiling exceeded')
    if sample['artifact_bytes'] > config['new_artifact_disk_gib_limit']*2**30:
        raise ValueError('cumulative artifact ceiling exceeded')
    if sample['download_bytes'] > config['new_download_gib_limit']*2**30:
        raise ValueError('cumulative download ceiling exceeded')
    if type(sample.get('gpu_pids')) is not list or type(sample.get('owned_pids')) is not list:
        raise ValueError('bounded GPU ownership sample required')
    if set(sample['gpu_pids'])-set(sample['owned_pids']):
        raise ValueError('foreign GPU process; serial ownership lost')


def _supervise_reserved(ledger, reservation, command, output, invocation_record, *, release_path, lifecycle):
    evidence = reservation.get('evidence', {})
    if reservation.get('event') != 'reserve' or evidence.get('record_kind') != 'actual' or evidence.get('execution_authorized') is not True or evidence.get('native_adapter_qualified') is not False or evidence.get('role') != 'native-qualification' or evidence.get('schema') != 'plan069-final-render-qualification-reservation-binding/v1':
        raise ValueError('checked qualification reservation required')
    if command != reservation['command']:
        raise ValueError('exact reserved command required')
    from .final_render_qualification import validate_dispatch_invocation
    validate_dispatch_invocation(invocation_record, ledger, reservation)
    invocation = bounded_json(invocation_record['path'])
    request = bounded_json(invocation['request']['path'])
    output = safe_path(output).resolve()
    release_path = safe_path(release_path).resolve()
    if str(output) != str(Path(invocation['output']).resolve()) or release_path.exists():
        raise ValueError('fresh bound output/release required')
    if '--release-file' not in command or command[command.index('--release-file')+1] != str(release_path):
        raise ValueError('exact reserved release gate required')
    seconds = reservation['seconds']
    start = reservation['monotonic_start']
    boot_id = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    if reservation['boot_id'] != boot_id or not math.isfinite(start) or start > time.monotonic():
        raise ValueError('reservation monotonic identity differs')
    deadline = start + seconds
    process = None
    primary = None
    secondary = []
    cleanup = False
    accepted = None
    final_sample = None
    helpers_clean = True
    peak_device = 0
    peak_cpu = 0
    control_root = output.parent/(output.name+'-controls')
    control_root.mkdir(exist_ok=False)
    if output.exists():
        raise ValueError('fresh qualification worker output required')
    index = 0
    try:
        if time.monotonic()+3 >= deadline:
            raise TimeoutError('insufficient allocation for worker cleanup')
        initial_sample = run_control('sample',invocation_record,control_root/'initial-sample',
            worker_pgid=None,deadline=deadline-3,seconds=15.)
        _check_sample(initial_sample,request,ledger.config)
        peak_device = max(peak_device,initial_sample['device_bytes'])
        peak_cpu = max(peak_cpu,initial_sample['cpu_workers_used'])
        env = cpu_environment()
        # The worker entry owns GPU access; only helpers hide CUDA visibility.
        env.pop('CUDA_VISIBLE_DEVICES', None)
        cache = control_root/'kernel-cache'
        cache.mkdir()
        env.update(TORCH_EXTENSIONS_DIR=str(cache/'torch'),TRITON_CACHE_DIR=str(cache/'triton'),
                   CUDA_CACHE_PATH=str(cache/'cuda'),PYTHONDONTWRITEBYTECODE='1')
        from .s1_helper_session import create_owned_process, register_owned
        with (control_root/'worker.log').open('xb') as log:
            lifecycle['launch_attempted'] = True
            lifecycle['cleanup_confirmed'] = False
            process = create_owned_process('qualification final render worker', subprocess.Popen,
                command, stdout=log, stderr=subprocess.STDOUT, env=env,
                start_new_session=True, deadline=deadline-3)
            register_owned(process.pid, 'qualification final render worker')
            ledger.note('started',job_id=reservation['job_id'],pid=process.pid,
                        pgid=process.pid,invocation=invocation_record)
            write_json(release_path, dict(schema='plan069-final-render-qualification-release/v1',
                                         invocation=invocation_record))
            while True:
                if time.monotonic()+3 >= deadline:
                    raise TimeoutError('qualification worker deadline exceeded')
                status = exited(process)
                if status is not None:
                    if status.si_code != os.CLD_EXITED or status.si_status != 0:
                        raise RuntimeError('qualification worker failed; inspect preserved worker.log')
                    break
                sample = run_control('sample', invocation_record,
                    control_root/f'sample-{index:05d}', worker_pgid=process.pid,
                    deadline=deadline-3, seconds=15.)
                index += 1
                _check_sample(sample,request,ledger.config)
                peak_device = max(peak_device,sample['device_bytes'])
                peak_cpu = max(peak_cpu,sample['cpu_workers_used'])
                # Each sample has a 15-second bound; pause at most three seconds.
                pause = min(time.monotonic()+3.,deadline-3)
                while time.monotonic() < pause:
                    if exited(process) is not None:
                        break
                    time.sleep(.05)
    except BaseException as error:
        primary = error
        if isinstance(error,ControlFailure) and not error.cleanup_confirmed:
            helpers_clean = False
    finally:
        if process is not None:
            try:
                cleanup = not stop_group(process, max(time.monotonic()+.1,deadline))
            except BaseException as error:
                secondary.append(repr(error))
        else:
            cleanup = not lifecycle['launch_attempted']
        cleanup = cleanup and helpers_clean
        lifecycle['cleanup_confirmed'] = cleanup
    if primary is None and cleanup:
        try:
            accepted = run_control('accept',invocation_record,control_root/'accept',
                                   deadline=deadline,seconds=max(.001,deadline-time.monotonic()))
        except BaseException as error:
            primary = error
            if isinstance(error,ControlFailure) and not error.cleanup_confirmed:
                cleanup = False
                lifecycle['cleanup_confirmed'] = False
    if primary is None and accepted is None:
        primary = RuntimeError('qualification acceptance result missing')
    if primary is None and cleanup:
        try:
            # No retained worker group remains: every compute PID is foreign.
            final_sample = run_control('sample',invocation_record,control_root/'final-sample',
                worker_pgid=None,deadline=deadline,seconds=min(15.,max(.001,deadline-time.monotonic())))
            _check_sample(final_sample,request,ledger.config)
            if final_sample['artifact_bytes']+2**20 > ledger.config['new_artifact_disk_gib_limit']*2**30 or final_sample['free_disk_bytes'] < 2**20 or final_sample['phase_artifact_bytes']+2**20 > request['artifact_bytes_limit']:
                raise ValueError('insufficient publication storage reserve')
            peak_device = max(peak_device,final_sample['device_bytes'])
            peak_cpu = max(peak_cpu,final_sample['cpu_workers_used'])
        except BaseException as error:
            primary = error
            if isinstance(error,ControlFailure) and not error.cleanup_confirmed:
                cleanup = False
                lifecycle['cleanup_confirmed'] = False
    if primary is None and not cleanup:
        primary = RuntimeError('qualification worker cleanup uncertain')
    if primary is None and time.monotonic()+1 >= deadline:
        primary = TimeoutError('insufficient qualification terminal publication reserve')
    receipt = dict(schema='plan069-final-render-qualification-supervision/v1',record_kind='actual',
        status='complete' if primary is None else 'failed',invocation=invocation_record,
        reservation_sha256=reservation['event_sha256'],cleanup_confirmed=cleanup,cleanup_uncertain=not cleanup,
        acceptance=accepted,final_sample=final_sample,peak_device_bytes=peak_device,peak_cpu_workers=peak_cpu,
        error=None if primary is None else repr(primary),secondary_errors=secondary,
        execution_authorized=primary is None,native_adapter_qualified=False,role='native-qualification',
        publication_reserve_seconds=1.,elapsed_measurement_boundary='before-terminal-ledger-append')
    receipt_path = control_root/'supervision.json'
    write_json(receipt_path, receipt)
    elapsed = time.monotonic()-start
    if primary is None and elapsed > seconds:
        # Published evidence is never used as success when publication crosses cap.
        primary = TimeoutError('supervision publication exceeded qualification allocation')
        write_json(control_root/'publication-failure.json',dict(error=repr(primary),execution_authorized=False))
    accepted_result = accepted['result'] if primary is None and accepted is not None else None
    finish = ledger.finish(reservation['job_id'],'complete' if primary is None else 'failed',
        elapsed,invocation=invocation_record,cleanup_confirmed=cleanup,cleanup_uncertain=not cleanup,
        result=accepted_result,
        supervision=file_record(receipt_path))
    if time.monotonic() >= deadline:
        terminal = dict(schema='plan069-final-render-qualification-terminal-publication-failure/v1',
            record_kind='actual',invocation=invocation_record,finish=finish,
            elapsed_seconds=time.monotonic()-start,cleanup_confirmed=cleanup,
            execution_authorized=False,native_adapter_qualified=False,role='native-qualification',
            error='terminal publication exceeded allocation; phase receipt is ineligible')
        write_json(control_root/'terminal-publication-failure.json',terminal)
        raise QualificationSupervisionFailure(terminal['error'],
            dict(receipt=receipt,finish=finish,terminal_publication_failure=terminal)) from primary
    if primary is not None:
        raise QualificationSupervisionFailure(str(primary), dict(receipt=receipt,finish=finish)) from primary
    return dict(result=accepted_result,supervision=file_record(receipt_path),finish=finish)


def supervise_reserved(ledger, reservation, command, output, invocation_record, *, release_path):
    """Consume one exact reservation, including charging prelaunch failures."""
    evidence = reservation.get('evidence', {})
    if reservation.get('event') != 'reserve' or evidence.get('record_kind') != 'actual' or evidence.get('execution_authorized') is not True or evidence.get('native_adapter_qualified') is not False or evidence.get('role') != 'native-qualification' or evidence.get('schema') != 'plan069-final-render-qualification-reservation-binding/v1':
        raise ValueError('checked qualification reservation required')
    if ledger.states().get(reservation['job_id']) != reservation:
        raise ValueError('exact current active reservation required before supervision')
    lifecycle = dict(launch_attempted=False,cleanup_confirmed=True)
    try:
        return _supervise_reserved(ledger,reservation,command,output,invocation_record,
                                  release_path=release_path,lifecycle=lifecycle)
    except QualificationSupervisionFailure:
        raise
    except BaseException as error:
        # Do not charge an unrelated or already completed ledger allocation.
        try:
            state = ledger.states().get(reservation['job_id'])
            if state != reservation:
                raise ValueError('exact active reservation changed during supervision')
            failed = dict(schema='plan069-final-render-qualification-supervision-failure/v1',
                record_kind='actual',invocation=invocation_record,error=repr(error),
                cleanup_confirmed=lifecycle['cleanup_confirmed'],execution_authorized=False,
                native_adapter_qualified=False,role='native-qualification')
            failure_path = safe_path(output).parent/('supervision-failure-'+reservation['event_sha256']+'.json')
            write_json(failure_path,failed)
            finish = ledger.finish(reservation['job_id'],'failed',
                max(0.,time.monotonic()-reservation['monotonic_start']),
                invocation=invocation_record,cleanup_confirmed=lifecycle['cleanup_confirmed'],
                cleanup_uncertain=not lifecycle['cleanup_confirmed'],failure=file_record(failure_path))
        except BaseException as secondary:
            error.add_note('terminal accounting: '+repr(secondary))
            raise error
        raise QualificationSupervisionFailure(str(error),dict(failure=failed,finish=finish)) from error
