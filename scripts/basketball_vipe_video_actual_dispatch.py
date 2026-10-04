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


def _selected_setup(candidate, local, accepted, *, setup_path=None):
    """Keep the original default; explicit recovery selects one owned D9 job."""
    original = local / 'jobs' / f'plan069-{candidate}-setup-001' / 'result.json'
    selected = original if setup_path is None else Path(setup_path).resolve()
    allowed = [original]
    if candidate == 'D9':
        from vipe_benchmark.depth_recovery_lineage import JOBS
        allowed.extend(local / 'jobs' / job / 'result.json' for job in JOBS)
    if selected not in allowed:
        raise ValueError('exact owned video setup path required')
    record = file_record(selected)
    if setup_path is not None and accepted.get('completed_setup') != record:
        raise ValueError('explicit video setup differs from passed admission')
    return selected.parent.name, record


def _qualified_sources(candidate, proposal, accepted, source_review, setup_record,
                       review, authorization, *, events=None, run_root=None):
    """Rehash current native lineage before writing or reserving an attempt."""
    from vipe_benchmark.depth_admission import local_source_records
    from vipe_benchmark.video_native import native_source_records
    source = read_json(verify_record(source_review)['path'])
    setup = read_json(verify_record(setup_record)['path'])
    recovery = setup.get('schema') in ('plan069-video-setup-recovery-result/v1', 'plan069-video-setup-recovery-result/v2')
    if recovery:
        if candidate != 'D9' or events is None or run_root is None:
            raise ValueError('protected accepted recovery lineage required before video dispatch')
        from vipe_benchmark.depth_recovery_lineage import accepted_setup_lineage
        lineage = accepted_setup_lineage(setup_record, events, run_root)
        if lineage['map_proposal'] != proposal or accepted.get('completed_setup') != setup_record:
            raise ValueError('recovery setup differs from qualified map proposal or admission')
    qualification = accepted.get('qualification')
    if not isinstance(qualification, dict):
        raise ValueError('video admission requires explicit full qualification bundle')
    bundle = read_json(verify_record(qualification)['path'])
    runtime_record = accepted.get('runtime', {}).get('receipt')
    if not isinstance(runtime_record, dict):
        raise ValueError('video admission requires exact runtime receipt')
    runtime = read_json(verify_record(runtime_record)['path'])
    current = local_source_records(candidate)
    if (source.get('schema') != 'plan069-depth-source-review/v1' or
            source.get('status') != 'passed' or source.get('candidate') != candidate or
            not source.get('reviewer') or
            source.get('source_revision') != proposal['candidate_config']['code']['revision'] or
            source.get('profile_inventory') != proposal['profile_inventory'] or
            source.get('local_sources') != current or
            (not recovery and setup.get('schema') != 'plan069-video-setup-result/v1') or
            setup.get('record_kind') != 'actual' or setup.get('status') != 'complete' or
            setup.get('candidate') != candidate or setup.get('review') != review or
            setup.get('authorization') != authorization or
            setup.get('source_revision') != source['source_revision'] or
            setup.get('weight_revision') != proposal['candidate_config']['weights']['revision'] or
            runtime.get('schema') != 'plan069-depth-runtime-qualification/v1' or
            runtime.get('record_kind') != 'actual' or runtime.get('candidate') != candidate or
            runtime.get('status') != 'passed' or runtime.get('setup') != setup_record or
            runtime.get('source_revision') != source['source_revision'] or
            runtime.get('local_sources') != current or runtime.get('profile') != proposal['profile'] or
            runtime.get('source_review') != source_review or
            bundle.get('schema') != f'plan069-depth-{candidate}-qualification/v1' or
            bundle.get('candidate') != candidate or bundle.get('status') != 'passed' or
            bundle.get('record_kind') != 'actual' or bundle.get('setup') != setup_record or
            bundle.get('source_review') != source_review or
            bundle.get('runtime', {}).get('receipt') != runtime_record or
            bundle.get('commercial', {}).get('assessment') != accepted.get('commercial', {}).get('assessment')):
        raise ValueError('current independent video source/runtime qualification required')
    archive, files = setup.get('source_archive'), setup.get('source_files')
    if (not archive or not files or any(document.get('source_archive') != archive or
            document.get('source_files') != files for document in (source, runtime, bundle))):
        raise ValueError('exact video archive and source-file qualification required')
    verify_record(archive)
    if native_source_records(setup['source_dir']) != files:
        raise ValueError('native video source changed since qualification')
    return qualification


def dispatch(candidate, admission_path, context_path,
             run_id='plan031-20260913T032700Z', *, qualitative_admission_path=None, source_review_path=None,
             authorization_path=None, setup_path=None):
    if candidate not in ('D9', 'D10') or run_id != 'plan031-20260913T032700Z':
        raise ValueError('only approved D9/D10 native run')
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('native video supervision requires host PID visibility')
    local = shared_run_root() / '.local/vipe-alternatives' / run_id
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    if authorization_path is None:
        authorization = file_record(DO)
        review = read_json(DO)['review']
    else:
        from vipe_benchmark.depth_authorization import execution_authorization
        review, authorization, _, _ = execution_authorization(
            candidate, authorization_path=authorization_path)
    approved = read_json(authorization['path'])
    source_review = file_record(Path(source_review_path) if source_review_path is not None else
        ROOT / 'docs/research/vipe-alternatives/' /
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
    setup_id, setup = _selected_setup(candidate, local, accepted, setup_path=setup_path)
    state = ledger.states().get(setup_id, {})
    if (state.get('event') != 'finish' or state.get('status') != 'complete' or
            state.get('result') != setup):
        raise ValueError('completed exact video setup required')
    qualification = _qualified_sources(candidate, proposal, accepted, source_review, setup, review,
        authorization, events=ledger.events(), run_root=local)
    validate_runtime_interpreter(accepted['runtime'], sys.executable)
    job_id = f'plan069-{candidate}-maps-001'
    output = local / 'jobs' / job_id
    request_path = local / 'requests' / (job_id + '.json')
    refreshed_path = local / 'requests' / (job_id + '-admission.json')
    if any(path.exists() for path in (output, request_path, refreshed_path)):
        raise ValueError('video inference already prepared, reserved or attempted')
    grant = next(row for row in approved['candidate_approvals'] if row['candidate'] == candidate)
    from vipe_benchmark.depth_recovery_lineage import recovery_cap_authorization
    caps = recovery_cap_authorization(proposal, authorization, setup, ledger.events(), local)
    if caps is None:
        caps = approved['cap_amendment'], approved['cap_approval']
    previous_live = accepted['live']
    blockers = admit(proposal, config=config, commercial=accepted['commercial'],
        assets=accepted['assets'], runtime=accepted['runtime'], live=previous_live,
        source_review=source_review, approval=grant,
        cap_amendment=caps[0], cap_approval=caps[1],
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
    parser.add_argument('--source-review', help='Exact immutable current post-setup source review')
    parser.add_argument('--authorization', help='Explicit approved versioned video runtime authorization')
    parser.add_argument('--setup', help='Exact owned setup result bound by the passed admission')
    parser.add_argument('--run-id', default='plan031-20260913T032700Z')
    args = parser.parse_args()
    options = dict(qualitative_admission_path=args.qualitative_admission, source_review_path=args.source_review)
    if args.authorization is not None:
        options['authorization_path'] = args.authorization
    if args.setup is not None:
        options['setup_path'] = args.setup
    dispatch(args.candidate, args.admission, args.context, args.run_id, **options)


if __name__ == '__main__':
    main()
