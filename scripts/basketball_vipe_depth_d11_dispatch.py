"""Admit and supervise one approved D11 GPU map attempt on the shared ledger."""
import argparse
from pathlib import Path
import subprocess
import sys
import time

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.depth_admission import review as admit
from vipe_benchmark.depth_d11_run import JOB, validate_result
from vipe_benchmark.depth_native_runtime import verify_runtime
from vipe_benchmark.depth_source_integrity import verify_source
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, object_hash, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import supervise


DO = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'
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
        raise ValueError('D11 qualified virtual environment interpreter differs')


def dispatch(context, qualification, setup, *, source_review_path, run_id='plan031-20260913T032700Z'):
    if run_id != 'plan031-20260913T032700Z':
        raise ValueError('D11 depth attempt is bound to the accepted run')
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('D11 supervision requires host PID visibility')
    local = shared_run_root() / '.local/vipe-alternatives' / run_id
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    approved = file_record(DO)
    do = read_json(DO)
    review = do['review']
    source_review = file_record(source_review_path)
    proposal = next(row for row in read_json(review['path'])['proposals']
                    if row['candidate'] == 'D11')
    grant = next(row for row in do['candidate_approvals']
                 if row['candidate'] == 'D11')
    qualification_record = file_record(qualification)
    qualified = read_json(qualification_record['path'])
    if qualified.get('schema') != 'plan069-depth-D11-qualification/v1':
        raise ValueError('exact D11 qualification bundle required')
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
    if (setup_result.get('candidate') != 'D11' or
            setup_result.get('status') != 'complete' or
            setup_result.get('record_kind') != 'actual' or
            setup_result.get('job_id') != 'plan069-D11-setup-001' or
            setup_result.get('source_revision') != proposal['candidate_config']['code']['revision'] or
            setup_result.get('weight_revision') != proposal['candidate_config']['weights']['revision'] or
            setup_result.get('review') != review or
            setup_result.get('authorization') != approved or
            Path(setup).resolve() != (local / 'jobs/plan069-D11-setup-001/result.json').resolve()):
        raise ValueError('successful D11 setup receipt required')
    verify_record(setup_result['source_archive'])
    verify_source(setup_result)
    verify_runtime(setup_result, sys.executable)
    runtime_receipt = read_json(verify_record(qualified['runtime']['receipt'])['path'])
    if (qualified.get('setup') != setup_record or qualified.get('assets') != setup_result['assets'] or
            runtime_receipt.get('setup') != setup_record or
            runtime_receipt.get('python_executable') != setup_result['runtime']['python_executable']):
        raise ValueError('D11 exact prepared setup, assets and runtime qualification required')
    output = local / 'jobs' / JOB
    request_path = local / 'requests' / (JOB + '.json')
    admission_path = local / 'requests' / (JOB + '-admission.json')
    if any(path.exists() for path in (output, request_path, admission_path)):
        raise ValueError('D11 map attempt was prepared, allocated or consumed')
    live = _live(ledger, local)
    commercial, assets, runtime = (qualified[key]
                                   for key in ('commercial', 'assets', 'runtime'))
    blockers = admit(proposal, config=config, commercial=commercial,
        assets=assets, runtime=runtime, live=live,
        source_review=source_review, approval=grant,
        cap_amendment=do['cap_amendment'], cap_approval=do['cap_approval'],
        ledger_head_sha256=live['ledger_head_sha256'])
    if blockers:
        raise ValueError('D11 admission failed: ' + '; '.join(blockers))
    # Evidence hashing can outlast the live snapshot window. The locked
    # allocator rechecks all evidence against this freshly sampled state.
    live = _live(ledger, local)
    admission = dict(schema='plan069-depth-admission-result/v1', status='passed',
        candidate='D11', proposal_sha256=object_hash(proposal), review=review,
        authorization=approved, source_review=source_review,
        qualification=qualification_record, commercial=commercial,
        assets=assets, runtime=runtime, live=live)
    write_json(admission_path, admission)
    admission_record = file_record(admission_path)
    request = dict(schema='plan069-D11-maps-request/v1', record_kind='actual',
        candidate='D11', job_id=JOB, ledger_path=str(ledger.path),
        inputs=file_record(local / 'prepare/inputs.json'),
        context=context_record, setup=setup_record,
        review=review, authorization=approved, source_review=source_review,
        qualification=qualification_record, admission=admission_record)
    write_json(request_path, request)
    command = [sys.executable, str(ROOT / 'scripts/basketball_vipe_depth_d11_maps.py'),
        '--request', str(request_path), '--output', str(output)]
    ledger.authorize_depth_attempt('D11', review, approved, source_review, admission_record,
        command=command, request=file_record(request_path),
        worker=file_record(ROOT / 'scripts/basketball_vipe_depth_d11_maps.py'),
        executable=file_record(sys.executable))
    def validate(out):
        result = read_json(verify_record(file_record(out / 'result.json'))['path'])
        validate_result(result, request)
    return supervise(ledger, JOB, command, output,
        evidence=dict(request=file_record(request_path),
                      admission=admission_record, review=review,
                      authorization=approved, source_review=source_review,
                      worker=file_record(ROOT / 'scripts/basketball_vipe_depth_d11_maps.py'),
                      executable=file_record(sys.executable)),
        sample_resources=lambda: resources(local, gpu=True),
        validate_result=validate, poll_seconds=2.)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--context', required=True)
    parser.add_argument('--qualification', required=True)
    parser.add_argument('--setup', required=True)
    parser.add_argument('--source-review', required=True)
    parser.add_argument('--run-id', default='plan031-20260913T032700Z')
    args = parser.parse_args()
    dispatch(args.context, args.qualification, args.setup,
        source_review_path=args.source_review, run_id=args.run_id)


if __name__ == '__main__':
    main()
