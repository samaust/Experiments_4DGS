"""Prepare immutable video source review inputs only after root's final freeze."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

PREPARATION = Path(__file__).resolve().parents[5] / ".local/source-next"
CANONICAL = Path('/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension')
SUPPLEMENTAL = (
    'scripts/vipe_benchmark/depth_driver_qualification.py',
    'scripts/basketball_vipe_depth_driver_qualification.py',
    'scripts/vipe_benchmark/depth_driver_diagnostic.py',
    'scripts/basketball_vipe_depth_driver_diagnostic.py',
    'scripts/basketball_vipe_depth_driver_diagnostic_worker.py',
    'docs/research/vipe-alternatives/plan031-execution/video-cpu-method-003/producer.py',
    'docs/research/vipe-alternatives/plan069-D9-recovery-dispatch-002/prepare_recovery.py',
    'docs/research/vipe-alternatives/plan031-execution/video-native-wrapper-001/wrapper.py',
    'docs/research/vipe-alternatives/plan031-execution/video-native-wrapper-001/prepare_admission.py',
    'docs/research/vipe-alternatives/plan031-execution/video-native-wrapper-001/prepare_request.py',
    'docs/research/vipe-alternatives/plan031-execution/video-native-wrapper-002/wrapper.py',
    'docs/research/vipe-alternatives/plan031-execution/video-native-wrapper-002/prepare_admission.py',
    'docs/research/vipe-alternatives/plan031-execution/video-native-wrapper-002/prepare_request.py',
    'docs/research/vipe-alternatives/plan031-execution/video-post-recovery-controls-001/commercial.py',
    'docs/research/vipe-alternatives/plan031-execution/video-post-recovery-controls-001/prepare_D10.py',
)


def parser():
    result = argparse.ArgumentParser()
    result.add_argument('--expected-head', required=True)
    result.add_argument('--output', required=True)
    result.add_argument('--D9-review', required=True)
    result.add_argument('--accepted-D9-setup', required=True)
    result.add_argument('--supplemental', action='append', default=[])
    return result


def prepare(expected_head, output, D9_review, accepted_D9_setup, extra_supplemental=()):
    """No receipts, canonical writes, installs, models or ledger operations."""
    if not re.fullmatch(r'[0-9a-f]{40}', expected_head):
        raise ValueError('exact root-approved final commit required')
    output = Path(output).resolve()
    if output == PREPARATION or not output.is_relative_to(PREPARATION):
        raise ValueError('output must be a fresh private preparation directory')
    if output.exists():
        raise FileExistsError(output)
    review_relative = Path(D9_review)
    if (review_relative.is_absolute() or '..' in review_relative.parts or
            'prompts' in review_relative.parts or review_relative.suffix != '.json' or
            not review_relative.is_relative_to('docs/research/vipe-alternatives')):
        raise ValueError('D9 REVIEW must be a canonical research JSON metadata path')
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
    supplemental_names = tuple(dict.fromkeys((*SUPPLEMENTAL, *extra_supplemental)))
    if any(Path(name).is_absolute() or '..' in Path(name).parts or 'prompts' in Path(name).parts
           or Path(name).suffix != '.py' or Path(name).parts[0] not in ('docs', 'scripts')
           for name in supplemental_names):
        raise ValueError('supplemental must be safe canonical-relative paths')
    supplemental = [file_record(CANONICAL / name) for name in supplemental_names]
    D6_review = read_json(CANONICAL / 'docs/specs/plan031-execution/D6-driver-qualification-review-003.json')
    tracer = verify_record(D6_review['proposal']['strace'])
    if tracer['path'] != '/usr/bin/strace':
        raise ValueError('only the exact reviewed external tracer is permitted')
    supplemental.append(tracer)  # hash only; covers D6 proof in combined CPU capture
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
        protected_paths += list(supplemental_names)
        protected_paths += [str(review_path.relative_to(CANONICAL)),
            str(Path(proposal['profile_inventory']['path']).relative_to(CANONICAL)),
            str(Path(proposal['runtime_recipe']['path']).relative_to(CANONICAL))]
        subprocess.run(['git', 'diff', '--exit-code', expected_head, '--', *protected_paths],
                       cwd=CANONICAL, check=True, stdout=subprocess.DEVNULL)
        previous = file_record(CANONICAL / ('docs/research/vipe-alternatives/plan031-execution/' +
                                            f'depth-{candidate}-source-review-006.json'))
        documents.append(dict(schema='plan069-depth-source-review-input/v1', candidate=candidate,
            status='awaiting_independent_review', canonical_head=head,
            source_revision=proposal['candidate_config']['code']['revision'],
            profile_inventory=file_record(VIDEO_FRAME_PROFILES), runtime_recipe=verify_record(proposal['runtime_recipe']), local_sources=sources,
            supplemental_sources=supplemental, previous_source_review=previous,
            review=review, authorization=None, authorization_status="absent; REVIEW-only preparation",
            proposal_sha256=object_hash(proposal),
            setup_recovery_proposal_sha256=object_hash(recovery) if recovery else None,
            source_inventory_sha256=object_hash(sources),
            scope='CPU source preparation only; no native/runtime/commercial qualification or admission'))
    original = read_json(CANONICAL / D9_review)['setup_recovery_proposal']['original_setup']
    documents[0].update(source_archive=original['source_archive'], source_files=original['source_files'])
    verify_record(original['source_archive'])
    for record in original['source_files']:
        verify_record(record)
    expected_setup = CANONICAL.parents[2] / '.local/vipe-alternatives/plan031-20260913T032700Z/jobs/plan069-D9-setup-recovery-002/result.json'
    if Path(accepted_D9_setup).absolute() != expected_setup or expected_setup != expected_setup.resolve():
        raise ValueError('exact accepted recovery002 result path required before reading')
    accepted_record = file_record(expected_setup)
    accepted = read_json(verify_record(accepted_record)['path'])
    if (accepted.get('schema') != 'plan069-video-setup-recovery-result/v2' or
            accepted.get('candidate') != 'D9' or accepted.get('status') != 'complete' or
            accepted.get('record_kind') != 'actual' or
            Path(accepted_record['path']).parent.name != 'plan069-D9-setup-recovery-002'):
        raise ValueError('actual accepted D9 recovery002 setup metadata required')
    runtime_record = verify_record(accepted['runtime_environment'])
    runtime = read_json(runtime_record['path'])
    expected_recipe = read_json(CANONICAL / D9_review)['proposals'][0]['runtime_recipe']
    recipe = read_json(verify_record(expected_recipe)['path'])
    if (runtime.get('schema') != 'plan069-depth-environment-result/v1' or
            runtime.get('candidate') != 'D9' or runtime.get('status') != 'complete' or
            runtime.get('record_kind') != 'actual' or
            accepted.get('runtime_recipe') != expected_recipe or runtime.get('runtime_recipe') != expected_recipe or
            accepted.get('runtime_profile') != recipe['runtime_profile'] or
            runtime.get('runtime_profile') != recipe['runtime_profile']):
        raise ValueError('accepted D9 runtime/selected recipe lineage differs')
    inventory_record = verify_record(accepted['inventory'])
    runtime_inventory = read_json(inventory_record['path'])
    if (runtime.get('inventory') != inventory_record or
            len(runtime_inventory.get('packages', [])) != 48 or
            runtime_inventory.get('gpu_operations') != 0 or runtime_inventory.get('model_imports') != 0 or
            runtime_inventory.get('inventory_only') is not True or
            len(documents[0]['source_files']) != 37):
        raise ValueError('accepted inventory/native source invariants differ')
    # Metadata only: never import prepared dependencies or open model payloads.
    if accepted['source_archive'] != documents[0]['source_archive'] or accepted['source_files'] != documents[0]['source_files']:
        raise ValueError('accepted recovery changed original native source lineage')
    documents[0]['accepted_setup_metadata'] = dict(setup=accepted_record,
        runtime=runtime_record, inventory=inventory_record)
    documents[0]['accepted_runtime_status'] = 'Metadata bound; native qualification remains pending'
    final_head = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=CANONICAL, text=True).strip()
    if final_head != expected_head:
        raise ValueError('HEAD changed during source freeze')
    for document in documents:
        if document['local_sources'] != local_source_records(document['candidate']):
            raise ValueError('executable source changed during freeze')
        verify_record(document['review'])
        verify_record(document['profile_inventory'])
        verify_record(document['runtime_recipe'])
        for record in document['supplemental_sources']:
            verify_record(record)
    verify_record(documents[0]['source_archive'])
    for native_record in documents[0]['source_files']:
        verify_record(native_record)
    for metadata_record in documents[0]['accepted_setup_metadata'].values():
        verify_record(metadata_record)
    output.mkdir(parents=True, exist_ok=False)
    for document in documents:
        write_json(output / f"depth-{document['candidate']}-source-review-input-007.json", document)
    write_json(output / 'timing.json', dict(cpu_elapsed_seconds=time.perf_counter()-start,
        canonical_head=head, source_counts={row['candidate']:len(row['local_sources']) for row in documents},
        supplementary_records=len(supplemental), gpu_used=False, ledger_modified=False))
    return dict(output=str(output), candidates=['D9','D10'], canonical_head=head)


if __name__ == '__main__':
    args = parser().parse_args()
    print(json.dumps(prepare(args.expected_head, args.output, args.D9_review, args.accepted_D9_setup, args.supplemental)))
