"""Standing S1 calibration retries: fresh identities after reviewed corrections.

The authority removes the aggregate identity cap. Every immutable allocation
still consumes one attempt, keeps its original recipe and has a finite deadline.
"""
import copy
import hashlib
import json
from pathlib import Path

from .config import ROOT
from .files import canonical, object_hash
from .s1_identity import is_standing_retry_job, job_from_attempt, prior_job

SCHEMA = 'vipe-benchmark-s1-standing-calibration-recovery/v1'
APPROVAL = ROOT / 'docs/research/vipe-alternatives/plan067-execution/s1-standing-retry-approval-001.json'
APPROVAL_SHA256 = '9e1ca6be982f0c5230ce8eb3c11d1979bf826040a7efc2afc555c3af01e017e2'
POLICY = ROOT / 'docs/specs/plan031-execution/s1-retry-policy-amendment-001.md'
POLICY_SHA256 = 'e8c2e35d53958857e8773ab871113ac7d8018bd9b2b253264f6aba5935f6d664'
NINTH_FINISH = dict(sequence=578, event_sha256='db47dacfcb3e35f0e35f677af39390677404e5c361ec50a24d7ad72146470fd4')


def authority():
    from . import s1_recovery as recovery
    approval = recovery.strict_record(recovery.file_record(APPROVAL))
    policy = recovery.strict_record(recovery.file_record(POLICY))
    if approval['sha256'] != APPROVAL_SHA256 or policy['sha256'] != POLICY_SHA256:
        raise ValueError('standing retry authority or policy changed')
    return dict(approval=approval, policy_amendment=policy)


def validate_authority(document):
    from . import s1_recovery as recovery
    if document.get('standing_retry_authority') != authority() or document.get('total_attempts_limit', 0) is not None:
        raise ValueError('standing retry authority must be exact and uncapped')
    approved = recovery.read_json(document['standing_retry_authority']['approval']['path'])
    if document.get('authorization') != approved['user_authorization']:
        raise ValueError('standing retry authority text changed')


def source_changes(before, after):
    """Exact source membership diff, including additions and removals."""
    old = {record['path']: record for record in before}
    new = {record['path']: record for record in after}
    if len(old) != len(before) or len(new) != len(after):
        raise ValueError('duplicate retry qualification sources')
    return [dict(before=old.get(path), after=new.get(path))
            for path in sorted(old.keys() | new.keys()) if old.get(path) != new.get(path)]


def build_correction(finish, previous_authorization, diagnosis, qualification,
                     implementation_review, ledger_snapshot):
    """Bind the actual failed attempt, source correction, review and qualification."""
    from . import s1_recovery as recovery
    previous = recovery.read_json(recovery.strict_record(previous_authorization)['path'])
    qualified = recovery.validation_record(qualification, previous['semantic_amendment'], previous['configuration'])
    old = recovery.read_json(recovery.strict_record(previous['repair_validation'])['path'])
    changes = source_changes(old['sources'], qualified['sources'])
    if not changes:
        raise ValueError('unchanged failed execution cannot be retried')
    for record in (diagnosis, implementation_review, ledger_snapshot):
        recovery.strict_record(record)
    return dict(schema='plan067-s1-retry-correction/v1', failed_job_id=finish['job_id'],
        failed_finish=recovery.event_ref(finish), previous_validation=previous['repair_validation'],
        diagnosis=diagnosis, qualification=qualification, implementation_review=implementation_review,
        failed_ledger_snapshot=ledger_snapshot, changes=changes)


def validate_correction(document, finish, previous):
    from . import s1_recovery as recovery
    value = recovery.read_json(recovery.strict_record(document.get('retry_correction'))['path'])
    if (value.get('schema') != 'plan067-s1-retry-correction/v1'
            or value.get('failed_job_id') != finish['job_id']
            or value.get('failed_finish') != recovery.event_ref(finish)
            or value.get('previous_validation') != previous['repair_validation']
            or value.get('qualification') != document['repair_validation']
            or value.get('implementation_review') != document['implementation_review']
            or value.get('failed_ledger_snapshot') != document['prior_ledger_snapshot']):
        raise ValueError('retry correction is not bound to failed attempt/review/qualification')
    recovery.strict_record(value.get('diagnosis'))
    recovery.strict_record(value['implementation_review'])
    old = recovery.read_json(recovery.strict_record(previous['repair_validation'])['path'])
    qualified = recovery.validation_record(document['repair_validation'], document['semantic_amendment'], document['configuration'])
    expected = source_changes(old['sources'], qualified['sources'])
    if not expected or value.get('changes') != expected:
        raise ValueError('retry correction must change the exact failed source qualification')
    return value


