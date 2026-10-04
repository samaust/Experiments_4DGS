"""Fixed native control operations run in bounded, retained process groups.

The fixture entry only tests operating-system boundaries and never issues actual
execution authority. Production operations are selected by name, never callbacks.
"""
import argparse
import json
import math
import os
from pathlib import Path
import subprocess
import shutil
import sys
import time

from .files import file_record, read_json, safe_path, verify_record, write_json
from .supervisor import group_processes, stop_group

MAX_MESSAGE = 1024 * 1024


class ControlFailure(RuntimeError):
    def __init__(self, message, *, cleanup_confirmed=True):
        self.cleanup_confirmed = cleanup_confirmed
        super().__init__(message)


def bounded_json(path):
    path = safe_path(path)
    with path.open('rb') as stream:
        payload = stream.read(MAX_MESSAGE + 1)
    if len(payload) > MAX_MESSAGE:
        raise ValueError('control message exceeds bounded transport')
    return json.loads(payload)


def exited(process):
    """Observe completion without reaping the group identity retained for cleanup."""
    return os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)


def cpu_environment():
    env = os.environ.copy()
    for name in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS',
                 'NUMEXPR_NUM_THREADS','OPENCV_FOR_THREADS_NUM'):
        env[name] = '1'
    env['CUDA_VISIBLE_DEVICES'] = ''
    return env


def _run(command, root, seconds, deadline, kind):
    root = safe_path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    if any(root.iterdir()):
        raise ValueError('fresh control evidence directory required')
    if not math.isfinite(seconds) or seconds <= 0:
        raise ValueError('positive finite control deadline required')
    finish = min(time.monotonic()+seconds, deadline) if deadline is not None else time.monotonic()+seconds
    if finish <= time.monotonic():
        raise ControlFailure('control deadline exhausted before launch')
    process = None
    launch_attempted = False
    primary = None
    cleanup = False
    observed = None
    try:
        from .s1_helper_session import create_owned_process, register_owned
        with (root/'control.log').open('xb') as log:
            launch_attempted = True
            process = create_owned_process('final render control', subprocess.Popen,
                command, stdout=log, stderr=subprocess.STDOUT, cwd=root,
                env=cpu_environment(), start_new_session=True, deadline=finish)
            register_owned(process.pid, 'final render control')
            while time.monotonic() < finish:
                observed = exited(process)
                if observed is not None:
                    break
                time.sleep(min(.02,max(0,finish-time.monotonic())))
            if observed is None:
                raise ControlFailure('control operation deadline exceeded')
            if observed.si_code != os.CLD_EXITED or observed.si_status != 0:
                raise ControlFailure('control operation failed; inspect control.log')
    except BaseException as error:
        primary = error
    finally:
        if process is not None:
            try:
                # Cleanup gets a bounded emergency window even after work expires.
                # The caller charges this window and rejects a phase overrun.
                remaining = stop_group(process, time.monotonic()+2.5)
                cleanup = not remaining
            except BaseException as error:
                if primary is None:
                    primary = error
                else:
                    primary.add_note('control cleanup: '+repr(error))
        else:
            cleanup = not launch_attempted
    if primary is None and time.monotonic() >= finish:
        primary = ControlFailure('control cleanup exceeded operation deadline')
    if primary is not None or not cleanup:
        write_json(root/'control-failure.json', dict(schema='plan069-final-render-control-failure/v1',
            record_kind=kind, error=repr(primary), cleanup_confirmed=cleanup,
            execution_authorized=False))
        raise ControlFailure(str(primary or 'control cleanup uncertain'),cleanup_confirmed=cleanup) from primary
    message = bounded_json(root/'response.json')
    if type(message) is not dict:
        raise ControlFailure('control response must be an object')
    if kind == 'fixture':
        message = dict(message, record_kind='fixture', execution_authorized=False,
                       native_adapter_qualified=False)
    if time.monotonic() >= finish:
        write_json(root/'control-failure.json',dict(schema='plan069-final-render-control-failure/v1',
            record_kind=kind,error='control publication exceeded operation deadline',
            cleanup_confirmed=cleanup,execution_authorized=False))
        raise ControlFailure('control publication exceeded operation deadline',cleanup_confirmed=cleanup)
    return message


