"""User-approved D6 (MoGe-3) runtime replacement over its completed but unusable setup.

The accepted original setup completed, but its torch 2.6.0 / Triton 3.2.0 runtime cannot compile
flex_gemm's kernels (Triton ``dtype.itemsize``); D6 maps-001 failed cleanly with no maps. One
separately approved recovery job (a later attempt only after a clean failed earlier one) keeps the reviewed MoGe source, checkpoint and derived FlexGEMM
archive (source and checkpoint hard-linked; the derived archive installed in place, so no new bytes) and provisions a new runtime offline from the run's own
package cache with torch 2.14.1+cu130 / Triton 3.8.0. It makes no network transfer; uv's own local
cache metadata (bounded, recorded) is the only cache growth it tolerates. The original setup,
its runtime and every consumed attempt stay preserved.
"""
import os
from pathlib import Path
import time

from .config import ROOT
from .files import file_record, object_hash, read_json, verify_record, write_json
from .setup_recovery_core import RECOVERY_CANDIDATES, RECOVERY_EVENT, completed_recovery

CANDIDATE = 'D6'
ORIGINAL_JOB = RECOVERY_CANDIDATES[CANDIDATE]['original_job']
JOBS = RECOVERY_CANDIDATES[CANDIDATE]['jobs']
JOB = JOBS[-1]  # The current attempt; earlier attempts are consumed failures.
EVENT = RECOVERY_EVENT
RESULT_SCHEMA = RECOVERY_CANDIDATES[CANDIDATE]['result_schemas'][JOB]
# uv writes interpreter metadata into the package cache even offline; the run's download metric counts
# cache growth, so a small recorded allowance separates it from any (forbidden) network transfer.
CACHE_METADATA_ALLOWANCE = 2**20
PROPOSAL_SCHEMA = 'plan069-depth-setup-recovery-proposal/v1'
REQUEST_SCHEMA = 'plan069-depth-setup-recovery-request/v1'
KIND = 'runtime_replacement'
RECOVERY_SECONDS = 900
FAILED_MAPS_JOB = 'plan069-D6-maps-001'
CONSTRAINTS = ('torch==2.14.1+cu130', 'torchvision==0.29.1+cu130', 'triton==3.8.0', 'numpy==2.1.3')
INDEXES = ('https://pypi.org/simple', 'https://download.pytorch.org/whl/cu130',
           'https://download.pytorch.org/whl/cu124')
AUTHORITY = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-D6-runtime-replacement-authority-001.json'


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def replacement_recipe(original_recipe, run_root, job=JOB):
    """The original reviewed recipe with only the runtime pins, indexes and owned cache replaced."""
    from .moge_source_build import cache_path
    return dict(original_recipe, constraints=list(CONSTRAINTS), indexes=list(INDEXES),
                flex_cache_path=str(cache_path(Path(run_root).resolve() / 'jobs' / job / 'runtime')))


def _cache_inventory(run_root):
    """Regular files under the run package cache, by path, with their sizes."""
    root = Path(run_root) / 'setup-cache'
    files = {}
    for parent, _, names in os.walk(root, followlinks=False):
        for name in names:
            path = Path(parent) / name
            if not path.is_symlink() and path.is_file():
                files[str(path.relative_to(root))] = path.stat().st_size
    return files


def _metadata_growth(before, after):
    """Cache files added or grown during provisioning; only uv interpreter metadata is tolerated."""
    grown = {path: size for path, size in after.items() if before.get(path) != size}
    _require(all(path.startswith('interpreter-v4/') for path in grown) and
             sum(grown.values()) <= CACHE_METADATA_ALLOWANCE,
             'offline runtime replacement grew the package cache beyond uv interpreter metadata')
    return sorted(grown)


def _previous_attempts(job, proposal, events):
    """Every earlier attempt must be a consumed, cleanly failed recovery named by the proposal."""
    from .setup_recovery_core import failed_setup_ancestry
    earlier = JOBS[:JOBS.index(job)]
    descriptors = proposal.get('failed_recoveries', [])
    _require(isinstance(descriptors, list) and [row.get('job_id') for row in descriptors] == list(earlier),
             'exact earlier failed runtime replacement attempts required')
    for descriptor in descriptors:
        failed_setup_ancestry(CANDIDATE, descriptor['job_id'], events, descriptor)
    return descriptors


