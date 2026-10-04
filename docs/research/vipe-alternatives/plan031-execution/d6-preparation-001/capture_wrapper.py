"""Local preparation only: reviewed root admission required before actual use."""
import argparse
import ctypes
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

DENIED = ('socket', 'socketpair', 'connect', 'bind', 'listen', 'accept', 'accept4',
          'sendto', 'sendmsg', 'sendmmsg', 'recvfrom', 'recvmsg', 'recvmmsg',
          'io_uring_setup', 'io_uring_enter', 'io_uring_register')


def require(value, message):
    if not value:
        raise ValueError(message)


def record(path):
    path = Path(path).absolute()
    require('prompts' not in path.parts and 'prompts' not in path.resolve().parts, 'prompts prohibited')
    require(path.is_file(), 'missing file: ' + str(path))
    return dict(path=str(path), bytes=path.stat().st_size,
                sha256=hashlib.sha256(path.read_bytes()).hexdigest())


def write(path, value):
    with Path(path).open('x') as stream:
        json.dump(value, stream, indent=2)
        stream.write('\n')


def disk_bytes(path):
    # No symlink following, content reading or hashing. Deduplicate hard links.
    seen, total = set(), 0
    for directory, dirs, files in os.walk(path, followlinks=False):
        require('prompts' not in dirs and 'prompts' not in Path(directory).parts, 'disk scope reaches prompts')
        dirs[:] = [d for d in dirs if not Path(directory, d).is_symlink()]
        for name in files:
            p = Path(directory, name)
            stat = p.lstat()
            identity = (stat.st_dev, stat.st_ino)
            if not p.is_symlink() and identity not in seen:
                seen.add(identity)
                total += max(stat.st_size, stat.st_blocks * 512)
    return total


def census():
    result = {}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit():
            continue
        try:
            raw = (p / 'stat').read_text()
            fields = raw[raw.rindex(')') + 2:].split()
            result[int(p.name)] = dict(pid=int(p.name), ppid=int(fields[1]),
                start_ticks=int(fields[19]), state=fields[0])
        except FileNotFoundError:
            continue
    return result


def network_sandbox(command):
    # Linux libseccomp filter inherited across fork/exec; no-new-privileges prevents removal.
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(38, 1, 0, 0, 0) == 0, 'PR_SET_NO_NEW_PRIVS failed')
    lib = ctypes.CDLL('libseccomp.so.2', use_errno=True)
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_syscall_resolve_name.argtypes = [ctypes.c_char_p]
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = [ctypes.c_void_p]
    lib.seccomp_release.argtypes = [ctypes.c_void_p]
    ctx = lib.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    require(bool(ctx), 'seccomp_init failed')
    try:
        for name in DENIED:
            nr = lib.seccomp_syscall_resolve_name(name.encode())
            require(nr >= 0, 'unsupported syscall: ' + name)
            require(lib.seccomp_rule_add(ctx, 0x00050001, nr, 0) == 0,
                    'seccomp rule failed: ' + name)  # errno EPERM
        require(lib.seccomp_load(ctx) == 0, 'seccomp_load failed')
    finally:
        lib.seccomp_release(ctx)
    os.execve(command[0], command, dict(os.environ))


def observe_descendants(observed):
    current = census()
    changed = True
    while changed:
        changed = False
        parents = {os.getpid()} | {i['pid'] for i in observed.values()
            if current.get(i['pid'], {}).get('start_ticks') == i['start_ticks']}
        for pid, info in current.items():
            identity = (pid, info['start_ticks'])
            if identity not in observed and info['ppid'] in parents:
                try:
                    descriptor = os.pidfd_open(pid)
                except ProcessLookupError:
                    continue
                if census().get(pid, {}).get('start_ticks') != info['start_ticks']:
                    os.close(descriptor)
                    raise ValueError('PID identity changed')
                observed[identity] = dict(info, pidfd=descriptor)
                changed = True
    return current


