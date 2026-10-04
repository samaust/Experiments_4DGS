"""One-use shared-ledger supervision for approved D9/D10 source acquisition."""

import argparse
from pathlib import Path
import subprocess
import sys

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import supervise
from vipe_benchmark.video_environment import environment_request


DO = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'


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


def dispatch(candidate, run_id='plan031-20260913T032700Z', *, source_review_path=None,
             authorization_path=None):
    if candidate not in ('D9', 'D10') or run_id != 'plan031-20260913T032700Z':
        raise ValueError('only approved D9/D10 setup in accepted run')
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('video setup supervision requires host PID visibility')
    local = shared_run_root() / '.local/vipe-alternatives' / run_id
    docs = ROOT / 'docs/research/vipe-alternatives' / run_id
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
    verify_record(review)
    source_review_path = (Path(source_review_path) if source_review_path is not None else
        ROOT / 'docs/research/vipe-alternatives/'
        f'plan031-execution/depth-{candidate}-source-review-001.json')
    source_review = file_record(source_review_path)
    proposal = next(row for row in read_json(review['path'])['proposals']
                    if row['candidate'] == candidate)
    job_id = f'plan069-{candidate}-setup-001'
    output = local / 'jobs' / job_id
    request_path = local / 'requests' / (job_id + '.json')
    if output.exists() or request_path.exists():
        raise ValueError('video setup already prepared, reserved or attempted')
    snapshot = resources(local, gpu=True)
    if snapshot['gpu_pids']:
        raise ValueError('GPU owner active before video setup')
    request = dict(schema='plan069-depth-setup-request/v1',
        record_kind='actual', candidate=candidate, job_id=job_id,
        ledger_path=str(ledger.path), review=review, authorization=authorization,
        runtime_environment=environment_request(candidate, local,
            recipe_path=proposal.get('runtime_recipe', {}).get('path')))
    write_json(request_path, request)
    ledger.authorize_depth_setup(candidate, review, authorization, source_review)
    worker = ROOT / 'scripts/basketball_vipe_video_setup.py'
    command = [sys.executable, str(worker), '--request', str(request_path),
               '--output', str(output)]
    def validate(out):
        result = read_json(verify_record(file_record(out / 'result.json'))['path'])
        asset = read_json(proposal['required_assets']['path'])['candidates'][candidate]['files'][0]
        checkpoint = verify_record(result['checkpoint'])
        for record in result['source_files']:
            verify_record(record)
        verify_record(result['source_archive'])
        runtime = read_json(verify_record(result['runtime_environment'])['path'])
        for key in ('python', 'dependency_lock', 'inventory'):
            verify_record(runtime[key])
        for record in result['media_tools'].values():
            verify_record(record)
        if (result.get('schema') != 'plan069-video-setup-result/v1' or
                result.get('status') != 'complete' or
                result.get('record_kind') != 'actual' or
                result.get('candidate') != candidate or
                result.get('job_id') != job_id or
                result.get('review') != review or
                result.get('authorization') != authorization or
                runtime.get('status') != 'complete' or runtime.get('candidate') != candidate or
                runtime.get('python_executable') != result.get('python_executable') or
                result.get('python_executable') != str(output / 'runtime/environment/bin/python') or
                result.get('python') != runtime['python'] or
                result.get('dependency_lock') != runtime['dependency_lock'] or
                result.get('inventory') != runtime['inventory'] or
                result.get('media_tools') != request['runtime_environment']['media_tools'] or
                result.get('source_revision') != proposal['candidate_config']['code']['revision'] or
                result.get('weight_revision') != proposal['candidate_config']['weights']['revision'] or
                checkpoint['bytes'] != asset['bytes'] or
                checkpoint['sha256'] != asset['lfs_sha256'] or
                result.get('bytes_received', 10**30) > proposal['allocation']['download_bytes'] or
                result.get('elapsed_seconds', 10**30) > proposal['allocation']['setup_seconds']):
            raise ValueError('video setup differs from approved assets or bounds')
    outcome = supervise(ledger, job_id, command, output,
        evidence=dict(request=file_record(request_path), review=review,
                      authorization=authorization, source_review=source_review,
                      worker=file_record(worker)),
        sample_resources=lambda: resources(local, gpu=True),
        validate_result=validate, poll_seconds=2.)
    write_json(docs / f'{job_id}.json', dict(
        schema='plan069-video-setup-dispatch/v1', status='complete',
        outcome=outcome, result=file_record(output / 'result.json')))
    return outcome


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True, choices=('D9', 'D10'))
    parser.add_argument('--run-id', default='plan031-20260913T032700Z')
    parser.add_argument('--source-review', help='Exact immutable independently reviewed source receipt')
    parser.add_argument('--authorization', help='Explicit approved versioned video runtime authorization')
    args = parser.parse_args()
    options = dict(source_review_path=args.source_review)
    if args.authorization is not None:
        options['authorization_path'] = args.authorization
    dispatch(args.candidate, args.run_id, **options)


if __name__ == '__main__':
    main()
