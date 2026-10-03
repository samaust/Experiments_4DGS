"""Pinned, metered asset setup for D8 PointMap and D11 Marigold."""

import hashlib
from pathlib import Path
import time

from .budgets import budget_snapshot
from .depth_source_integrity import source_manifest
from .depth_native_runtime import prepare
from .depth_setup import _acquire, _active_reservation, _unpack_source
from .files import file_record, object_hash, read_json, verify_record, write_json


SOURCE = {
    'D8': ('metric-anything/metric-anything',
           'models/student_pointmap/moge/model/v2.py'),
    'D11': ('huawei-bayerlab/marigold-v2', 'scripts/infer.py'),
}
ASSET_DIRS = {
    'D8': {'metricanything': 'MetricAnything'},
    'D11': {'marigold': 'Marigold-V2', 'qwen': 'Qwen-Image-Edit-2509'},
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _asset_identity(record, expected):
    """Check LFS content hash or the pinned Git blob for small HF files."""
    _require(record['bytes'] == expected['bytes'], 'pinned asset byte count changed')
    if expected['lfs_sha256'] is not None:
        _require(record['sha256'] == expected['lfs_sha256'],
                 'pinned asset LFS digest changed')
    else:
        content = Path(record['path']).read_bytes()
        blob = hashlib.sha1(b'blob ' + str(len(content)).encode() + b'\0' + content).hexdigest()
        _require(blob == expected['git_oid'], 'pinned asset Git blob changed')


def _setup_request(request):
    candidate = request.get('candidate')
    _require(candidate in SOURCE and
             request.get('schema') == 'plan069-depth-setup-request/v1' and
             request.get('job_id') == f'plan069-{candidate}-setup-001',
             'exact D8/D11 setup identity required')
    review = read_json(verify_record(request['review'])['path'])
    approved = read_json(verify_record(request['authorization'])['path'])
    proposal = next((row for row in review.get('proposals', [])
                     if row.get('candidate') == candidate), None)
    grant = next((row for row in approved.get('candidate_approvals', [])
                  if row.get('candidate') == candidate), None)
    _require(review.get('schema') == 'plan069-depth-execution-review/v1' and
             review.get('status') == 'REVIEW' and
             approved.get('schema') == 'plan069-depth-user-authorization/v1' and
             approved.get('status') == 'DO' and
             approved.get('review') == request['review'] and
             proposal is not None and grant is not None and
             grant.get('status') == 'approved' and
             grant.get('proposal_sha256') == object_hash(proposal),
             'exact approved D8/D11 setup proposal required')
    inventory = read_json(verify_record(proposal['required_assets'])['path'])
    assets = inventory['candidates'][candidate]['files']
    _require(assets and {row['repository'] for row in assets} == set(ASSET_DIRS[candidate]) and
             all('/' not in row['repository'] and
                 all(part not in ('', '.', '..') for part in Path(row['path']).parts)
                 for row in assets) and
             sum(row['bytes'] for row in assets) + 256 * 2**20 <=
                 proposal['allocation']['download_bytes'],
             'required asset paths or transfer allocation changed')
    config = proposal['candidate_config']
    _require(config['code']['url'].removeprefix('https://github.com/') == SOURCE[candidate][0] and
             all(len(config[key]['revision']) == 40 for key in ('code', 'weights')) and
             (candidate != 'D11' or len(config['base']['revision']) == 40),
             'pinned source or weight repository changed')
    return proposal, assets


def run_setup(request, output, *, request_path=None, acquire=_acquire,
              prepare_environment=prepare):
    """Download only reviewed source/assets under the active one-use reservation."""
    started = time.monotonic()
    proposal, assets = _setup_request(request)
    candidate, job_id = request['candidate'], request['job_id']
    output = Path(output)
    if request.get('record_kind') == 'actual':
        run_root, config = _active_reservation(request, request_path, output)
    else:
        _require(request.get('record_kind') == 'fixture', 'setup origin required')
        run_root = output.parent
        config = dict(new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    _require(output.name == job_id and not output.exists(),
             'immutable D8/D11 setup output identity changed or exists')
    allocation = proposal['allocation']
    deadline = started + allocation['setup_seconds']
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    baseline_snapshot = budget_snapshot(run_root)
    baseline = baseline_snapshot['download_bytes']
    download_limit = min(config['new_download_gib_limit'] * 2**30,
                         baseline + allocation['download_bytes'])
    artifact_limit = min(config['new_artifact_disk_gib_limit'] * 2**30,
                         baseline_snapshot['artifact_bytes'] + allocation['artifact_bytes'])
    try:
        code = proposal['candidate_config']['code']
        source_archive = output / 'source.tar.gz'
        source_url = 'https://codeload.github.com/' + SOURCE[candidate][0] + '/tar.gz/' + code['revision']
        archive_record = acquire(source_url, source_archive, max_bytes=256 * 2**20,
            deadline=deadline, run_root=run_root, download_limit=download_limit,
            artifact_limit=artifact_limit)
        source_dir = output / 'source'
        _unpack_source(source_archive, source_dir, code['revision'],
                       deadline=deadline, required=SOURCE[candidate][1])
        extracted_source = source_manifest(source_dir)
        asset_bytes = sum(row['bytes'] for row in assets)
        runtime = prepare_environment(request, output, config, run_root=run_root,
            deadline=deadline, acquire=acquire, download_limit=download_limit - asset_bytes,
            artifact_limit=artifact_limit - asset_bytes, request_path=request_path)
        records = []
        for asset in assets:
            repository = asset['repository']
            pin = (proposal['candidate_config']['base'] if repository == 'qwen'
                   else proposal['candidate_config']['weights'])
            assets_root = output / 'assets'
            if candidate == 'D11':
                assets_root /= 'checkpoints'
            path = assets_root / ASSET_DIRS[candidate][repository] / asset['path']
            url = pin['url'] + '/resolve/' + pin['revision'] + '/' + asset['path']
            record = acquire(url, path, max_bytes=asset['bytes'], deadline=deadline,
                run_root=run_root, download_limit=download_limit,
                artifact_limit=artifact_limit)
            _asset_identity(record, asset)
            records.append(dict(repository=repository, path=asset['path'], record=record))
        received = budget_snapshot(run_root)['download_bytes'] - baseline
        _require(received <= allocation['download_bytes'] and time.monotonic() <= deadline,
                 'depth setup allocation exceeded')
        result = dict(schema='plan069-depth-setup-result/v1', status='complete',
            candidate=candidate, job_id=job_id, record_kind=request['record_kind'],
            review=request['review'], authorization=request['authorization'],
            source_revision=code['revision'],
            weight_revision=proposal['candidate_config']['weights']['revision'],
            source_archive=file_record(source_archive),
            source_dir=str(source_dir), native_source=file_record(source_dir / SOURCE[candidate][1]),
            source_manifest=extracted_source, assets=records, runtime=runtime,
            bytes_received=received, elapsed_seconds=time.monotonic() - started)
        _require(source_manifest(source_dir) == extracted_source,
                 'native source tree changed during setup')
        _require(time.monotonic() <= deadline, 'depth setup allocation exceeded')
        result['elapsed_seconds'] = time.monotonic() - started
        write_json(output / 'result.json', result)
        return result
    except BaseException as error:
        received = budget_snapshot(run_root)['download_bytes'] - baseline
        write_json(output / 'failure.json', dict(schema='plan069-depth-setup-failure/v1',
            candidate=candidate, job_id=job_id, status='failed',
            error=f'{type(error).__name__}: {error}', bytes_received=received,
            elapsed_seconds=time.monotonic() - started))
        raise
