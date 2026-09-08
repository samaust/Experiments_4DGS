"""Frozen 144-attempt conditioning screen; failures do not block scalar screening."""
import os
import sys
import subprocess
import time
from pathlib import Path
import numpy as np
from basketball_scale import read,write
from basketball_shared_diagnose_v5 import compressed_read,compressed_write
from basketball_shared_profiles_v8 import group_job
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_solver_v3 import objective_agreement

def worker(config,gid,weight,output):
    p=read(config);groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    deadline=p['investigation_started_unix']+4200
    state=group_job((groups[gid],cameras,dict(a=1,b=2),window,10,weight,'v8-condition',p['pilot_lags'],None,deadline))
    for lag,rows in state['attempts'].items():
        transforms={r['transform_sha256'] for r in rows if 'x' in r}
        if len(transforms)!=1:raise ArithmeticError('non-frozen per-problem transform')
    compressed_write(output,dict(group_id=gid,weight=weight,attempts=state['attempts'],problem_key=state['problem_key']))

def condition(p,output,predecessor):
    from basketball_shared_regressions_v8 import conditioning_regressions
    write(output/'derivative-regressions.json',conditioning_regressions())
    tasks=[]
    for w in p['v8']['weights']:
        for gid in p['pilot_groups']:
            artifact=output/f'weight{w}-group{gid:02d}.json.gz'
            tasks.append(dict(group_id=gid,weight=w,artifact=str(artifact),scheduled=24,executed=None))
    write(output/'worker-ledger.json',dict(tasks=tasks))
    children=[subprocess.Popen([sys.executable,__file__,'worker','configs/basketball-rev2/timing-shared-v8.json',str(t['group_id']),str(t['weight']),t['artifact']]) for t in tasks]
    failures=[]
    for child,t in zip(children,tasks):
        code=child.wait()
        if code:failures.append(dict(task=t,exit_code=code))
    if failures:raise ArithmeticError('conditioning worker failed: '+str(failures))
    comparisons=[];ratios=[];recoveries=[];issues=[]
    for t in tasks:
        state=compressed_read(t['artifact']);old=compressed_read(f'docs/experiments/basketball-shared-timing-v6/pilot/weight{t["weight"]}-group{t["group_id"]:02d}.json.gz')
        for lag,rows in state['attempts'].items():
            for row,before in zip(rows,old['attempts'][str(float(lag))]):
                assert row['start']==before['start']
                keep=bool(row['valid'] and (row['objective']<=before['objective'] or objective_agreement(row['objective'],before['objective'])))
                entry=dict(group_id=t['group_id'],weight=t['weight'],lag=float(lag),start=row['start'],old_qualified=before['valid'],new_qualified=row['valid'],preserved=keep,old_objective=before['objective'],new_objective=row.get('objective'),old_KKT=before['optimality'],new_KKT=row.get('optimality'),wall_seconds=row.get('wall_seconds'))
                comparisons.append(entry)
                if not before['valid']:
                    ratios.append(float('inf') if row.get('optimality') is None else row['optimality']/before['optimality'])
                    if row['valid']:recoveries.append(entry)
                if row.get('x'):
                    if row['nfev']>200 or len(row['solver_trace'])>200:raise ArithmeticError('local cap exceeded')
                    from basketball_shared_diagnose_v4 import state_record
                    from basketball_shared_recovery_v8 import fixture
                    problem=fixture(t['group_id'],lag,t['weight'])
                    first=state_record(problem,np.asarray(row['initial_x']),False);last=state_record(problem,np.asarray(row['x']),False)
                    norms=[max(abs(v) for obs in s['observations'] for xyz in obs['normalized_xyz'] for v in xyz) for s in [first,last]]
                    if norms[1]>max(1e6,100*norms[0]):issues.append(dict(reason='observable growth',**entry))
    preserved=sum(r['preserved'] for r in comparisons if r['old_qualified']);median=float(np.median(ratios));groups=sorted({r['group_id'] for r in recoveries})
    passed=preserved==94 and len(recoveries)>=25 and groups==p['pilot_groups'] and median<=.1 and not issues
    write(output/'conditioning-decision.json',dict(passed=passed,scheduled=144,executed=len(comparisons),qualified=sum(r['new_qualified'] for r in comparisons),preserved=preserved,recovered=len(recoveries),recovery_groups=groups,median_failed_KKT_ratio=median if np.isfinite(median) else None,median_infinite=not np.isfinite(median),comparisons=comparisons,issues=issues,inherited_disagreements_retained=True,timing_qualification=False))
    return dict(status='passed' if passed else 'blocked',terminal_kind=None if passed else 'scientific_rejection',blockers=[] if passed else ['conditioning screen failed'],executed_counts=dict(local_attempts=len(comparisons)))

if __name__=='__main__':
    assert sys.argv[1]=='worker'
    worker(Path(sys.argv[2]),int(sys.argv[3]),float(sys.argv[4]),Path(sys.argv[5]))
