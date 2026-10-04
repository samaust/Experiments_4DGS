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
from typing import Any

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


def read_json(path):
    record(path)  # Guard lexical and resolved paths before content access.
    return json.loads(Path(path).read_text())


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


def verify_admission(config, review):
    """Validate protected setup, cumulative CPU admission and exact CPU source proof."""
    root = Path(config['root']).absolute()
    require(root == root.resolve() and 'prompts' not in root.parts, 'unsafe root')
    sys.path.insert(0, str(root / 'scripts'))
    from vipe_benchmark.config import load
    from vipe_benchmark.ledger import Ledger
    from vipe_benchmark.depth_recovery_lineage import accepted_setup_lineage
    from vipe_benchmark.depth_authorization import execution_authorization
    candidate = config['candidate']
    ledger_path = Path(config['ledger']).absolute()
    require('prompts' not in ledger_path.parts and 'prompts' not in ledger_path.resolve().parts, 'prompts ledger prohibited')
    ledger = Ledger(ledger_path, dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210))
    events = ledger.events()
    require(events and not any(row['event'] == 'reserve' for row in ledger.states(events).values()), 'active job or absent protected ledger')
    setup = read_json(config['bindings']['setup']['path'])
    require(candidate == 'D9', 'D10 ordinary setup requires separately reviewed wrapper extension')
    accepted = accepted_setup_lineage(config['bindings']['setup'], events, ledger.path.parent)
    require(setup.get('job_id') == 'plan069-D9-setup-recovery-002' and accepted['request'] == config['bindings']['setup_request'], 'accepted002 lineage required')
    _, authorization, _, _ = execution_authorization(candidate, authorization_path=config['bindings']['authorization']['path'])
    require(authorization == config['bindings']['authorization'] and setup['authorization'] == authorization, 'existing explicit DO mismatch')
    admission = read_json(config['bindings']['cpu_admission']['path'])
    require(admission.get('schema') == 'plan069-video-native-cpu-admission/v1' and admission.get('candidate') == candidate and admission.get('cpu_accounting_owner') == candidate and admission.get('seconds') == config['seconds'], 'fresh named CPU admission required')
    require(admission.get('ledger_head_sequence') == events[-1]['sequence'] and admission.get('ledger_head_sha256') == events[-1]['event_sha256'], 'CPU admission protected prefix changed')
    require(admission.get('candidate_cpu_remaining_seconds', 0) >= config['seconds'] and admission.get('global_cpu_remaining_seconds', 0) >= config['seconds'], 'cumulative CPU budget insufficient')
    require(admission.get('source_review') == config['bindings']['source_review'] and admission.get('setup') == config['bindings']['setup'], 'admission scope mismatch')
    cpu = read_json(config['bindings']['cpu_qualification']['path'])
    require(cpu.get('schema') == 'plan069-delta-cpu-test-capture/v1' and cpu.get('passed') is True and all(row.get('cleanup', {}).get('confirmed_no_surviving_observed_processes') is True for row in cpu.get('commands', [])) and bool(cpu.get('commands')) and cpu.get('source_bytes_unchanged') is True, 'actual clean focused CPU qualification required')
    sources = {row['path']: row for row in cpu['sources_after']}
    wrapper_files = [record(Path(__file__).resolve().parent / name) for name in ('wrapper.py', 'prepare_admission.py', 'prepare_request.py')]
    for row in wrapper_files:
        require(row in review.get('supplemental_sources', []), 'all three wrapper files must be reviewed supplementals')
    for row in review['local_sources'] + review.get('supplemental_sources', []) + wrapper_files + [config['method']]:
        require(sources.get(row['path']) == row, 'missing or stale qualified source')
    command = config['command']
    require(len(command) == 23 and set(command[5::2]) == {'--root', '--candidate', '--setup', '--setup-request', '--authorization', '--ledger', '--output', '--seconds', '--artifact-bytes'}, 'unexpected capture command flags')
    require(command[command.index('--ledger') + 1] == str(ledger.path), 'wrong protected ledger command')
    require(int(command[command.index('--artifact-bytes') + 1]) == 64 * 1024 * 1024, '64MiB artifact allowance required')
    require(config['cpu_workers'] == 7, 'unchanged method003 CPU thread allocation')
    require(record(__file__) in review.get('supplemental_sources', []), 'wrapper must be reviewed supplemental source')


