"""Prospective retained ownership proofs; cumulative byte totals never decrease.

Only a checked setup grant can bind the before inventory. A cleaned accepted
setup can then reconcile newly retained declared files and command-bound reads.
Old grants without this evidence retain conservative v1 accounting.
"""
from pathlib import Path
import hashlib
import math
import re
import time

from .budgets import _inventory, _snapshot
from .files import file_record, object_hash, read_json, safe_path, verify_record, write_json


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _check_deadline(deadline):
    if deadline is not None and time.monotonic() >= deadline:
        raise TimeoutError('setup byte reconciliation CPU deadline exceeded')


def _timed_verify(record, deadline):
    declared_path = safe_path(record['path'])
    _require(declared_path.is_absolute() and not any(
             component.is_symlink() for component in (declared_path, *declared_path.parents)),
             'reconciliation file symlink or relative path rejected')
    if deadline is None:
        actual = verify_record(record)
        actual['path'] = record['path']
        _require(actual == record, 'changed file during reconciliation: ' + record['path'])
        return actual
    path = safe_path(record['path']).resolve()
    checksum = hashlib.sha256()
    with path.open('rb') as stream:
        while True:
            _check_deadline(deadline)
            block = stream.read(2**20)
            if not block:
                break
            checksum.update(block)
    actual = dict(path=record['path'], sha256=checksum.hexdigest(), bytes=path.stat().st_size)
    _require(actual == record, 'changed file during bounded reconciliation: ' + str(path))
    return actual


def _metadata(info):
    return dict(device=info.st_dev, inode=info.st_ino, logical_bytes=info.st_size,
                allocated_bytes=info.st_blocks * 512, mtime_ns=info.st_mtime_ns)


def _key(row):
    return row['device'], row['inode']


def _files(root, deadline=None):
    return {str(Path(path).relative_to(root)): _metadata(info)
            for path, info in _inventory(root, deadline_check=lambda: _check_deadline(deadline)).items()}


def capture_checkpoint(run_root, candidate, reading):
    """Called under the ledger lock immediately before the protected grant."""
    root = safe_path(run_root).resolve()
    before = _files(root)
    snapshot = _snapshot(root)
    _require(before == _files(root), 'setup checkpoint inventory changed during capture')
    _require(all(snapshot[key] == reading[key] for key in
                 ('download_bytes', 'artifact_bytes', 'logical_artifact_bytes')),
             'setup checkpoint differs from protected live baseline')
    document = dict(schema='plan069-depth-setup-byte-checkpoint/v1', candidate=candidate,
        resource_snapshot=reading, files=before, uv_progress=snapshot['uv_progress'])
    path = root / 'prepare' / f'plan069-{candidate}-setup-byte-checkpoint.json'
    write_json(path, document)
    return file_record(path)


def acquisition_credit(direct, uv, cache, owned_uv, owned_cache):
    """Remove only proved contributions from the same max(UV, cache) metric."""
    _require(all(type(x) is int and x >= 0 for x in (direct, uv, cache, owned_uv, owned_cache))
             and owned_uv <= uv and owned_cache <= cache, 'invalid causal acquisition components')
    return direct + max(uv, cache) - max(uv - owned_uv, cache - owned_cache)


def _checkpoint(root, grant, *, verifier=verify_record):
    record = grant.get('byte_checkpoint')
    _require(isinstance(record, dict), 'prospective protected setup byte checkpoint required')
    _require(verifier(record) == record and Path(record['path']) == root / 'prepare' /
             f"plan069-{grant['candidate']}-setup-byte-checkpoint.json",
             'owned immutable setup byte checkpoint required')
    checkpoint = read_json(record['path'])
    _require(checkpoint.get('schema') == 'plan069-depth-setup-byte-checkpoint/v1' and
             checkpoint.get('candidate') == grant['candidate'] and
             checkpoint.get('resource_snapshot') == grant['resource_snapshot'],
             'checkpoint differs from protected setup grant')
    return checkpoint