def validate_predecessor(finish, authorization):
    from . import s1_recovery as recovery
    job = finish.get('job_id')
    if (finish.get('event') != 'finish' or finish.get('status') != 'failed'
            or finish.get('cleanup_confirmed') is not True
            or finish.get('cleanup_uncertain') is not False or finish.get('surviving_pids')):
        raise ValueError('standing retry requires exact failed predecessor and confirmed cleanup')
    if job == recovery.JOB_9:
        if (recovery.event_ref(finish) != NINTH_FINISH or finish.get('stop_required') is not True
                or finish.get('terminal_receipt') is not None or finish.get('acceptance') is not None
                or finish.get('result') is not None or finish.get('terminal_publication_status') != 'unavailable'
                or finish.get('terminal_publication_block_reason') != 'poisoned_helper'):
            raise ValueError('standing retry must preserve exact stopped ninth poisoned-helper failure')
    elif not is_standing_retry_job(job):
        raise ValueError('standing retry predecessor identity')
    elif finish.get('terminal_receipt'):
        receipt = recovery.read_json(recovery.strict_record(finish['terminal_receipt'])['path'])
        if (receipt.get('job_id') != job or receipt.get('status') != 'failed'
                or receipt.get('authorization') != authorization or receipt.get('reservation') != finish.get('reservation')
                or receipt.get('attempt_consumed') is not True or receipt.get('reconstruction_authorized') is not False):
            raise ValueError('standing retry predecessor terminal binding changed')
    elif (finish.get('stop_required') is not True or finish.get('terminal_publication_status') != 'unavailable'
            or not finish.get('terminal_publication_block_reason')):
        raise ValueError('standing retry absent terminal history is ambiguous')


def validate_chain(document, authorization, events, states):
    from . import s1_recovery as recovery
    job = document['job_id']
    registrations = [event for event in events if event['event'] == 'component_recovery_authorized'
                     and event.get('original_job_id', '').startswith('S1-')]
    number = int(job.rsplit('-', 1)[1])
    if number not in (len(registrations), len(registrations) + 1):
        raise ValueError('standing retry requires the next sequential fresh identity')
    expected = [job_from_attempt(index) for index in range(1, number)]
    if (len(registrations) not in (len(expected), len(expected) + 1)
            or [event['job_id'] for event in registrations[:len(expected)]] != expected
            or any(event['job_id'] != job or event.get('authorization') != authorization
                   for event in registrations[len(expected):])):
        raise ValueError('standing retry requires the next sequential fresh identity')
    previous_record = previous_finish = None
    previous = None
    for event in registrations[:len(expected)]:
        record = recovery.strict_record(event['authorization'])
        old = recovery.read_json(record['path'])
        finish = states.get(event['job_id'], {})
        if (old.get('job_id') != event['job_id'] or old.get('additional_attempt_approved') is not True
                or old.get('authorization_context', {}).get('stage') != 'DO'
                or any(event.get(key) != old.get(key) for key in recovery.BINDINGS)
                or finish.get('event') != 'finish' or finish.get('status') != 'failed'
                or finish.get('cleanup_confirmed') is not True or finish.get('cleanup_uncertain', False) is not False
                or finish.get('surviving_pids')
                or (previous_record is not None and (
                    old.get('previous_recovery_authorization') != previous_record
                    or old.get('previous_recovery_failure_event_sha256') != previous_finish['event_sha256']))):
            raise ValueError('standing retry consumed predecessor chain changed or already succeeded')
        previous_record, previous_finish, previous = record, finish, old
    if (document.get('previous_recovery_authorization') != previous_record
            or document.get('previous_recovery_failure') != previous_finish
            or document.get('previous_recovery_failure_event_sha256') != previous_finish['event_sha256']):
        raise ValueError('standing retry exact predecessor binding changed')
    validate_predecessor(previous_finish, previous_record)
    return previous, previous_finish


