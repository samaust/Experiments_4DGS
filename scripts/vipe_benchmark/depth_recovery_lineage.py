"""Accepted recovery ancestry and paid model allowance, without execution.

A consumed failed setup never qualifies itself. Only its independently approved,
cleanly finished recovery can expose the unchanged retained model to maps.
"""
from pathlib import Path

from .files import file_record, object_hash, read_json, verify_record

CANDIDATE = 'D9'
JOB = 'plan069-D9-setup-recovery-001'
ORIGINAL_JOB = 'plan069-D9-setup-001'


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _one(events, event, job=None):
    rows = [row for row in events if row.get('event') == event and
            (job is None or row.get('job_id') == job)]
    _require(len(rows) == 1, 'unique accepted recovery ' + event + ' required')
    return rows[0]


def accepted_setup_lineage(setup_record, events, run_root, *, verifier=verify_record):
    """Validate exact immutable recovery and its separately checked DO ancestry."""
    root = Path(run_root).resolve()
    job = root / 'jobs' / JOB
    _require(verifier(setup_record) == setup_record and
             Path(setup_record['path']) == job / 'result.json',
             'owned accepted recovery result required')
    result = read_json(setup_record['path'])
    _require(result.get('schema') == 'plan069-video-setup-recovery-result/v1' and
             result.get('record_kind') == 'actual' and result.get('status') == 'complete' and
             result.get('candidate') == CANDIDATE and result.get('job_id') == JOB,
             'actual completed D9 recovery required')
    grant = _one(events, 'depth_setup_recovery_authorized')
    reserve = _one(events, 'reserve', JOB)
    finish = _one(events, 'finish', JOB)
    _require(grant.get('candidate') == CANDIDATE and grant.get('job_id') == JOB and
             grant['sequence'] < reserve['sequence'] < finish['sequence'] and
             reserve.get('resource') == finish.get('resource') == 'setup' and
             finish.get('status') == 'complete' and finish.get('result') == setup_record and
             finish.get('cleanup_confirmed') is True and finish.get('cleanup_uncertain') is False and
             finish.get('surviving_pids') == [] and finish.get('deadline_exceeded') is False,
             'clean independently authorized recovery completion required')
    _require(not any(row.get('event') == 'reserve' and not any(
        end.get('event') in ('finish', 'account') and end.get('job_id') == row.get('job_id') and
        end['sequence'] > row['sequence'] for end in events) for row in events),
        'active attempt prevents accepted recovery lineage')
    request_record = result['request']
    from .depth_setup_recovery import validate_recovery_request
    normalized = validate_recovery_request(request_record, events, root,
        require_reservation=False, verifier=verifier)
    request = read_json(request_record['path'])
    proposal, maps, original = (normalized[key] for key in ('proposal', 'map_proposal', 'original'))
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
        result_record=setup_record, grant=grant, reserve=reserve, finish=finish, job=JOB)


def recovery_map_allocation(proposal, setup, events, run_root, assets, *, verifier=verify_record):
    """Credit only the retained model after accepted recovery; preserve all caps."""
    accepted = accepted_setup_lineage(setup, events, run_root, verifier=verifier)
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
        original_setup=accepted['original'], recovery_lineage=dict(job_id=JOB,
            grant_event_sha256=accepted['grant']['event_sha256'],
            reserve_event_sha256=accepted['reserve']['event_sha256'],
            finish_event_sha256=accepted['finish']['event_sha256'], request=accepted['request'],
            paid_asset_receipt=paid_record))