def run(config_path):
    started = time.monotonic()
    def initial_deadline(signum, frame):
        raise TimeoutError('whole wrapper preflight deadline')
    signal.signal(signal.SIGALRM, initial_deadline)
    signal.setitimer(signal.ITIMER_REAL, 160)
    config_record = record(config_path)
    config = read_json(config_path)
    require(config['schema'] == 'plan069-video-parent-cpu-request/v1', 'wrong request schema')
    require(config['candidate'] == 'D9', 'accepted recovery wrapper requires D9')
    require(record(Path(sys.executable).resolve()) == config['bootstrap'], 'exact bootstrap interpreter changed')
    require(Path(config['interpreter_invocation']).absolute() == Path(sys.executable).absolute(), 'explicit interpreter invocation changed')
    for variable in ('LD_PRELOAD', 'LD_AUDIT'):
        require(variable not in os.environ, 'unreviewed loader injection: ' + variable)
    require(config['seconds'] == 180 and config['cleanup_seconds'] == 20, 'invalid time bound')
    require(config['cpu_workers'] == 7, 'retained producer requires seven threads')
    require(config['admitted'] is True and config['charge_owner'] == 'root' and config['cpu_accounting_owner'] == 'D9', 'root admission required')
    require(set(config['bindings']) == {'setup', 'setup_request', 'runtime_recipe', 'source_review', 'cpu_qualification', 'cpu_admission', 'authorization'}, 'missing or unexpected binding role')
    for item in config['bindings'].values():
        require(record(item['path']) == item, 'immutable input changed: ' + item['path'])
    require(config['bindings']['setup']['sha256'] == config['accepted_setup_sha256'], 'different historical setup')
    review = read_json(config['bindings']['source_review']['path'])
    require(review.get('candidate') == config['candidate'] and review.get('status') == 'passed' and
            review.get('schema') == 'plan069-depth-source-review/v1', 'wrong current source review')
    require(review['runtime_recipe'] == config['bindings']['runtime_recipe'], 'review recipe mismatch')
    for item in review['local_sources'] + review.get('supplemental_sources', []):
        require(record(item['path']) == item, 'current source changed')
    verify_admission(config, review)
    # All source, authority and prior CPU records are exact immutable bindings.
    # Never apply historical worker records to current mutable source paths.
    command = config['command']
    require(command[0] == config['interpreter_invocation'] and command[1:4] == ['-I', '-B', config['method']['path']], 'exact method invocation required')
    require(record(config['method']['path']) == config['method'], 'method changed')
    require(command[4] == 'capture', 'capture mode required')
    for flag, role in (('--setup', 'setup'), ('--setup-request', 'setup_request'), ('--authorization', 'authorization')):
        require(command.count(flag) == 1 and command[command.index(flag) + 1] == config['bindings'][role]['path'], 'command binding mismatch: ' + flag)
    require(command.count('--root') == 1 and command[command.index('--root') + 1] == config['root'], 'root command mismatch')
    require(all(Path(i['path']).is_relative_to(Path(config['root'])) for i in review['local_sources']), 'source escaped reviewed root')
    require(command.count('--candidate') == 1 and command[command.index('--candidate') + 1] == config['candidate'], 'wrong command candidate')
    require(float(command[command.index('--seconds') + 1]) <= config['seconds'] - config['cleanup_seconds'], 'cleanup reserve missing')
    out = Path(config['output']).absolute()
    require('prompts' not in out.parts and 'prompts' not in out.resolve().parts, 'prompts output prohibited')
    require(not out.exists(), 'wrapper output already exists')
    capture_out = Path(command[command.index('--output') + 1]).absolute()
    require('prompts' not in capture_out.parts and 'prompts' not in capture_out.resolve().parts, 'prompts capture prohibited')
    require(out == out.resolve() and capture_out == capture_out.resolve() and not capture_out.exists(), 'capture output is existing or escapes through symlink')
    roots = config['disk_roots']
    require({r['role'] for r in roots} >= {'global', 'candidate', 'runtime-cache'}, 'all disk scopes required')
    for r in roots:
        p = Path(r['path']).absolute()
        require('prompts' not in p.parts and 'prompts' not in p.resolve().parts, 'prompts disk scope prohibited')
        require(p == p.resolve() and p.exists(), 'invalid disk scope')
        require(r['maximum_total_bytes'] > 0 and r['maximum_delta_bytes'] >= 65536, 'invalid disk cap')
    require(any(capture_out.is_relative_to(Path(r['path'])) and out.is_relative_to(Path(r['path'])) for r in roots if r['role'] == 'candidate'), 'outputs escape candidate scope')
    require(any(Path(r['path']).is_relative_to(Path(g['path'])) for r in roots if r['role'] == 'candidate' for g in roots if g['role'] == 'global'), 'candidate escapes global scope')
    libc = ctypes.CDLL(None, use_errno=True)
    require(libc.prctl(36, 1, 0, 0, 0) == 0, 'subreaper setup failed')
    baseline = {r['role']: disk_bytes(r['path']) for r in roots}
    require(all(baseline[r['role']] <= r['maximum_total_bytes'] for r in roots), 'initial disk cap exceeded')
    out.mkdir(parents=True)
    process, error, peak = None, None, dict(baseline)
    observed: dict[tuple[int, int], dict[str, Any]] = {}
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
    def cancellation(signum, frame):
        raise InterruptedError('wrapper externally terminated')
    previous_term = signal.signal(signal.SIGTERM, cancellation)
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
        captured = read_json(capture_out / 'capture.json')
        require(captured.get('schema') == 'plan069-video-cpu-capture/v1' and captured.get('candidate') == config['candidate'] and
                captured.get('status') == 'passed' and captured.get('cleanup_confirmed') is True and
                captured.get('native_cpu') == record(capture_out / 'native-cpu.json'), 'missing or failed exact capture result')
        native = read_json(capture_out / 'native-cpu.json')
        require(native.get('strict_cpu_loads') == 2 and native.get('inference') is False and native.get('cuda_initialized') is False, 'two strict CPU-only loads required')
        for item in config['bindings'].values():
            require(record(item['path']) == item, 'input changed during capture')
        for item in review['local_sources'] + review.get('supplemental_sources', []):
            require(record(item['path']) == item, 'current source changed during capture')
        verify_admission(config, review)
    except BaseException as exc:
        error = type(exc).__name__ + ': ' + str(exc)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        cleanup_deadline = min(started + config['seconds'], time.monotonic() + config['cleanup_seconds'])
        signal.setitimer(signal.ITIMER_REAL, max(.001, cleanup_deadline - time.monotonic()))
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
        signal.setitimer(signal.ITIMER_REAL, max(.001, started + config['seconds'] - time.monotonic()))
        elapsed = time.monotonic() - started
        write(out / 'result.json', dict(schema='plan069-video-parent-cpu-result/v1', candidate=config['candidate'], cpu_accounting_owner=config['candidate'],
            status='passed' if error is None and cleanup_confirmed and elapsed <= config['seconds'] else 'failed',
            error=error, elapsed_seconds=elapsed, timing_scope='wrapper entry through observed descendant cleanup and final disk census; terminal assembly/write remains guarded by the total deadline; root meters invocation through return',
            cleanup_confirmed=cleanup_confirmed, cleanup_scope='all observed PID/start_ticks identities; subreaper orphan adoption',
            descendants=[{k: v for k, v in i.items() if k != 'pidfd'} for i in observed.values()],
            baseline_bytes=baseline, peak_bytes=peak, network_policy='inherited seccomp socket syscall denial',
            download_bytes=0, inference=False, cuda_operations=False, cpu_charge_applied=False, ledger_modified=False,
            final_terminal_disk_census_required=True, result_assembly_charge_required=True))
        for info in observed.values():
            os.close(info['pidfd'])
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous_handler)
        signal.signal(signal.SIGTERM, previous_term)
    require(error is None and cleanup_confirmed and elapsed <= config['seconds'], error or 'cleanup/deadline failed')


if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'sandbox':
        network_sandbox(sys.argv[3:])
    else:
        parser = argparse.ArgumentParser()
        parser.add_argument('--request', required=True)
        run(parser.parse_args().request)
