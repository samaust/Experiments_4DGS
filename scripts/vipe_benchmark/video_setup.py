"""Metered, one-use acquisition for pinned D9/D10 native video models."""

from pathlib import Path, PurePosixPath
import tarfile
import time

from .budgets import budget_snapshot
from .depth_setup import _acquire, _active_reservation
from .files import file_record, object_hash, read_json, verify_record, write_json
from .video_native import native_source_records
from .video_environment import bind_source_environment


def _extract(archive, destination, revision, deadline):
    destination.mkdir(exist_ok=False)
    with tarfile.open(archive, 'r:gz') as stream:
        members = stream.getmembers()
        if not members or len(members) > 10000 or sum(
                member.size for member in members if member.isfile()) > 2**30:
            raise ValueError('video source archive size or member bound')
        roots = {PurePosixPath(member.name).parts[0] for member in members}
        if len(roots) != 1 or not next(iter(roots)).endswith(revision):
            raise ValueError('video source archive revision changed')
        for member in members:
            if time.monotonic() >= deadline:
                raise TimeoutError('video source extraction deadline')
            parts = PurePosixPath(member.name).parts
            if (not all(part not in ('', '.', '..') for part in parts) or
                    member.issym() or member.islnk() or
                    not (member.isfile() or member.isdir())):
                raise ValueError('unsafe video source archive member')
            if len(parts) == 1:
                continue
            path = destination.joinpath(*parts[1:])
            if not path.is_relative_to(destination):
                raise ValueError('video source archive traversal')
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            else:
                path.parent.mkdir(parents=True, exist_ok=True)
                with stream.extractfile(member) as source, path.open('xb') as target:
                    while chunk := source.read(2**20):
                        if time.monotonic() >= deadline:
                            raise TimeoutError('video source extraction deadline')
                        target.write(chunk)
    return native_source_records(destination)


