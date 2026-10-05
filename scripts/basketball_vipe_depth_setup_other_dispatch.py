"""Supervise one approved D8 or D11 setup using the shared Plan 031 ledger."""

import argparse
from pathlib import Path
import subprocess
import sys

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.depth_authorization import execution_authorization
from vipe_benchmark.depth_admission import local_source_records
from vipe_benchmark.execution import resources
from vipe_benchmark.depth_native_runtime import recipe, verify_runtime
from vipe_benchmark.depth_source_integrity import verify_source
from vipe_benchmark.files import file_record, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import supervise




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


def dispatch(candidate, run_id, *, source_review_path=None):
    if candidate not in ('D8', 'D11') or run_id != 'plan031-20260913T032700Z':
        raise ValueError('setup candidate/run differs from reviewed Plan 069 scope')
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('depth setup supervision requires host PID visibility')
    local = shared_run_root() / '.local/vipe-alternatives' / run_id
    docs = ROOT / 'docs/research/vipe-alternatives' / run_id
    job_id = f'plan069-{candidate}-setup-001'
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    review, authorization, proposal, _ = execution_authorization(candidate)
    source_path = (Path(source_review_path) if source_review_path is not None else
        ROOT / 'docs/research/vipe-alternatives' / run_id /
        f'depth-{candidate}-source-review-001.json')
    source_review = file_record(source_path)
    source = read_json(verify_record(source_review)['path'])
    if (source.get('schema') != 'plan069-depth-source-review/v1' or
            source.get('status') != 'passed' or source.get('candidate') != candidate or
            source.get('source_revision') != proposal['candidate_config']['code']['revision'] or
            source.get('profile_inventory') != proposal['profile_inventory'] or
            source.get('local_sources') != local_source_records(candidate) or
            not source.get('reviewer')):
        raise ValueError('current independent depth source review required')
    output = local / 'jobs' / job_id
    request_path = local / 'requests' / (job_id + '.json')
    if output.exists() or request_path.exists():
        raise ValueError('setup already prepared, reserved or attempted')
    snapshot = resources(local, gpu=True)
    if snapshot['gpu_pids']:
        raise ValueError('GPU owner active before depth setup')
    request = dict(schema='plan069-depth-setup-request/v1', record_kind='actual',
        candidate=candidate, job_id=job_id, ledger_path=str(ledger.path),
        review=review, authorization=authorization, environment=recipe(candidate, local))
    write_json(request_path, request)
    ledger.authorize_depth_setup(candidate, review, authorization, source_review)
    worker = ROOT / 'scripts/basketball_vipe_depth_setup_other.py'
    command = [sys.executable, str(worker), '--request', str(request_path),
               '--output', str(output)]

    def validate(out):
        result = read_json(verify_record(file_record(out / 'result.json'))['path'])
        inventory = read_json(proposal['required_assets']['path'])['candidates'][candidate]['files']
        expected = {(row['repository'], row['path']): row for row in inventory}
        actual = {(row['repository'], row['path']): row for row in result['assets']}
        if set(actual) != set(expected) or len(result['assets']) != len(expected):
            raise ValueError('depth setup asset inventory differs from approved set')
        for key, row in actual.items():
            record = verify_record(row['record'])
            if record['bytes'] != expected[key]['bytes'] or (expected[key]['lfs_sha256'] and
                    record['sha256'] != expected[key]['lfs_sha256']):
                raise ValueError('depth setup asset receipt differs')
        verify_record(result['source_archive'])
        verify_record(result['native_source'])
        verify_source(result)
        verify_runtime(result, result['runtime']['python_executable'])
        if (result.get('schema') != 'plan069-depth-setup-result/v1' or
                result.get('status') != 'complete' or result.get('record_kind') != 'actual' or
                result.get('candidate') != candidate or result.get('job_id') != job_id or
                result.get('review') != review or result.get('authorization') != authorization or
                result.get('source_revision') != proposal['candidate_config']['code']['revision'] or
                result.get('weight_revision') != proposal['candidate_config']['weights']['revision'] or
                result.get('bytes_received', 10**30) > proposal['allocation']['download_bytes'] or
                result.get('elapsed_seconds', 10**30) > proposal['allocation']['setup_seconds']):
            raise ValueError('setup result differs from approved source, bounds or origin')

    outcome = supervise(ledger, job_id, command, output,
        evidence=dict(request=file_record(request_path), review=review,
                      authorization=authorization, source_review=source_review,
                      worker=file_record(worker)),
        sample_resources=lambda: resources(local, gpu=True),
        validate_result=validate, poll_seconds=2.)
    write_json(docs / f'plan069-{candidate}-setup-001.json', dict(
        schema='plan069-depth-setup-dispatch/v1', status='complete',
        outcome=outcome, result=file_record(output / 'result.json')))
    return outcome