def _failed_attempts_preserved(root, descriptors, events):
    """Failed attempts keep their failure evidence, never a result, and consume setup seconds."""
    used = 0.
    for descriptor in descriptors:
        attempt = root / 'jobs' / descriptor['job_id']
        _require(not (attempt / 'result.json').exists() and
                 ((attempt / 'failure.json').is_file() or (attempt / 'runtime/failure.json').is_file()),
                 'failed runtime replacement attempt must stay a preserved failure')
        used += next(row['elapsed_seconds'] for row in events if row.get('event') == 'finish' and
                     row.get('job_id') == descriptor['job_id'])
    return used


def original_setup_lineage(original, events, run_root, *, verifier=verify_record):
    """Validate the completed accepted original setup and the clean failed maps attempt it motivates."""
    from .setup_recovery_core import accepted_setup
    root = Path(run_root).resolve()
    setup_record = original.get('setup')
    _require(isinstance(setup_record, dict) and Path(setup_record['path']) == root / 'jobs' / ORIGINAL_JOB / 'result.json',
             'exact accepted original D6 setup required')
    setup, job_id = accepted_setup(CANDIDATE, setup_record, events, root, verifier=verifier)
    _require(job_id == ORIGINAL_JOB and setup.get('schema') == 'plan069-depth-setup-result/v1' and
             setup.get('status') == 'complete' and setup.get('record_kind') == 'actual' and
             setup.get('candidate') == CANDIDATE, 'accepted completed original D6 setup required')
    grants = [row for row in events if row.get('event') == 'depth_setup_authorized' and row.get('candidate') == CANDIDATE]
    reserves = [row for row in events if row.get('event') == 'reserve' and row.get('job_id') == ORIGINAL_JOB]
    finishes = [row for row in events if row.get('event') == 'finish' and row.get('job_id') == ORIGINAL_JOB]
    _require(len(grants) == len(reserves) == len(finishes) == 1 and
             finishes[0]['event_sha256'] == original.get('setup_finish_event_sha256'),
             'exact original D6 setup ledger lineage required')
    request_record = original.get('request')
    _require(request_record == reserves[0].get('evidence', {}).get('request') and
             verifier(request_record) == request_record, 'exact original D6 setup request required')
    request = read_json(request_record['path'])
    _require(request.get('job_id') == ORIGINAL_JOB and request.get('candidate') == CANDIDATE and
             isinstance(request.get('runtime_environment'), dict), 'original reviewed D6 runtime recipe required')
    for key in ('source_archive', 'checkpoint', 'runtime_environment'):
        _require(verifier(setup[key]) == setup[key], 'retained original setup evidence changed: ' + key)
    for row in setup.get('dependency_sources', []):
        _require(verifier(row['record']) == row['record'], 'retained original dependency source changed')
    maps_failure = original.get('maps_failure')
    finish = [row for row in events if row.get('event') == 'finish' and row.get('job_id') == FAILED_MAPS_JOB]
    maps_job = root / 'jobs' / FAILED_MAPS_JOB
    _require(isinstance(maps_failure, dict) and len(finish) == 1 and
             finish[0]['event_sha256'] == maps_failure.get('finish_event_sha256') and
             finish[0].get('status') == 'failed' and finish[0].get('failure_kind') == 'worker_failure' and
             finish[0].get('resource') == 'gpu' and finish[0].get('cleanup_confirmed') is True and
             finish[0].get('cleanup_uncertain') is False and finish[0].get('deadline_exceeded') is False and
             finish[0].get('surviving_pids') == [] and
             Path(maps_failure['failure']['path']) == maps_job / 'failure.json' and
             verifier(maps_failure['failure']) == maps_failure['failure'] and
             not (maps_job / 'result.json').exists() and
             read_json(maps_failure['failure']['path']).get('completed_map_rows') == 0,
             'the clean zero-output failed D6 maps attempt must motivate the replacement')
    review = read_json(verifier(grants[0]['review'])['path'])
    proposals = [row for row in review.get('proposals', []) if row.get('candidate') == CANDIDATE]
    _require(len(proposals) == 1 and object_hash(proposals[0]) == grants[0].get('proposal_sha256'),
             'exact original approved D6 proposal required')
    return dict(grant=grants[0], reserve=reserves[0], finish=finishes[0], proposal=proposals[0],
                original=original, setup=setup, request=request)


