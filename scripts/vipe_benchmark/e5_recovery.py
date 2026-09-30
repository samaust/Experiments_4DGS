"""Explicit source-bound E5 recovery identities; REVIEW never grants an attempt."""
from pathlib import Path

from .config import ROOT
from .files import file_record, object_hash, read_json, write_json
from .runtime import TARGETS
from .s1_validation_contract import source_paths, strict_record

SCHEMA = 'vipe-benchmark-e5-packaging-recovery/v1'
JOB = 'E5-setup-recovery-001'
SECOND_JOB = 'E5-setup-recovery-002'
SECOND_SCHEMA = 'vipe-benchmark-e5-packaging-recovery/v2'
THIRD_JOB = 'E5-setup-recovery-003'
THIRD_SCHEMA = 'vipe-benchmark-e5-packaging-recovery/v3'
FOURTH_JOB = 'E5-setup-recovery-004'
FOURTH_SCHEMA = 'vipe-benchmark-e5-packaging-recovery/v4'
JOBS = (JOB, SECOND_JOB, THIRD_JOB, FOURTH_JOB)
SCHEMAS = dict(zip(JOBS, (SCHEMA, SECOND_SCHEMA, THIRD_SCHEMA, FOURTH_SCHEMA)))
PREDECESSORS = {SECOND_JOB: JOB, THIRD_JOB: SECOND_JOB, FOURTH_JOB: THIRD_JOB}
PRESERVED_HISTORY = {THIRD_JOB: (JOB, SECOND_JOB), FOURTH_JOB: (JOB, SECOND_JOB, THIRD_JOB)}
ATTEMPT_SECONDS = 3600.
TARGET = dict(python='3.11', torch='2.5.1+cu124', torchvision='0.20.1+cu124', numpy='1.26.4')


def _assets(local, record):
    from .backends import AssetBundle
    strict_record(record)
    original = Path(local).resolve() / 'jobs/E5-setup'
    if record['path'] != str(original / 'assets-before-build.json'):
        raise ValueError('E5 recovery must reuse the preserved failed setup asset provenance')
    assets = read_json(record['path'])
    AssetBundle('D2', assets)
    for name in ('da3_source', 'da3_snapshot'):
        if not Path(assets[name]['path']).resolve().is_relative_to(original):
            raise ValueError('E5 assets must belong to the original failed setup')
    strict_record(assets['da3_source']['archive'])
    if not Path(assets['da3_source']['archive']['path']).is_relative_to(original):
        raise ValueError('E5 source archive must belong to the failed setup')
    return assets


def _qualification(record):
    strict_record(record)
    checks = read_json(record['path'])
    if checks.get('status') != 'passed' or checks.get('sources') != [file_record(p) for p in source_paths()]:
        raise ValueError('E5 recovery requires passing current complete source qualification')
    for source in checks['sources']:
        strict_record(source)


def _scope(config, job_id=JOB):
    if job_id not in JOBS:
        raise ValueError('only exact E5 recovery identities 001, 002, 003 and 004 are supported')
    from .setup_recipes import recipe
    selected = recipe('E5')
    if TARGETS['E5'] != TARGET or [r for r in selected['requirements'] if r.startswith('editables')] != ['editables~=0.3']:
        raise ValueError('E5 repair must preserve target pins and exact editables dependency')
    if [r for r in selected['requirements'] if r.startswith('xformers')] != ['xformers==0.0.28.post3']:
        raise ValueError('E5 repair must preserve prescribed xFormers')
    return dict(schema=SCHEMAS[job_id], job_id=job_id, original_job_id='E5-setup', environment='E5',
        recovery_attempts_limit=1, setup_wall_seconds_limit=config['setup_wall_seconds_limit'],
        reset_previous_consumption=False, changes_to_prescribed_runtime=False,
        unrelated_attempts_reopened=False, configuration_sha256=object_hash(config),
        recipe=selected, target=TARGET, model_forwards=0, cuda_context_initialization=False)


