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
from .s1_validation_contract import ROOT, STDIN, ARGV, RUNNER, CAPTURE, ENVIRONMENT, source_paths, no_timeout_launch


def stamp():
    return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), monotonic=time.monotonic())


def capture(directory, timeout_seconds=300, diagnostic=False, *, no_timeout=False):
    if type(no_timeout) is not bool or (no_timeout and timeout_seconds is not None):
        raise ValueError('no-timeout mode requires null timeout')
    if not no_timeout and (type(timeout_seconds) is not int or not 0 < timeout_seconds <= (120 if diagnostic else 300)):
        raise ValueError('invalid invocation cap')
    directory = Path(directory).resolve()
    launch=None
    if no_timeout:
        launch=file_record(os.environ['S1_OWNED_ROOT_NOTE'])
        no_timeout_launch(launch,str(directory),diagnostic=diagnostic)
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
        creation=None
        if no_timeout:
            # The stdin runner does not exist yet, so its later ancestry anchor
            # cannot audit its own creation. Bind this first edge to the freshly
            # verified driver note and the complete current capture subtree.
            note=no_timeout_launch(launch,str(directory),diagnostic=diagnostic)
            from .s1_helper_session import creation_identity_snapshot,owned_charge,register_owned,retire_owned
            before_creation=creation_identity_snapshot(os.getpid())
            if before_creation['processes']!=[note['ownership_root']]:raise ValueError('capture differs from Main admitted root')
            owned_charge(before_creation['B']+1,0)
            creation=dict(before=before_creation,authority=note['admission'],cpu_bound='B+max(1,H)≤8')
        process = subprocess.Popen(ARGV, cwd=ROOT, env=env, stdin=stdin, stdout=stdout, stderr=stderr, start_new_session=True)
        try:
            if no_timeout:
                register_owned(process.pid,'capture stdin runner')
                creation['after']=creation_identity_snapshot(os.getpid())
                creation['child']=next(row for row in creation['after']['processes'] if row['pid']==process.pid)
                if creation['after']['processes']!=sorted([note['ownership_root'],creation['child']],key=lambda row:row['pid']):raise ValueError('unexpected process at capture creation')
            returncode = process.wait() if no_timeout else process.wait(timeout=timeout_seconds)
        except subprocess.TimeoutExpired:
            timed_out = True
            os.killpg(process.pid, signal.SIGKILL)
            returncode = process.wait()
        except BaseException as primary:
            if no_timeout:
                try:
                    if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
                    process.wait();retire_owned(process.pid)
                except BaseException as cleanup:
                    primary.s1_owned_process=process
                    primary.add_note('capture owned retirement: '+repr(cleanup))
            raise
        finally:
            if no_timeout and process.returncode is not None:retire_owned(process.pid)
    if no_timeout:
        creation['retired']=creation_identity_snapshot(os.getpid())
        if creation['retired']['processes']!=[note['ownership_root']]:raise ValueError('capture child retirement unresolved')
        creation['retirement']=dict(identity=creation['child'],method='matching Popen.wait',returncode=returncode,completed=True,absent_after=True)
    end = stamp()
    receipt = directory/'receipt.json'
    value = dict(schema='s1-cpu-execution/v1', requested_argv=ARGV, cwd=str(ROOT.resolve()), environment=environment,
        run_directory=str(directory), start=start, end=end, elapsed_seconds=end['monotonic']-start['monotonic'],
        child_pid=process.pid, returncode=returncode, timed_out=timed_out, wait_completed=True, timeout_seconds=timeout_seconds,
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(), sources_before=before,
        sources_after=[file_record(p) for p in source_paths()], receipt=file_record(receipt) if receipt.exists() else None,
        stdin=file_record(directory/'stdin.py'), runner=file_record(directory/'runner.py'), capture=file_record(directory/'capture.py'),
        interpreter=file_record(ROOT/ARGV[0]), stdout=file_record(directory/'process-stdout.log'), stderr=file_record(directory/'process-stderr.log'))
    if no_timeout:
        value.update(schema='s1-cpu-execution/v2',execution_mode='no-timeout',launch_note=launch,creation=creation,
            wait=dict(method='Popen.wait',timeout_seconds=None,pid=process.pid,returncode=returncode,completed=True))
    (directory/'execution.json').write_text(json.dumps(value, indent=2, allow_nan=False)+'\n')
    print(json.dumps(dict(directory=str(directory), child_pid=process.pid, returncode=returncode, timed_out=timed_out)))
    return returncode if returncode >= 0 else 128-returncode


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('directory')
    mode=parser.add_mutually_exclusive_group()
    mode.add_argument('--timeout',type=int)
    mode.add_argument('--no-timeout',action='store_true')
    parser.add_argument('--diagnostic', action='store_true')
    args = parser.parse_args()
    return capture(args.directory,None if args.no_timeout else (300 if args.timeout is None else args.timeout),args.diagnostic,no_timeout=args.no_timeout)


if __name__ == '__main__':
    raise SystemExit(main())