def validate_recovery_request(request_record, events, run_root, *, require_reservation=False,
                              verifier=verify_record, historical=False):
    """Validate the reviewed D6 runtime replacement and its explicit DO, without dispatch."""
    root = Path(run_root).resolve()
    _require(verifier(request_record) == request_record, 'exact unchanged recovery request required')
    request = read_json(request_record['path'])
    job = request.get('job_id')
    _require(job in JOBS and Path(request_record['path']) == root / 'requests' / (job + '.json') and
             request.get('schema') == REQUEST_SCHEMA and request.get('record_kind') == 'actual' and
             request.get('candidate') == CANDIDATE and request.get('ledger_path') == str(root / 'ledger.jsonl'),
             'exact actual owned D6 runtime replacement request required')
    review_record, authorization_record = request['review'], request['authorization']
    review = read_json(verifier(review_record)['path'])
    approval = read_json(verifier(authorization_record)['path'])
    proposal = review.get('setup_recovery_proposal')
    authority = file_record(AUTHORITY)
    _require(review.get('schema') == 'plan069-depth-execution-review/v1' and review.get('status') == 'REVIEW' and
             isinstance(proposal, dict) and proposal.get('schema') == PROPOSAL_SCHEMA and
             proposal.get('kind') == KIND and proposal.get('candidate') == CANDIDATE and
             proposal.get('job_id') == job and proposal.get('max_attempts') == 1 and
             proposal.get('downloads') == 0 and proposal.get('user_authority') == authority and
             approval.get('schema') == 'plan069-depth-user-authorization/v1' and
             approval.get('status') == 'DO' and approval.get('review') == review_record and
             approval.get(RECOVERY_CANDIDATES[CANDIDATE]['approval_field']) == dict(
                 candidate=CANDIDATE, job_id=job, status='approved', max_attempts=1,
                 proposal_sha256=object_hash(proposal)),
             'explicit separately approved one-attempt D6 runtime replacement required')
    failed_recoveries = _previous_attempts(job, proposal, events)
    _require(request.get('original_setup') == proposal.get('original_setup'),
             'recovery request changed reviewed original ancestry')
    lineage = original_setup_lineage(proposal['original_setup'], events, root, verifier=verifier)
    map_proposal = lineage['proposal']
    _require(proposal.get('map_proposal_sha256') == object_hash(map_proposal),
             'recovery must keep the original approved D6 map proposal')
    seconds = proposal.get('recovery_seconds')
    elapsed = lineage['finish'].get('elapsed_seconds')
    earlier = _failed_attempts_preserved(root, failed_recoveries, events)
    _require(type(seconds) is int and seconds == RECOVERY_SECONDS and type(elapsed) in (int, float) and
             0 <= elapsed and elapsed + earlier + seconds <= map_proposal['allocation']['setup_seconds'],
             'runtime replacement must fit the original remaining setup allowance')
    recipe = replacement_recipe(lineage['request']['runtime_environment'], root, job)
    _require(request.get('runtime_environment') == proposal.get('runtime_recipe') == recipe,
             'exact reviewed replacement runtime recipe required')
    source_record = request['source_review']
    source = read_json(verifier(source_record)['path'])
    from .depth_admission import local_source_records
    _require(source.get('schema') == 'plan069-depth-source-review/v1' and source.get('status') == 'passed' and
             source.get('candidate') == CANDIDATE and
             source.get('setup_recovery_proposal_sha256') == object_hash(proposal) and
             (historical or source.get('local_sources') == local_source_records(CANDIDATE)),
             'current independently reviewed recovery source closure required')
    grants = [row for row in events if row.get('event') == EVENT and row.get('job_id') == job]
    if require_reservation:
        _require(len(grants) == 1 and grants[0].get('request') == request_record, 'exact checked recovery grant required')
    from .config import load
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    # Offline: the job itself forbids every new transfer; the shared caps bound the reservation.
    limits = {key: config[cap] * 2**30 for key, cap in (('download_bytes', 'new_download_gib_limit'),
                                                         ('artifact_bytes', 'new_artifact_disk_gib_limit'))}
    return dict(job_id=job, proposal=proposal, map_proposal=map_proposal, original=proposal['original_setup'],
                failed_recoveries=failed_recoveries,
                lineage=lineage, runtime_environment=recipe, request=request_record,
                allocation=dict(map_proposal['allocation'], setup_seconds=seconds), byte_limits=limits,
                config=config, review=review_record, authorization=authorization_record, source_review=source_record)


def accepted_setup_lineage(setup_record, events, run_root, *, verifier=verify_record):
    """Validate the clean completed D6 runtime replacement and its immutable bindings."""
    root = Path(run_root).resolve()
    job = Path(setup_record['path']).parent.name
    _require(job in JOBS and Path(setup_record['path']) == root / 'jobs' / job / 'result.json' and
             verifier(setup_record) == setup_record, 'owned accepted recovery result required')
    result = read_json(setup_record['path'])
    completion = completed_recovery(CANDIDATE, job, setup_record, events)
    grant, reserve, finish = completion['grant'], completion['reserve'], completion['finish']
    request_record = result.get('request')
    _require(request_record == grant.get('request') == reserve.get('evidence', {}).get('request'),
             'exact completed recovery request binding required')
    normalized = validate_recovery_request(request_record, events, root, verifier=verifier, historical=True)
    for key in ('review', 'authorization', 'source_review'):
        _require(grant.get(key) == normalized[key], 'completed recovery approval binding changed: ' + key)
    validate_recovery_result(result, normalized)
    return dict(normalized, accepted_result=result, setup=setup_record, grant=grant, reserve=reserve,
                finish=finish, job=job)


