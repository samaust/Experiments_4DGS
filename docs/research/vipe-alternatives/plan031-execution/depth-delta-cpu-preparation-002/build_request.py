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
    parser.add_argument('--candidate', required=True, choices=['D6', 'D9'])
    parser.add_argument('--cpu-admission', required=True)
    parser.add_argument('--source-review', required=True)
    parser.add_argument('--selector', action='append', default=[])
    parser.add_argument('--cpu-accounting-owner', required=True, choices=['D6'])
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
    admission_doc = json.loads(Path(admission['path']).read_text())
    if admission_doc.get('cpu_accounting_owner') != args.cpu_accounting_owner or admission_doc.get('seconds') != 60:
        raise ValueError('fresh owner-matched 60-second CPU admission required')
    source_review = record(args.source_review)
    review = json.loads(Path(source_review['path']).read_text())
    helper_files = review.get('local_sources', review.get('local_source_records'))
    if review.get('candidate') != args.candidate or review.get('status') != 'passed' or not isinstance(helper_files, list) or not helper_files:
        raise ValueError('passed declared helper review for requested candidate required')
    if len({row['path'] for row in helper_files}) != len(helper_files):
        raise ValueError('duplicate declared helper record')
    if 'local_sources' in review and 'local_source_records' in review and review['local_sources'] != review['local_source_records']:
        raise ValueError('ambiguous declared helper list')
    supplemental_key = 'supplemental_sources' if 'supplemental_sources' in review else 'supplemental_cpu_sources'
    if 'supplemental_sources' in review and 'supplemental_cpu_sources' in review and review['supplemental_sources'] != review['supplemental_cpu_sources']:
        raise ValueError('ambiguous supplemental source list')
    supplemental_sources = review.get(supplemental_key, [])
    if not isinstance(supplemental_sources, list) or len({row['path'] for row in supplemental_sources}) != len(supplemental_sources):
        raise ValueError('invalid supplemental CPU source list')
    for row in helper_files + supplemental_sources + review.get('changed_tracked_python_sources', []):
        if record(row['path']) != row:
            raise ValueError('changed reviewed source record')
    # Baseline: passing full suites 025/026/027 and delta016; changes are measured from full027's head.
    prior_full = record(root / '.local/plan069-combined-cpu-qualification-027/receipt.json')
    prior_delta = record(root / '.local/plan069-combined-cpu-qualification-016/receipt.json')
    prior_recent = record(root / '.local/plan069-combined-cpu-qualification-026/receipt.json')
    prior_latest = record(root / '.local/plan069-combined-cpu-qualification-025/receipt.json')
    prior_current = record(root / '.local/plan069-combined-cpu-qualification-027/receipt.json')
    for prior in (prior_full, prior_delta, prior_recent, prior_latest, prior_current):
        if json.loads(Path(prior['path']).read_text()).get('passed') is not True:
            raise ValueError('prior qualification must have passed')
    prior_head = json.loads(Path(prior_current['path']).read_text())['head']
    changed = git('diff', '--name-only', '-z', prior_head, head).split('\0')
    changed_public_producers = []
    changed_tests = []
    for name in changed:
        path = root / name
        if not name or 'prompts' in Path(name).parts or not path.is_file() or path.suffix != '.py':
            continue
        row = record(path)
        if name.startswith('tests/test_'):
            changed_tests.append(path.stem)
        elif name.startswith(('scripts/', 'docs/')):
            changed_public_producers.append(row)
    by_path = {row['path']: row for row in helper_files}
    for row in changed_public_producers:
        by_path[row['path']] = row
    helper_files = sorted(by_path.values(), key=lambda row: row['path'])
    default_selectors = ['test_vipe_benchmark_video_commercial_producer']
    selectors = list(dict.fromkeys(default_selectors + changed_tests + args.selector))
    for name in selectors:
        module = name.split('.')[0]
        if not module.startswith('test_') or not (root / 'tests' / (module + '.py')).is_file():
            raise ValueError('unknown public test selector: ' + name)
    # Preserve the existing CPU metadata/pycolmap inventory scope. Rehashing an
    # existing inventory fails if its contents changed; it never silently accepts
    # replacement dependencies or grants native model qualification.
    template = root / 'docs/research/vipe-alternatives/plan031-execution/depth-combined-cpu-retry-review-001/environment-bindings.json'
    record(template)
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
    source_by_path = {row['path']: row for row in sources}
    for row in supplemental_sources:
        if row['path'] in source_by_path and source_by_path[row['path']] != row:
            raise ValueError('supplemental source conflicts with tracked source')
        source_by_path[row['path']] = row
    sources = sorted(source_by_path.values(), key=lambda row: row['path'])
    if git('rev-parse', 'HEAD').strip() != head or git('status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('checkout changed while preparing bindings')
    packet.mkdir(parents=True, exist_ok=False)
    write(packet / 'source-bindings.json', sources)
    write(packet / 'environment-bindings.json', environment)
    request_path = packet / 'request.json'
    command = ['python3', '-B', launcher['path'], '--checkout', str(root), '--overlay', str(overlay), '--output', str(output), '--max-seconds', '60', '--review-request', str(request_path)]
    request = dict(schema='plan069-delta-cpu-review/v1', record_kind='proposal', status='REVIEW', issue=44, base_head=head, checkout=str(root), overlay=str(overlay), output=str(output), max_seconds=60, candidate=args.candidate, source_component=args.candidate, cpu_accounting_owner=args.cpu_accounting_owner, cpu_admission=admission, prior_full_capture=prior_full, prior_delta_capture=prior_delta, prior_recent_capture=prior_recent, prior_latest_capture=prior_latest, prior_current_capture=prior_current, changed_since_prior_capture_head=prior_head, changed_public_producers=changed_public_producers, source_review=source_review, reviewed_helper_files=helper_files, supplemental_cpu_sources=supplemental_sources, supplemental_source_key=supplemental_key, supplemental_binding_scope='Read/hash only; external binary metadata binding does not imply execution or runtime qualification', selectors=selectors, private_test_files=[], launcher=launcher, builder=record(__file__), interpreter=interpreter, source_bindings=record(packet / 'source-bindings.json'), environment_bindings=record(packet / 'environment-bindings.json'), command=command, no_install=True, no_download=True, no_gpu=True, no_ledger_mutation_by_launcher=True, scope='Only explicitly selected changed public API tests after passing full027 (and full025/026, delta016); no repeated composer suite and no native runtime/model qualification')
    write(request_path, request)
    write(packet / 'preparation.json', dict(schema='plan069-final-full-cpu-preparation/v1', record_kind='actual', cpu_accounting_owner='D9', source_component=args.candidate, elapsed_seconds=time.monotonic() - start, request=record(request_path), tests_run=False, ledger_mutated=False))
    print(json.dumps(dict(request=str(request_path), command=command)))


if __name__ == '__main__':
    main()
