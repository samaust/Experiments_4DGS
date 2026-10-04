"""Prepare D6 static source014 only after an exact approved canonical freeze."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import time

CANONICAL = Path('/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension')
PRIVATE = Path(__file__).resolve().parents[5] / '.local/source-next'
BASE = 'docs/research/vipe-alternatives/plan031-execution'
SUPPLEMENTAL = (
    BASE + '/moge-driver-method-006/producer.py',
    BASE + '/moge-driver-method-006/network_guard.py',
    BASE + '/moge-driver-method-006/startup.py',
    BASE + '/moge-driver-method-006/test_guard.py',
    'scripts/basketball_vipe_depth_driver_qualification_local_bind.py',
    'docs/specs/plan031-execution/D6-driver-qualification-review-003.json',
    'docs/specs/plan031-execution/moge-runtime-recipes-001/D6-runtime-environment.json',
    'docs/specs/plan031-execution/depth-runtime-profiles-v1.json',
)


def record(path):
    path = Path(path).absolute()
    if 'prompts' in path.parts or 'prompts' in path.resolve().parts:
        raise ValueError('prompts prohibited')
    data = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def verified(value):
    if record(value['path']) != value:
        raise ValueError('physical record changed: ' + value['path'])
    return value


def head():
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CANONICAL, text=True).strip()


def prepare(expected_head, output):
    start = time.perf_counter()
    if not re.fullmatch('[0-9a-f]{40}', expected_head) or head() != expected_head:
        raise ValueError('exact root-approved canonical freeze required')
    output = Path(output).resolve()
    if not output.is_relative_to(PRIVATE) or output == PRIVATE or output.exists():
        raise ValueError('fresh private preparation output required')
    sys.path.insert(0, str(CANONICAL / 'scripts'))
    from vipe_benchmark.config import ROOT
    from vipe_benchmark.depth_admission import local_source_records
    if ROOT != CANONICAL:
        raise ValueError('imports must bind canonical source helpers')
    prior_record = record(CANONICAL / BASE / 'depth-D6-source-review-013.json')
    prior = json.loads(Path(prior_record['path']).read_text())
    draft = dict(prior)
    review = record(CANONICAL / 'docs/specs/plan031-execution/D6-driver-qualification-review-003.json')
    reviewed = json.loads(Path(review['path']).read_text())
    if reviewed.get('schema') != 'plan069-D6-driver-qualification-review/v3' or reviewed.get('status') != 'REVIEW':
        raise ValueError('concrete REVIEW003 required; no DO is granted')
    proposal = reviewed['proposal']
    keys = ('authority', 'network_guard', 'guard_startup', 'worker', 'dispatcher', 'strace', 'setup',
            'predecessor_finish', 'diagnostic_finish', 'diagnostic_result', 'diagnostic_trace',
            'second_predecessor_finish', 'second_predecessor_trace')
    bindings = {key: verified(proposal[key]) for key in keys}
    local = local_source_records('D6')
    setup = [record(value['path']) for value in prior['setup_sources']]
    supplemental = [record(CANONICAL / name) for name in SUPPLEMENTAL]
    supplemental.append(verified(proposal['strace']))  # hash-only, never executed
    changed = subprocess.check_output(['git', 'diff', '--name-only', '--diff-filter=ACMRT',
        prior['root_source_commit'], expected_head, '--', '*.py'], cwd=CANONICAL, text=True).splitlines()
    changed_records = [record(CANONICAL / name) for name in changed]
    protected = [str(Path(value['path']).relative_to(CANONICAL))
                 for value in (*local, *setup, *supplemental, *changed_records)
                 if Path(value['path']).is_relative_to(CANONICAL)]
    subprocess.run(['git', 'diff', '--exit-code', expected_head, '--', *protected],
                   cwd=CANONICAL, check=True, stdout=subprocess.DEVNULL)
    draft.pop('qualification002_review', None)
    draft.pop('qualification002_method_bindings', None)
    draft.update(status='review', reviewer='', independent_reviews={}, independent_review_report=None,
        root_source_commit=expected_head, local_sources=local, setup_sources=setup,
        supplemental_cpu_sources=supplemental, changed_tracked_python_base=prior['root_source_commit'],
        changed_tracked_python_sources=changed_records, qualification003_review=review,
        qualification003_method_bindings=bindings, previous_source_review=prior_record,
        implementation_review_baseline='b1b43c58',
        qualification_scope='Static current-source review only; qualification003 REVIEW is not DO; no driver/native evidence.')
    verified(draft['source_archive'])
    for value in draft['source_files']:
        verified(value['record'])
    for value in (*local, *setup, *supplemental, *changed_records, *bindings.values(),
                  review, prior_record, draft['review'], draft['authorization'],
                  draft['profile_inventory'], draft['runtime_recipe']):
        verified(value)
    original_authorization = json.loads(Path(verified(draft['authorization'])['path']).read_text())
    original_review = json.loads(Path(verified(draft['review'])['path']).read_text())
    original_proposal = next(row for row in original_review['proposals'] if row['candidate'] == 'D6')
    setup_request_record = record(Path(bindings['setup']['path']).with_name('request.json'))
    setup_request = json.loads(Path(setup_request_record['path']).read_text())
    if (setup_request.get('schema') != 'plan069-depth-setup-request/v1' or
            setup_request.get('candidate') != 'D6' or setup_request.get('record_kind') != 'actual' or
            setup_request.get('runtime_environment_record') != draft['runtime_recipe']):
        raise ValueError('accepted D6 setup recipe differs')
    draft['accepted_setup_request'] = setup_request_record
    verified(setup_request_record)
    if (original_authorization.get('review') != draft['review'] or
            original_proposal['profile_inventory'] != draft['profile_inventory'] or
            original_proposal['candidate_config']['code']['revision'] != draft['source_revision']):
        raise ValueError('original approved D6 source/profile lineage differs')
    if head() != expected_head or local_source_records('D6') != local:
        raise ValueError('canonical source changed during preparation')
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'depth-D6-source-review-input-014.json').open('x') as stream:
        json.dump(draft, stream, indent=2)
        stream.write('\n')
    timing = dict(elapsed_seconds=time.perf_counter()-start, canonical_head=expected_head,
                  local_helper_count=len(local), native_files=len(draft['source_files']),
                  supplemental_count=len(supplemental), gpu_used=False, ledger_modified=False)
    with (output / 'timing.json').open('x') as stream:
        json.dump(timing, stream, indent=2)
        stream.write('\n')
    return timing


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--expected-head', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    print(json.dumps(prepare(args.expected_head, args.output)))