def _accepted(root, candidate, events, *, verifier=verify_record):
    """Use the existing exact approval/request/asset/clean-finish validator."""
    from .depth_map_allowance import remaining_map_allocation
    from .depth_recovery_lineage import JOBS
    recovery_finishes = [row for row in events if row.get('event') == 'finish' and
                         row.get('job_id') in JOBS]
    completed_recoveries = [row for row in recovery_finishes if row.get('status') == 'complete']
    if candidate == 'D9' and recovery_finishes:
        _require(len(completed_recoveries) == 1, 'clean independently authorized recovery completion required')
        from .depth_recovery_lineage import accepted_setup_lineage
        accepted = accepted_setup_lineage(completed_recoveries[0]['result'], events, root,
                                          verifier=verifier)
        return (accepted['lineage']['grant'], accepted['finish'],
                accepted['accepted_result'], accepted['map_proposal'])
    grants = [row for row in events if row.get('event') == 'depth_setup_authorized' and
              row.get('candidate') == candidate]
    finishes = [row for row in events if row.get('event') == 'finish' and
                row.get('job_id') == f'plan069-{candidate}-setup-001']
    _require(len(grants) == len(finishes) == 1, 'one protected completed setup required')
    grant, finish = grants[0], finishes[0]
    review = read_json(verifier(grant['review'])['path'])
    proposals = [row for row in review['proposals'] if row['candidate'] == candidate]
    _require(len(proposals) == 1 and object_hash(proposals[0]) == grant['proposal_sha256'],
             'exact setup proposal required for reconciliation')
    proposal = proposals[0]
    result = read_json(verifier(finish['result'])['path'])
    assets = result.get('assets')
    if assets is None:
        required = read_json(verifier(proposal['required_assets'])['path'])['candidates'][candidate]['files']
        _require(len(required) == 1, 'single owned checkpoint required')
        assets = [dict(repository=required[0]['repository'], path=required[0]['path'],
                       record=result['checkpoint'])]
    remaining_map_allocation(proposal, finish['result'], events, root, assets, verifier=verifier)
    return grant, finish, result, proposal


