"""Bounded, immutable acquisition of the approved MoGe-2 and MoGe-3 assets."""

import os
from pathlib import Path, PurePosixPath
import tarfile
import time

from .files import file_record, object_hash, read_json, verify_record, write_json


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def source_tree_records(source):
    """Bind every extracted file and reject added files, links or unsafe directories."""
    source = Path(source).resolve()
    records = []
    for parent, directories, files in os.walk(source):
        for name in directories:
            path = Path(parent) / name
            _require(name != 'prompts' and not path.is_symlink(),
                     'unsafe MoGe source directory')
        for name in files:
            path = Path(parent) / name
            _require(not path.is_symlink() and path.is_file(),
                     'unsafe MoGe source file')
            records.append((path.relative_to(source).as_posix(), file_record(path)))
    _require(bool(records) and len(records) <= 10000,
             'missing or oversized MoGe source tree')
    return [dict(relative_path=name, record=record) for name, record in sorted(records)]


def _acquire(url, path, *, max_bytes, deadline, run_root,
             download_limit, artifact_limit):
    from .budgets import budget_snapshot
    from .runtime import download
    _require(time.monotonic() < deadline, 'MoGe setup transfer deadline')
    already = budget_snapshot(run_root)['download_bytes']
    ceiling = min(download_limit, already + max_bytes)
    record = download(url, path, run_root / 'transfers', limit=ceiling,
        run_root=run_root, artifact_limit=artifact_limit)
    _require(record['bytes'] <= max_bytes and time.monotonic() < deadline,
             'MoGe setup transfer bound exceeded')
    return record


def _unpack_source(archive, output, revision, *, deadline):
    output.mkdir(exist_ok=False)
    with tarfile.open(archive, 'r:gz') as stream:
        members = stream.getmembers()
        _require(bool(members) and len(members) <= 10000,
                 'empty or oversized MoGe source archive')
        _require(sum(member.size for member in members if member.isfile()) <= 2**30,
                 'MoGe source extraction byte ceiling')
        roots = {PurePosixPath(member.name).parts[0] for member in members}
        _require(len(roots) == 1 and next(iter(roots)).endswith(revision),
                 'MoGe source archive revision root changed')
        for member in members:
            _require(time.monotonic() < deadline, 'MoGe source extraction deadline')
            parts = PurePosixPath(member.name).parts
            _require(all(part not in ('', '.', '..') for part in parts) and
                     not member.issym() and not member.islnk() and
                     (member.isdir() or member.isfile()),
                     'unsafe MoGe source archive member')
            if len(parts) == 1:
                continue
            destination = output.joinpath(*parts[1:])
            _require(destination.is_relative_to(output), 'MoGe source archive traversal')
            if member.isdir():
                destination.mkdir(parents=True, exist_ok=True)
            else:
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = stream.extractfile(member)
                if source is None:
                    raise ValueError('MoGe source archive file content missing')
                with source, destination.open('xb') as target:
                    while chunk := source.read(2**20):
                        _require(time.monotonic() < deadline,
                                 'MoGe source extraction deadline')
                        target.write(chunk)
    _require(all((output / name).is_file() for name in
                 ('moge/model/v2.py', 'moge/model/v3.py', 'pyproject.toml', 'LICENSE')),
             'pinned MoGe native source or license absent')


def _active_reservation(request, request_path, output):
    from .config import load
    from .ledger import Ledger
    _require(request_path is not None, 'actual setup requires saved request path')
    ledger_path = Path(request['ledger_path']).resolve()
    run_root = ledger_path.parent
    _require(output.resolve() == (run_root / 'jobs' / request['job_id']).resolve(),
             'actual MoGe setup output must be the reserved job directory')
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
             'active exact ledger MoGe setup reservation required')
    return run_root, config


