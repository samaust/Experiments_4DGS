"""Fail-closed binding for the one amendment-bound S1 calibration allocation.

Validation accepts a locked event snapshot so registration/reservation never
re-enter a ledger lock or derive a request through recovered-result lookup.
"""
from pathlib import Path

from .config import ROOT
from .files import file_record, object_hash, read_json, safe_path, verify_record

SCHEMA = 'vipe-benchmark-s1-amendment-calibration-recovery/v1'
JOB = 'S1-calibration-recovery-001'
AMENDMENT = 'plan031-s1-s0-token-sum-v1'
LIMITS = dict(gpu_concurrency=1, gpu_peak_device_gib_limit=22,
    gpu_total_seconds_limit=93600, cpu_max_workers=8,
    cpu_prepare_score_report_seconds_limit=57600, setup_wall_seconds_limit=57600,
    new_download_gib_limit=60, new_artifact_disk_gib_limit=150,
    new_setup_attempts=0, new_downloads=0, extra_smoke_jobs=0,
    reconstruction_attempts=0, cleanup_reserve_seconds_max=30)
BINDINGS = ('semantic_amendment', 'repair_validation', 'configuration',
            'original_request_sha256', 'baseline_correction')


# Compatibility exports keep admission and execution on one static contract.
from .s1_validation_contract import (SUITES, source_paths, strict_record,
    required_cases, receipt_totals, validate_wrapper)


def validation_record(record, amendment, configuration):
    return validate_wrapper(read_json(strict_record(record)['path']), amendment, configuration)


def event_ref(event):
    return {key: event[key] for key in ('sequence', 'event_sha256')}


