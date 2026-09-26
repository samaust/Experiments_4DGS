#!/usr/bin/env python3
"""Pi-launch driver (Plan061, provenance class pi-launch).

Launches the owned no-timeout capture when driven by pi's bash tool. It
mirrors launch-049-exec.py minus the Codex session protocol: no bootstrap
handoff, no ADMIT, no job ledger, no session proof. The prospective
identity note (plan061-pi-launch/v1) binds this driver's own process
identity — which survives os.execve into the capture (same pid/start_ticks)
— plus the live preexisting ancestry to pid 0. Everything the note binds is
re-verified live at every owned call by owned_workload; nothing here is
simulated or predicted.

Usage: python -B pi_launch_driver.py <diagnostic|aggregate> <index> <reason>
"""
import ast
import datetime
import hashlib
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path('/home/auss/git_repos/samaust/Experiments_4DGS')
sys.path.insert(0, str(ROOT / 'scripts'))
from vipe_benchmark.config import ROOT as CONTRACT_ROOT  # noqa: E402
from vipe_benchmark.files import file_record  # noqa: E402
from vipe_benchmark.s1_validation_contract import (  # noqa: E402
    ARGV, STDIN, THREADS, source_paths, pi_launch, pi_launch_output_paths)

RUN = CONTRACT_ROOT / 'docs/continuous-improvement/plan031-s1-recovery-20260919/pi-launch'
INTERPRETER = CONTRACT_ROOT / '.local/envs/stg-colmap/bin/python'


def stamp():
    return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), monotonic=__import__('time').monotonic())


def publish(path, value):
    raw = (json.dumps(value, indent=2, allow_nan=False) + '\n').encode()
    path.write_bytes(raw)
    with path.open('rb') as handle:
        os.fsync(handle.fileno())
    return file_record(path)


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def process_row(pid):
    fields = Path('/proc', str(pid), 'stat').read_text().rsplit(')', 1)[1].split()
    return dict(boot_id=boot_id(), pid=pid, ppid=int(fields[1]), pgid=int(fields[2]), start_ticks=int(fields[19]))


def thread_start_ticks(pid, tid):
    fields = Path('/proc', str(pid), 'task', str(tid), 'stat').read_text().rsplit(')', 1)[1].split()
    return int(fields[19])


def full_identity(pid):
    """Complete stable identity in the exact _identity_record field set."""
    first = process_row(pid)

    def tasks():
        tids = sorted(int(path.name) for path in Path('/proc', str(pid), 'task').iterdir())
        return [dict(boot_id=first['boot_id'], pid=pid, process_start_ticks=first['start_ticks'],
                     tid=tid, start_ticks=thread_start_ticks(pid, tid)) for tid in tids]
    before = tasks()
    after = tasks()
    last = process_row(pid)
    if first != last:
        raise ValueError('driver identity changed during sampling')
    return dict(first, threads=before, threads_before=before, threads_after=after,
                process_before=first, process_after=last)


def attempt_high_water(kind):
    values = []
    patterns = (re.compile(r'^launch-note-061-%s-(\d+)\.json$' % kind),
                re.compile(r'^driver-061-%s-(\d+)-(?:exec-start\.json|stdout\.log|stderr\.log)$' % kind),
                re.compile(r'^%s-061-(\d{3,})$' % kind))
    if RUN.exists():
        for entry in RUN.iterdir():
            for pattern in patterns:
                matched = pattern.fullmatch(entry.name)
                if matched:
                    values.append(int(matched.group(1)))
    return max(values) if values else 0