def _predecessor(ledger, events, job_id):
    if job_id == JOB:
        return None
    predecessor_job = PREDECESSORS[job_id]
    if predecessor_job != JOB:
        _predecessor(ledger, events, predecessor_job)
    registrations = [e for e in events if e['event'] == 'setup_recovery_authorized'
                     and e['job_id'] == predecessor_job and e['environment'] == 'E5']
    previous = ledger.states(events).get(predecessor_job, {})
    if (len(registrations) != 1 or previous.get('event') != 'finish'
            or previous.get('status') != 'failed' or previous.get('cleanup_confirmed') is not True
            or previous.get('cleanup_uncertain') or previous.get('surviving_pids')
            or previous.get('stop_required')):
        raise ValueError(f'{job_id} requires the cleaned-up failed {predecessor_job}')
    strict_record(registrations[0]['authorization'])
    return previous


def propose(local, config, validation, asset_provenance, output, *, job_id=JOB):
    """Publish immutable review evidence without registering or reserving a job."""
    from .ledger import Ledger
    local, output = Path(local).resolve(), Path(output).resolve()
    _qualification(validation)
    _assets(local, asset_provenance)
    scope = _scope(config, job_id)
    ledger = Ledger(local / 'ledger.jsonl', config)
    with ledger.locked() as (_, events):
        failure = ledger.states(events).get('E5-setup', {})
        if (failure.get('event') != 'finish' or failure.get('status') != 'failed'
                or failure.get('cleanup_confirmed') is not True or failure.get('cleanup_uncertain')
                or failure.get('surviving_pids')):
            raise ValueError('E5 recovery requires the original cleaned-up failure')
        if any(e['event'] == 'setup_recovery_authorized' and e['job_id'] == job_id for e in events):
            raise ValueError('E5 recovery already allocated')
        previous = _predecessor(ledger, events, job_id)
        if any(s['event'] == 'reserve' for s in ledger.states(events).values()):
            raise ValueError('unreconciled active attempt; refusing E5 proposal')
        totals = ledger.totals(events)
        remaining = config['setup_wall_seconds_limit'] - totals['setup']['elapsed_seconds']
        if remaining <= 0:
            raise ValueError('cumulative setup allocation exhausted')
        write_json(output / 'ledger-before.json', events)
        document = dict(scope, mode='REVIEW', authorization=None, run_root=str(local),
            repair_validation=validation, asset_provenance=asset_provenance,
            original_failure_event_sha256=failure['event_sha256'],
            ledger_before=file_record(output / 'ledger-before.json'), cumulative_totals=totals,
            attempt_wall_seconds_limit=min(ATTEMPT_SECONDS, remaining))
        if previous is not None:
            document.update(previous_job_id=previous['job_id'], previous_failure_event_sha256=previous['event_sha256'])
        if job_id in PRESERVED_HISTORY:
            document['preserved_recovery_failures'] = [dict(job_id=j, event_sha256=ledger.states(events)[j]['event_sha256'])
                for j in PRESERVED_HISTORY[job_id]]
        write_json(output / 'review.json', document)
        return file_record(output / 'review.json')


def approve(review, approval, output):
    """Bind the explicit human instruction to the exact reviewed document."""
    strict_record(review)
    document = read_json(review['path'])
    if document.get('schema') not in tuple(SCHEMAS.values()) or document.get('mode') != 'REVIEW' or not isinstance(approval, str) or not approval.strip():
        raise ValueError('E5 recovery requires an exact REVIEW and explicit DO approval')
    write_json(output, dict(document, mode='DO', authorization=approval, reviewed_proposal=review))
    return file_record(output)


