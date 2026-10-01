"""Prepare and charge the one shared accepted depth comparison context."""

import argparse
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

from vipe_benchmark.config import ROOT, load
from vipe_benchmark.depth_clips import prepare_context
from vipe_benchmark.execution import result_artifact
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.ledger import Ledger


RUN_ID = 'plan031-20260913T032700Z'
JOB_ID = 'plan069-depth-context-002'
REVIEW = ROOT / 'docs/specs/plan031-execution/depth-execution-review-001.json'
DO = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'


def _stop_worker(process):
    """Reap the full context process group before releasing the ledger lock."""
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    try:
        process.communicate(timeout=10)
    except subprocess.TimeoutExpired as error:
        raise RuntimeError('depth context worker survived termination') from error
    try:
        os.killpg(process.pid, 0)
    except ProcessLookupError:
        return
    raise RuntimeError('depth context worker process group survived termination')


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


def run():
    repository = shared_run_root()
    local = repository / '.local/vipe-alternatives' / RUN_ID
    output = local / 'jobs' / JOB_ID
    docs = ROOT / 'docs/research/vipe-alternatives' / RUN_ID
    receipt_path = docs / (JOB_ID + '.json')
    charge_path = docs / (JOB_ID + '-charge.json')
    if output.exists() or receipt_path.exists() or charge_path.exists():
        raise ValueError('shared depth context already prepared or attempted')
    config = load()
    ledger = Ledger(local / 'ledger.jsonl', config)
    review, approved = file_record(REVIEW), file_record(DO)
    proposal = next(row for row in read_json(REVIEW)['proposals']
                    if row['candidate'] == 'D7')
    authority = read_json(DO)
    grant = next(row for row in authority['candidate_approvals']
                 if row['candidate'] == 'D7')
    if (authority['review'] != review or grant['status'] != 'approved' or
            grant['proposal_sha256'] != object_hash(proposal)):
        raise ValueError('exact approved D7 context preparation required')
    seconds = proposal['allocation']['cpu_seconds']
    if type(seconds) is not int or seconds <= 60:
        raise ValueError('approved CPU preparation allocation unavailable')
    inputs = result_artifact(local, 'prepare', 'inputs')
    if inputs != file_record(local / 'prepare/inputs.json'):
        raise ValueError('ledger-accepted input manifest differs')
    with ledger.locked() as (stream, events):
        if any(state['event'] == 'reserve' for state in ledger.states(events).values()):
            raise ValueError('active reservation prevents depth context preparation')
        if (ledger.totals(events)['cpu']['elapsed_seconds'] + seconds >
                config['cpu_prepare_score_report_seconds_limit']):
            raise ValueError('approved CPU preparation allocation unavailable')
        started = time.monotonic()
        context = None
        error = None
        try:
            command = [sys.executable, str(Path(__file__).resolve()), '--worker',
                '--inputs-sha256', inputs['sha256'], '--inputs-bytes', str(inputs['bytes']),
                '--output', str(output)]
            process = subprocess.Popen(command, stdout=subprocess.PIPE,
                stderr=subprocess.PIPE, start_new_session=True)
            try:
                _, stderr = process.communicate(timeout=seconds - 60)
            except BaseException as worker_error:
                _stop_worker(process)
                if isinstance(worker_error, subprocess.TimeoutExpired):
                    raise TimeoutError('approved depth CPU preparation deadline exceeded') from worker_error
                raise
            try:
                os.killpg(process.pid, 0)
            except ProcessLookupError:
                pass
            else:
                _stop_worker(process)
                raise RuntimeError('depth context worker left a process group')
            if process.returncode:
                raise RuntimeError('depth context worker failed: ' +
                    stderr.decode(errors='replace')[-2000:])
            context = file_record(output / 'context.json')
        except BaseException as caught:
            error = caught
        elapsed = time.monotonic() - started
        if elapsed >= seconds:
            error = TimeoutError('approved depth CPU preparation deadline exceeded')
        charge_payload = dict(schema='plan069-depth-context-charge/v1',
            status='failed' if error else 'prepared', inputs=inputs,
            context=context, elapsed_seconds=elapsed,
            error=None if error is None else f'{type(error).__name__}: {error}')
        write_json(charge_path, charge_payload)
        charge = ledger._append(stream, events, dict(event='cpu_preparation_charge',
            resource='cpu', elapsed_seconds=elapsed, evidence=file_record(charge_path)))
        write_json(receipt_path, dict(schema='plan069-depth-context-preparation/v1',
            status='failed' if error else 'complete', context=context, inputs=inputs,
            review=review, authorization=approved,
            proposal_sha256=object_hash(proposal),
            source=file_record(ROOT / 'scripts/vipe_benchmark/depth_clips.py'),
            elapsed_seconds=elapsed, charge_event_sha256=charge['event_sha256'],
            error=charge_payload['error']))
        if error is not None:
            raise error
        return dict(context=context, charge=charge)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run-id', default=RUN_ID)
    parser.add_argument('--worker', action='store_true')
    parser.add_argument('--inputs-sha256')
    parser.add_argument('--inputs-bytes', type=int)
    parser.add_argument('--output')
    args = parser.parse_args()
    if args.worker:
        if args.inputs_sha256 is None or args.inputs_bytes is None or args.output is None:
            raise ValueError('exact worker input and output records required')
        local = shared_run_root() / '.local/vipe-alternatives' / RUN_ID
        inputs = file_record(local / 'prepare/inputs.json')
        if inputs['sha256'] != args.inputs_sha256 or inputs['bytes'] != args.inputs_bytes:
            raise ValueError('accepted input changed before context worker')
        if Path(args.output) != local / 'jobs' / JOB_ID:
            raise ValueError('shared context output identity changed')
        prepare_context(inputs, args.output, load())
        return
    if args.run_id != RUN_ID:
        raise ValueError('shared depth context run identity changed')
    run()


if __name__ == '__main__':
    main()
