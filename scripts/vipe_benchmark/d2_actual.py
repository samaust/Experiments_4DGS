"""One admitted D2 map attempt and separately charged matched-clip publication."""

from pathlib import Path
import subprocess
import sys
import time

from .config import ROOT, load
from .d2_maps import CAMERAS, FRAMES, RESULT_SCHEMA, build_request, worker_command
from .d2_preflight import SCHEMA as PREFLIGHT_SCHEMA, verify_runtime
from .depth_admission import review as admit
from .depth_clips import publish_fixture_clips
from .execution import resources
from .files import file_record, object_hash, read_json, verify_record, write_json
from .ledger import Ledger
from .supervisor import supervise

RUN = 'plan031-20260913T032700Z'
JOB = 'plan069-D2-maps-001'
CONTEXT_JOB = 'plan069-depth-context-003'
DO = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'
SOURCE = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-D2-source-review-002.json'
CONTEXT_RECEIPT = ROOT / 'docs/research/vipe-alternatives' / RUN / (CONTEXT_JOB + '.json')


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def shared_run_root():
    common = Path(subprocess.check_output(['git', 'rev-parse', '--git-common-dir'],
                                         cwd=ROOT, text=True).strip())
    directory = common if common.is_absolute() else ROOT / common
    repository = directory.resolve().parent
    _require(repository.name == 'Experiments_4DGS', 'unexpected shared repository root')
    return repository


def _live(ledger, local):
    reading = resources(local, gpu=True)
    events = ledger.events()
    totals = ledger.totals(events)
    return dict(active_gpu_owner=reading['gpu_pids'][0] if reading['gpu_pids'] else None,
        active_reservations=[job for job, state in ledger.states(events).items()
                             if state['event'] == 'reserve'],
        fresh=True, sampled_unix=time.time(),
        ledger_head_sha256=events[-1]['event_sha256'] if events else '0' * 64,
        used=dict(download_bytes=reading['download_bytes'], artifact_bytes=reading['artifact_bytes'],
                  gpu_seconds=totals['gpu']['elapsed_seconds'],
                  cpu_seconds=totals['cpu']['elapsed_seconds'], setup_seconds=totals['setup']['elapsed_seconds']),
        reserved=dict(download_bytes=0, artifact_bytes=0,
                      gpu_seconds=totals['gpu']['reserved_seconds'],
                      cpu_seconds=totals['cpu']['reserved_seconds'], setup_seconds=totals['setup']['reserved_seconds']),
        device_peak_bytes=reading['device_bytes'])


def _context(ledger, local, context):
    _require(Path(context).resolve() == (local / 'jobs' / CONTEXT_JOB / 'context.json').resolve(),
             'exact accepted depth context 003 path required')
    record = file_record(context)
    receipt = read_json(verify_record(file_record(CONTEXT_RECEIPT))['path'])
    inputs = file_record(local / 'prepare/inputs.json')
    charge_record = file_record(CONTEXT_RECEIPT.with_name(CONTEXT_JOB + '-charge.json'))
    charge = read_json(charge_record['path'])
    events = [event for event in ledger.events() if event['event'] == 'cpu_preparation_charge'
              and event['evidence'] == charge_record]
    context_doc = read_json(record['path'])
    expected = {(camera, frame) for camera in range(34)
                if camera not in load()['held_out_cameras'] for frame in range(50, 200)}
    _require(receipt.get('schema') == 'plan069-depth-context-preparation/v1' and
             receipt.get('status') == 'complete' and receipt.get('context') == record and
             receipt.get('inputs') == inputs and charge.get('schema') == 'plan069-depth-context-charge/v1' and
             charge.get('status') == 'prepared' and charge.get('context') == record and
             charge.get('inputs') == inputs and len(events) == 1 and
             receipt.get('charge_event_sha256') == events[0]['event_sha256'] and
             context_doc.get('schema') == 'plan069-depth-context/v1' and
             context_doc.get('inputs') == inputs and len(context_doc.get('rows', [])) == 4500 and
             {(row['camera'], row['frame']) for row in context_doc['rows']} == expected,
             'ledger-charged accepted context 003 receipt required')
    return record