def validate_binding(local, config, authorization, *, events=None, consumed=False):
    """Read-only admission; consumed=True is only for terminal resolution."""
    from .ledger import Ledger
    from .runtime import TARGETS
    from .backends import AssetBundle
    local = Path(local)
    ledger = Ledger(local / 'ledger.jsonl', config)
    events = ledger.events() if events is None else events
    states = ledger.states(events)
    document = read_json(strict_record(authorization)['path'])
    required = dict(schema=SCHEMA, job_id=JOB, original_job_id='S1-calibration',
        attempts_limit=1, seconds_limit=3600, gpu_total_seconds_limit=93600,
        reset_previous_consumption=False, changes_to_prescribed_configuration=True,
        unrelated_attempts_reopened=False, reconstruction_authorized=False,
        semantic_amendment_approved=True, additional_attempt_approved=True)
    if (any(type(document.get(k)) is not type(v) or document[k] != v for k, v in required.items())
            or not isinstance(document.get('authorization'), str) or not document['authorization'].strip()
            or not isinstance(document.get('authorization_context'), dict)
            or not all(document['authorization_context'].get(k) for k in ('request_date', 'stage', 'scope'))
            or document['authorization_context']['stage'] != 'DO'
            or document.get('branch', 'calibration') != 'calibration'):
        raise ValueError('exact explicit S1 calibration amendment authorization required')
    configuration = strict_record(document['configuration'])
    if (configuration != file_record(ROOT / 'configs/vipe-alternatives/benchmark-v1.json')
            or read_json(configuration['path']) != config
            or document.get('resource_limits') != LIMITS
            or any(config.get(k) != v for k, v in LIMITS.items() if k in config)):
        raise ValueError('frozen configuration and resource ceilings required')
    for key in ('plan', 'baseline', 'implementation_review'):
        strict_record(document[key])
    preservation(local, document, events, authorization)
    amendment = read_json(strict_record(document['semantic_amendment'])['path'])
    if (amendment.get('schema') != 'plan031-s1-semantic-assignment-amendment/v1'
            or amendment.get('amendment_id') != AMENDMENT
            or amendment.get('changes_to_semantic_protocol') is not True
            or 'S1-calibration' not in amendment.get('scope', [])):
        raise ValueError('S1 semantic amendment record required')
    for parent in [*amendment['frozen_parents'], *amendment['verified_s0_sources'], amendment['native_predict_source']]:
        strict_record(parent)
    failures = [f for f in amendment['original_failures'] if f['branch'] == 'calibration']
    original = states.get('S1-calibration', {})
    if (len(failures) != 1 or failures[0]['failure'] != document['original_failure']
            or failures[0]['event_sha256'] != document['original_failure_event_sha256']
            or failures[0]['cleanup_confirmed'] is not True
            or original.get('event') != 'finish' or original.get('status') != 'failed'
            or original.get('cleanup_confirmed') is not True or original.get('surviving_pids')
            or original.get('event_sha256') != document['original_failure_event_sha256']):
        raise ValueError('S1 must bind live original cleaned-up calibration failure')
    failure = read_json(strict_record(document['original_failure'])['path'])
    if (Path(document['original_failure']['path']) != (local / 'jobs/S1-calibration/failure.json').resolve()
            or failure.get('job_id') != 'S1-calibration' or failure.get('status') != 'failed'):
        raise ValueError('wrong original S1 failure artifact')
    validation = validation_record(document['repair_validation'], document['semantic_amendment'], configuration)
    if validation.get('baseline') != document['baseline'] or validation.get('plan') != document['plan'] or validation.get('baseline_correction') != document['baseline_correction']:
        raise ValueError('validation baseline/plan mismatch')
    prior = [e for e in events if e['event'] == 'component_recovery_authorized'
             and e['original_job_id'].startswith('S1-')]
    if prior and (len(prior) != 1 or prior[0]['job_id'] != JOB or prior[0]['authorization'] != authorization):
        raise ValueError('different or second S1 allocation')
    if not consumed and (JOB in states or any(s['event'] == 'reserve' for s in states.values())):
        raise ValueError('consumed S1 identity or active attempt')
    total = ledger.totals(events)['gpu']
    if not consumed and total['elapsed_seconds'] + total['reserved_seconds'] >= 93600:
        raise ValueError('cumulative GPU allocation exhausted')
    def artifact(job, field=None):
        state = states.get(job, {})
        if state.get('event') != 'finish' or state.get('status') != 'complete':
            raise ValueError('completed prerequisite required: ' + job)
        record = strict_record(state['result'])
        result = read_json(record['path'])
        if result.get('status') != 'complete':
            raise ValueError('incomplete prerequisite: ' + job)
        return strict_record(result[field]) if field else record
    setup = artifact('E1-setup-recovery-002')
    result = read_json(setup['path'])
    if (setup != document['e1_qualification'] or result.get('environment') != 'E1'
            or result.get('components') != ['S1'] or result['assets'] != document['e1_assets']
            or result['runtime'] != document['e1_runtime'] or result['runtime']['versions'] != TARGETS['E1']):
        raise ValueError('exact E1 qualification/assets/runtime required')
    for key in ('inventory', 'imports', 'dependency_lock', 'build_inputs'):
        strict_record(result['runtime'][key])
    imports = read_json(result['runtime']['imports']['path'])
    if imports.get('status') != 'complete' or imports.get('forwards') != 0 or imports.get('cuda_context_initialized') is not False:
        raise ValueError('E1 import-only qualification required')
    assets = read_json(strict_record(document['e1_assets'])['path'])
    AssetBundle('S1', assets)
    for key, job in [('inputs', 'prepare'), ('annotations', 'annotations')]:
        if document[key] != artifact(job, key):
            raise ValueError('exact frozen ' + key + ' required')
    annotation = read_json(document['annotations']['path'])
    if (annotation.get('policy') != document['annotation_policy']
            or annotation['contributors']['independent_review']['record'] != document['annotation_review']):
        raise ValueError('annotation policy/review binding changed')
    for key in ('annotation_policy', 'annotation_review'):
        strict_record(document[key])
    amendments = [e for e in events if e['event'] == 'annotation_amendment'
                  and event_ref(e) == document['annotation_amendment_event']]
    if len(amendments) != 1 or amendments[0]['policy'] != document['annotation_policy']:
        raise ValueError('annotation amendment event required')
    historical = strict_record(document['historical_request'])
    reservations = [e for e in events if e['event'] == 'reserve' and e['job_id'] == 'S1-calibration']
    if (len(reservations) != 1 or reservations[0]['evidence']['request'] != historical
            or Path(historical['path']) != (local / 'requests/S1-calibration.json').resolve()):
        raise ValueError('historical dispatch provenance required')
    # Same canonical recipe as make_request, without components()/result lookup
    # recursion while a registration/reservation lock is held.
    request = dict(job_id='S1-calibration', component='S1', branch='calibration',
        inputs=document['inputs'], runtime=result['runtime'], assets=assets,
        forbidden_vipe_roots=[read_json(local / 'qualification/historical-assets.json')['assets']['vipe_source']['path']])
    if (object_hash(request) != document['original_request_sha256']
            or read_json(historical['path']) != dict(request, configuration=configuration)):
        raise ValueError('derived canonical request or historical dispatch differs')
    return document, request