def run_fixture_control(command, root, *, seconds=1., deadline=None):
    """CPU fake process seam; its output cannot satisfy actual admission."""
    return _run(list(command), root, seconds, deadline, 'fixture')


def run_control(operation, invocation_record, root, *, worker_pgid=None,
                seconds=15., deadline=None):
    if operation not in ('sample', 'accept'):
        raise ValueError('fixed control operation required')
    if verify_record(invocation_record) != invocation_record:
        raise ValueError('immutable invocation changed')
    invocation = bounded_json(invocation_record['path'])
    worker = invocation['interpreter']
    # Interpreter is verified again inside the source-bound invocation gate.
    from .final_render_admission import interpreter_invocation
    interpreter = interpreter_invocation(worker, invocation['interpreter_invocation'])
    entry = Path(__file__).resolve().parents[1]/'final-render-actual-control.py'
    command = [interpreter, str(entry), operation, '--invocation', invocation_record['path']]
    if worker_pgid is not None:
        command += ['--worker-pgid', str(worker_pgid)]
    value = _run(command, root, seconds, deadline, 'actual')
    if value.get('schema') != 'plan069-final-render-control-response/v1' or value.get('operation') != operation or value.get('invocation') != invocation_record or value.get('cleanup_confirmed') is not True:
        raise ControlFailure('unbound control response')
    return value


def _operation(operation, invocation_record, pgid):
    from .final_render_admission import invocation_binding
    from .extended_final_render_contract import parse_request
    invocation = bounded_json(invocation_record['path'])
    request = parse_request(bounded_json(invocation['request']['path']))
    if operation == 'accept' or pgid is not None:
        invocation_binding(invocation_record, request, invocation['arm'], invocation['phase'])
    elif invocation.get('record_kind') != 'actual' or verify_record(invocation['request']) != invocation['request']:
        raise ValueError('actual immutable prelaunch invocation required')
    value = dict(schema='plan069-final-render-control-response/v1', record_kind='actual',
                 operation=operation, invocation=invocation_record, cleanup_confirmed=True)
    if operation == 'sample':
        from .supervisor import gpu_reading, directory_bytes
        from .budgets import budget_snapshot
        members = group_processes(pgid) if pgid is not None else []
        threads = 0
        for pid in members:
            try:
                threads += len(list(Path('/proc',str(pid),'task').iterdir()))
            except FileNotFoundError:
                pass
        run_root = Path(invocation['ledger_path']).resolve().parent
        storage = budget_snapshot(run_root)
        numerical = max(1,request['cpu_workers_limit']-1) if invocation['phase'] in ('train','render') else 1
        workers = numerical+max(0,len(members)-1)+1 if members else 0
        value.update(gpu_reading(), artifact_bytes=storage['artifact_bytes'],
                     download_bytes=storage['download_bytes'],
                     free_disk_bytes=shutil.disk_usage(run_root).free,
                     phase_artifact_bytes=directory_bytes(invocation['output']) if Path(invocation['output']).exists() else 0,
                     cpu_workers_used=workers, observed_thread_count=threads,
                     owned_pids=members, observed_unix=time.time())
    else:
        from .final_render_actual_result import validate_actual_worker_result
        result_path = safe_path(invocation['output'])/'result.json'
        result_record = file_record(result_path)
        result = read_json(result_path)
        validate_actual_worker_result(request, invocation['arm'], invocation['phase'], result, published=True)
        if file_record(result_path) != result_record:
            raise ValueError('result changed during acceptance')
        value['result'] = result_record
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('operation', choices=('sample','accept'))
    parser.add_argument('--invocation', required=True)
    parser.add_argument('--worker-pgid', type=int)
    args = parser.parse_args()
    write_json(Path.cwd()/'response.json', _operation(args.operation,
        file_record(args.invocation), args.worker_pgid))


if __name__ == '__main__':
    main()
