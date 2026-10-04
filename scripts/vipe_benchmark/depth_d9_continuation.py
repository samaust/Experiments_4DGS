"""Extra current-evidence gate for the single protected, unstarted D9 grant.

The immutable request, command, admission and byte accounting remain the original
allocation's bindings. This module neither allocates a job nor reopens a state.
"""
from pathlib import Path
import time

from .files import digest, object_hash, read_json, verify_record

JOB = 'plan069-D9-maps-001'
EVENT = 'depth_d9_attempt_continued'
SCHEMA = 'plan069-D9-unstarted-continuation/v1'
GRANT_SHA256 = '4a65c3191857d999f1134bc98446aff435edfa9e5486252b9b44383235e250b6'


def original_grant(events):
    grants = [row for row in events if row.get('event') == 'depth_attempt_authorized'
              and row.get('candidate') == 'D9']
    if (len(grants) != 1 or grants[0].get('sequence') != 851 or
            grants[0].get('event_sha256') != GRANT_SHA256):
        raise ValueError('exact immutable original grant851 required')
    grant = grants[0]
    unhashed = {key: value for key, value in grant.items() if key != 'event_sha256'}
    if object_hash(unhashed) != GRANT_SHA256:
        raise ValueError('original grant851 content changed')
    return grant


def _require(condition, reason):
    if not condition:
        raise ValueError(reason)


def _cpu_capture(record, current_sources):
    _require(verify_record(record) == record, 'CPU capture record changed')
    cpu = read_json(record['path'])
    schemas = ('plan069-integrated-cpu-test-capture/v1', 'plan069-delta-cpu-test-capture/v1')
    before, after = cpu.get('sources_before'), cpu.get('sources_after')
    _require(cpu.get('schema') in schemas and cpu.get('record_kind') == 'actual' and
             cpu.get('passed') is True and cpu.get('within_wall_limit') is True and
             cpu.get('source_bytes_unchanged') is True and
             cpu.get('environment_bytes_unchanged') is True and
             cpu.get('head_unchanged') is True and cpu.get('head') == cpu.get('head_after') and
             isinstance(before, list) and before == after and
             all(source in before for source in current_sources),
             'passing physical CPU capture with unchanged current D9 sources required')
    for source in current_sources:
        _require(verify_record(source) == source, 'CPU-qualified D9 source changed')
    commands = cpu.get('commands')
    _require(isinstance(commands, list) and bool(commands), 'physical CPU commands required')
    for command in commands:
        cleanup = command.get('cleanup', {})
        _require(command.get('returncode') == 0 and command.get('timed_out') is False and
                 cleanup.get('confirmed_no_surviving_observed_processes') is True and
                 cleanup.get('surviving_observed_owned_processes') == [] and
                 isinstance(command.get('command'), list) and bool(command['command']) and
                 digest(command['log']) == command.get('log_sha256'),
                 'successful hash-bound CPU command log and cleanup required')
    _require(any('unittest' in command['command'] or 'pytest' in command['command']
                 for command in commands), 'CPU test command required')
    return cpu


