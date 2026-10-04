"""Prepare immutable video source review inputs only after root's final freeze."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

PREPARATION = Path(__file__).resolve().parent
CANONICAL = Path('/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension')
SUPPLEMENTAL = (
    'scripts/vipe_benchmark/depth_driver_qualification.py',
    'scripts/basketball_vipe_depth_driver_qualification.py',
    'scripts/vipe_benchmark/depth_driver_diagnostic.py',
    'scripts/basketball_vipe_depth_driver_diagnostic.py',
    'scripts/basketball_vipe_depth_driver_diagnostic_worker.py',
    'docs/research/vipe-alternatives/plan031-execution/video-cpu-method-003/producer.py',
    'docs/research/vipe-alternatives/plan069-D9-recovery-dispatch-002/prepare_recovery.py',
)


def parser():
    result = argparse.ArgumentParser()
    result.add_argument('--expected-head', required=True)
    result.add_argument('--output', required=True)
    result.add_argument('--D9-review', required=True)
    return result


def prepare(expected_head, output, D9_review):
    """No receipts, canonical writes, installs, models or ledger operations."""
    if not re.fullmatch(r'[0-9a-f]{40}', expected_head):
        raise ValueError('exact root-approved final commit required')
    output = Path(output).resolve()
    if output == PREPARATION or not output.is_relative_to(PREPARATION):
        raise ValueError('output must be a fresh private preparation directory')
    if output.exists():
        raise FileExistsError(output)
    start = time.perf_counter()
    head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CANONICAL, text=True).strip()
    if head != expected_head:
        raise ValueError('canonical HEAD differs from root-approved freeze')
    helper = CANONICAL / 'scripts/vipe_benchmark/depth_budget_reconciliation.py'
    if not helper.is_file():
        raise ValueError('causal reconciliation helper not integrated')
    sys.path.insert(0, str(CANONICAL / 'scripts'))
    from vipe_benchmark.config import ROOT
    from vipe_benchmark.depth_admission import local_source_records, VIDEO_FRAME_PROFILES, selected_profile_inventory
    from vipe_benchmark.files import file_record, object_hash, read_json, verify_record, write_json
    if ROOT != CANONICAL:
        raise ValueError('imports did not bind canonical checkout')
    supplemental = [file_record(CANONICAL / name) for name in SUPPLEMENTAL]
    documents = []
    for candidate in ('D9', 'D10'):
        review_path = CANONICAL / (
            D9_review
            if candidate == 'D9' else
            'docs/research/vipe-alternatives/plan031-execution/video-D10-frame-amendment-review-001/REVIEW.json')
        review = file_record(review_path)
        reviewed = read_json(review_path)
        proposals = reviewed.get('proposals', [])
        if (reviewed.get('schema') != 'plan069-depth-execution-review/v1' or
                reviewed.get('status') != 'REVIEW' or len(proposals) != 1 or
                proposals[0].get('candidate') != candidate):
            raise ValueError('exact one-row fresh frame-input REVIEW required')
        proposal = proposals[0]
        if selected_profile_inventory(proposal) != VIDEO_FRAME_PROFILES:
            raise ValueError('explicit v4 frame recipe and profile required')
        prior = read_json(CANONICAL / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-003.json')
        prior_review = read_json(verify_record(prior['review'])['path'])
        original = next(row for row in prior_review['proposals'] if row['candidate'] == candidate)
        import copy
        restored = copy.deepcopy(proposal)
        for key in ('profile', 'profile_inventory', 'runtime_recipe'):
            restored[key] = original[key]
        if restored != original:
            raise ValueError('fresh frame proposal changes scientific settings or approved bounds')
        recovery = reviewed.get('setup_recovery_proposal')
        if candidate == 'D9' and (not isinstance(recovery, dict) or
                recovery.get('map_proposal_sha256') != object_hash(proposal) or
                recovery.get('runtime_recipe') != proposal['runtime_recipe'] or
                recovery.get('profile_inventory') != proposal['profile_inventory']):
            raise ValueError('exact separately reviewed D9 recovery proposal required')
        if candidate=='D9' and (recovery.get('schema')!='plan069-video-setup-recovery-proposal/v2' or
                recovery.get('job_id')!='plan069-D9-setup-recovery-002' or
                len(recovery.get('failed_recoveries',[]))!=1 or
                recovery['failed_recoveries'][0].get('job_id')!='plan069-D9-setup-recovery-001'):
            raise ValueError('exact recovery002 proposal and consumed recovery001 ancestry required')
        sources = local_source_records(candidate)
        paths = [row['path'] for row in sources]
        if str(helper) not in paths or str(CANONICAL / 'scripts/vipe_benchmark/video_setup_budget.py') not in paths:
            raise ValueError('final source closure lacks a required budget helper')
        if proposal['profile_inventory'] != file_record(VIDEO_FRAME_PROFILES):
            raise ValueError('exact frame-input v4 profile required')
        protected_paths = [str(Path(path).relative_to(CANONICAL)) for path in paths]
        protected_paths += list(SUPPLEMENTAL)
        subprocess.run(['git', 'diff', '--exit-code', expected_head, '--', *protected_paths],
                       cwd=CANONICAL, check=True, stdout=subprocess.DEVNULL)
        previous = file_record(CANONICAL / ('docs/research/vipe-alternatives/plan031-execution/' +
                                            f'depth-{candidate}-source-review-005.json'))
        documents.append(dict(schema='plan069-depth-source-review-input/v1', candidate=candidate,
            status='awaiting_independent_review', canonical_head=head,
            source_revision=proposal['candidate_config']['code']['revision'],
            profile_inventory=file_record(VIDEO_FRAME_PROFILES), local_sources=sources,
            supplemental_sources=supplemental, previous_source_review=previous,
            review=review, authorization=None, authorization_status="absent; REVIEW-only preparation",
            proposal_sha256=object_hash(proposal),
            setup_recovery_proposal_sha256=object_hash(recovery) if recovery else None,
            source_inventory_sha256=object_hash(sources),
            scope='CPU source preparation only; no native/runtime/commercial qualification or admission'))
    original = read_json(CANONICAL / D9_review)['setup_recovery_proposal']['original_setup']
    documents[0].update(source_archive=original['source_archive'], source_files=original['source_files'])
    for record in original['source_files']:
        verify_record(record)
    final_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CANONICAL, text=True).strip()
    if final_head != expected_head:
        raise ValueError('HEAD changed during source freeze')
    for document in documents:
        if document['local_sources'] != local_source_records(document['candidate']):
            raise ValueError('executable source changed during freeze')
        for record in document['supplemental_sources']:
            verify_record(record)
    output.mkdir(parents=True, exist_ok=False)
    for document in documents:
        write_json(output / f"depth-{document['candidate']}-source-review-input-006.json", document)
    write_json(output / 'timing.json', dict(cpu_elapsed_seconds=time.perf_counter()-start,
        canonical_head=head, source_counts={row['candidate']:len(row['local_sources']) for row in documents},
        supplementary_records=len(supplemental), gpu_used=False, ledger_modified=False))
    return dict(output=str(output), candidates=['D9','D10'], canonical_head=head)


if __name__ == '__main__':
    args = parser().parse_args()
    print(json.dumps(prepare(args.expected_head, args.output, args.D9_review)))
