"""Explicit D9 recovery authority over immutable failed setup ancestry.

A failed attempt remains consumed. A separately approved recovery may reuse its
successful retained inputs, but no failed result can mint completed setup credit.
"""
from pathlib import Path

from .files import file_record, object_hash, read_json, verify_record


CANDIDATE = 'D9'
ORIGINAL_JOB = 'plan069-D9-setup-001'
JOB = 'plan069-D9-setup-recovery-001'
EVENT = 'depth_setup_recovery_authorized'


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _one(events, predicate, reason):
    selected = [row for row in events if predicate(row)]
    _require(len(selected) == 1, reason)
    return selected[0]


def original_setup_lineage(original, events, run_root, *, verifier=verify_record):
    """Validate the consumed failed attempt and every exact retained input."""
    root = Path(run_root).resolve()
    job = root / 'jobs' / ORIGINAL_JOB
    grant = _one(events, lambda row: row.get('event') == 'depth_setup_authorized' and
        row.get('candidate') == CANDIDATE, 'unique original D9 setup grant required')
    finish = _one(events, lambda row: row.get('event') == 'finish' and
        row.get('job_id') == ORIGINAL_JOB, 'unique consumed original setup finish required')
    reserve = _one(events, lambda row: row.get('event') == 'reserve' and
        row.get('job_id') == ORIGINAL_JOB, 'unique original setup reservation required')
    _require(original.get('grant_event_sha256') == grant['event_sha256'] and
             original.get('failed_finish_event_sha256') == finish['event_sha256'] and
             grant['sequence'] < reserve['sequence'] < finish['sequence'] and
             reserve.get('resource') == finish.get('resource') == 'setup' and
             finish.get('status') == 'failed' and finish.get('cleanup_confirmed') is True and
             finish.get('cleanup_uncertain') is False and finish.get('surviving_pids') == [] and
             finish.get('deadline_exceeded') is False,
             'exact consumed failed setup with confirmed cleanup required')
    _require(original.get('byte_checkpoint') == grant.get('byte_checkpoint') and
             original.get('request') == reserve.get('evidence', {}).get('request'),
             'recovery must retain original protected checkpoint and request')
    checkpoint_record = original['byte_checkpoint']
    _require(verifier(checkpoint_record) == checkpoint_record and
             Path(checkpoint_record['path']) == root / 'prepare' /
             'plan069-D9-setup-byte-checkpoint.json', 'owned original prospective byte checkpoint required')
    checkpoint = read_json(checkpoint_record['path'])
    _require(checkpoint.get('schema') == 'plan069-depth-setup-byte-checkpoint/v1' and
             checkpoint.get('candidate') == CANDIDATE and
             checkpoint.get('resource_snapshot') == grant.get('resource_snapshot'),
             'original byte checkpoint differs from consumed grant')
    request_record = original['request']
    _require(verifier(request_record) == request_record and
             Path(request_record['path']) == root / 'requests' / (ORIGINAL_JOB + '.json'),
             'owned original setup request required')
    request = read_json(request_record['path'])
    _require(request.get('schema') == 'plan069-depth-setup-request/v1' and
             request.get('record_kind') == 'actual' and request.get('candidate') == CANDIDATE and
             request.get('job_id') == ORIGINAL_JOB and request.get('ledger_path') == str(root / 'ledger.jsonl') and
             request.get('review') == grant['review'] and request.get('authorization') == grant['authorization'],
             'original setup request approval binding changed')
    review = read_json(verifier(grant['review'])['path'])
    proposals = [row for row in review.get('proposals', []) if row.get('candidate') == CANDIDATE]
    _require(len(proposals) == 1 and object_hash(proposals[0]) == grant['proposal_sha256'],
             'exact original approved D9 proposal required')
    proposal = proposals[0]
    approval = read_json(verifier(grant['authorization'])['path'])
    _require(approval.get('status') == 'DO' and approval.get('review') == grant['review'] and
             any(row.get('candidate') == CANDIDATE and row.get('status') == 'approved' and
                 row.get('max_attempts') == 1 and row.get('proposal_sha256') == object_hash(proposal)
                 for row in approval.get('candidate_approvals', [])),
             'original setup explicit approval required')
    rows = [original[key] for key in ('source_archive', 'checkpoint', 'runtime_failure', 'dependency_lock')]
    source_files = original.get('source_files')
    _require(isinstance(source_files, list) and bool(source_files), 'exact original source files required')
    rows.extend(source_files)
    _require(len({row['path'] for row in rows}) == len(rows), 'duplicate original retained input')
    for row in rows:
        path = Path(row['path'])
        _require(path.is_relative_to(job) and not path.is_symlink() and verifier(row) == row,
                 'unchanged retained original owned input required')
    _require(Path(original['source_archive']['path']) == job / 'source.tar.gz' and
             Path(original['runtime_failure']['path']) == job / 'runtime/failure.json' and
             Path(original['dependency_lock']['path']) == job / 'runtime/requirements.lock' and
             all(Path(row['path']).is_relative_to(job / 'source') for row in source_files),
             'exact original input roles required')
    failure = read_json(original['runtime_failure']['path'])
    _require(failure.get('schema') == 'plan069-depth-environment-failure/v1' and
             failure.get('status') == 'failed' and failure.get('candidate') == CANDIDATE and
             isinstance(failure.get('command_receipts'), list), 'exact original failed runtime receipt required')
    for record in failure['command_receipts']:
        _require(Path(record['path']).is_relative_to(job / 'runtime/commands') and verifier(record) == record,
                 'unchanged original runtime command required')
        command = read_json(record['path'])
        if command.get('uv_transfer_receipt') is not None:
            from .transfer_proxy import completed_uv_receipt
            receipt = command['uv_transfer_receipt']
            _require(verifier(receipt) == receipt, 'original completed UV receipt changed')
            session = read_json(receipt['path'])
            _require(command.get('record_kind') == 'actual' and command.get('error') is None and
                     command.get('package_transfer_proxy') is True and
                     Path(receipt['path']) == completed_uv_receipt(root, session['transfer_id']),
                     'only successful original owned UV reads can be retained')
    required = read_json(verifier(proposal['required_assets'])['path'])['candidates'][CANDIDATE]['files']
    _require(len(required) == 1 and required[0]['bytes'] == original['checkpoint']['bytes'] and
             required[0].get('lfs_sha256') == original['checkpoint']['sha256'],
             'original retained checkpoint differs from approved model')
    return dict(grant=grant, reserve=reserve, finish=finish, proposal=proposal,
                checkpoint=checkpoint, original=original, failure=failure)


