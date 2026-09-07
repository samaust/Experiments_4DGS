"""Separate eight GPU-hour ledger with sequential, supervised attempts."""
import argparse
import fcntl
import json
import math
from pathlib import Path
import time
from training_budget import atomic_json
from training_supervisor import supervise

LIMIT = 28800.


def run(ledger_path, command, *, seconds, log_path):
    ledger_path = Path(ledger_path)
    ledger_path.parent.mkdir(parents=True, exist_ok=True)
    if not math.isfinite(seconds) or seconds <= 32:
        raise ValueError('attempt must reserve more than 32 seconds')
    with ledger_path.with_suffix('.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        ledger = json.loads(ledger_path.read_text()) if ledger_path.exists() else {
            'schema': 'basketball-calibration-budget/v1', 'limit_seconds': LIMIT, 'attempts': []}
        if ledger.get('schema') != 'basketball-calibration-budget/v1' or ledger.get('limit_seconds') != LIMIT:
            raise ValueError('invalid calibration ledger')
        charges = [a['charged_seconds'] for a in ledger['attempts']]
        if any(not math.isfinite(c) or c < 0 or c > LIMIT for c in charges):
            raise ValueError('invalid charge')
        available = LIMIT - sum(charges)
        if seconds > available:
            raise ValueError(f'only {available} calibration seconds remain')
        attempt = {'command': command, 'started_unix_seconds': time.time(), 'status': 'reserved',
                   'reserved_seconds': seconds, 'charged_seconds': seconds}
        ledger['attempts'].append(attempt)
        atomic_json(ledger_path, ledger)
        started = time.monotonic()
        try:
            with Path(log_path).open('x') as log:
                outcome = supervise(command, cwd=Path.cwd(), log=log, seconds=seconds)
            attempt.update(outcome)
            attempt['status'] = ('deadline' if outcome['stop_requested'] or outcome['forced_kill']
                                 else 'completed' if outcome['exit_code'] == 0 else 'failed')
        except BaseException:
            # An uncertain process termination retains the entire reservation.
            raise
        else:
            attempt['charged_seconds'] = time.monotonic() - started
            atomic_json(ledger_path, ledger)
        return outcome['exit_code']


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--ledger', required=True, type=Path)
    p.add_argument('--seconds', required=True, type=float)
    p.add_argument('--log', required=True, type=Path)
    p.add_argument('command', nargs=argparse.REMAINDER)
    a = p.parse_args()
    command = a.command[1:] if a.command[:1] == ['--'] else a.command
    if not command:
        p.error('worker command required')
    return run(a.ledger, command, seconds=a.seconds, log_path=a.log)


if __name__ == '__main__':
    raise SystemExit(main())
