"""Turn one complete QUALIFY arm into the native qualification production DO requires.

The QUALIFY arm runs the unchanged production workers under a distinct REVIEW
request identity with identical settings. Only cleaned successful ledger
finishes for all four phases, reserved under that QUALIFY envelope, qualify.
Production admission re-derives the record from the ledger with `verify`, so a
hand-written or compatibility-only receipt cannot stand in for it.

In actual worker records `native_adapter_qualified` means "ran under a reviewed
native-adapter envelope (DO or QUALIFY)"; the reservation `role` distinguishes
qualification runs, and only this record states that the stack is qualified.
"""
import copy

from .files import file_record, read_json, verify_record, write_json
from .final_render_contract import PHASES

SCHEMA = 'plan069-final-render-native-qualification/v1'
PHASE_SCHEMA = 'plan069-final-render-qualify-phase-receipt/v1'
RESERVATION = 'plan069-final-render-reservation-binding/v1'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _bound(record):
    _require(type(record) is dict and set(record) == {'path', 'sha256', 'bytes'} and
        verify_record(record) == record, 'exact unchanged qualification evidence required')
    return read_json(record['path'])


def _settings(request):
    """Request content that must match between QUALIFY and production."""
    settings = copy.deepcopy(request)
    for name in ('id', 'allocations'):
        settings.pop(name)
    settings['bindings'].pop('proposal', None)
    prefix = request['id']+'/'
    _require(all(a['id'].startswith(prefix) for a in request['allocations']),
        'request allocation identities differ from request id')
    allocations = [dict(a, id=a['id'][len(prefix):]) for a in request['allocations']]
    return settings, allocations


def derive(production_record, envelope_record, events, states):
    """Return the phase receipts and qualification content implied by the ledger."""
    envelope = _bound(envelope_record)
    _require(envelope.get('schema') == 'plan069-final-render-do/v1' and envelope.get('record_kind') == 'actual' and
        envelope.get('mode') == 'QUALIFY', 'actual QUALIFY envelope required')
    production = _bound(production_record)
    qualify = _bound(envelope['request'])
    _require(qualify['id'] != production['id'], 'distinct qualification request identity required')
    _require(_settings(qualify) == _settings(production), 'qualification settings differ from production request')
    from .final_render_admission import command_keys
    keys = command_keys(envelope, qualify)
    _require(set(envelope['commands']) == keys, 'exact one-arm qualification commands required')
    arm = next(iter(keys)).split('/')[0]
    receipts, results, tails = {}, {}, []
    for phase in PHASES:
        job = f"{qualify['id']}/{arm}/{phase}"
        finish = states.get(job, {})
        _require(finish.get('event') == 'finish' and finish.get('status') == 'complete' and
            finish.get('cleanup_confirmed') is True and finish.get('cleanup_uncertain') is False and
            finish.get('deadline_exceeded') is False, 'cleaned successful qualification phase required: '+phase)
        reservations = [e for e in events if e.get('event') == 'reserve' and e.get('job_id') == job]
        _require(len(reservations) == 1, 'single qualification reservation required: '+phase)
        evidence = reservations[0]['evidence']
        _require(evidence.get('schema') == RESERVATION and evidence.get('role') == 'native-qualification' and
            evidence.get('envelope') == envelope_record and evidence.get('request') == envelope['request'] and
            evidence.get('arm') == arm and evidence.get('phase') == phase,
            'QUALIFY envelope reservation required: '+phase)
        result = _bound(finish['result'])
        supervision = _bound(finish['supervision'])
        _require(result.get('status') == 'complete' and supervision.get('status') == 'complete' and
            result.get('allocation_id') == job, 'cleaned successful qualification phase required: '+phase)
        workers = supervision.get('peak_cpu_workers')
        _require(type(workers) is int and workers > 0, 'measured positive CPU worker usage required: '+phase)
        results[phase] = result
        # Conservative upper bound on cleanup: everything in the allocation outside
        # the worker's own budget (launch, imports, process-group stop, acceptance
        # and the final resource sample).
        tails.append(finish['elapsed_seconds']-result['elapsed_seconds'])
        receipts[phase] = dict(schema=PHASE_SCHEMA, record_kind='actual', status='passed', phase=phase, arm=arm,
            request=production_record, qualification_request=envelope['request'], qualification_envelope=envelope_record,
            runtime=production['bindings']['runtime'], job_id=job, command=reservations[0]['command'],
            result=finish['result'], supervision=finish['supervision'], elapsed_seconds=finish['elapsed_seconds'],
            cpu_workers_used=workers, peak_device_bytes=supervision['peak_device_bytes'],
            artifact_bytes=result['artifact_bytes'], cleanup_confirmed=True, native_adapter_qualified=True)
    timings = [_bound(r) for r in results['train']['artifacts'] if r['path'].endswith('/checkpoint-timing.json')]
    _require(len(timings) == 1 and timings[0].get('checkpoint') == results['train']['checkpoint'],
        'measured checkpoint timing required')
    qualification = dict(schema=SCHEMA, record_kind='actual', status='passed', request=production_record,
        qualification_envelope=envelope_record, runtime=production['bindings']['runtime'],
        source_files=envelope['source_files'], interpreter=envelope['interpreter'],
        matcher_runtime=envelope['matcher_runtime'],
        initializer_bytes=results['initializer']['artifact_bytes'],
        checkpoint_bytes=results['train']['checkpoint']['bytes'],
        checkpoint_seconds=timings[0]['save_seconds'], cleanup_seconds=max(tails),
        cleanup_seconds_basis='upper bound: allocation time outside the worker budget')
    return receipts, qualification


def build(production_record, envelope_record, ledger, output):
    """Publish passed phase receipts and the aggregate native qualification record."""
    events = ledger.events()
    receipts, qualification = derive(production_record, envelope_record, events, ledger.states(events))
    # Every check precedes publication; a refused qualification writes nothing.
    output.mkdir(parents=True, exist_ok=False)
    runs = {}
    for phase, run in receipts.items():
        write_json(output/f'{phase}.json', run)
        runs[phase] = file_record(output/f'{phase}.json')
    write_json(output/'qualification.json', dict(qualification, runs=runs))
    return file_record(output/'qualification.json')


def verify(qualification_record, production_record, events, states):
    """Re-derive a published qualification from the ledger; return it if identical."""
    qualification = _bound(qualification_record)
    _require(qualification.get('schema') == SCHEMA and qualification.get('request') == production_record,
        'native qualification for this production request required')
    receipts, expected = derive(production_record, qualification.get('qualification_envelope'), events, states)
    runs = qualification.get('runs')
    _require(type(runs) is dict and set(runs) == set(PHASES) and
        all(_bound(runs[phase]) == receipts[phase] for phase in PHASES) and
        {k: v for k, v in qualification.items() if k != 'runs'} == expected,
        'native qualification differs from its ledger evidence')
    return qualification