def preservation(local, document, events, authorization):
    """Exact scientific bytes, original ledger prefix, explicit bookkeeping policy."""
    import hashlib
    from .files import canonical
    baseline = read_json(strict_record(document['baseline'])['path'])
    correction = read_json(strict_record(document['baseline_correction'])['path'])
    if (baseline.get('schema') != 'plan032-s1-recovery-baseline/v1'
            or correction.get('schema') != 'plan033-s1-baseline-correction/v1'
            or correction.get('baseline') != document['baseline']
            or correction.get('plan') != document['plan']):
        raise ValueError('explicit baseline correction required')
    strict_record(correction['review'])
    if correction.get('predecessor'):
        predecessor = read_json(strict_record(correction['predecessor'])['path'])
        strict_record(predecessor['review'])
        if (predecessor.get('baseline') != document['baseline']
                or predecessor.get('ledger_snapshot') != correction.get('ledger_snapshot')
                or predecessor.get('frozen_records') != correction.get('frozen_records')
                or predecessor.get('bookkeeping_baseline') != correction.get('bookkeeping_baseline')
                or correction.get('bookkeeping_transitions', [])[:len(predecessor.get('bookkeeping_transitions', []))]
                   != predecessor.get('bookkeeping_transitions', [])):
            raise ValueError('baseline correction predecessor changed')
    if correction.get('assessment'):
        strict_record(correction['assessment'])
    snap = baseline['ledger_snapshot']
    if correction.get('ledger_snapshot') != snap or document['ledger_baseline'] != snap:
        raise ValueError('baseline ledger snapshot substitution')
    records = baseline['preserved_records']
    status_path = str(Path(document['baseline']['path']).parent / 'status.md')
    frozen = [r for r in records if r['path'] not in (snap['path'], status_path)]
    bookkeeping = [r for r in records if r['path'] == status_path]
    if (not frozen or len(bookkeeping) != 1 or correction.get('frozen_records') != frozen
            or correction.get('bookkeeping_baseline') != bookkeeping[0]
            or [r for r in records if r['path'] == snap['path']] !=
                [{k: snap[k] for k in ('path', 'sha256', 'bytes')} ]):
        raise ValueError('exact baseline preservation categories required')
    for record in frozen:
        strict_record(record)
    if correction.get('bookkeeping_policy') != 'separate immutable old/new hash transitions; never scientific evidence':
        raise ValueError('explicit bookkeeping policy required')
    current = bookkeeping[0]
    for record in correction.get('bookkeeping_transitions', []):
        transition = read_json(strict_record(record)['path'])
        if (transition.get('schema') != 'plan034-s1-bookkeeping-transition/v1'
                or transition.get('old') != current or not transition.get('reason')
                or transition.get('new', {}).get('path') != status_path):
            raise ValueError('broken bookkeeping transition')
        current = transition['new']
    if file_record(status_path) != current:
        raise ValueError('unrecorded bookkeeping status change')
    n = snap['events']
    if type(n) is not int or not 0 < n <= len(events):
        raise ValueError('preserved ledger prefix required')
    previous = None
    for sequence, event in enumerate(events):
        payload = {k:v for k,v in event.items() if k != 'event_sha256'}
        if (event['sequence'] != sequence or event['previous_sha256'] != previous
                or object_hash(payload) != event['event_sha256']):
            raise ValueError('ledger corruption')
        previous = event['event_sha256']
    prefix = ''.join(canonical(e) + '\n' for e in events[:n]).encode()
    # Check actual bytes as well as parsed chain, including under the ledger lock.
    with safe_path(Path(local) / 'ledger.jsonl').open('rb') as stream:
        actual = stream.read(snap['bytes'])
    if (str((Path(local) / 'ledger.jsonl').resolve()) != snap['path']
            or actual != prefix or hashlib.sha256(prefix).hexdigest() != snap['sha256']
            or len(prefix) != snap['bytes'] or events[n-1]['event_sha256'] != snap['last_event_sha256']):
        raise ValueError('preserved ledger prefix required')
    lifecycle(events[n:], authorization, document)
    return [dict(record=r, matches=True) for r in frozen]