def validate_recovery_result(result, normalized):
    """Require the replacement result to keep the original sources, model and accounting."""
    from .moge_setup import source_tree_records
    original = normalized['lineage']['setup']
    proposal = normalized['map_proposal']
    _require(result.get('schema') == RECOVERY_CANDIDATES[CANDIDATE]['result_schemas'].get(normalized['job_id']) and
             result.get('record_kind') == 'actual' and
             result.get('status') == 'complete' and result.get('candidate') == CANDIDATE and
             result.get('job_id') == normalized['job_id'] and result.get('kind') == KIND and
             result.get('request') == normalized['request'] and
             all(result.get(key) == normalized[key] for key in ('review', 'authorization', 'source_review')),
             'runtime replacement result differs from its reviewed request')
    tree = result.get('source_tree')
    _require(result.get('original_setup') == normalized['original'] and
             result.get('source_archive') == original['source_archive'] and
             result.get('dependency_sources') == original.get('dependency_sources') and
             result.get('source_revision') == original['source_revision'] ==
                 proposal['candidate_config']['code']['revision'] and
             result.get('weight_revision') == original['weight_revision'] ==
                 proposal['candidate_config']['weights']['revision'] and
             isinstance(tree, list) and
             [(r['relative_path'], r['record']['sha256'], r['record']['bytes']) for r in tree] ==
                 [(r['relative_path'], r['record']['sha256'], r['record']['bytes']) for r in original['source_tree']] and
             Path(result.get('source_dir', '')) == Path(normalized['request']['path']).parents[1] / 'jobs' / normalized['job_id'] / 'source' and
             source_tree_records(result['source_dir']) == tree and
             result.get('checkpoint', {}).get('sha256') == original['checkpoint']['sha256'] and
             result.get('checkpoint', {}).get('bytes') == original['checkpoint']['bytes'] and
             result.get('bytes_received') == original['bytes_received'] and result.get('new_bytes_received') == 0 and
             type(result.get('cache_metadata_bytes')) is int and 0 <= result['cache_metadata_bytes'] <= CACHE_METADATA_ALLOWANCE and
             result.get('original_setup_preserved') is True and result.get('automatic_retries') == 0,
             'runtime replacement changed original sources, model or accounting')
    job = Path(normalized['request']['path']).parents[1] / 'jobs' / normalized['job_id']
    _require(Path(result['checkpoint']['path']) == job / 'model.pt' and
             Path(result['runtime_environment']['path']) == job / 'runtime/result.json' and
             result.get('python_executable') == str(job / 'runtime/environment/bin/python'),
             'runtime replacement outputs escaped the owned recovery job')
    runtime = read_json(verify_record(result['runtime_environment'])['path'])
    _require(Path(verify_record(result['runtime_request'])['path']) == job / 'runtime/request.json',
             'hash-bound provisioned runtime request required')
    provisioned = read_json(result['runtime_request']['path'])
    _require(provisioned.get('constraints') == list(CONSTRAINTS) and provisioned.get('indexes') == list(INDEXES) and
             provisioned.get('requirements') == normalized['runtime_environment']['requirements'],
             'provisioned runtime request differs from the reviewed replacement pins')
    _require(runtime.get('status') == 'complete' and runtime.get('candidate') == CANDIDATE and
             runtime.get('python_executable') == result.get('python_executable') and
             runtime.get('source_packages') == original.get('dependency_sources') and
             runtime.get('flex_cache_path') == normalized['runtime_environment']['flex_cache_path'],
             'replacement runtime receipt differs from its reviewed recipe')


def _link_tree(original, output):
    """Hard-link the reviewed source tree; no byte is copied or modified."""
    source = Path(original['source_dir']).resolve()
    for row in original['source_tree']:
        target = output / row['relative_path']
        target.parent.mkdir(parents=True, exist_ok=True)
        _require(verify_record(row['record'])['path'] == str(source / row['relative_path']),
                 'original source tree record escaped its setup')
        os.link(row['record']['path'], target)


