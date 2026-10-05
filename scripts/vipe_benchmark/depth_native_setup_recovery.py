"""Explicit native-depth (D8) setup recovery authority over its failed setup ancestry.

The failed original setup stays consumed. A separately approved recovery reuses
its retained source archives and package cache, acquires only the approved model
checkpoint plus an exact wheel allowlist, and installs the amended lock.
"""
from pathlib import Path

from .files import object_hash, read_json, verify_record
from .setup_recovery_core import RECOVERY_CANDIDATES, RECOVERY_EVENT, failed_setup_ancestry

CANDIDATE = 'D8'
ORIGINAL_JOB = RECOVERY_CANDIDATES[CANDIDATE]['original_job']
JOBS = RECOVERY_CANDIDATES[CANDIDATE]['jobs']
(JOB,) = JOBS
EVENT = RECOVERY_EVENT
RETAINED = dict(source_archive='source.tar.gz', utils3d_archive='utils3d-source.tar.gz',
                setup_failure='failure.json', runtime_failure='runtime/failure.json',
                dependency_lock='runtime/requirements.lock')


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def original_setup_lineage(original, events, run_root, *, verifier=verify_record):
    """Validate the consumed failed native setup and every retained input it names."""
    root = Path(run_root).resolve()
    job = root / 'jobs' / ORIGINAL_JOB
    ancestry = failed_setup_ancestry(CANDIDATE, ORIGINAL_JOB, events, original)
    grant, reserve, finish = ancestry['grant'], ancestry['reserve'], ancestry['finish']
    request_record = original.get('request')
    _require(isinstance(request_record, dict) and
             request_record == reserve.get('evidence', {}).get('request') and
             verifier(request_record) == request_record and
             Path(request_record['path']) == root / 'requests' / (ORIGINAL_JOB + '.json'),
             'recovery must retain the original owned setup request')
    request = read_json(request_record['path'])
    _require(request.get('schema') == 'plan069-depth-setup-request/v1' and
             request.get('record_kind') == 'actual' and request.get('candidate') == CANDIDATE and
             request.get('job_id') == ORIGINAL_JOB and request.get('ledger_path') == str(root / 'ledger.jsonl') and
             request.get('review') == grant.get('review') and
             request.get('authorization') == grant.get('authorization'),
             'original setup request approval binding changed')
    review = read_json(verifier(grant['review'])['path'])
    proposals = [row for row in review.get('proposals', []) if row.get('candidate') == CANDIDATE]
    _require(len(proposals) == 1 and object_hash(proposals[0]) == grant.get('proposal_sha256'),
             'exact original approved D8 proposal required')
    proposal = proposals[0]
    approval = read_json(verifier(grant['authorization'])['path'])
    _require(approval.get('status') == 'DO' and approval.get('review') == grant['review'] and
             any(row.get('candidate') == CANDIDATE and row.get('status') == 'approved' and
                 row.get('max_attempts') == 1 and row.get('proposal_sha256') == object_hash(proposal)
                 for row in approval.get('candidate_approvals', [])),
             'original setup explicit approval required')
    for key, name in RETAINED.items():
        record = original.get(key)
        _require(isinstance(record, dict) and Path(record['path']) == job / name and
                 not Path(record['path']).is_symlink() and verifier(record) == record,
                 'unchanged retained original owned input required: ' + key)
    setup_failure = read_json(original['setup_failure']['path'])
    runtime_failure = read_json(original['runtime_failure']['path'])
    _require(setup_failure.get('schema') == 'plan069-depth-setup-failure/v1' and
             setup_failure.get('candidate') == CANDIDATE and setup_failure.get('job_id') == ORIGINAL_JOB and
             setup_failure.get('status') == 'failed' and
             runtime_failure.get('schema') == 'plan069-depth-environment-failure/v1' and
             runtime_failure.get('candidate') == CANDIDATE and runtime_failure.get('status') == 'failed' and
             runtime_failure.get('record_kind') == 'actual',
             'exact original failed native setup receipts required')
    return dict(grant=grant, reserve=reserve, finish=finish, proposal=proposal, original=original)