def lifecycle(events, authorization, document):
    """Validate only a caller-owned snapshot; never acquire a ledger lock."""
    admission = registration = reservation = temporary = started = finish = None
    for event in events:
        kind = event['event']
        if finish is not None:
            raise ValueError('S1 lifecycle append after finish')
        if kind == 'admission':
            value = read_json(strict_record(event['evidence'])['path'])
            if (admission is not None or registration is not None
                    or value.get('status') not in ('blocked', 'admitted')
                    or value.get('evidence', {}).get('s1_recovery_authorization') != authorization):
                raise ValueError('S1 lifecycle unrelated/duplicate admission')
            if value['status'] == 'admitted':
                admitted_event([event], authorization, document)
                admission = event
            continue
        if event.get('job_id') != JOB:
            raise ValueError('S1 lifecycle unrelated allocation/event')
        if kind == 'component_recovery_authorized':
            if (not admission or registration or event.get('authorization') != authorization
                    or event.get('admission') != admission['evidence']
                    or event.get('original_job_id') != 'S1-calibration'
                    or event.get('original_failure_event_sha256') != document['original_failure_event_sha256']
                    or any(event.get(k) != document[k] for k in BINDINGS)):
                raise ValueError('S1 lifecycle registration binding/order')
            registration = event
        elif kind == 'reserve':
            evidence = event.get('evidence', {})
            if (not registration or reservation
                    or evidence.get('authorization') != authorization
                    or evidence.get('authorization_event') != event_ref(registration)
                    or evidence.get('admission') != admission['evidence']
                    or any(evidence.get(k) != document[k] for k in BINDINGS if k != 'original_request_sha256')
                    or evidence.get('worker') != file_record(ROOT / 'scripts/basketball_vipe_worker.py')):
                raise ValueError('S1 lifecycle reservation binding/order')
            canonical_dispatch(document, authorization, evidence, command=event.get('command'))
            reservation = event
        elif kind == 'temporary_directory':
            if not reservation or temporary or started:
                raise ValueError('S1 lifecycle temporary directory order')
            temporary = event
        elif kind == 'started':
            if not reservation or not temporary or started:
                raise ValueError('S1 lifecycle orphan/duplicate start')
            started = event
        elif kind == 'gpu_ownership_failure':
            if not reservation or not event.get('phase') or not event.get('foreign_pids'):
                raise ValueError('S1 lifecycle ownership diagnostic outside active phase')
        elif kind == 'finish':
            if (not reservation or event.get('reservation') != event_ref(reservation)
                    or event.get('status') not in ('complete', 'failed')):
                raise ValueError('S1 lifecycle orphan/changed finish')
            receipt = event.get('terminal_receipt')
            if receipt:
                value = read_json(strict_record(receipt)['path'])
                if (value.get('reservation') != event_ref(reservation)
                        or value.get('authorization') != authorization
                        or value.get('baseline_correction') != document['baseline_correction']):
                    raise ValueError('S1 lifecycle terminal receipt binding')
            if event['status'] == 'complete' and (not started or not receipt or not event.get('acceptance')):
                raise ValueError('S1 lifecycle success lacks start/acceptance/receipt')
            finish = event
        else:
            raise ValueError('S1 lifecycle unrelated event')
    return dict(admission=admission, registration=registration, reservation=reservation,
                started=started, finish=finish)


def admitted_event(events, authorization, document):
    matches = []
    for event in events:
        if event['event'] != 'admission':
            continue
        value = read_json(strict_record(event['evidence'])['path'])
        if value.get('evidence', {}).get('s1_recovery_authorization') == authorization:
            matches.append((event, value))
    if not matches or matches[-1][1].get('status') != 'admitted':
        raise ValueError('successful amendment-bound admission required')
    event, value = matches[-1]
    evidence = value['evidence']
    for key in ('semantic_amendment', 'configuration', 'original_failure', 'e1_qualification',
                'e1_assets', 'e1_runtime', 'inputs', 'annotations', 'annotation_policy', 'annotation_review',
                'baseline_correction'):
        if evidence.get(key) != document[key]:
            raise ValueError('admission evidence changed: ' + key)
    if evidence.get('implementation_validation') != document['repair_validation']:
        raise ValueError('admission validation mismatch')
    return event['evidence']


