"""Prospective retained ownership proofs; cumulative byte totals never decrease.

Only a checked setup grant can bind the before inventory. A cleaned accepted
setup can then reconcile newly retained declared files and command-bound reads.
Old grants without this evidence retain conservative v1 accounting.
"""
from pathlib import Path

from .budgets import _inventory, _snapshot
from .files import file_record, object_hash, read_json, safe_path, verify_record, write_json


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _metadata(info):
    return dict(device=info.st_dev, inode=info.st_ino, logical_bytes=info.st_size,
                allocated_bytes=info.st_blocks * 512, mtime_ns=info.st_mtime_ns)


def _key(row):
    return row['device'], row['inode']


def _files(root):
    return {str(Path(path).relative_to(root)): _metadata(info)
            for path, info in _inventory(root).items()}


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


def _checkpoint(root, grant):
    record = grant.get('byte_checkpoint')
    _require(isinstance(record, dict), 'prospective protected setup byte checkpoint required')
    _require(verify_record(record) == record and Path(record['path']) == root / 'prepare' /
             f"plan069-{grant['candidate']}-setup-byte-checkpoint.json",
             'owned immutable setup byte checkpoint required')
    checkpoint = read_json(record['path'])
    _require(checkpoint.get('schema') == 'plan069-depth-setup-byte-checkpoint/v1' and
             checkpoint.get('candidate') == grant['candidate'] and
             checkpoint.get('resource_snapshot') == grant['resource_snapshot'],
             'checkpoint differs from protected setup grant')
    return checkpoint


def _accepted(root, candidate, events):
    """Use the existing exact approval/request/asset/clean-finish validator."""
    from .depth_map_allowance import remaining_map_allocation
    grants = [row for row in events if row.get('event') == 'depth_setup_authorized' and
              row.get('candidate') == candidate]
    finishes = [row for row in events if row.get('event') == 'finish' and
                row.get('job_id') == f'plan069-{candidate}-setup-001']
    _require(len(grants) == len(finishes) == 1, 'one protected completed setup required')
    grant, finish = grants[0], finishes[0]
    review = read_json(verify_record(grant['review'])['path'])
    proposals = [row for row in review['proposals'] if row['candidate'] == candidate]
    _require(len(proposals) == 1 and object_hash(proposals[0]) == grant['proposal_sha256'],
             'exact setup proposal required for reconciliation')
    proposal = proposals[0]
    result = read_json(verify_record(finish['result'])['path'])
    assets = result.get('assets')
    if assets is None:
        required = read_json(verify_record(proposal['required_assets'])['path'])['candidates'][candidate]['files']
        _require(len(required) == 1, 'single owned checkpoint required')
        assets = [dict(repository=required[0]['repository'], path=required[0]['path'],
                       record=result['checkpoint'])]
    remaining_map_allocation(proposal, finish['result'], events, root, assets)
    return grant, finish, result, proposal


def prepare_reconciliation(run_root, candidate, events):
    """Build attribution only after accepted finish; caller protects its record."""
    root = safe_path(run_root).resolve()
    grant, finish, result, proposal = _accepted(root, candidate, events)
    checkpoint = _checkpoint(root, grant)
    prior = {_key(row) for row in checkpoint['files'].values()}
    job = root / 'jobs' / f'plan069-{candidate}-setup-001'
    files = _files(root)
    snapshot = _snapshot(root)
    for key in ('download_bytes', 'artifact_bytes'):
        _require(checkpoint['resource_snapshot'][key] <= snapshot[key] <=
                 checkpoint['resource_snapshot'][key] + proposal['allocation'][key],
                 'accepted setup exceeds unchanged whole-slot allocation')
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
    runtime_record = result.get('runtime_environment')
    _require(isinstance(runtime_record, dict) and verify_record(runtime_record) == runtime_record and
             Path(runtime_record['path']) == job / 'runtime/result.json',
             'accepted owned actual runtime required for reconciliation')
    runtime = read_json(runtime_record['path'])
    _require(runtime.get('schema') == 'plan069-depth-environment-result/v1' and
             runtime.get('status') == 'complete' and runtime.get('record_kind') == 'actual' and
             runtime.get('candidate') == candidate and runtime.get('inventory') == result.get('inventory'),
             'exact accepted actual runtime inventory required')
    inventory_record = verify_record(runtime['inventory'])
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
        path = safe_path(record['path'])
        _require(path.is_relative_to(job) and not path.is_symlink(), 'declared setup file outside owned job')
        relative = str(path.relative_to(root))
        info = files.get(relative)
        _require(info is not None and info['logical_bytes'] == record['bytes'],
                 'accepted setup file metadata changed')
        _require(verify_record(record) == record, 'accepted setup file content changed')
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
    for command_record in runtime.get('command_receipts', []):
        _require(verify_record(command_record) == command_record and
                 Path(command_record['path']).is_relative_to(job / 'runtime/commands'),
                 'owned accepted runtime command required')
        command = read_json(command_record['path'])
        _require(command.get('record_kind') == 'actual' and command.get('error') is None,
                 'successful actual runtime command required')
        receipt = command.get('uv_transfer_receipt')
        if receipt is None:
            continue
        from .transfer_proxy import completed_uv_receipt
        _require(verify_record(receipt) == receipt, 'UV receipt changed')
        document = read_json(receipt['path'])
        _require(command.get('package_transfer_proxy') is True and
                 Path(receipt['path']) == completed_uv_receipt(root, document['transfer_id']) and
                 document['transfer_id'] not in checkpoint['uv_progress'],
                 'UV receipt is not a new owned command transfer')
        uv.append(dict(command=command_record, receipt=receipt))
    _require(len({row['receipt']['path'] for row in uv}) == len(uv), 'duplicate owned UV session')
    direct = []
    direct_paths = {row['path'] for row in declared if Path(row['path']).parent == job}
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
    _require(files == _files(root), 'setup ownership inventory changed during reconciliation')
    path = root / 'prepare' / f'plan069-{candidate}-setup-byte-reconciliation.json'
    write_json(path, document)
    return file_record(path)


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