def run_video_setup(request, output, *, request_path=None, acquire=_acquire,
                    environment_runner=None):
    """Acquire one pinned source archive and checkpoint, preserving all failures."""
    started = time.monotonic()
    candidate = request.get('candidate')
    if candidate not in ('D9', 'D10'):
        raise ValueError('D9 or D10 video setup candidate required')
    review = read_json(verify_record(request['review'])['path'])
    authorization = read_json(verify_record(request['authorization'])['path'])
    proposal = next((row for row in review.get('proposals', [])
        if row.get('candidate') == candidate), None)
    grant = next((row for row in authorization.get('candidate_approvals', [])
        if row.get('candidate') == candidate), None)
    job_id = f'plan069-{candidate}-setup-001'
    if (request.get('schema') != 'plan069-depth-setup-request/v1' or
            request.get('job_id') != job_id or
            authorization.get('review') != request['review'] or
            proposal is None or grant is None or
            grant.get('status') != 'approved' or
            grant.get('proposal_sha256') != object_hash(proposal) or
            proposal.get('max_attempts') != 1):
        raise ValueError('exact approved native video setup required')
    source = proposal['candidate_config']['code']
    weights = proposal['candidate_config']['weights']
    if (source.get('url') != 'https://github.com/DepthAnything/Video-Depth-Anything' or
            source.get('revision') != '4f5ae23172ba60fd7bc11ef671cca678842c7072' or
            weights.get('url') != 'https://huggingface.co/depth-anything/' +
                ('Video-Depth-Anything-Small' if candidate == 'D9' else
                 'Metric-Video-Depth-Anything-Small')):
        raise ValueError('native video source or weight repository changed')
    inventory = read_json(verify_record(proposal['required_assets'])['path'])
    assets = inventory['candidates'][candidate]['files']
    expected_name = ('video_depth_anything_vits.pth' if candidate == 'D9' else
                     'metric_video_depth_anything_vits.pth')
    if (len(assets) != 1 or assets[0]['path'] != expected_name or
            assets[0]['repository'] != ('vda' if candidate == 'D9' else 'vdame') or
            not assets[0]['lfs_sha256']):
        raise ValueError('video required-only checkpoint changed')
    allocation = proposal['allocation']
    if proposal.get('runtime_recipe') is not None:
        from .depth_admission import selected_profile_inventory
        selected_profile_inventory(proposal)
        environment = request.get('runtime_environment', {})
        if (environment.get('recipe') != proposal['runtime_recipe'] or
                environment.get('runtime_profile') != proposal['profile'].get('runtime_profile')):
            raise ValueError('video runtime proposal and environment profile differ')
    elif request.get('runtime_environment', {}).get('runtime_profile') is not None:
        raise ValueError('video runtime profile requires an explicitly amended proposal')
    if (allocation['setup_seconds'] != 2400 or
            allocation['download_bytes'] < assets[0]['bytes'] or
            allocation['download_bytes'] > 3 * 2**30):
        raise ValueError('video setup allocation changed')
    deadline = started + allocation['setup_seconds']
    output = Path(output)
    if request.get('record_kind') == 'actual':
        if not isinstance(request.get('runtime_environment'), dict) or environment_runner is not None:
            raise ValueError('actual video setup requires frozen runtime environment without fixture runner')
        run_root, config = _active_reservation(request, request_path, output)
    elif request.get('record_kind') == 'fixture':
        run_root = output.parent
        config = dict(new_download_gib_limit=110,
                      new_artifact_disk_gib_limit=210)
    else:
        raise ValueError('video setup record kind required')
    if output.name != job_id or output.exists():
        raise ValueError('immutable video setup output identity changed or exists')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    baseline = budget_snapshot(run_root)['download_bytes']
    download_limit = min(config['new_download_gib_limit'] * 2**30,
                         baseline + allocation['download_bytes'])
    artifact_limit = config['new_artifact_disk_gib_limit'] * 2**30
    try:
        archive = output / 'source.tar.gz'
        archive_record = acquire(
            'https://codeload.github.com/DepthAnything/Video-Depth-Anything/tar.gz/' +
                source['revision'], archive, max_bytes=128 * 2**20,
            deadline=deadline, run_root=run_root, download_limit=download_limit,
            artifact_limit=artifact_limit)
        if archive_record['bytes'] + assets[0]['bytes'] > allocation['download_bytes']:
            raise ValueError('video source and checkpoint exceed transfer allocation')
        source_dir = output / 'source'
        source_files = _extract(archive, source_dir, source['revision'], deadline)
        runtime = None
        if 'runtime_environment' in request:
            environment = bind_source_environment(request['runtime_environment'], source_dir,
                source['revision'], candidate=candidate, record_kind=request['record_kind'])
            if request['record_kind'] == 'actual':
                environment.update(ledger_path=request['ledger_path'],
                                   setup_request=file_record(request_path))
        checkpoint = output / expected_name
        checkpoint_record = acquire(
            weights['url'] + '/resolve/' + weights['revision'] + '/' + expected_name,
            checkpoint, max_bytes=assets[0]['bytes'], deadline=deadline,
            run_root=run_root, download_limit=download_limit,
            artifact_limit=artifact_limit)
        if (checkpoint_record['bytes'] != assets[0]['bytes'] or
                checkpoint_record['sha256'] != assets[0]['lfs_sha256']):
            raise ValueError('video checkpoint differs from pinned LFS object')
        if 'runtime_environment' in request:
            from .depth_environment import provision_depth_environment
            runtime = provision_depth_environment(environment, output / 'runtime', config,
                run_root=run_root, deadline=deadline, download_limit=download_limit,
                artifact_limit=artifact_limit, runner=environment_runner)
        received = budget_snapshot(run_root)['download_bytes'] - baseline
        if received > allocation['download_bytes'] or time.monotonic() >= deadline:
            raise ValueError('video setup allocation exceeded')
        result = dict(schema='plan069-video-setup-result/v1',
            status='complete', candidate=candidate, job_id=job_id,
            record_kind=request['record_kind'], review=request['review'],
            authorization=request['authorization'], source_revision=source['revision'],
            weight_revision=weights['revision'], source_archive=file_record(archive),
            source_dir=str(source_dir), source_files=source_files,
            checkpoint=file_record(checkpoint), bytes_received=received,
            elapsed_seconds=time.monotonic() - started)
        if runtime is not None:
            result.update(runtime_environment=file_record(output / 'runtime/result.json'),
                python_executable=runtime['python_executable'], python=runtime['python'],
                dependency_lock=runtime['dependency_lock'], inventory=runtime['inventory'],
                media_tools=environment['media_tools'], xformers=environment['xformers'])
            if environment.get('runtime_profile') is not None:
                result.update(runtime_recipe=environment['recipe'],
                              runtime_profile=environment['runtime_profile'])
        write_json(output / 'result.json', result)
        return result
    except BaseException as error:
        write_json(output / 'failure.json', dict(
            schema='plan069-video-setup-failure/v1', status='failed',
            candidate=candidate, job_id=job_id,
            error=f'{type(error).__name__}: {error}',
            bytes_received=budget_snapshot(run_root)['download_bytes'] - baseline,
            elapsed_seconds=time.monotonic() - started))
        raise