def canonical_dispatch(document, authorization, evidence, *, command=None, reservation=None,
                       captured=None, local=None):
    """One read-only comparison for reservation, consumed state and launch."""
    historical = read_json(strict_record(document['historical_request'])['path'])
    original = {k:v for k,v in historical.items() if k != 'configuration'}
    if object_hash(original) != document['original_request_sha256']:
        raise ValueError('canonical historical request changed')
    expected = dict(original, job_id=JOB, recovery_authorization=authorization,
                    configuration=document['configuration'])
    request = read_json(strict_record(evidence['request'])['path'])
    worker = file_record(ROOT / 'scripts/basketball_vipe_worker.py')
    if (request != expected or request.get('branch') != 'calibration'
            or evidence.get('worker') != worker):
        raise ValueError('canonical dispatch request/worker changed')
    local = Path(local) if local is not None else Path(document['historical_request']['path']).parent.parent
    request_path = str((local / 'requests' / (JOB + '.json')).resolve())
    expected_command = [request['runtime']['python'], worker['path'], '--operation', 'component',
        '--config', document['configuration']['path'], '--request', request_path,
        '--output', str((local / 'jobs' / JOB).resolve())]
    if evidence['request']['path'] != request_path:
        raise ValueError('canonical request path changed')
    if command is not None and command != expected_command:
        raise ValueError('canonical launch command changed')
    if captured is not None and (reservation != captured or command != captured.get('command')):
        raise ValueError('captured active reservation changed')
    return expected_command


def active_binding(local, config, captured, command):
    from .ledger import Ledger
    events = Ledger(Path(local) / 'ledger.jsonl', config).events()
    document, _ = validate_binding(local, config, captured['evidence']['authorization'],
                                    events=events, consumed=True)
    active = Ledger(Path(local) / 'ledger.jsonl', config).states(events).get(JOB)
    if not active or active.get('event') != 'reserve':
        raise ValueError('missing active S1 reservation')
    canonical_dispatch(document, captured['evidence']['authorization'], active['evidence'],
        command=command, reservation=active, captured=captured, local=local)
    return document


def reservation_binding(local, config, events, evidence, command=None):
    document, original = validate_binding(local, config, evidence['authorization'], events=events)
    registered = [e for e in events if e['event'] == 'component_recovery_authorized' and e['job_id'] == JOB]
    if len(registered) != 1:
        raise ValueError('unique S1 registration required')
    event = registered[0]
    for key in BINDINGS:
        if event.get(key) != document[key] or (key != 'original_request_sha256' and evidence.get(key) != document[key]):
            raise ValueError('registered/reservation S1 binding changed')
    if (evidence.get('authorization_event') != event_ref(event)
            or evidence.get('admission') != event['admission']
            or admitted_event(events, evidence['authorization'], document) != event['admission']):
        raise ValueError('reservation admission/authorization event changed')
    canonical_dispatch(document, evidence['authorization'], evidence, command=command, local=local)
    return document


