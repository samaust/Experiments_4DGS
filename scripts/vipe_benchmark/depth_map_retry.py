"""Operator-approved second GPU map attempt after a clean no-output worker failure.

A retry never reopens the consumed first attempt. It is a new job with its own
authorization, bounded by the approved proposal's GPU seconds minus the whole
seconds charged to the first attempt, and only after that attempt failed in its
worker with confirmed cleanup and no map output.
"""
import math
from pathlib import Path
import re

from .config import ROOT
from .files import file_record, object_hash, read_json

SCHEMA = 'plan069-depth-map-retry-approval/v1'
RETRIES = {'D8': dict(failed_job='plan069-D8-maps-001', job='plan069-D8-maps-002',
                      approval=ROOT / 'docs/research/vipe-alternatives/plan031-execution'
                                      / 'depth-D8-maps-retry-approval-001.json'),
           # D6 maps-001 failed at its first Triton compile on Triton 3.2; maps-002 runs on the replacement.
           'D6': dict(failed_job='plan069-D6-maps-001', job='plan069-D6-maps-002',
                      approval=ROOT / 'docs/research/vipe-alternatives/plan031-execution'
                                      / 'depth-D6-maps-retry-approval-001.json')}
FIRST_JOB = re.compile(r'plan069-(D2|D5|D6|D7|D8|D9|D10|D11)-maps-001')


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def first_job(candidate):
    return f'plan069-{candidate}-maps-001'


def is_map_job(job_id):
    return bool(FIRST_JOB.fullmatch(job_id)) or any(row['job'] == job_id for row in RETRIES.values())


VOID_EVENT = 'depth_attempt_voided'
VOID_SCHEMA = 'plan069-depth-grant-void-approval/v1'
# Only these reviewed user approvals may void a grant, as RETRIES pins its approvals.
VOID_APPROVALS = {'D6': ROOT / 'docs/research/vipe-alternatives/plan031-execution'
                         / 'depth-D6-maps-grant-void-approval-001.json'}


def voided_grant_hashes(events):
    return {row.get('grant_event_sha256') for row in events if row.get('event') == VOID_EVENT}


def active_grants(events, candidate=None):
    """Map grants that were not voided as provably unstarted (see Ledger.void_unstarted_depth_attempt)."""
    voided = voided_grant_hashes(events)
    return [row for row in events if row.get('event') == 'depth_attempt_authorized' and
            row.get('event_sha256') not in voided and (candidate is None or row.get('candidate') == candidate)]


def event_job(grant):
    """Map job allocated by a depth_attempt_authorized event; first attempts omit it."""
    return grant.get('job_id', first_job(grant['candidate']))


def map_job(candidate, events):
    """The candidate's current map job: the approved retry once the first attempt failed."""
    retry = RETRIES.get(candidate)
    if retry is not None and any(row.get('event') == 'finish' and row.get('job_id') == retry['failed_job']
                                 and row.get('status') == 'failed' for row in events):
        return retry['job']
    return first_job(candidate)


def current_allocation(candidate, events):
    """Return the latest exact map grant, or None unless the grants are exact.

    Between the first attempt's failure and the retry grant this is still the
    first grant; its slot byte budget remains the binding one until replaced.
    """
    grants = active_grants(events, candidate)
    retry = RETRIES.get(candidate)
    expected = [first_job(candidate)] + ([retry['job']] if retry is not None and len(grants) == 2 else [])
    return grants[-1] if [event_job(row) for row in grants] == expected else None


def validate_retry(candidate, proposal, events, run_root):
    """Check the first attempt's clean no-output failure and the exact operator approval."""
    retry = RETRIES.get(candidate)
    _require(retry is not None, 'no approved map retry for this candidate')
    failed = retry['failed_job']
    grants = [row for row in active_grants(events, candidate) if event_job(row) == failed]
    reserves = [row for row in events if row.get('event') == 'reserve' and row.get('job_id') == failed]
    finishes = [row for row in events if row.get('event') == 'finish' and row.get('job_id') == failed]
    _require(len(grants) == len(reserves) == len(finishes) == 1,
             'exactly one consumed first map attempt required')
    finish = finishes[0]
    _require(finish.get('status') == 'failed' and finish.get('failure_kind') == 'worker_failure' and
             finish.get('resource') == 'gpu' and finish.get('cleanup_confirmed') is True and
             finish.get('cleanup_uncertain') is False and finish.get('surviving_pids') == [] and
             finish.get('deadline_exceeded') is False,
             'clean worker failure of the first map attempt required')
    output = Path(run_root).resolve() / 'jobs' / failed
    failure_path = output / 'failure.json'
    _require(failure_path.is_file() and not (output / 'result.json').exists(),
             'first map attempt must have no map output')
    failure = read_json(failure_path)
    _require(failure.get('status') == 'failed' and failure.get('candidate') == candidate and
             failure.get('job_id') == failed and failure.get('completed_map_rows') == 0,
             'first map attempt must have no map output')
    approved_seconds = proposal.get('allocation', {}).get('gpu_seconds')
    elapsed = finish.get('elapsed_seconds')
    _require(type(approved_seconds) is int and isinstance(elapsed, (int, float)) and
             math.isfinite(elapsed) and elapsed >= 0, 'bounded first attempt GPU seconds required')
    seconds = approved_seconds - math.ceil(elapsed)
    _require(seconds > 0, 'no GPU seconds remain for a map retry')
    _require(Path(retry['approval']).is_file(), 'operator map retry approval required')
    approval_record = file_record(retry['approval'])
    approval = read_json(approval_record['path'])
    _require(approval.get('schema') == SCHEMA and approval.get('status') == 'DO' and
             approval.get('candidate') == candidate and approval.get('failed_job') == failed and
             approval.get('job') == retry['job'] and
             approval.get('failed_finish_event_sha256') == finish['event_sha256'] and
             approval.get('failure') == file_record(failure_path) and
             approval.get('proposal_sha256') == object_hash(proposal) and
             approval.get('review') == grants[0].get('review') and
             approval.get('authorization') == grants[0].get('authorization') and
             approval.get('device_ceiling_unchanged') is True and
             approval.get('gpu_seconds') == seconds and approval.get('max_attempts') == 1,
             'exact operator map retry approval required')
    return dict(job=retry['job'], seconds=seconds, approval=approval_record,
                failed_finish_event_sha256=finish['event_sha256'])
