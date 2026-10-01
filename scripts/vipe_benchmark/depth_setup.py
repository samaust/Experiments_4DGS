"""Bounded, immutable acquisition for the first Plan 069 native depth slot."""

import os
from pathlib import Path, PurePosixPath
import tarfile
import time

from .files import file_record, object_hash, read_json, verify_record, write_json


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _acquire(url, path, *, max_bytes, deadline, run_root,
             download_limit, artifact_limit):
    """Use the run's durable direct-transfer meter and its shared download lock."""
    from .budgets import budget_snapshot
    from .runtime import download
    _require(time.monotonic() < deadline, 'depth setup transfer deadline')
    already = budget_snapshot(run_root)['download_bytes']
    ceiling = min(download_limit, already + max_bytes)
    record = download(url, path, run_root / 'transfers', limit=ceiling,
        run_root=run_root, artifact_limit=artifact_limit)
    _require(record['bytes'] <= max_bytes and time.monotonic() < deadline,
             'depth setup transfer bound exceeded')
    return record


def _unpack_source(archive, output, revision, *, deadline, max_bytes=2**30,
                   max_files=10000, required='metric_depth/depth_anything_v2/dpt.py'):
    """Extract regular pinned source files without links or path traversal."""
    output.mkdir(exist_ok=False)
    with tarfile.open(archive, 'r:gz') as stream:
        members = stream.getmembers()
        _require(bool(members) and len(members) <= max_files,
                 'empty or oversized pinned source archive')
        _require(sum(member.size for member in members if member.isfile()) <= max_bytes,
                 'source extraction byte ceiling')
        roots = {PurePosixPath(member.name).parts[0] for member in members}
        _require(len(roots) == 1 and next(iter(roots)).endswith(revision),
                 'source archive revision root changed')
        for member in members:
            _require(time.monotonic() < deadline, 'source extraction deadline')
            parts = PurePosixPath(member.name).parts
            _require(all(part not in ('', '.', '..') for part in parts) and
                     not member.issym() and not member.islnk() and
                     (member.isdir() or member.isfile()),
                     'unsafe source archive member')
            if len(parts) == 1:
                continue
            destination = output.joinpath(*parts[1:])
            _require(destination.is_relative_to(output), 'source archive traversal')
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                with stream.extractfile(member) as source, destination.open('xb') as target:
                    while chunk := source.read(2**20):
                        _require(time.monotonic() < deadline,
                                 'source extraction deadline')
                        target.write(chunk)
    _require((output / required).is_file(), 'pinned inference source absent')


def _active_reservation(request, request_path, output):
    """Reject direct or duplicate actual worker invocation outside supervision."""
    from .config import load
    from .ledger import Ledger
    _require(request_path is not None, 'actual setup requires saved request path')
    ledger_path = Path(request['ledger_path']).resolve()
    run_root = ledger_path.parent
    _require(output.resolve() == (run_root / 'jobs' / request['job_id']).resolve(),
             'actual setup output must be the reserved job directory')
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    state = Ledger(ledger_path, config).states().get(request['job_id'], {})
    command = state.get('command', [])
    _require(state.get('event') == 'reserve' and
             state.get('evidence', {}).get('request') == file_record(request_path) and
             '--request' in command and '--output' in command and
             command[command.index('--request') + 1] == str(request_path) and
             command[command.index('--output') + 1] == str(output) and
             os.environ.get('VIPE_RESERVATION_START') == str(state.get('monotonic_start')),
             'active exact ledger setup reservation required')
    return run_root, config