def validate_result(result, request, historical):
    """Rehash every map and require the exact bounded workload and source lineage."""
    rows = result.get('rows', [])
    keys = [(row['camera'], row['frame']) for row in rows]
    expected = {(camera, frame) for camera in CAMERAS for frame in FRAMES}
    _require(result.get('schema') == RESULT_SCHEMA and result.get('status') == 'complete' and
             result.get('candidate') == 'D2' and result.get('record_kind') == 'actual' and
             result.get('job_id') == JOB and len(keys) == 200 and set(keys) == expected and
             result.get('new_maps') == 196 and result.get('reused_anchors') == 4 and
             all(result.get(key) == request[key] for key in
                 ('context', 'historical_check', 'preflight', 'proposal_sha256')),
             'D2 completed map membership or provenance changed')
    context = read_json(verify_record(request['context'])['path'])
    sources = {(row['camera'], row['frame']): row for row in context['rows']}
    anchors = {row['identity']['camera']: row for row in historical['rows']
               if row['identity']['frame'] == 175}
    for row in rows:
        source = sources[row['camera'], row['frame']]
        _require(row.get('source_rgb') == source['source_rgb'] and row.get('inputs') == context['inputs'] and
                 row.get('grid') == 'scale-opencv-integer' and row.get('domain') == 'camera_z_metres' and
                 row.get('settings') == historical['component_sha256'] and
                 row.get('reused_anchor') is (row['frame'] == 175) and
                 row.get('metadata', {}).get('native_processed_K') is not None,
                 'D2 completed map source or native metadata changed')
        verify_record(row['prediction'])
        if row['frame'] == 175:
            _require(row['prediction'] == anchors[row['camera']]['depth'] and
                     row['metadata'] == anchors[row['camera']]['metadata'],
                     'D2 frozen anchor record changed')


def dispatch(context, qualification, *, run_id=RUN):
    _require(run_id == RUN, 'D2 attempt belongs to the accepted run')
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('D2 supervision requires host PID visibility')
    local = shared_run_root() / '.local/vipe-alternatives' / run_id
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    authorization = file_record(DO)
    approved = read_json(DO)
    review = verify_record(approved['review'])
    source_review = file_record(SOURCE)
    proposal = next(row for row in read_json(review['path'])['proposals'] if row['candidate'] == 'D2')
    grant = next(row for row in approved['candidate_approvals'] if row['candidate'] == 'D2')
    qualified_record = file_record(qualification)
    qualified = read_json(qualified_record['path'])
    _require(qualified.get('schema') == 'plan069-depth-D2-qualification/v1' and
             qualified.get('candidate') == 'D2', 'exact D2 qualification bundle required')
    preflight_record = verify_record(qualified['preflight'])
    preflight = read_json(preflight_record['path'])
    _require(preflight.get('schema') == PREFLIGHT_SCHEMA and preflight.get('candidate') == 'D2' and
             preflight.get('status') == 'cpu_preflight_passed' and
             preflight.get('proposal_sha256') == object_hash(proposal) and
             qualified.get('worker_runtime') == preflight.get('runtime') and
             qualified.get('assets_record') == preflight.get('assets') and
             sys.executable == qualified['worker_runtime']['python'],
             'D2 dispatcher must use exact preflight E5 interpreter/assets')
    verify_runtime(qualified['worker_runtime'])
    setup_record = verify_record(preflight['e5_result'])
    setup = read_json(setup_record['path'])
    state = ledger.states().get('E5-setup-recovery-004', {})
    _require(setup.get('status') == 'complete' and setup.get('environment') == 'E5' and
             setup.get('runtime') == qualified['worker_runtime'] and
             state.get('event') == 'finish' and state.get('status') == 'complete' and
             state.get('result') == setup_record,
             'completed exact E5-004 runtime setup required')
    context_record = _context(ledger, local, context)
    historical_record = ledger.states().get('D2-check', {}).get('result')
    _require(historical_record is not None and ledger.states()['D2-check'].get('status') == 'complete',
             'accepted completed historical D2 check required')
    historical = read_json(verify_record(historical_record)['path'])
    forbidden = read_json(verify_record(historical['configuration'])['path'])['forbidden_vipe_roots']
    output = local / 'jobs' / JOB
    request_path = local / 'requests' / (JOB + '.json')
    admission_path = local / 'requests' / (JOB + '-admission.json')
    _require(not any(path.exists() for path in (output, request_path, admission_path)),
             'D2 map attempt already prepared or consumed')
    # Slow runtime/context checks finish before the five-second admission sample.
    live = _live(ledger, local)
    blockers = admit(proposal, config=config, commercial=qualified['commercial'],
        assets=qualified['assets'], runtime=qualified['runtime'], live=live,
        source_review=source_review, approval=grant, cap_amendment=approved['cap_amendment'],
        cap_approval=approved['cap_approval'], ledger_head_sha256=live['ledger_head_sha256'])
    _require(not blockers, 'D2 admission failed: ' + '; '.join(blockers))
    # The locked allocator repeats the full closure check over a fresh sample.
    live = _live(ledger, local)
    admission = dict(schema='plan069-depth-admission-result/v1', status='passed', candidate='D2',
        proposal_sha256=object_hash(proposal), review=review, authorization=authorization,
        source_review=source_review, qualification=qualified_record, live=live,
        **{key: qualified[key] for key in ('commercial', 'assets', 'runtime')})
    write_json(admission_path, admission)
    admission_record = file_record(admission_path)
    request = build_request(proposal=proposal, preflight=preflight_record,
        historical_check=historical_record, context=context_record, admission=admission_record,
        ledger_path=ledger.path, forbidden_vipe_roots=forbidden)
    request.update(review=review, authorization=authorization, source_review=source_review,
                   qualification=qualified_record)
    write_json(request_path, request)
    command = worker_command(request, request_path, output)
    binding = dict(request=file_record(request_path), worker=file_record(command[1]),
                   executable=file_record(command[0]))
    ledger.authorize_depth_attempt('D2', review, authorization, source_review, admission_record,
                                   command=command, **binding)
    outcome = supervise(ledger, JOB, command, output,
        evidence=dict(admission=admission_record, review=review, authorization=authorization,
                      source_review=source_review, **binding),
        sample_resources=lambda: resources(local, gpu=True),
        validate_result=lambda out: validate_result(read_json(out / 'result.json'), request, historical),
        poll_seconds=2.)
    _require(ledger.states().get(JOB, {}).get('cleanup_confirmed') is True,
             'D2 supervised cleanup not confirmed')
    return outcome


