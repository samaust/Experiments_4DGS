"""Publish D7 clips only after the single native GPU result is accepted."""
from pathlib import Path
import time

from .budgets import budget_snapshot, directory_bytes
from .config import load
from .depth_clips import publish_fixture_clips
from .depth_d7_run import JOB, RESULT
from .files import file_record, object_hash, read_json, verify_record, write_json
from .ledger import Ledger


CLIPS_JOB = 'plan069-D7-clips-001'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def publish_d7_after_gpu(map_result_record, output):
    """Create four matched clips and charge their CPU time against D7's cap."""
    map_result_record = verify_record(map_result_record)
    map_path = Path(map_result_record['path']).resolve()
    local = map_path.parents[2]
    _require(map_path == local / 'jobs' / JOB / 'result.json',
             'accepted D7 GPU result path required')
    output = Path(output)
    _require(output.resolve() == (local / 'jobs' / CLIPS_JOB).resolve() and
             not output.exists(), 'immutable D7 clip output identity changed or exists')
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    state = ledger.states().get(JOB, {})
    _require(state.get('event') == 'finish' and state.get('status') == 'complete' and
             state.get('result') == map_result_record and
             state.get('cleanup_confirmed') is True and
             not state.get('cleanup_uncertain') and not state.get('surviving_pids') and
             not state.get('deadline_exceeded') and not state.get('error'),
             'successful supervised D7 GPU result required')
    outcome_path = local / 'receipts' / (JOB + '-finish.json')
    if outcome_path.exists():
        _require(read_json(outcome_path) == state,
                 'D7 copied finish event differs from current ledger')
    else:
        write_json(outcome_path, state)
    outcome_record = file_record(outcome_path)
    result = read_json(map_path)
    _require(result.get('schema') == RESULT and result.get('status') == 'complete' and
             result.get('record_kind') == 'actual' and result.get('candidate') == 'D7' and
             result.get('job_id') == JOB and len(result.get('rows', [])) == 256,
             'complete actual D7 maps required')
    request_record = file_record(map_path.parent / 'request.json')
    request = read_json(request_record['path'])
    reservations = [event for event in ledger.events()
        if event['event'] == 'reserve' and event.get('job_id') == JOB]
    original_request = file_record(local / 'requests' / (JOB + '.json'))
    _require(original_request['sha256'] == request_record['sha256'] and
             original_request['bytes'] == request_record['bytes'],
             'D7 copied request differs from reserved request')
    _require(len(reservations) == 1 and
             reservations[0].get('evidence', {}).get('request') == original_request and
             request.get('admission') == reservations[0].get('evidence', {}).get('admission') and
             request.get('context') == result['context'] and
             request.get('inputs') == result['inputs'],
             'D7 map request/result admission binding changed')
    review = read_json(verify_record(request['review'])['path'])
    proposal = next(row for row in review['proposals'] if row['candidate'] == 'D7')
    _require(proposal['workload']['unique_published_maps'] == 256 and
             proposal['workload']['clips'] == 4 and
             proposal['workload']['clip_frames'] == 50 and
             proposal['workload']['clip_fps'] == 25,
             'reviewed D7 clip workload changed')
    fit = read_json(verify_record(result['scales']['fit'])['path'])
    check = read_json(verify_record(result['scales']['check'])['path'])
    _require(fit.get('role') == 'fit' and check.get('role') == 'selection' and
             check.get('frozen_fit') == result['scales']['fit'],
             'D7 scale fit/check binding changed')
    if fit.get('status') != 'passed':
        proof = read_json(verify_record(request['qualitative_admission'])['path'])
        _require(proof == dict(schema='plan069-depth-qualitative-admission/v1',
            record_kind='actual', component='D7', inputs=request['inputs'],
            purpose='qualitative-only', status='admitted') and
            result.get('engineering_eligibility') == 'blocked',
            'failed D7 fit requires separate qualitative admission')
    rows = result['rows']
    keys = [(row['camera'], row['frame']) for row in rows]
    if len(set(keys)) != 256:
        raise ValueError('duplicate D7 map identity')
    expected_anchors = {(camera, frame) for camera in range(34)
        if camera not in config['held_out_cameras'] for frame in (100, 175)}
    expected_clips = {(camera, frame) for camera in (1, 11, 21, 31)
                      for frame in range(150, 200)}
    _require(set(keys) == expected_anchors | expected_clips,
             'D7 map membership differs from approved workload')
    by_key = dict(zip(keys, rows))
    setting = object_hash(proposal['candidate_config'])
    clip_rows = []
    for camera, frame in sorted(expected_clips):
        row = by_key[camera, frame]
        _require(row['kind'] == ('anchor' if frame == 175 else 'clip-extra') and
                 row['domain'] == 'camera_z_metres' and
                 row['grid'] == 'scale-opencv-integer' and
                 row['context'] == result['context'] and row['inputs'] == result['inputs'],
                 'D7 clip row source or grid changed')
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
    _require(seconds > 0, 'D7 CPU publication allocation exhausted')
    current = budget_snapshot(local)['artifact_bytes']
    _require(current < config['new_artifact_disk_gib_limit'] * 2**30,
             'D7 publication artifact cap exhausted')
    provenance = dict(source_result=map_result_record,
        admission=request['admission'], configuration=request_record,
        ledger_outcome=outcome_record)
    started = time.monotonic()
    try:
        receipt = publish_fixture_clips(result['context'], 'D7',
            'camera_z_metres', clip_rows, anchors, output, provenance,
            max_seconds=seconds, record_kind='actual')
        elapsed = time.monotonic() - started
        _require(elapsed <= seconds and receipt.get('clips') == 4 and
                 receipt.get('new_map_identities') == 196 and
                 receipt.get('record_kind') == 'actual',
                 'D7 actual clip receipt differs from reviewed allocation')
        _require(directory_bytes(map_path.parent) + directory_bytes(output)
                 <= proposal['allocation']['artifact_bytes'],
                 'D7 map/clip artifacts exceed candidate allocation')
        _require(budget_snapshot(local)['artifact_bytes'] <=
                 config['new_artifact_disk_gib_limit'] * 2**30,
                 'D7 publication exceeded cumulative artifact cap')
        write_json(output / 'cpu-accounting.json', dict(
            schema='plan069-D7-clips-accounting/v1', status='complete',
            candidate='D7', map_result=map_result_record,
            clips_result=file_record(output / 'result.json'),
            elapsed_seconds=elapsed))
        ledger.charge_cpu_preparation(elapsed, file_record(output / 'cpu-accounting.json'))
        return receipt
    except BaseException as error:
        elapsed = time.monotonic() - started
        output.mkdir(parents=True, exist_ok=True)
        write_json(output / 'cpu-failure.json', dict(
            schema='plan069-D7-clips-accounting/v1', status='failed',
            candidate='D7', map_result=map_result_record,
            error=f'{type(error).__name__}: {error}',
            elapsed_seconds=elapsed))
        ledger.charge_cpu_preparation(elapsed, file_record(output / 'cpu-failure.json'))
        raise