def stop_resolution(document, finish):
    from . import s1_recovery as recovery
    if not finish.get('stop_required'):
        return None
    return dict(schema='plan067-s1-standing-stop-resolution/v1',
        authority=document['standing_retry_authority'], stopped_finish=recovery.event_ref(finish),
        correction=document['retry_correction'], historical_stop_preserved=True,
        unavailable_terminal_preserved=finish.get('terminal_receipt') is None,
        previous_result_accepted=False, scope='fresh standing S1 calibration identity only')


def validate_review(document):
    from . import s1_recovery as recovery
    proposal = recovery.read_json(recovery.strict_record(document.get('review_proposal'))['path'])
    if (proposal.get('schema') != SCHEMA or proposal.get('job_id') != document['job_id']
            or proposal.get('additional_attempt_approved') is not False
            or proposal.get('authorization_context', {}).get('stage') != 'REVIEW'
            or proposal.get('required_rows') != 510 or proposal.get('row_metadata_bytes_limit') != 256 * 1024
            or proposal.get('resource_sample_seconds') != 2. or proposal.get('total_attempts_limit', 0) is not None):
        raise ValueError('exact standing retry REVIEW proposal required')
    expected = dict(proposal, additional_attempt_approved=True, authorization=document['authorization'],
        authorization_context=dict(proposal['authorization_context'], stage='DO'), review_proposal=document['review_proposal'])
    if document != expected:
        raise ValueError('standing retry DO differs from exact reviewed proposal')


def preserve_predecessor(local, document, events, authorization, process_amendment):
    from . import s1_recovery as recovery
    snapshot = recovery.strict_record(document['prior_ledger_snapshot'])
    frozen = Path(snapshot['path']).read_bytes()
    frozen_events = [json.loads(line) for line in frozen.splitlines()]
    finish = document['previous_recovery_failure']
    count = finish['sequence'] + 1
    expected = ''.join(canonical(event) + '\n' for event in events[:count]).encode()
    if (len(frozen_events) != count or frozen != expected or frozen_events[-1] != finish
            or not (Path(local) / 'ledger.jsonl').read_bytes().startswith(frozen)):
        raise ValueError('standing retry consumed predecessor snapshot changed')
    previous_record = recovery.strict_record(document['previous_recovery_authorization'])
    previous = recovery.read_json(previous_record['path'])
    recovery.preservation(local, previous, events[:count], previous_record,
                          process_amendment_override=process_amendment)
    live = document['live_ledger_snapshot']
    length = live.get('events')
    if type(length) is not int or not count <= length <= len(events):
        raise ValueError('standing retry REVIEW ledger prefix required')
    prefix = ''.join(canonical(event) + '\n' for event in events[:length]).encode()
    if (live != dict(path=str((Path(local) / 'ledger.jsonl').resolve()), bytes=len(prefix),
            sha256=hashlib.sha256(prefix).hexdigest(), events=length,
            last_event_sha256=events[length - 1]['event_sha256'], active_jobs=[])
            or (Path(local) / 'ledger.jsonl').read_bytes()[:len(prefix)] != prefix):
        raise ValueError('standing retry REVIEW ledger prefix changed')
    recovery.lifecycle(events[length:], authorization, document)


