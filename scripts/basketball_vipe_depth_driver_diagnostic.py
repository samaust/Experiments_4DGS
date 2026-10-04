"""Dispatch one newly approved driver-only syscall diagnostic, never a retry."""
import argparse
import os
from pathlib import Path

from vipe_benchmark.config import load
from vipe_benchmark.depth_driver_diagnostic import JOB, validate_request, validate_result
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import supervise


def dispatch(path):
    record = file_record(path); request, proposal = validate_request(record)
    if request['record_kind'] != 'actual' or os.environ.get('CUDA_VISIBLE_DEVICES') not in (None, '0'):
        raise ValueError('actual unmasked single GPU diagnostic required')
    if any(key in os.environ for key in ('LD_PRELOAD', 'LD_AUDIT', 'PYTHONPATH', 'PYTHONHOME')):
        raise ValueError('unreviewed loader/path injection')
    run = Path(request['ledger_path']).parent; output = Path(request['output'])
    trace = output.with_suffix('.syscalls.log')
    if output.exists() or trace.exists() or trace.is_symlink() or trace.absolute() != trace.resolve():
        raise ValueError('diagnostic output must be fresh')
    ledger = Ledger(request['ledger_path'], dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210))
    def sample():
        from vipe_benchmark.budgets import directory_bytes
        reading = resources(run, gpu=True)
        size = (directory_bytes(output) if output.exists() else 0) + (trace.stat().st_size if trace.exists() else 0)
        if reading['device_bytes'] > proposal['device_bytes'] or size > proposal['artifact_bytes']:
            raise ValueError('diagnostic device/artifact bound exceeded')
        return reading
    ledger.authorize_depth_driver_diagnostic(record)
    supervise(ledger, JOB, request['command'], output, evidence=dict(request=record),
        sample_resources=sample, validate_result=lambda out: validate_result(read_json(out / 'result.json'), record),
        poll_seconds=.2, cpu_workers_limit=7, cleanup_reserve_seconds=proposal['cleanup_seconds'])
    finish = ledger.states().get(JOB, {})
    if finish.get('event') != 'finish' or finish.get('status') != 'complete' or finish.get('cleanup_confirmed') is not True:
        raise ValueError('diagnostic did not finish with confirmed cleanup')
    write_json(output / 'trace-record.json', file_record(trace))
    write_json(output / 'finish.json', finish)
    return finish


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--request', required=True)
    dispatch(parser.parse_args().request)
