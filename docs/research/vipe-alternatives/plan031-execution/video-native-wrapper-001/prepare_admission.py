"""Publish fresh D9-owned CPU admission; no ledger writes, tests or models."""
import argparse
import fcntl
import hashlib
import json
import subprocess
import time
import signal
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
    def deadline(signum, frame):
        raise TimeoutError('CPU admission preparation ten-second deadline')
    signal.signal(signal.SIGALRM, deadline)
    signal.setitimer(signal.ITIMER_REAL, 10)
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('checkout', 'run', 'output', 'source-review', 'setup', 'cpu-qualification'):
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
    review = read(root / 'docs/specs/plan031-execution/depth-execution-review-002.json')
    approved_cpu = next(row['allocation']['cpu_seconds'] for row in review['proposals'] if row['candidate'] == 'D9')
    candidate_limit = 1800  # Root's narrower prospective D9 accounting envelope.
    if approved_cpu < candidate_limit or config['cpu_prepare_score_report_seconds_limit'] != 57600:
        raise ValueError('approved CPU limits do not cover admission')
    source_record = record(args.source_review)
    source = read(args.source_review)
    helpers = source.get('local_sources', source.get('local_source_records'))
    if source.get('candidate') != 'D9' or source.get('status') != 'passed' or not isinstance(helpers, list) or not helpers or len({row['path'] for row in helpers}) != len(helpers):
        raise ValueError('passed exact declared D9 helper review required')
    supplemental_key = 'supplemental_sources' if 'supplemental_sources' in source else 'supplemental_cpu_sources'
    if 'supplemental_sources' in source and 'supplemental_cpu_sources' in source and source['supplemental_sources'] != source['supplemental_cpu_sources']:
        raise ValueError('ambiguous supplemental source list')
    supplemental = source.get(supplemental_key, [])
    if not isinstance(supplemental, list) or len({row['path'] for row in supplemental}) != len(supplemental):
        raise ValueError('invalid supplemental source list')
    for helper in helpers + supplemental + source.get('changed_tracked_python_sources', []):
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
    clarification_path = root / '.local/D9-frame-recovery-outcome-001/accounting-owner-clarification.json'
    clarification = read(clarification_path)
    if clarification.get('charged_sequence') != 785 or clarification.get('cpu_accounting_owner') != 'D9':
        raise ValueError('unexpected accounting owner clarification')
    parent_charge = events[785]
    if parent_charge['event'] != 'cpu_preparation_charge' or parent_charge['evidence'] != clarification['evidence'] or parent_charge['elapsed_seconds'] != clarification['elapsed_seconds']:
        raise ValueError('clarification does not bind exact existing charge785')
    if record(clarification['evidence']['path']) != clarification['evidence'] or read(clarification['evidence']['path']).get('cpu_preparation_owner') != 'D9':
        raise ValueError('immutable owner alias evidence differs')
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
        if event['sequence'] == 785:
            owner = 'D9'
        if owner == 'D9':
            if record(path) != event['evidence']:
                raise ValueError('changed D9 CPU charge evidence')
            attributed.append(dict(sequence=event['sequence'], seconds=event['elapsed_seconds'], evidence=event['evidence']))
    candidate_used = sum(row['seconds'] for row in attributed)
    global_used = sum(event['elapsed_seconds'] for event in events if event['event'] == 'cpu_preparation_charge' or event['event'] in ('finish', 'checkpoint') and event['resource'] == 'cpu')
    bounds = dict(capture_seconds=180, preparation_reserve_seconds=20)
    needed = sum(bounds.values())
    if candidate_used + needed > candidate_limit or global_used + needed > config['cpu_prepare_score_report_seconds_limit']:
        raise ValueError('candidate/global CPU allocation exhausted')
    if guarded(ledger).read_bytes() != raw or git('rev-parse', 'HEAD').strip() != head or git('status', '--porcelain', '--untracked-files=no').strip():
        raise ValueError('ledger or checkout changed during admission')
    out.mkdir(parents=True, exist_ok=False)
    with (out / 'effective-config.json').open('x') as stream:
        json.dump(config, stream, indent=2)
        stream.write('\n')
    admission = dict(schema='plan069-video-native-cpu-admission/v1', candidate='D9', cpu_accounting_owner='D9', source_component='D9', source_head=head, source_review=source_record, setup=record(args.setup), cpu_qualification=record(args.cpu_qualification), seconds=180, candidate_cpu_allocation_seconds=candidate_limit, broader_review_cpu_seconds=approved_cpu, purpose='Bounded D9 accepted002 two strict CPU model loads; no inference/GPU/download', ledger_head_sequence=events[-1]['sequence'], ledger_head_sha256=previous, ledger_event_count=len(events), candidate_cpu_elapsed_seconds=candidate_used, candidate_cpu_remaining_seconds=candidate_limit-candidate_used, D9_attribution_rows=attributed, immutable_owner_alias_clarification=record(clarification_path), global_cpu_elapsed_seconds=global_used, global_cpu_remaining_seconds=config['cpu_prepare_score_report_seconds_limit']-global_used, prospective_bounds=bounds, candidate_remaining_after_prospective_bounds_seconds=candidate_limit-candidate_used-needed, global_remaining_after_prospective_bounds_seconds=config['cpu_prepare_score_report_seconds_limit']-global_used-needed, configuration=record(config_path), effective_configuration=record(out/'effective-config.json'), no_ledger_mutation=True, elapsed_seconds=time.monotonic()-began)
    with (out/'admission.json').open('x') as stream:
        json.dump(admission, stream, indent=2)
        stream.write('\n')
    signal.setitimer(signal.ITIMER_REAL, 0)
    print(json.dumps(dict(admission=str(out/'admission.json'), candidate_remaining=admission['candidate_cpu_remaining_seconds'], head=head)))


if __name__ == '__main__':
    main()