def publish(*, run_id=RUN):
    _require(run_id == RUN, 'D2 publication belongs to the accepted run')
    local = shared_run_root() / '.local/vipe-alternatives' / run_id
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    result_record = file_record(local / 'jobs' / JOB / 'result.json')
    result = read_json(result_record['path'])
    finish = ledger.states().get(JOB, {})
    _require(finish.get('event') == 'finish' and finish.get('status') == 'complete' and
             finish.get('result') == result_record and finish.get('cleanup_confirmed') is True and
             not finish.get('surviving_pids') and not finish.get('cleanup_uncertain'),
             'completed D2 map attempt with confirmed cleanup required')
    request_record = file_record(local / 'requests' / (JOB + '.json'))
    reservations = [row for row in ledger.events() if row['event'] == 'reserve' and row['job_id'] == JOB]
    _require(len(reservations) == 1 and reservations[0].get('evidence', {}).get('request') == request_record,
             'D2 publication requires unique exact map reservation')
    request = read_json(request_record['path'])
    _require(reservations[0]['evidence'].get('admission') == request.get('admission'),
             'D2 publication admission differs from map reservation')
    historical_record = verify_record(request['historical_check'])
    historical = read_json(historical_record['path'])
    validate_result(result, request, historical)
    _context(ledger, local, request['context']['path'])
    _require(not any(row['event'] == 'reserve' for row in ledger.states().values()),
             'CPU publication cannot overlap active work')
    seconds = min(600, config['cpu_prepare_score_report_seconds_limit'] - ledger.totals()['cpu']['elapsed_seconds'])
    _require(seconds > 0 and resources(local)['artifact_bytes'] < config['new_artifact_disk_gib_limit'] * 2**30,
             'D2 CPU publication resource allowance exhausted')
    output = local / 'jobs/plan069-D2-clips-001'
    finish_path = local / 'receipts' / (JOB + '-finish.json')
    failure_path = local / 'receipts/plan069-D2-clips-001-failure.json'
    _require(not any(path.exists() for path in (output, finish_path, failure_path)),
             'immutable D2 clip publication already attempted')
    write_json(finish_path, finish)
    anchors = {row['camera']: row['prediction'] for row in result['rows'] if row['reused_anchor']}
    provenance = dict(source_result=result_record, historical_result=historical_record,
        ledger_outcome=file_record(finish_path), admission=request['admission'],
        configuration=historical['configuration'])
    start = time.monotonic()
    try:
        receipt = publish_fixture_clips(request['context'], 'D2', 'camera_z_metres',
            result['rows'], anchors, output, provenance, max_seconds=seconds, record_kind='actual')
    except BaseException as error:
        write_json(failure_path, dict(schema='plan069-depth-clips-failure/v1', candidate='D2',
            status='failed', error=f'{type(error).__name__}: {error}', elapsed_seconds=time.monotonic()-start))
        ledger.charge_cpu_preparation(time.monotonic()-start, file_record(failure_path))
        raise
    ledger.charge_cpu_preparation(time.monotonic()-start, file_record(output / 'result.json'))
    return receipt