def build_review_proposal(local, config, validation, implementation_review,
                         request_date, *, correction, job_id=None):
    """Prepare the next immutable REVIEW under standing authority, without writes."""
    from . import s1_recovery as recovery
    from .s1_review_proposal import _events
    from .ledger import Ledger
    local = Path(local).resolve()
    path = local / 'ledger.jsonl'
    raw = path.read_bytes()
    events = _events(raw)
    ledger = object.__new__(Ledger)
    ledger.path, ledger.config = path, config
    states = ledger.states(events)
    registrations = [event for event in events if event['event'] == 'component_recovery_authorized'
                     and event.get('original_job_id', '').startswith('S1-')]
    next_job = job_from_attempt(len(registrations) + 1)
    job = next_job if job_id is None else job_id
    if not is_standing_retry_job(job) or job != next_job:
        raise ValueError('standing retry requires the next sequential fresh identity')
    if job in states or any(event.get('job_id') == job for event in events):
        raise ValueError('consumed or previously registered standing retry identity')
    if any(state['event'] == 'reserve' for state in states.values()):
        raise ValueError('active attempt prevents standing retry REVIEW')
    last = registrations[-1]
    predecessor_record = recovery.strict_record(last['authorization'])
    predecessor = recovery.read_json(predecessor_record['path'])
    finish = states.get(prior_job(job), {})
    validate_predecessor(finish, predecessor_record)
    proposal = copy.deepcopy(predecessor)
    for key in ('review_proposal', 'fresh_attempt_approval'):
        proposal.pop(key, None)
    bound_authority = authority()
    approved = recovery.read_json(bound_authority['approval']['path'])
    correction_value = recovery.read_json(recovery.strict_record(correction)['path'])
    proposal.update(schema=SCHEMA, job_id=job, attempts_limit=1, total_attempts_limit=None,
        additional_attempt_approved=False, authorization=approved['user_authorization'],
        authorization_context=dict(request_date=request_date, stage='REVIEW',
            scope='Fresh S1 calibration after a reviewed validated correction under standing authority'),
        standing_retry_authority=bound_authority, retry_correction=correction,
        repair_validation=validation, implementation_review=implementation_review,
        previous_recovery_authorization=predecessor_record, previous_recovery_failure=copy.deepcopy(finish),
        previous_recovery_failure_event_sha256=finish['event_sha256'],
        previous_recovery_primary_failure=copy.deepcopy(finish.get('primary_failure')),
        previous_recovery_secondary_failures=copy.deepcopy(finish.get('secondary_failures', [])),
        prior_ledger_snapshot=correction_value['failed_ledger_snapshot'],
        live_ledger_snapshot=dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
            events=len(events), last_event_sha256=events[-1]['event_sha256'], active_jobs=[]),
        cumulative_resource_totals=ledger.totals(events), required_rows=510,
        row_metadata_bytes_limit=256 * 1024, resource_sample_seconds=2., dispatch_supported=True, approval_required=False)
    proposal['operational_stop_resolution'] = stop_resolution(proposal, finish)
    validate_authority(proposal)
    validate_chain(proposal, None, events, states)
    validate_correction(proposal, finish, predecessor)
    recovery.preservation(local, proposal, events, None)
    configuration = recovery.strict_record(proposal['configuration'])
    if (configuration != recovery.file_record(recovery.ROOT / 'configs/vipe-alternatives/benchmark-v1.json')
            or recovery.read_json(configuration['path']) != config or proposal['resource_limits'] != recovery.LIMITS):
        raise ValueError('frozen configuration and resource ceilings required')
    if any(ledger.totals(events)[resource]['elapsed_seconds'] + ledger.totals(events)[resource]['reserved_seconds'] >= limit
           for resource, limit in [('cpu', 57600), ('setup', 57600)]):
        raise ValueError('standing retry preparation budget exhausted')
    if ledger.totals(events)['gpu']['elapsed_seconds'] + ledger.totals(events)['gpu']['reserved_seconds'] + 3600 > 93600:
        raise ValueError('insufficient cumulative GPU allowance for standing retry')
    if path.read_bytes() != raw:
        raise ValueError('live ledger changed while preparing standing REVIEW')
    return proposal


def approve_review(proposal_record):
    """Create the exact DO mapping from a persisted REVIEW; caller writes once."""
    from . import s1_recovery as recovery
    proposal = recovery.read_json(recovery.strict_record(proposal_record)['path'])
    if not is_standing_retry_job(proposal.get('job_id')) or proposal.get('authorization_context', {}).get('stage') != 'REVIEW':
        raise ValueError('standing retry REVIEW mapping required')
    validate_authority(proposal)
    return dict(proposal, additional_attempt_approved=True,
        authorization_context=dict(proposal['authorization_context'], stage='DO'), review_proposal=proposal_record)
