"""Admit and supervise one approved D7 GPU map attempt on the shared ledger."""
import argparse
from pathlib import Path
import subprocess
import sys
import time

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.depth_admission import review as admit
from vipe_benchmark.depth_d7_run import JOB, RESULT
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, object_hash, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import supervise


DO = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'
SOURCE_REVIEW = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-D7-source-review-002.json'
CONTEXT_JOB = 'plan069-depth-context-003'
CONTEXT_RECEIPT = (ROOT / 'docs/research/vipe-alternatives' /
                   'plan031-20260913T032700Z' / (CONTEXT_JOB + '.json'))


def shared_run_root():
    common = subprocess.check_output(['git', 'rev-parse', '--git-common-dir'],
                                     cwd=ROOT, text=True).strip()
    directory = Path(common)
    if not directory.is_absolute():
        directory = ROOT / directory
    repository = directory.resolve().parent
    if repository.name != 'Experiments_4DGS':
        raise ValueError('unexpected shared Plan 031 repository root')
    return repository


def _live(ledger, local):
    reading = resources(local, gpu=True)
    events = ledger.events()
    states = ledger.states(events)
    totals = ledger.totals(events)
    return dict(active_gpu_owner=reading['gpu_pids'][0] if reading['gpu_pids'] else None,
        active_reservations=[job for job, state in states.items()
                             if state['event'] == 'reserve'],
        fresh=True, sampled_unix=time.time(),
        ledger_head_sha256=events[-1]['event_sha256'] if events else '0' * 64,
        used=dict(download_bytes=reading['download_bytes'],
                  artifact_bytes=reading['artifact_bytes'],
                  gpu_seconds=totals['gpu']['elapsed_seconds'],
                  cpu_seconds=totals['cpu']['elapsed_seconds'],
                  setup_seconds=totals['setup']['elapsed_seconds']),
        reserved=dict(download_bytes=0, artifact_bytes=0,
                      gpu_seconds=totals['gpu']['reserved_seconds'],
                      cpu_seconds=totals['cpu']['reserved_seconds'],
                      setup_seconds=totals['setup']['reserved_seconds']),
        device_peak_bytes=reading['device_bytes'])


def validate_runtime_interpreter(qualification, executable):
    """Admission binds the absolute virtual environment invocation spelling."""
    if qualification.get('runtime', {}).get('python_executable') != str(Path(executable).absolute()):
        raise ValueError('D7 qualified virtual environment interpreter differs')