def _recovery_evidence(grant):
    """The exact grant fields the ledger requires as reservation evidence."""
    return {key: grant[key] for key in ('request', 'review', 'authorization', 'source_review',
                                        'worker', 'executable')}


def dispatch_recovery(run_root, inputs):
    """Write, authorize and supervise the reviewed D8 setup recovery in ``run_root``.

    ``inputs`` names the exact recovery REVIEW, its DO and the current source review.
    The ledger validates the full recovery authority before the single reservation.
    A request left by a refused authorization is reused only if byte-identical and
    nothing was granted, reserved or written for the job.
    """
    from vipe_benchmark.depth_native_setup_recovery import (CANDIDATE, JOB, validate_recovery_request,
                                                            validate_recovery_result)
    from vipe_benchmark.setup_recovery_core import RECOVERY_CANDIDATES, RECOVERY_EVENT
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('depth setup recovery supervision requires host PID visibility')
    run_root = Path(run_root).resolve()
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    ledger = Ledger(run_root / 'ledger.jsonl', config)
    review = verify_record(inputs['review'])
    proposal = read_json(review['path'])['setup_recovery_proposal']
    output = run_root / 'jobs' / JOB
    request_path = run_root / 'requests' / (JOB + '.json')
    request = dict(schema='plan069-depth-setup-recovery-request/v1', record_kind='actual',
        candidate=CANDIDATE, job_id=JOB, ledger_path=str(run_root / 'ledger.jsonl'), review=review,
        authorization=verify_record(inputs['authorization']), source_review=verify_record(inputs['source_review']),
        original_setup=proposal['original_setup'], runtime_environment=recipe(CANDIDATE, run_root),
        acquisitions=proposal['acquisitions'])
    if output.exists() or output.is_symlink() or any(
            row.get('job_id') == JOB and row.get('event') in (RECOVERY_EVENT, 'reserve', 'finish', 'account')
            for row in ledger.events()):
        raise ValueError('setup recovery already prepared, reserved or attempted')
    if request_path.exists() or request_path.is_symlink():
        if request_path.is_symlink() or read_json(request_path) != request:
            raise ValueError('setup recovery already prepared, reserved or attempted')
    else:
        write_json(request_path, request)
    request_record = file_record(request_path)
    normalized = validate_recovery_request(request_record, ledger.events(), run_root)
    worker = ROOT / 'scripts' / RECOVERY_CANDIDATES[CANDIDATE]['worker']
    command = [sys.executable, str(worker), '--request', str(request_path), '--output', str(output)]
    grant = ledger.authorize_depth_setup_recovery(request_record, command=command, worker=file_record(worker),
                                                  executable=file_record(sys.executable))

    def sample():
        reading = resources(run_root, gpu=True)
        for key in ('download_bytes', 'artifact_bytes'):
            if reading[key] > grant['byte_limits'][key]:
                raise ValueError(key + ' setup recovery exceeds its approved byte limit')
        return reading

    def validate(out):
        validate_recovery_result(read_json(verify_record(file_record(out / 'result.json'))['path']), normalized)
    return supervise(ledger, JOB, command, output, evidence=_recovery_evidence(grant),
        sample_resources=sample, validate_result=validate, poll_seconds=2., seconds_limit=grant['seconds'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', choices=('D8', 'D11'), required=True)
    parser.add_argument('--run-id', default='plan031-20260913T032700Z')
    parser.add_argument('--source-review', help='Exact immutable independently reviewed source receipt')
    parser.add_argument('--recovery-review', help='Reviewed D8 setup-recovery REVIEW (recovery dispatch)')
    parser.add_argument('--recovery-authorization', help='Explicit D8 setup-recovery DO (recovery dispatch)')
    args = parser.parse_args()
    if args.recovery_review or args.recovery_authorization:
        if not (args.candidate == 'D8' and args.recovery_review and args.recovery_authorization and
                args.source_review and args.run_id == 'plan031-20260913T032700Z'):
            raise ValueError('D8 recovery needs its REVIEW, DO and current source review in the Plan 031 run')
        run_root = shared_run_root() / '.local/vipe-alternatives' / args.run_id
        dispatch_recovery(run_root, {key: file_record(path) for key, path in (
            ('review', args.recovery_review), ('authorization', args.recovery_authorization),
            ('source_review', args.source_review))})
        return
    dispatch(args.candidate, args.run_id, source_review_path=args.source_review)


if __name__ == '__main__':
    main()