def validate_request(record, events, config, run_root, *, historical=False):
    """Read-only validation against the unstarted prefix, never a reservation."""
    entered_unix = time.time()
    grant = original_grant(events)
    _require(not any(row.get('job_id') == JOB and row.get('event') in
                     ('reserve', 'start', 'finish', 'account', EVENT) for row in events),
             'continuation requires the same unstarted allocation')
    root = Path(run_root).resolve()
    if not historical:
        _require(not (root / 'jobs' / JOB).exists() and
                 not (root / 'jobs' / JOB).is_symlink(),
                 'unstarted continuation cannot reuse existing worker output')
    _require(not any(row.get('event') == 'reserve' and not any(
        end.get('job_id') == row.get('job_id') and end.get('event') in ('finish', 'account')
        and end['sequence'] > row['sequence'] for end in events) for row in events),
        'active attempt prevents continuation')
    _require(verify_record(record) == record, 'continuation file record changed')
    document = read_json(record['path'])
    required = dict(schema=SCHEMA, candidate='D9', job_id=JOB,
        original_grant_sha256=GRANT_SHA256, original_request=grant['request'],
        command=grant['command'], config_sha256=object_hash(config),
        ledger_head_sha256=events[-1]['event_sha256'], new_allocations=0,
        reset_previous_consumption=False)
    _require(all(document.get(key) == value for key, value in required.items()),
             'exact unchanged continuation identity/command/configuration required')
    for key in ('review', 'authorization', 'source_review', 'admission',
                'request', 'worker', 'executable'):
        _require(verify_record(grant[key]) == grant[key], 'original grant evidence changed: ' + key)
    request = read_json(grant['request']['path'])
    _require(request.get('candidate') == 'D9' and request.get('job_id') == JOB and
             request.get('record_kind') == 'actual' and
             Path(request['ledger_path']).resolve() == root / 'ledger.jsonl' and
             grant['command'][3] == grant['request']['path'] and
             grant['command'][-1] == str(root / 'jobs' / JOB) and
             all(request.get(key) == grant[key] for key in
                 ('review', 'authorization', 'source_review', 'admission')),
             'immutable original actual request differs from grant851')
    admitted_record = document.get('admission')
    source_record = document.get('source_review')
    admitted = read_json(verify_record(admitted_record)['path'])
    reviewed = read_json(grant['review']['path'])
    approved = read_json(grant['authorization']['path'])
    proposal = next(row for row in reviewed['proposals'] if row['candidate'] == 'D9')
    approval = next(row for row in approved['candidate_approvals'] if row['candidate'] == 'D9')
    _require(object_hash(proposal) == grant['proposal_sha256'] and
             proposal.get('max_attempts') == 1 and grant['seconds'] ==
             request.get('max_seconds') == proposal['allocation']['gpu_seconds'] and
             approved.get('schema') == 'plan069-depth-user-authorization/v1' and
             approved.get('status') == 'DO' and approved.get('review') == grant['review'] and
             admitted.get('schema') == 'plan069-depth-admission-result/v1' and
             admitted.get('status') == 'passed' and admitted.get('candidate') == 'D9' and
             admitted.get('proposal_sha256') == grant['proposal_sha256'] and
             admitted.get('source_review') == source_record and
             admitted.get('completed_setup') == request['setup'] and
             all(admitted.get(key) == grant[key] for key in ('review', 'authorization')) and
             admitted.get('live', {}).get('ledger_head_sha256') == document['ledger_head_sha256'],
             'passing current admission for unchanged approved proposal required')
    from .depth_admission import local_source_records, review as admit
    from .video_depth import validate_runtime_interpreter
    from basketball_vipe_video_actual_dispatch import _qualified_sources
    _qualified_sources('D9', proposal, admitted, source_record, request['setup'],
        grant['review'], grant['authorization'], events=events, run_root=root)
    validate_runtime_interpreter(admitted['runtime'], grant['command'][0],
                                 executable_record=grant['executable'])
    current = local_source_records('D9')
    _cpu_capture(document.get('cpu_validation'), current)
    mypy = _cpu_capture(document.get('mypy_validation'), current)
    _require(any('mypy' in command['command'] for command in mypy['commands']),
             'physical scoped mypy command required')
    from .depth_recovery_lineage import recovery_cap_authorization
    caps = recovery_cap_authorization(proposal, grant['authorization'], request['setup'], events, root)
    _require(caps is not None, 'unchanged approved recovery caps required')
    live = admitted['live']
    blockers = admit(proposal, config=config, commercial=admitted['commercial'],
        assets=admitted['assets'], runtime=admitted['runtime'], live=live,
        source_review=source_record, approval=approval, cap_amendment=caps[0],
        cap_approval=caps[1], ledger_head_sha256=document['ledger_head_sha256'],
        now_unix=live['sampled_unix'] if historical else entered_unix,
        completed_setup=request['setup'], setup_events=events, run_root=root)
    _require(not blockers, 'current continuation admission failed: ' + '; '.join(blockers))
    return document, grant


