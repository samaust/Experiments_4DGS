"""Reserved one-use D2 map worker; no model load before exact ledger binding."""

import argparse
import os
from pathlib import Path
import sys

from vipe_benchmark.config import load
from vipe_benchmark.d2_maps import run, worker_command
from vipe_benchmark.d2_preflight import verify_runtime
from vipe_benchmark.depth_admission import local_source_records
from vipe_benchmark.files import file_record, object_hash, read_json, verify_record
from vipe_benchmark.ledger import Ledger


def active_reservation(request, request_path, output):
    if request.get('record_kind') != 'actual':
        return False
    ledger_path = Path(request['ledger_path'])
    if not ledger_path.is_absolute() or ledger_path.name != 'ledger.jsonl':
        return False
    job_id = 'plan069-D2-maps-001'
    if request.get('job_id') != job_id or output.resolve() != (
            ledger_path.parent / 'jobs' / job_id).resolve():
        return False
    if not isinstance(request.get('admission'), dict):
        return False
    admission = read_json(verify_record(request['admission'])['path'])
    if (admission.get('schema') != 'plan069-depth-admission-result/v1' or
            admission.get('status') != 'passed' or admission.get('candidate') != 'D2' or
            request.get('component') != 'D2' or
            admission.get('proposal_sha256') != request.get('proposal_sha256') or
            object_hash(request.get('proposal')) != request.get('proposal_sha256') or
            request.get('local_sources') != local_source_records('D2')):
        return False
    reviewed = read_json(verify_record(admission['review'])['path'])
    if request['proposal'] not in reviewed.get('proposals', []):
        return False
    source = read_json(verify_record(admission['source_review'])['path'])
    if source.get('local_sources') != request['local_sources']:
        return False
    qualified = read_json(verify_record(admission['qualification'])['path'])
    if (qualified.get('schema') != 'plan069-depth-D2-qualification/v1' or
            qualified.get('candidate') != 'D2' or
            qualified.get('worker_runtime') != request.get('runtime') or
            qualified.get('preflight') != request.get('preflight') or
            qualified.get('assets_record') != request.get('assets_record') or
            qualified.get('runtime') != admission.get('runtime')):
        return False
    preflight = read_json(verify_record(request['preflight'])['path'])
    if (preflight.get('runtime') != request.get('runtime') or
            preflight.get('assets') != request.get('assets_record') or
            preflight.get('proposal_sha256') != request['proposal_sha256']):
        return False
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    state = Ledger(ledger_path, config).states().get(job_id, {})
    command = worker_command(request, request_path, output)
    return bool(state.get('event') == 'reserve' and
        state.get('resource') == 'gpu' and state.get('seconds') == 3600 and
        state.get('command') == command and
        state.get('evidence', {}).get('executable') == file_record(request['runtime']['python']) and
        state.get('evidence', {}).get('request') == file_record(request_path) and
        state.get('evidence', {}).get('admission') == request.get('admission') and
        os.environ.get('VIPE_RESERVATION_START') == str(state.get('monotonic_start')))


class LazyD2Backend:
    component = 'D2'

    def __init__(self, request):
        self.request = request
        self.native = None

    def predict(self, rgb, K, valid):
        if self.native is None:
            from vipe_benchmark.backends import build_backend
            from vipe_benchmark.stages import _model_runtime
            verify_runtime(self.request['runtime'])
            _model_runtime(self.request)
            assets = read_json(self.request['assets_record']['path'])
            self.native = build_backend('D2', assets, device='cuda')
        return self.native.predict(rgb, K, valid)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    request = read_json(args.request)
    if sys.executable != request.get('runtime', {}).get('python'):
        raise ValueError('D2 worker interpreter differs from qualified E5 runtime')
    if not active_reservation(request, args.request, args.output):
        raise ValueError('active exact D2 GPU reservation required')
    run(request, args.output, backend=LazyD2Backend(request),
        reservation_check=lambda row, out: active_reservation(row, args.request, out))


if __name__ == '__main__':
    main()
