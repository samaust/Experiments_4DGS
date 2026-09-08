"""Durable, conservative plan-004 attempt accounting (not a process watchdog).

Hold one ledger lock throughout a GPU attempt. An interrupted attempt with no
final accounting consumes its entire reservation, so retries cannot recover
unrecorded training time. The trainer must honor remaining_seconds(), reserve
checkpoint time, and have a supervisor enforcing its hard deadline.
"""
import fcntl
import json
import math
import os
from pathlib import Path
import tempfile
import time


METHODS = ('stg-lite', 'stg-full', 'freetimegs', 'moe-gs', 'atgs', 'freetimegs-plus-plus')
SCENES = ('selfcap-dance1', 'vru-basketball-dg')


def allocation(method, scene, stage):
    if method not in METHODS or scene not in SCENES:
        raise ValueError('unknown plan-004 method/scene')
    if method == 'moe-gs':
        if stage in ('expert-0', 'expert-1', 'expert-2', 'expert-3'):
            return 1500.
        if stage == 'router':
            return 1200.
        raise ValueError('MoE requires a specific expert or router stage')
    if stage != 'train':
        raise ValueError('non-MoE method requires train stage')
    return 7200.


def atomic_json(path, value):
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, prefix=path.name+'.',
                                     delete=False) as stream:
        temporary = Path(stream.name)
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write('\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


class TrainingBudget:
    def __init__(self, path, *, method, scene, stage='train', clock=time.monotonic):
        self.path = Path(path)
        self.key = [method, scene, stage]
        self.limit = allocation(method, scene, stage)
        self.clock = clock
        self.lock = None
        self.active = None

    def __enter__(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.lock = self.path.with_suffix(self.path.suffix+'.lock').open('a')
        try:
            fcntl.flock(self.lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            self.ledger = (json.loads(self.path.read_text()) if self.path.exists()
                           else dict(schema='plan-004-training-budget/v1', attempts=[]))
            if self.ledger.get('schema') != 'plan-004-training-budget/v1':
                raise ValueError('unsupported training ledger')
            for attempt in self.ledger['attempts']:
                expected = allocation(*attempt['key'])
                charge = attempt['charged_seconds']
                if not math.isfinite(charge) or not 0 <= charge <= expected:
                    raise ValueError('invalid recorded budget charge')
            self.available = self.limit-sum(a['charged_seconds'] for a in self.ledger['attempts']
                                             if a['key'] == self.key)
            self.available = min(self.available, 86400.-sum(
                a['charged_seconds'] for a in self.ledger['attempts']))
            if self.available <= 0:
                raise RuntimeError('training allocation exhausted (including unfinished reservations)')
            return self
        except BaseException:
            self.lock.close()
            self.lock = None
            raise

    def start(self, *, command, provenance, seconds=None):
        if self.lock is None or self.active is not None:
            raise RuntimeError('start requires a locked, unused attempt')
        if seconds is not None and (not math.isfinite(seconds) or not 0 < seconds <= self.available):
            raise ValueError('requested reservation exceeds remaining training allocation')
        self.reserved = self.available if seconds is None else seconds
        self.started = self.clock()
        self.deadline = self.started+self.reserved
        self.active = dict(key=self.key, command=command, provenance=provenance,
                           started_unix_seconds=time.time(), status='reserved',
                           reserved_seconds=self.reserved, charged_seconds=self.reserved)
        self.ledger['attempts'].append(self.active)
        atomic_json(self.path, self.ledger)

    def remaining_seconds(self):
        if self.active is None:
            raise RuntimeError('attempt has not started')
        return max(0., self.deadline-self.clock())

    def finish(self, status):
        if self.active is None or self.active['status'] != 'reserved':
            raise RuntimeError('no active reservation')
        if status not in ('completed', 'failed', 'deadline'):
            raise ValueError('invalid completion status')
        elapsed = max(0., self.clock()-self.started)
        self.active.update(status=status, wall_seconds=elapsed,
                           charged_seconds=min(elapsed, self.reserved),
                           overrun_seconds=max(0., elapsed-self.reserved))
        atomic_json(self.path, self.ledger)
        if elapsed > self.reserved:
            raise RuntimeError('training exceeded its allocation; overrun recorded')

    def __exit__(self, exc_type, exc_value, traceback):
        try:
            # Explicit finish is required for a successful attempt. Leaving
            # normally without it retains the full crash-safe reservation.
            if exc_type is not None and self.active is not None and self.active['status'] == 'reserved':
                self.finish('failed')
        finally:
            if self.lock is not None:
                self.lock.close()
                self.lock = None
