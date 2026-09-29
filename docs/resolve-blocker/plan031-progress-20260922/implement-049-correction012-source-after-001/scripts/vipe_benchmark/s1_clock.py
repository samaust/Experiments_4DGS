"""Reservation-derived S1 clocks; recorded validation never authorizes live work."""
from dataclasses import dataclass
import math
from pathlib import Path
import time

SCHEMA = 'plan041-s1-reservation-clock/v1'


def number(value, name, *, positive=False):
    try:
        valid = type(value) in (int, float) and math.isfinite(value) and value >= 0 and (not positive or value > 0)
    except OverflowError:
        valid = False
    if not valid:
        raise ValueError(f'invalid reservation clock {name}')
    return value


def boot_id():
    return Path('/proc/sys/kernel/random/boot_id').read_text().strip()


def typed_equal(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(typed_equal(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(typed_equal(a, b) for a, b in zip(left, right))
    return left == right


@dataclass(frozen=True)
class ReservationClock:
    job_id: str
    request_path: str
    request_sha256: str
    request_bytes: int
    sequence: int
    event_sha256: str
    boot_id: str
    monotonic_start: float
    effective_seconds: float
    cleanup_reserve_seconds: float
    total_deadline: float
    work_deadline: float

    @classmethod
    def from_reservation(cls, reservation):
        if not isinstance(reservation, dict) or reservation.get('event') != 'reserve':
            raise ValueError('reservation clock requires reserve event')
        value = dict(schema=SCHEMA, job_id=reservation.get('job_id'),
            request=reservation.get('evidence', {}).get('request'),
            reservation={k: reservation.get(k) for k in ('sequence', 'event_sha256')},
            boot_id=reservation.get('boot_id'), monotonic_start=reservation.get('monotonic_start'),
            effective_seconds=reservation.get('seconds'))
        start = number(value['monotonic_start'], 'monotonic_start')
        total = number(value['effective_seconds'], 'effective_seconds', positive=True)
        cleanup = min(30., total / 4)
        value.update(cleanup_reserve_seconds=cleanup, total_deadline=start + total,
                     work_deadline=start + total - cleanup)
        return cls.from_mapping(value)

    @classmethod
    def from_mapping(cls, value):
        from .s1_validation_contract import strict_record
        if not isinstance(value, dict) or set(value) != {'schema', 'job_id', 'request', 'reservation',
                'boot_id', 'monotonic_start', 'effective_seconds', 'cleanup_reserve_seconds',
                'total_deadline', 'work_deadline'} or value.get('schema') != SCHEMA:
            raise ValueError('invalid reservation clock mapping/schema')
        if value['job_id'] != 'S1-calibration-recovery-001' or type(value['job_id']) is not str:
            raise ValueError('invalid reservation clock job_id')
        record = strict_record(value['request'])
        ref = value['reservation']
        if (not isinstance(ref, dict) or set(ref) != {'sequence', 'event_sha256'}
                or type(ref['sequence']) is not int or ref['sequence'] < 0
                or type(ref['event_sha256']) is not str or len(ref['event_sha256']) != 64
                or any(c not in '0123456789abcdef' for c in ref['event_sha256'])):
            raise ValueError('invalid reservation clock reservation identity')
        if type(value['boot_id']) is not str or not value['boot_id'].strip():
            raise ValueError('invalid reservation clock boot_id')
        start = number(value['monotonic_start'], 'monotonic_start')
        total = number(value['effective_seconds'], 'effective_seconds', positive=True)
        cleanup = number(value['cleanup_reserve_seconds'], 'cleanup_reserve_seconds', positive=True)
        deadline = number(value['total_deadline'], 'total_deadline', positive=True)
        work = number(value['work_deadline'], 'work_deadline', positive=True)
        if (total > 3600 or cleanup != min(30., total / 4) or deadline != start + total
                or work != deadline - cleanup or not start < work < deadline):
            raise ValueError('invalid reservation clock derived window')
        return cls(value['job_id'], record['path'], record['sha256'], record['bytes'],
            ref['sequence'], ref['event_sha256'], value['boot_id'], start, total, cleanup, deadline, work)

    def mapping(self):
        return dict(schema=SCHEMA, job_id=self.job_id,
            request=dict(path=self.request_path, sha256=self.request_sha256, bytes=self.request_bytes),
            reservation=dict(sequence=self.sequence, event_sha256=self.event_sha256), boot_id=self.boot_id,
            monotonic_start=self.monotonic_start, effective_seconds=self.effective_seconds,
            cleanup_reserve_seconds=self.cleanup_reserve_seconds, total_deadline=self.total_deadline,
            work_deadline=self.work_deadline)

    def match(self, value):
        supplied = self.from_mapping(value)
        if not typed_equal(supplied.mapping(), self.mapping()):
            raise ValueError('reservation clock differs from authoritative reservation')
        return True

    def recorded(self, seconds, status):
        number(seconds, 'elapsed_seconds_from_reservation')
        if status == 'passed':
            if seconds >= self.work_deadline - self.monotonic_start:
                raise ValueError('reservation clock passed evidence at/after work deadline')
        elif status in ('failed', 'not_reached'):
            if seconds > self.effective_seconds:
                raise ValueError('reservation clock failure evidence after total deadline')
        else:
            raise ValueError('reservation clock unknown evidence status')
        return seconds

    def observe(self, *, work=True):
        observation = number(time.monotonic(), 'observation')
        if boot_id() != self.boot_id:
            raise ValueError('reservation clock live boot mismatch')
        if observation < self.monotonic_start:
            raise ValueError('reservation clock observation before start')
        if work and observation >= self.work_deadline:
            raise TimeoutError('reservation clock work deadline reached')
        if not work and observation > self.total_deadline:
            raise TimeoutError('reservation clock total deadline exceeded')
        return observation - self.monotonic_start


def require_clock(clock):
    if type(clock) is not ReservationClock:
        raise ValueError('trusted reservation clock required')
    # A frozen value still needs its strict invariants checked at every boundary.
    clock.match(clock.mapping())
    return clock


def diagnostic(clock, error):
    """Truthful JSON-safe clock evidence, even when qualification is impossible."""
    observation = time.monotonic()
    safe = lambda v: v if type(v) in (int, float) and math.isfinite(v) else repr(v)
    elapsed = observation - clock.monotonic_start if type(clock) is ReservationClock and type(observation) in (int, float) else None
    return dict(clock_status='unverified', clock_error=f'{type(error).__name__}: {error}',
        clock_observation=safe(observation), elapsed_seconds_from_reservation=safe(elapsed) if elapsed is not None else None,
        reservation_clock=clock.mapping() if type(clock) is ReservationClock else None)
