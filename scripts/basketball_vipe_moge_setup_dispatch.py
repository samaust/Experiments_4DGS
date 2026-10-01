"""Reserve and supervise one approved D5 or D6 setup on the shared ledger."""

import argparse
from pathlib import Path
import subprocess
import sys

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.moge_setup import source_tree_records
from vipe_benchmark.supervisor import supervise


REVIEW = ROOT / 'docs/specs/plan031-execution/depth-execution-review-001.json'
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


def dispatch(candidate, run_id):
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
    review, authorization = file_record(REVIEW), file_record(DO)
    source_review_path = (ROOT / 'docs/research/vipe-alternatives/plan031-execution' /
                          f'depth-{candidate}-source-review-001.json')
    source_review = file_record(source_review_path)
    source_evidence = read_json(source_review_path)
    setup_sources = [file_record(ROOT / path) for path in (
        'scripts/vipe_benchmark/moge_setup.py',
        'scripts/vipe_benchmark/moge_native.py',
        'scripts/basketball_vipe_moge_setup.py',
        'scripts/basketball_vipe_moge_setup_dispatch.py')]
    if source_evidence.get('setup_sources') != setup_sources:
        raise ValueError('current MoGe setup source review required')
    proposal = next(row for row in read_json(REVIEW)['proposals']
                    if row['candidate'] == candidate)
    output = local / 'jobs' / job_id
    request_path = local / 'requests' / (job_id + '.json')
    if output.exists() or request_path.exists():
        raise ValueError(candidate + ' setup already prepared, reserved or attempted')
    snapshot = resources(local, gpu=True)
    if snapshot['gpu_pids']:
        raise ValueError('GPU owner active before MoGe setup')
    request = dict(schema='plan069-depth-setup-request/v1',
        record_kind='actual', candidate=candidate, job_id=job_id,
        ledger_path=str(ledger.path), review=review, authorization=authorization)
    write_json(request_path, request)
    ledger.authorize_depth_setup(candidate, review, authorization, source_review)
    command = [sys.executable, str(ROOT / 'scripts/basketball_vipe_moge_setup.py'),
        '--request', str(request_path), '--output', str(output)]
    def validate(out):
        result = read_json(verify_record(file_record(out / 'result.json'))['path'])
        expected = read_json(proposal['required_assets']['path'])['candidates'][candidate]['files'][0]
        checkpoint = verify_record(result['checkpoint'])
        verify_record(result['source_archive'])
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
                      worker=file_record(ROOT / 'scripts/basketball_vipe_moge_setup.py')),
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
    args = parser.parse_args()
    dispatch(args.candidate, args.run_id)


if __name__ == '__main__':
    main()
