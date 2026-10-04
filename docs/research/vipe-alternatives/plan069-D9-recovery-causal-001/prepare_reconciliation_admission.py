"""Prepare fresh D9 recovery reconciliation CPU admission; no ledger writes or models."""
import argparse
import fcntl
import hashlib
import json
import subprocess
import time
from pathlib import Path


def guarded(path):
    path = Path(path).absolute()
    if 'prompts' in path.parts or 'prompts' in path.resolve().parts:
        raise ValueError('forbidden prompts path')
    return path


def record(path):
    path = guarded(path)
    data = path.read_bytes()
    return dict(path=str(path), sha256=hashlib.sha256(data).hexdigest(), bytes=len(data))


def read(path):
    return json.loads(guarded(path).read_text())


def main():
    began = time.monotonic()
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('checkout', 'run', 'output', 'source-review'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    root, run, out = (guarded(value).resolve() for value in (args.checkout, args.run, args.output))
    if out.exists():
        raise ValueError('admission output must be fresh')
    git = lambda *words: subprocess.check_output(['git', *words], cwd=root, text=True)
    head = git('rev-parse', 'HEAD').strip()
    if git('status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('tracked final checkout must be clean')
    config_path = root / 'configs/vipe-alternatives/benchmark-v1.json'
    config = dict(read(config_path), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    candidate_limit = 1800  # Root's narrower prospective D9 accounting envelope.
    if config['cpu_prepare_score_report_seconds_limit'] != 57600:
        raise ValueError('approved CPU limits do not cover admission')
    source_record = record(args.source_review)
    source = read(args.source_review)
    helpers = source.get('local_sources', source.get('local_source_records'))
    if source.get('status') != 'passed' or source.get('candidate') != 'D9' or not isinstance(helpers, list) or not helpers or len({row['path'] for row in helpers}) != len(helpers):
        raise ValueError('exact declared D9 recovery helper review required')
    for helper in helpers:
        if record(helper['path']) != helper:
            raise ValueError('changed reviewed helper')
    ledger = guarded(run / 'ledger.jsonl')
    with ledger.open('rb') as stream:
        fcntl.flock(stream, fcntl.LOCK_SH)
        raw = stream.read()
        fcntl.flock(stream, fcntl.LOCK_UN)
    events = [json.loads(line) for line in raw.splitlines()]
    previous = None
    states = {}
    for index, event in enumerate(events):
        body = {key: value for key, value in event.items() if key != 'event_sha256'}
        hashed = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()
        if event['sequence'] != index or event['previous_sha256'] != previous or event['event_sha256'] != hashed:
            raise ValueError('ledger corruption')
        previous = hashed
        if event['event'] in ('reserve', 'finish', 'account', 'checkpoint'):
            states[event['job_id']] = event
        elif event['event'] == 'checkpoint_resume':
            states[event['job_id']] = dict(event, event='reserve')
        elif event['event'] == 'resume_unstarted':
            for job in event['job_ids']:
                states.pop(job, None)
    if any(row['event'] == 'reserve' for row in states.values()):
        raise ValueError('active reservation prevents CPU capture')
    originals = [row for row in events if row.get('event') == 'depth_setup_authorized' and row.get('candidate') == 'D9']
    if len(originals) != 1 or record(originals[0]['review']['path']) != originals[0]['review']:
        raise ValueError('exact original approved allocation required')
    original_review = read(originals[0]['review']['path'])
    proposals = [row for row in original_review['proposals'] if row['candidate'] == 'D9']
    if len(proposals) != 1:
        raise ValueError('unique original D9 proposal required')
    approved_cpu = proposals[0]['allocation']['cpu_seconds']
    if approved_cpu < candidate_limit:
        raise ValueError('unchanged approved candidate CPU allowance required')
    recovery_job = 'plan069-D9-setup-recovery-001'
    grants = [row for row in events if row.get('event') == 'depth_setup_recovery_authorized' and row.get('job_id') == recovery_job]
    finishes = [row for row in events if row.get('event') == 'finish' and row.get('job_id') == recovery_job]
    if len(grants) != 1 or len(finishes) != 1:
        raise ValueError('accepted approved recovery required before reconciliation admission')
    grant, finish = grants[0], finishes[0]
    if not (grant['sequence'] < finish['sequence'] and finish.get('status') == 'complete' and finish.get('cleanup_confirmed') is True and finish.get('cleanup_uncertain') is False and finish.get('surviving_pids') == [] and finish.get('deadline_exceeded') is False and finish.get('resource') == 'setup'):
        raise ValueError('clean accepted recovery required')
    if grant.get('source_review') != source_record or record(finish['result']['path']) != finish['result']:
        raise ValueError('accepted recovery must bind exact current source review/result')
    result = read(finish['result']['path'])
    if result.get('schema') != 'plan069-video-setup-recovery-result/v1' or result.get('status') != 'complete' or result.get('record_kind') != 'actual' or result.get('candidate') != 'D9' or result.get('request') != grant.get('request') or result.get('source_review') != source_record:
        raise ValueError('actual reviewed accepted recovery required')
    if any(row.get('event') == 'depth_setup_bytes_reconciled' and row.get('candidate') == 'D9' for row in events):
        raise ValueError('D9 reconciliation already protected')
    attributed = []
    for event in events:
        if event['event'] != 'cpu_preparation_charge':
            continue
        path = guarded(event['evidence']['path'])
        # These exact historical metadata scopes are shared video preparation;
        # root conservatively attributes each entirely to D9, never to D6.
        owner = 'D9' if event['sequence'] in (707, 713) else None
        if event['sequence'] > 754 and path.suffix == '.json':
            doc = read(path)
            declared = doc.get('cpu_accounting_owner')
            if declared is None and doc.get('candidate') == 'D9':
                declared = 'D9'
            if declared == 'D9':
                owner = 'D9'
            elif declared in ('D6', 'D10'):
                owner = None
        if owner == 'D9':
            if record(path) != event['evidence']:
                raise ValueError('changed D9 CPU charge evidence')
            attributed.append(dict(sequence=event['sequence'], seconds=event['elapsed_seconds'], evidence=event['evidence']))
    candidate_used = sum(row['seconds'] for row in attributed)
    global_used = sum(event['elapsed_seconds'] for event in events if event['event'] == 'cpu_preparation_charge' or event['event'] in ('finish', 'checkpoint') and event['resource'] == 'cpu')
    bounds = dict(reconciliation_seconds=120, preparation_reserve_seconds=10, qualification_headroom_seconds=180, maps_headroom_seconds=160)
    needed = sum(bounds.values())
    if candidate_used + needed > candidate_limit or global_used + needed > config['cpu_prepare_score_report_seconds_limit']:
        raise ValueError('candidate/global CPU allocation exhausted')
    if guarded(ledger).read_bytes() != raw or git('rev-parse', 'HEAD').strip() != head or git('status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('ledger or checkout changed during admission')
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'effective-config.json').open('x') as stream:
        json.dump(config, stream, indent=2)
        stream.write('\n')
    admission = dict(schema='plan069-root-cpu-fixture-admission/v1', candidate='D9', cpu_accounting_owner='D9', source_component='D9', source_head=head, source_review=source_record, seconds=120, candidate_cpu_allocation_seconds=candidate_limit, broader_review_cpu_seconds=approved_cpu, purpose='Reconcile accepted D9 recovery retained bytes; no model/GPU/native authority', ledger_head_sequence=events[-1]['sequence'], ledger_head_sha256=previous, ledger_event_count=len(events), candidate_cpu_elapsed_seconds=candidate_used, candidate_cpu_remaining_seconds=candidate_limit-candidate_used, D9_attribution_rows=attributed, global_cpu_elapsed_seconds=global_used, global_cpu_remaining_seconds=config['cpu_prepare_score_report_seconds_limit']-global_used, prospective_bounds=bounds, candidate_remaining_after_prospective_bounds_seconds=candidate_limit-candidate_used-needed, global_remaining_after_prospective_bounds_seconds=config['cpu_prepare_score_report_seconds_limit']-global_used-needed, configuration=record(config_path), effective_configuration=record(out/'effective-config.json'), no_ledger_mutation=True, elapsed_seconds=time.monotonic()-began)
    with (out/'admission.json').open('x') as stream:
        json.dump(admission, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(admission=str(out/'admission.json'), candidate_remaining=admission['candidate_cpu_remaining_seconds'], head=head)))


if __name__ == '__main__':
    main()
