"""Locked, append-only, hash-chained attempt and resource ledger."""
from contextlib import contextmanager
import fcntl
import json
import math
import os
import re
from pathlib import Path
import time

from .config import jobs
from .files import canonical, object_hash, read_json, safe_path, verify_record


class Ledger:
    def __init__(self, path, config):
        self.path = safe_path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.config = config

    def _jobs(self, events):
        allocated = jobs(self.config)
        for event in events:
            if event['event'] == 'memory_diagnostic_authorized':
                verify_record(event['authorization'])
                allocated[event['job_id']] = dict(allocated['S3-reconstruction'],
                    id=event['job_id'], seconds=600, scope='explicit user-authorized 48-pair S3 memory diagnostic')
            if event['event'] == 'reconstruction_recovery_authorized':
                verify_record(event['authorization'])
                allocated[event['job_id']] = dict(allocated['S3-reconstruction'],
                    id=event['job_id'], seconds=5400, scope='explicit user-authorized S3 reconstruction recovery')
            if event['event'] == 'component_recovery_authorized':
                verify_record(event['authorization'])
                allocated[event['job_id']] = dict(allocated[event['original_job_id']],
                    id=event['job_id'], scope='explicit user-authorized component recovery')
            if event['event'] == 'setup_recovery_authorized':
                verify_record(event['authorization'])
                allocated[event['job_id']] = dict(allocated[event['original_job_id']],
                    id=event['job_id'], scope='explicit user-authorized setup recovery')
        return allocated

    @property
    def jobs(self):
        return self._jobs(self.events())

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
            elif row['event'] == 'setup_recovery_authorized':
                # Asset-only recovery was already conservatively charged to
                # preparation. It also belongs to cumulative setup wall time.
                totals['setup']['elapsed_seconds'] += row['preparation_elapsed_seconds']
        for row in self.states(events).values():
            if row['event'] == 'reserve':
                totals[row['resource']]['reserved_seconds'] += row['seconds']
        return totals

    def reserve(self, job_id, command, evidence, *, seconds_limit=None):
        with self.locked() as (stream, events):
            allocated = self._jobs(events)
            if job_id not in allocated:
                raise ValueError('unallocated job identity')
            states = self.states(events)
            if job_id in states:
                raise ValueError('job already consumed or accounted for; no automatic retry')
            if any(r['event'] == 'reserve' for r in states.values()):
                raise ValueError('unreconciled active attempt; refusing concurrent dispatch')
            spec = allocated[job_id]
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
                     'checkpoint_resume', 'cpu_preparation_charge', 'setup_recovery_authorized', 'component_recovery_authorized',
                     'reconstruction_recovery_authorized', 'memory_diagnostic_authorized'):
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
            if job_id not in self._jobs(events) or job_id in self.states(events):
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

    def authorize_component_recovery(self, authorization):
        """One approved fixed-configuration retry, retaining original failures."""
        document = read_json(verify_record(authorization)['path'])
        original_id = document.get('original_job_id', '')
        if not re.fullmatch(r'S[0-4]-(calibration|reconstruction)', original_id):
            raise ValueError('component recovery requires an original segmentation matrix arm')
        spec = jobs(self.config)[original_id]
        required = dict(schema='vipe-benchmark-component-recovery/v1', attempts_limit=1,
            seconds_limit=spec['seconds'], reset_previous_consumption=False,
            gpu_total_seconds_limit=self.config['gpu_total_seconds_limit'],
            changes_to_prescribed_configuration=False, unrelated_attempts_reopened=False)
        if any(document.get(k) != v for k, v in required.items()) or not document.get('authorization'):
            raise ValueError('exact explicit component recovery authorization required')
        validation = read_json(verify_record(document['repair_validation'])['path'])
        if validation.get('status') != 'passed' or not validation.get('sources'):
            raise ValueError('passing source-bound repair validation required')
        for source in validation['sources']:
            verify_record(source)
        with self.locked() as (stream, events):
            prior = [e for e in events if e['event'] == 'component_recovery_authorized'
                     and e['original_job_id'] == original_id]
            if any(e['job_id'] == document.get('job_id') for e in prior):
                raise ValueError('component recovery already allocated')
            if document.get('job_id') != f'{original_id}-recovery-{len(prior)+1:03d}':
                raise ValueError('component recovery must use next sequential identity')
            states = self.states(events)
            original = states.get(original_id, {})
            if (original.get('event') != 'finish' or original.get('status') != 'failed' or
                    original.get('cleanup_confirmed') is not True or
                    original.get('event_sha256') != document.get('original_failure_event_sha256')):
                raise ValueError('recovery must bind original cleaned-up component failure')
            if prior:
                previous = states.get(prior[-1]['job_id'], {})
                if (previous.get('event') != 'finish' or previous.get('status') != 'failed' or
                        previous.get('cleanup_confirmed') is not True or
                        previous.get('event_sha256') != document.get('previous_recovery_failure_event_sha256')):
                    raise ValueError('recovery must bind previous cleaned-up component failure')
            if any(s['event'] == 'reserve' for s in states.values()):
                raise ValueError('unreconciled active attempt')
            if self.totals(events)['gpu']['elapsed_seconds'] >= self.config['gpu_total_seconds_limit']:
                raise ValueError('cumulative GPU allocation exhausted')
            return self._append(stream, events, dict(event='component_recovery_authorized',
                job_id=document['job_id'], original_job_id=original_id, authorization=authorization,
                original_failure_event_sha256=original['event_sha256']))

    def authorize_reconstruction_recovery(self, authorization):
        document = read_json(verify_record(authorization)['path'])
        required = dict(schema='vipe-benchmark-s3-reconstruction-recovery/v1',
            original_job_id='S3-reconstruction',
            attempts_limit=1, seconds_limit=5400, reset_previous_consumption=False,
            gpu_total_seconds_limit=self.config['gpu_total_seconds_limit'], unrelated_attempts_reopened=False)
        if any(document.get(k) != v for k, v in required.items()) or not document.get('authorization'):
            raise ValueError('exact explicit S3 reconstruction recovery authorization required')
        if not re.fullmatch(r'S3-reconstruction-recovery-[0-9]{3}', document.get('job_id', '')):
            raise ValueError('reconstruction recovery requires a numbered fresh identity')
        validation = read_json(verify_record(document['repair_validation'])['path'])
        if validation.get('status') != 'passed' or not validation.get('sources'):
            raise ValueError('passing bound native-helper repair validation required')
        for source in validation['sources']:
            verify_record(source)
        if document.get('memory_diagnostic_review'):
            from .sam3_memory import validate_diagnostic_review
            review = validate_diagnostic_review(document['memory_diagnostic_review'])
            state = self.states().get('S3-memory-diagnostic-001', {})
            if state.get('status') != 'complete' or state.get('result') != review['diagnostic_result'] or not state.get('cleanup_confirmed'):
                raise ValueError('diagnostic review must bind a completed supervised diagnostic')
        with self.locked() as (stream, events):
            prior = [e for e in events if e['event'] == 'reconstruction_recovery_authorized']
            if any(e['job_id'] == document['job_id'] for e in prior):
                raise ValueError('S3 reconstruction recovery already allocated')
            if document['job_id'] != f'S3-reconstruction-recovery-{len(prior)+1:03d}':
                raise ValueError('reconstruction recovery must use the next sequential identity')
            states = self.states(events)
            if prior:
                previous = states.get(prior[-1]['job_id'], {})
                if (previous.get('event') != 'finish' or previous.get('status') != 'failed' or
                        previous.get('cleanup_confirmed') is not True or previous.get('event_sha256') !=
                        document.get('previous_recovery_failure_event_sha256')):
                    raise ValueError('recovery must bind the previous cleaned-up recovery failure')
            if (document['job_id'] == 'S3-reconstruction-recovery-003' and
                    any(e['event'] == 'memory_diagnostic_authorized' for e in events) and
                    not document.get('memory_diagnostic_review')):
                raise ValueError('approved full memory-repair run is conditional on diagnostic validation')
            original = states.get('S3-reconstruction', {})
            if (original.get('event') != 'finish' or original.get('status') != 'failed' or
                    original.get('cleanup_confirmed') is not True or
                    original.get('event_sha256') != document.get('original_failure_event_sha256')):
                raise ValueError('recovery must bind original cleaned-up reconstruction failure')
            if any(s['event'] == 'reserve' for s in states.values()):
                raise ValueError('unreconciled active attempt')
            if self.totals(events)['gpu']['elapsed_seconds'] >= self.config['gpu_total_seconds_limit']:
                raise ValueError('cumulative GPU allocation exhausted')
            return self._append(stream, events, dict(event='reconstruction_recovery_authorized',
                job_id=document['job_id'], original_job_id='S3-reconstruction', authorization=authorization,
                original_failure_event_sha256=original['event_sha256']))

    def authorize_memory_diagnostic(self, authorization):
        document = read_json(verify_record(authorization)['path'])
        required = dict(schema='vipe-benchmark-s3-memory-diagnostic/v1', job_id='S3-memory-diagnostic-001',
            attempts_limit=1, seconds_limit=600, pairs_limit=48, gpu_total_seconds_limit=self.config['gpu_total_seconds_limit'],
            reset_previous_consumption=False, unrelated_attempts_reopened=False)
        if any(document.get(k) != v for k, v in required.items()) or not document.get('authorization'):
            raise ValueError('exact explicit 48-pair memory diagnostic authorization required')
        validation = read_json(verify_record(document['repair_validation'])['path'])
        if validation.get('status') != 'passed' or not validation.get('sources'):
            raise ValueError('passing bound implementation validation required')
        for source in validation['sources']:
            verify_record(source)
        with self.locked() as (stream, events):
            if any(e['event'] == 'memory_diagnostic_authorized' for e in events):
                raise ValueError('memory diagnostic already allocated')
            states = self.states(events)
            previous = states.get('S3-reconstruction-recovery-002', {})
            if (previous.get('status') != 'failed' or previous.get('cleanup_confirmed') is not True or
                    previous.get('event_sha256') != document.get('previous_failure_event_sha256')):
                raise ValueError('memory diagnostic must bind the preserved cleaned-up memory failure')
            if any(s['event'] == 'reserve' for s in states.values()):
                raise ValueError('unreconciled active attempt')
            return self._append(stream, events, dict(event='memory_diagnostic_authorized', job_id=document['job_id'],
                authorization=authorization, previous_failure_event_sha256=previous['event_sha256']))

    def authorize_setup_recovery(self, authorization):
        """Register the user's one SAM3 access recovery without reopening E3.

        This deliberately does not grant a general retry pool or reinterpret
        unused time as attempts. The original failed state and all charges stay
        intact, and the new process shares the original cumulative setup cap.
        """
        document = read_json(verify_record(authorization)['path'])
        if document.get('schema') == 'vipe-benchmark-e1-recovery/v1':
            return self._authorize_e1_recovery(authorization, document)
        if document.get('schema') == 'vipe-benchmark-setup-recovery/v1':
            if document.get('environment') not in ('E2', 'E4'):
                raise ValueError('generic recovery is limited to approved E2/E4 environments')
            return self._authorize_e1_recovery(authorization, document, document['environment'])
        required = dict(schema='vipe-benchmark-sam3-recovery/v1',
            job_id='E3-setup-recovery-001', original_job_id='E3-setup', environment='E3',
            recovery_attempts_limit=1, setup_wall_seconds_limit=self.config['setup_wall_seconds_limit'],
            reset_previous_consumption=False, changes_to_prescribed_runtime=False,
            sam3_access_resolved=True, unrelated_attempts_reopened=False)
        if any(document.get(key) != value for key, value in required.items()) or not document.get('authorization'):
            raise ValueError('recovery requires the exact explicit SAM3 authorization scope')
        acquisition = read_json(verify_record(document['asset_preparation'])['path'])
        if (acquisition.get('status') != 'complete' or acquisition.get('environment_builds') != 0 or
                acquisition.get('model_forwards') != 0):
            raise ValueError('SAM3 recovery requires completed asset-only preparation')
        verify_record(acquisition['assets'])
        preparation_seconds = acquisition.get('elapsed_seconds')
        if not isinstance(preparation_seconds, (int, float)) or not math.isfinite(preparation_seconds) or preparation_seconds < 0:
            raise ValueError('invalid SAM3 acquisition elapsed time')
        with self.locked() as (stream, events):
            if any(event['event'] == 'setup_recovery_authorized' and event['environment'] == 'E3'
                   for event in events):
                raise ValueError('SAM3 recovery already allocated; no additional recovery attempt')
            states = self.states(events)
            original = states.get('E3-setup', {})
            if (original.get('event') != 'finish' or original.get('status') != 'failed' or
                    original.get('cleanup_confirmed') is not True or
                    original.get('event_sha256') != document.get('original_failure_event_sha256')):
                raise ValueError('recovery must bind the preserved, cleaned-up E3 failure')
            if any(state['event'] == 'reserve' for state in states.values()):
                raise ValueError('unreconciled active attempt; refusing recovery allocation')
            if self.totals(events)['setup']['elapsed_seconds'] + preparation_seconds >= self.config['setup_wall_seconds_limit']:
                raise ValueError('cumulative setup allocation exhausted')
            return self._append(stream, events, dict(event='setup_recovery_authorized',
                job_id=document['job_id'], original_job_id='E3-setup', environment='E3',
                original_failure_event_sha256=original['event_sha256'], authorization=authorization,
                preparation_elapsed_seconds=preparation_seconds,
                preparation_evidence=document['asset_preparation']))

    def _authorize_e1_recovery(self, authorization, document, environment="E1"):
        """One explicit retry, with only the recorded E4 amendment permitted."""
        from .runtime import TARGETS
        from .setup_recipes import recipe

        # This is a dated, E4-only exception, not general runtime-change authority.
        # The immutable authorization record retained in the event names the amendment.
        e4_audio_amendment = (
            environment == 'E4' and
            document.get('runtime_amendment') == 'plan031-e4-torchaudio-211-20260919' and
            document.get('changes_to_prescribed_runtime') is True and
            TARGETS['E4'] == dict(python='3.11', torch='2.13.0+cu130',
                                  torchvision='0.28.0+cu130', numpy='2.1.3') and
            [r for r in recipe('E4')['requirements'] if r.startswith('torchaudio')]
            == ['torchaudio==2.11.0+cu130'])
        if environment == 'E4' and not e4_audio_amendment:
            raise ValueError('recovery requires the exact explicit E4 authorization scope')
        required = dict(original_job_id=f'{environment}-setup',
            environment=environment, recovery_attempts_limit=1,
            setup_wall_seconds_limit=self.config['setup_wall_seconds_limit'],
            reset_previous_consumption=False, changes_to_prescribed_runtime=e4_audio_amendment,
            unrelated_attempts_reopened=False)
        if any(document.get(k) != v for k, v in required.items()) or not document.get('authorization'):
            raise ValueError(f'recovery requires the exact explicit {environment} authorization scope')
        if not re.fullmatch(rf'{environment}-setup-recovery-[0-9]{{3}}', document.get('job_id', '')):
            raise ValueError(f'{environment} recovery requires a numbered fresh identity')
        validation = read_json(verify_record(document['repair_validation'])['path'])
        if validation.get('status') != 'passed':
            raise ValueError(f'{environment} recovery requires passing repair validation')
        for record in validation['source_files']:
            verify_record(record)
        with self.locked() as (stream, events):
            prior = [e for e in events if e['event'] == 'setup_recovery_authorized' and e['environment'] == environment]
            if any(e['job_id'] == document['job_id'] for e in prior):
                raise ValueError(f'{environment} recovery already allocated; no additional recovery attempt')
            if document['job_id'] != f'{environment}-setup-recovery-{len(prior) + 1:03d}':
                raise ValueError(f'{environment} recovery must use the next sequential identity')
            states = self.states(events)
            if prior:
                previous = states.get(prior[-1]['job_id'], {})
                if (previous.get('event') != 'finish' or previous.get('status') != 'failed' or
                        previous.get('cleanup_confirmed') is not True or
                        previous.get('event_sha256') != document.get('previous_recovery_failure_event_sha256')):
                    raise ValueError(f'new {environment} authorization must bind the previous cleaned-up recovery failure')
            original = states.get(f'{environment}-setup', {})
            if (original.get('event') != 'finish' or original.get('status') != 'failed' or
                    original.get('cleanup_confirmed') is not True or
                    original.get('event_sha256') != document.get('original_failure_event_sha256')):
                raise ValueError(f'recovery must bind the preserved, cleaned-up {environment} failure')
            if any(state['event'] == 'reserve' for state in states.values()):
                raise ValueError('unreconciled active attempt; refusing recovery allocation')
            if self.totals(events)['setup']['elapsed_seconds'] >= self.config['setup_wall_seconds_limit']:
                raise ValueError('cumulative setup allocation exhausted')
            return self._append(stream, events, dict(event='setup_recovery_authorized',
                job_id=document['job_id'], original_job_id=f'{environment}-setup', environment=environment,
                original_failure_event_sha256=original['event_sha256'], authorization=authorization,
                preparation_elapsed_seconds=0., preparation_evidence=document['repair_validation']))
