"""Locked, append-only, hash-chained attempt and resource ledger."""
from contextlib import contextmanager
import fcntl
import json
import math
import os
from pathlib import Path
import time

from .config import jobs
from .files import canonical, object_hash, safe_path


class Ledger:
    def __init__(self, path, config):
        self.path = safe_path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.jobs = jobs(config)

    @contextmanager
    def locked(self):
        with self.path.open('a+') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.seek(0)
            events = []
            previous = None
            for line in stream:
                row = json.loads(line)
                stored = row.pop('event_sha256')
                if row['sequence'] != len(events) or row['previous_sha256'] != previous or object_hash(row) != stored:
                    raise ValueError('ledger corruption; cannot reset consumed attempts')
                row['event_sha256'] = stored
                events.append(row)
                previous = stored
            try:
                yield stream, events
            finally:
                fcntl.flock(stream, fcntl.LOCK_UN)

    def _append(self, stream, events, event):
        event = dict(event, sequence=len(events), previous_sha256=events[-1]['event_sha256'] if events else None,
                     recorded_unix=time.time())
        event['event_sha256'] = object_hash(event)
        stream.seek(0, os.SEEK_END)
        stream.write(canonical(event) + '\n')
        stream.flush()
        os.fsync(stream.fileno())
        events.append(event)
        return event

    def events(self):
        with self.locked() as (_, events):
            return events

    def states(self, events=None):
        states = {}
        for row in self.events() if events is None else events:
            if row['event'] in ('reserve', 'finish', 'account', 'checkpoint'):
                states[row['job_id']] = row
            elif row['event'] == 'checkpoint_resume':
                states[row['job_id']] = dict(row, event='reserve')
            elif row['event'] == 'resume_unstarted':
                for job_id in row['job_ids']:
                    states.pop(job_id, None)
        return states

    def totals(self, events=None):
        events = self.events() if events is None else events
        totals = {k: dict(attempts=0, elapsed_seconds=0., reserved_seconds=0.)
                  for k in ('gpu', 'cpu', 'setup', 'motion', 'neighbor')}
        for row in events:
            if row['event'] == 'reserve':
                totals[row['resource']]['attempts'] += 1
            elif row['event'] in ('finish', 'checkpoint'):
                totals[row['resource']]['elapsed_seconds'] += row['elapsed_seconds']
            elif row['event'] == 'cpu_preparation_charge':
                totals['cpu']['elapsed_seconds'] += row['elapsed_seconds']
        for row in self.states(events).values():
            if row['event'] == 'reserve':
                totals[row['resource']]['reserved_seconds'] += row['seconds']
        return totals

    def reserve(self, job_id, command, evidence, *, seconds_limit=None):
        with self.locked() as (stream, events):
            if job_id not in self.jobs:
                raise ValueError('unallocated job identity')
            states = self.states(events)
            if job_id in states:
                raise ValueError('job already consumed or accounted for; no automatic retry')
            if any(r['event'] == 'reserve' for r in states.values()):
                raise ValueError('unreconciled active attempt; refusing concurrent dispatch')
            spec = self.jobs[job_id]
            resource = spec['resource']
            total = self.totals(events)[resource]['elapsed_seconds']
            caps = dict(gpu=self.config['gpu_total_seconds_limit'],
                        cpu=self.config['cpu_prepare_score_report_seconds_limit'],
                        setup=self.config['setup_wall_seconds_limit'],
                        motion=self.config['cpu_motion_jobs']['attempts'] * self.config['cpu_motion_jobs']['seconds_each'],
                        neighbor=self.config['cpu_neighbor_jobs']['attempts'] * self.config['cpu_neighbor_jobs']['seconds_each'])
            seconds = min(spec['seconds'], caps[resource] - total)
            if seconds_limit is not None:
                if not math.isfinite(seconds_limit) or seconds_limit <= 0:
                    raise ValueError('invalid narrower job deadline')
                seconds = min(seconds, seconds_limit)
            if seconds <= 0:
                raise ValueError('resource wall allocation exhausted')
            return self._append(stream, events, dict(event='reserve', job_id=job_id, resource=resource,
                seconds=seconds, command=command, evidence=evidence, monotonic_start=time.monotonic(),
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()))

    def charge_cpu_preparation(self, elapsed_seconds, evidence):
        """Charge separately retriable input acquisition without a model attempt."""
        from .files import verify_record
        verify_record(evidence)
        if not math.isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise ValueError('invalid preparation time charge')
        with self.locked() as (stream, events):
            if any(e['event'] == 'cpu_preparation_charge' and e['evidence'] == evidence for e in events):
                raise ValueError('preparation evidence already charged')
            total = self.totals(events)['cpu']['elapsed_seconds'] + elapsed_seconds
            if total > self.config['cpu_prepare_score_report_seconds_limit']:
                raise ValueError('CPU preparation allocation exhausted')
            return self._append(stream, events, dict(event='cpu_preparation_charge',
                                resource='cpu', elapsed_seconds=elapsed_seconds, evidence=evidence))

    def checkpoint(self, job_id, elapsed_seconds, **fields):
        """Pause only the single aggregation transaction between frozen stages."""
        if job_id != 'aggregate' or not math.isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise ValueError('only aggregation may checkpoint a bounded stage')
        with self.locked() as (stream, events):
            state = self.states(events).get(job_id)
            if not state or state['event'] != 'reserve' or elapsed_seconds > state['seconds']:
                raise ValueError('aggregation checkpoint has no valid active reservation')
            return self._append(stream, events, dict(event='checkpoint', job_id=job_id,
                status='checkpointed', resource='cpu', elapsed_seconds=elapsed_seconds, **fields))

    def resume_checkpoint(self, job_id, command, evidence, *, seconds_limit=None):
        if job_id != 'aggregate':
            raise ValueError('only the aggregation transaction has resumable checkpoints')
        with self.locked() as (stream, events):
            states = self.states(events)
            if states.get(job_id, {}).get('event') != 'checkpoint':
                raise ValueError('no frozen aggregate checkpoint to resume')
            if any(s['event'] == 'reserve' for s in states.values()):
                raise ValueError('unreconciled active attempt; refusing concurrent dispatch')
            seconds = self.config['cpu_prepare_score_report_seconds_limit'] - self.totals(events)['cpu']['elapsed_seconds']
            if seconds_limit is not None:
                if not math.isfinite(seconds_limit) or seconds_limit <= 0:
                    raise ValueError('invalid narrower job deadline')
                seconds = min(seconds, seconds_limit)
            if seconds <= 0:
                raise ValueError('CPU allocation exhausted')
            return self._append(stream, events, dict(event='checkpoint_resume', job_id=job_id,
                resource='cpu', seconds=seconds, command=command, evidence=evidence,
                previous_result=states[job_id].get('result'), monotonic_start=time.monotonic(),
                boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip()))

    def note(self, event, **fields):
        if event in ('reserve', 'finish', 'account', 'resume_unstarted', 'checkpoint',
                     'checkpoint_resume', 'cpu_preparation_charge'):
            raise ValueError('use the checked ledger transition')
        with self.locked() as (stream, events):
            return self._append(stream, events, dict(event=event, **fields))

    def finish(self, job_id, status, elapsed_seconds, **fields):
        if status not in ('complete', 'failed') or not math.isfinite(elapsed_seconds) or elapsed_seconds < 0:
            raise ValueError('invalid attempt completion')
        with self.locked() as (stream, events):
            state = self.states(events).get(job_id)
            if not state or state['event'] != 'reserve':
                raise ValueError('attempt not reserved or already finished')
            return self._append(stream, events, dict(event='finish', job_id=job_id, status=status,
                resource=state['resource'], elapsed_seconds=elapsed_seconds,
                deadline_exceeded=elapsed_seconds > state['seconds'], **fields))

    def account(self, job_id, status, reason):
        if status not in ('blocked', 'skipped') or not reason:
            raise ValueError('unstarted jobs require explicit blocked/skipped reasons')
        with self.locked() as (stream, events):
            if job_id not in self.jobs or job_id in self.states(events):
                raise ValueError('unknown or already accounted job')
            return self._append(stream, events, dict(event='account', job_id=job_id, status=status, reason=reason))

    def resume_unstarted(self, job_ids, authorization):
        """Explicit resume may reopen blocked slots, never consumed attempts."""
        if not authorization or not job_ids or len(set(job_ids)) != len(job_ids):
            raise ValueError('explicit resume authorization and unique job IDs required')
        with self.locked() as (stream, events):
            states = self.states(events)
            consumed = {r['job_id'] for r in events if r['event'] == 'reserve'}
            if any(job_id in consumed or states.get(job_id, {}).get('event') != 'account' for job_id in job_ids):
                raise ValueError('resume can reopen only unstarted accounted slots, not consumed attempts')
            return self._append(stream, events, dict(event='resume_unstarted', job_ids=job_ids,
                                                     authorization=authorization))
