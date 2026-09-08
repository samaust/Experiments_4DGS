"""Independent scalar camera-3 profiles; historical states never select grid points."""
import hashlib
import json
import sys
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import numpy as np
from basketball_scale import read,write
from basketball_shared_diagnose_v5 import compressed_read,compressed_write
from basketball_shared_spline_v2 import SplineProblem
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_solver_v6 import solve,ConstrainedProblem
from basketball_shared_profiles_v6 import nearest_valid,canonical
from basketball_shared_solver_v3 import objective_agreement
from basketball_audit import sha256

PATHS=['cold','ascending','descending']

def minima(grid,values):
    """Inclusive comparisons preserve tied and endpoint minima; missing neighbors block."""
    found=[]
    for i,v in enumerate(values):
        if v is None or not np.isfinite(v):continue
        neighbors=[values[j] for j in [i-1,i+1] if 0<=j<len(values)]
        if all(w is not None and np.isfinite(w) and v<=w for w in neighbors):found.append(i)
    return found

def refinement(curves,step,competing=False):
    points=set();grid=sorted(curves['cold'])
    valid_costs=[r['objective'] for curve in curves.values() for r in curve.values() if r.get('valid')]
    best=min(valid_costs) if valid_costs else None
    for curve in curves.values():
        values=[curve[x].get('objective') if curve[x].get('valid') else None for x in grid]
        for i in minima(grid,values):
            if competing and (best is None or np.sqrt(values[i])>np.sqrt(best)+.05):continue
            lo=max(-25.,grid[i]-.05) if competing else grid[max(0,i-1)]
            hi=min(25.,grid[i]+.05) if competing else grid[min(len(grid)-1,i+1)]
            # Integer hundredths avoid rounded duplicate coordinates and include endpoints.
            stride=int(round(step*100))
            points.update(k/100 for k in range(int(round(lo*100)),int(round(hi*100))+1,stride))
    return sorted(points-set(grid))

def key_for(group,cameras,lag,weight,conditioned):
    return hashlib.sha256(json.dumps(dict(group=group,calibration=cameras,outer_lag=lag,weight=weight,gauge=1,role='v8-pilot' if conditioned else 'v8-basins',window=[50,149],spacing=10,conditioned=conditioned,source={str(f):sha256(f) for f in Path('scripts').glob('basketball_shared_*_v8.py')}),default=canonical,sort_keys=True).encode()).hexdigest()

def profile(p,gid,lag,weight,output,conditioned=False,deadline=None,fixed_P=None):
    groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12);group=groups[gid]
    end=deadline or p['investigation_started_unix']+(13200 if conditioned else 10200)
    def check():
        if time.time()>=end:raise TimeoutError('scalar profile deadline')
    key=key_for(group,cameras,lag,weight,conditioned);curves={d:{} for d in PATHS};events=output.with_suffix('.events.jsonl')
    scheduled=executed=0
    def event(value):
        with events.open('a') as f:f.write(json.dumps(value,default=canonical)+'\n');f.flush()
    def fit(offset,path,seed):
        nonlocal executed
        check();event(dict(event='started',offset=offset,path=path,problem_key=key))
        if path!='cold' and seed is None:
            row=dict(valid=False,objective=None,error='missing valid seed; no retry',offset=offset,start=path,executed=False)
        else:
            problem=SplineProblem([group],cameras,{1:0.,2:lag,3:offset},window,10,weight,(1,2,3),check)
            if seed is not None and seed[1]['problem_key']!=key:raise ArithmeticError('cross-profile seed')
            solver=solve
            if conditioned:
                from basketball_shared_solver_v8 import solve as conditioned_solve
                from functools import partial
                solver=partial(conditioned_solve,conditioned=fixed_P is None,P=fixed_P)
            row=solver(problem,None if seed is None else seed[1]['x'],None if seed is None else seed[0],3)
            executed+=1
            if row.get('x') is not None:
                # Omitted derivative is evaluated at the same physical state, never optimized.
                joint=SplineProblem([group],cameras,{1:0.,2:lag,3:0.},window,10,weight,(1,2),check)
                a=ConstrainedProblem(joint);x=np.r_[offset,row['x']];r,J=a.evaluate(x/a.scale)
                vg=row.get('multipliers_depth');z,D=a.raw_depth(x/a.scale)
                row['omitted_camera_offset_objective_derivative_per_frame']=float((2*J.T@r)[0]/25.)
                row['omitted_camera_offset_lagrangian_derivative_per_frame']=None if vg is None else float((2*J.T@r+D.T@vg)[0]/25.)
                np.testing.assert_allclose(r@r,row['objective'],atol=1e-10,rtol=1e-9)
                np.testing.assert_allclose(z,row['normalized_depths'],atol=1e-12,rtol=1e-12)
                row['conditional_qualified']=row['valid'];row['joint_qualified']=False
            row.update(offset=offset,start=path,executed=True,seed_offset=None if seed is None else seed[0],seed_start=None if seed is None else seed[1]['start'])
        row['problem_key']=key
        event(dict(event='finished',offset=offset,path=path,executed=row['executed'],qualified=row['valid'],objective=row.get('objective')))
        return row
    def add(points,initial=False):
        nonlocal scheduled
        scheduled+=3*len(points);event(dict(event='scheduled',points=points,paths=PATHS))
        for offset in sorted(points):curves['cold'][offset]=fit(offset,'cold',None)
        for direction,ordered,side in [('ascending',sorted(points),'lower'),('descending',sorted(points,reverse=True),'upper')]:
            previous=None
            for offset in ordered:
                seed=(previous if previous is not None else nearest_valid(curves['cold'],offset)) if initial else nearest_valid(curves[direction],offset,side)
                row=fit(offset,direction,seed);curves[direction][offset]=row
                if row['valid']:previous=(offset,row)
        compressed_write(output,dict(group_id=gid,lag=lag,weight=weight,problem_key=key,curves=curves,scheduled=scheduled,executed=executed,complete=False))
    add(list(range(-25,26)),True)
    fine=refinement(curves,.05);add(fine)
    final=refinement(curves,.01,True);add(final)
    grid=sorted(curves['cold']);failures=[];disagreements=[]
    for x in grid:
        rows=[curves[d][x] for d in PATHS]
        failures.extend(dict(offset=x,path=d) for d,r in zip(PATHS,rows) if not r['valid'])
        values=[r.get('objective') for r in rows]
        if any(v is None for v in values) or not all(objective_agreement(values[0],v) for v in values[1:]):disagreements.append(x)
    # Flat intervals require qualified, agreeing and complete hundredth-frame coverage.
    flats=[];start=None
    for i in range(len(grid)):
        good=all(curves[d][grid[i]]['valid'] for d in PATHS) and grid[i] not in disagreements
        continuing=bool(i and good and start is not None and round((grid[i]-grid[i-1])*100)==1 and all(objective_agreement(curves[d][grid[start]]['objective'],curves[d][grid[i]]['objective']) for d in PATHS))
        if not continuing:
            if start is not None and i-1>start:flats.append([grid[start],grid[i-1]])
            start=i if good else None
    if start is not None and len(grid)-1>start:flats.append([grid[start],grid[-1]])
    result=dict(group_id=gid,lag=lag,weight=weight,problem_key=key,curves=curves,scheduled=scheduled,executed=executed,qualified=scheduled-len(failures),complete=True,failures=failures,disagreements=disagreements,flat_intervals=flats,fine_added=fine,final_added=final,minima={d:[grid[i] for i in minima(grid,[curves[d][x].get('objective') if curves[d][x]['valid'] else None for x in grid])] for d in PATHS})
    compressed_write(output,result);return result

