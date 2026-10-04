"""D10-only optional decoder amendment; preserve prior attempts and budgets."""
import copy
import json
from pathlib import Path

from .files import file_record, object_hash, read_json, verify_record


def unstarted_prefix(record):
    """Validate immutable full ledger prefix and reject any prior D10 grant/job."""
    path = verify_record(record)['path']
    events: list[dict] = []
    previous = None
    for line in Path(path).read_text().splitlines():
        row = json.loads(line)
        stored = row.pop('event_sha256')
        if (row.get('sequence') != len(events) or row.get('previous_sha256') != previous or
                object_hash(row) != stored):
            raise ValueError('D10 unstarted ledger prefix corrupt')
        if ((row.get('candidate') == 'D10' and
                (row.get('event') in ('depth_setup_authorized', 'depth_attempt_authorized',
                                     'video_depth_setup_recovery_authorized') or
                 row.get('resource') in ('setup', 'gpu'))) or
                str(row.get('job_id', '')).startswith(('plan069-D10-setup-', 'plan069-D10-maps-'))):
            raise ValueError('D10 setup or native attempt already started')
        row['event_sha256'] = stored
        events.append(row)
        previous = stored
    if not events:
        raise ValueError('nonempty protected D10 ledger prefix required')
    return events


def validate_frame_amendment(candidate, approved, reviewed, *, root):
    """Validate fresh explicit approval of an otherwise unchanged D10 proposal."""
    from .depth_admission import VIDEO_FRAME_PROFILES, selected_profile_inventory, local_source_records
    from .video_environment import FRAME_RECIPE
    if candidate != 'D10':
        raise ValueError('unstarted frame amendment is D10-only')
    prior_record = verify_record(approved['previous_authorization'])
    local_prior = file_record(root / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-003.json')
    if any(prior_record[key] != local_prior[key] for key in ('sha256', 'bytes')):
        raise ValueError('frame amendment requires immutable DO003 predecessor')
    prior = read_json(prior_record['path'])
    if prior.get('status') != 'DO' or prior.get('schema') != 'plan069-depth-user-authorization/v1':
        raise ValueError('approved DO003 predecessor required')
    baseline = read_json(verify_record(prior['review'])['path'])
    original = [row for row in baseline.get('proposals', []) if row.get('candidate') == 'D10']
    proposals = reviewed.get('proposals', [])
    if len(original) != 1 or len(proposals) != 1 or proposals[0].get('candidate') != 'D10':
        raise ValueError('exact single D10 frame proposal required')
    proposal = proposals[0]
    if selected_profile_inventory(proposal) != VIDEO_FRAME_PROFILES:
        raise ValueError('exact D10 frame recipe and profile required')
    restored = copy.deepcopy(proposal)
    for key in ('profile', 'profile_inventory', 'runtime_recipe'):
        restored[key] = original[0][key]
    if restored != original[0]:
        raise ValueError('D10 frame amendment changes science, caps or attempt scope')
    prefix = reviewed.get('unstarted_ledger_prefix')
    unstarted_prefix(prefix)
    expected = dict(schema='plan069-video-frame-amendment-approval/v1', status='approved',
        candidate='D10', optional_decoder_omission_approved=True,
        runtime_recipe=file_record(FRAME_RECIPE), profile_inventory=file_record(VIDEO_FRAME_PROFILES),
        unstarted_ledger_prefix=prefix)
    amendment = approved.get('video_frame_amendment')
    if not isinstance(amendment, dict):
        raise ValueError('explicit optional Decord omission approval required')
    qualification_record = amendment.get('D9_runtime_qualification')
    if dict(amendment, D9_runtime_qualification=None) != dict(expected, D9_runtime_qualification=None):
        raise ValueError('exact D10 frame amendment approval required')
    validate_D9_prerequisite(qualification_record)
    if (reviewed.get('asset_inventory') != baseline.get('asset_inventory') or
            approved.get('reset_previous_consumption') is not False or
            any(approved.get(key) != prior.get(key) for key in ('cap_amendment', 'cap_approval', 'video_amendment')) or
            approved.get('candidate_approvals') is None or
            [grant.get('candidate') for grant in approved['candidate_approvals']] != ['D10']):
        raise ValueError('D10 frame amendment differs from approved budget or lineage')


def validate_D9_prerequisite(record):
    """Validate retained actual native CPU qualification and its receipt chain."""
    from .depth_admission import VIDEO_FRAME_PROFILES, local_source_records
    from .depth_extension import CONFIG
    from .video_environment import FRAME_RECIPE, validate_runtime_versions, validate_runtime_observation
    qualified = read_json(verify_record(record)['path'])
    profile = read_json(VIDEO_FRAME_PROFILES)['profiles']['D9']
    candidate_config = read_json(CONFIG)['candidates']['D9']
    revision = candidate_config['code']['revision']
    if (qualified.get('schema') != 'plan069-depth-runtime-qualification/v1' or
            qualified.get('record_kind') != 'actual' or qualified.get('candidate') != 'D9' or
            qualified.get('status') != 'passed' or qualified.get('source_revision') != revision or
            qualified.get('profile') != profile or qualified.get('local_sources') != local_source_records('D9')):
        raise ValueError('current passed actual D9 frame runtime qualification required before D10')
    verify_record(qualified['python'])
    dependencies = read_json(verify_record(qualified['dependency_manifest'])['path'])
    environment = dict(recipe=file_record(FRAME_RECIPE), runtime_profile=profile['runtime_profile'])
    if (dependencies.get('schema') != 'plan069-depth-installed-dependencies/v1' or
            dependencies.get('candidate') != 'D9' or dependencies.get('source_revision') != revision or
            dependencies.get('runtime_recipe') != environment['recipe'] or not dependencies.get('files')):
        raise ValueError('actual D9 frame installed dependency closure required')
    validate_runtime_versions(environment, dependencies.get('versions', {}))
    validate_runtime_observation(environment, dependencies.get('runtime_observation'))
    setup = read_json(verify_record(qualified['setup'])['path'])
    runtime = read_json(verify_record(setup['runtime_environment'])['path'])
    native = read_json(verify_record(qualified['native_cpu'])['path'])
    capture = read_json(verify_record(qualified['capture'])['path'])
    source = read_json(verify_record(qualified['source_review'])['path'])
    if (setup.get('schema') != 'plan069-video-setup-result/v1' or
            setup.get('record_kind') != 'actual' or setup.get('status') != 'complete' or
            setup.get('candidate') != 'D9' or setup.get('source_revision') != revision or
            setup.get('weight_revision') != candidate_config['weights']['revision'] or
            setup.get('runtime_recipe') != environment['recipe'] or
            setup.get('runtime_profile') != profile['runtime_profile'] or
            not setup.get('source_archive') or not setup.get('source_files') or
            dependencies.get('setup') != qualified['setup'] or
            dependencies.get('runtime_environment') != setup['runtime_environment'] or
            runtime.get('schema') != 'plan069-depth-environment-result/v1' or
            runtime.get('record_kind') != 'actual' or runtime.get('status') != 'complete' or
            runtime.get('candidate') != 'D9' or environment['recipe'] not in runtime.get('requirement_sources', []) or
            runtime.get('python') != qualified.get('python') or
            runtime.get('python_executable') != qualified.get('python_executable') or
            native.get('runtime_environment') != setup['runtime_environment'] or
            source.get('schema') != 'plan069-depth-source-review/v1' or source.get('status') != 'passed' or
            source.get('candidate') != 'D9' or not source.get('reviewer') or
            source.get('source_revision') != revision or source.get('profile_inventory') != file_record(VIDEO_FRAME_PROFILES) or
            source.get('local_sources') != qualified['local_sources'] or
            native.get('schema') != 'plan069-video-native-cpu-qualification/v1' or
            native.get('record_kind') != 'actual' or native.get('candidate') != 'D9' or
            native.get('status') != 'passed' or native.get('strict_cpu_loads') != 2 or
            native.get('inference') is not False or native.get('cuda_initialized') is not False or
            native.get('dependency_manifest') != qualified['dependency_manifest'] or
            capture.get('schema') != 'plan069-video-cpu-capture/v1' or capture.get('candidate') != 'D9' or
            capture.get('status') != 'passed' or capture.get('cleanup_confirmed') is not True or
            capture.get('native_cpu') != qualified['native_cpu'] or
            any(native.get(key) != qualified.get(key) for key in
                ('setup', 'source_revision', 'profile', 'local_sources', 'python', 'python_executable')) or
            any(document.get(key) != setup.get(key) for document in (qualified, native, source)
                for key in ('source_archive', 'source_files'))):
        raise ValueError('actual D9 native capture, setup and source qualification chain required')