def validate_recovery_request(request_record, events, run_root, *, require_reservation=False,
                              verifier=verify_record):
    """Validate reviewed recovery and explicit fresh DO, without dispatch."""
    root = Path(run_root).resolve()
    _require(verifier(request_record) == request_record and
             Path(request_record['path']) == root / 'requests' / (JOB + '.json'),
             'exact owned recovery request required')
    request = read_json(request_record['path'])
    _require(request.get('schema') == 'plan069-video-setup-recovery-request/v1' and
             request.get('record_kind') == 'actual' and request.get('candidate') == CANDIDATE and
             request.get('job_id') == JOB and request.get('ledger_path') == str(root / 'ledger.jsonl'),
             'exact actual D9 recovery request required')
    review_record, authorization_record = request['review'], request['authorization']
    review = read_json(verifier(review_record)['path'])
    approval = read_json(verifier(authorization_record)['path'])
    proposal = review.get('setup_recovery_proposal')
    _require(review.get('schema') == 'plan069-depth-execution-review/v1' and
             review.get('status') == 'REVIEW' and isinstance(proposal, dict) and
             proposal.get('schema') == 'plan069-video-setup-recovery-proposal/v1' and
             proposal.get('candidate') == CANDIDATE and proposal.get('job_id') == JOB and
             proposal.get('max_attempts') == 1 and
             approval.get('schema') == 'plan069-depth-user-authorization/v1' and
             approval.get('status') == 'DO' and approval.get('review') == review_record and
             approval.get('setup_recovery_approval') == dict(candidate=CANDIDATE,job_id=JOB,
                 status='approved',max_attempts=1,proposal_sha256=object_hash(proposal)),
             'explicit separately approved one-attempt recovery required')
    maps = [row for row in review.get('proposals', []) if row.get('candidate') == CANDIDATE]
    _require(len(maps) == 1 and proposal.get('map_proposal_sha256') == object_hash(maps[0]) and
             any(row.get('candidate') == CANDIDATE and row.get('status') == 'approved' and
                 row.get('max_attempts') == 1 and row.get('proposal_sha256') == object_hash(maps[0])
                 for row in approval.get('candidate_approvals', [])),
             'updated runtime map proposal must be explicitly approved')
    map_proposal = maps[0]
    _require(request.get('original_setup') == proposal.get('original_setup'),
             'recovery request changed reviewed original ancestry')
    lineage = original_setup_lineage(proposal['original_setup'], events, root, verifier=verifier)
    original = lineage['proposal']
    _require(map_proposal.get('candidate_config') == original.get('candidate_config') and
             map_proposal.get('allocation') == original.get('allocation') and
             map_proposal.get('max_attempts') == 1 and
             map_proposal.get('required_assets') == original.get('required_assets') and
             proposal.get('runtime_recipe') == map_proposal.get('runtime_recipe') and
             proposal.get('profile_inventory') == map_proposal.get('profile_inventory'),
             'recovery changed scientific settings or combined approved caps')
    seconds = proposal.get('recovery_seconds')
    elapsed = lineage['finish'].get('elapsed_seconds')
    _require(type(seconds) is int and seconds > 0 and type(elapsed) in (int, float) and
             elapsed >= 0 and elapsed + seconds <= original['allocation']['setup_seconds'],
             'recovery setup time must fit original remaining candidate allowance')
    source_record = request['source_review']
    source = read_json(verifier(source_record)['path'])
    from .depth_admission import local_source_records, selected_profile_inventory
    _require(source.get('schema') == 'plan069-depth-source-review/v1' and
             source.get('status') == 'passed' and source.get('candidate') == CANDIDATE and
             source.get('proposal_sha256') == object_hash(map_proposal) and
             source.get('setup_recovery_proposal_sha256') == object_hash(proposal) and
             source.get('local_sources') == local_source_records(CANDIDATE),
             'current independently reviewed recovery source closure required')
    selected_profile_inventory(map_proposal)
    from .video_environment import FRAME_RECIPE
    from .depth_admission import VIDEO_FRAME_PROFILES
    _require(map_proposal.get('runtime_recipe') == file_record(FRAME_RECIPE) and
             map_proposal.get('profile_inventory') == file_record(VIDEO_FRAME_PROFILES),
             'recovery requires reviewed frame-input v4 exception')
    environment = request.get('runtime_environment')
    _require(isinstance(environment, dict) and environment.get('recipe') == proposal['runtime_recipe'] and
             environment.get('runtime_profile') == map_proposal['profile'].get('runtime_profile') and
             environment.get('candidate') == CANDIDATE and environment.get('record_kind') == 'actual',
             'exact reviewed new recovery environment required')
    grants = [row for row in events if row.get('event') == EVENT]
    if require_reservation:
        _require(len(grants) == 1, 'exact checked recovery grant required')
        grant = grants[0]
        reserve = _one(events, lambda row: row.get('event') == 'reserve' and row.get('job_id') == JOB,
                       'exact active recovery reservation required')
        _require(grant.get('request') == request_record and grant.get('proposal_sha256') == object_hash(proposal) and
                 reserve.get('resource') == 'setup' and reserve.get('evidence', {}).get('request') == request_record and
                 grant['sequence'] < reserve['sequence'] and
                 not any(row.get('event') == 'finish' and row.get('job_id') == JOB for row in events) and
                 not any(row.get('event') == 'reserve' and row.get('job_id') != JOB and
                     not any(end.get('event') in ('finish','account') and end.get('job_id') == row['job_id']
                         and end['sequence'] > row['sequence'] for end in events) for row in events),
                 'live exact recovery reservation required before any environment work')
    from .config import load
    config = dict(load(),new_download_gib_limit=110,new_artifact_disk_gib_limit=210)
    limits = {key:min(lineage['grant']['resource_snapshot'][key] + original['allocation'][key],
                     config[cap]*2**30) for key,cap in
              (('download_bytes','new_download_gib_limit'),('artifact_bytes','new_artifact_disk_gib_limit'))}
    return dict(proposal=proposal,map_proposal=map_proposal,original=proposal['original_setup'],
        lineage=lineage,runtime_environment=environment,request=request_record,
        allocation=dict(original['allocation'],setup_seconds=seconds),byte_limits=limits,config=config,
        resource_snapshot=grants[0]['resource_snapshot'] if require_reservation else None,
        review=review_record,authorization=authorization_record,source_review=source_record)
