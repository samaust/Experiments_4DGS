from .s1_progress import clock_match
from .s1_progress import checked_clock_reservation
"""Fail-closed binding for the one amendment-bound S1 calibration allocation.

Validation accepts a locked event snapshot so registration/reservation never
re-enter a ledger lock or derive a request through recovered-result lookup.
"""
from pathlib import Path

from .config import ROOT
from .files import file_record, object_hash, read_json, safe_path, verify_record
from .s1_progress import (checked_file_record as file_record,
    checked_verify_record as verify_record,checked_read_json as read_json)

SCHEMA = 'vipe-benchmark-s1-amendment-calibration-recovery/v1'
JOB = 'S1-calibration-recovery-001'
SCHEMA_2 = 'vipe-benchmark-s1-amendment-calibration-recovery/v2'
JOB_2 = 'S1-calibration-recovery-002'
SCHEMA_3 = 'vipe-benchmark-s1-amendment-calibration-recovery/v3'
JOB_3 = 'S1-calibration-recovery-003'
SCHEMA_4 = 'vipe-benchmark-s1-amendment-calibration-recovery/v4'
JOB_4 = 'S1-calibration-recovery-004'
SCHEMA_5 = 'vipe-benchmark-s1-amendment-calibration-recovery/v5'
JOB_5 = 'S1-calibration-recovery-005'
SCHEMA_6 = 'vipe-benchmark-s1-amendment-calibration-recovery/v6'
JOB_6 = 'S1-calibration-recovery-006'
SCHEMA_7 = 'vipe-benchmark-s1-amendment-calibration-recovery/v7'
JOB_7 = 'S1-calibration-recovery-007'
SCHEMA_8 = 'vipe-benchmark-s1-amendment-calibration-recovery/v8'
JOB_8 = 'S1-calibration-recovery-008'
AMENDMENT = 'plan031-s1-s0-token-sum-v1'
LIMITS = dict(gpu_concurrency=1, gpu_peak_device_gib_limit=22,
    gpu_total_seconds_limit=93600, cpu_max_workers=8,
    cpu_prepare_score_report_seconds_limit=57600, setup_wall_seconds_limit=57600,
    new_download_gib_limit=60, new_artifact_disk_gib_limit=150,
    new_setup_attempts=0, new_downloads=0, extra_smoke_jobs=0,
    reconstruction_attempts=0, cleanup_reserve_seconds_max=30)
BINDINGS = ('semantic_amendment', 'repair_validation', 'configuration',
            'original_request_sha256', 'baseline_correction')
PROCESS_FILE_AMENDMENT = ROOT / 'docs/research/vipe-alternatives/issue3-preparation/s1-process-file-amendment-001.json'
PROCESS_FILE_AMENDMENT_SHA256 = 'e273a23b2b5b594ce8e1deae48b659e27c3a8f4ee1b28d680ea21cfb005c84dc'
PROCESS_FILE_AMENDMENT_2 = ROOT / 'docs/research/vipe-alternatives/plan031-execution/s1-process-file-amendment-002.json'
PROCESS_FILE_AMENDMENT_2_SHA256 = 'fdcad90cb7fd680b5c6b0c536f20eea01b39b34019705d341a8456774ae10cb6'
PROCESS_FILE_AMENDMENT_3 = ROOT / 'docs/research/vipe-alternatives/plan031-execution/s1-process-file-amendment-003.json'
PROCESS_FILE_AMENDMENT_3_SHA256 = 'b3cc86ef987e7df4a54fcba0036bb95e5aca926f665831158718a1b6c60c00a2'


# Compatibility exports keep admission and execution on one static contract.
from .s1_validation_contract import (SUITES, source_paths, strict_record,
    required_cases, receipt_totals, validate_wrapper)


def strict_record(record):
    from .s1_progress import checked_strict_record
    return checked_strict_record(record)


def validation_record(record, amendment, configuration):
    return validate_wrapper(read_json(strict_record(record)['path']), amendment, configuration)


def event_ref(event):
    return {key: event[key] for key in ('sequence', 'event_sha256')}


def source_requalification_event(events):
    matches = [e for e in events if e['event'] == 's1_source_requalified']
    if len(matches) > 1:
        raise ValueError('duplicate S1 source requalification')
    return matches[0] if matches else None