def protected_continuation(events, config, run_root, *, phase):
    """Recheck additional evidence at reserve, worker, finish and publication."""
    rows = [row for row in events if row.get('event') == EVENT]
    if not rows:
        return None
    _require(len(rows) == 1, 'unique protected D9 continuation required')
    event = rows[0]
    index = events.index(event)
    if phase == 'reserve':
        root = Path(run_root).resolve()
        _require(events[-1] == event and
                 0 <= time.time() - event['recorded_unix'] <= 30 and
                 not (root / 'jobs' / JOB).exists() and not (root / 'jobs' / JOB).is_symlink(),
                 'fresh latest unstarted continuation required')
    document, grant = validate_request(event['request'], events[:index], config,
        run_root, historical=True)
    _require(event.get('job_id') == JOB and event.get('candidate') == 'D9',
             'protected continuation identity changed')
    attempts = [row for row in events if row.get('job_id') == JOB and
                row.get('event') in ('reserve', 'start', 'finish', 'account')]
    if phase == 'reserve':
        _require(not attempts,
                 'fresh latest unstarted continuation required')
    else:
        reservations = [row for row in attempts if row['event'] == 'reserve']
        finishes = [row for row in attempts if row['event'] == 'finish']
        _require(len(reservations) == 1 and reservations[0]['sequence'] > event['sequence'] and
                 reservations[0].get('command') == grant['command'] and
                 reservations[0].get('resource') == 'gpu' and
                 reservations[0].get('seconds', 10**30) <= grant['seconds'] and
                 reservations[0].get('evidence') == dict(
                     **{key: grant[key] for key in ('review', 'authorization', 'source_review',
                        'admission', 'request', 'worker', 'executable')}, continuation=event['request']) and
                 not any(row['event'] in ('start', 'account') for row in attempts),
                 'exact single continued reservation required')
        if phase in ('worker', 'finish'):
            _require(not finishes, 'continued worker attempt already finished')
        elif phase == 'publish':
            _require(len(finishes) == 1 and finishes[0]['sequence'] > reservations[0]['sequence'] and
                     finishes[0].get('status') == 'complete' and
                     finishes[0].get('cleanup_confirmed') is True and
                     finishes[0].get('cleanup_uncertain') is False and
                     finishes[0].get('surviving_pids') == [] and
                     finishes[0].get('deadline_exceeded') is False,
                     'clean complete continued attempt required before publication')
        else:
            raise ValueError('unknown continuation boundary')
    return event


def active_phase_evidence(events, reservation):
    """Select extra protected source/runtime proof without altering slot lineage.

    Full CPU/admission validation runs at worker entry and completion. Accepted
    recovery ancestry uses this selector to rehash the same immutable phase
    records while preserving the original admission for allocation accounting.
    """
    rows = [row for row in events if row.get('event') == EVENT]
    if not rows:
        return None
    _require(len(rows) == 1, 'unique protected continuation phase required')
    event = rows[0]
    grant = original_grant(events)
    record = event['request']
    _require(verify_record(record) == record and
             reservation.get('job_id') == JOB and reservation.get('resource') == 'gpu' and
             reservation.get('command') == grant['command'] and
             reservation.get('evidence', {}).get('continuation') == record and
             grant['sequence'] < event['sequence'] < reservation['sequence'],
             'active protected continuation phase binding changed')
    document = read_json(record['path'])
    _require(document.get('schema') == SCHEMA and document.get('job_id') == JOB and
             document.get('original_grant_sha256') == GRANT_SHA256 and
             document.get('original_request') == grant['request'] and
             document.get('command') == grant['command'] and
             document.get('ledger_head_sha256') == event.get('previous_sha256'),
             'unchanged protected phase evidence required')
    admission = read_json(verify_record(document['admission'])['path'])
    _require(admission.get('source_review') == document.get('source_review') and
             all(admission.get(key) == grant[key] for key in ('review', 'authorization')) and
             admission.get('proposal_sha256') == grant['proposal_sha256'],
             'current continuation phase authority changed')
    return document['source_review'], admission