def basins(p,output,predecessor):
    from basketball_shared_regressions_v8 import scalar_regressions
    write(output/'scalar-regressions.json',scalar_regressions())
    tasks=[dict(group_id=g,lag=l,weight=w,artifact=str(output/f'weight{w}-group{g:02d}-lag{l}.json.gz')) for w in p['v8']['weights'] for g in p['pilot_groups'] for l in p['pilot_lags']]
    write(output/'worker-ledger.json',dict(tasks=tasks,scheduled_initial=7344))
    def launch(t):
        if time.time()>=p['investigation_started_unix']+10200:return dict(task=t,executed=False,exit_code=None)
        child=subprocess.Popen([sys.executable,__file__,'worker','configs/basketball-rev2/timing-shared-v8.json',str(t['group_id']),str(t['lag']),str(t['weight']),t['artifact']])
        return dict(task=t,executed=True,exit_code=child.wait())
    with ThreadPoolExecutor(max_workers=6) as pool:
        completed=list(pool.map(launch,tasks))
    write(output/'worker-outcomes.json',dict(records=completed))
    if any(r['exit_code']!=0 for r in completed):raise ArithmeticError('scalar worker interrupted or failed; inspect worker events')
    states=[compressed_read(t['artifact']) for t in tasks]
    # Historical offsets are opened only after every curve and refinement is complete.
    historical=compressed_read('docs/experiments/basketball-shared-timing-v7/prepare/diagnostic-manifest.json.gz')['historical'];coverage=[]
    for ref in historical:
        s=next(s for s in states if (s['group_id'],s['lag'],s['weight'])==(ref['group_id'],ref['lag'],1.))
        s['curves']={d:{float(x):r for x,r in curve.items()} for d,curve in s['curves'].items()}
        points=list(s['curves']['cold'])
        close=[x for x in points if abs(x-ref['nuisance_offset'])<=.05+1e-12]
        covered=any(all(s['curves'][d][x]['valid'] and (s['curves'][d][x]['objective']<=ref['objective'] or objective_agreement(s['curves'][d][x]['objective'],ref['objective'])) for d in PATHS) for x in close)
        coverage.append(dict(**ref,recovered=covered))
    passed=all(not s['failures'] and not s['disagreements'] and s['complete'] for s in states) and all(c['recovered'] for c in coverage)
    write(output/'basin-decision.json',dict(passed=passed,problems=48,initial_scheduled=7344,scheduled=sum(s['scheduled'] for s in states),executed=sum(s['executed'] for s in states),qualified=sum(s['qualified'] for s in states),failed=sum(len(s['failures']) for s in states),disagreements=sum(len(s['disagreements']) for s in states),coverage=coverage,timing_qualification=False))
    return dict(status='passed' if passed else 'blocked',terminal_kind=None if passed else 'scientific_rejection',blockers=[] if passed else ['scalar search screen failed'])

if __name__=='__main__':
    assert sys.argv[1]=='worker'
    profile(read(sys.argv[2]),int(sys.argv[3]),float(sys.argv[4]),float(sys.argv[5]),Path(sys.argv[6]))