def validate_recovery_request(request_record, events, run_root, *, require_reservation=False,
                              verifier=verify_record, historical=False):
    """Validate the reviewed D8 recovery and its explicit fresh DO, without dispatch."""
    root = Path(run_root).resolve()
    _require(verifier(request_record) == request_record, 'exact unchanged recovery request required')
    request = read_json(request_record['path'])
    _require(request.get('job_id') == JOB and
             Path(request_record['path']) == root / 'requests' / (JOB + '.json'),
             'exact owned recovery request required')
    _require(request.get('schema') == 'plan069-depth-setup-recovery-request/v1' and
             request.get('record_kind') == 'actual' and request.get('candidate') == CANDIDATE and
             request.get('ledger_path') == str(root / 'ledger.jsonl'),
             'exact actual D8 recovery request required')
    review_record, authorization_record = request['review'], request['authorization']
    review = read_json(verifier(review_record)['path'])
    approval = read_json(verifier(authorization_record)['path'])
    proposal = review.get('setup_recovery_proposal')
    _require(review.get('schema') == 'plan069-depth-execution-review/v1' and
             review.get('status') == 'REVIEW' and isinstance(proposal, dict) and
             proposal.get('schema') == 'plan069-depth-setup-recovery-proposal/v1' and
             proposal.get('candidate') == CANDIDATE and proposal.get('job_id') == JOB and
             proposal.get('max_attempts') == 1 and
             approval.get('schema') == 'plan069-depth-user-authorization/v1' and
             approval.get('status') == 'DO' and approval.get('review') == review_record and
             approval.get(RECOVERY_CANDIDATES[CANDIDATE]['approval_field']) == dict(
                 candidate=CANDIDATE, job_id=JOB, status='approved', max_attempts=1,
                 proposal_sha256=object_hash(proposal)),
             'explicit separately approved one-attempt recovery required')
    _require(request.get('original_setup') == proposal.get('original_setup'),
             'recovery request changed reviewed original ancestry')
    lineage = original_setup_lineage(proposal['original_setup'], events, root, verifier=verifier)
    map_proposal = lineage['proposal']
    _require(proposal.get('map_proposal_sha256') == object_hash(map_proposal),
             'recovery must keep the original approved D8 map proposal')
    seconds = proposal.get('recovery_seconds')
    elapsed = lineage['finish'].get('elapsed_seconds')
    _require(type(seconds) is int and seconds > 0 and type(elapsed) in (int, float) and elapsed >= 0 and
             elapsed + seconds <= map_proposal['allocation']['setup_seconds'],
             'recovery setup time must fit original remaining candidate allowance')
    from .depth_native_runtime import recipe
    environment = request.get('runtime_environment')
    _require(environment == proposal.get('runtime_recipe') == recipe(CANDIDATE, root),
             'exact reviewed amended recovery environment required')
    acquisitions = request.get('acquisitions')
    _require(isinstance(acquisitions, list) and acquisitions == proposal.get('acquisitions') and
             all(isinstance(row, dict) and isinstance(row.get('url'), str) and
                 isinstance(row.get('sha256'), str) and len(row['sha256']) == 64 and
                 type(row.get('bytes')) is int and row['bytes'] > 0 for row in acquisitions) and
             len({row['name'] for row in acquisitions}) == len(acquisitions),
             'exact reviewed acquisition allowlist required')
    source_record = request['source_review']
    source = read_json(verifier(source_record)['path'])
    from .depth_admission import local_source_records
    _require(source.get('schema') == 'plan069-depth-source-review/v1' and
             source.get('status') == 'passed' and source.get('candidate') == CANDIDATE and
             source.get('setup_recovery_proposal_sha256') == object_hash(proposal) and
             (historical or source.get('local_sources') == local_source_records(CANDIDATE)),
             'current independently reviewed recovery source closure required')
    grants = [row for row in events if row.get('event') == EVENT and row.get('job_id') == JOB]
    if require_reservation:
        _require(len(grants) == 1 and grants[0].get('request') == request_record,
                 'exact checked recovery grant required')
    from .config import load
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    allocation = map_proposal['allocation']
    limits = {key: min(lineage['grant']['resource_snapshot'][key] + allocation[key], config[cap] * 2**30)
              for key, cap in (('download_bytes', 'new_download_gib_limit'),
                               ('artifact_bytes', 'new_artifact_disk_gib_limit'))}
    return dict(job_id=JOB, proposal=proposal, map_proposal=map_proposal, original=proposal['original_setup'],
                lineage=lineage, runtime_environment=environment, acquisitions=acquisitions,
                request=request_record, allocation=dict(allocation, setup_seconds=seconds),
                byte_limits=limits, config=config, review=review_record,
                authorization=authorization_record, source_review=source_record)
