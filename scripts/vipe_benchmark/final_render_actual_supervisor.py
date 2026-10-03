"""Supervise an existing actual reservation through bounded fixed operations.

No reservation, native callback or authority is manufactured here. The immutable
DO invocation controls the worker and the release handshake binds its live PID.
"""
import math
import os
from pathlib import Path
import subprocess
import time

from .files import file_record, safe_path, write_json
from .final_render_actual_control import bounded_json, cpu_environment, exited, run_control
from .supervisor import stop_group


class ActualSupervisionFailure(RuntimeError):
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
    if type(sample.get('phase_artifact_bytes')) is not int or sample['phase_artifact_bytes'] > request['artifact_bytes_limit']:
        raise ValueError('phase artifact ceiling exceeded')
    if sample['artifact_bytes'] > config['new_artifact_disk_gib_limit']*2**30:
        raise ValueError('cumulative artifact ceiling exceeded')
    if sample['download_bytes'] > config['new_download_gib_limit']*2**30:
        raise ValueError('cumulative download ceiling exceeded')
    if type(sample.get('gpu_pids')) is not list or type(sample.get('owned_pids')) is not list:
        raise ValueError('bounded GPU ownership sample required')
    if set(sample['gpu_pids'])-set(sample['owned_pids']):
        raise ValueError('foreign GPU process; serial ownership lost')


def supervise_reserved(ledger, reservation, command, output, invocation_record, *, release_path):
    evidence = reservation.get('evidence', {})
    if reservation.get('event') != 'reserve' or evidence.get('record_kind') != 'actual' or evidence.get('execution_authorized') is not True or evidence.get('native_adapter_qualified') is not True:
        raise ValueError('checked actual reservation required')
    if command != reservation['command']:
        raise ValueError('exact reserved command required')
    from .final_render_admission import validate_dispatch_invocation
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
    peak_device = 0
    peak_cpu = 0
    control_root = output.parent/(output.name+'-controls')
    control_root.mkdir(exist_ok=False)
    if output.exists():
        raise ValueError('fresh actual worker output required')
    index = 0
    try:
        if time.monotonic()+3 >= deadline:
            raise TimeoutError('insufficient allocation for worker cleanup')
        env = cpu_environment()
        # The worker entry owns GPU access; only helpers hide CUDA visibility.
        env.pop('CUDA_VISIBLE_DEVICES', None)
        cache = control_root/'kernel-cache'
        cache.mkdir()
        env.update(TORCH_EXTENSIONS_DIR=str(cache/'torch'),TRITON_CACHE_DIR=str(cache/'triton'),
                   CUDA_CACHE_PATH=str(cache/'cuda'),PYTHONDONTWRITEBYTECODE='1')
        from .s1_helper_session import create_owned_process, register_owned
        with (control_root/'worker.log').open('xb') as log:
            process = create_owned_process('actual final render worker', subprocess.Popen,
                command, stdout=log, stderr=subprocess.STDOUT, env=env,
                start_new_session=True, deadline=deadline-3)
            register_owned(process.pid, 'actual final render worker')
            ledger.note('started',job_id=reservation['job_id'],pid=process.pid,
                        pgid=process.pid,invocation=invocation_record)
            write_json(release_path, dict(schema='plan069-final-render-actual-release/v1',
                                         invocation=invocation_record))
            while True:
                if time.monotonic()+3 >= deadline:
                    raise TimeoutError('actual worker deadline exceeded')
                status = exited(process)
                if status is not None:
                    if status.si_code != os.CLD_EXITED or status.si_status != 0:
                        raise RuntimeError('actual worker failed; inspect preserved worker.log')
                    break
                sample = run_control('sample', invocation_record,
                    control_root/f'sample-{index:05d}', worker_pgid=process.pid,
                    deadline=deadline-3, seconds=15.)
                index += 1
                _check_sample(sample,request,ledger.config)
                peak_device = max(peak_device,sample['device_bytes'])
                peak_cpu = max(peak_cpu,sample['cpu_workers_used'])
                # Max three seconds between bounded observations, including exit.
                pause = min(time.monotonic()+3.,deadline-3)
                while time.monotonic() < pause:
                    if exited(process) is not None:
                        break
                    time.sleep(.05)
    except BaseException as error:
        primary = error
    finally:
        if process is not None:
            try:
                cleanup = not stop_group(process, max(time.monotonic()+.1,deadline))
            except BaseException as error:
                secondary.append(repr(error))
        else:
            cleanup = True
    if primary is None and cleanup:
        try:
            accepted = run_control('accept',invocation_record,control_root/'accept',
                                   deadline=deadline,seconds=max(.001,deadline-time.monotonic()))
        except BaseException as error:
            primary = error
    if primary is None and not cleanup:
        primary = RuntimeError('actual worker cleanup uncertain')
    if primary is None and time.monotonic() >= deadline:
        primary = TimeoutError('publication-inclusive actual allocation exceeded')
    receipt = dict(schema='plan069-final-render-actual-supervision/v1',record_kind='actual',
        status='complete' if primary is None else 'failed',invocation=invocation_record,
        reservation_sha256=reservation['event_sha256'],cleanup_confirmed=cleanup,
        acceptance=accepted,peak_device_bytes=peak_device,peak_cpu_workers=peak_cpu,
        error=None if primary is None else repr(primary),secondary_errors=secondary,
        execution_authorized=primary is None,native_adapter_qualified=primary is None)
    receipt_path = control_root/'supervision.json'
    write_json(receipt_path, receipt)
    elapsed = time.monotonic()-start
    if primary is None and elapsed > seconds:
        # Published evidence is never used as success when publication crosses cap.
        primary = TimeoutError('supervision publication exceeded actual allocation')
        write_json(control_root/'publication-failure.json',dict(error=repr(primary),execution_authorized=False))
    finish = ledger.finish(reservation['job_id'],'complete' if primary is None else 'failed',
        elapsed,invocation=invocation_record,cleanup_confirmed=cleanup,
        result=None if primary is not None else accepted['result'],
        supervision=file_record(receipt_path))
    if primary is not None:
        raise ActualSupervisionFailure(str(primary), dict(receipt=receipt,finish=finish)) from primary
    return dict(result=accepted['result'],supervision=file_record(receipt_path),finish=finish)
