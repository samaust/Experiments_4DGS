"""Run the retained full CPU suite under a reviewed overall deadline."""
import argparse
import hashlib
import json
import os
import signal
import subprocess
import time
from pathlib import Path
from typing import Any


def record(path):
    path = Path(path).absolute()
    if 'prompts' in path.parts or 'prompts' in path.resolve().parts:
        raise ValueError('forbidden prompts path')
    data = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def read_json(path):
    record(path)  # Guard both the original spelling and resolved target first.
    return json.loads(Path(path).read_text())


def verify(row):
    if record(row['path']) != row:
        raise ValueError('changed reviewed file: ' + row['path'])


def process_rows():
    rows = {}
    for path in Path('/proc').glob('[0-9]*/stat'):
        try:
            raw = path.read_text()
            fields = raw[raw.rfind(')') + 2:].split()
            pid = int(path.parent.name)
            rows[pid] = dict(pid=pid, ppid=int(fields[1]), pgid=int(fields[2]), start_ticks=int(fields[19]), state=fields[0])
        except (OSError, ValueError, IndexError):
            pass
    return rows


def census(child, owned):
    rows = process_rows()
    branch = {pid for pid, old in owned.items() if pid in rows and rows[pid]['start_ticks'] == old['start_ticks']}
    while True:
        updated = branch | {pid for pid, row in rows.items() if row['ppid'] in branch}
        if updated == branch:
            break
        branch = updated
    for pid in branch:
        if pid in rows and pid not in owned:
            owned[pid] = rows[pid]
    return rows


def survivors(owned):
    return [row for pid, row in process_rows().items() if pid in owned and row['start_ticks'] == owned[pid]['start_ticks'] and row['state'] != 'Z']


