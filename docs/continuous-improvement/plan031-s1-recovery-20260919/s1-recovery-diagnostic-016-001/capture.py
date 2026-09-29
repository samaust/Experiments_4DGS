"""Outer CPU process capture: immutable evidence is published only after wait."""
import argparse
import datetime
import json
import os
from pathlib import Path
import signal
import subprocess
import time

from .files import file_record
from .s1_validation_contract import ROOT, STDIN, ARGV, RUNNER, CAPTURE, ENVIRONMENT, source_paths


def stamp():
    return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), monotonic=time.monotonic())


def capture(directory, timeout_seconds=300, diagnostic=False):
    if type(timeout_seconds) is not int or not 0 < timeout_seconds <= (120 if diagnostic else 300):
        raise ValueError('invalid invocation cap')
    directory = Path(directory).resolve()
    directory.mkdir(parents=True, exist_ok=False)
    (directory/'stdin.py').write_text(STDIN)
    (directory/'runner.py').write_bytes(RUNNER.read_bytes())
    (directory/'capture.py').write_bytes(CAPTURE.read_bytes())
    before = [file_record(p) for p in source_paths()]
    environment = dict(ENVIRONMENT)
    if diagnostic:
        environment['S1_RECEIPT_DIAGNOSTIC'] = '1'
    env = os.environ.copy()
    for key, value in environment.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    env['S1_VALIDATION_RUN_DIRECTORY'] = str(directory)
    start = stamp()
    timed_out = False
    with (directory/'stdin.py').open('rb') as stdin, (directory/'process-stdout.log').open('wb') as stdout, (directory/'process-stderr.log').open('wb') as stderr:
        process = subprocess.Popen(ARGV, cwd=ROOT, env=env, stdin=stdin, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            returncode = process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            returncode = process.wait()
    end = stamp()
    receipt = directory/'receipt.json'
    value = dict(schema='s1-cpu-execution/v1', requested_argv=ARGV, cwd=str(ROOT.resolve()), environment=environment,
        run_directory=str(directory), start=start, end=end, elapsed_seconds=end['monotonic']-start['monotonic'],
        child_pid=process.pid, returncode=returncode, timed_out=timed_out, wait_completed=True, timeout_seconds=timeout_seconds,
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), sources_before=before,
        sources_after=[file_record(p) for p in source_paths()], receipt=file_record(receipt) if receipt.exists() else None,
        stdin=file_record(directory/'stdin.py'), runner=file_record(directory/'runner.py'), capture=file_record(directory/'capture.py'),
        interpreter=file_record(ROOT/ARGV[0]), stdout=file_record(directory/'process-stdout.log'), stderr=file_record(directory/'process-stderr.log'))
    (directory/'execution.json').write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(directory=str(directory), child_pid=process.pid, returncode=returncode, timed_out=timed_out)))
    return returncode if returncode >= 0 else 128-returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    parser.add_argument('--timeout', type=int, default=300)
    parser.add_argument('--diagnostic', action='store_true')
    args = parser.parse_args()
    return capture(args.directory, args.timeout, args.diagnostic)


if __name__ == '__main__':
    raise SystemExit(main())
