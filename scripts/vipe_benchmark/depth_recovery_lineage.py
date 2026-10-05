"""Accepted recovery ancestry and paid model allowance, without execution.

A consumed failed setup never qualifies itself. Only its independently approved,
cleanly finished recovery can expose the unchanged retained model to maps.
"""
from pathlib import Path

from .files import file_record, object_hash, read_json, verify_record
from .setup_recovery_core import (RECOVERY_CANDIDATES, completed_recovery, failed_setup_ancestry,
                                  owned_active_attempt)

# D9 video-setup recovery profile; shared ancestry checks live in setup_recovery_core.
CANDIDATE = 'D9'
JOBS = RECOVERY_CANDIDATES[CANDIDATE]['jobs']
JOB, REPAIR_JOB = JOBS
RESULT_SCHEMAS = RECOVERY_CANDIDATES[CANDIDATE]['result_schemas']
ORIGINAL_JOB = RECOVERY_CANDIDATES[CANDIDATE]['original_job']


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _one(events, event, job=None):
    rows = [row for row in events if row.get('event') == event and
            (job is None or row.get('job_id') == job)]
    _require(len(rows) == 1, 'unique accepted recovery ' + event + ' required')
    return rows[0]


def checked_failed_recoveries(job_id, descriptors, events, run_root, *, verifier=verify_record,
                              before_sequence=None):
    """Recheck only the explicitly approved failed predecessor, without new closure."""
    expected = [JOB] if job_id == REPAIR_JOB else []
    _require(job_id in JOBS and isinstance(descriptors, list) and
             [row.get('job_id') for row in descriptors] == expected,
             'exact approved failed recovery chain required')
    root = Path(run_root).resolve()
    for row in descriptors:
        try:
            ancestry = failed_setup_ancestry(CANDIDATE, row['job_id'], events, row)
        except ValueError as error:
            raise ValueError('protected clean failed recovery ancestry changed') from error
        grant, reserve, finish = ancestry['grant'], ancestry['reserve'], ancestry['finish']
        _require((before_sequence is None or finish['sequence'] < before_sequence) and
                 grant.get('request') == reserve.get('evidence', {}).get('request') == row.get('request'),
                 'protected clean failed recovery ancestry changed')
        for key in ('request', 'failure'):
            _require(verifier(row[key]) == row[key], 'failed recovery evidence changed')
        _require(Path(row['failure']['path']) == root / 'jobs' / JOB / 'failure.json',
                 'owned historical recovery failure required')
        failure = read_json(row['failure']['path'])
        _require(failure.get('schema') == 'plan069-video-setup-recovery-failure/v1' and
                 failure.get('record_kind') == 'actual' and failure.get('status') == 'failed' and
                 failure.get('job_id') == JOB and isinstance(failure.get('error'), str) and
                 bool(failure['error']) and type(failure.get('automatic_retries')) is int and
                 failure['automatic_retries'] == 0 and failure.get('gpu_operations') is False and
                 failure.get('original_setup') == read_json(row['request']['path']).get('original_setup'), 'historical failed recovery receipt changed')
    return descriptors


