"""Bind a root-approved D6 CPU capture or finalization; never launch it."""
import argparse
import json
from pathlib import Path
import sys
from prepare_source_review import record


def prepare(args):
    root, run = Path(args.root).absolute(), Path(args.run).absolute()
    review_path = Path(args.source_review).absolute()
    review = json.loads(review_path.read_text())
    if review.get('candidate') != 'D6' or review.get('status') != 'passed' or not review.get('reviewer'):
        raise ValueError('passed independent D6 source review required')
    for item in review['local_sources']:
        if record(item['path']) != item:
            raise ValueError('current source changed')
    setup_path = run / 'jobs/plan069-D6-setup-001/result.json'
    setup = json.loads(setup_path.read_text())
    if setup.get('candidate') != 'D6' or setup.get('status') != 'complete' or setup.get('record_kind') != 'actual':
        raise ValueError('accepted actual D6 setup required')
    bootstrap = Path(args.interpreter).absolute()
    method_dir = root / 'docs/research/vipe-alternatives/plan031-execution'
    bindings = dict(runtime_recipe=review['runtime_recipe'], source_review=record(review_path))
    command = [str(bootstrap), '-B']
    if args.mode == 'capture':
        method = method_dir / 'moge-cpu-method-002/producer.py'
        bindings.update(setup=record(setup_path),
            setup_request=record(run / 'requests/plan069-D6-setup-001.json'),
            setup_dispatch=record(root / 'docs/research/vipe-alternatives/plan031-20260913T032700Z/plan069-D6-setup-001.json'))
        command += [str(method), 'capture', '--root', str(root), '--candidate', 'D6',
            '--setup', bindings['setup']['path'], '--setup-request', bindings['setup_request']['path'],
            '--setup-dispatch', bindings['setup_dispatch']['path'], '--output', args.producer_output,
            '--seconds', str(args.seconds - args.cleanup_seconds), '--artifact-bytes', str(args.artifact_bytes)]
        schema = 'plan069-moge-parent-cpu-request/v1'
    else:
        if not args.capture or not args.commercial_assessment:
            raise ValueError('capture and independent commercial assessment required')
        capture_dir = Path(args.capture).absolute()
        capture = json.loads((capture_dir / 'capture.json').read_text())
        native = json.loads((capture_dir / 'native-cpu.json').read_text())
        assessment_path = Path(args.commercial_assessment).absolute()
        assessment = json.loads(assessment_path.read_text())
        method = method_dir / 'moge-cpu-method-003/producer.py'
        bindings.update(capture=record(capture_dir / 'capture.json'), native_cpu=record(capture_dir / 'native-cpu.json'),
            dependency_manifest=native['dependency_manifest'], commercial_assessment=record(assessment_path),
            permission_report=assessment['permission_report'], capture_method=capture['method'])
        command += [str(method), 'finalize', '--root', str(root), '--candidate', 'D6',
            '--capture', str(capture_dir), '--commercial-assessment', str(assessment_path),
            '--source-review', str(review_path), '--output', args.producer_output]
        schema = 'plan069-moge-parent-finalize-request/v2'
    request = dict(schema=schema, candidate='D6', root=str(root),
        root_source_commit=review['root_source_commit'], accepted_setup_sha256=record(setup_path)['sha256'],
        bootstrap=record(bootstrap.resolve()), interpreter_invocation=str(bootstrap),
        seconds=args.seconds, cleanup_seconds=args.cleanup_seconds, cpu_workers=7,
        admitted=True, charge_owner='root', bindings=bindings, command=command, method=record(method),
        output=args.wrapper_output, disk_roots=json.loads(Path(args.disk_roots).read_text()))
    with Path(args.output).open('x') as stream:
        json.dump(request, stream, indent=2)
        stream.write('\n')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'run', 'source-review', 'interpreter', 'disk-roots', 'producer-output', 'wrapper-output', 'output'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--mode', choices=('capture', 'finalize'), required=True)
    parser.add_argument('--seconds', type=float, default=180)
    parser.add_argument('--cleanup-seconds', type=float, default=20)
    parser.add_argument('--artifact-bytes', type=int, default=67108864)
    parser.add_argument('--capture')
    parser.add_argument('--commercial-assessment')
    prepare(parser.parse_args())