def run_runtime_replacement(request, output, *, request_path):
    """Provision the approved replacement runtime offline under the active reservation."""
    from .budgets import budget_snapshot
    from .depth_environment import provision_depth_environment
    from .ledger import Ledger
    from .moge_setup import _active_reservation, source_tree_records
    started = time.monotonic()
    output = Path(output)
    _require(request.get('record_kind') == 'actual' and request.get('candidate') == CANDIDATE and
             request.get('job_id') in JOBS, 'actual explicitly reserved D6 runtime replacement required')
    job = request['job_id']
    run_root, config = _active_reservation(request, request_path, output)
    _require(output.name == job and not output.exists() and not output.is_symlink(),
             'immutable recovery output identity changed or exists')
    events = Ledger(run_root / 'ledger.jsonl', config).events()
    normalized = validate_recovery_request(file_record(request_path), events, run_root, require_reservation=True)
    original = normalized['lineage']['setup']
    deadline = started + normalized['allocation']['setup_seconds']
    output.mkdir(parents=True, exist_ok=False)
    baseline = None
    try:
        write_json(output / 'request.json', request)
        from .budgets import _snapshot
        before = _snapshot(run_root)
        cache_before = _cache_inventory(run_root)
        baseline = before['download_bytes']
        _link_tree(original, output / 'source')
        tree = source_tree_records(output / 'source')
        checkpoint = output / 'model.pt'
        os.link(verify_record(original['checkpoint'])['path'], checkpoint)
        runtime_request = dict(normalized['runtime_environment'], sources=original['dependency_sources'],
                               ledger_path=request['ledger_path'], setup_request=file_record(request_path))
        runtime = provision_depth_environment(runtime_request, output / 'runtime', config, run_root=run_root,
            deadline=deadline, download_limit=baseline + CACHE_METADATA_ALLOWANCE,
            artifact_limit=config['new_artifact_disk_gib_limit'] * 2**30, offline=True)
        after = _snapshot(run_root)
        transferred = {key: after[key] - before[key] for key in ('direct_download_bytes', 'uv_metered_bytes')}
        metadata = after['download_bytes'] - baseline
        _require(transferred == dict(direct_download_bytes=0, uv_metered_bytes=0) and
                 0 <= metadata <= CACHE_METADATA_ALLOWANCE and time.monotonic() <= deadline,
                 'offline runtime replacement transferred bytes')
        metadata_files = _metadata_growth(cache_before, _cache_inventory(run_root))
        received = 0
        from .depth_map_allowance import owned_slot_bytes, slot_allocation
        owned = owned_slot_bytes(run_root, CANDIDATE, recovery_lineage=dict(job_id=job, failed_recoveries=normalized['failed_recoveries']))
        _require(owned <= slot_allocation(normalized['map_proposal'])['artifact_bytes'],
                 'runtime replacement exceeds the amended D6 whole-slot artifact allocation')
        result = dict(schema=RECOVERY_CANDIDATES[CANDIDATE]['result_schemas'][job], status='complete', kind=KIND,
            candidate=CANDIDATE, job_id=job,
            record_kind='actual', request=file_record(request_path), review=normalized['review'],
            authorization=normalized['authorization'], source_review=normalized['source_review'],
            original_setup=normalized['original'], source_revision=original['source_revision'],
            weight_revision=original['weight_revision'], source_archive=original['source_archive'],
            source_dir=str(output / 'source'), source_tree=tree, checkpoint=file_record(checkpoint),
            dependency_sources=original['dependency_sources'], runtime_environment=file_record(output / 'runtime/result.json'),
            runtime_request=file_record(output / 'runtime/request.json'),
            python_executable=runtime['python_executable'], bytes_received=original['bytes_received'],
            new_bytes_received=received, cache_metadata_bytes=metadata, cache_metadata_files=metadata_files, original_setup_preserved=True, automatic_retries=0,
            elapsed_seconds=time.monotonic() - started)
        write_json(output / 'result.json', result)
        validate_recovery_result(result, normalized)
        return result
    except BaseException as error:
        try:
            received = None if baseline is None else budget_snapshot(run_root)['download_bytes'] - baseline
        except Exception:
            received = None  # Never let accounting hide the original failure.
        write_json(output / 'failure.json', dict(schema='plan069-depth-setup-recovery-failure/v1',
            candidate=CANDIDATE, job_id=job, status='failed', record_kind='actual', kind=KIND,
            error=f'{type(error).__name__}: {error}', original_setup=normalized['original'],
            new_bytes_received=received, automatic_retries=0, elapsed_seconds=time.monotonic() - started))
        raise