def dispatch(context, qualification, setup, *, qualitative_admission=None, run_id='plan031-20260913T032700Z'):
    if run_id != 'plan031-20260913T032700Z':
        raise ValueError('D7 depth attempt is bound to the accepted run')
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('D7 supervision requires host PID visibility')
    local = shared_run_root() / '.local/vipe-alternatives' / run_id
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    approved = file_record(DO)
    do = read_json(DO)
    review = do['review']
    source_review = file_record(SOURCE_REVIEW)
    proposal = next(row for row in read_json(review['path'])['proposals']
                    if row['candidate'] == 'D7')
    grant = next(row for row in do['candidate_approvals']
                 if row['candidate'] == 'D7')
    qualification_record = file_record(qualification)
    qualified = read_json(qualification_record['path'])
    if qualified.get('schema') != 'plan069-depth-D7-qualification/v1':
        raise ValueError('exact D7 qualification bundle required')
    validate_runtime_interpreter(qualified, sys.executable)
    context_record = file_record(context)
    if Path(context).resolve() != (local / 'jobs' / CONTEXT_JOB / 'context.json').resolve():
        raise ValueError('exact accepted depth context 003 path required')
    context_receipt = read_json(verify_record(file_record(CONTEXT_RECEIPT))['path'])
    accepted_inputs = file_record(local / 'prepare/inputs.json')
    charge_record = file_record(CONTEXT_RECEIPT.with_name(CONTEXT_JOB + '-charge.json'))
    charge = read_json(charge_record['path'])
    charge_events = [event for event in ledger.events()
                     if event['event'] == 'cpu_preparation_charge' and
                     event['evidence'] == charge_record]
    if (context_receipt.get('schema') != 'plan069-depth-context-preparation/v1' or
            context_receipt.get('status') != 'complete' or
            context_receipt.get('context') != context_record or
            context_receipt.get('inputs') != accepted_inputs or
            charge.get('schema') != 'plan069-depth-context-charge/v1' or
            charge.get('status') != 'prepared' or
            charge.get('context') != context_record or
            charge.get('inputs') != accepted_inputs or
            len(charge_events) != 1 or
            context_receipt.get('charge_event_sha256') != charge_events[0]['event_sha256']):
        raise ValueError('ledger-charged accepted depth context 003 receipt required')
    setup_record = file_record(setup)
    setup_result = read_json(setup_record['path'])
    if (setup_result.get('candidate') != 'D7' or
            setup_result.get('status') != 'complete' or
            setup_result.get('record_kind') != 'actual' or
            setup_result.get('job_id') != 'plan069-D7-setup-001' or
            setup_result.get('source_revision') != proposal['candidate_config']['code']['revision'] or
            setup_result.get('weight_revision') != proposal['candidate_config']['weights']['revision'] or
            setup_result.get('review') != review or
            setup_result.get('authorization') != approved or
            Path(setup).resolve() != (local / 'jobs/plan069-D7-setup-001/result.json').resolve()):
        raise ValueError('successful D7 setup receipt required')
    verify_record(setup_result['source_archive'])
    verify_record(setup_result['checkpoint'])
    if (qualified.get('setup') != setup_record or
            not any(row.get('record') == setup_result['checkpoint'] for row in qualified.get('assets', []))):
        raise ValueError('D7 setup checkpoint differs from exact qualification asset')
    output = local / 'jobs' / JOB
    request_path = local / 'requests' / (JOB + '.json')
    admission_path = local / 'requests' / (JOB + '-admission.json')
    if any(path.exists() for path in (output, request_path, admission_path)):
        raise ValueError('D7 map attempt was prepared, allocated or consumed')
    live = _live(ledger, local)
    commercial, assets, runtime = (qualified[key]
                                   for key in ('commercial', 'assets', 'runtime'))
    blockers = admit(proposal, config=config, commercial=commercial,
        assets=assets, runtime=runtime, live=live,
        source_review=source_review, approval=grant,
        cap_amendment=do['cap_amendment'], cap_approval=do['cap_approval'],
        ledger_head_sha256=live['ledger_head_sha256'])
    if blockers:
        raise ValueError('D7 admission failed: ' + '; '.join(blockers))
    admission = dict(schema='plan069-depth-admission-result/v1', status='passed',
        candidate='D7', proposal_sha256=object_hash(proposal), review=review,
        authorization=approved, source_review=source_review,
        qualification=qualification_record, commercial=commercial,
        assets=assets, runtime=runtime, live=live)
    write_json(admission_path, admission)
    admission_record = file_record(admission_path)
    request = dict(schema='plan069-D7-maps-request/v1', record_kind='actual',
        candidate='D7', job_id=JOB, ledger_path=str(ledger.path),
        inputs=file_record(local / 'prepare/inputs.json'),
        context=context_record, setup=setup_record,
        review=review, authorization=approved, source_review=source_review,
        qualification=qualification_record, admission=admission_record)
    if qualitative_admission is not None:
        request['qualitative_admission'] = file_record(qualitative_admission)
    write_json(request_path, request)
    command = [sys.executable, str(ROOT / 'scripts/basketball_vipe_depth_d7_maps.py'),
        '--request', str(request_path), '--output', str(output)]
    ledger.authorize_depth_attempt('D7', review, approved, source_review, admission_record,
        command=command, request=file_record(request_path),
        worker=file_record(ROOT / 'scripts/basketball_vipe_depth_d7_maps.py'),
        executable=file_record(sys.executable))
    def validate(out):
        result = read_json(verify_record(file_record(out / 'result.json'))['path'])
        rows = result.get('rows', [])
        keys = [(row['camera'], row['frame']) for row in rows]
        cameras = [camera for camera in range(34)
                   if camera not in config['held_out_cameras']]
        expected_anchors = {(camera, frame) for camera in cameras
                            for frame in (100, 175)}
        expected = expected_anchors | {(camera, frame)
            for camera in (1, 11, 21, 31) for frame in range(150, 200)}
        if (result.get('schema') != RESULT or result.get('status') != 'complete' or
                result.get('record_kind') != 'actual' or result.get('candidate') != 'D7' or
                result.get('job_id') != JOB or result.get('context') != context_record or
                result.get('setup') != setup_record or len(rows) != 256 or
                len(set(keys)) != 256 or set(keys) != expected or
                sum(row['kind'] == 'anchor' for row in rows) != 60 or
                sum(row['kind'] == 'clip-extra' for row in rows) != 196):
            raise ValueError('D7 map result membership/provenance differs')
        fit = read_json(verify_record(result['scales']['fit'])['path'])
        check = read_json(verify_record(result['scales']['check'])['path'])
        if (fit.get('role') != 'fit' or check.get('role') != 'selection' or
                fit.get('component') != 'D7' or check.get('component') != 'D7' or
                fit.get('provenance', {}).get('inputs') != request['inputs'] or
                check.get('provenance') != fit.get('provenance') or
                check.get('frozen_fit') != result['scales']['fit'] or
                (fit.get('status') == 'passed' and check.get('scale') != fit.get('scale')) or
                result.get('engineering_eligibility') != ('passed' if
                    fit.get('status') == check.get('status') == 'passed' else 'blocked')):
            raise ValueError('D7 frozen scale fit/check provenance differs')
        if fit.get('status') != 'passed':
            proof = read_json(verify_record(request['qualitative_admission'])['path'])
            if proof != dict(schema='plan069-depth-qualitative-admission/v1',
                    record_kind='actual', component='D7', inputs=request['inputs'],
                    purpose='qualitative-only', status='admitted'):
                raise ValueError('D7 failed fit qualitative admission differs')
        accepted_context = read_json(verify_record(context_record)['path'])
        by_context = {(row['camera'], row['frame']): row for row in accepted_context['rows']}
        for row in rows:
            source = by_context[row['camera'], row['frame']]
            if (row.get('source_rgb') != source.get('source_rgb') or
                    row.get('source_rgb_grid') != source.get('source_rgb_grid') or
                    row.get('accepted_anchor') != source.get('accepted_anchor')):
                raise ValueError('D7 exact accepted context pixels differ')
            if (row.get('kind') != ('anchor' if (row['camera'], row['frame']) in expected_anchors
                                   else 'clip-extra') or
                    row.get('domain') != 'camera_z_metres' or
                    row.get('context') != context_record or
                    row.get('inputs') != request['inputs'] or
                    row.get('grid') != 'scale-opencv-integer'):
                raise ValueError('D7 map row provenance differs')
            verify_record(row['prediction'])
    return supervise(ledger, JOB, command, output,
        evidence=dict(request=file_record(request_path),
                      admission=admission_record, review=review,
                      authorization=approved, source_review=source_review,
                      worker=file_record(ROOT / 'scripts/basketball_vipe_depth_d7_maps.py'),
                      executable=file_record(sys.executable)),
        sample_resources=lambda: resources(local, gpu=True),
        validate_result=validate, poll_seconds=2.)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--context', required=True)
    parser.add_argument('--qualification', required=True)
    parser.add_argument('--setup', required=True)
    parser.add_argument('--qualitative-admission')
    parser.add_argument('--run-id', default='plan031-20260913T032700Z')
    args = parser.parse_args()
    dispatch(args.context, args.qualification, args.setup,
        qualitative_admission=args.qualitative_admission, run_id=args.run_id)


if __name__ == '__main__':
    main()