def prepare_reconciliation(run_root, candidate, events, *, deadline=None):
    """Build attribution only after accepted finish; caller protects its record."""
    root = safe_path(run_root).resolve()
    verified = {}
    def verifier(record):
        _check_deadline(deadline)
        key = object_hash(record)
        if key not in verified:
            verified[key] = _timed_verify(record, deadline)
        return verified[key]
    _check_deadline(deadline)
    grant, finish, result, proposal = _accepted(root, candidate, events, verifier=verifier)
    checkpoint = _checkpoint(root, grant, verifier=verifier)
    prior = {_key(row) for row in checkpoint['files'].values()}
    recovery = result.get('schema') in ('plan069-video-setup-recovery-result/v1', 'plan069-video-setup-recovery-result/v2')
    original_job = root / 'jobs' / f'plan069-{candidate}-setup-001'
    job = root / 'jobs' / (result['job_id'] if recovery else f'plan069-{candidate}-setup-001')
    files = _files(root, deadline)
    snapshot = _snapshot(root)
    for key in ('download_bytes', 'artifact_bytes'):
        _require(checkpoint['resource_snapshot'][key] <= snapshot[key] <=
                 checkpoint['resource_snapshot'][key] + proposal['allocation'][key],
                 'accepted setup exceeds unchanged whole-slot allocation')
    if recovery:
        _require(result.get('bytes_received') == 0, 'offline recovery cannot acquire bytes')
    else:
        _require(result.get('bytes_received') == snapshot['download_bytes'] -
                 checkpoint['resource_snapshot']['download_bytes'],
                 'accepted setup acquisition differs from prospective checkpoint')
    declared = []
    for row in result.get('assets', []):
        declared.append(row['record'])
    for key in ('checkpoint', 'source_archive'):
        if result.get(key) is not None:
            declared.append(result[key])
    declared.extend(result.get('source_files', []))
    if recovery:
        declared.append(result['original_setup']['checkpoint'])
    retained_paths = ({row['path'] for row in [result['original_setup']['checkpoint'],
                      result['source_archive'], *result['source_files']]} if recovery else set())
    runtime_record = result.get('runtime_environment')
    _require(isinstance(runtime_record, dict) and verifier(runtime_record) == runtime_record and
             Path(runtime_record['path']) == job / 'runtime/result.json',
             'accepted owned actual runtime required for reconciliation')
    runtime = read_json(runtime_record['path'])
    _require(runtime.get('schema') == 'plan069-depth-environment-result/v1' and
             runtime.get('status') == 'complete' and runtime.get('record_kind') == 'actual' and
             runtime.get('candidate') == candidate and runtime.get('inventory') == result.get('inventory'),
             'exact accepted actual runtime inventory required')
    inventory_record = verifier(runtime['inventory'])
    _require(inventory_record == runtime['inventory'] and
             Path(inventory_record['path']) == job / 'runtime/inventory.json',
             'owned runtime inventory required')
    inventory = read_json(inventory_record['path'])
    _require(inventory.get('inventory_only') is True and inventory.get('model_imports') is False and
             inventory.get('gpu_operations') is False, 'installed-file inventory scope required')
    installed_records = [row for package in inventory['packages'] for row in package['files']]
    declared.extend(installed_records)
    installed_paths = {row['path'] for row in installed_records}
    installed_keys = set()
    owned = {}
    for record in declared:
        declared_path = safe_path(record['path'])
        _require(declared_path.is_absolute() and not any(
                 component.is_symlink() for component in (declared_path, *declared_path.parents)),
                 'declared setup file symlink or relative path rejected')
        path = declared_path.resolve(strict=True)
        _require((path.is_relative_to(job) or (record['path'] in retained_paths and
                  path.is_relative_to(original_job))) and not path.is_symlink(),
                 'declared setup file outside approved owned lineage')
        relative = str(path.relative_to(root))
        info = files.get(relative)
        _require(info is not None and info['logical_bytes'] == record['bytes'],
                 'accepted setup file metadata changed')
        _require(verifier(record) == record, 'accepted setup file content changed')
        if _key(info) not in prior:
            owned[relative] = info
            if record['path'] in installed_paths:
                installed_keys.add(_key(info))
    # Cache files must share a new accepted installed inode. A new alias of an
    # old inode is not new acquisition; no credit for unowned cache growth.
    cache = {}
    seen = set()
    for path, info in files.items():
        if Path(path).parts[0] in ('setup-cache', 'managed-python') and _key(info) in installed_keys:
            if _key(info) not in seen:
                cache[path] = info
                seen.add(_key(info))
    uv = []
    commands = [(record, job) for record in runtime.get('command_receipts', [])]
    if recovery:
        failure = read_json(verifier(result['original_setup']['runtime_failure'])['path'])
        commands.extend((record, original_job) for record in failure['command_receipts']
                        if read_json(verifier(record)['path']).get('uv_transfer_receipt') is not None)
    for command_record, command_job in commands:
        _require(verifier(command_record) == command_record and
                 Path(command_record['path']).is_relative_to(command_job / 'runtime/commands'),
                 'owned accepted runtime command required')
        command = read_json(command_record['path'])
        _require(command.get('record_kind') == 'actual' and command.get('error') is None,
                 'successful actual runtime command required')
        receipt = command.get('uv_transfer_receipt')
        if receipt is None:
            continue
        from .transfer_proxy import completed_uv_receipt
        _require(verifier(receipt) == receipt, 'UV receipt changed')
        document = read_json(receipt['path'])
        _require(command.get('package_transfer_proxy') is True and
                 Path(receipt['path']) == completed_uv_receipt(root, document['transfer_id']) and
                 document['transfer_id'] not in checkpoint['uv_progress'],
                 'UV receipt is not a new owned command transfer')
        uv.append(dict(command=command_record, receipt=receipt))
    _require(len({row['receipt']['path'] for row in uv}) == len(uv), 'duplicate owned UV session')
    direct = []
    direct_paths = {row['path'] for row in declared if Path(row['path']).parent in (job, original_job)}
    for path in (root / 'transfers').glob('transfer-*.json'):
        document = read_json(path)
        if document.get('output') not in direct_paths:
            continue
        relative = str(Path(document['output']).relative_to(root))
        info = owned.get(relative)
        identity = document.get('output_identity') or {}
        _require(info is not None and document.get('error') is None and
                 identity == dict(device=info['device'], inode=info['inode'],
                                  size=info['logical_bytes'], mtime_ns=info['mtime_ns']) and
                 type(document.get('bytes_received')) is int and
                 document['bytes_received'] == info['logical_bytes'] and
                 str(path.relative_to(root)) not in checkpoint['files'],
                 'direct transfer is not newly retained accepted setup data')
        direct.append(file_record(path))
    _require(len({read_json(row['path'])['transfer_id'] for row in direct}) == len(direct),
             'duplicate owned direct transfer')
    document = dict(schema='plan069-depth-setup-byte-reconciliation/v1', candidate=candidate,
        setup_grant_sha256=grant['event_sha256'], setup_finish_event_sha256=finish['event_sha256'],
        setup=finish['result'], checkpoint=grant['byte_checkpoint'],
        runtime=runtime_record, inventory=inventory_record,
        owned_files=owned, retained_cache_files=cache, uv_transfers=uv, direct_transfers=direct)
    if recovery:
        from .depth_recovery_lineage import accepted_setup_lineage
        accepted = accepted_setup_lineage(finish['result'], events, root, verifier=verifier)
        document['recovery_lineage'] = dict(job_id=accepted['job'], grant_event_sha256=accepted['grant']['event_sha256'],
            reserve_event_sha256=accepted['reserve']['event_sha256'],
            failed_finish_event_sha256=accepted['lineage']['finish']['event_sha256'],
            request=accepted['request'], **(dict(failed_recoveries=accepted['failed_recoveries'])
                if accepted['failed_recoveries'] else {}))
    _check_deadline(deadline)
    _require(files == _files(root, deadline), 'setup ownership inventory changed during reconciliation')
    _check_deadline(deadline)
    path = root / 'prepare' / f'plan069-{candidate}-setup-byte-reconciliation.json'
    write_json(path, document)
    record = file_record(path)
    _check_deadline(deadline)
    return record


