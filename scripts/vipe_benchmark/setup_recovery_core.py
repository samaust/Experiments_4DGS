"""Candidate-agnostic setup-recovery ancestry over immutable ledger events.

Each recovering candidate contributes one table entry: its original setup job,
its ordered recovery jobs and their result schemas. Setup-specific evidence
(byte checkpoints, runtime recipes, media tools) stays in that candidate's own
profile module; this core only proves which attempts happened and how they ended.
"""
from typing import TypedDict


class RecoveryCandidate(TypedDict):
    original_job: str
    jobs: tuple[str, ...]
    result_schemas: dict[str, str]


RECOVERY_CANDIDATES: dict[str, RecoveryCandidate] = {
    'D9': RecoveryCandidate(
        original_job='plan069-D9-setup-001',
        jobs=('plan069-D9-setup-recovery-001', 'plan069-D9-setup-recovery-002'),
        result_schemas={'plan069-D9-setup-recovery-001': 'plan069-video-setup-recovery-result/v1',
                        'plan069-D9-setup-recovery-002': 'plan069-video-setup-recovery-result/v2'}),
}
RECOVERY_EVENT = 'depth_setup_recovery_authorized'
CLEAN_FINISH = dict(cleanup_confirmed=True, cleanup_uncertain=False, surviving_pids=[],
                    deadline_exceeded=False)


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _one(events, event, job_id, reason):
    rows = [row for row in events if row.get('event') == event and row.get('job_id') == job_id]
    _require(len(rows) == 1, reason)
    return rows[0]


def candidate_for_job(job_id):
    """Return the candidate owning a recovery job, or None for any other job."""
    owners = [name for name, entry in RECOVERY_CANDIDATES.items() if job_id in entry['jobs']]
    return owners[0] if len(owners) == 1 else None


def _clean(finish):
    return all(finish.get(key) == value for key, value in CLEAN_FINISH.items())


def failed_setup_ancestry(candidate, job_id, events, descriptor):
    """Prove one consumed, cleanly failed setup attempt bound by its descriptor.

    The original setup is granted by ``depth_setup_authorized``; a recovery by the
    protected recovery event. Grant, reservation and failed finish must be unique,
    ordered and cleaned up, and the descriptor must name the exact grant and finish.
    """
    entry = RECOVERY_CANDIDATES[candidate]
    if job_id == entry['original_job']:
        grants = [row for row in events if row.get('event') == 'depth_setup_authorized' and
                  row.get('candidate') == candidate]
        _require(len(grants) == 1, f'unique original {candidate} setup grant required')
        grant = grants[0]
    else:
        _require(job_id in entry['jobs'], f'unknown {candidate} setup recovery job')
        grant = _one(events, RECOVERY_EVENT, job_id, 'unique failed recovery grant required')
        _require(grant.get('candidate') == candidate, 'failed recovery grant candidate changed')
    reserve = _one(events, 'reserve', job_id, 'unique consumed setup reservation required')
    finish = _one(events, 'finish', job_id, 'unique consumed setup finish required')
    _require(descriptor.get('grant_event_sha256') == grant['event_sha256'] and
             descriptor.get('failed_finish_event_sha256') == finish['event_sha256'] and
             grant['sequence'] < reserve['sequence'] < finish['sequence'] and
             reserve.get('resource') == finish.get('resource') == 'setup' and
             finish.get('status') == 'failed' and _clean(finish),
             'exact consumed failed setup with confirmed cleanup required')
    return dict(grant=grant, reserve=reserve, finish=finish)


def completed_recovery(candidate, job_id, setup_record, events):
    """Prove one protected recovery finished complete and clean with this result."""
    _require(candidate_for_job(job_id) == candidate, 'owned accepted recovery job required')
    grant = _one(events, RECOVERY_EVENT, job_id, 'unique accepted recovery grant required')
    reserve = _one(events, 'reserve', job_id, 'unique accepted recovery reservation required')
    finish = _one(events, 'finish', job_id, 'unique accepted recovery finish required')
    _require(grant.get('candidate') == candidate and grant.get('job_id') == job_id and
             grant['sequence'] < reserve['sequence'] < finish['sequence'] and
             reserve.get('resource') == finish.get('resource') == 'setup' and
             finish.get('status') == 'complete' and finish.get('result') == setup_record and
             _clean(finish), 'clean independently authorized recovery completion required')
    return dict(grant=grant, reserve=reserve, finish=finish)