def run(config_path):
    started = time.monotonic()
    config_record = record(config_path)
    config = json.loads(Path(config_path).read_text())
    require(config['schema'] == 'plan069-moge-parent-cpu-request/v1', 'wrong request schema')
    require(config['candidate'] == 'D6', 'this prepared wrapper is D6 only')
    require(record(Path(sys.executable).resolve()) == config['bootstrap'], 'exact bootstrap interpreter changed')
    require(Path(config['interpreter_invocation']).absolute() == Path(sys.executable).absolute(), 'explicit interpreter invocation changed')
    for variable in ('LD_PRELOAD', 'LD_AUDIT'):
        require(variable not in os.environ, 'unreviewed loader injection: ' + variable)
    require(0 < config['seconds'] <= 180 and 5 <= config['cleanup_seconds'] < config['seconds'], 'invalid time bound')
    require(config['cpu_workers'] == 7, 'retained producer requires seven threads')
    require(config['admitted'] is True and config['charge_owner'] == 'root', 'root admission required')
    require(set(config['bindings']) == {'setup', 'setup_request', 'setup_dispatch', 'runtime_recipe', 'source_review'}, 'missing or unexpected binding role')
    for item in config['bindings'].values():
        require(record(item['path']) == item, 'immutable input changed: ' + item['path'])
    require(config['bindings']['setup']['sha256'] == config['accepted_setup_sha256'], 'different historical setup')
    review = json.loads(Path(config['bindings']['source_review']['path']).read_text())
    require(review.get('candidate') == 'D6' and review.get('status') == 'passed' and
            review.get('root_source_commit') == config['root_source_commit'], 'wrong current source review')
    require(review['runtime_recipe'] == config['bindings']['runtime_recipe'], 'review recipe mismatch')
    for item in review['local_sources']:
        require(record(item['path']) == item, 'current source changed')
    # Root supplies small method/current sources/setup/request/dispatch/recipe records.
    # Never apply historical worker records to current mutable source paths.
    command = config['command']
    require(command[0] == config['interpreter_invocation'] and command[1:3] == ['-B', config['method']['path']], 'exact method invocation required')
    require(record(config['method']['path']) == config['method'], 'method changed')
    require(command[3] == 'capture', 'capture mode required')
    for flag, role in (('--setup', 'setup'), ('--setup-request', 'setup_request'), ('--setup-dispatch', 'setup_dispatch')):
        require(command.count(flag) == 1 and command[command.index(flag) + 1] == config['bindings'][role]['path'], 'command binding mismatch: ' + flag)
    require(command.count('--root') == 1 and command[command.index('--root') + 1] == config['root'], 'root command mismatch')
    require(all(Path(i['path']).is_relative_to(Path(config['root'])) for i in review['local_sources']), 'source escaped reviewed root')
    require(command.count('--candidate') == 1 and command[command.index('--candidate') + 1] == 'D6', 'wrong command candidate')
    require(float(command[command.index('--seconds') + 1]) <= config['seconds'] - config['cleanup_seconds'], 'cleanup reserve missing')
    out = Path(config['output']).absolute()
    require(not out.exists(), 'wrapper output already exists')
    capture_out = Path(command[command.index('--output') + 1]).absolute()
    require(out == out.resolve() and capture_out == capture_out.resolve() and not capture_out.exists(), 'capture output is existing or escapes through symlink')
    roots = config['disk_roots']
    require({r['role'] for r in roots} >= {'global', 'candidate', 'runtime-cache'}, 'all disk scopes required')
    for r in roots:
        p = Path(r['path']).absolute()
        require(p == p.resolve() and p.exists(), 'invalid disk scope')
        require(r['maximum_total_bytes'] > 0 and r['maximum_delta_bytes'] >= 65536, 'invalid disk cap')
    require(any(capture_out.is_relative_to(Path(r['path'])) and out.is_relative_to(Path(r['path'])) for r in roots if r['role'] == 'candidate'), 'outputs escape candidate scope')
    require(any(Path(r['path']).is_relative_to(Path(g['path'])) for r in roots if r['role'] == 'candidate' for g in roots if g['role'] == 'global'), 'candidate escapes global scope')
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(36, 1, 0, 0, 0) == 0, 'subreaper setup failed')
    baseline = {r['role']: disk_bytes(r['path']) for r in roots}
    require(all(baseline[r['role']] <= r['maximum_total_bytes'] for r in roots), 'initial disk cap exceeded')
    out.mkdir(parents=True)
    process, error, observed, peak = None, None, {}, dict(baseline)
    cleanup_confirmed = False

    def sample():
        for r in roots:
            size = disk_bytes(r['path'])
            peak[r['role']] = max(peak[r['role']], size)
            require(size <= r['maximum_total_bytes'] and size - baseline[r['role']] <= r['maximum_delta_bytes'] - 32768,
                    'disk cap exceeded: ' + r['role'])

    def deadline(signum, frame):
        raise TimeoutError('whole wrapper capture deadline')

    previous_handler = signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, max(.001, started + config['seconds'] - config['cleanup_seconds'] - time.monotonic()))
    try:
        write(out / 'request.json', config)
        write(out / 'command.json', dict(command=command, sandbox=['libseccomp.so.2', list(DENIED)],
            wrapper=record(__file__), config=config_record, baseline_bytes=baseline))
        env = dict(os.environ, CUDA_VISIBLE_DEVICES='', HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1',
            HF_DATASETS_OFFLINE='1', UV_OFFLINE='1', PIP_NO_INDEX='1', PYTHONDONTWRITEBYTECODE='1', OMP_NUM_THREADS='7', MKL_NUM_THREADS='7',
            OPENBLAS_NUM_THREADS='7', NUMEXPR_NUM_THREADS='7', OPENCV_FOR_THREADS_NUM='7', MAX_JOBS='7')
        with (out / 'stdout.txt').open('xb') as stdout, (out / 'stderr.txt').open('xb') as stderr:
            process = subprocess.Popen([sys.executable, '-B', str(Path(__file__).absolute()), 'sandbox', '--'] + command,
                env=env, stdin=subprocess.DEVNULL, stdout=stdout, stderr=stderr, start_new_session=True)
            while True:
                observe_descendants(observed)
                sample()
                require(time.monotonic() - started < config['seconds'] - config['cleanup_seconds'], 'CPU capture deadline')
                if process.poll() is not None:
                    require(process.returncode == 0, 'producer failed')
                    break
                time.sleep(.1)
        captured = json.loads((capture_out / 'capture.json').read_text())
        require(captured.get('schema') == 'plan069-moge-cpu-capture/v1' and captured.get('candidate') == 'D6' and
                captured.get('status') == 'passed' and captured.get('cleanup_confirmed') is True and
                captured.get('native_cpu') == record(capture_out / 'native-cpu.json'), 'missing or failed exact capture result')
        for item in config['bindings'].values():
            require(record(item['path']) == item, 'input changed during capture')
        for item in review['local_sources']:
            require(record(item['path']) == item, 'current source changed during capture')
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        cleanup_deadline = min(started + config['seconds'], time.monotonic() + config['cleanup_seconds'])
        try:
            while time.monotonic() < cleanup_deadline:
                current = observe_descendants(observed)
                live = [i for i in observed.values() if current.get(i['pid'], {}).get('start_ticks') == i['start_ticks'] and current[i['pid']]['state'] != 'Z']
                for info in live:
                    try:
                        signal.pidfd_send_signal(info['pidfd'], signal.SIGKILL)
                    except ProcessLookupError:
                        pass  # Exited after census; continue retiring all other identities.
                while True:
                    try:
                        if os.waitpid(-1, os.WNOHANG)[0] == 0:
                            break
                    except ChildProcessError:
                        break
                if not live:
                    cleanup_confirmed = True
                    break
                time.sleep(.05)
            require(cleanup_confirmed, 'observed descendant cleanup unconfirmed')
            sample()
        except BaseException as exc:
            error = (error or '') + '; cleanup: ' + type(exc).__name__ + ': ' + str(exc)
        elapsed = time.monotonic() - started
        write(out / 'result.json', dict(schema='plan069-moge-parent-cpu-result/v1', candidate='D6',
            status='passed' if error is None and cleanup_confirmed and elapsed <= config['seconds'] else 'failed',
            error=error, elapsed_seconds=elapsed, timing_scope='wrapper entry through observed descendant cleanup and final disk census; terminal write excluded',
            cleanup_confirmed=cleanup_confirmed, cleanup_scope='all observed PID/start_ticks identities; subreaper orphan adoption',
            descendants=[{k: v for k, v in i.items() if k != 'pidfd'} for i in observed.values()],
            baseline_bytes=baseline, peak_bytes=peak, network_policy='inherited seccomp socket syscall denial',
            download_bytes=0, inference=False, cuda_operations=False, cpu_charge_applied=False, ledger_modified=False,
            final_terminal_disk_census_required=True, result_assembly_charge_required=True))
        for info in observed.values():
            os.close(info['pidfd'])
        signal.signal(signal.SIGALRM, previous_handler)
    require(error is None and cleanup_confirmed and elapsed <= config['seconds'], error or 'cleanup/deadline failed')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sandbox':
        network_sandbox(sys.argv[3:])
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('--request', required=True)
        run(parser.parse_args().request)
