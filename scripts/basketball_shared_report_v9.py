"""Terminal packaging of complete, rejected or interrupted Plan 015 stages."""
from pathlib import Path
import json
import time
from collections import Counter
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_shared_benchmark_v9 import event_accounting


def baseline_events(root):
    folder=root/'adapt/baseline';schedule=read(folder/'scheduled.json') if (folder/'scheduled.json').exists() else None
    rows=[];counts=Counter();unique=set();uncertain=False
    for f in sorted(folder.glob('*.events.jsonl')):
        account=event_accounting(f);uncertain|=not account['exact'];events=[]
        for line in f.read_text().splitlines():
            try:events.append(json.loads(line))
            except json.JSONDecodeError:uncertain=True
        for e in events:
            if e['event']=='allocated':
                if e['id'] in unique:raise ArithmeticError('duplicate scheduled attempt identity')
                unique.add(e['id'])
            counts[e['event']]+=1
            if e['event']=='completed':
                counts['executed_reported']+=e['executed'];counts['qualified_reported']+=e['qualified'];counts['missing']+=not e['executed'];counts['states_reported']+=e.get('states',0)
                if e.get('states',0)>200 or e.get('iterations',0)>200:raise ArithmeticError('reported local cap exceeded')
        rows.append(dict(path=str(f),sha256=sha256(f),accounting=account,events=events))
    complete=bool(schedule is not None and counts['allocated']==counts['completed']==schedule['attempts'] and not uncertain)
    return dict(scheduled=None if schedule is None else schedule['attempts'],executed=counts['executed_reported'] if complete else None,
        executed_lower_bound=counts['executed_reported'],missing=counts['missing'] if complete else None,completed_events=counts['completed'],
        event_counts_exact=complete,reported_qualified=counts['qualified_reported'],independently_verifiable_qualified=None,
        reported_distinct_states=counts['states_reported'],independently_reconciled_baseline_states=None,
        retained_full_attempt_records=0,qualification_status='unassessed: detailed state and entry records unavailable',records=rows)


def package(output,prior,predecessor,p):
    root=output.parent;events=baseline_events(root)
    correction=read(root/'corrections/serialization.json') if (root/'corrections/serialization.json').exists() else None
    numerical_stages={}
    for name in ['prepare-resumed','account','diagnose','adapt','benchmark']:
        f=root/name/'result.json'
        if f.exists():numerical_stages[name]=read(f)
    computational=bool(correction and correction['scientific_runs_stopped'])
    arms={name:dict(status='unassessed',scheduled=0,executed=0,qualified=None,reason='baseline full states/ledgers could not be retained; no retries') for name in ['metric','initialization','stopping']}
    write(output/'attempt-events.json',events)
    write(output/'standalone-arm-decisions.json',dict(arms=arms))
    write(output/'final-benchmark-decision.json',dict(status='unassessed',executed=0,qualified=None,ready_for_full_screens=False,reason='no standalone adaptation qualified',full_screens_launched=False))
    write(output/'resources.json',dict(started_unix=p['investigation_started_unix'],elapsed_seconds=time.time()-p['investigation_started_unix'],hard_cap_seconds=5400,
        restart_authorization=str(root/'restart/authorization.json'),absolute_deadlines_minutes=p['v9']['deadlines_minutes'],
        scientific_solves_before_restart=0,baseline=events['executed'],candidate_solves=0,final_benchmark_solves=0,accounting_reproductions=0,numerical_workers_limit=6,CPU_workers_limit=8,numerical_threads=1,gpu_seconds=0,training_seconds=0,
        phase_elapsed_seconds={name:r['elapsed_seconds'] for name,r in numerical_stages.items()},scientific_retries=0))
    kind='computational_blocker' if computational else prior.get('terminal_kind')
    write(output/'terminal-decision.json',dict(status='blocked',terminal_kind=kind,reason=correction['reason'] if computational else prior.get('blockers'),
        accounting='passed_observation_only_checks',saved_state_diagnosis='passed',baseline='unverifiable_full_records_missing',standalone_arms='unassessed',focused_final_benchmark='unassessed',
        ready_for_full_screens=False,accepted_timing=None,production_candidate=None,final_validation_protocol=None,git_commit='blocked_by_approval_review_timeout'))
    return dict(status='blocked',terminal_kind=kind,blockers=['baseline serialization failed; full fitted states and numerical-entry ledgers unavailable; no scientific retries'],
        executed_counts=dict(baseline_scheduled=events['scheduled'],baseline_executed=events['executed'],baseline_missing=events['missing'],baseline_qualified=None,
            baseline_reported_qualified=events['reported_qualified'],candidate_attempts=0,final_benchmark_attempts=0,accounting_reproductions=0))