def validate_source_requalification(event, registration, authorization, document):
    """Narrow source-only amendment; historical allocation/recipe stay intact."""
    note = read_json(strict_record(event['amendment'])['path'])
    if (event.get('job_id') != JOB or event.get('authorization') != authorization
            or note.get('schema') != 'plan066-s1-source-requalification/v1'
            or note.get('authorization') != authorization
            or note.get('registration') != event_ref(registration)
            or note.get('ledger_head') != event_ref(registration)
            or event['sequence'] != registration['sequence'] + 1
            or event['previous_sha256'] != registration['event_sha256']
            or note.get('previous_validation') != document['repair_validation']
            or note.get('scope') != 'resource-sampler-and-codex-launch; no new allocation; unchanged deadlines'):
        raise ValueError('S1 source requalification identity/scope/order')
    for key in ('approval', 'plan', 'review'):
        strict_record(note[key])
    old = read_json(strict_record(note['previous_validation'])['path'])
    new = read_json(strict_record(note['validation'])['path'])
    before, after = old['sources'], new['sources']
    paths = [str(p) for p in source_paths()]
    if ([r['path'] for r in before] != paths or [r['path'] for r in after] != paths):
        raise ValueError('S1 source requalification exact source membership')
    changed = [(a,b) for a,b in zip(before, after) if a != b]
    allowed = {str(ROOT / p) for p in (
        'scripts/vipe_benchmark/budgets.py', 'scripts/vipe_benchmark/s1_recovery.py',
        'scripts/vipe_benchmark/execution.py', 'tests/test_vipe_benchmark_budgets.py',
        'scripts/vipe_benchmark/s1_helper_session.py',
        'scripts/vipe_benchmark/s1_validation_contract.py',
        'scripts/vipe_benchmark/supervisor.py',
        'tests/test_vipe_benchmark_s1_helper_fixtures.py',
        'tests/test_vipe_benchmark_supervisor.py',
        'tests/test_vipe_benchmark_s1_recovery.py')}
    changes = note.get('changes')
    if (not changed or not {a['path'] for a,b in changed} <= allowed
            or type(changes) is not list or len(changes) != len(changed)):
        raise ValueError('S1 source requalification changed-source scope')
    for (a,b), change in zip(changed, changes):
        snapshot = strict_record(change['old_snapshot'])
        if (change.get('before') != a or change.get('after') != b
                or any(snapshot[k] != a[k] for k in ('bytes', 'sha256'))):
            raise ValueError('S1 source requalification historical source snapshot')
        strict_record(b)
    return note['validation']


def register_source_requalification(local, config, amendment):
    """Validate a prospective append under lock; never rewrite registration."""
    import time
    from .ledger import Ledger
    amendment = strict_record(amendment)
    note = read_json(amendment['path'])
    ledger = Ledger(Path(local) / 'ledger.jsonl', config)
    with ledger.locked() as (stream, events):
        if source_requalification_event(events) is not None:
            raise ValueError('duplicate S1 source requalification')
        payload = dict(event='s1_source_requalified', job_id=JOB,
                       authorization=note['authorization'], amendment=amendment)
        candidate = dict(payload, sequence=len(events), previous_sha256=events[-1]['event_sha256'],
                         recorded_unix=time.time())
        candidate['event_sha256'] = object_hash(candidate)
        validate_binding(local, config, note['authorization'], events=events + [candidate])
        return ledger._append(stream, events, payload)


def validate_fifth_review(document):
    """Exact reviewed proposal plus one explicit approval; no allocation drift."""
    proposal = read_json(strict_record(document.get('review_proposal'))['path'])
    if (proposal.get('schema') != {JOB_5: SCHEMA_5, JOB_6: SCHEMA_6, JOB_7: SCHEMA_7, JOB_8: SCHEMA_8}.get(document.get('job_id'))
            or proposal.get('job_id') != document.get('job_id')
            or proposal.get('additional_attempt_approved') is not False
            or proposal.get('authorization_context', {}).get('stage') != 'REVIEW'
            or proposal.get('required_rows') != 510
            or proposal.get('row_metadata_bytes_limit') != 256*1024
            or proposal.get('resource_sample_seconds') != 2.):
        raise ValueError('exact fifth REVIEW proposal required')
    expected = dict(proposal, additional_attempt_approved=True,
        authorization=document['authorization'],
        authorization_context=dict(proposal['authorization_context'], stage='DO'),
        review_proposal=document['review_proposal'])
    if document != expected:
        raise ValueError('fifth DO differs from the exact REVIEW proposal')


def validate_sixth_predecessor(finish, authorization, *, job=JOB_5):
    """Keep the exact consumed predecessor terminal evidence bound."""
    if job == JOB_7:
        if (finish.get('sequence') != 546
                or finish.get('event_sha256') != 'dce4f9418bc8794715467ff24201f914682ef7c07294fbcea02be48d21fb8d6b'
                or finish.get('status') != 'failed' or finish.get('result') is not None
                or finish.get('acceptance') is not None or finish.get('stop_required') is not True
                or finish.get('terminal_receipt') is not None
                or finish.get('terminal_publication_status') != 'unavailable'
                or finish.get('terminal_publication_block_reason') != 'poisoned_helper'
                or finish.get('cleanup_confirmed') is not True or finish.get('cleanup_uncertain') is not False
                or finish.get('surviving_pids')):
            raise ValueError('eighth requires exact stopped seventh failure without terminal receipt')
        return
    terminal = read_json(strict_record(finish.get('terminal_receipt'))['path'])
    if job == JOB_6 and (finish.get('sequence') != 535
            or finish.get('event_sha256') != 'ca7f1cc0fbdeb0b065b5bc059b6f9901dd41ada81d1a7172aba819c7fe82f915'):
        raise ValueError('seventh requires exact consumed sixth finish')
    if (terminal.get('job_id') != job or terminal.get('status') != 'failed'
            or terminal.get('authorization') != authorization
            or terminal.get('reservation') != finish.get('reservation')
            or terminal.get('attempt_consumed') is not True
            or terminal.get('reconstruction_authorized') is not False):
        raise ValueError('new S1 recovery requires exact consumed predecessor terminal receipt')