def run_d7_setup(request, output, *, request_path=None, acquire=_acquire):
    """Acquire pinned D7 source and checkpoint within its one approved setup."""
    started = time.monotonic()
    review = read_json(verify_record(request['review'])['path'])
    approved = read_json(verify_record(request['authorization'])['path'])
    proposal = next((row for row in review.get('proposals', [])
                     if row.get('candidate') == 'D7'), None)
    grant = next((row for row in approved.get('candidate_approvals', [])
                  if row.get('candidate') == 'D7'), None)
    _require(request.get('schema') == 'plan069-depth-setup-request/v1' and
             request.get('candidate') == 'D7' and
             request.get('job_id') == 'plan069-D7-setup-001' and
             approved.get('review') == request['review'] and
             proposal is not None and grant is not None and
             grant.get('status') == 'approved' and
             grant.get('proposal_sha256') == object_hash(proposal),
             'exact approved D7 setup request required')
    inventory = read_json(verify_record(proposal['required_assets'])['path'])
    asset = inventory['candidates']['D7']['files']
    _require(len(asset) == 1 and asset[0]['repository'] == 'dav2metric' and
             asset[0]['path'] == 'depth_anything_v2_metric_hypersim_vits.pth',
             'D7 required-only checkpoint changed')
    allocation = proposal['allocation']
    _require(allocation['setup_seconds'] == 1800 and
             allocation['download_bytes'] >= asset[0]['bytes'],
             'D7 setup bounds changed')
    deadline = started + allocation['setup_seconds']
    output = Path(output)
    if request.get('record_kind') == 'actual':
        run_root, config = _active_reservation(request, request_path, output)
    else:
        _require(request.get('record_kind') == 'fixture', 'setup origin required')
        run_root = output.parent
        config = dict(new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    _require(output.name == request['job_id'] and not output.exists(),
             'immutable D7 setup output identity changed or exists')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    from .budgets import budget_snapshot
    baseline_download = budget_snapshot(run_root)['download_bytes']
    download_limit = min(config['new_download_gib_limit'] * 2**30,
                         baseline_download + allocation['download_bytes'])
    artifact_limit = config['new_artifact_disk_gib_limit'] * 2**30
    try:
        source = proposal['candidate_config']['code']
        archive = output / 'source.tar.gz'
        source_url = 'https://codeload.github.com/DepthAnything/Depth-Anything-V2/tar.gz/' + source['revision']
        archive_result = acquire(source_url, archive, max_bytes=128 * 2**20,
            deadline=deadline, run_root=run_root, download_limit=download_limit,
            artifact_limit=artifact_limit)
        _require(archive_result['bytes'] + asset[0]['bytes'] <= allocation['download_bytes'],
                 'D7 source plus checkpoint exceeds transfer allocation')
        _unpack_source(archive, output / 'source', source['revision'], deadline=deadline)
        weights = proposal['candidate_config']['weights']
        checkpoint = output / asset[0]['path']
        weight_url = weights['url'] + '/resolve/' + weights['revision'] + '/' + asset[0]['path']
        weight_result = acquire(weight_url, checkpoint,
            max_bytes=asset[0]['bytes'], deadline=deadline, run_root=run_root,
            download_limit=download_limit, artifact_limit=artifact_limit)
        _require(weight_result['bytes'] == asset[0]['bytes'] and
                 weight_result['sha256'] == asset[0]['lfs_sha256'],
                 'D7 checkpoint bytes differ from pinned LFS object')
        received = budget_snapshot(run_root)['download_bytes'] - baseline_download
        _require(received <= allocation['download_bytes'] and
                 time.monotonic() <= deadline, 'D7 setup allocation exceeded')
        result = dict(schema='plan069-depth-setup-result/v1', status='complete',
            candidate='D7', job_id=request['job_id'], record_kind=request['record_kind'],
            review=request['review'], authorization=request['authorization'],
            source_revision=source['revision'], weight_revision=weights['revision'],
            source_archive=file_record(archive), checkpoint=file_record(checkpoint),
            source_dir=str(output / 'source'), bytes_received=received,
            elapsed_seconds=time.monotonic() - started)
        write_json(output / 'result.json', result)
        return result
    except BaseException as error:
        received = budget_snapshot(run_root)['download_bytes'] - baseline_download
        write_json(output / 'failure.json', dict(
            schema='plan069-depth-setup-failure/v1', candidate='D7',
            job_id=request['job_id'], status='failed',
            error=f'{type(error).__name__}: {error}',
            bytes_received=received, elapsed_seconds=time.monotonic() - started))
        raise
