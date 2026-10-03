"""Supervise one admitted D9/D10 native video attempt on the shared GPU."""

import argparse
from pathlib import Path
import sys
import time

from basketball_vipe_video_setup_dispatch import shared_run_root, DO
from vipe_benchmark.config import ROOT, load, training_cameras
from vipe_benchmark.depth_extension import CONFIG
from vipe_benchmark.depth_admission import review as admit
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, object_hash, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import supervise
from vipe_benchmark.video_depth import validate_runtime_interpreter


def _live(ledger, local):
    reading = resources(local, gpu=True)
    events = ledger.events()
    states, totals = ledger.states(events), ledger.totals(events)
    return dict(active_gpu_owner=reading['gpu_pids'][0] if reading['gpu_pids'] else None,
        active_reservations=[job for job, state in states.items() if state['event'] == 'reserve'],
        fresh=True, sampled_unix=time.time(),
        ledger_head_sha256=events[-1]['event_sha256'] if events else '0' * 64,
        used=dict(download_bytes=reading['download_bytes'], artifact_bytes=reading['artifact_bytes'],
            gpu_seconds=totals['gpu']['elapsed_seconds'], cpu_seconds=totals['cpu']['elapsed_seconds'],
            setup_seconds=totals['setup']['elapsed_seconds']),
        reserved=dict(download_bytes=0, artifact_bytes=0,
            gpu_seconds=totals['gpu']['reserved_seconds'], cpu_seconds=totals['cpu']['reserved_seconds'],
            setup_seconds=totals['setup']['reserved_seconds']),
        device_peak_bytes=reading['device_bytes'])


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
    approved = read_json(DO)
    review = approved['review']
    source_review = file_record(ROOT / 'docs/research/vipe-alternatives/'
        f'plan031-execution/depth-{candidate}-source-review-001.json')
    input_admission = file_record(admission_path)
    context = file_record(context_path)
    proposal = next(row for row in read_json(review['path'])['proposals']
                    if row['candidate'] == candidate)
    accepted = read_json(verify_record(input_admission)['path'])
    source = read_json(verify_record(context)['path'])
    cameras = training_cameras(config)
    expected = {(camera, frame) for camera in cameras for frame in range(50, 200)}
    if (accepted.get('schema') != 'plan069-depth-admission-result/v1' or
            accepted.get('status') != 'passed' or
            accepted.get('candidate') != candidate or
            accepted.get('proposal_sha256') != object_hash(proposal) or
            accepted.get('review') != review or accepted.get('authorization') != authorization or
            accepted.get('source_review') != source_review or
            source.get('schema') != 'plan069-depth-context/v1' or
            len(source.get('rows', [])) != 4500 or
            {(row['camera'], row['frame']) for row in source['rows']} != expected):
        raise ValueError('exact passing admission and complete video context required')
    qualification = accepted.get('qualification', accepted.get('runtime', {}).get('receipt'))
    if not isinstance(qualification, dict):
        raise ValueError('video admission must bind exact runtime qualification')
    verify_record(qualification)
    validate_runtime_interpreter(accepted['runtime'], sys.executable)
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
    refreshed_path = local / 'requests' / (job_id + '-admission.json')
    if any(path.exists() for path in (output, request_path, refreshed_path)):
        raise ValueError('video inference already prepared, reserved or attempted')
    grant = next(row for row in approved['candidate_approvals'] if row['candidate'] == candidate)
    previous_live = accepted['live']
    blockers = admit(proposal, config=config, commercial=accepted['commercial'],
        assets=accepted['assets'], runtime=accepted['runtime'], live=previous_live,
        source_review=source_review, approval=grant,
        cap_amendment=approved['cap_amendment'], cap_approval=approved['cap_approval'],
        ledger_head_sha256=previous_live['ledger_head_sha256'],
        now_unix=previous_live['sampled_unix'], completed_setup=setup,
        setup_events=ledger.events(), run_root=local)
    if blockers:
        raise ValueError('video qualification evidence failed: ' + '; '.join(blockers))
    request = dict(schema='plan069-video-depth-request/v1', record_kind='actual',
        id=job_id, job_id=job_id, component=candidate, candidate=candidate,
        ledger_path=str(ledger.path), setup=setup,
        review=review, authorization=authorization, source_review=source_review,
        qualification=qualification, context=context,
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
    worker = ROOT / 'scripts/basketball_vipe_video_actual.py'
    command = [sys.executable, str(worker), '--request', str(request_path),
               '--output', str(output)]
    worker_record = file_record(worker)
    executable_record = file_record(sys.executable)
    # Complete evidence hashing before sampling the five-second live window.
    live = _live(ledger, local)
    if live['active_gpu_owner'] is not None or live['active_reservations']:
        raise ValueError('single GPU or reservation already owned')
    refreshed = dict(accepted, live=live, input_admission=input_admission, completed_setup=setup)
    write_json(refreshed_path, refreshed)
    admission = file_record(refreshed_path)
    request['admission'] = admission
    write_json(request_path, request)
    request_record = file_record(request_path)
    allocation_event = ledger.authorize_depth_attempt(candidate, review, authorization,
        source_review, admission, command=command, request=request_record,
        worker=worker_record, executable=executable_record)
    from vipe_benchmark.depth_map_allowance import check_slot_byte_budget
    def slot_resources():
        reading = resources(local, gpu=True)
        check_slot_byte_budget(proposal, allocation_event['slot_byte_budget'], local, reading)
        return reading
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
        evidence=dict(request=request_record, admission=admission,
                      setup=setup, review=review, authorization=authorization,
                      source_review=source_review, qualification=qualification,
                      worker=worker_record, executable=executable_record),
        sample_resources=slot_resources,
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