def operational_stop_resolution(finish, validation, implementation_review):
    """Read-only evidence for a separately approved new identity; no old promotion."""
    validate_sixth_predecessor(finish, None, job=JOB_7)
    approval = strict_record(file_record(ROOT / 'docs/research/vipe-alternatives/plan067-execution/fresh-runtime-attempts-approval-002.json'))
    if approval['sha256'] != 'f4571bfab60283dd10302f1afdfa9acac0543ed3a29f1c6e09971b72451accae':
        raise ValueError('exact new eighth attempt approval required')
    document = read_json(approval['path'])
    if (document.get('schema') != 'plan067-fresh-runtime-attempt-approval/v1'
            or document.get('scope', {}).get('S1') != dict(job_id=JOB_8, branch='calibration', attempts=1, seconds_limit=3600)):
        raise ValueError('explicit eighth calibration scope required')
    strict_record(document['approved_proposal'])
    strict_record(validation); strict_record(implementation_review)
    return dict(schema='plan067-s1-operational-stop-resolution/v1', approval=approval,
        stopped_finish=event_ref(finish), correction_validation=validation,
        correction_review=implementation_review, historical_stop_preserved=True,
        unavailable_terminal_preserved=True, previous_result_accepted=False,
        scope='one fresh008 calibration only; preserve failed007 and poisoned helper; no reconstruction')


