"""Locked, append-only, hash-chained attempt and resource ledger."""
from .s1_identity import is_recovery_job, is_standing_retry_job
from contextlib import contextmanager
import fcntl
import json
import math
import os
import re
from pathlib import Path
import time
import sys

from .config import jobs
from .files import canonical, file_record, object_hash, read_json, safe_path, verify_record


class Ledger:
    def __init__(self, path, config):
        self.path = safe_path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.config = config

    def _jobs(self, events):
        allocated = jobs(self.config)
        for event in events:
            if event['event'] == 'depth_driver_qualification_triton_cache_authorized':
                from .depth_driver_qualification_triton_cache import validate_request as qualification_triton_cache_request
                granted, proposal = qualification_triton_cache_request(event['request'], completed=True)
                if granted['job_id'] != event.get('job_id'):
                    raise ValueError('Triton-cache grant job differs from its request')
                allocated[granted['job_id']] = dict(id=granted['job_id'], resource='gpu', seconds=proposal['seconds'],
                    scope='separately approved D6 Triton-helper-cache driver ' + granted['job_id'])
            if event['event'] == 'depth_driver_qualification_local_listen_authorized':
                from .depth_driver_qualification_local_listen import JOB as qualification_local_listen_job, validate_request as qualification_local_listen_request
                _, proposal = qualification_local_listen_request(event['request'], completed=True)
                allocated[qualification_local_listen_job] = dict(id=qualification_local_listen_job, resource='gpu', seconds=proposal['seconds'],
                    scope='separately approved D6 local-listen driver qualification004')
            if event['event'] == 'depth_driver_qualification_local_bind_authorized':
                from .depth_driver_qualification_local_bind import JOB as qualification_local_bind_job, validate_request as qualification_local_bind_request
                _, proposal = qualification_local_bind_request(event['request'], completed=True)
                allocated[qualification_local_bind_job] = dict(id=qualification_local_bind_job, resource='gpu', seconds=proposal['seconds'],
                    scope='separately approved D6 local-bind driver qualification003')
            if event['event'] == 'depth_driver_qualification_recovery_authorized':
                from .depth_driver_qualification_recovery import JOB as qualification_recovery_job, validate_request as qualification_recovery_request
                _, proposal = qualification_recovery_request(event['request'], completed=True)
                allocated[qualification_recovery_job] = dict(id=qualification_recovery_job, resource='gpu', seconds=proposal['seconds'],
                    scope='separately approved D6 creation-only driver qualification002')
            if event['event'] == 'depth_driver_diagnostic_authorized':
                from .depth_driver_diagnostic import JOB, validate_request
                _, proposal = validate_request(event['request'], completed=True)
                allocated[JOB] = dict(id=JOB, resource='gpu', seconds=proposal['seconds'],
                    scope='separately approved D6 driver-only syscall diagnostic')
            if event['event'] == 'depth_setup_recovery_authorized':
                from .setup_recovery_core import candidate_for_job
                recovery_job = event.get('job_id')
                recovery_candidate = candidate_for_job(recovery_job)
                if recovery_candidate is None or event.get('candidate', 'D9') != recovery_candidate:
                    raise ValueError('unknown checked setup recovery job')
                for key in ('request','review','authorization','source_review'):
                    verify_record(event[key])
                allocated[recovery_job] = dict(id=recovery_job,resource='setup',seconds=event['seconds'],
                    scope=f'explicitly approved one-attempt {recovery_candidate} retained-input recovery')
            if event['event'] == 'depth_driver_qualification_authorized':
                from .depth_driver_qualification import JOB, validate_request
                _, proposal = validate_request(event['request'], completed=True)
                allocated[JOB] = dict(id=JOB, resource='gpu', seconds=proposal['seconds'],
                    scope='approved D6 driver-aware import and two strict CPU model loads')
            if event['event'] == 'depth_attempt_authorized':
                for key in ('review', 'authorization', 'source_review', 'admission'):
                    verify_record(event[key])
                from .depth_map_retry import event_job
                job_id = event_job(event)
                allocated[job_id] = dict(id=job_id, resource='gpu',
                    seconds=event['seconds'],
                    scope=('operator-approved Plan 069 native depth map retry' if 'retry' in event
                           else 'approved one-attempt Plan 069 native depth inference'))
            if event['event'] == 'depth_setup_authorized':
                verify_record(event['review'])
                verify_record(event['authorization'])
                verify_record(event['source_review'])
                candidate = event['candidate']
                job_id = f'plan069-{candidate}-setup-001'
                allocated[job_id] = dict(id=job_id, resource='setup',
                    seconds=event['seconds'],
                    scope='approved one-attempt Plan 069 depth setup and exact transfers')
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
                if event['environment'] == 'E5':
                    allocated[event['job_id']]['seconds'] = read_json(event['authorization']['path'])['attempt_wall_seconds_limit']
        return allocated

    @property
    def jobs(self):
        return self._jobs(self.events())

    @contextmanager
    def locked(self):
        with self.path.open('a+') as stream:
            fcntl.flock(stream, fcntl.LOCK_EX)
            stream.seek(0)
            events: list[dict] = []
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
            if job_id == 'plan069-D6-driver-diagnostic-001':
                from .depth_driver_diagnostic import validate_request as diagnostic_request
                grants = [row for row in events if row['event'] == 'depth_driver_diagnostic_authorized']
                if len(grants) != 1 or time.time() - grants[0]['recorded_unix'] > 30:
                    raise ValueError('fresh checked diagnostic authority required')
                from .depth_admission import local_source_records
                request, _ = diagnostic_request(grants[0]['request'], current_sources=local_source_records('D6'))
                if command != request['command'] or evidence != dict(request=grants[0]['request']):
                    raise ValueError('diagnostic command/evidence differs')
            if job_id in states:
                raise ValueError('job already consumed or accounted for; no automatic retry')
            if any(r['event'] == 'reserve' for r in states.values()):
                raise ValueError('unreconciled active attempt; refusing concurrent dispatch')
            from .setup_recovery_core import candidate_for_job
            if candidate_for_job(job_id) is not None:
                self._depth_recovery_reservation(events, evidence, command, job_id=job_id)
            from .depth_map_retry import event_job, is_map_job
            if is_map_job(job_id):
                candidate = job_id.split('-')[1]
                continuation = None
                if candidate == 'D9':
                    from .depth_d9_continuation import protected_continuation
                    continuation = protected_continuation(events, self.config, self.path.parent,
                        phase='reserve')
                authorized = [row for row in events if
                    row['event'] == 'depth_attempt_authorized' and
                    row['candidate'] == candidate and event_job(row) == job_id]
                if len(authorized) != 1 or (continuation is None and
                        (events[-1] != authorized[0] or
                         time.time() - authorized[0]['recorded_unix'] > 30)):
                    raise ValueError('fresh exact depth authorization required')
                bound = authorized[0]
                from .depth_admission import local_source_records
                source = read_json(verify_record(bound['source_review'])['path'])
                if continuation is None and source.get('local_sources') != local_source_records(candidate):
                    raise ValueError('depth sources changed after review')
                if not isinstance(evidence, dict) or any(
                        evidence.get(key) != bound[key] for key in
                        ('review', 'authorization', 'source_review', 'admission')):
                    raise ValueError('depth reservation evidence differs from authorization')
                if command != bound.get('command') or any(evidence.get(key) != bound.get(key)
                        for key in ('request', 'worker', 'executable')):
                    raise ValueError('depth command differs from authorization')
                if continuation is not None:
                    expected = dict(**{key: bound[key] for key in ('review', 'authorization',
                        'source_review', 'admission', 'request', 'worker', 'executable')},
                        continuation=continuation['request'])
                    if evidence != expected:
                        raise ValueError('exact original evidence plus protected continuation required')
                    self._depth_d9_continuation_resources(events)
                if 'retry' in bound:
                    from .depth_map_retry import validate_retry
                    review = read_json(verify_record(bound['review'])['path'])
                    proposal = next(row for row in review['proposals'] if row['candidate'] == candidate)
                    if validate_retry(candidate, proposal, events, self.path.parent) != bound['retry']:
                        raise ValueError('map retry approval changed after authorization')
                self._depth_command(candidate, bound, source, evidence, command, job_id=job_id)
            from .depth_driver_qualification_triton_cache import ATTEMPTS as triton_cache_attempts
            if job_id in triton_cache_attempts:
                from .depth_driver_qualification_triton_cache import check_predecessor as triton_cache_predecessor, validate_request as triton_cache_request
                grants = [row for row in events if row['event'] == 'depth_driver_qualification_triton_cache_authorized' and row.get('job_id') == job_id]
                if len(grants) != 1 or events[-1] != grants[0] or time.time() - grants[0]['recorded_unix'] > 30:
                    raise ValueError('fresh exact ' + job_id + ' authorization required')
                from .depth_admission import local_source_records
                request, _ = triton_cache_request(grants[0]['request'], current_sources=local_source_records('D6'))
                triton_cache_predecessor(events, request)
                if request['job_id'] != job_id or command != request['command'] or evidence != dict(request=grants[0]['request']):
                    raise ValueError(job_id + ' command/evidence differs')
            if job_id == 'plan069-D6-driver-qualification-004':
                from .depth_driver_qualification_local_listen import check_predecessor as local_listen_predecessor, validate_request as local_listen_request
                grants = [row for row in events if row['event'] == 'depth_driver_qualification_local_listen_authorized']
                if len(grants) != 1 or events[-1] != grants[0] or time.time() - grants[0]['recorded_unix'] > 30:
                    raise ValueError('fresh exact qualification004 authorization required')
                from .depth_admission import local_source_records
                request, _ = local_listen_request(grants[0]['request'], current_sources=local_source_records('D6'))
                local_listen_predecessor(events, request)
                if command != request['command'] or evidence != dict(request=grants[0]['request']):
                    raise ValueError('qualification004 command/evidence differs')
            if job_id == 'plan069-D6-driver-qualification-003':
                from .depth_driver_qualification_local_bind import check_predecessor as local_bind_predecessor, validate_request as local_bind_request
                grants = [row for row in events if row['event'] == 'depth_driver_qualification_local_bind_authorized']
                if len(grants) != 1 or events[-1] != grants[0] or time.time() - grants[0]['recorded_unix'] > 30:
                    raise ValueError('fresh exact qualification003 authorization required')
                from .depth_admission import local_source_records
                request, _ = local_bind_request(grants[0]['request'], current_sources=local_source_records('D6'))
                local_bind_predecessor(events, request)
                if command != request['command'] or evidence != dict(request=grants[0]['request']):
                    raise ValueError('qualification003 command/evidence differs')
            if job_id == 'plan069-D6-driver-qualification-002':
                from .depth_driver_qualification_recovery import check_predecessor as recovery_predecessor, validate_request as recovery_request
                grants = [row for row in events if row['event'] == 'depth_driver_qualification_recovery_authorized']
                if len(grants) != 1 or events[-1] != grants[0] or time.time() - grants[0]['recorded_unix'] > 30:
                    raise ValueError('fresh exact qualification002 authorization required')
                from .depth_admission import local_source_records
                request, _ = recovery_request(grants[0]['request'], current_sources=local_source_records('D6'))
                recovery_predecessor(events, request)
                if command != request['command'] or evidence != dict(request=grants[0]['request']):
                    raise ValueError('qualification002 command/evidence differs')
            if job_id == 'plan069-D6-driver-qualification-001':
                from .depth_driver_qualification import validate_request
                grants = [row for row in events if row['event'] == 'depth_driver_qualification_authorized']
                if len(grants) != 1 or events[-1] != grants[0] or time.time() - grants[0]['recorded_unix'] > 30:
                    raise ValueError('fresh exact driver qualification authorization required')
                from .depth_admission import local_source_records
                request, _ = validate_request(grants[0]['request'], current_sources=local_source_records('D6'))
                if command != request['command'] or evidence != dict(request=grants[0]['request']):
                    raise ValueError('driver qualification command/evidence differs')
            if is_recovery_job(job_id):
                from .s1_recovery import reservation_binding as s1_reservation_binding
                s1_reservation_binding(self.path.parent, self.config, events, evidence, command=command)
            if job_id in ('E5-setup-recovery-001', 'E5-setup-recovery-002', 'E5-setup-recovery-003', 'E5-setup-recovery-004'):
                from .e5_recovery import reservation_binding as e5_reservation_binding
                e5_reservation_binding(self.path.parent, self.config, events, command, evidence, job_id=job_id)
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

    def authorize_depth_driver_diagnostic(self, request_record):
        """Allocate exactly one newly approved driver-only diagnostic."""
        from .depth_driver_diagnostic import JOB, check_predecessor, validate_request
        from .depth_admission import local_source_records
        request, proposal = validate_request(request_record, current_sources=local_source_records('D6'))
        if Path(request['ledger_path']).absolute() != self.path.absolute():
            raise ValueError('diagnostic ledger binding differs')
        from .execution import resources
        with self.locked() as (stream, events):
            check_predecessor(events, request)
            if any(row['event'] == 'depth_driver_diagnostic_authorized' for row in events) or JOB in self.states(events):
                raise ValueError('diagnostic already authorized or consumed')
            if any(row['event'] == 'reserve' for row in self.states(events).values()):
                raise ValueError('unreconciled active attempt')
            live = resources(self.path.parent, gpu=True)
            if live['gpu_pids'] or live['device_bytes'] > proposal['device_bytes']:
                raise ValueError('diagnostic GPU owner/device bound')
            if self.config['gpu_total_seconds_limit'] - self.totals(events)['gpu']['elapsed_seconds'] < proposal['seconds']:
                raise ValueError('insufficient diagnostic GPU allocation')
            if live['download_bytes'] > self.config['new_download_gib_limit'] * 1024**3 or live['artifact_bytes'] > self.config['new_artifact_disk_gib_limit'] * 1024**3:
                raise ValueError('global diagnostic disk/download bound')
            return self._append(stream, events, dict(event='depth_driver_diagnostic_authorized',
                job_id=JOB, request=request_record, seconds=proposal['seconds']))

    def authorize_depth_driver_qualification(self, request_record):
        """Allocate only the separately approved one-use D6 driver qualification."""
        from .depth_driver_qualification import JOB, validate_request
        from .depth_admission import local_source_records
        request, proposal = validate_request(request_record, current_sources=local_source_records('D6'))
        if Path(request['ledger_path']).absolute() != self.path.absolute():
            raise ValueError('driver qualification ledger binding differs')
        from .execution import resources
        with self.locked() as (stream, events):
            if any(row['event'] == 'depth_driver_qualification_authorized' for row in events) or JOB in self.states(events):
                raise ValueError('driver qualification already authorized or consumed')
            if any(row['event'] == 'reserve' for row in self.states(events).values()):
                raise ValueError('unreconciled active attempt')
            live = resources(self.path.parent, gpu=True)
            if self.config['gpu_total_seconds_limit'] - self.totals(events)['gpu']['elapsed_seconds'] < proposal['seconds']:
                raise ValueError('insufficient global GPU wall allocation')
            if live['gpu_pids']:
                raise ValueError('GPU owner active before driver qualification')
            if live['device_bytes'] > proposal['device_bytes']:
                raise ValueError('driver qualification initial VRAM cap exceeded')
            if live['download_bytes'] > self.config['new_download_gib_limit'] * 1024**3 or \
                    live['artifact_bytes'] > self.config['new_artifact_disk_gib_limit'] * 1024**3:
                raise ValueError('global disk or download cap exceeded')
            return self._append(stream, events, dict(event='depth_driver_qualification_authorized',
                job_id=JOB, request=request_record, seconds=proposal['seconds']))

    def authorize_depth_driver_qualification_triton_cache(self, request_record):
        """Allocate one fresh explicit approval for the next Triton-cache attempt; earlier slots remain consumed."""
        from .depth_driver_qualification_triton_cache import check_predecessor, validate_request
        from .depth_admission import local_source_records
        request, proposal = validate_request(request_record, current_sources=local_source_records('D6'))
        job = request['job_id']
        if Path(request['ledger_path']).absolute() != self.path.absolute():
            raise ValueError(job + ' ledger binding differs')
        from .execution import resources
        with self.locked() as (stream, events):
            check_predecessor(events, request)
            if any(row['event'] == 'depth_driver_qualification_triton_cache_authorized' and row.get('job_id') == job
                   for row in events) or job in self.states(events):
                raise ValueError(job + ' already authorized or consumed')
            if any(row['event'] == 'reserve' for row in self.states(events).values()):
                raise ValueError('unreconciled active attempt')
            live = resources(self.path.parent, gpu=True)
            if self.config['gpu_total_seconds_limit'] - self.totals(events)['gpu']['elapsed_seconds'] < proposal['seconds']:
                raise ValueError('insufficient global GPU wall allocation')
            if live['gpu_pids'] or live['device_bytes'] > proposal['device_bytes']:
                raise ValueError(job + ' GPU owner/device bound')
            if live['download_bytes'] > self.config['new_download_gib_limit'] * 1024**3 or live['artifact_bytes'] > self.config['new_artifact_disk_gib_limit'] * 1024**3:
                raise ValueError('global disk or download cap exceeded')
            return self._append(stream, events, dict(event='depth_driver_qualification_triton_cache_authorized',
                job_id=job, request=request_record, seconds=proposal['seconds']))

    def authorize_depth_driver_qualification_local_listen(self, request_record):
        """Allocate one fresh explicit004 approval; original slots remain consumed."""
        from .depth_driver_qualification_local_listen import JOB, check_predecessor, validate_request
        from .depth_admission import local_source_records
        request, proposal = validate_request(request_record, current_sources=local_source_records('D6'))
        if Path(request['ledger_path']).absolute() != self.path.absolute():
            raise ValueError('qualification004 ledger binding differs')
        from .execution import resources
        with self.locked() as (stream, events):
            check_predecessor(events, request)
            if any(row['event'] == 'depth_driver_qualification_local_listen_authorized' for row in events) or JOB in self.states(events):
                raise ValueError('qualification004 already authorized or consumed')
            if any(row['event'] == 'reserve' for row in self.states(events).values()):
                raise ValueError('unreconciled active attempt')
            live = resources(self.path.parent, gpu=True)
            if self.config['gpu_total_seconds_limit'] - self.totals(events)['gpu']['elapsed_seconds'] < proposal['seconds']:
                raise ValueError('insufficient global GPU wall allocation')
            if live['gpu_pids'] or live['device_bytes'] > proposal['device_bytes']:
                raise ValueError('qualification004 GPU owner/device bound')
            if live['download_bytes'] > self.config['new_download_gib_limit'] * 1024**3 or live['artifact_bytes'] > self.config['new_artifact_disk_gib_limit'] * 1024**3:
                raise ValueError('global disk or download cap exceeded')
            return self._append(stream, events, dict(event='depth_driver_qualification_local_listen_authorized',
                job_id=JOB, request=request_record, seconds=proposal['seconds']))

    def authorize_depth_driver_qualification_local_bind(self, request_record):
        """Allocate one fresh explicit003 approval; original slots remain consumed."""
        from .depth_driver_qualification_local_bind import JOB, check_predecessor, validate_request
        from .depth_admission import local_source_records
        request, proposal = validate_request(request_record, current_sources=local_source_records('D6'))
        if Path(request['ledger_path']).absolute() != self.path.absolute():
            raise ValueError('qualification003 ledger binding differs')
        from .execution import resources
        with self.locked() as (stream, events):
            check_predecessor(events, request)
            if any(row['event'] == 'depth_driver_qualification_local_bind_authorized' for row in events) or JOB in self.states(events):
                raise ValueError('qualification003 already authorized or consumed')
            if any(row['event'] == 'reserve' for row in self.states(events).values()):
                raise ValueError('unreconciled active attempt')
            live = resources(self.path.parent, gpu=True)
            if self.config['gpu_total_seconds_limit'] - self.totals(events)['gpu']['elapsed_seconds'] < proposal['seconds']:
                raise ValueError('insufficient global GPU wall allocation')
            if live['gpu_pids'] or live['device_bytes'] > proposal['device_bytes']:
                raise ValueError('qualification003 GPU owner/device bound')
            if live['download_bytes'] > self.config['new_download_gib_limit'] * 1024**3 or live['artifact_bytes'] > self.config['new_artifact_disk_gib_limit'] * 1024**3:
                raise ValueError('global disk or download cap exceeded')
            return self._append(stream, events, dict(event='depth_driver_qualification_local_bind_authorized',
                job_id=JOB, request=request_record, seconds=proposal['seconds']))

    def authorize_depth_driver_qualification_recovery(self, request_record):
        """Allocate one fresh explicit002 approval; original slots remain consumed."""
        from .depth_driver_qualification_recovery import JOB, check_predecessor, validate_request
        from .depth_admission import local_source_records
        request, proposal = validate_request(request_record, current_sources=local_source_records('D6'))
        if Path(request['ledger_path']).absolute() != self.path.absolute():
            raise ValueError('qualification002 ledger binding differs')
        from .execution import resources
        with self.locked() as (stream, events):
            check_predecessor(events, request)
            if any(row['event'] == 'depth_driver_qualification_recovery_authorized' for row in events) or JOB in self.states(events):
                raise ValueError('qualification002 already authorized or consumed')
            if any(row['event'] == 'reserve' for row in self.states(events).values()):
                raise ValueError('unreconciled active attempt')
            live = resources(self.path.parent, gpu=True)
            if self.config['gpu_total_seconds_limit'] - self.totals(events)['gpu']['elapsed_seconds'] < proposal['seconds']:
                raise ValueError('insufficient global GPU wall allocation')
            if live['gpu_pids'] or live['device_bytes'] > proposal['device_bytes']:
                raise ValueError('qualification002 GPU owner/device bound')
            if live['download_bytes'] > self.config['new_download_gib_limit'] * 1024**3 or live['artifact_bytes'] > self.config['new_artifact_disk_gib_limit'] * 1024**3:
                raise ValueError('global disk or download cap exceeded')
            return self._append(stream, events, dict(event='depth_driver_qualification_recovery_authorized',
                job_id=JOB, request=request_record, seconds=proposal['seconds']))

    def _depth_frame_prerequisite(self, candidate, approved, events):
        """Recheck a D10 frame prerequisite while owning the current ledger lock."""
        amendment = approved.get('video_frame_amendment')
        if candidate == 'D10' and amendment is not None:
            from .depth_video_frame_authorization import validate_D9_prerequisite
            validate_D9_prerequisite(amendment['D9_runtime_qualification'],
                ledger_prefix=amendment.get('D9_qualification_ledger_prefix'),
                approved=approved, current_events=events, allow_owned_active=False)

    def authorize_depth_setup(self, candidate, review, authorization, source_review, *,
                              prospective_byte_checkpoint=False):
        """Allocate one bounded setup attempt from exact user-approved proposals."""
        if candidate not in ('D2', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11'):
            raise ValueError('unknown approved depth setup candidate')
        from .files import object_hash
        reviewed = read_json(verify_record(review)['path'])
        approved = read_json(verify_record(authorization)['path'])
        proposal = next((row for row in reviewed.get('proposals', [])
            if row.get('candidate') == candidate), None)
        grant = next((row for row in approved.get('candidate_approvals', [])
            if row.get('candidate') == candidate), None)
        if (reviewed.get('schema') != 'plan069-depth-execution-review/v1' or
                reviewed.get('status') != 'REVIEW' or
                approved.get('schema') != 'plan069-depth-user-authorization/v1' or
                approved.get('status') != 'DO' or approved.get('review') != review or
                proposal is None or proposal.get('max_attempts') != 1 or
                grant is None or grant.get('schema') != 'plan069-depth-execution-approval/v1' or
                grant.get('status') != 'approved' or
                grant.get('proposal_sha256') != object_hash(proposal)):
            raise ValueError('exact approved depth setup proposal required')
        from .depth_admission import BENCHMARK, CAP_AMENDMENT, local_source_records
        source = read_json(verify_record(source_review)['path'])
        if (source.get('schema') != 'plan069-depth-source-review/v1' or
                source.get('status') != 'passed' or
                source.get('candidate') != candidate or
                source.get('source_revision') != proposal['candidate_config']['code']['revision'] or
                source.get('profile_inventory') != proposal['profile_inventory'] or
                source.get('local_sources') != local_source_records(candidate) or
                not source.get('reviewer')):
            raise ValueError('current independent depth source review required')
        historical = read_json(BENCHMARK)
        effective = dict(historical, new_download_gib_limit=110,
                         new_artifact_disk_gib_limit=210)
        if self.config != historical:
            amendment = read_json(verify_record(approved['cap_amendment'])['path'])
            if (self.config != effective or
                    approved['cap_amendment'] != file_record(CAP_AMENDMENT) or
                    amendment != dict(schema='plan069-depth-cap-amendment/v1',
                        status='REVIEW', historical_configuration={
                            key: file_record(BENCHMARK)[key] for key in ('sha256', 'bytes')},
                        new_download_gib_limit=110, new_artifact_disk_gib_limit=210) or
                    approved.get('cap_approval') != dict(
                        schema='plan069-depth-cap-approval/v1', status='approved',
                        amendment_sha256=object_hash(amendment))):
                raise ValueError('exact approved depth cap amendment required')
        seconds = proposal.get('allocation', {}).get('setup_seconds')
        if type(seconds) is not int or seconds <= 0:
            raise ValueError('bounded setup seconds required')
        with self.locked() as (stream, events):
            states = self.states(events)
            if any(row['event'] == 'reserve' for row in states.values()):
                raise ValueError('active attempt prevents depth setup authorization')
            if any(row['event'] == 'depth_setup_authorized' and row['candidate'] == candidate
                    for row in events):
                raise ValueError('depth setup attempt already authorized')
            if any(row['event'] == 'depth_setup_authorized' and
                    f"plan069-{row['candidate']}-setup-001" not in states
                    for row in events):
                raise ValueError('unstarted depth setup authorization prevents another allocation')
            self._depth_frame_prerequisite(candidate, approved, events)
            if self.totals(events)['setup']['elapsed_seconds'] + seconds > self.config['setup_wall_seconds_limit']:
                raise ValueError('setup allocation exceeds cumulative cap')
            from .execution import resources
            reading = resources(self.path.parent)
            for key, limit in (('download_bytes', 'new_download_gib_limit'),
                               ('artifact_bytes', 'new_artifact_disk_gib_limit')):
                if reading[key] + proposal['allocation'][key] > self.config[limit] * 2**30:
                    raise ValueError(key + ' setup allocation exceeds live cumulative cap')
            from .depth_budget_reconciliation import capture_checkpoint
            byte_checkpoint = (capture_checkpoint(self.path.parent, candidate, reading)
                               if prospective_byte_checkpoint else None)
            return self._append(stream, events, dict(event='depth_setup_authorized',
                candidate=candidate, seconds=seconds,
                proposal_sha256=object_hash(proposal), review=review,
                authorization=authorization, source_review=source_review,
                resource_snapshot=reading, byte_checkpoint=byte_checkpoint))

    def authorize_depth_setup_recovery(self, request, *, command, worker, executable):
        """Approve a fresh immutable recovery only under an explicit new DO."""
        from .setup_recovery_core import (RECOVERY_CANDIDATES, RECOVERY_EVENT as EVENT, candidate_for_job,
                                          recovery_profile)
        with self.locked() as (stream, events):
            if any(row['event'] == 'reserve' for row in self.states(events).values()):
                raise ValueError('active attempt prevents setup recovery authorization')
            # Route by the request's recovery job; unknown jobs keep the D9 profile's refusals.
            document = read_json(verify_record(request)['path'])
            candidate = candidate_for_job(document.get('job_id') if isinstance(document, dict) else None) or 'D9'
            normalized = recovery_profile(candidate).validate_recovery_request(request, events, self.path.parent)
            job_id = normalized['job_id']
            if job_id in self.states(events) or any(row.get('event') == EVENT and row.get('job_id') == job_id for row in events):
                raise ValueError('setup recovery already authorized or consumed')
            source = read_json(verify_record(normalized['source_review'])['path'])
            expected = [sys.executable, worker['path'], '--request', request['path'],
                        '--output', str(self.path.parent / 'jobs' / job_id)]
            if verify_record(worker) != worker or verify_record(executable) != executable or \
                    executable != file_record(sys.executable) or command != expected or \
                    worker not in source.get('local_sources',[]) or \
                    Path(worker['path']) != Path(__file__).parents[1] / RECOVERY_CANDIDATES[candidate]['worker']:
                raise ValueError('exact independently reviewed recovery executable worker command required')
            seconds = normalized['allocation']['setup_seconds']
            if self.totals(events)['setup']['elapsed_seconds'] + seconds > self.config['setup_wall_seconds_limit']:
                raise ValueError('recovery exceeds cumulative setup allowance')
            from .execution import resources
            reading = resources(self.path.parent, gpu=True)
            if reading.get('gpu_pids'):
                raise ValueError('GPU owner prevents CPU setup recovery dispatch')
            for key, cap in (('download_bytes','new_download_gib_limit'),
                             ('artifact_bytes','new_artifact_disk_gib_limit')):
                if reading[key] > min(self.config[cap] * 2**30,normalized['byte_limits'][key]):
                    raise ValueError(key + ' recovery exceeds unchanged original/global byte cap')
            acquisitions = {'acquisitions': normalized['acquisitions']} if 'acquisitions' in normalized else {}
            return self._append(stream, events, dict(event=EVENT,candidate=candidate,job_id=job_id,
                seconds=seconds,proposal_sha256=object_hash(normalized['proposal']),request=request,
                review=normalized['review'],authorization=normalized['authorization'],
                source_review=normalized['source_review'],command=command,worker=worker,
                executable=executable,resource_snapshot=reading,
                original_setup=normalized['original'],byte_limits=normalized['byte_limits'],**acquisitions))

    def _depth_recovery_reservation(self, events, evidence, command, *, job_id):
        from .setup_recovery_core import RECOVERY_EVENT as EVENT, candidate_for_job, recovery_profile
        grants = [row for row in events if row.get('event') == EVENT and row.get('job_id') == job_id]
        if len(grants) != 1 or events[-1] != grants[0] or time.time()-grants[0]['recorded_unix'] > 30:
            raise ValueError('fresh exact setup recovery authorization required')
        grant = grants[0]
        normalized = recovery_profile(candidate_for_job(job_id)).validate_recovery_request(
            grant['request'], events, self.path.parent)
        if command != grant['command'] or not isinstance(evidence,dict) or any(
                evidence.get(key) != grant[key] for key in
                ('request','review','authorization','source_review','worker','executable')):
            raise ValueError('recovery reservation differs from checked command authority')
        for key in ('worker','executable'):
            if verify_record(grant[key]) != grant[key]:
                raise ValueError('recovery command binding changed')
        from .execution import resources
        reading = resources(self.path.parent,gpu=True)
        if reading.get('gpu_pids'):
            raise ValueError('GPU owner prevents setup recovery reservation')
        for key, cap in (('download_bytes','new_download_gib_limit'),
                         ('artifact_bytes','new_artifact_disk_gib_limit')):
            if reading[key] > min(self.config[cap]*2**30,normalized['byte_limits'][key]):
                raise ValueError(key + ' recovery exceeds unchanged original/global byte cap')

    def reconcile_depth_setup_bytes(self, candidate, *, deadline=None, expected_head=None):
        """Protect prospective attribution after exact accepted cleanup."""
        from .depth_budget_reconciliation import prepare_reconciliation
        with self.locked() as (stream, events):
            if expected_head is not None and (not events or events[-1]['event_sha256'] != expected_head):
                raise ValueError('CPU reconciliation admission ledger head changed')
            if any(row['event'] == 'reserve' for row in self.states(events).values()):
                raise ValueError('active attempt prevents setup byte reconciliation')
            if any(row.get('event') == 'depth_setup_bytes_reconciled' and
                   row.get('candidate') == candidate for row in events):
                raise ValueError('setup byte reconciliation already protected')
            from .budgets import budget_snapshot
            reading = budget_snapshot(self.path.parent)
            for key, cap in (('download_bytes', 'new_download_gib_limit'),
                             ('artifact_bytes', 'new_artifact_disk_gib_limit')):
                if reading[key] > self.config[cap] * 2**30:
                    raise ValueError(key + ' reconciliation exceeds global cap')
            proof = prepare_reconciliation(self.path.parent, candidate, events, deadline=deadline)
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError('setup byte reconciliation CPU deadline exceeded before protected append')
            return self._append(stream, events, dict(event='depth_setup_bytes_reconciled',
                candidate=candidate, proof=proof))

    def _depth_command(self, candidate, bound, source, evidence, command, job_id=None):
        """Rehash the exact authorized worker, interpreter and immutable request."""
        from .depth_map_retry import first_job
        job_id = job_id or first_job(candidate)
        if not all(isinstance(evidence.get(key), dict) for key in
                   ('request', 'worker', 'executable')):
            raise ValueError('exact executable worker request command binding required')
        request_record = verify_record(evidence['request'])
        worker = verify_record(evidence['worker'])
        executable = verify_record(evidence['executable'])
        expected_command = [sys.executable, worker['path'], '--request',
            request_record['path'], '--output', str(self.path.parent / 'jobs' / job_id)]
        request = read_json(request_record['path'])
        if (command != expected_command or executable != file_record(sys.executable) or
                worker not in source.get('local_sources', []) or
                Path(worker['path']).name != ('basketball_vipe_depth_single_maps.py' if
                    candidate in ('D5', 'D6', 'D8') else
                    'basketball_vipe_d2_maps.py' if candidate == 'D2' else
                    'basketball_vipe_video_actual.py' if candidate in ('D9', 'D10') else
                    f'basketball_vipe_depth_{candidate.lower()}_maps.py') or
                request_record['path'] != str(self.path.parent / 'requests' / (job_id + '.json')) or
                request.get('candidate') != candidate or request.get('job_id') != job_id or
                request.get('record_kind') != 'actual' or
                any(request.get(key) != bound[key] for key in
                    ('review', 'authorization', 'source_review', 'admission'))):
            raise ValueError('exact executable worker request command binding required')

    def authorize_depth_attempt(self, candidate, review, authorization,
                                source_review, admission, *, command, request, worker, executable):
        """Allocate one native GPU slot only from current reviewed live evidence."""
        from .depth_admission import review as decide
        from .execution import resources
        if candidate not in ('D2', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11'):
            raise ValueError('unknown approved depth candidate')
        reviewed = read_json(verify_record(review)['path'])
        approved = read_json(verify_record(authorization)['path'])
        evidence = read_json(verify_record(admission)['path'])
        proposal = next((row for row in reviewed.get('proposals', [])
            if row.get('candidate') == candidate), None)
        grant = next((row for row in approved.get('candidate_approvals', [])
            if row.get('candidate') == candidate), None)
        if (reviewed.get('schema') != 'plan069-depth-execution-review/v1' or
                reviewed.get('status') != 'REVIEW' or
                approved.get('status') != 'DO' or
                approved.get('schema') != 'plan069-depth-user-authorization/v1' or
                approved.get('review') != review or proposal is None or
                proposal.get('max_attempts') != 1 or grant is None or
                grant.get('proposal_sha256') != object_hash(proposal) or
                grant.get('status') != 'approved' or
                evidence.get('schema') != 'plan069-depth-admission-result/v1' or
                evidence.get('status') != 'passed' or
                evidence.get('candidate') != candidate or
                evidence.get('proposal_sha256') != object_hash(proposal) or
                evidence.get('review') != review or
                evidence.get('authorization') != authorization or
                evidence.get('source_review') != source_review):
            raise ValueError('exact approved depth attempt and admission required')
        binding = dict(request=request, worker=worker, executable=executable)
        source = read_json(verify_record(source_review)['path'])
        from .depth_map_retry import event_job, first_job, map_job, validate_retry
        job_id = map_job(candidate, self.events())
        self._depth_command(candidate, dict(review=review, authorization=authorization,
            source_review=source_review, admission=admission), source, binding, command, job_id=job_id)
        seconds = proposal.get('allocation', {}).get('gpu_seconds')
        if type(seconds) is not int or seconds <= 0:
            raise ValueError('bounded depth GPU seconds required')
        with self.locked() as (stream, events):
            states = self.states(events)
            if map_job(candidate, events) != job_id:
                raise ValueError('current map job changed during authorization')
            if job_id in states or any(row['event'] == 'depth_attempt_authorized' and
                                       row['candidate'] == candidate and event_job(row) == job_id
                                       for row in events):
                raise ValueError('depth model attempt already authorized or consumed')
            if any(row['event'] == 'reserve' for row in states.values()):
                raise ValueError('active attempt prevents depth GPU allocation')
            if any(row['event'] == 'depth_attempt_authorized' and
                   event_job(row) not in states for row in events):
                raise ValueError('unstarted depth GPU allocation prevents another')
            retry = None
            if job_id != first_job(candidate):
                retry = validate_retry(candidate, proposal, events, self.path.parent)
                seconds = retry['seconds']
            self._depth_frame_prerequisite(candidate, approved, events)
            head = events[-1]['event_sha256'] if events else '0' * 64
            live = evidence.get('live', {})
            if live.get('ledger_head_sha256') != head:
                raise ValueError('depth admission ledger head is stale')
            if candidate in ('D5','D6','D8','D9','D10','D11') and evidence.get('completed_setup') is None:
                raise ValueError('new native slot requires completed setup stage proof')
            from .depth_admission import BENCHMARK, CAP_AMENDMENT
            historical = read_json(BENCHMARK)
            cap_amendment = file_record(CAP_AMENDMENT) if self.config != historical else None
            cap_approval = approved.get('cap_approval')
            from .depth_recovery_lineage import recovery_cap_authorization
            inherited = recovery_cap_authorization(proposal, authorization,
                evidence.get('completed_setup'), events, self.path.parent)
            if inherited is not None:
                cap_amendment, cap_approval = inherited
            blockers = decide(proposal, config=self.config,
                commercial=evidence['commercial'], assets=evidence['assets'],
                runtime=evidence['runtime'], live=live,
                source_review=source_review, approval=grant,
                cap_amendment=cap_amendment,
                cap_approval=cap_approval,
                ledger_head_sha256=head,
                completed_setup=evidence.get('completed_setup'),
                setup_events=events, run_root=self.path.parent)
            if blockers:
                raise ValueError('depth admission failed: ' + '; '.join(blockers))
            allocation = proposal['allocation']
            stage = None
            if evidence.get('completed_setup') is not None:
                from .depth_map_allowance import remaining_map_allocation
                if read_json(verify_record(request)['path']).get('setup') != evidence['completed_setup']:
                    raise ValueError('map request differs from credited completed setup')
                stage = remaining_map_allocation(proposal, evidence['completed_setup'],
                    events, self.path.parent, evidence['assets'])
                allocation = stage['allocation']
            reading = resources(self.path.parent, gpu=True)
            if reading['gpu_pids']:
                raise ValueError('GPU owner active before depth allocation')
            if stage is not None and any(reading[key] < stage['credited_assets_bytes']
                    for key in ('download_bytes', 'artifact_bytes')):
                raise ValueError('completed setup assets no longer included in live accounting')
            slot_budget = None
            if stage is not None:
                from .depth_map_allowance import bind_slot_byte_budget
                slot_budget = bind_slot_byte_budget(proposal, stage, events, self.path.parent, reading)
            total = self.totals(events)['gpu']['elapsed_seconds']
            if total + seconds > self.config['gpu_total_seconds_limit']:
                raise ValueError('depth GPU cumulative allowance exhausted')
            for key, cap in (('download_bytes', 'new_download_gib_limit'),
                             ('artifact_bytes', 'new_artifact_disk_gib_limit')):
                if reading[key] + allocation[key] > self.config[cap] * 2**30:
                    raise ValueError(key + ' depth allocation exceeds live cap')
            if reading['device_bytes'] + allocation['device_bytes'] > self.config['gpu_peak_device_gib_limit'] * 2**30:
                raise ValueError('depth allocation exceeds device ceiling')
            return self._append(stream, events, dict(event='depth_attempt_authorized',
                candidate=candidate, seconds=seconds,
                proposal_sha256=object_hash(proposal), review=review,
                authorization=authorization, source_review=source_review,
                admission=admission, resource_snapshot=reading, map_stage_allowance=stage,
                slot_byte_budget=slot_budget,
                command=command, **binding, **({} if retry is None else dict(job_id=job_id, retry=retry))))

    def continue_depth_d9_attempt(self, request_record):
        """Continue only the already allocated, unstarted grant851."""
        from .depth_d9_continuation import EVENT, JOB, validate_request
        with self.locked() as (stream, events):
            validate_request(request_record, events, self.config, self.path.parent)
            if any(row.get('event') == EVENT for row in events):
                raise ValueError('D9 allocation already continued; no automatic replay')
            self._depth_d9_continuation_resources(events)
            return self._append(stream, events, dict(event=EVENT, job_id=JOB,
                candidate='D9', request=request_record))

    def _depth_d9_continuation_resources(self, events):
        """Recheck the original allowance against a fresh host GPU sample."""
        from .depth_d9_continuation import original_grant
        from .depth_map_allowance import check_slot_byte_budget
        from .execution import resources
        grant = original_grant(events)
        reading = resources(self.path.parent, gpu=True)
        proposal = next(row for row in read_json(grant['review']['path'])['proposals']
                        if row['candidate'] == 'D9')
        if reading['gpu_pids'] or reading.get('device_uuid') != grant['resource_snapshot'].get('device_uuid'):
            raise ValueError('original single GPU identity/ownership changed before D9 continuation')
        check_slot_byte_budget(proposal, grant['slot_byte_budget'], self.path.parent, reading, events=events)
        if (reading['device_bytes'] + proposal['allocation']['device_bytes'] >
                self.config['gpu_peak_device_gib_limit'] * 2**30 or
                self.totals(events)['gpu']['elapsed_seconds'] + grant['seconds'] >
                self.config['gpu_total_seconds_limit']):
            raise ValueError('unchanged D9 GPU allocation exceeds live global ceiling')
        for key, cap in (('download_bytes', 'new_download_gib_limit'),
                         ('artifact_bytes', 'new_artifact_disk_gib_limit')):
            if reading[key] + grant['map_stage_allowance']['allocation'][key] > self.config[cap] * 2**30:
                raise ValueError(key + ' D9 continuation exceeds unchanged global cap')

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
                     'checkpoint_resume', 'depth_driver_qualification_triton_cache_authorized', 'depth_driver_qualification_local_listen_authorized', 'depth_driver_qualification_local_bind_authorized', 'depth_driver_qualification_recovery_authorized', 'depth_driver_diagnostic_authorized', 'depth_driver_qualification_authorized',
                     'depth_setup_authorized', 'depth_attempt_authorized', 'depth_d9_attempt_continued', 'depth_setup_bytes_reconciled',
                     'depth_setup_recovery_authorized',
                     'native_qualification_authorized', 'final_render_do_authorized', 'cpu_preparation_charge', 'setup_recovery_authorized', 'component_recovery_authorized',
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
            if job_id == 'plan069-D9-maps-001' and status == 'complete':
                from .depth_d9_continuation import EVENT, protected_continuation
                if any(row.get('event') == EVENT for row in events):
                    try:
                        protected_continuation(events, self.config, self.path.parent, phase='finish')
                    except Exception as error:
                        status = 'failed'
                        fields['continuation_validation_error'] = f'{type(error).__name__}: {error}'
                    elapsed_seconds = max(elapsed_seconds, time.monotonic() - state['monotonic_start'])
                    if elapsed_seconds > state['seconds']:
                        status = 'failed'
                        fields['continuation_validation_deadline_exceeded'] = True
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
        """One explicit recovery, retaining original failures and all charges."""
        from .s1_recovery import SCHEMA, SCHEMA_2, SCHEMA_3, SCHEMA_4, SCHEMA_5, SCHEMA_6, SCHEMA_7, SCHEMA_8, SCHEMA_9, validate_binding
        document = read_json(verify_record(authorization)['path'])
        original_id = document.get('original_job_id', '')
        amended = document.get('schema') in (SCHEMA, SCHEMA_2, SCHEMA_3, SCHEMA_4, SCHEMA_5, SCHEMA_6, SCHEMA_7, SCHEMA_8, SCHEMA_9)
        if is_standing_retry_job(document.get('job_id')):
            from .s1_recovery import STANDING_SCHEMA
            amended = document.get('schema') == STANDING_SCHEMA
        if not amended and original_id.startswith('S1-'):
            raise ValueError('S1 requires calibration-only semantic amendment authorization; reconstruction blocked')
        if not re.fullmatch(r'S[0-4]-(calibration|reconstruction)', original_id):
            raise ValueError('component recovery requires an original segmentation matrix arm')
        spec = jobs(self.config)[original_id]
        required = dict(schema=document.get('schema') if amended else 'vipe-benchmark-component-recovery/v1', attempts_limit=1,
            seconds_limit=spec['seconds'], reset_previous_consumption=False,
            gpu_total_seconds_limit=self.config['gpu_total_seconds_limit'],
            changes_to_prescribed_configuration=amended, unrelated_attempts_reopened=False)
        if any(document.get(k) != v for k, v in required.items()) or not document.get('authorization'):
            raise ValueError('exact explicit component recovery authorization required')
        validation = read_json(verify_record(document['repair_validation'])['path'])
        if validation.get('status') != 'passed' or not validation.get('sources'):
            raise ValueError('passing source-bound repair validation required')
        for source in validation['sources']:
            verify_record(source)
        with self.locked() as (stream, events):
            extra = {}
            if amended:
                from .s1_recovery import admitted_event, BINDINGS
                document, _ = validate_binding(self.path.parent, self.config, authorization, events=events)
                extra = {k: document[k] for k in BINDINGS}
                extra['admission'] = admitted_event(events, authorization, document)
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
                original_failure_event_sha256=original['event_sha256'], **extra))

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
        if document.get('schema') in ('vipe-benchmark-e5-packaging-recovery/v1',
                                     'vipe-benchmark-e5-packaging-recovery/v2',
                                     'vipe-benchmark-e5-packaging-recovery/v3',
                                     'vipe-benchmark-e5-packaging-recovery/v4'):
            from .e5_recovery import validate
            with self.locked() as (stream, events):
                document = validate(self.path.parent, self.config, authorization, events)
                if any(e['event'] == 'setup_recovery_authorized' and e['job_id'] == document['job_id'] for e in events):
                    raise ValueError('E5 recovery already allocated; no additional recovery attempt')
                if any(s['event'] == 'reserve' for s in self.states(events).values()):
                    raise ValueError('unreconciled active attempt; refusing E5 recovery allocation')
                if self.totals(events)['setup']['elapsed_seconds'] >= self.config['setup_wall_seconds_limit']:
                    raise ValueError('cumulative setup allocation exhausted')
                return self._append(stream, events, dict(event='setup_recovery_authorized',
                    job_id=document['job_id'], original_job_id='E5-setup', environment='E5',
                    original_failure_event_sha256=document['original_failure_event_sha256'],
                    authorization=authorization, preparation_elapsed_seconds=0.,
                    preparation_evidence=document['repair_validation']))
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