def resolved_result(local, config, events, finish):
    registered = [e for e in events if e['event'] == 'component_recovery_authorized' and e['job_id'] == JOB]
    if (len(registered) != 1 or finish.get('cleanup_confirmed') is not True
            or finish.get('surviving_pids') or finish.get('deadline_exceeded')
            or finish.get('stop_required') or finish.get('status') != 'complete'):
        raise ValueError('S1 result lacks unique supervised successful cleanup')
    event = registered[0]
    document, original = validate_binding(local, config, event['authorization'], events=events, consumed=True)
    if any(event.get(k) != document[k] for k in BINDINGS):
        raise ValueError('S1 registered terminal binding changed')
    reserves = [e for e in events if e['event'] == 'reserve' and e['job_id'] == JOB]
    if len(reserves) != 1 or reserves[0]['evidence']['authorization_event'] != event_ref(event):
        raise ValueError('S1 supervised reservation missing')
    request = dict(original, job_id=JOB, recovery_authorization=event['authorization'], configuration=document['configuration'])
    if read_json(strict_record(reserves[0]['evidence']['request'])['path']) != request:
        raise ValueError('S1 reserved request changed')
    result = read_json(strict_record(finish['result'])['path'])
    acceptance = read_json(strict_record(finish['acceptance'])['path'])
    receipt = read_json(strict_record(finish['terminal_receipt'])['path'])
    if (acceptance.get('schema') != 'plan035-s1-acceptance/v1' or acceptance.get('status') != 'passed'
            or acceptance.get('count') != 510 or acceptance.get('result') != finish['result']
            or acceptance.get('authorization') != event['authorization']
            or acceptance.get('baseline_correction') != document['baseline_correction']
            or acceptance.get('first_result') != result.get('first_result')
            or receipt.get('status') != 'complete' or receipt.get('acceptance') != finish['acceptance']
            or receipt.get('outcome', {}).get('result') != finish['result']):
        raise ValueError('S1 finish acceptance/receipt binding missing')
    if acceptance['records'] != referenced_records([result, request]):
        raise ValueError('S1 accepted referenced bytes changed')
    from .s1_evidence import validate_result_numerics
    validate_result_numerics(result, config)
    first = read_json(strict_record(result['first_result'])['path'])
    if not 0 <= first['elapsed_seconds_from_reservation'] <= finish['elapsed_seconds'] <= reserves[0]['seconds']:
        raise ValueError('S1 reservation-relative timing inconsistent')
    for field, limit in [('device_bytes','gpu_peak_device_gib_limit'), ('artifact_bytes','new_artifact_disk_gib_limit'), ('download_bytes','new_download_gib_limit')]:
        if finish.get('peak', {}).get(field, float('inf')) > config[limit]*2**30:
            raise ValueError('S1 supervised resource evidence missing/exceeded')
    return finish['result']


def referenced_records(value):
    """Collect exact resolved references without trusting a cached success flag."""
    found = {}
    def visit(value):
        if isinstance(value, dict):
            if {'path', 'sha256', 'bytes'} <= value.keys():
                record = {k:value[k] for k in ('path','sha256','bytes')}
                strict_record(record)
                old = found.setdefault(record['path'], record)
                if old != record:
                    raise ValueError('conflicting referenced file identities')
            for item in value.values(): visit(item)
        elif isinstance(value, list):
            for item in value: visit(item)
    visit(value)
    return sorted(found.values(), key=lambda r:r['path'])


def accept_result(local, config, request, result, output):
    from .s1_evidence import validate_result
    from .files import write_json
    document, _ = validate_binding(local, config, request['recovery_authorization'], consumed=True)
    validate_result(result, request, config)
    result_record = file_record(output / 'result.json')
    value = dict(schema='plan035-s1-acceptance/v1', status='passed', job_id=JOB,
        authorization=request['recovery_authorization'], baseline_correction=document['baseline_correction'],
        result=result_record, first_result=result['first_result'],
        records=referenced_records([result, request]), count=510)
    path = output / 'acceptance.json'
    write_json(path, value)
    return file_record(path)


def prepare_terminal_evidence(local, reservation, outcome, deadline):
    """All expensive optional evidence inspection belongs inside work time."""
    from .s1_evidence import reconcile_rows, evidence_counts, qualify_runtime, reconcile_first
    import time
    output = Path(local) / 'jobs' / JOB
    errors = []
    def optional(label, function):
        try:
            if time.monotonic() >= deadline:
                raise TimeoutError('evidence reconciliation work deadline')
            return dict(status='verified', value=function())
        except Exception as exc:
            errors.append(dict(evidence=label, error=f'{type(exc).__name__}: {exc}'))
            return dict(status='unverified', value=None)
    request = optional('request', lambda: read_json(strict_record(reservation['evidence']['request'])['path']))['value']
    result = optional('result', lambda: read_json(output / 'result.json'))['value']
    complete = not outcome.get('error') and bool(outcome.get('acceptance'))
    if complete:
        accepted = read_json(strict_record(outcome['acceptance'])['path'])
        if accepted['result'] != outcome['result']:
            raise ValueError('terminal acceptance/result conflict')
        identities = [r['identity'] for r in result['rows']]
        summary = dict(counts=evidence_counts(identities, identities, complete=True),
            produced_identities=identities, qualified_identities=identities,
            verification_errors=[], scan_complete=True)
    elif isinstance(request, dict):
        state = optional('rows', lambda: reconcile_rows(output, request, result=result, deadline=deadline))
        summary = state['value']
    else:
        summary = None
    summary = summary or dict(counts=evidence_counts(), scan_complete=False, verification_errors=[])
    runtime = {}
    if isinstance(request, dict):
        for name in ('initial-runtime.json', 'partial-runtime.json'):
            def inspect(name=name):
                record = file_record(output / name)
                qualify_runtime(read_json(record['path']), request)
                return record
            runtime[name] = optional(name, inspect)
        if isinstance(result, dict):
            runtime['final'] = optional('final_runtime', lambda: qualify_runtime(result['runtime'], request))
        summary['first_result'] = optional('first_result', lambda: reconcile_first(request, output,
            error=outcome.get('error') or 'worker did not publish first-result evidence'))
    summary['runtime'] = runtime
    summary['verification_errors'].extend(errors)
    return summary


