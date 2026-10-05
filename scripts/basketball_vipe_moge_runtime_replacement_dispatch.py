"""Write, authorize and supervise the reviewed D6 runtime replacement (one offline setup job)."""
import argparse
from pathlib import Path
import subprocess
import sys

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, read_json, verify_record, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import supervise

RUN = 'plan031-20260913T032700Z'


def shared_run_root():
    common = Path(subprocess.check_output(['git', 'rev-parse', '--git-common-dir'], cwd=ROOT, text=True).strip())
    directory = common if common.is_absolute() else ROOT / common
    repository = directory.resolve().parent
    if repository.name != 'Experiments_4DGS':
        raise ValueError('unexpected shared repository root')
    return repository / '.local/vipe-alternatives' / RUN


def _evidence(grant):
    """The exact grant fields the ledger requires as reservation evidence."""
    return {key: grant[key] for key in ('request', 'review', 'authorization', 'source_review', 'worker', 'executable')}


def dispatch(run_root, inputs):
    """``inputs`` names the exact REVIEW, its DO and the current source review."""
    from vipe_benchmark.depth_moge_runtime_replacement import (CACHE_METADATA_ALLOWANCE, CANDIDATE, JOBS,
                                                              validate_recovery_request, validate_recovery_result)
    from vipe_benchmark.budgets import _snapshot
    from vipe_benchmark.setup_recovery_core import RECOVERY_CANDIDATES, RECOVERY_EVENT
    if Path('/proc/1/comm').read_text().strip() != 'systemd':
        raise PermissionError('runtime replacement supervision requires host PID visibility')
    run_root = Path(run_root).resolve()
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    ledger = Ledger(run_root / 'ledger.jsonl', config)
    review = verify_record(inputs['review'])
    proposal = read_json(review['path'])['setup_recovery_proposal']
    JOB = proposal['job_id']
    if JOB not in JOBS:
        raise ValueError('unknown runtime replacement attempt')
    output = run_root / 'jobs' / JOB
    request_path = run_root / 'requests' / (JOB + '.json')
    request = dict(schema='plan069-depth-setup-recovery-request/v1', record_kind='actual', candidate=CANDIDATE,
        job_id=JOB, ledger_path=str(run_root / 'ledger.jsonl'), review=review,
        authorization=verify_record(inputs['authorization']), source_review=verify_record(inputs['source_review']),
        original_setup=proposal['original_setup'], runtime_environment=proposal['runtime_recipe'])
    if output.exists() or output.is_symlink() or any(
            row.get('job_id') == JOB and row.get('event') in (RECOVERY_EVENT, 'reserve', 'finish', 'account')
            for row in ledger.events()):
        raise ValueError('runtime replacement already prepared, reserved or attempted')
    if request_path.exists() or request_path.is_symlink():
        if request_path.is_symlink() or read_json(request_path) != request:
            raise ValueError('runtime replacement already prepared, reserved or attempted')
    else:
        write_json(request_path, request)
    request_record = file_record(request_path)
    normalized = validate_recovery_request(request_record, ledger.events(), run_root)
    worker = ROOT / 'scripts' / RECOVERY_CANDIDATES[CANDIDATE]['worker']
    command = [sys.executable, str(worker), '--request', str(request_path), '--output', str(output)]
    grant = ledger.authorize_depth_setup_recovery(request_record, command=command, worker=file_record(worker),
                                                  executable=file_record(sys.executable))
    before = _snapshot(run_root)

    def sample():
        reading = resources(run_root, gpu=True)
        now = _snapshot(run_root)
        if (now['direct_download_bytes'] != before['direct_download_bytes'] or
                now['uv_metered_bytes'] != before['uv_metered_bytes'] or
                now['download_bytes'] - before['download_bytes'] > CACHE_METADATA_ALLOWANCE):
            raise ValueError('offline runtime replacement transferred bytes')
        if reading['artifact_bytes'] > grant['byte_limits']['artifact_bytes']:
            raise ValueError('runtime replacement exceeds the shared artifact cap')
        return reading

    def validate(out):
        validate_recovery_result(read_json(verify_record(file_record(out / 'result.json'))['path']), normalized)
    return supervise(ledger, JOB, command, output, evidence=_evidence(grant), sample_resources=sample,
        validate_result=validate, poll_seconds=2., seconds_limit=grant['seconds'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--review', required=True)
    parser.add_argument('--authorization', required=True)
    parser.add_argument('--source-review', required=True)
    args = parser.parse_args()
    dispatch(shared_run_root(), {key: file_record(path) for key, path in (
        ('review', args.review), ('authorization', args.authorization), ('source_review', args.source_review))})


if __name__ == '__main__':
    main()
