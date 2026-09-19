"""Serializable CPU operations for the S1 monitor; never construct a model."""
import os


def run(operation):
    from pathlib import Path
    name = operation['operation']
    args = operation.get('args', {})
    if name == 'constant':
        return args['value']
    if name == 'resources' and os.environ.get('VIPE_CPU_VALIDATION') == '1':
        raise AssertionError('unexpected live resource operation in CPU validation')
    if name == 'resources':
        from .execution import resources
        return resources(Path(args['local']), gpu=True)
    if name == 'prelaunch':
        from .s1_recovery import active_binding
        active_binding(Path(args['local']), args['config'], args['reservation'], args['command'])
        return None
    if name == 'accept':
        from .s1_recovery import active_binding, accept_result
        from .files import read_json, file_record
        local, output = Path(args['local']), Path(args['output'])
        active_binding(local, args['config'], args['reservation'], args['command'])
        request = read_json(args['reservation']['evidence']['request']['path'])
        result = read_json(output / 'result.json')
        accepted = accept_result(local, args['config'], request, result, output)
        return file_record(output / 'result.json'), accepted
    if name == 'reconcile':
        from .s1_recovery import prepare_terminal_evidence
        return prepare_terminal_evidence(Path(args['local']), args['reservation'], args['outcome'], args['deadline'])
    if name == 'publish':
        from .s1_recovery import terminal_receipt
        return terminal_receipt(Path(args['local']), Path(args['docs']), args['config'],
            args['reservation']['evidence']['authorization'], reservation=args['reservation'], outcome=args['outcome'])
    raise ValueError('unknown CPU helper operation')


def entry(connection, operation):
    # Spawned interpreter, no inherited model/native thread state.
    import signal
    import traceback
    import time
    os.setsid()
    for name in ('OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS'):
        os.environ[name] = '1'
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, signal.SIG_DFL)
    try:
        result = run(operation)
        connection.send((True, result))
    except BaseException as exc:
        connection.send((False, dict(error_class=type(exc).__name__, message=str(exc),
            phase=operation['operation'], traceback=traceback.format_exc())))
    finally:
        connection.close()
