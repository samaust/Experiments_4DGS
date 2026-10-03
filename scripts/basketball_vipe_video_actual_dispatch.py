"""Supervise one admitted D9/D10 native video attempt on the shared GPU."""

import argparse
from pathlib import Path
import sys

from basketball_vipe_video_setup_dispatch import shared_run_root, DO
from vipe_benchmark.config import ROOT, load, training_cameras
from vipe_benchmark.depth_extension import CONFIG
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import supervise


def dispatch(candidate, admission_path, context_path,
             run_id='plan031-20260913T032700Z', *, qualitative_admission_path=None):
    if candidate not in ('D9', 'D10') or run_id != 'plan031-20260913T032700Z':
        raise ValueError('only approved D9/D10 native run')
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('native video supervision requires host PID visibility')
    local = shared_run_root() / '.local/vipe-alternatives' / run_id
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    authorization = file_record(DO)
    review = read_json(DO)['review']
    source_review = file_record(ROOT / 'docs/research/vipe-alternatives/'
        f'plan031-execution/depth-{candidate}-source-review-001.json')
    admission = file_record(admission_path)
    context = file_record(context_path)
    proposal = next(row for row in read_json(review['path'])['proposals']
                    if row['candidate'] == candidate)
    accepted = read_json(verify_record(admission)['path'])
    source = read_json(verify_record(context)['path'])
    cameras = training_cameras(config)
    expected = {(camera, frame) for camera in cameras for frame in range(50, 200)}
    if (accepted.get('schema') != 'plan069-depth-admission-result/v1' or
            accepted.get('status') != 'passed' or
            accepted.get('candidate') != candidate or
            source.get('schema') != 'plan069-depth-context/v1' or
            len(source.get('rows', [])) != 4500 or
            {(row['camera'], row['frame']) for row in source['rows']} != expected):
        raise ValueError('exact passing admission and complete video context required')
    setup_id = f'plan069-{candidate}-setup-001'
    setup_path = local / 'jobs' / setup_id / 'result.json'
    setup = file_record(setup_path)
    state = ledger.states().get(setup_id, {})
    if (state.get('event') != 'finish' or state.get('status') != 'complete' or
            state.get('result') != setup):
        raise ValueError('completed exact video setup required')
    job_id = f'plan069-{candidate}-maps-001'
    output = local / 'jobs' / job_id
    request_path = local / 'requests' / (job_id + '.json')
    if output.exists() or request_path.exists():
        raise ValueError('video inference already prepared, reserved or attempted')
    snapshot = resources(local, gpu=True)
    if snapshot['gpu_pids']:
        raise ValueError('single GPU already owned')
    request = dict(schema='plan069-video-depth-request/v1', record_kind='actual',
        id=job_id, job_id=job_id, component=candidate,
        ledger_path=str(ledger.path), admission=admission, setup=setup,
        review=review, authorization=authorization, context=context,
        configuration=file_record(ROOT / 'configs/vipe-alternatives/benchmark-v1.json'),
        extension_configuration=file_record(CONFIG), cameras=cameras,
        max_seconds=proposal['allocation']['gpu_seconds'])
    if qualitative_admission_path is not None:
        qualitative = file_record(qualitative_admission_path)
        if (candidate != 'D10' or read_json(qualitative['path']) != dict(
                schema='plan069-depth-qualitative-admission/v1', record_kind='actual',
                component='D10', inputs=source['inputs'],
                purpose='qualitative-only', status='admitted')):
            raise ValueError('D10 qualitative admission binding changed')
        request['qualitative_admission'] = qualitative
    write_json(request_path, request)
    ledger.authorize_depth_attempt(candidate, review, authorization,
                                   source_review, admission)
    worker = ROOT / 'scripts/basketball_vipe_video_actual.py'
    command = [sys.executable, str(worker), '--request', str(request_path),
               '--output', str(output)]
    def validate(out):
        result = read_json(verify_record(file_record(out / 'result.json'))['path'])
        if (result.get('schema') != 'plan069-video-depth-result/v1' or
                result.get('status') != 'complete' or
                result.get('record_kind') != 'actual' or
                result.get('component') != candidate or
                result.get('id') != job_id or
                len(result.get('rows', [])) != 256 or
                len(result.get('anchor_rows', [])) != 60 or
                len(result.get('sequences', [])) != 60):
            raise ValueError('actual video result lacks all anchors or contexts')
    return supervise(ledger, job_id, command, output,
        evidence=dict(request=file_record(request_path), admission=admission,
                      setup=setup, review=review, authorization=authorization,
                      source_review=source_review, worker=file_record(worker)),
        sample_resources=lambda: resources(local, gpu=True),
        validate_result=validate, poll_seconds=2.)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True, choices=('D9', 'D10'))
    parser.add_argument('--admission', required=True)
    parser.add_argument('--context', required=True)
    parser.add_argument('--qualitative-admission')
    parser.add_argument('--run-id', default='plan031-20260913T032700Z')
    args = parser.parse_args()
    dispatch(args.candidate, args.admission, args.context, args.run_id,
             qualitative_admission_path=args.qualitative_admission)


if __name__ == '__main__':
    main()
