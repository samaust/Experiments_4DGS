"""Build an immutable diagnostic request after its separate DO; never execute it."""
import argparse
import hashlib
import json
from pathlib import Path


def record(path):
    path = Path(path).absolute()
    if 'prompts' in path.parts or 'prompts' in path.resolve().parts:
        raise ValueError('prompts prohibited')
    data = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'run', 'authorization', 'source-review', 'cpu-validation', 'worker-output', 'output'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    root = Path(args.root).resolve(); run = Path(args.run).resolve(); target = Path(args.output).absolute()
    review_path = root / 'docs/specs/plan031-execution/D6-driver-diagnostic-review-001.json'
    proposal = json.loads(review_path.read_text())['proposal']
    setup = json.loads(Path(proposal['setup']['path']).read_text())
    output = Path(args.worker_output).absolute()
    if not output.is_relative_to(run) or output.exists() or output.with_suffix('.syscalls.log').is_symlink():
        raise ValueError('fresh diagnostic output in shared run required')
    request = dict(schema='plan069-D6-driver-diagnostic-request/v1', record_kind='actual',
        review=record(review_path), authorization=record(args.authorization),
        source_review=record(args.source_review), cpu_validation=record(args.cpu_validation),
        setup=proposal['setup'], predecessor_finish=proposal['predecessor_finish'],
        worker=proposal['worker'], guard=proposal['guard'], strace=proposal['strace'],
        dependencies=proposal['dependencies'], interpreter_invocation=setup['python_executable'],
        executable=record(Path(setup['python_executable']).resolve()),
        ledger_path=str(run / 'ledger.jsonl'), output=str(output))
    request['command'] = [request['strace']['path'], '-f', '-qq', '-s', '128', '-e',
        'trace=socket,socketpair,connect,bind,listen,accept,accept4,sendto,sendmsg,recvfrom,recvmsg,ioctl',
        '-e', 'raw=sendto,sendmsg,recvfrom,recvmsg,ioctl', '-o', str(output.with_suffix('.syscalls.log')),
        request['interpreter_invocation'], '-I', '-B', request['worker']['path'], '--request', str(target)]
    approval = json.loads(Path(args.authorization).read_text())
    if approval.get('status') != 'DO' or approval.get('review') != request['review']:
        raise ValueError('separate matching diagnostic DO required before request creation')
    with target.open('x') as stream:
        json.dump(request, stream, indent=2); stream.write('\n')


if __name__ == '__main__':
    main()