def terminal_receipt(local, docs, config, authorization, *, error=None,
                     reservation=None, outcome=None):
    """Minimal identity is independent of optional, possibly corrupt evidence.

    Consumed publication is called only by the supervisor before finish. It
    cannot resolve a historical result or initiate another acceptance pass.
    """
    import time
    from .ledger import Ledger
    from .files import write_json
    events = Ledger(local / 'ledger.jsonl', config).events()
    if reservation is None:
        if any(e.get('job_id') == JOB and e['event'] == 'reserve' for e in events):
            raise ValueError('consumed S1 publication belongs to active supervisor')
        errors = []
        supplied = authorization.get('path') if isinstance(authorization, dict) else str(authorization)
        verified = None
        try:
            verified = strict_record(authorization) if isinstance(authorization, dict) else file_record(authorization)
            read_json(verified['path'])
        except (OSError, ValueError, KeyError, TypeError) as exc:
            errors.append(f'{type(exc).__name__}: {exc}')
        value = dict(schema='plan033-s1-pre-dispatch-block/v1', supplied_path=supplied,
            authorization=verified, verification_errors=errors, error=error,
            attempt_consumed=False, ledger_head=event_ref(events[-1]) if events else None)
        path = docs / ('S1-pre-dispatch-block-' + object_hash(value) + '.json')
    else:
        from .s1_evidence import qualify_row, qualify_runtime, reconcile_first
        output = local / 'jobs' / JOB
        outcome = dict(outcome or {})
        errors = []
        def optional(label, function):
            try:
                return dict(status='verified', value=function())
            except Exception as exc:
                errors.append(dict(evidence=label, error=f'{type(exc).__name__}: {exc}'))
                return dict(status='unverified', value=None)
        summary = outcome.get('evidence_summary') or dict(
            counts=__import__(__package__ + '.s1_evidence', fromlist=['evidence_counts']).evidence_counts(),
            scan_complete=False, verification_errors=[])
        first = summary.get('first_result', dict(status='unverified', value=None))
        runtime = summary.get('runtime', {})
        complete = not outcome.get('error') and bool(outcome.get('acceptance'))
        if complete and summary['counts'].get('complete') != 510:
            raise ValueError('complete terminal requires previously accepted evidence summary')
        counts = summary['counts']
        errors.extend(summary['verification_errors'])
        value = dict(schema='plan032-s1-calibration-recovery-receipt/v1',
            status='complete' if complete else 'failed', job_id=JOB, original_job_id='S1-calibration',
            authorization=reservation['evidence']['authorization'],
            baseline_correction=reservation['evidence']['baseline_correction'],
            reservation=event_ref(reservation), authorization_event=reservation['evidence']['authorization_event'],
            admission=reservation['evidence']['admission'], request=reservation['evidence']['request'],
            outcome=outcome, acceptance=outcome.get('acceptance'), first_result=first,
            runtime=runtime, evidence_summary=summary, counts=counts,
            verification_errors=errors, attempt_consumed=True, reconstruction_authorized=False,
            elapsed_through_preparation=time.monotonic()-reservation['monotonic_start'],
            timing_scope='finish charges publication and cleanup; receipt alone is not completion')
        path = docs / (JOB + '.json')
    if path.exists():
        if read_json(path) != value:
            raise ValueError('conflicting immutable terminal receipt')
    else:
        write_json(path, value)
    return file_record(path)