def run_moge_setup(request, output, *, request_path=None, acquire=_acquire):
    """Acquire only the exact approved source/checkpoint for D5 or D6."""
    started = time.monotonic()
    candidate = request.get('candidate')
    environment = request.get('runtime_environment')
    if request.get('record_kind') == 'actual':
        _require(isinstance(environment, dict), 'reviewed MoGe runtime environment required')
    _require(candidate in ('D5', 'D6'), 'MoGe setup candidate must be D5 or D6')
    review = read_json(verify_record(request['review'])['path'])
    approved = read_json(verify_record(request['authorization'])['path'])
    proposal = next((row for row in review.get('proposals', [])
                     if row.get('candidate') == candidate), None)
    grant = next((row for row in approved.get('candidate_approvals', [])
                  if row.get('candidate') == candidate), None)
    job_id = f'plan069-{candidate}-setup-001'
    _require(request.get('schema') == 'plan069-depth-setup-request/v1' and
             request.get('job_id') == job_id and
             approved.get('review') == request['review'] and
             proposal is not None and grant is not None and
             grant.get('status') == 'approved' and
             grant.get('proposal_sha256') == object_hash(proposal),
             'exact approved MoGe setup request required')
    assert proposal is not None  # Guaranteed by the approved-request gate above.
    model = proposal['candidate_config']
    _require(model['code']['url'] == 'https://github.com/microsoft/MoGe' and
             model['code']['revision'] == '74fbce054ebed49800de42d0ad0e83495065719a' and
             model['weights']['url'] == f'https://huggingface.co/Ruicheng/moge-{2 if candidate == "D5" else 3}-vitl',
             'MoGe pinned source or weight repository changed')
    inventory = read_json(verify_record(proposal['required_assets'])['path'])
    assets = inventory['candidates'][candidate]['files']
    repository = 'moge2' if candidate == 'D5' else 'moge3'
    _require(len(assets) == 1 and assets[0]['repository'] == repository and
             assets[0]['path'] == 'model.pt' and assets[0]['lfs_sha256'],
             'MoGe required-only checkpoint changed')
    asset = assets[0]
    allocation = proposal['allocation']
    _require(allocation['setup_seconds'] == 1800 and
             allocation['download_bytes'] >= asset['bytes'],
             'MoGe setup bounds changed')
    deadline = started + allocation['setup_seconds']
    output = Path(output)
    if request.get('record_kind') == 'actual':
        run_root, config = _active_reservation(request, request_path, output)
    else:
        _require(request.get('record_kind') == 'fixture', 'MoGe setup origin required')
        run_root = output.parent
        config = dict(new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    _require(output.name == job_id and not output.exists(),
             'immutable MoGe setup output identity changed or exists')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    from .budgets import budget_snapshot
    baseline = budget_snapshot(run_root)['download_bytes']
    download_limit = min(config['new_download_gib_limit'] * 2**30,
                         baseline + allocation['download_bytes'])
    artifact_limit = config['new_artifact_disk_gib_limit'] * 2**30
    try:
        archive = output / 'source.tar.gz'
        source_url = ('https://codeload.github.com/microsoft/MoGe/tar.gz/' +
                      model['code']['revision'])
        source_result = acquire(source_url, archive, max_bytes=128 * 2**20,
            deadline=deadline, run_root=run_root, download_limit=download_limit,
            artifact_limit=artifact_limit)
        _require(source_result['bytes'] + asset['bytes'] <= allocation['download_bytes'],
                 'MoGe source plus checkpoint exceeds transfer allocation')
        _unpack_source(archive, output / 'source', model['code']['revision'],
                       deadline=deadline)
        runtime_result = None
        dependency_archives = []
        if environment is not None:
            from .moge_environment import validate_environment_request
            validate_environment_request(environment, output / 'source', candidate,
                                         request['record_kind'])
            for package in environment['sources']:
                path = output / 'dependency-sources' / (package['name'] + '.tar.gz')
                path.parent.mkdir(parents=True, exist_ok=True)
                record = acquire(package['url'], path, max_bytes=package['max_bytes'],
                    deadline=deadline, run_root=run_root, download_limit=download_limit,
                    artifact_limit=artifact_limit)
                dependency_archives.append(dict(name=package['name'], revision=package['revision'],
                    record=record, install_local_offline=True))
        checkpoint = output / asset['path']
        weight_url = (model['weights']['url'] + '/resolve/' +
                      model['weights']['revision'] + '/' + asset['path'])
        weight_result = acquire(weight_url, checkpoint, max_bytes=asset['bytes'],
            deadline=deadline, run_root=run_root, download_limit=download_limit,
            artifact_limit=artifact_limit)
        _require(weight_result['bytes'] == asset['bytes'] and
                 weight_result['sha256'] == asset['lfs_sha256'],
                 'MoGe checkpoint bytes differ from pinned LFS object')
        if environment is not None:
            from .depth_environment import provision_depth_environment
            runtime_request = dict(environment, sources=dependency_archives)
            if request['record_kind'] == 'actual':
                runtime_request.update(ledger_path=request['ledger_path'],
                    setup_request=file_record(request_path))
            runtime_result = provision_depth_environment(runtime_request, output / 'runtime', config,
                run_root=run_root, deadline=deadline, download_limit=download_limit,
                artifact_limit=artifact_limit)
        received = budget_snapshot(run_root)['download_bytes'] - baseline
        _require(received <= allocation['download_bytes'] and
                 time.monotonic() <= deadline, 'MoGe setup allocation exceeded')
        result = dict(schema='plan069-depth-setup-result/v1', status='complete',
            candidate=candidate, job_id=job_id,
            record_kind=request['record_kind'], review=request['review'],
            authorization=request['authorization'],
            source_revision=model['code']['revision'],
            weight_revision=model['weights']['revision'],
            source_archive=file_record(archive), checkpoint=file_record(checkpoint),
            source_dir=str(output / 'source'),
            source_tree=source_tree_records(output / 'source'), bytes_received=received,
            elapsed_seconds=time.monotonic() - started)
        if runtime_result is not None:
            runtime_path = output / 'runtime/result.json'
            _require(runtime_path.is_file() and read_json(runtime_path) == runtime_result and
                     runtime_result.get('status') == 'complete' and
                     runtime_result.get('candidate') == candidate, 'MoGe runtime receipt missing or incomplete')
            result['runtime_environment'] = file_record(runtime_path)
            result['python_executable'] = runtime_result['python_executable']
            result['dependency_sources'] = dependency_archives
        write_json(output / 'result.json', result)
        from .budgets import directory_bytes
        _require(directory_bytes(output) <= allocation.get('artifact_bytes', artifact_limit),
                 'MoGe setup exceeded candidate artifact allocation')
        return result
    except BaseException as error:
        received = budget_snapshot(run_root)['download_bytes'] - baseline
        write_json(output / 'failure.json', dict(
            schema='plan069-depth-setup-failure/v1', candidate=candidate,
            job_id=job_id, status='failed',
            error=f'{type(error).__name__}: {error}',
            bytes_received=received, elapsed_seconds=time.monotonic() - started))
        raise
