"""Explicit file-based Plan 031 CPU workers; no inference during preparation."""
import argparse
from pathlib import Path

from vipe_benchmark.config import load
from vipe_benchmark.files import read_json, verify_record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--operation', choices=['prepare', 'annotations', 'auto-annotations',
                        'setup', 'component', 'geometry', 'aggregate', 'report'], required=True)
    args = parser.parse_args()
    clock = None
    request = read_json(args.request)
    if request.get('job_id') != 'S1-calibration-recovery-001':
        config = load(args.config)
        verify_record(request['configuration'])
        if Path(request['configuration']['path']).resolve() != args.config.resolve():
            raise ValueError('worker configuration differs from its frozen request')
    if args.operation == 'prepare' and request.get('job_id') != 'S1-calibration-recovery-001':
        from vipe_benchmark.prepare import prepare
        verify_record(request['exposure'])
        prepare(args.output, config, exposure=request['exposure'])
    elif args.operation == 'auto-annotations' and request.get('job_id') != 'S1-calibration-recovery-001':
        from vipe_benchmark.auto_annotations import run
        run(request, args.output, config)
    elif args.operation in ('setup', 'component', 'geometry', 'aggregate', 'report') or request.get('job_id') == 'S1-calibration-recovery-001':
        try:
            config = load(args.config)
            verify_record(request['configuration'])
            if Path(request['configuration']['path']).resolve() != args.config.resolve():
                raise ValueError('worker configuration differs from its frozen request')
            if request.get('job_id') == 'S1-calibration-recovery-001':
                from vipe_benchmark.s1_recovery import worker_clock
                clock = worker_clock(args, request, config)
            if args.operation == 'setup':
                from vipe_benchmark.runtime import setup as operation
            elif args.operation == 'component':
                from vipe_benchmark.stages import run as operation
            elif args.operation == 'geometry':
                from vipe_benchmark.diagnostics import run as operation
            elif args.operation == 'aggregate':
                from vipe_benchmark.aggregation import run as operation
            else:
                from vipe_benchmark.reporting import run as operation
            if clock is not None:
                operation(request, args.output, config, clock=clock)
            else:
                operation(request, args.output, config)
        except BaseException as exc:
            from vipe_benchmark.files import write_json
            import traceback
            reason = f'{type(exc).__name__}: {exc}'
            extra = {}
            if request.get('job_id') == 'S1-calibration-recovery-001':
                from vipe_benchmark.s1_evidence import preserve_failure
                if not hasattr(exc, 's1_failure_record'):
                    try:
                        preserve_failure(request, args.output, None, exc, stage='worker_before_result', clock=clock)
                    except BaseException as persistence_error:
                        extra['evidence_publication_error'] = str(persistence_error)
                extra.update(first_result=getattr(exc, 's1_first_result', None),
                             failure_evidence=getattr(exc, 's1_failure_record', None))
            try:
                args.output.mkdir(parents=True, exist_ok=True)
                write_json(args.output / 'failure.json', dict(status='failed', reason=reason, **extra,
                    traceback=traceback.format_exc(), job_id=request.get('job_id'),
                    requires_permission_review=isinstance(exc, (PermissionError, ConnectionError)) or
                        any(word in reason.lower() for word in ['permission', 'network', 'connection', 'urlopen', 'cuda unavailable'])))
            except BaseException as persistence_error:
                exc.add_note(f'failure.json publication failed: {persistence_error}')
            raise
    else:
        from vipe_benchmark.annotations import validate
        from vipe_benchmark.files import file_record, write_json
        verify_record(request['inputs'])
        verify_record(request['annotations'])
        bundle = dict(read_json(request['annotations']['path']), status='reviewed')
        result = validate(bundle, read_json(request['inputs']['path']), config)
        args.output.mkdir(parents=True, exist_ok=False)
        write_json(args.output / 'annotations.json', bundle)
        write_json(args.output / 'validation.json', result)
        write_json(args.output / 'result.json', dict(status='complete', annotations=file_record(args.output / 'annotations.json'),
                   validation=file_record(args.output / 'validation.json'), source_bundle=request['annotations']))


if __name__ == '__main__':
    main()