def _recovery_proof_lineage(proof, events, original_grant, finish):
    """Recheck small protected bindings; retained large files use inode metadata."""
    lineage = proof.get('recovery_lineage')
    _require(isinstance(lineage, dict) and proof.get('candidate') == 'D9',
             'checked D9 recovery causal lineage required')
    def event(kind, digest):
        rows = [row for row in events if row.get('event') == kind and
                row.get('event_sha256') == digest]
        _require(len(rows) == 1, 'unique protected recovery causal event required')
        return rows[0]
    from .depth_recovery_lineage import JOBS, JOB, REPAIR_JOB, RESULT_SCHEMAS, checked_failed_recoveries
    job_id = lineage.get('job_id', JOB)
    _require(job_id in JOBS, 'exact approved causal recovery job required')
    grant = event('depth_setup_recovery_authorized', lineage['grant_event_sha256'])
    reserve = event('reserve', lineage['reserve_event_sha256'])
    failed = event('finish', lineage['failed_finish_event_sha256'])
    _require(original_grant['sequence'] < failed['sequence'] < grant['sequence'] <
             reserve['sequence'] < finish['sequence'] and
             grant.get('candidate') == 'D9' and
             grant.get('job_id') == reserve.get('job_id') == finish.get('job_id') ==
             job_id and
             failed.get('job_id') == 'plan069-D9-setup-001' and failed.get('status') == 'failed' and
             failed.get('cleanup_confirmed') is True and failed.get('cleanup_uncertain') is False and
             failed.get('surviving_pids') == [] and failed.get('deadline_exceeded') is False and
             reserve.get('resource') == finish.get('resource') == 'setup',
             'causal recovery did not preserve failed setup and checked completion')
    request = lineage['request']
    _require(verify_record(request) == request and grant.get('request') == request and
             reserve.get('evidence', {}).get('request') == request,
             'checked recovery causal request changed')
    document = read_json(request['path'])
    original = document['original_setup']
    _require(document.get('schema') == ('plan069-video-setup-recovery-request/v2'
                 if job_id == REPAIR_JOB else 'plan069-video-setup-recovery-request/v1') and
             original.get('grant_event_sha256') == original_grant['event_sha256'] and
             original.get('failed_finish_event_sha256') == failed['event_sha256'] and
             original.get('byte_checkpoint') == proof['checkpoint'] and
             grant.get('original_setup') == original,
             'original prospective recovery checkpoint binding changed')
    for key in ('review', 'authorization', 'source_review'):
        _require(verify_record(document[key]) == document[key] == grant.get(key) ==
                 reserve.get('evidence', {}).get(key), 'recovery causal authority changed')
    descriptors = checked_failed_recoveries(job_id, lineage.get('failed_recoveries', []),
        events, Path(proof['setup']['path']).parents[2], before_sequence=grant['sequence'])
    accepted = read_json(proof['setup']['path'])
    if job_id == REPAIR_JOB:
        _require(document.get('failed_recoveries') == accepted.get('failed_recoveries') == descriptors,
                 'causal accepted failed recovery ancestry changed')
    _require(accepted.get('schema') == RESULT_SCHEMAS[job_id] and
             accepted.get('original_setup') == original and accepted.get('request') == request and
             accepted.get('bytes_received') == 0 and accepted.get('original_failure_preserved') is True,
             'accepted recovery causal result changed')