def main():
    kind, index, reason = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    if kind not in ('diagnostic', 'aggregate') or index < 1 or not reason.strip():
        raise ValueError('launch kind/index/reason')
    if CONTRACT_ROOT.resolve() != ROOT.resolve() or os.geteuid() != os.getuid():
        raise ValueError('repository root or privilege mismatch')
    if index != attempt_high_water(kind) + 1:
        raise ValueError('candidate must be the next vacant high-water index')
    suffix = '%s-%s' % (kind, str(index).zfill(3))
    directory = RUN / (kind + '-061-' + str(index).zfill(3))
    if directory.exists() or directory.is_symlink():
        raise ValueError('output path occupied')
    for name in ('launch-note-061-' + suffix + '.json',
                 'driver-061-' + suffix + '-exec-start.json',
                 'driver-061-' + suffix + '-stdout.log',
                 'driver-061-' + suffix + '-stderr.log'):
        if (RUN / name).exists() or (RUN / name).is_symlink():
            raise ValueError('attempt evidence output path occupied: ' + name)
    sources = [file_record(path) for path in source_paths()]
    if len(sources) != 78:
        raise ValueError('source membership count: %d' % len(sources))
    for path in source_paths():
        if path.suffix == '.py':
            ast.parse(path.read_bytes())
    command = [str(INTERPRETER), '-B', '-m', 'vipe_benchmark.s1_validation_capture', str(directory), '--no-timeout']
    if kind == 'diagnostic':
        command.append('--diagnostic')
    settings = {key: '1' for key in (*THREADS, 'OPENCV_FOR_THREADS_NUM', 'VIPE_CPU_VALIDATION')}
    settings['PYTHONPATH'] = str(ROOT / 'scripts')
    env = dict(os.environ, **settings)
    for key in ('S1_HELPER_DIAGNOSTIC', 'S1_RECEIPT_DIAGNOSTIC', 'S1_JOB_LEDGER'):
        env.pop(key, None)
    env['S1_OWNED_ROOT_NOTE'] = str(RUN / ('launch-note-061-' + suffix + '.json'))
    env['S1_OWNED_ROOT_SHA256'] = '0' * 64
    if len([path.name for path in Path('/proc/self/task').iterdir()]) != 1:
        raise ValueError('pi-launch driver must be single-threaded')
    root = full_identity(os.getpid())
    ancestors, cursor = [], root['ppid']
    while cursor != 0:
        row = full_identity(cursor)
        if row['start_ticks'] > root['start_ticks']:
            raise ValueError('pi-launch ancestor newer than root')
        ancestors.append(row)
        cursor = row['ppid']
    note = dict(
        schema='plan061-pi-launch/v1', execution_mode='no-timeout', timeout_seconds=None, provenance='pi-launch',
        driver=file_record(Path(__file__).resolve()), authorization=file_record(RUN / 'pi-launch-authorization.md'),
        plan=file_record(CONTRACT_ROOT / 'plans/plan_061.md'),
        bindings=[], sources=sources, kind=kind, attempt_index=index, reason=reason,
        command=command, cwd=str(ROOT), run_directory=str(directory), environment=settings,
        unset_environment=['S1_HELPER_DIAGNOSTIC', 'S1_RECEIPT_DIAGNOSTIC'],
        stdin_identity=dict(bytes=len(STDIN.encode()), sha256=hashlib.sha256(STDIN.encode()).hexdigest(), content=STDIN),
        ownership_root=root, preexisting_ancestors=ancestors,
        ancestry_terminal=dict(pid=ancestors[-1]['pid'], ppid=0), retained_wrappers=[],
        output_paths=pi_launch_output_paths(directory, kind, index), job_ledger=None,
        observed=stamp(), cpu_bound='B+max(1,H)\u22648')
    note['bindings'] = [note['driver'], note['authorization'], note['plan']]
    note_record = publish(RUN / ('launch-note-061-' + suffix + '.json'), note)
    env['S1_OWNED_ROOT_SHA256'] = note_record['sha256']
    pi_launch(note_record, str(directory), diagnostic=kind == 'diagnostic')
    print(json.dumps(dict(launch_note=note_record['path'], kind=kind, index=index,
                          ownership_root_pid=root['pid'], ancestors=len(ancestors),
                          reason=reason, command=command)), flush=True)
    prefix = RUN / ('driver-061-' + suffix)
    with (prefix.with_name(prefix.name + '-stdout.log')).open('xb') as out, \
            (prefix.with_name(prefix.name + '-stderr.log')).open('xb') as err:
        logs = {}
        for number, stream in ((1, out), (2, err)):
            stream.flush()
            os.fsync(stream.fileno())
            info = os.fstat(stream.fileno())
            logs[str(number)] = dict(device=info.st_dev, inode=info.st_ino)
        for record in note['bindings'] + sources + [note_record]:
            if file_record(Path(record['path'])) != record:
                raise ValueError('authority/source changed before exec')
        if full_identity(os.getpid()) != root:
            raise ValueError('driver identity changed immediately before exec')
        publish(prefix.with_name(prefix.name + '-exec-start.json'),
                dict(schema='plan061-exec-launch/v1', execution_mode='no-timeout', timeout_seconds=None,
                     note=note_record, before_launch=stamp(), logs=logs, command=command,
                     provenance='pi-launch'))
        os.dup2(out.fileno(), 1)
        os.dup2(err.fileno(), 2)
    os.execve(command[0], command, env)


if __name__ == '__main__':
    main()