def validate_operational_stop_resolution(document):
    expected = operational_stop_resolution(document['previous_recovery_failure'],
        document['repair_validation'], document['implementation_review'])
    if (document.get('operational_stop_resolution') != expected
            or document['authorization'] != read_json(expected['approval']['path'])['user_authorization']):
        raise ValueError('exact eighth operational stop resolution and approval required')


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
    job = document.get('job_id')
    if job not in (JOB, JOB_2, JOB_3, JOB_4, JOB_5, JOB_6, JOB_7, JOB_8):
        raise ValueError('unrecognized S1 recovery identity')
    required = dict(schema={JOB: SCHEMA, JOB_2: SCHEMA_2, JOB_3: SCHEMA_3, JOB_4: SCHEMA_4, JOB_5: SCHEMA_5, JOB_6: SCHEMA_6, JOB_7: SCHEMA_7, JOB_8: SCHEMA_8}[job], job_id=job, original_job_id='S1-calibration',
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
    if job in (JOB_5, JOB_6, JOB_7, JOB_8):
        validate_fifth_review(document)
    if job == JOB_8:
        validate_operational_stop_resolution(document)
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
    requalification = source_requalification_event(events) if job == JOB else None
    validation_ref = (read_json(strict_record(requalification['amendment'])['path'])['validation']
                      if requalification else document['repair_validation'])
    validation = validation_record(validation_ref, document['semantic_amendment'], configuration)
    if validation.get('baseline') != document['baseline'] or validation.get('plan') != document['plan'] or validation.get('baseline_correction') != document['baseline_correction']:
        raise ValueError('validation baseline/plan mismatch')
    prior = [e for e in events if e['event'] == 'component_recovery_authorized'
             and e['original_job_id'].startswith('S1-')]
    if job == JOB:
        if prior and (len(prior) != 1 or prior[0]['job_id'] != JOB or prior[0]['authorization'] != authorization):
            raise ValueError('different or second S1 allocation')
    elif job == JOB_2:
        predecessor = strict_record(document['previous_recovery_authorization'])
        finished = states.get(JOB, {})
        if (len(prior) not in (1, 2) or prior[0]['job_id'] != JOB
                or prior[0]['authorization'] != predecessor
                or any(event['job_id'] != JOB_2 or event['authorization'] != authorization for event in prior[1:])
                or finished.get('event') != 'finish' or finished.get('status') != 'failed'
                or finished.get('cleanup_confirmed') is not True or finished.get('surviving_pids')
                or finished.get('event_sha256') != document.get('previous_recovery_failure_event_sha256')):
            raise ValueError('new S1 identity requires the exact consumed cleaned-up predecessor')
    elif job == JOB_3:
        predecessor = strict_record(document['previous_recovery_authorization'])
        finished = states.get(JOB_2, {})
        if (len(prior) not in (2, 3) or [event['job_id'] for event in prior[:2]] != [JOB, JOB_2]
                or prior[0]['authorization'] != read_json(predecessor['path'])['previous_recovery_authorization']
                or prior[1]['authorization'] != predecessor
                or any(event['job_id'] != JOB_3 or event['authorization'] != authorization for event in prior[2:])
                or finished.get('event') != 'finish' or finished.get('status') != 'failed'
                or finished.get('cleanup_confirmed') is not True or finished.get('cleanup_uncertain') is not False
                or finished.get('surviving_pids') or finished.get('event_sha256') != document.get('previous_recovery_failure_event_sha256')):
            raise ValueError('third S1 identity requires exact consumed cleaned-up second attempt')
    elif job == JOB_4:
        predecessor = strict_record(document['previous_recovery_authorization'])
        finished = states.get(JOB_3, {})
        if (len(prior) not in (3, 4) or [event['job_id'] for event in prior[:3]] != [JOB, JOB_2, JOB_3]
                or prior[0]['authorization'] != read_json(
                    read_json(predecessor['path'])['previous_recovery_authorization']['path'])['previous_recovery_authorization']
                or prior[1]['authorization'] != read_json(predecessor['path'])['previous_recovery_authorization']
                or prior[2]['authorization'] != predecessor
                or any(event['job_id'] != JOB_4 or event['authorization'] != authorization for event in prior[3:])
                or finished.get('event') != 'finish' or finished.get('status') != 'failed'
                or finished.get('cleanup_confirmed') is not True or finished.get('cleanup_uncertain') is not False
                or finished.get('surviving_pids') or finished.get('event_sha256') != document.get('previous_recovery_failure_event_sha256')):
            raise ValueError('fourth S1 identity requires exact consumed cleaned-up third attempt')
    else:
        predecessor = strict_record(document['previous_recovery_authorization'])
        chain = [JOB, JOB_2, JOB_3, JOB_4] + ([JOB_5] if job in (JOB_6, JOB_7, JOB_8) else []) + ([JOB_6] if job in (JOB_7, JOB_8) else []) + ([JOB_7] if job == JOB_8 else [])
        finished = states.get(chain[-1], {})
        count = len(chain)
        if job in (JOB_6, JOB_7, JOB_8) and len(prior) >= count:
            linked = predecessor
            for index in range(count - 1, -1, -1):
                if linked != prior[index]['authorization']:
                    raise ValueError('sixth predecessor authorization chain changed')
                linked_document = read_json(strict_record(linked)['path'])
                if index:
                    linked = linked_document['previous_recovery_authorization']
        if (len(prior) not in (count, count + 1) or [event['job_id'] for event in prior[:count]] != chain
                or prior[count-1]['authorization'] != predecessor
                or any(event['job_id'] != job or event['authorization'] != authorization for event in prior[count:])
                or finished.get('event') != 'finish' or finished.get('status') != 'failed'
                or finished.get('cleanup_confirmed') is not True or finished.get('cleanup_uncertain') is not False
                or finished.get('surviving_pids') or finished != document.get('previous_recovery_failure')
                or finished.get('event_sha256') != document.get('previous_recovery_failure_event_sha256')):
            raise ValueError('fifth S1 identity requires exact consumed cleaned-up fourth attempt')
    if not consumed and (job in states or any(s['event'] == 'reserve' for s in states.values())):
        raise ValueError('consumed S1 identity or active attempt')
    total = ledger.totals(events)['gpu']
    if not consumed and (total['elapsed_seconds'] + total['reserved_seconds'] >= 93600
            or (job in (JOB_5, JOB_6, JOB_7, JOB_8) and total['elapsed_seconds'] + total['reserved_seconds'] + 3600 > 93600)):
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


def preservation(local, document, events, authorization, *, process_amendment_override=None):
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
    process_amendment = process_amendment_override or document.get('process_file_amendment')
    sixth_amendment = document['job_id'] in (JOB_6, JOB_7, JOB_8) or process_amendment_override is not None
    eighth_amendment = document['job_id'] == JOB_8 or (process_amendment_override is not None
        and process_amendment_override.get('sha256') == PROCESS_FILE_AMENDMENT_3_SHA256)
    amended_record = None
    if process_amendment is not None:
        expected_amendment = PROCESS_FILE_AMENDMENT_3 if eighth_amendment else PROCESS_FILE_AMENDMENT_2 if sixth_amendment else PROCESS_FILE_AMENDMENT
        expected_sha256 = PROCESS_FILE_AMENDMENT_3_SHA256 if eighth_amendment else PROCESS_FILE_AMENDMENT_2_SHA256 if sixth_amendment else PROCESS_FILE_AMENDMENT_SHA256
        if (strict_record(process_amendment) != file_record(expected_amendment)
                or process_amendment['sha256'] != expected_sha256):
            raise ValueError('exact S1 process-file amendment required')
        note = read_json(process_amendment['path'])
        agents = [record for record in frozen if record['path'] == str((ROOT / 'AGENTS.md').resolve())]
        if (len(agents) != 1 or set(note) != {'schema', 'issue', 'scope', 'baseline',
                'baseline_correction', 'old', 'new'} | ({'previous_amendment'} if sixth_amendment else set())
                or note['schema'] != ('plan031-s1-process-file-preservation-amendment/v3' if eighth_amendment else 'plan031-s1-process-file-preservation-amendment/v2' if sixth_amendment else 'plan031-s1-process-file-preservation-amendment/v1')
                or note['issue'] != 3
                or note['scope'] != 'AGENTS.md process instructions only; no scientific input, allocation, attempt, or approval change'
                or note['baseline'] != document['baseline']
                or note['baseline_correction'] != document['baseline_correction']
                or note['old'] != agents[0]
                or note['new'] != file_record(ROOT / 'AGENTS.md')):
            raise ValueError('S1 process-file preservation scope changed')
        if eighth_amendment:
            if (strict_record(note['previous_amendment']) != file_record(PROCESS_FILE_AMENDMENT_2)
                    or note['previous_amendment']['sha256'] != PROCESS_FILE_AMENDMENT_2_SHA256):
                raise ValueError('historical second process-file amendment changed')
            note = read_json(note['previous_amendment']['path'])
        if sixth_amendment and (strict_record(note['previous_amendment']) != file_record(PROCESS_FILE_AMENDMENT)
                or note['previous_amendment']['sha256'] != PROCESS_FILE_AMENDMENT_SHA256):
            raise ValueError('historical process-file amendment changed')
        if not eighth_amendment:
            strict_record(note['new'])
        amended_record = agents[0]
    for record in frozen:
        if record != amended_record:
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
    if document['job_id'] in (JOB_5, JOB_6, JOB_7, JOB_8):
        eighth = document['job_id'] == JOB_8
        seventh = document['job_id'] in (JOB_7, JOB_8)
        sixth = document['job_id'] in (JOB_6, JOB_7, JOB_8)
        count_predecessor = 547 if eighth else 536 if seventh else 520 if sixth else 472
        prior = strict_record(document['prior_ledger_snapshot'])
        expected = ROOT / ('docs/research/vipe-alternatives/plan031-execution/s1-recovery-007/outcome/ledger-after.jsonl' if eighth else 'docs/research/vipe-alternatives/plan031-execution/s1-recovery-006/outcome/ledger-after.jsonl' if seventh else 'docs/research/vipe-alternatives/plan031-execution/s1-recovery-005/outcome/ledger-after.jsonl' if sixth else 'docs/research/vipe-alternatives/issue3-preparation/s1-dispatch-004-outcome/post-dispatch-ledger-004.jsonl')
        previous_record = strict_record(document['previous_recovery_authorization'])
        previous = read_json(previous_record['path'])
        if (prior != file_record(expected) or previous.get('job_id') != (JOB_7 if eighth else JOB_6 if seventh else JOB_5 if sixth else JOB_4)
                or len(events) < count_predecessor or events[count_predecessor-1] != document['previous_recovery_failure']):
            raise ValueError('fifth consumed predecessor snapshot changed')
        if sixth:
            validate_sixth_predecessor(events[count_predecessor-1], previous_record, job=JOB_7 if eighth else JOB_6 if seventh else JOB_5)
        preservation(local, previous, events[:count_predecessor], previous_record,
                     process_amendment_override=process_amendment if sixth_amendment else None)
        live = document['live_ledger_snapshot']
        count = live.get('events')
        if type(count) is not int or not count_predecessor <= count <= len(events):
            raise ValueError('fifth REVIEW live ledger prefix required')
        prefix = ''.join(canonical(event) + '\n' for event in events[:count]).encode()
        if (live != dict(path=str((Path(local) / 'ledger.jsonl').resolve()), bytes=len(prefix),
                sha256=hashlib.sha256(prefix).hexdigest(), events=count,
                last_event_sha256=events[count-1]['event_sha256'], active_jobs=[])
                or (Path(local) / 'ledger.jsonl').read_bytes()[:len(prefix)] != prefix):
            raise ValueError('fifth REVIEW live ledger prefix changed')
        lifecycle(events[count:], authorization, document)
    elif document['job_id'] in (JOB_2, JOB_3, JOB_4):
        prior = strict_record(document['prior_ledger_snapshot'])
        snapshot = ('requalification-066/post-dispatch-ledger.jsonl' if document['job_id'] == JOB_2
                    else 'requalification-067/post-dispatch-ledger-002.jsonl' if document['job_id'] == JOB_3
                    else 'requalification-069/post-dispatch-ledger-003.jsonl')
        if prior['path'] != str((ROOT / 'docs/continuous-improvement/plan031-s1-recovery-20260919' / snapshot).resolve()):
            raise ValueError('wrong consumed predecessor snapshot')
        frozen_bytes = Path(prior['path']).read_bytes()
        live_bytes = (Path(local) / 'ledger.jsonl').read_bytes()
        count = {JOB_2: 453, JOB_3: 459, JOB_4: 467}[document['job_id']]
        predecessor_job = {JOB_2: JOB, JOB_3: JOB_2, JOB_4: JOB_3}[document['job_id']]
        if (len(frozen_bytes) != prior['bytes'] or not live_bytes.startswith(frozen_bytes)
                or len(events) < count or events[count-1].get('event') != 'finish'
                or events[count-1].get('job_id') != predecessor_job
                or events[count-1].get('event_sha256') != document.get('previous_recovery_failure_event_sha256')):
            raise ValueError('consumed S1 prefix changed')
        if document['job_id'] in (JOB_3, JOB_4):
            previous = read_json(document['previous_recovery_authorization']['path'])
            start = 453 if document['job_id'] == JOB_3 else 459
            lifecycle(events[start:count], document['previous_recovery_authorization'], previous)
        lifecycle(events[count:], authorization, document)
    else:
        lifecycle(events[n:], authorization, document)
    return [dict(record=r, matches=True) for r in frozen]


def lifecycle(events, authorization, document):
    """Validate only a caller-owned snapshot; never acquire a ledger lock."""
    admission = registration = reservation = temporary = started = finish = requalification = None
    job = document['job_id']
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
        if event.get('job_id') != job:
            raise ValueError('S1 lifecycle unrelated allocation/event')
        if kind == 'component_recovery_authorized':
            if (not admission or registration or event.get('authorization') != authorization
                    or event.get('admission') != admission['evidence']
                    or event.get('original_job_id') != 'S1-calibration'
                    or event.get('original_failure_event_sha256') != document['original_failure_event_sha256']
                    or any(event.get(k) != document[k] for k in BINDINGS)):
                raise ValueError('S1 lifecycle registration binding/order')
            registration = event
        elif kind == 's1_source_requalified':
            if job != JOB or registration is None or reservation is not None or requalification is not None:
                raise ValueError('S1 source requalification order/duplicate')
            validate_source_requalification(event, registration, authorization, document)
            requalification = event
        elif kind == 'reserve':
            evidence = event.get('evidence', {})
            if evidence.get('source_requalification') != (event_ref(requalification) if requalification else None):
                raise ValueError('S1 reservation source requalification binding')
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
        elif kind == 'monitor_gap_recovered':
            if (not started or job not in (JOB_3, JOB_4, JOB_5, JOB_6, JOB_7, JOB_8) or type(event.get('expired_samples')) is not int
                    or event['expired_samples'] < 1 or type(event.get('gap_seconds')) not in (int, float)
                    or not 0 < event['gap_seconds'] <= 15):
                raise ValueError('S1 recovered monitor gap outside bounded worker phase')
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
    job = document['job_id']
    expected = dict(original, job_id=job, recovery_authorization=authorization,
                    configuration=document['configuration'])
    request = read_json(strict_record(evidence['request'])['path'])
    worker = file_record(ROOT / 'scripts/basketball_vipe_worker.py')
    if (request != expected or request.get('branch') != 'calibration'
            or evidence.get('worker') != worker):
        raise ValueError('canonical dispatch request/worker changed')
    local = Path(local) if local is not None else Path(document['historical_request']['path']).parent.parent
    request_path = str((local / 'requests' / (job + '.json')).resolve())
    expected_command = [request['runtime']['python'], worker['path'], '--operation', 'component',
        '--config', document['configuration']['path'], '--request', request_path,
        '--output', str((local / 'jobs' / job).resolve())]
    if evidence['request']['path'] != request_path:
        raise ValueError('canonical request path changed')
    if command is not None and command != expected_command:
        raise ValueError('canonical launch command changed')
    if captured is not None and (reservation != captured or command != captured.get('command')):
        raise ValueError('captured active reservation changed')
    return expected_command


def active_binding(local, config, captured, command, *, with_reservation=False):
    from .ledger import Ledger
    events = Ledger(Path(local) / 'ledger.jsonl', config).events()
    states = Ledger(Path(local) / 'ledger.jsonl', config).states(events)
    active = states.get(captured['job_id']) if captured is not None else next(
        (states.get(job) for job in (JOB_8, JOB_7, JOB_6, JOB_5, JOB_4, JOB_3, JOB_2, JOB) if states.get(job, {}).get('event') == 'reserve'), None)
    if not active or active.get('event') != 'reserve':
        raise ValueError('missing active S1 reservation')
    from .s1_clock import typed_equal
    captured = active if captured is None else captured
    if not typed_equal(active, captured):
        raise ValueError('captured active reservation changed')
    document, _ = validate_binding(local, config, captured['evidence']['authorization'], events=events, consumed=True)
    canonical_dispatch(document, captured['evidence']['authorization'], active['evidence'],
        command=command, reservation=active, captured=captured, local=local)
    return (document, active) if with_reservation else document


def captured_clock(local, config, reservation, command):
    from .s1_progress import operation,reservation_deadline
    if type(reservation) is not dict:
        raise ValueError('captured reservation required for helper clock')
    return operation(_captured_clock,local,config,reservation,command,deadline=reservation_deadline(reservation))


def _captured_clock(local, config, reservation, command):
    from .s1_clock import ReservationClock
    if type(reservation) is not dict:
        raise ValueError('captured reservation required for helper clock')
    _, active = active_binding(local, config, reservation, command, with_reservation=True)
    return checked_clock_reservation(active)


def worker_clock(args, request, config):
    import json
    import os
    import sys
    from .s1_clock import ReservationClock
    path = args.request.resolve()
    if request.get('job_id') not in (JOB, JOB_2, JOB_3, JOB_4, JOB_5, JOB_6, JOB_7, JOB_8) or path.name != request['job_id'] + '.json' or path.parent.name != 'requests':
        raise ValueError('canonical worker request path required')
    local = path.parent.parent
    command = [request['runtime']['python'], str((ROOT / 'scripts/basketball_vipe_worker.py').resolve()),
        '--operation', args.operation, '--config', str(args.config.resolve()),
        '--request', str(path), '--output', str(args.output.resolve())]
    if (Path(sys.executable).resolve() != Path(request['runtime']['python']).resolve()
            or Path(sys.argv[0]).resolve() != ROOT / 'scripts/basketball_vipe_worker.py'):
        raise ValueError('canonical worker interpreter/script changed')
    if sys.argv[1:] != command[2:]:
        raise ValueError('canonical worker arguments changed')
    _, reservation = active_binding(local, config, None, command, with_reservation=True)
    clock = checked_clock_reservation(reservation)
    if read_json(strict_record(clock.mapping()['request'])['path']) != request:
        raise ValueError('canonical worker request changed')
    try:
        transported = json.loads(os.environ['VIPE_S1_RESERVATION_CLOCK'])
    except (KeyError, ValueError) as exc:
        raise ValueError('missing/invalid transported reservation clock') from exc
    clock_match(clock,transported)
    clock.observe()
    return clock


def reservation_binding(local, config, events, evidence, command=None):
    document, original = validate_binding(local, config, evidence['authorization'], events=events)
    job = document['job_id']
    requalification = source_requalification_event(events) if job == JOB else None
    if evidence.get('source_requalification') != (event_ref(requalification) if requalification else None):
        raise ValueError('S1 reservation source requalification binding')
    registered = [e for e in events if e['event'] == 'component_recovery_authorized' and e['job_id'] == job]
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
    job = finish.get('job_id')
    if job not in (JOB, JOB_2, JOB_3, JOB_4, JOB_5, JOB_6, JOB_7, JOB_8): raise ValueError('S1 result identity')
    registered = [e for e in events if e['event'] == 'component_recovery_authorized' and e['job_id'] == job]
    if (len(registered) != 1 or finish.get('cleanup_confirmed') is not True
            or finish.get('surviving_pids') or finish.get('deadline_exceeded')
            or finish.get('stop_required') or finish.get('status') != 'complete'):
        raise ValueError('S1 result lacks unique supervised successful cleanup')
    event = registered[0]
    document, original = validate_binding(local, config, event['authorization'], events=events, consumed=True)
    if any(event.get(k) != document[k] for k in BINDINGS):
        raise ValueError('S1 registered terminal binding changed')
    reserves = [e for e in events if e['event'] == 'reserve' and e['job_id'] == job]
    if len(reserves) != 1 or reserves[0]['evidence']['authorization_event'] != event_ref(event):
        raise ValueError('S1 supervised reservation missing')
    request = dict(original, job_id=job, recovery_authorization=event['authorization'], configuration=document['configuration'])
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
    from .s1_clock import ReservationClock
    clock = checked_clock_reservation(reserves[0])
    for value in (first, result, acceptance):
        clock_match(clock,value.get('reservation_clock'))
    clock.recorded(first.get('elapsed_seconds_from_reservation'), 'passed')
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


def accept_result(local, config, request, result, output, *, reservation):
    from .s1_progress import operation,reservation_deadline
    return operation(_accept_result,local,config,request,result,output,reservation=reservation,
        deadline=reservation_deadline(reservation))


def _accept_result(local, config, request, result, output, *, reservation):
    from .s1_evidence import validate_result
    from .files import write_json
    from .s1_progress import checked_read_json as read_json,checked_file_record as file_record,write_exclusive,encode
    document = active_binding(local, config, reservation, reservation['command'])
    clock = captured_clock(local, config, reservation, reservation['command'])
    if read_json(strict_record(clock.mapping()['request'])['path']) != request:
        raise ValueError('accepted request differs from reservation')
    clock.observe()
    validate_result(result, request, config, clock=clock,deadline=clock.work_deadline)
    clock.observe()
    result_record = file_record(output / 'result.json')
    value = dict(schema='plan035-s1-acceptance/v1', status='passed', job_id=request['job_id'],
        authorization=request['recovery_authorization'], baseline_correction=document['baseline_correction'],
        result=result_record, first_result=result['first_result'], reservation_clock=clock.mapping(),
        records=referenced_records([result, request]), count=510)
    path = output / 'acceptance.json'
    return write_exclusive(path,encode(value,32*1024*1024))


def prepare_terminal_evidence(local, reservation, outcome, deadline, *, config, publisher=None):
    from .s1_progress import operation
    return operation(_prepare_terminal_evidence,local,reservation,outcome,deadline,config=config,
        publisher=publisher,deadline=deadline)


def _prepare_terminal_evidence(local, reservation, outcome, deadline, *, config, publisher=None):
    """All expensive optional evidence inspection belongs inside work time."""
    from .s1_evidence import reconcile_rows, evidence_counts, qualify_runtime, reconcile_first
    from .s1_progress import checked_read_json as read_json,checked_file_record as file_record
    import time
    output = Path(local) / 'jobs' / reservation['job_id']
    errors = []
    def optional(label, function):
        try:
            if time.monotonic() >= deadline:
                raise TimeoutError('evidence reconciliation work deadline')
            value=function()
            if time.monotonic() >= deadline:raise TimeoutError('evidence operation completed at work deadline')
            return dict(status='verified', value=value)
        except Exception as exc:
            errors.append(dict(evidence=label, error=f'{type(exc).__name__}: {exc}'))
            return dict(status='unverified', value=None)
    clock_state = optional('reservation_clock', lambda: captured_clock(local, config, reservation, reservation['command']))
    clock = clock_state['value']
    request = optional('request', lambda: read_json(strict_record(reservation['evidence']['request'])['path']))['value']
    result = optional('result', lambda: read_json(output / 'result.json'))['value']
    complete = not outcome.get('error') and bool(outcome.get('acceptance'))
    if complete:
        if time.monotonic() >= deadline:raise TimeoutError('complete evidence work deadline')
        accepted = read_json(strict_record(outcome['acceptance'])['path'])
        if time.monotonic() >= deadline:raise TimeoutError('complete evidence read reached work deadline')
        if accepted['result'] != outcome['result']:
            raise ValueError('terminal acceptance/result conflict')
        if publisher is not None:
            from .s1_progress import accepted_progress
            accepted_progress(publisher,result,outcome['result'],outcome['acceptance'])
        identities = [r['identity'] for r in result['rows']]
        summary = dict(counts=evidence_counts(identities, identities, complete=True),
            produced_identities=identities, qualified_identities=identities,
            verification_errors=[], scan_complete=True)
    elif isinstance(request, dict):
        state = optional('rows', lambda: reconcile_rows(output, request, result=result, deadline=deadline, publisher=publisher))
        summary = state['value']
    else:
        summary = None
    summary = summary or dict(counts=evidence_counts(), scan_complete=False, verification_errors=[])
    runtime = {}
    if isinstance(request, dict):
        for name in ('initial-runtime.json', 'partial-runtime.json'):
            def inspect(name=name):
                record = file_record(output / name)
                qualify_runtime(read_json(record['path']), request,deadline=deadline)
                if time.monotonic() >= deadline:raise TimeoutError('runtime verification completed late')
                if publisher is not None:
                    publisher.runtime[name]=record
                    publisher.publish()
                return record
            runtime[name] = optional(name, inspect)
        if isinstance(result, dict):
            def final_runtime():
                qualify_runtime(result['runtime'],request,deadline=deadline)
                if time.monotonic() >= deadline:raise TimeoutError('final runtime verification completed late')
                record=file_record(output/'result.json')
                if publisher is not None:publisher.runtime['final']=record;publisher.publish()
                return record
            runtime['final'] = optional('final_runtime', final_runtime)
        summary['first_result'] = optional('first_result', lambda: reconcile_first(request, output,
            clock=clock, error=outcome.get('error') or 'worker did not publish first-result evidence'))
    if publisher is not None and summary.get('first_result',{}).get('status')=='verified':
        if time.monotonic() >= deadline:raise TimeoutError('first verification completed late')
        publisher.first_result=summary['first_result']['value'];publisher.publish()
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
    supplied_document = None
    try:
        supplied_document = read_json(authorization['path'] if isinstance(authorization, dict) else authorization)
    except (OSError, ValueError, KeyError, TypeError):
        pass
    job = reservation['job_id'] if reservation is not None else (
        supplied_document.get('job_id', JOB) if isinstance(supplied_document, dict) else JOB)
    if job not in (JOB, JOB_2, JOB_3, JOB_4, JOB_5, JOB_6, JOB_7, JOB_8): raise ValueError('S1 terminal identity')
    if reservation is None:
        if any(e.get('job_id') == job and e['event'] == 'reserve' for e in events):
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
        output = local / 'jobs' / job
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
            status='complete' if complete else 'failed', job_id=job, original_job_id='S1-calibration',
            authorization=reservation['evidence']['authorization'],
            baseline_correction=reservation['evidence']['baseline_correction'],
            reservation=event_ref(reservation), authorization_event=reservation['evidence']['authorization_event'],
            admission=reservation['evidence']['admission'], request=reservation['evidence']['request'],
            source_requalification=reservation['evidence'].get('source_requalification'),
            outcome=outcome, acceptance=outcome.get('acceptance'), first_result=first,
            runtime=runtime, evidence_summary=summary, counts=counts,
            verification_errors=errors, attempt_consumed=True, reconstruction_authorized=False,
            elapsed_through_preparation=time.monotonic()-reservation['monotonic_start'],
            timing_scope='finish charges publication and cleanup; receipt alone is not completion')
        path = docs / (job + '.json')
    if path.exists():
        if read_json(path) != value:
            raise ValueError('conflicting immutable terminal receipt')
    else:
        write_json(path, value)
    return file_record(path)