def causal_credits(run_root, subject_grant, events, proofs=None):
    """Revalidate protected ownership and recompute max-metric credit live."""
    root = safe_path(run_root).resolve()
    reconciled = [row for row in events if row.get('event') == 'depth_setup_bytes_reconciled' and
                  row.get('sequence', -1) > subject_grant.get('sequence', len(events)) and
                  row.get('candidate') != subject_grant['candidate']]
    if proofs is not None:
        _require([row['event_sha256'] for row in reconciled] == proofs,
                 'protected causal reconciliation set changed')
    files = _files(root)
    snapshot = _snapshot(root)
    owned: dict[tuple[int, int], int] = {}
    cache: dict[tuple[int, int], int] = {}
    uv_ids, direct_ids = set(), set()
    direct = uv = 0
    for event in reconciled:
        _require(event.get('candidate') != subject_grant['candidate'], 'cannot credit own setup')
        record = event['proof']
        _require(verify_record(record) == record and Path(record['path']) == root / 'prepare' /
                 f"plan069-{event['candidate']}-setup-byte-reconciliation.json",
                 'protected owned causal proof required')
        proof = read_json(record['path'])
        grants = [row for row in events if row.get('event') == 'depth_setup_authorized' and
                  row.get('event_sha256') == proof.get('setup_grant_sha256')]
        finishes = [row for row in events if row.get('event') == 'finish' and
                    row.get('event_sha256') == proof.get('setup_finish_event_sha256')]
        _require(len(grants) == len(finishes) == 1 and
                 subject_grant['sequence'] < grants[0]['sequence'] < finishes[0]['sequence'] < event['sequence'] and
                 event.get('candidate') == grants[0]['candidate'] == proof.get('candidate') and
                 proof.get('schema') == 'plan069-depth-setup-byte-reconciliation/v1' and
                 finishes[0].get('result') == proof.get('setup') and
                 finishes[0].get('status') == 'complete' and finishes[0].get('cleanup_confirmed') is True and
                 finishes[0].get('cleanup_uncertain') is False and finishes[0].get('surviving_pids') == [] and
                 finishes[0].get('deadline_exceeded') is False,
                 'causal proof lacks later accepted setup lineage')
        if proof.get('recovery_lineage') is not None:
            _recovery_proof_lineage(proof, events, grants[0], finishes[0])
        else:
            _require(finishes[0].get('job_id') == f"plan069-{proof['candidate']}-setup-001",
                     'recovery causal proof requires protected ancestry')
        for key in ('setup', 'runtime', 'inventory'):
            _require(verify_record(proof[key]) == proof[key], 'accepted causal evidence changed')
        accepted = read_json(proof['setup']['path'])
        runtime = read_json(proof['runtime']['path'])
        _require(accepted.get('runtime_environment') == proof['runtime'] and
                 accepted.get('inventory') == runtime.get('inventory') == proof['inventory'],
                 'accepted causal runtime binding changed')
        checkpoint = _checkpoint(root, grants[0])
        _require(proof['checkpoint'] == grants[0]['byte_checkpoint'], 'causal checkpoint binding changed')
        prior = {_key(row) for row in checkpoint['files'].values()}
        for group, collection in (('owned_files', owned), ('retained_cache_files', cache)):
            for path, info in proof[group].items():
                _require(files.get(path) == info and _key(info) not in prior,
                         'causal retained inode changed or predates setup')
                if group == 'retained_cache_files':
                    _require(_key(info) in {_key(row) for row in proof['owned_files'].values()},
                             'cache inode has no accepted setup owner')
                collection[_key(info)] = max(collection.get(_key(info), 0),
                    info['logical_bytes'] if group == 'retained_cache_files' else
                    max(info['logical_bytes'], info['allocated_bytes']))
        for row in proof['uv_transfers']:
            _require(verify_record(row['receipt']) == row['receipt'] and
                     verify_record(row['command']) == row['command'], 'command-bound UV evidence changed')
            command = read_json(row['command']['path'])
            document = read_json(row['receipt']['path'])
            identifier = document['transfer_id']
            from .transfer_proxy import completed_uv_receipt
            _require(command.get('uv_transfer_receipt') == row['receipt'] and
                     Path(row['receipt']['path']) == completed_uv_receipt(root, identifier) and
                     identifier not in checkpoint['uv_progress'] and identifier not in uv_ids,
                     'duplicate preexisting or unbound causal UV session')
            uv_ids.add(identifier); uv += document['bytes_received']
        for row in proof['direct_transfers']:
            _require(verify_record(row) == row, 'causal direct receipt changed')
            document = read_json(row['path'])
            identifier = document['transfer_id']
            _require(identifier not in direct_ids, 'duplicate causal direct transfer')
            direct_ids.add(identifier); direct += document['bytes_received']
    _require(direct <= snapshot['direct_download_bytes'], 'causal direct contribution absent from global totals')
    return dict(artifact_bytes=sum(owned.values()),
        download_bytes=acquisition_credit(direct, snapshot['uv_metered_bytes'],
            snapshot['retained_package_bytes'], uv, sum(cache.values())),
        protected_events=[row['event_sha256'] for row in reconciled], snapshot=snapshot)