def accepted_setup_lineage(setup_record, events, run_root, *, verifier=verify_record,
                           active_map_admission=None):
    """Validate exact immutable recovery and its separately checked DO ancestry."""
    root = Path(run_root).resolve()
    job_id = Path(setup_record['path']).parent.name
    _require(job_id in JOBS, 'owned accepted recovery result required')
    job = root / 'jobs' / job_id
    _require(verifier(setup_record) == setup_record and
             Path(setup_record['path']) == job / 'result.json',
             'owned accepted recovery result required')
    result = read_json(setup_record['path'])
    _require(result.get('schema') == RESULT_SCHEMAS[job_id] and
             result.get('record_kind') == 'actual' and result.get('status') == 'complete' and
             result.get('candidate') == CANDIDATE and result.get('job_id') == job_id,
             'actual completed D9 recovery required')
    completion = completed_recovery(CANDIDATE, job_id, setup_record, events)
    grant, reserve, finish = completion['grant'], completion['reserve'], completion['finish']
    owned = owned_active_attempt(CANDIDATE, events, active_map_admission)
    active = [owned] if owned is not None else []
    map_grant = None
    if active:
        _require(verifier(active_map_admission) == active_map_admission,
                 'exact active recovery map admission required')
        admission = read_json(active_map_admission['path'])
        map_grant = _one([row for row in events if row.get('candidate') == CANDIDATE],
                         'depth_attempt_authorized')
        _require(admission.get('schema') == 'plan069-depth-admission-result/v1' and
                 admission.get('status') == 'passed' and admission.get('candidate') == CANDIDATE and
                 admission.get('completed_setup') == setup_record and
                 map_grant.get('candidate') == CANDIDATE and
                 map_grant.get('admission') == active_map_admission and
                 map_grant['sequence'] < active[0]['sequence'],
                 'protected passed recovery map admission required')
    request_record = result['request']
    _require(grant.get('request') == reserve.get('evidence', {}).get('request') == request_record,
             'exact completed recovery request binding required')
    for key in ('review', 'authorization', 'source_review'):
        _require(result.get(key) == grant.get(key) == reserve.get('evidence', {}).get(key),
                 'completed recovery approval binding changed: ' + key)
    from .depth_setup_recovery import validate_recovery_request
    normalized = validate_recovery_request(request_record, events, root,
        require_reservation=False, verifier=verifier, historical=True)
    request = read_json(request_record['path'])
    _require(normalized.get('job_id', JOB) == job_id, 'normalized recovery job changed')
    failed_recoveries = checked_failed_recoveries(job_id, normalized.get('failed_recoveries', []),
        events, root, verifier=verifier, before_sequence=grant['sequence'])
    if job_id == REPAIR_JOB:
        _require(result.get('failed_recoveries') == request.get('failed_recoveries') ==
                 failed_recoveries, 'accepted recovery failed ancestry changed')
    proposal, maps, original = (normalized[key] for key in ('proposal', 'map_proposal', 'original'))
    if map_grant is not None:
        _require(map_grant.get('proposal_sha256') == object_hash(maps) and all(
            map_grant.get(key) == normalized[key] == active[0].get('evidence', {}).get(key)
            for key in ('review', 'authorization')),
            'active recovery map authority binding changed')
        source_record = map_grant.get('source_review')
        _require(isinstance(source_record, dict) and source_record ==
                 active[0].get('evidence', {}).get('source_review') == admission.get('source_review') and
                 verifier(source_record) == source_record and all(
                     key not in admission or admission[key] == normalized[key]
                     for key in ('review', 'authorization')) and
                 ('proposal_sha256' not in admission or admission['proposal_sha256'] == object_hash(maps)),
                 'active recovery map authority source or admission binding changed')
        from .depth_admission import local_source_records
        from .depth_d9_continuation import active_phase_evidence
        continued = active_phase_evidence(events, active[0])
        if continued is not None:
            source_record, admission = continued
            _require(verifier(source_record) == source_record,
                     'current continuation source review record changed')
        source = read_json(source_record['path'])
        _require(source.get('schema') == 'plan069-depth-source-review/v1' and
                 source.get('status') == 'passed' and source.get('candidate') == CANDIDATE and
                 bool(source.get('reviewer')) and
                 source.get('local_sources') == local_source_records(CANDIDATE) and
                 source.get('source_revision') == maps['candidate_config']['code']['revision'] ==
                 result.get('source_revision') and source.get('profile_inventory') == maps.get('profile_inventory') and
                 source.get('source_archive') == original['source_archive'] and
                 source.get('source_files') == original['source_files'] and
                 ('proposal_sha256' not in source or source['proposal_sha256'] == object_hash(maps)),
                 'current independent recovery map source review required')
        runtime_record = admission.get('runtime', {}).get('receipt')
        phase_records = [row for row in (runtime_record, admission.get('qualification'))
                         if isinstance(row, dict)]
        phase_expected = dict(candidate=CANDIDATE, record_kind='actual', status='passed',
            source_review=source_record, setup=setup_record, source_revision=result['source_revision'],
            source_archive=original['source_archive'], source_files=original['source_files'],
            local_sources=source['local_sources'], profile=maps.get('profile'))
        for record in phase_records:
            _require(verifier(record) == record, 'active recovery map native phase changed')
            phase = read_json(record['path'])
            _require(all(key not in phase or phase[key] == value for key, value in phase_expected.items()) and
                     ('runtime' not in phase or phase['runtime'].get('receipt') == runtime_record),
                     'active recovery map native phase binding changed')
    _require(grant.get('request') == request_record == normalized['request'] and
             grant.get('proposal_sha256') == object_hash(proposal) and
             reserve.get('evidence', {}).get('request') == request_record and
             reserve.get('seconds') == normalized['allocation']['setup_seconds'],
             'exact recovery request and bounded reservation required')
    for key in ('review', 'authorization', 'source_review'):
        _require(result.get(key) == request.get(key) == normalized[key] == grant.get(key) and
                 reserve.get('evidence', {}).get(key) == normalized[key],
                 'recovery approval binding changed: ' + key)
    _require(result.get('original_setup') == request.get('original_setup') == original and
             result.get('source_revision') == maps['candidate_config']['code']['revision'] and
             result.get('weight_revision') == maps['candidate_config']['weights']['revision'] and
             result.get('source_archive') == original['source_archive'] and
             result.get('source_files') == original['source_files'] and
             result.get('source_dir') == str(root / 'jobs' / ORIGINAL_JOB / 'source') and
             type(result.get('bytes_received')) is int and result['bytes_received'] == 0 and
             result.get('original_failure_preserved') is True and
             result.get('model_imports') is False and result.get('gpu_operations') is False and
             type(result.get('automatic_retries')) is int and result['automatic_retries'] == 0,
             'recovery changed original sources, model or offline scope')
    for record in [original['source_archive'], *original['source_files']]:
        _require(verifier(record) == record, 'retained original source changed')
    checkpoint = result['checkpoint']
    old = original['checkpoint']
    path, old_path = Path(checkpoint['path']), Path(old['path'])
    _require(path == job / old_path.name and not path.is_symlink() and
             verifier(checkpoint) == checkpoint and verifier(old) == old and
             checkpoint['sha256'] == old['sha256'] and checkpoint['bytes'] == old['bytes'],
             'exact retained checkpoint at native recovery path required')
    current, previous = path.stat(), old_path.stat()
    _require((current.st_dev, current.st_ino) == (previous.st_dev, previous.st_ino),
             'recovery checkpoint must share original retained inode')
    environment = normalized['runtime_environment']
    runtime_record = result['runtime_environment']
    _require(Path(runtime_record['path']) == job / 'runtime/result.json' and
             verifier(runtime_record) == runtime_record, 'owned completed recovery runtime required')
    runtime = read_json(runtime_record['path'])
    _require(runtime.get('schema') == 'plan069-depth-environment-result/v1' and
             runtime.get('record_kind') == 'actual' and runtime.get('status') == 'complete' and
             runtime.get('candidate') == CANDIDATE and
             runtime.get('python_executable') == result.get('python_executable') ==
             str(job / 'runtime/environment/bin/python') and
             result.get('media_tools') == environment['media_tools'] and
             result.get('runtime_recipe') == environment['recipe'] and
             result.get('runtime_profile') == environment['runtime_profile'] and
             result.get('excluded_distributions') == ['decord', 'xformers'] and
             result.get('xformers') == environment.get('xformers'),
             'recovery runtime or media-tool bindings changed')
    _require(runtime.get('runtime_recipe') == environment['recipe'] and
             runtime.get('runtime_profile') == environment['runtime_profile'] and
             runtime.get('python_seed') == environment['python_seed'] and
             runtime.get('requirement_sources') == environment['requirement_sources'] and
             runtime.get('excluded_distributions') == ['decord', 'xformers'] and
             runtime.get('offline') is True and runtime.get('model_imports') is False and
             runtime.get('gpu_operations') is False and
             type(runtime.get('automatic_retries')) is int and runtime['automatic_retries'] == 0,
             'recovery environment differs from reviewed offline recipe')
    for key, expected in (('dependency_lock', job / 'runtime/requirements.lock'),
                          ('inventory', job / 'runtime/inventory.json')):
        record = result[key]
        _require(runtime.get(key) == record and Path(record['path']) == expected and
                 verifier(record) == record, 'exact recovery runtime file required: ' + key)
    _require(runtime.get('python') == result.get('python') and
             verifier(result['python']) == result['python'], 'exact recovery interpreter required')
    executable = Path(result['python_executable'])
    _require(executable.is_file() and executable.resolve() == Path(result['python']['path']),
             'native recovery executable differs from recorded interpreter')
    for record in result['media_tools'].values():
        _require(verifier(record) == record, 'reviewed media tool changed')
    inventory = read_json(result['inventory']['path'])
    _require(inventory.get('inventory_only') is True and inventory.get('model_imports') is False and
             inventory.get('gpu_operations') is False and
             inventory.get('executable') == result['python_executable'],
             'actual CPU-only recovery inventory required')
    _require({row['name'].lower().replace('_', '-') for row in inventory['packages']}.isdisjoint(
        {'decord', 'xformers'}), 'excluded recovery distributions must remain absent')
    return dict(normalized, accepted_result=result, setup=setup_record,
        result_record=setup_record, grant=grant, reserve=reserve, finish=finish, job=job_id, failed_recoveries=failed_recoveries)


