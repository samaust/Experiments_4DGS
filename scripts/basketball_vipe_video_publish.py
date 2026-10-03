"""Publish admitted D9/D10 matched clips after the GPU map attempt finishes."""

import argparse
from pathlib import Path
import time

from basketball_vipe_video_setup_dispatch import shared_run_root
from vipe_benchmark.config import load
from vipe_benchmark.depth_clips import publish_fixture_clips
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, object_hash, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger


def publish(candidate, run_id='plan031-20260913T032700Z'):
    if candidate not in ('D9', 'D10') or run_id != 'plan031-20260913T032700Z':
        raise ValueError('only completed D9/D10 native video publication')
    local = shared_run_root() / '.local/vipe-alternatives' / run_id
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    job_id = f'plan069-{candidate}-maps-001'
    result_record = file_record(local / 'jobs' / job_id / 'result.json')
    result = read_json(result_record['path'])
    finish = ledger.states().get(job_id, {})
    if (finish.get('event') != 'finish' or finish.get('status') != 'complete' or
            finish.get('result') != result_record or
            result.get('schema') != 'plan069-video-depth-result/v1' or
            result.get('record_kind') != 'actual' or
            result.get('component') != candidate or
            len(result.get('rows', [])) != 256 or
            len(result.get('anchor_rows', [])) != 60 or
            len(result.get('sequences', [])) != 60):
        raise ValueError('completed 60-context video map attempt required')
    request_record = file_record(local / 'requests' / (job_id + '.json'))
    request = read_json(request_record['path'])
    if (request.get('context') != result['context'] or
            request.get('admission') is None or
            request.get('component') != candidate):
        raise ValueError('video result/request/context binding changed')
    if any(row['event'] == 'reserve' for row in ledger.states().values()):
        raise ValueError('CPU package cannot overlap active run')
    seconds = min(600, config['cpu_prepare_score_report_seconds_limit'] -
                  ledger.totals()['cpu']['elapsed_seconds'])
    if seconds <= 0:
        raise ValueError('CPU publication allocation exhausted')
    if resources(local)['artifact_bytes'] >= config['new_artifact_disk_gib_limit'] * 2**30:
        raise ValueError('artifact storage allocation exhausted')
    output = local / 'jobs' / f'plan069-{candidate}-clips-001'
    finish_path = local / 'receipts' / f'{job_id}-finish.json'
    if output.exists() or finish_path.exists():
        raise ValueError('immutable video clip publication already attempted')
    write_json(finish_path, finish)
    context = read_json(verify_record(request['context'])['path'])
    settings = object_hash(read_json(request['extension_configuration']['path'])
                           ['candidates'][candidate])
    source_rows = {(row['camera'], row['frame']): row for row in context['rows']}
    rows = []
    anchors = {}
    for row in result['rows']:
        camera, frame = row['camera'], row['frame']
        if camera not in (1, 11, 21, 31) or not 150 <= frame <= 199:
            continue
        prediction = row['depth']
        verify_record(prediction)
        rows.append(dict(camera=camera, frame=frame,
            source_rgb=row['source_rgb'], inputs=context['inputs'],
            grid='scale-opencv-integer', domain=result['domain'],
            prediction=prediction, settings=settings,
            reused_anchor=frame == 175))
        if source_rows[camera, frame]['source_rgb'] != row['source_rgb']:
            raise ValueError('video map/source context changed')
        if frame == 175:
            anchors[camera] = prediction
    provenance = dict(source_result=result_record,
        ledger_outcome=file_record(finish_path),
        admission=request['admission'], configuration=request['configuration'])
    start = time.monotonic()
    try:
        receipt = publish_fixture_clips(request['context'], candidate, result['domain'],
            rows, anchors, output, provenance, max_seconds=seconds,
            record_kind='actual')
    except BaseException as error:
        failure = local / 'receipts' / f'plan069-{candidate}-clips-001-failure.json'
        write_json(failure, dict(schema='plan069-depth-clips-failure/v1',
            candidate=candidate, status='failed',
            error=f'{type(error).__name__}: {error}',
            elapsed_seconds=time.monotonic() - start))
        ledger.charge_cpu_preparation(time.monotonic() - start, file_record(failure))
        raise
    ledger.charge_cpu_preparation(time.monotonic() - start,
                                  file_record(output / 'result.json'))
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True, choices=('D9', 'D10'))
    parser.add_argument('--run-id', default='plan031-20260913T032700Z')
    args = parser.parse_args()
    publish(args.candidate, args.run_id)


if __name__ == '__main__':
    main()