def run_reconciliation(ledger, candidate, admission, output, *, seconds_limit=120.):
    """Execute a fresh named CPU admission, preserve cleanup, charge actual time.

    The caller supplies the existing independently checked root CPU admission.
    This grants no installation, download, model, GPU or native maps authority.
    """
    started = time.monotonic()
    _require(type(seconds_limit) in (int, float) and math.isfinite(seconds_limit) and
             seconds_limit > 5, 'bounded CPU reconciliation deadline required')
    deadline = started + seconds_limit - 5
    record = _timed_verify(admission, deadline)
    _require(record == admission, 'exact independently checked CPU admission required')
    approved = read_json(record['path'])
    _require(type(seconds_limit) in (int, float) and math.isfinite(seconds_limit) and
             seconds_limit > 5, 'bounded CPU reconciliation deadline required')
    events = ledger.events()
    _require(events and approved.get('schema') == 'plan069-root-cpu-fixture-admission/v1' and
             approved.get('candidate') == approved.get('cpu_accounting_owner') == candidate and
             approved.get('ledger_head_sequence') == events[-1]['sequence'] and
             approved.get('ledger_head_sha256') == events[-1]['event_sha256'] and
             approved.get('ledger_event_count') == len(events),
             'fresh named CPU reconciliation admission required')
    grants = [row for row in events if row.get('event') == 'depth_setup_authorized' and
              row.get('candidate') == candidate]
    _require(len(grants) == 1, 'exact protected setup allocation required')
    review = read_json(verify_record(grants[0]['review'])['path'])
    proposal = next(row for row in review['proposals'] if row['candidate'] == candidate)
    allocation = approved.get('candidate_cpu_allocation_seconds')
    elapsed = approved.get('candidate_cpu_elapsed_seconds')
    remaining = approved.get('candidate_cpu_remaining_seconds')
    _require(all(type(x) in (int, float) and math.isfinite(x) and x >= 0
                 for x in (allocation, elapsed, remaining)) and
             allocation <= proposal['allocation']['cpu_seconds'] and
             math.isclose(allocation - elapsed, remaining, abs_tol=1e-6),
             'checked candidate CPU remaining allowance required')
    global_elapsed = ledger.totals(events)['cpu']['elapsed_seconds']
    global_remaining = ledger.config['cpu_prepare_score_report_seconds_limit'] - global_elapsed
    _require(approved.get('global_cpu_elapsed_seconds') == global_elapsed and
             approved.get('global_cpu_remaining_seconds') == global_remaining and
             type(approved.get('seconds')) in (int, float) and
             seconds_limit <= approved['seconds'] and
             seconds_limit + 180 + 160 <= min(remaining, global_remaining),
             'CPU reconciliation must preserve qualification and maps headroom')
    _require(not any(row['event'] == 'reserve' for row in ledger.states(events).values()),
             'active attempt prevents CPU reconciliation')
    root = ledger.path.resolve().parent
    literal_output = safe_path(output).absolute()
    _require(not any(component.is_symlink() for component in
                     (literal_output, *literal_output.parents)),
             'immutable owned CPU reconciliation output required')
    output = literal_output.resolve()
    numbered = re.fullmatch(r'plan069-' + re.escape(candidate) +
                            r'-setup-byte-reconciliation-([0-9]{3,})', output.name)
    _require(output.parent == root / 'prepare' and numbered is not None and
             int(numbered[1]) > 0 and numbered[1] == f'{int(numbered[1]):03}' and
             not output.exists(), 'immutable owned CPU reconciliation output required')
    output.mkdir(parents=True, exist_ok=False)
    receipt = dict(schema='plan069-depth-setup-byte-reconciliation-cpu/v1',
        candidate=candidate, cpu_accounting_owner=candidate, status='failed',
        admission=record, seconds_limit=seconds_limit, qualification_headroom_seconds=180,
        maps_cpu_headroom_seconds=160, cleanup_confirmed=True, surviving_pids=[],
        model_loads=False, gpu_operations=False, downloads=False, automatic_retries=0)
    try:
        _check_deadline(deadline)
        _require(read_json(_timed_verify(approved['effective_configuration'], deadline)['path']) == ledger.config,
                 'exact effective CPU configuration required')
        from .depth_admission import local_source_records
        source = read_json(_timed_verify(approved['source_review'], deadline)['path'])
        _require(source.get('status') == 'passed' and source.get('candidate') == candidate and
                 source.get('local_sources') == local_source_records(candidate),
                 'CPU reconciliation sources differ from passing independent review')
        _check_deadline(deadline)
        event = ledger.reconcile_depth_setup_bytes(candidate,
            deadline=deadline,
            expected_head=approved['ledger_head_sha256'])
        _check_deadline(started + seconds_limit)
        receipt.update(status='complete', protected_reconciliation_event=event['event_sha256'],
                       proof=event['proof'])
        return receipt
    except BaseException as exception:
        receipt['error'] = f'{type(exception).__name__}: {exception}'
        raise
    finally:
        receipt['elapsed_seconds'] = time.monotonic() - started
        path = output / 'receipt.json'
        write_json(path, receipt)
        ledger.charge_cpu_preparation(receipt['elapsed_seconds'], file_record(path))


def main():
    import argparse
    from .ledger import Ledger
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', choices=('D9', 'D10'), required=True)
    parser.add_argument('--ledger', type=Path, required=True)
    parser.add_argument('--admission', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--seconds-limit', type=float, default=120.)
    args = parser.parse_args()
    admission = file_record(args.admission)
    document = read_json(admission['path'])
    config = read_json(verify_record(document['effective_configuration'])['path'])
    run_reconciliation(Ledger(args.ledger, config), args.candidate,
                       admission, args.output, seconds_limit=args.seconds_limit)


if __name__ == '__main__':
    main()