def cleanup(child, owned, deadline):
    # Signal only observed identities, including descendants in detached groups.
    census(child, owned)
    for sig in (signal.SIGTERM, signal.SIGKILL):
        if child.poll() is None:
            child.send_signal(sig)
        snapshot = survivors(owned)
        for row in snapshot:
            if time.monotonic() >= deadline - 2:
                raise TimeoutError('owned cleanup deadline reached')
            current = process_rows().get(row['pid'])
            if current and current['start_ticks'] == row['start_ticks']:
                try:
                    os.kill(row['pid'], sig)
                except ProcessLookupError:
                    pass
        until = min(deadline - 2, time.monotonic() + 1)
        while survivors(owned) and time.monotonic() < until:
            time.sleep(.05)
    if child.poll() is None and time.monotonic() < deadline - 1:
        try:
            child.wait(timeout=min(1, deadline - time.monotonic() - 1))
        except subprocess.TimeoutExpired:
            pass
    remaining = survivors(owned)
    return dict(method='observed /proc PID/start-ticks census and verified-identity TERM/KILL', surviving_observed_owned_processes=remaining, confirmed_no_surviving_observed_processes=not remaining, limitation='100 ms polling cannot prove ownership of unobserved short-lived or detached descendants')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('checkout', 'overlay', 'output', 'review-request'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--max-seconds', type=float, default=1200)
    args = parser.parse_args()
    started = time.monotonic()
    if not 20 < args.max_seconds <= 1200:
        raise ValueError('full CPU cap must be within (20, 1200] seconds')
    deadline = started + args.max_seconds
    root = Path(args.checkout).resolve()
    out = Path(args.output).resolve()
    out.mkdir(exist_ok=False)
    fixture = out / 'disposable-results'
    fixture.mkdir()
    matplotlib = out / 'matplotlib'
    matplotlib.mkdir()
    python = '/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python'
    env = dict(os.environ, PYTHONPATH=f'{args.overlay}:{root}/scripts:{root}/tests', VIPE_CPU_VALIDATION='1', S1_VALIDATION_RUN_DIRECTORY=str(fixture), CUDA_VISIBLE_DEVICES='', MPLCONFIGDIR=str(matplotlib), MPLBACKEND='Agg', PYTHONDONTWRITEBYTECODE='1', PYTEST_DISABLE_PLUGIN_AUTOLOAD='1', OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1', NUMEXPR_NUM_THREADS='1')
    receipt = dict(schema='plan069-integrated-cpu-test-capture/v1', record_kind='actual', scope='Full CPU test suite; no model admission receipt', checkout=str(root), max_seconds=args.max_seconds, commands=[], passed=False)

    def expired(signum, frame):
        raise TimeoutError('overall CPU qualification deadline reached')

    def git(*words):
        return subprocess.check_output(['git', *words], cwd=root, text=True, timeout=max(.001, deadline - time.monotonic() - 1))

    def sources():
        rows = []
        for name in sorted(git('ls-files', '-z').split('\0')):
            path = root / name
            if name and 'prompts' not in Path(name).parts and path.is_file() and path.suffix in ['.py', '.json', '.txt', '.in', '.md', '.yaml', '.yml', '.toml']:
                rows.append(record(path))
        return rows

    def environment_records(request):
        verify(request['interpreter'])
        verify(request['environment_bindings'])
        for package in read_json(request['environment_bindings']['path']):
            for row in package['metadata'] + package.get('files', []):
                verify(row)

    old_alarm = signal.signal(signal.SIGALRM, expired)
    old_term = signal.signal(signal.SIGTERM, expired)
    signal.setitimer(signal.ITIMER_REAL, args.max_seconds - 15)
    request = None
    try:
        request = read_json(args.review_request)
        receipt['review_request'] = record(args.review_request)
        if request.get('status') != 'REVIEW':
            raise ValueError('CPU request is not finalized for review')
        for key in ('launcher', 'builder', 'cpu_admission', 'source_bindings'):
            verify(request[key])
        if request['launcher']['path'] != str(Path(__file__).resolve()) or request['output'] != str(out) or request['max_seconds'] != args.max_seconds:
            raise ValueError('reviewed launcher/output/time mismatch')
        if request['checkout'] != str(root) or request['overlay'] != str(Path(args.overlay).resolve()) or request['interpreter']['path'] != python:
            raise ValueError('reviewed checkout/overlay/interpreter mismatch')
        receipt['head'] = git('rev-parse', 'HEAD').strip()
        if receipt['head'] != request['base_head']:
            raise ValueError('reviewed HEAD changed')
        environment_records(request)
        receipt['sources_before'] = sources()
        if receipt['sources_before'] != read_json(request['source_bindings']['path']):
            raise ValueError('reviewed source set changed')
        receipt['environment'] = {key: env[key] for key in ('PYTHONPATH', 'VIPE_CPU_VALIDATION', 'S1_VALIDATION_RUN_DIRECTORY', 'CUDA_VISIBLE_DEVICES', 'MPLCONFIGDIR', 'MPLBACKEND', 'PYTHONDONTWRITEBYTECODE', 'PYTEST_DISABLE_PLUGIN_AUTOLOAD', 'OMP_NUM_THREADS', 'OPENBLAS_NUM_THREADS', 'MKL_NUM_THREADS', 'NUMEXPR_NUM_THREADS')}
        jobs = [('pytest', [python, '-B', '-m', 'pytest', '-q', '-p', 'no:cacheprovider', 'tests/test_basketball_scene.py', 'tests/test_sync_pivot_budget.py', 'tests/test_sync_timing.py']), ('unittest', [python, '-B', '-m', 'unittest', 'discover', '-s', 'tests', '-v'])]
        for name, command in jobs:
            row: dict[str, Any] = dict(name=name, command=command, timed_out=False, start_new_session=True)
            receipt['commands'].append(row)
            log = out / (name + '.log')
            row['log'] = str(log)
            phase_start = time.monotonic()
            with log.open('xb') as stream:
                child = subprocess.Popen(command, cwd=root, env=env, stdout=stream, stderr=subprocess.STDOUT, start_new_session=True)
                owned = {}
                try:
                    initial = process_rows().get(child.pid)
                    if initial is not None:
                        owned[child.pid] = initial
                    print(json.dumps(dict(running=name, pid=child.pid, output=str(out))), flush=True)
                    while child.poll() is None:
                        census(child, owned)
                        time.sleep(.1)
                except TimeoutError:
                    row['timed_out'] = True
                    raise
                finally:
                    signal.setitimer(signal.ITIMER_REAL, max(.001, deadline - time.monotonic() - 2))
                    signal.signal(signal.SIGTERM, signal.SIG_IGN)
                    try:
                        row['cleanup'] = cleanup(child, owned, deadline)
                    except (Exception, KeyboardInterrupt) as error:
                        row['cleanup'] = dict(confirmed_no_surviving_observed_processes=False, verification_incomplete=True, error=dict(type=type(error).__name__, message=str(error)))
                    row['observed_owned_processes'] = list(owned.values())
                    row['returncode'] = child.poll()
                    row['elapsed_seconds'] = time.monotonic() - phase_start
                    signal.signal(signal.SIGTERM, expired)
                    signal.setitimer(signal.ITIMER_REAL, max(.001, deadline - time.monotonic() - 15))
            row['log_sha256'] = record(log)['sha256']
            if row['returncode'] or not row['cleanup']['confirmed_no_surviving_observed_processes']:
                break
        receipt['passed'] = len(receipt['commands']) == 2 and all(row['returncode'] == 0 and not row['timed_out'] and row['cleanup']['confirmed_no_surviving_observed_processes'] for row in receipt['commands'])
    except (Exception, KeyboardInterrupt) as error:
        receipt['error'] = dict(type=type(error).__name__, message=str(error))
        receipt['passed'] = False
    finally:
        signal.setitimer(signal.ITIMER_REAL, max(.001, deadline - time.monotonic() - 1))
        try:
            if request is None:
                raise ValueError('preflight request unavailable')
            verify(receipt['review_request'])
            for key in ('launcher', 'builder', 'cpu_admission', 'source_bindings'):
                verify(request[key])
            environment_records(request)
            receipt['environment_bytes_unchanged'] = True
            receipt['head_after'] = git('rev-parse', 'HEAD').strip()
            receipt['head_unchanged'] = receipt.get('head') == receipt['head_after']
            receipt['sources_after'] = sources()
            receipt['source_bytes_unchanged'] = receipt.get('sources_before') == receipt['sources_after']
            receipt['passed'] = receipt['passed'] and receipt['head_unchanged'] and receipt['source_bytes_unchanged']
        except (Exception, KeyboardInterrupt) as error:
            receipt['verification_error'] = dict(type=type(error).__name__, message=str(error))
            receipt['passed'] = False
        signal.setitimer(signal.ITIMER_REAL, 0)
        receipt['elapsed_seconds'] = time.monotonic() - started
        receipt['within_wall_limit'] = receipt['elapsed_seconds'] <= args.max_seconds
        receipt['passed'] = receipt['passed'] and receipt['within_wall_limit']
        (out / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
        signal.signal(signal.SIGALRM, old_alarm)
        signal.signal(signal.SIGTERM, old_term)
        print(json.dumps(dict(passed=receipt['passed'], elapsed_seconds=receipt['elapsed_seconds'], receipt=str(out / 'receipt.json'))), flush=True)


if __name__ == '__main__':
    main()
