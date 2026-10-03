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
            if event['event'] == 'depth_attempt_authorized':
                for key in ('review', 'authorization', 'source_review', 'admission'):
                    verify_record(event[key])
                candidate = event['candidate']
                job_id = f'plan069-{candidate}-maps-001'
                allocated[job_id] = dict(id=job_id, resource='gpu',
                    seconds=event['seconds'],
                    scope='approved one-attempt Plan 069 native depth inference')
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
            if job_id in states:
                raise ValueError('job already consumed or accounted for; no automatic retry')
            if any(r['event'] == 'reserve' for r in states.values()):
                raise ValueError('unreconciled active attempt; refusing concurrent dispatch')
            if re.fullmatch(r'plan069-(D2|D5|D6|D7|D8|D9|D10|D11)-maps-001', job_id):
                candidate = job_id.split('-')[1]
                authorized = [row for row in events if
                    row['event'] == 'depth_attempt_authorized' and
                    row['candidate'] == candidate]
                if len(authorized) != 1 or events[-1] != authorized[0] or \
                        time.time() - authorized[0]['recorded_unix'] > 30:
                    raise ValueError('fresh exact depth authorization required')
                bound = authorized[0]
                from .depth_admission import local_source_records
                source = read_json(verify_record(bound['source_review'])['path'])
                if source.get('local_sources') != local_source_records(candidate):
                    raise ValueError('depth sources changed after review')
                if not isinstance(evidence, dict) or any(
                        evidence.get(key) != bound[key] for key in
                        ('review', 'authorization', 'source_review', 'admission')):
                    raise ValueError('depth reservation evidence differs from authorization')
                if command != bound.get('command') or any(evidence.get(key) != bound.get(key)
                        for key in ('request', 'worker', 'executable')):
                    raise ValueError('depth command differs from authorization')
                self._depth_command(candidate, bound, source, evidence, command)
            if is_recovery_job(job_id):
                from .s1_recovery import reservation_binding
                reservation_binding(self.path.parent, self.config, events, evidence, command=command)
            if job_id in ('E5-setup-recovery-001', 'E5-setup-recovery-002', 'E5-setup-recovery-003', 'E5-setup-recovery-004'):
                from .e5_recovery import reservation_binding
                reservation_binding(self.path.parent, self.config, events, command, evidence, job_id=job_id)
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

    def authorize_depth_setup(self, candidate, review, authorization, source_review):
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
            if self.totals(events)['setup']['elapsed_seconds'] + seconds > self.config['setup_wall_seconds_limit']:
                raise ValueError('setup allocation exceeds cumulative cap')
            from .execution import resources
            reading = resources(self.path.parent)
            for key, limit in (('download_bytes', 'new_download_gib_limit'),
                               ('artifact_bytes', 'new_artifact_disk_gib_limit')):
                if reading[key] + proposal['allocation'][key] > self.config[limit] * 2**30:
                    raise ValueError(key + ' setup allocation exceeds live cumulative cap')
            return self._append(stream, events, dict(event='depth_setup_authorized',
                candidate=candidate, seconds=seconds,
                proposal_sha256=object_hash(proposal), review=review,
                authorization=authorization, source_review=source_review,
                resource_snapshot=reading))

    def _depth_command(self, candidate, bound, source, evidence, command):
        """Rehash the exact authorized worker, interpreter and immutable request."""
        job_id = f'plan069-{candidate}-maps-001'
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
        self._depth_command(candidate, dict(review=review, authorization=authorization,
            source_review=source_review, admission=admission), source, binding, command)
        seconds = proposal.get('allocation', {}).get('gpu_seconds')
        if type(seconds) is not int or seconds <= 0:
            raise ValueError('bounded depth GPU seconds required')
        with self.locked() as (stream, events):
            states = self.states(events)
            job_id = f'plan069-{candidate}-maps-001'
            if job_id in states or any(row['event'] == 'depth_attempt_authorized' and
                                       row['candidate'] == candidate for row in events):
                raise ValueError('depth model attempt already authorized or consumed')
            if any(row['event'] == 'reserve' for row in states.values()):
                raise ValueError('active attempt prevents depth GPU allocation')
            if any(row['event'] == 'depth_attempt_authorized' and
                   f"plan069-{row['candidate']}-maps-001" not in states for row in events):
                raise ValueError('unstarted depth GPU allocation prevents another')
            head = events[-1]['event_sha256'] if events else '0' * 64
            live = evidence.get('live', {})
            if live.get('ledger_head_sha256') != head:
                raise ValueError('depth admission ledger head is stale')
            if candidate in ('D5','D6','D8','D9','D10','D11') and evidence.get('completed_setup') is None:
                raise ValueError('new native slot requires completed setup stage proof')
            from .depth_admission import BENCHMARK, CAP_AMENDMENT
            historical = read_json(BENCHMARK)
            cap_amendment = file_record(CAP_AMENDMENT) if self.config != historical else None
            blockers = decide(proposal, config=self.config,
                commercial=evidence['commercial'], assets=evidence['assets'],
                runtime=evidence['runtime'], live=live,
                source_review=source_review, approval=grant,
                cap_amendment=cap_amendment,
                cap_approval=approved.get('cap_approval'),
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
                command=command, **binding))

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
