"""Plan 026 immutable inputs, split guards, and append-only study accounting."""
import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / '.local/basketball-dense-temporal'
DOCS = ROOT / 'docs/experiments/basketball-dense-temporal'
MANIFEST = ROOT / '.local/sync-pivot/basketball-zero/manifest.json'
CURVE = (5000, 10000, 20000, 30000, 50000)
KEYFRAMES = (0, 5, 10, 15, 25, 30, 35, 40, 45)
PILOT = (0, 25, 45)
CAMERAS = tuple(c for c in range(34) if c not in (0, 10, 20, 30))


def digest(path):
    path = Path(path)
    if 'prompts' in path.parts:
        raise ValueError('prohibited path')
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_new(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')


def training_key(camera, frame):
    if str(camera) != str(int(camera)) or int(camera) not in CAMERAS:
        raise ValueError('held-out or invalid initialization camera')
    if type(frame) is not int or not 0 <= frame < 50 or 20 <= frame <= 24:
        raise ValueError('held-out or invalid initialization frame')
    return str(camera), frame


def verify_files(files):
    for path, expected in files.items():
        if digest(path) != expected:
            raise ValueError(f'changed historical input: {path}')


def preflight():
    """Verify parents without opening evaluation scores or changing old evidence."""
    selection = ROOT / '.local/sync-pivot/evaluation-inputs.json'
    records = json.loads(selection.read_text())
    parents = []
    for run in records['runs']:
        checkpoint = ROOT / run['checkpoint']['path']
        if digest(checkpoint) != run['checkpoint']['sha256']:
            raise ValueError(f'parent checkpoint changed: {checkpoint}')
        provenance = checkpoint.parent / 'provenance.json'
        verify_files(json.loads(provenance.read_text())['files'])
        parents.append(dict(arm=run['method'], seed=run['seed'],
                            path=str(checkpoint), sha256=digest(checkpoint),
                            bytes=checkpoint.stat().st_size,
                            provenance_sha256=digest(provenance)))
    expected = {(m, s) for m in ('stg-full', 'freetimegs') for s in range(3)}
    if len(parents) != 6 or {(r['arm'], r['seed']) for r in parents} != expected:
        raise ValueError('historical parent coverage mismatch')
    manifest = json.loads(MANIFEST.read_text())
    keys = [training_key(c, f) for c, f in manifest['training_keys']]
    if len(keys) != 1350 or len(set(keys)) != 1350:
        raise ValueError('training split changed')
    history = [ROOT / 'docs/research/basketball-sync-pivot/gpu-budget.json',
               ROOT / '.local/sync-pivot/central-training-before.json']
    return dict(schema='basketball-dense-temporal-preflight/v1',
                plan_sha256=digest(ROOT / 'plans/plan_026.md'),
                manifest_sha256=digest(MANIFEST), parents=parents,
                historical_accounting={str(p): digest(p) for p in history},
                free_bytes=shutil.disk_usage(ROOT).free,
                storage_status='production estimate pending pilot point count',
                limits=dict(gpu_concurrency=1, time_seconds=None, gpu_hours=None),
                training_images=1350, evaluation_images=350,
                baseline_scores_reused=False)


@contextmanager
def ledger_lock():
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    with (ARTIFACTS / 'gpu.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def append_event(value):
    value = dict(utc=datetime.now(timezone.utc).isoformat(), **value)
    with (ARTIFACTS / 'ledger.jsonl').open('a') as stream:
        stream.write(json.dumps(value, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


def supervise(command, stage, output):
    """One GPU process group, no total deadline, graceful then forced shutdown."""
    output = Path(output)
    with ledger_lock():
        output.mkdir(parents=True, exist_ok=False)
        started = time.monotonic()
        append_event(dict(event='start', stage=stage, output=str(output), command=command))
        interrupted = [False]
        handlers = {}
        def stop(*_):
            interrupted[0] = True
        for sig in (signal.SIGINT, signal.SIGTERM):
            handlers[sig] = signal.signal(sig, stop)
        process = None
        try:
            with (output / 'worker.log').open('w') as log:
                process = subprocess.Popen(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                stop_time = None
                while process.poll() is None:
                    if interrupted[0] and stop_time is None:
                        os.killpg(process.pid, signal.SIGTERM)
                        stop_time = time.monotonic()
                    if stop_time is not None and time.monotonic() - stop_time >= 60:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait()
                        break
                    time.sleep(.5)
            result = dict(event='finish', stage=stage, output=str(output),
                          exit_code=process.returncode, interrupted=interrupted[0],
                          charged_seconds=time.monotonic()-started)
            append_event(result)
            write_new(output / 'segment.json', result)
            return result
        finally:
            if process is not None:
                try:
                    os.killpg(process.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                process.wait()
            for sig, handler in handlers.items():
                signal.signal(sig, handler)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    check = sub.add_parser('preflight')
    check.add_argument('--output', type=Path, required=True)
    run = sub.add_parser('run')
    run.add_argument('--stage', choices=('initialization', 'training', 'evaluation', 'validation'), required=True)
    run.add_argument('--output', type=Path, required=True)
    run.add_argument('command', nargs=argparse.REMAINDER)
    a = parser.parse_args()
    if a.action == 'preflight':
        write_new(a.output, preflight())
    else:
        command = a.command[1:] if a.command[:1] == ['--'] else a.command
        if not command:
            parser.error('missing worker command')
        result = supervise(command, a.stage, a.output)
        raise SystemExit(result['exit_code'] or (130 if result['interrupted'] else 0))


if __name__ == '__main__':
    main()
