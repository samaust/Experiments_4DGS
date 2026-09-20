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
        from .s1_recovery import captured_clock
        captured_clock(Path(args['local']), args['config'], args['reservation'], args['command'])
        return None
    if name == 'accept':
        from .s1_recovery import active_binding, accept_result
        from .files import read_json, file_record
        local, output = Path(args['local']), Path(args['output'])
        active_binding(local, args['config'], args['reservation'], args['command'])
        request = read_json(args['reservation']['evidence']['request']['path'])
        result = read_json(output / 'result.json')
        accepted = accept_result(local, args['config'], request, result, output, reservation=args['reservation'])
        return file_record(output / 'result.json'), accepted
    if name == 'reconcile':
        from .s1_recovery import prepare_terminal_evidence
        return prepare_terminal_evidence(Path(args['local']), args['reservation'], args['outcome'], args['deadline'], config=args['config'])
    if name == 'publish':
        from .s1_recovery import terminal_receipt
        return terminal_receipt(Path(args['local']), Path(args['docs']), args['config'],
            args['reservation']['evidence']['authorization'], reservation=args['reservation'], outcome=args['outcome'])
    raise ValueError('unknown CPU helper operation')


def summary_binding(session, request_id, reservation):
    return dict(schema='s1-helper-summary/v1', session=session, role='work', request_id=request_id,
        reservation={key: reservation[key] for key in ('sequence', 'event_sha256')})


def session_operation(operation, session, request_id):
    """Bulk evidence stays in owned immutable files, verified by the work role."""
    from pathlib import Path
    from .files import write_json, file_record, read_json
    from .s1_recovery import strict_record
    name, args = operation['operation'], operation.get('args', {})
    if name == 'reconcile':
        summary = run(operation)
        binding = summary_binding(session, request_id, args['reservation'])
        path = Path(args['local'])/'jobs'/'S1-calibration-recovery-001'/('helper-summary-'+session+'-'+str(request_id)+'.json')
        write_json(path, dict(binding, summary=summary))
        return dict(binding, record=file_record(path))
    if name == 'publish':
        outcome = dict(args['outcome'])
        reference = outcome.get('evidence_summary_record')
        if reference is not None:
            expected = summary_binding(session, reference['request_id'], args['reservation'])
            if set(reference) != set(expected) | {'record'} or any(reference[k] != v for k,v in expected.items()):
                raise ValueError('helper summary reference correlation')
            path = Path(args['local'])/'jobs'/'S1-calibration-recovery-001'/('helper-summary-'+session+'-'+str(reference['request_id'])+'.json')
            if Path(reference['record']['path']) != path:
                raise ValueError('helper summary reference path')
            document = read_json(strict_record(reference['record'])['path'])
            if set(document) != set(expected) | {'summary'} or any(document[k] != v for k,v in expected.items()):
                raise ValueError('helper summary artifact correlation')
            outcome['evidence_summary'] = document['summary']
        return run(dict(operation=name, args=dict(args, outcome=outcome)))
    value = run(operation)
    return list(value) if isinstance(value, tuple) else value


def main(role, session, fd, *, operation_runner=session_operation, before_ready=None):
    import socket
    import time
    from .s1_helper_session import Wire, THREADS, identity
    from pathlib import Path
    channel = socket.socket(fileno=int(fd))
    wire = Wire(channel)
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    def envelope(kind, sequence, payload):
        return dict(version=1, session=session, boot_id=boot, role=role, request_id=sequence, kind=kind, payload=payload)
    if before_ready is not None:
        before_ready(channel)
    wire.queue(envelope('ready', 0, dict(identity(os.getpid()), threads={key:os.environ.get(key) for key in THREADS})))
    last = 0
    try:
        while True:
            message = wire.tick()
            if message is not None:
                if (type(message) is not dict or set(message) != {'version','session','boot_id','role','request_id','kind','payload'} or
                        type(message['version']) is not int or message['version'] != 1 or message['session'] != session or
                        message['boot_id'] != boot or message['role'] != role or message['kind'] != 'request' or
                        type(message['request_id']) is not int or message['request_id'] != last+1):
                    raise ValueError('helper request correlation')
                last += 1
                operation = message['payload']
                name = operation['operation']
                allowed = ('resources','constant') if role == 'sample' else ('prelaunch','accept','reconcile','publish','constant')
                if name not in allowed or (name == 'constant' and os.environ.get('VIPE_CPU_VALIDATION') != '1'):
                    raise ValueError('helper role operation')
                start = time.monotonic()
                try:
                    value = operation_runner(operation, session, last)
                    end = time.monotonic()
                    ok = True
                except BaseException as exc:
                    end = time.monotonic()
                    import traceback
                    raw = traceback.format_exc()
                    value = dict(error_class=type(exc).__name__, message=str(exc)[:1024])
                    args = operation.get('args', {})
                    if 'local' in args:
                        from .files import write_json, file_record
                        path = Path(args['local'])/'jobs'/'S1-calibration-recovery-001'/('helper-error-'+session+'-'+str(last)+'.json')
                        write_json(path, dict(error=raw, session=session, request_id=last))
                        value['record'] = file_record(path)
                    ok = False
                wire.queue(envelope('response', last, dict(operation=name, ok=ok, value=value,
                    acquisition_start=start if role == 'sample' else None,
                    acquisition_end=end if role == 'sample' else None)))
            time.sleep(.001)
    finally:
        channel.close()


if __name__ == '__main__':
    import sys
    main(*sys.argv[1:])
