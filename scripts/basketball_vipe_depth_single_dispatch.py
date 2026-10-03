"""Admit and supervise one D5/D6/D8 single-image PointMap GPU attempt."""
import argparse
from pathlib import Path
import subprocess
import sys
import time

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.depth_authorization import execution_authorization
from vipe_benchmark.depth_admission import review as admit, local_source_records
from vipe_benchmark.depth_single_run import CANDIDATES, SCHEMA, validate_result
from vipe_benchmark.depth_source_integrity import verify_source
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, object_hash, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.moge_setup import source_tree_records
from vipe_benchmark.supervisor import supervise

RUN = 'plan031-20260913T032700Z'
CONTEXT_JOB = 'plan069-depth-context-003'
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


def dispatch(candidate, context, qualification, setup, source_review, *,
             qualitative_admission=None, run_id=RUN):
    _require(candidate in CANDIDATES and run_id == RUN,
             'single-image dispatch requires approved candidate and accepted run')
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('single-image supervision requires host PID visibility')
    local = shared_run_root() / '.local/vipe-alternatives' / run_id
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    review, authorization, proposal, grant = execution_authorization(candidate)
    approved = read_json(authorization['path'])
    source_record = file_record(source_review)
    source = read_json(source_record['path'])
    _require(source.get('schema') == 'plan069-depth-source-review/v1' and
             source.get('candidate') == candidate and source.get('status') == 'passed' and
             source.get('source_revision') == proposal['candidate_config']['code']['revision'] and
             source.get('local_sources') == local_source_records(candidate),
             'current exact candidate source review required')
    qualified_record = file_record(qualification)
    qualified = read_json(qualified_record['path'])
    _require(qualified.get('schema') == f'plan069-depth-{candidate}-qualification/v1' and
             qualified.get('candidate') == candidate, 'exact single-image qualification bundle required')
    setup_record = file_record(setup)
    _require(Path(setup).resolve() == (local / 'jobs' / f'plan069-{candidate}-setup-001/result.json').resolve(),
             'exact accepted native setup path required')
    setup_result = read_json(setup_record['path'])
    state = ledger.states().get(f'plan069-{candidate}-setup-001', {})
    _require(setup_result.get('schema') == 'plan069-depth-setup-result/v1' and
             setup_result.get('status') == 'complete' and setup_result.get('record_kind') == 'actual' and
             setup_result.get('candidate') == candidate and
             setup_result.get('job_id') == f'plan069-{candidate}-setup-001' and
             setup_result.get('review') == review and setup_result.get('authorization') == authorization and
             setup_result.get('source_revision') == proposal['candidate_config']['code']['revision'] and
             setup_result.get('weight_revision') == proposal['candidate_config']['weights']['revision'] and
             state.get('event') == 'finish' and state.get('status') == 'complete' and
             state.get('result') == setup_record and qualified.get('setup') == setup_record,
             'successful ledger-bound single-image native setup required')
    verify_record(setup_result['source_archive'])
    runtime = read_json(verify_record(qualified['runtime']['receipt'])['path'])
    interpreter = runtime.get('python_executable')
    _require(isinstance(interpreter, str) and Path(interpreter).is_absolute() and
             Path(interpreter).is_file() and interpreter == str(Path(sys.executable).absolute()) and
             runtime.get('setup') == setup_record and runtime.get('candidate') == candidate and
             runtime.get('status') == 'passed',
             'dispatcher interpreter must match qualified setup runtime')
    if candidate in ('D5', 'D6'):
        _require(source_tree_records(setup_result['source_dir']) == setup_result.get('source_tree'),
                 'native MoGe source tree differs from accepted setup')
        assets = qualified['assets']
        _require(len(assets) == 1 and assets[0]['path'] == 'model.pt' and
                 assets[0]['record'] == verify_record(setup_result['checkpoint']),
                 'qualified MoGe checkpoint differs from native setup')
    else:
        _require(setup_result.get('assets') == qualified.get('assets'),
                 'qualified PointMap assets differ from native setup')
        verify_record(setup_result['native_source'])
        verify_source(setup_result)
    context_record = _context(ledger, local, context)
    inputs = file_record(local / 'prepare/inputs.json')
    qualitative_record = None
    if qualitative_admission is not None:
        qualitative_record = file_record(qualitative_admission)
        _require(read_json(qualitative_record['path']) == dict(
            schema='plan069-depth-qualitative-admission/v1', record_kind='actual',
            component=candidate, inputs=inputs, purpose='qualitative-only', status='admitted'),
            'qualitative-only admission differs from candidate and accepted inputs')
    job = f'plan069-{candidate}-maps-001'
    output = local / 'jobs' / job
    request_path = local / 'requests' / (job + '.json')
    admission_path = local / 'requests' / (job + '-admission.json')
    _require(not any(path.exists() for path in (output, request_path, admission_path)),
             'single-image map attempt already prepared or consumed')
    live = _live(ledger, local)
    blockers = admit(proposal, config=config, commercial=qualified['commercial'],
        assets=qualified['assets'], runtime=qualified['runtime'], live=live,
        source_review=source_record, approval=grant, cap_amendment=approved['cap_amendment'],
        cap_approval=approved['cap_approval'], ledger_head_sha256=live['ledger_head_sha256'],
        completed_setup=setup_record, setup_events=ledger.events(), run_root=local)
    _require(not blockers, 'single-image admission failed: ' + '; '.join(blockers))
    # Rehashing the closure can consume most of the five-second sample window.
    # The allocator fully revalidates this refreshed snapshot under its lock.
    live = _live(ledger, local)
    admission = dict(schema='plan069-depth-admission-result/v1', status='passed', candidate=candidate,
        proposal_sha256=object_hash(proposal), review=review, authorization=authorization,
        source_review=source_record, qualification=qualified_record, live=live,completed_setup=setup_record,
        **{key: qualified[key] for key in ('commercial', 'assets', 'runtime')})
    write_json(admission_path, admission)
    admission_record = file_record(admission_path)
    request = dict(schema=SCHEMA, record_kind='actual', candidate=candidate, job_id=job,
        inputs=inputs, context=context_record, setup=setup_record, ledger_path=str(ledger.path),
        review=review, authorization=authorization, source_review=source_record,
        qualification=qualified_record, admission=admission_record)
    if qualitative_record is not None:
        request['qualitative_admission'] = qualitative_record
    write_json(request_path, request)
    worker = ROOT / 'scripts/basketball_vipe_depth_single_maps.py'
    command = [interpreter, str(worker), '--request', str(request_path), '--output', str(output)]
    binding = dict(request=file_record(request_path), worker=file_record(worker),
                   executable=file_record(interpreter))
    allocation_event = ledger.authorize_depth_attempt(candidate, review, authorization, source_record, admission_record,
                                   command=command, **binding)
    from vipe_benchmark.depth_map_allowance import check_slot_byte_budget
    def slot_resources():
        reading = resources(local,gpu=True)
        check_slot_byte_budget(proposal,allocation_event['slot_byte_budget'],local,reading)
        return reading
    outcome = supervise(ledger, job, command, output,
        evidence=dict(admission=admission_record, review=review, authorization=authorization,
                      source_review=source_record, **binding),
        sample_resources=slot_resources,
        validate_result=lambda out: validate_result(read_json(out / 'result.json'), request), poll_seconds=2.)
    finish = ledger.states().get(job, {})
    _require(finish.get('event') == 'finish' and finish.get('status') == 'complete' and
             finish.get('cleanup_confirmed') is True and not finish.get('cleanup_uncertain') and
             not finish.get('surviving_pids'), 'single-image completed supervision cleanup not confirmed')
    return outcome


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate', required=True, choices=CANDIDATES)
    parser.add_argument('--context', required=True)
    parser.add_argument('--qualification', required=True)
    parser.add_argument('--setup', required=True)
    parser.add_argument('--source-review', required=True)
    parser.add_argument('--qualitative-admission')
    parser.add_argument('--run-id', default=RUN)
    args = parser.parse_args()
    dispatch(args.candidate, args.context, args.qualification, args.setup, args.source_review,
             qualitative_admission=args.qualitative_admission, run_id=args.run_id)


if __name__ == '__main__':
    main()
