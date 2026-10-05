"""Publish single-image clips only after the single native GPU result is accepted."""
from pathlib import Path
import time

from .budgets import budget_snapshot, directory_bytes
from .config import load
from .depth_single_run import CANDIDATES, RESULT
from .files import file_record, object_hash, read_json, verify_record, write_json
from .ledger import Ledger


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def publish_after_gpu(map_result_record, output):
    """Create four matched clips and charge their CPU time against the candidate cap."""
    map_result_record = verify_record(map_result_record)
    map_path = Path(map_result_record['path']).resolve()
    result = read_json(map_path)
    candidate = result.get('candidate')
    _require(candidate in (*CANDIDATES, 'D11'), 'single-image publisher candidate changed')
    domain = 'relative_log' if candidate == 'D11' else 'camera_z_metres'
    expected_schema = RESULT
    if candidate == 'D11':
        from .depth_d11_run import RESULT as d11_schema
        expected_schema = d11_schema
    from .depth_map_retry import current_allocation, is_map_job, map_job
    CLIPS_JOB = f'plan069-{candidate}-clips-001'
    local = map_path.parents[2]
    _require(map_path.name == 'result.json' and map_path.parent.parent == local / 'jobs' and
             is_map_job(map_path.parent.name) and map_path.parent.name.split('-')[1] == candidate,
             'accepted single-image GPU result path required')
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    JOB = map_job(candidate, ledger.events())
    _require(map_path == local / 'jobs' / JOB / 'result.json',
             'accepted single-image GPU result path required')
    output = Path(output)
    _require(output.resolve() == (local / 'jobs' / CLIPS_JOB).resolve() and
             not output.exists(), 'immutable single-image clip output identity changed or exists')
    state = ledger.states().get(JOB, {})
    _require(state.get('event') == 'finish' and state.get('status') == 'complete' and
             state.get('result') == map_result_record and
             state.get('cleanup_confirmed') is True and
             not state.get('cleanup_uncertain') and not state.get('surviving_pids') and
             not state.get('deadline_exceeded') and not state.get('error'),
             'successful supervised single-image GPU result required')
    outcome_path = local / 'receipts' / (JOB + '-finish.json')
    if outcome_path.exists():
        _require(read_json(outcome_path) == state,
                 'single-image copied finish event differs from current ledger')
    else:
        write_json(outcome_path, state)
    outcome_record = file_record(outcome_path)
    result = read_json(map_path)
    _require(result.get('schema') == expected_schema and result.get('status') == 'complete' and
             result.get('record_kind') == 'actual' and result.get('candidate') == candidate and
             result.get('job_id') == JOB and len(result.get('rows', [])) == 256,
             'complete actual single-image maps required')
    request_record = file_record(map_path.parent / 'request.json')
    request = read_json(request_record['path'])
    reservations = [event for event in ledger.events()
        if event['event'] == 'reserve' and event.get('job_id') == JOB]
    original_request = file_record(local / 'requests' / (JOB + '.json'))
    _require(original_request['sha256'] == request_record['sha256'] and
             original_request['bytes'] == request_record['bytes'],
             'single-image copied request differs from reserved request')
    _require(len(reservations) == 1 and
             reservations[0].get('evidence', {}).get('request') == original_request and
             request.get('admission') == reservations[0].get('evidence', {}).get('admission') and
             request.get('context') == result['context'] and
             request.get('inputs') == result['inputs'],
             'single-image map request/result admission binding changed')
    review = read_json(verify_record(request['review'])['path'])
    proposal = next(row for row in review['proposals'] if row['candidate'] == candidate)
    from .depth_map_allowance import check_slot_byte_budget
    allocation = current_allocation(candidate, ledger.events())
    slot_budget = allocation.get('slot_byte_budget') if allocation is not None else None
    _require(slot_budget is not None, 'native publication requires whole-slot byte budget')
    def check_slot():
        if slot_budget is not None:
            check_slot_byte_budget(proposal, slot_budget, local, budget_snapshot(local))
    check_slot()
    _require(proposal['workload']['unique_published_maps'] == 256 and
             proposal['workload']['clips'] == 4 and
             proposal['workload']['clip_frames'] == 50 and
             proposal['workload']['clip_fps'] == 25,
             'reviewed single-image clip workload changed')
    _require(result.get('admission') == request.get('admission') and
             result.get('setup') == request.get('setup'),
             'single-image finished request/setup binding changed')
    if candidate == 'D11':
        from .depth_d11_run import validate_result
    else:
        from .depth_single_run import validate_result
    validate_result(result, request)
    rows = result['rows']
    keys = [(row['camera'], row['frame']) for row in rows]
    if len(set(keys)) != 256:
        raise ValueError('duplicate single-image map identity')
    expected_anchors = {(camera, frame) for camera in range(34)
        if camera not in config['held_out_cameras'] for frame in (100, 175)}
    expected_clips = {(camera, frame) for camera in (1, 11, 21, 31)
                      for frame in range(150, 200)}
    _require(set(keys) == expected_anchors | expected_clips,
             'single-image map membership differs from approved workload')
    by_key = dict(zip(keys, rows))
    setting = object_hash(proposal['candidate_config'])
    clip_rows = []
    for camera, frame in sorted(expected_clips):
        row = by_key[camera, frame]
        _require(row['kind'] == ('anchor' if frame == 175 else 'clip-extra') and
                 row['domain'] == domain and
                 row['grid'] == 'scale-opencv-integer' and
                 row['context'] == result['context'] and row['inputs'] == result['inputs'],
                 'single-image clip row source or grid changed')
        verify_record(row['prediction'])
        clip_rows.append(dict(camera=camera, frame=frame,
            source_rgb=row['source_rgb'], inputs=row['inputs'],
            source_rgb_grid=row.get('source_rgb_grid', 'scale-opencv-integer' if frame == 175 else 'distorted-opencv-integer'),
            grid=row['grid'], domain=row['domain'],
            prediction=row['prediction'], settings=setting,
            reused_anchor=(frame == 175)))
    anchors = {camera: by_key[camera, 175]['prediction']
               for camera in (1, 11, 21, 31)}
    remaining = config['cpu_prepare_score_report_seconds_limit'] - \
                ledger.totals()['cpu']['elapsed_seconds']
    seconds = min(proposal['allocation']['cpu_seconds'], remaining)
    _require(seconds > 0, 'single-image CPU publication allocation exhausted')
    current = budget_snapshot(local)['artifact_bytes']
    _require(current < config['new_artifact_disk_gib_limit'] * 2**30,
             'single-image publication artifact cap exhausted')
    provenance = dict(source_result=map_result_record,
        admission=request['admission'], configuration=request_record,
        ledger_outcome=outcome_record)
    started = time.monotonic()
    try:
        from .depth_clips import publish_fixture_clips
        receipt = publish_fixture_clips(result['context'], candidate,
            domain, clip_rows, anchors, output, provenance,
            max_seconds=seconds, record_kind='actual', resource_guard=check_slot)
        elapsed = time.monotonic() - started
        _require(elapsed <= seconds and receipt.get('clips') == 4 and
                 receipt.get('new_map_identities') == 196 and
                 receipt.get('record_kind') == 'actual',
                 'single-image actual clip receipt differs from reviewed allocation')
        check_slot()
        _require(directory_bytes(map_path.parent) + directory_bytes(output)
                 <= proposal['allocation']['artifact_bytes'],
                 'single-image map/clip artifacts exceed candidate allocation')
        _require(budget_snapshot(local)['artifact_bytes'] <=
                 config['new_artifact_disk_gib_limit'] * 2**30,
                 'single-image publication exceeded cumulative artifact cap')
        write_json(output / 'publication.json', dict(
            schema='plan069-depth-single-publication/v1', status='complete',
            record_kind='actual', candidate=candidate, source_result=map_result_record,
            context=result['context'], inputs=result['inputs'], scales=result.get('scales'), domain=domain,
            engineering_eligibility=result['engineering_eligibility'],
            physical_accuracy='unverified', package=receipt['package'],
            clips_result=file_record(output / 'result.json')))
        write_json(output / 'cpu-accounting.json', dict(
            schema='plan069-depth-single-clips-accounting/v1', status='complete',
            candidate=candidate, map_result=map_result_record,
            clips_result=file_record(output / 'result.json'),
            elapsed_seconds=elapsed))
        check_slot()
        ledger.charge_cpu_preparation(elapsed, file_record(output / 'cpu-accounting.json'))
        return receipt
    except BaseException as error:
        elapsed = time.monotonic() - started
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / 'cpu-failure.json', dict(
            schema='plan069-depth-single-clips-accounting/v1', status='failed',
            candidate=candidate, map_result=map_result_record,
            error=f'{type(error).__name__}: {error}',
            elapsed_seconds=elapsed))
        ledger.charge_cpu_preparation(elapsed, file_record(output / 'cpu-failure.json'))
        raise
