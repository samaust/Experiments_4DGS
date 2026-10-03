"""Reserve and supervise one approved D5 or D6 setup on the shared ledger."""

import argparse
from pathlib import Path
import subprocess
import sys

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.depth_authorization import execution_authorization
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.moge_setup import source_tree_records
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


def dispatch(candidate, run_id, runtime_environment, *, source_review_path=None):
    if candidate not in ('D5', 'D6'):
        raise ValueError('MoGe setup candidate must be D5 or D6')
    if run_id != 'plan031-20260913T032700Z':
        raise ValueError('MoGe setup is bound to the existing accepted run')
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('MoGe setup supervision requires host PID visibility')
    local = shared_run_root() / '.local/vipe-alternatives' / run_id
    docs = ROOT / 'docs/research/vipe-alternatives' / run_id
    job_id = f'plan069-{candidate}-setup-001'
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    ledger = Ledger(local / 'ledger.jsonl', config)
    environment_record = verify_record(file_record(runtime_environment))
    environment = read_json(environment_record['path'])
    from vipe_benchmark.moge_environment import validate_environment_request
    requirement_record = environment['requirement_sources'][0]
    validate_environment_request(environment, Path(requirement_record['path']).parent,
                                 candidate, 'actual')
    review, authorization, proposal, _ = execution_authorization(candidate)
    source_review_path = (Path(source_review_path) if source_review_path is not None else
        ROOT / 'docs/research/vipe-alternatives/plan031-execution' /
        f'depth-{candidate}-source-review-001.json')
    source_review = file_record(source_review_path)
    source_evidence = read_json(source_review_path)
    from vipe_benchmark.depth_admission import local_source_records
    if (source_evidence.get('schema') != 'plan069-depth-source-review/v1' or
            source_evidence.get('status') != 'passed' or
            source_evidence.get('candidate') != candidate or
            source_evidence.get('source_revision') != proposal['candidate_config']['code']['revision'] or
            source_evidence.get('profile_inventory') != proposal['profile_inventory'] or
            source_evidence.get('local_sources') != local_source_records(candidate) or
            not source_evidence.get('reviewer')):
        raise ValueError('current independent MoGe source review required before setup request')
    setup_sources = [file_record(ROOT / path) for path in (
        'scripts/vipe_benchmark/moge_setup.py',
        'scripts/vipe_benchmark/moge_native.py',
        'scripts/vipe_benchmark/moge_environment.py',
        'scripts/vipe_benchmark/moge_source_build.py',
        'scripts/vipe_benchmark/depth_environment.py',
        'scripts/vipe_benchmark/depth_authorization.py',
        'scripts/vipe_benchmark/runtime_inventory.py',
        'scripts/basketball_vipe_moge_setup.py',
        'scripts/basketball_vipe_moge_setup_dispatch.py')]
    if source_evidence.get('setup_sources') != setup_sources:
        raise ValueError('current MoGe setup source review required')
    if source_evidence.get('runtime_recipe') != environment_record:
        raise ValueError('exact reviewed MoGe runtime recipe required')
    output = local / 'jobs' / job_id
    request_path = local / 'requests' / (job_id + '.json')
    if output.exists() or request_path.exists():
        raise ValueError(candidate + ' setup already prepared, reserved or attempted')
    snapshot = resources(local, gpu=True)
    if snapshot['gpu_pids']:
        raise ValueError('GPU owner active before MoGe setup')
    request = dict(schema='plan069-depth-setup-request/v1',
        record_kind='actual', candidate=candidate, job_id=job_id,
        ledger_path=str(ledger.path), review=review, authorization=authorization,
        runtime_environment=environment, runtime_environment_record=environment_record)
    write_json(request_path, request)
    ledger.authorize_depth_setup(candidate, review, authorization, source_review)
    command = [sys.executable, str(ROOT / 'scripts/basketball_vipe_moge_setup.py'),
        '--request', str(request_path), '--output', str(output)]
    def validate(out):
        result = read_json(verify_record(file_record(out / 'result.json'))['path'])
        from vipe_benchmark.budgets import directory_bytes
        if directory_bytes(out) > proposal['allocation']['artifact_bytes']:
            raise ValueError(candidate + ' setup exceeds candidate artifact allocation')
        expected = read_json(proposal['required_assets']['path'])['candidates'][candidate]['files'][0]
        checkpoint = verify_record(result['checkpoint'])
        verify_record(result['source_archive'])
        runtime = read_json(verify_record(result['runtime_environment'])['path'])
        if (runtime.get('status') != 'complete' or runtime.get('candidate') != candidate or
                runtime.get('python_executable') != result.get('python_executable')):
            raise ValueError(candidate + ' isolated runtime receipt differs')
        verify_record(runtime['python'])
        verify_record(runtime['dependency_lock'])
        verify_record(runtime['inventory'])
        if source_tree_records(result['source_dir']) != result.get('source_tree'):
            raise ValueError(candidate + ' extracted source differs from setup receipt')
        if (result.get('schema') != 'plan069-depth-setup-result/v1' or
                result.get('status') != 'complete' or
                result.get('record_kind') != 'actual' or
                result.get('candidate') != candidate or
                result.get('job_id') != job_id or
                result.get('review') != review or
                result.get('authorization') != authorization or
                result.get('source_revision') != proposal['candidate_config']['code']['revision'] or
                result.get('weight_revision') != proposal['candidate_config']['weights']['revision'] or
                checkpoint['bytes'] != expected['bytes'] or
                checkpoint['sha256'] != expected['lfs_sha256'] or
                result.get('bytes_received', 10**30) > proposal['allocation']['download_bytes'] or
                result.get('elapsed_seconds', 10**30) > proposal['allocation']['setup_seconds']):
            raise ValueError(candidate + ' setup result differs from approved assets or bounds')
    outcome = supervise(ledger, job_id, command, output,
        evidence=dict(request=file_record(request_path), review=review,
                      authorization=authorization, source_review=source_review,
                      worker=file_record(ROOT / 'scripts/basketball_vipe_moge_setup.py'),
                      runtime_recipe=environment_record),
        sample_resources=lambda: resources(local, gpu=True),
        validate_result=validate, poll_seconds=2.)
    write_json(docs / (job_id + '.json'), dict(
        schema='plan069-depth-setup-dispatch/v1', status='complete',
        outcome=outcome, result=file_record(output / 'result.json')))
    return outcome


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', choices=('D5', 'D6'), required=True)
    parser.add_argument('--run-id', default='plan031-20260913T032700Z')
    parser.add_argument('--runtime-environment', required=True)
    parser.add_argument('--source-review', help='Exact immutable independently reviewed source receipt')
    args = parser.parse_args()
    dispatch(args.candidate, args.run_id, args.runtime_environment,
             source_review_path=args.source_review)


if __name__ == '__main__':
    main()
