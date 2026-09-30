"""Read-only S1 recovery planning; a REVIEW document cannot allocate work.

Historical source receipts describe their historical dispatches. Only the newly
supplied qualification is checked against current sources; old evidence is never
rewritten to make it describe a later implementation.
"""
import copy
import hashlib
import json
from pathlib import Path

from . import s1_recovery as recovery
from .files import canonical, file_record, object_hash, read_json, safe_path
from .ledger import Ledger

HISTORICAL_JOB = 'S1-calibration-recovery-005'
NEXT_JOB = 'S1-calibration-recovery-006'


def _events(raw):
    events = [json.loads(line) for line in raw.splitlines()]
    previous = None
    for sequence, event in enumerate(events):
        if (event.get('sequence') != sequence or event.get('previous_sha256') != previous
                or event.get('event_sha256') != object_hash(
                    {key: value for key, value in event.items() if key != 'event_sha256'})):
            raise ValueError('ledger corruption; cannot plan a recovery')
        previous = event['event_sha256']
    if not events or raw != ''.join(canonical(event) + '\n' for event in events).encode():
        raise ValueError('exact canonical ledger bytes required')
    return events


def build_review_proposal(local, config, validation, implementation_review,
                         request_date, *, job_id=HISTORICAL_JOB):
    """Bind a concrete fifth or sixth proposal to a stable live snapshot, without writes.

    Ticket #25 must bind this exact proposal and explicit approval before
    the exact identity can register or dispatch.
    """
    if job_id not in (HISTORICAL_JOB, NEXT_JOB):
        raise ValueError('only the next unconsumed fifth REVIEW identity is allowed')
    if not isinstance(request_date, str) or not request_date.strip():
        raise ValueError('REVIEW request date required')
    local = safe_path(local).resolve()
    path = local / 'ledger.jsonl'
    raw = path.read_bytes()
    events = _events(raw)
    # The Ledger reducers are pure with an explicit snapshot. Do not call its
    # constructor or events(), which can create directories or open for append.
    ledger = object.__new__(Ledger)
    ledger.path, ledger.config = path, config
    states = ledger.states(events)
    if job_id in states or any(event.get('job_id') == job_id for event in events):
        raise ValueError('consumed or previously registered fifth identity')
    if any(state['event'] == 'reserve' for state in states.values()):
        raise ValueError('active attempt prevents a stable REVIEW proposal')
    prior = [event for event in events if event['event'] == 'component_recovery_authorized'
             and event.get('original_job_id', '').startswith('S1-')]
    sixth = job_id == NEXT_JOB
    identities = [recovery.JOB, recovery.JOB_2, recovery.JOB_3, recovery.JOB_4] + ([recovery.JOB_5] if sixth else [])
    if [event['job_id'] for event in prior] != identities:
        raise ValueError('next unconsumed identity requires ordered consumed predecessor recovery chain')
    previous_record = None
    previous_finish = None
    for event in prior:
        record = recovery.strict_record(event['authorization'])
        document = read_json(record['path'])
        finish = states.get(event['job_id'], {})
        if (document.get('job_id') != event['job_id']
                or document.get('additional_attempt_approved') is not True
                or document.get('authorization_context', {}).get('stage') != 'DO'
                or any(event.get(key) != document.get(key) for key in recovery.BINDINGS)
                or finish.get('event') != 'finish' or finish.get('status') != 'failed'
                or finish.get('cleanup_confirmed') is not True
                or finish.get('cleanup_uncertain', False) is not False
                or finish.get('surviving_pids')
                or (previous_record is not None and (
                    document.get('previous_recovery_authorization') != previous_record
                    or document.get('previous_recovery_failure_event_sha256') != previous_finish['event_sha256']))):
            raise ValueError('exact consumed cleaned-up predecessor required')
        previous_record, previous_finish = record, finish
    if sixth:
        recovery.validate_sixth_predecessor(previous_finish, previous_record)
    predecessor = document
    snapshot = recovery.strict_record(file_record(recovery.ROOT / (
        'docs/research/vipe-alternatives/plan031-execution/s1-recovery-005/outcome/ledger-after.jsonl' if sixth else
        'docs/research/vipe-alternatives/issue3-preparation/s1-dispatch-004-outcome/post-dispatch-ledger-004.jsonl')))
    predecessor_count = 520 if sixth else 472
    frozen = Path(snapshot['path']).read_bytes()
    frozen_events = _events(frozen)
    if (not raw.startswith(frozen) or frozen_events[-1] != previous_finish
            or len(frozen_events) != predecessor_count):
        raise ValueError('fourth recovery immutable finish prefix changed')
    process_amendment = file_record(recovery.PROCESS_FILE_AMENDMENT_2) if sixth else None
    recovery.preservation(local, predecessor, frozen_events, previous_record,
                          process_amendment_override=process_amendment)
    configuration = recovery.strict_record(predecessor['configuration'])
    if (configuration != file_record(recovery.ROOT / 'configs/vipe-alternatives/benchmark-v1.json')
            or read_json(configuration['path']) != config
            or predecessor['resource_limits'] != recovery.LIMITS):
        raise ValueError('frozen configuration and resource ceilings required')
    validation = recovery.strict_record(validation)
    qualified = recovery.validation_record(validation, predecessor['semantic_amendment'], configuration)
    if any(qualified.get(key) != predecessor[key] for key in ('baseline', 'plan', 'baseline_correction')):
        raise ValueError('current qualification baseline/plan mismatch')
    implementation_review = recovery.strict_record(implementation_review)
    from .runtime import TARGETS
    from .backends import AssetBundle
    for key in ('e1_qualification', 'e1_assets', 'inputs', 'annotations',
                'annotation_policy', 'annotation_review', 'historical_request'):
        recovery.strict_record(predecessor[key])
    setup = read_json(predecessor['e1_qualification']['path'])
    if (states.get('E1-setup-recovery-002', {}).get('result') != predecessor['e1_qualification']
            or setup.get('status') != 'complete' or setup.get('environment') != 'E1'
            or setup.get('components') != ['S1'] or setup.get('assets') != predecessor['e1_assets']
            or setup.get('runtime') != predecessor['e1_runtime']
            or setup['runtime']['versions'] != TARGETS['E1']):
        raise ValueError('exact qualified E1 assets/runtime required')
    for key in ('inventory', 'imports', 'dependency_lock', 'build_inputs'):
        recovery.strict_record(setup['runtime'][key])
    imports = read_json(setup['runtime']['imports']['path'])
    if (imports.get('status') != 'complete' or imports.get('forwards') != 0
            or imports.get('cuda_context_initialized') is not False):
        raise ValueError('E1 import-only qualification required')
    assets = read_json(predecessor['e1_assets']['path'])
    AssetBundle('S1', assets)
    request = dict(job_id='S1-calibration', component='S1', branch='calibration',
        inputs=predecessor['inputs'], runtime=setup['runtime'], assets=assets,
        forbidden_vipe_roots=[read_json(local / 'qualification/historical-assets.json')['assets']['vipe_source']['path']])
    if (object_hash(request) != predecessor['original_request_sha256']
            or read_json(predecessor['historical_request']['path']) != dict(request, configuration=configuration)):
        raise ValueError('frozen canonical worker request changed')
    totals = ledger.totals(events)
    if totals['gpu']['elapsed_seconds'] + totals['gpu']['reserved_seconds'] + 3600 > recovery.LIMITS['gpu_total_seconds_limit']:
        raise ValueError('insufficient cumulative GPU allowance for proposed attempt')
    proposal = copy.deepcopy(predecessor)
    proposal.update(schema=recovery.SCHEMA_6 if sixth else recovery.SCHEMA_5,
        job_id=job_id, additional_attempt_approved=False,
        authorization=f'Proposed only: exactly one {job_id} GPU calibration attempt; explicit user approval required before dispatch.',
        authorization_context=dict(request_date=request_date, stage='REVIEW',
            scope='One new calibration identity; no redispatch, reset, reconstruction, setup or downloads'),
        repair_validation=validation, implementation_review=implementation_review,
        previous_recovery_authorization=previous_record,
        previous_recovery_failure_event_sha256=previous_finish['event_sha256'],
        previous_recovery_failure=copy.deepcopy(previous_finish),
        previous_recovery_primary_failure=copy.deepcopy(previous_finish.get('primary_failure')),
        previous_recovery_secondary_failures=copy.deepcopy(previous_finish.get('secondary_failures', [])),
        prior_ledger_snapshot=snapshot,
        live_ledger_snapshot=dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest(),
            events=len(events), last_event_sha256=events[-1]['event_sha256'], active_jobs=[]),
        cumulative_resource_totals=totals, required_rows=510,
        row_metadata_bytes_limit=256*1024, resource_sample_seconds=2.,
        dispatch_supported=True, approval_required=True)
    if sixth:
        proposal['process_file_amendment'] = process_amendment
    # Detect a concurrent append while verification was in progress. Callers
    # must still recheck the live state at any later approval/admission boundary.
    if path.read_bytes() != raw:
        raise ValueError('live ledger changed while preparing REVIEW proposal')
    return proposal


def main(argv=None):
    """Publish one immutable REVIEW artifact; never access devices or dispatch."""
    import argparse
    from .config import load
    from .files import write_json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--local', type=Path, required=True)
    parser.add_argument('--validation', type=Path, required=True)
    parser.add_argument('--implementation-review', type=Path, required=True)
    parser.add_argument('--request-date', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    value = build_review_proposal(args.local, load(), file_record(args.validation),
        file_record(args.implementation_review), args.request_date, job_id=NEXT_JOB)
    write_json(args.output, value)
    print(json.dumps(file_record(args.output), sort_keys=True))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
