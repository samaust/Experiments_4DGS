"""Bind the final integrated checkout without running tests or changing the ledger."""

import argparse
import hashlib
import json
import subprocess
import time
from pathlib import Path


def record(path):
    path = Path(path).absolute()
    if 'prompts' in path.parts or 'prompts' in path.resolve().parts:
        raise ValueError('forbidden prompts path')
    data = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def write(path, value):
    with path.open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def main():
    start = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', required=True)
    parser.add_argument('--overlay', required=True)
    parser.add_argument('--packet', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--candidate', required=True, choices=['D6', 'D8', 'D9', 'D10'])
    parser.add_argument('--cpu-admission', required=True)
    args = parser.parse_args()
    root = Path(args.checkout).resolve()
    overlay = Path(args.overlay).resolve()
    packet = Path(args.packet).resolve()
    output = Path(args.output).resolve()
    if packet.exists() or output.exists():
        raise ValueError('packet and capture output must both be fresh')
    if not overlay.is_dir():
        raise ValueError('CPU overlay is unavailable')
    git = lambda *words: subprocess.check_output(['git', *words], cwd=root, text=True)
    head = git('rev-parse', 'HEAD').strip()
    if git('status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('tracked checkout must be committed before binding')
    here = Path(__file__).resolve().parent
    launcher = record(here / 'launcher.py')
    interpreter = record('/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python')
    admission = record(args.cpu_admission)
    # Preserve the existing CPU metadata/pycolmap inventory scope. Rehashing an
    # existing inventory fails if its contents changed; it never silently accepts
    # replacement dependencies or grants native model qualification.
    template = root / 'docs/research/vipe-alternatives/plan031-execution/depth-combined-cpu-retry-review-001/environment-bindings.json'
    environment = json.loads(template.read_text())
    for package in environment:
        for row in package['metadata'] + package.get('files', []):
            if record(row['path']) != row:
                raise ValueError('changed CPU environment record: ' + row['path'])
    origins = {Path(package['origin']).resolve() for package in environment}
    if overlay not in origins:
        raise ValueError('overlay is not covered by existing CPU environment inventory')
    sources = []
    for name in sorted(git('ls-files', '-z').split('\0')):
        path = root / name
        if name and 'prompts' not in Path(name).parts and path.is_file() and path.suffix in ['.py', '.json', '.txt', '.in', '.md', '.yaml', '.yml', '.toml']:
            sources.append(record(path))
    if git('rev-parse', 'HEAD').strip() != head or git('status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('checkout changed while preparing bindings')
    packet.mkdir(parents=True, exist_ok=False)
    write(packet / 'source-bindings.json', sources)
    write(packet / 'environment-bindings.json', environment)
    request_path = packet / 'request.json'
    command = ['python3', '-B', launcher['path'], '--checkout', str(root), '--overlay', str(overlay), '--output', str(output), '--max-seconds', '1200', '--review-request', str(request_path)]
    request = dict(schema='plan069-final-full-cpu-review/v1', record_kind='proposal', status='REVIEW', issue=44, base_head=head, checkout=str(root), overlay=str(overlay), output=str(output), max_seconds=1200, candidate=args.candidate, cpu_admission=admission, launcher=launcher, builder=record(__file__), interpreter=interpreter, source_bindings=record(packet / 'source-bindings.json'), environment_bindings=record(packet / 'environment-bindings.json'), command=command, no_install=True, no_download=True, no_gpu=True, no_ledger_mutation_by_launcher=True, scope='Full CPU unittest discovery and the existing three pytest function-test modules; not native runtime/model qualification')
    write(request_path, request)
    write(packet / 'preparation.json', dict(schema='plan069-final-full-cpu-preparation/v1', record_kind='actual', elapsed_seconds=time.monotonic() - start, request=record(request_path), tests_run=False, ledger_mutated=False))
    print(json.dumps(dict(request=str(request_path), command=command)))


if __name__ == '__main__':
    main()