def recovery_cap_authorization(proposal, authorization, setup, events, run_root):
    """Return inherited cap authority only for an exact accepted D9 recovery.

    Recovery DO records approve their own setup and unchanged map proposal.
    Resource-cap approval remains in the protected original setup grant.
    """
    root = Path(run_root).resolve()
    if (proposal.get('candidate') != CANDIDATE or setup is None or
            Path(setup['path']) not in [root / 'jobs' / name / 'result.json' for name in JOBS]):
        return None
    accepted = accepted_setup_lineage(setup, events, root)
    _require(accepted['map_proposal'] == proposal and accepted['authorization'] == authorization,
             'recovered cap authority differs from exact map approval')
    original = read_json(verify_record(accepted['lineage']['grant']['authorization'])['path'])
    amendment, approval = original.get('cap_amendment'), original.get('cap_approval')
    _require(isinstance(amendment, dict) and isinstance(approval, dict),
             'original approved cap authority missing')
    verify_record(amendment)
    return amendment, approval


def recovery_map_allocation(proposal, setup, events, run_root, assets, *, verifier=verify_record,
                            active_map_admission=None):
    """Credit only the retained model after accepted recovery; preserve all caps."""
    accepted = accepted_setup_lineage(setup, events, run_root, verifier=verifier,
        active_map_admission=active_map_admission)
    _require(proposal == accepted['map_proposal'], 'exact approved recovered map proposal required')
    original = accepted['lineage']
    allocation = dict(original['proposal']['allocation'])
    _require(proposal['allocation'] == allocation, 'original combined allocation must remain unchanged')
    required = read_json(verifier(proposal['required_assets'])['path'])['candidates'][CANDIDATE]['files']
    _require(len(required) == len(assets) == 1 and
             (assets[0]['repository'], assets[0]['path']) ==
             (required[0]['repository'], required[0]['path']) and
             assets[0]['record'] == accepted['accepted_result']['checkpoint'],
             'exact accepted native model asset required')
    record = assets[0]['record']
    _require(record['bytes'] == required[0]['bytes'] and
             record['sha256'] == required[0]['lfs_sha256'], 'original approved model bytes required')
    credit = record['bytes']
    root = Path(run_root).resolve()
    old_path = Path(accepted['original']['checkpoint']['path'])
    info = old_path.stat()
    identity = dict(device=info.st_dev, inode=info.st_ino, size=info.st_size, mtime_ns=info.st_mtime_ns)
    before_files = original['checkpoint']['files']
    receipts = []
    for path in (root / 'transfers').glob('transfer-*.json'):
        _require(not path.is_symlink(), 'direct acquisition receipt must not be a symlink')
        receipt_record = file_record(path)
        _require(verifier(receipt_record) == receipt_record, 'direct acquisition receipt changed')
        receipt = read_json(path)
        if receipt.get('output') == str(old_path):
            receipts.append((receipt_record, receipt))
    _require(len(receipts) == 1, 'unique original retained checkpoint acquisition receipt required')
    paid_record, paid = receipts[0]
    _require(type(credit) is int and 0 < credit < allocation['artifact_bytes'] and
             credit <= allocation['download_bytes'] and paid.get('error') is None and
             'error' in paid and type(paid.get('bytes_received')) is int and
             paid['bytes_received'] == credit and paid.get('output_identity') == identity and
             isinstance(paid.get('transfer_id'), str) and bool(paid['transfer_id']) and
             str(Path(paid_record['path']).relative_to(root)) not in before_files and
             str(old_path.relative_to(root)) not in before_files and
             not any((row['device'], row['inode']) == (info.st_dev, info.st_ino)
                     for row in before_files.values()),
             'original retained asset credit lacks newly paid approved acquisition')
    from .budgets import _snapshot
    snapshot = _snapshot(root)
    _require(snapshot['direct_download_bytes'] >= credit and snapshot['download_bytes'] >= credit,
             'original paid model contribution absent from global accounting')
    for key in ('download_bytes', 'artifact_bytes'):
        allocation[key] -= credit
    return dict(allocation=allocation, credited_assets_bytes=credit,
        setup=setup, setup_finish_event_sha256=accepted['finish']['event_sha256'],
        original_setup=accepted['original'], recovery_lineage=dict(job_id=accepted['job'],
            grant_event_sha256=accepted['grant']['event_sha256'],
            reserve_event_sha256=accepted['reserve']['event_sha256'],
            finish_event_sha256=accepted['finish']['event_sha256'], request=accepted['request'],
            paid_asset_receipt=paid_record, **(dict(failed_recoveries=accepted['failed_recoveries'])
                if accepted['job'] == REPAIR_JOB else {})))