def validate(local, config, authorization, events):
    """Validate both approval and its original evidence before checked transitions."""
    from .ledger import Ledger
    strict_record(authorization)
    document = read_json(authorization['path'])
    if document.get('mode') != 'DO' or not isinstance(document.get('authorization'), str) or not document['authorization'].strip():
        raise ValueError('E5 recovery requires explicit DO approval; REVIEW cannot allocate')
    review = read_json(strict_record(document['reviewed_proposal'])['path'])
    if review.get('mode') != 'REVIEW' or review.get('authorization') is not None or document != dict(
            review, mode='DO', authorization=document['authorization'], reviewed_proposal=document['reviewed_proposal']):
        raise ValueError('E5 approval differs from the immutable reviewed proposal')
    if review.get('run_root') != str(Path(local).resolve()) or any(review.get(k) != v for k, v in _scope(config, review.get('job_id')).items()):
        raise ValueError('E5 recovery changes reviewed scope or recipe')
    _qualification(review['repair_validation'])
    _assets(local, review['asset_provenance'])
    baseline = read_json(strict_record(review['ledger_before'])['path'])
    ledger = Ledger(Path(local) / 'ledger.jsonl', config)
    if not baseline or events[:len(baseline)] != baseline or review.get('cumulative_totals') != ledger.totals(baseline):
        raise ValueError('E5 recovery must preserve the reviewed ledger prefix and charges')
    failure = ledger.states(events).get('E5-setup', {})
    if (failure.get('event') != 'finish' or failure.get('status') != 'failed'
            or failure.get('cleanup_confirmed') is not True or failure.get('cleanup_uncertain')
            or failure.get('surviving_pids') or failure.get('event_sha256') != review.get('original_failure_event_sha256')):
        raise ValueError('E5 recovery requires the preserved cleaned-up failure')
    previous = _predecessor(ledger, baseline, review['job_id'])
    if previous is not None and ledger.states(events).get(previous['job_id']) != previous:
        raise ValueError('E5 recovery predecessor changed after REVIEW')
    if previous is not None and (review.get('previous_job_id') != previous['job_id'] or
            review.get('previous_failure_event_sha256') != previous['event_sha256']):
        raise ValueError('E5 recovery must bind the preserved predecessor failure')
    if review['job_id'] in PRESERVED_HISTORY and any(ledger.states(events).get(j) != ledger.states(baseline).get(j)
                                           for j in PRESERVED_HISTORY[review['job_id']]):
        raise ValueError('E5 recovery prior failure history changed after REVIEW')
    if review['job_id'] in PRESERVED_HISTORY and review.get('preserved_recovery_failures') != [
            dict(job_id=j, event_sha256=ledger.states(baseline)[j]['event_sha256']) for j in PRESERVED_HISTORY[review['job_id']]]:
        raise ValueError('E5 recovery must preserve all reviewed prior recovery failures')
    remaining = config['setup_wall_seconds_limit'] - ledger.totals(baseline)['setup']['elapsed_seconds']
    if type(review.get('attempt_wall_seconds_limit')) not in (float, int) or review['attempt_wall_seconds_limit'] != min(ATTEMPT_SECONDS, remaining) or remaining <= 0:
        raise ValueError('E5 recovery requires the reviewed bounded setup allocation')
    return document


def reservation_binding(local, config, events, command, evidence, *, job_id=JOB):
    """Only the reviewed setup request and canonical worker may spend E5's attempt."""
    from .setup_recipes import request as setup_request
    registered = [e for e in events if e['event'] == 'setup_recovery_authorized'
                  and e['job_id'] == job_id and e['environment'] == 'E5']
    if len(registered) != 1:
        raise ValueError('unique E5 recovery registration required')
    authorization = registered[0]['authorization']
    document = validate(local, config, authorization, events)
    assets = _assets(local, document['asset_provenance'])
    configuration = file_record(ROOT / 'configs/vipe-alternatives/benchmark-v1.json')
    expected = dict(setup_request(local, 'E5'), job_id=job_id,
        recovery_authorization=authorization, reuse_assets={'da3_snapshot': assets['da3_snapshot']},
        reuse_source_archives={'da3_source': assets['da3_source']['archive']}, configuration=configuration)
    request_path = str((Path(local).resolve() / 'requests' / (job_id + '.json')).resolve())
    worker = file_record(ROOT / 'scripts/basketball_vipe_worker.py')
    if type(evidence) is not dict or set(evidence) != {'request', 'worker'}:
        raise ValueError('canonical E5 reservation evidence required')
    request = strict_record(evidence['request'])
    if (request['path'] != request_path or read_json(request['path']) != expected
            or evidence['worker'] != worker):
        raise ValueError('canonical E5 recovery request/path/worker changed')
    expected_command = [str(ROOT / '.local/envs/stg-colmap/bin/python'), worker['path'],
        '--operation', 'setup', '--config', configuration['path'], '--request', request_path,
        '--output', str((Path(local).resolve() / 'jobs' / job_id).resolve())]
    if command != expected_command:
        raise ValueError('canonical E5 recovery command changed')
    return document
