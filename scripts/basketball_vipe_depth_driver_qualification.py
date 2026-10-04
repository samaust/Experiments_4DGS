"""Dispatch only the separately approved D6 GPU-aware qualification."""
import argparse
import os
from pathlib import Path

from vipe_benchmark.config import load
from vipe_benchmark.depth_driver_qualification import JOB, validate_request, validate_result
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import supervise


def dispatch(request_path):
    record = file_record(request_path)
    request, proposal = validate_request(record)
    if os.environ.get('CUDA_VISIBLE_DEVICES') not in (None, '0'):
        raise ValueError('qualification requires the approved unmasked single GPU')
    for variable in ('LD_PRELOAD', 'LD_AUDIT', 'PYTHONPATH', 'PYTHONHOME'):
        if variable in os.environ:
            raise ValueError('unreviewed loader/path injection: ' + variable)
    if request['record_kind'] != 'actual':
        raise ValueError('fixture cannot dispatch actual GPU qualification')
    root = Path(request['ledger_path']).parent
    output = Path(request['output'])
    if not output.is_relative_to(root) or output.exists():
        raise ValueError('fresh output in shared run required')
    ledger = Ledger(request['ledger_path'], dict(load(), new_download_gib_limit=110,
        new_artifact_disk_gib_limit=210))
    def sample():
        reading = resources(root, gpu=True)
        if reading['device_bytes'] > proposal['device_bytes']:
            raise ValueError('driver qualification device cap exceeded')
        if output.exists():
            from vipe_benchmark.budgets import directory_bytes
            if directory_bytes(output) > proposal['artifact_bytes']:
                raise ValueError('driver qualification artifact cap exceeded')
        return reading
    def accept(out):
        result = read_json(out / 'result.json')
        # Supervisor separately proves descendant/GPU cleanup in its finish.
        validate_result(result, record, cleanup_confirmed=True)
        return dict(status='passed', scope='GPU driver import; two actual CPU weight loads; no inference')
    ledger.authorize_depth_driver_qualification(record)
    supervise(ledger, JOB, request['command'], output,
        evidence=dict(request=record), sample_resources=sample, validate_result=accept,
        poll_seconds=.5, cpu_workers_limit=7)
    finish = ledger.states().get(JOB, {})
    if finish.get('event') != 'finish' or finish.get('status') != 'complete' or finish.get('result') != file_record(output / 'result.json'):
        raise ValueError('accepted exact driver qualification finish missing')
    write_json(output / 'finish.json', finish)
    return finish


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    dispatch(parser.parse_args().request)
