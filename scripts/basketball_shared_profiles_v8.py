"""Independent three-start profiles. State never crosses a mathematical problem."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:
    os.environ[name]='1'
import hashlib
import json
import time
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
import multiprocessing
import numpy as np
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_shared_spline_v2 import (SplineProblem,clip_groups,predict,robust_residual_jacobian,
                                         curve_summary,InsufficientSupport)
from basketball_shared_solver_v6 import provenance
from basketball_shared_solver_v8 import solve as adapter_solve
from functools import partial
solve=partial(adapter_solve,conditioned=True)
from basketball_shared_synthetic_v2 import synthetic


def canonical(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)


def problem_key(group,cameras,edge,window,spacing,weight,role):
    return hashlib.sha256(json.dumps(dict(observations=group,calibration=cameras,edge=edge,
        window=window,spacing=spacing,weight=weight,role=role,solver=provenance(),derivative_sources={f:sha256(f) for f in ['scripts/basketball_shared_solver_v6.py','scripts/basketball_shared_spline_v2.py','scripts/basketball_shared_solver_v8.py','scripts/basketball_shared_profiles_v8.py']}),
        default=canonical,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def nearest_valid(rows,lag,side=None):
    choices=[(float(k),v) for k,v in rows.items() if v.get('valid')
             and (side is None or (float(k)<lag if side=='lower' else float(k)>lag))]
    return min(choices,key=lambda kv:(abs(kv[0]-lag),kv[0])) if choices else None


def attempt(group,cameras,edge,window,spacing,weight,lag,label,key,seed,check):
    seed_lag=None if seed is None else seed[0]
    trace=dict(lag=float(lag),start=label,problem_key=key,cache_key=f'{key}:{lag:.8f}',
               seed_lag=seed_lag,seed_start=None if seed is None else seed[1]['start'],
               seed_problem_key=None if seed is None else seed[1]['problem_key'])
    if label!='cold' and seed is None:
        return dict(**trace,valid=False,converged=False,objective=None,error='missing valid seed; no retry')
    if seed is not None and seed[1]['problem_key']!=key:raise ValueError('cross-problem seed forbidden')
    observed={o['camera_id'] for o in group['observations']}
    offsets={c:0. for c in observed};offsets[edge['b']]=float(lag)
    try:
        initialization_started=time.monotonic()
        problem=SplineProblem([group],cameras,offsets,window,spacing,weight,(edge['a'],edge['b']),check)
        construction_seconds=time.monotonic()-initialization_started
        fit=solve(problem,None if seed is None else seed[1]['x'],source_lag=seed_lag,endpoint=edge['b'])
        fit['problem_initialization_seconds']=construction_seconds
        return dict(**fit,**trace)
    except InsufficientSupport as error:
        return dict(**trace,valid=False,converged=False,objective=None,error=str(error))


def group_job(payload):
    group,cameras,edge,window,spacing,weight,role,grid,state,deadline=payload
    def check():
        if deadline is not None and time.time()>=deadline:raise TimeoutError('independent profile deadline')
    key=problem_key(group,cameras,edge,window,spacing,weight,role)
    if state is not None and state['problem_key']!=key:raise ValueError('cache isolation violation')
    state=state or dict(group_id=group['group_id'],problem_key=key,attempts={},cold={},ascending={},descending={})
    # Serialized lag dictionaries are normalized to float before any lookup.
    for field in ['attempts','cold','ascending','descending']:state[field]={float(k):v for k,v in state[field].items()}
    missing=sorted(float(l) for l in grid if float(l) not in state['attempts'])
    held={0,10,20,30};a,b=edge['a'],edge['b'];endpoint=a if a in held else b if b in held else None
    training=clip_groups([group],window,set(cameras)-held)
    observed={o['camera_id'] for g in training for o in g['observations']}
    if len(observed)<3 or not ({a,b}-held)<=observed:
        for lag in missing:
            state['attempts'][lag]=[dict(lag=lag,start='cold',valid=False,converged=False,objective=None,error='training support missing')]
        return state
    if endpoint is not None:
        if a in held and b in held:raise ValueError('held-held edge lacks training gauge')
        anchor=b if a in held else a
        if 'frozen_training' not in state:
            problem=SplineProblem(training,cameras,{c:0. for c in observed},window,spacing,weight,(anchor,),check)
            state['frozen_training']=solve(problem)
        fit=state['frozen_training']
        obs=next(o for o in clip_groups([group],window)[0]['observations'] if o['camera_id']==endpoint)
        for lag in missing:
            check();offset=lag if endpoint==b else -lag
            errors=predict(fit,0,cameras[endpoint],obs['frames'],offset)-obs['xy']
            residual=robust_residual_jacobian(errors,len(errors))[0]
            # Include held-out positive-depth validation, not merely training depth.
            from scipy.interpolate import BSpline
            from basketball_shared_spline_v2 import project_jacobian
            xyz=BSpline(fit['knots'],np.asarray(fit['coefficients'][0]),3)((obs['frames']-offset)/25)
            _,_,depth=project_jacobian(xyz,cameras[endpoint],np.asarray(fit['center']),fit['diameter'])
            row=dict(lag=lag,start='frozen_training',valid=bool(fit['valid'] and np.all(depth/fit['diameter']>1e-7)),
                     converged=fit['converged'],objective=float(np.sum(residual**2)),problem_key=key,
                     cache_key=f'{key}:{lag:.8f}',nuisance_fit_reused=True)
            state['attempts'][lag]=[row]
            for direction in ['cold','ascending','descending']:state[direction][lag]=row
        return state
    if not missing:return state
    initial=not state['attempts']
    for lag in missing:
        check();row=attempt(training[0],cameras,edge,window,spacing,weight,lag,'cold',key,None,check)
        state['cold'][lag]=row;state['attempts'][lag]=[row]
    for direction,ordered,side in [('ascending',missing,'lower'),('descending',missing[::-1],'upper')]:
        previous=None
        for lag in ordered:
            check()
            seed=(previous if previous is not None else nearest_valid(state['cold'],lag)) if initial else nearest_valid(state[direction],lag,side)
            row=attempt(training[0],cameras,edge,window,spacing,weight,lag,direction,key,seed,check)
            state[direction][lag]=row;state['attempts'][lag].append(row)
            if row['valid']:previous=(lag,row)
    return state



def pilot_worker(p,gid,weight,output):
    from basketball_shared_scalar_search_v8 import profile,PATHS
    from basketball_shared_solver_v8 import Adapter
    from basketball_shared_recovery_v8 import fixture
    from basketball_shared_diagnose_v5 import compressed_write
    groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    end=p['investigation_started_unix']+13200
    def check():
        if time.time()>=end:raise TimeoutError('combined pilot deadline')
    outer=group_job((groups[gid],cameras,dict(a=1,b=2),window,10,weight,'v8-pilot',p['pilot_lags'],None,end))
    results=[]
    for lag,rows in outer['attempts'].items():
        a=Adapter(fixture(gid,lag,weight,check),True)
        scalar=profile(p,gid,lag,weight,output/f'scalar-{lag}.json.gz',True,end,a.P[1:,1:])
        for path,row in zip(PATHS,rows):
            releases=[]
            for offset in scalar['minima'][path]:
                if not -25<offset<25:continue
                seed=np.r_[offset,scalar['curves'][path][offset]['x']]
                joint=adapter_solve(fixture(gid,lag,weight,check),seed,lag,2,True,a.P)
                releases.append(dict(offset=offset,fit=joint))
            candidates=[r for r in [row,*[r['fit'] for r in releases]] if r['valid']]
            best=min(candidates,key=lambda r:r['objective']) if candidates else None
            curve=scalar['curves'][path];minima=scalar['minima'][path]
            boundary=[curve[x]['objective'] for x in minima if abs(x)==25]
            interior=[curve[x]['objective'] for x in minima if abs(x)<25]
            boundary_blocked=bool(boundary and (not interior or min(boundary)<min(interior)-1e-6-1e-4*max(abs(min(boundary)),abs(min(interior)))))
            results.append(dict(group_id=gid,weight=weight,lag=lag,path=path,original_outer=row,joint_releases=releases,best=best,qualified=best is not None and not scalar['failures'] and not scalar['disagreements'] and not boundary_blocked,boundary_blocked=boundary_blocked))
            compressed_write(output/'outer-results.json.gz',dict(records=results))
    return results


def pilot(p,output,predecessor):
    from basketball_shared_diagnose_v5 import compressed_read,compressed_write
    from basketball_shared_solver_v3 import objective_agreement
    import subprocess,sys
    # Follow the hashed chain back to the conditioning decision; both passes are required.
    prior=read(predecessor/'result.json')
    decisions=[Path(f).parent/'conditioning-decision.json' for f in prior['source_sha256'] if f.endswith('/result.json')]
    if not any(f.exists() and read(f)['passed'] for f in decisions):
        return dict(status='blocked',terminal_kind='scientific_rejection',blockers=['conditioning did not pass; combined pilot unassessed'],combined_decision='unassessed')
    tasks=[]
    for weight in p['v8']['weights']:
        for gid in p['pilot_groups']:
            folder=output/f'weight{weight}-group{gid:02d}';folder.mkdir()
            tasks.append((gid,weight,folder))
    children=[subprocess.Popen([sys.executable,__file__,'pilot-worker',str(g),str(w),str(f)]) for g,w,f in tasks]
    codes=[c.wait() for c in children]
    if any(codes):raise ArithmeticError('combined worker failed')
    records=[r for _,_,f in tasks for r in compressed_read(f/'outer-results.json.gz')['records']]
    comparisons=[];transfers=[]
    for gid,weight,folder in tasks:
        historical=[]
        for version in [4,5,6]:
            f=Path(f'docs/experiments/basketball-shared-timing-v{version}')/(f'{"regularized" if weight else "data_only"}-group{gid:02d}.json.gz' if version==4 else f'pilot/weight{weight}-group{gid:02d}.json.gz')
            historical.append(compressed_read(f))
        for lag in p['pilot_lags']:
            rows=[r for r in records if (r['group_id'],r['weight'],r['lag'])==(gid,weight,lag)]
            refs=[r['objective'] for s in historical for r in s['attempts'].get(str(float(lag)),[]) if r['valid']]
            values=[r['best']['objective'] for r in rows if r['best'] is not None]
            comparisons.append(dict(group_id=gid,weight=weight,lag=lag,agreement=len(values)==3 and all(objective_agreement(values[0],v) for v in values),no_worse=len(values)==3 and (not refs or all(v<=min(refs) or objective_agreement(v,min(refs)) for v in values))))
        dest,source,direction=(-19.,-20.,'ascending') if gid==2 else (-7.,-6.,'descending')
        required=next(r['original_outer'] for r in records if (r['group_id'],r['weight'],r['lag'],r['path'])==(gid,weight,dest,direction))
        transfers.append(dict(group_id=gid,weight=weight,passed=required['valid'] and required['seed_lag']==source))
    passed=all(r['qualified'] for r in records) and all(r['agreement'] and r['no_worse'] for r in comparisons) and all(r['passed'] for r in transfers)
    write(output/'combined-decision.json',dict(passed=passed,outer_searches=144,qualified=sum(r['qualified'] for r in records),comparisons=comparisons,transfers=transfers,timing_qualification=False))
    return dict(status='passed' if passed else 'blocked',terminal_kind=None if passed else 'scientific_rejection',blockers=[] if passed else ['combined pilot failed'],combined_decision='passed' if passed else 'failed')

if __name__=='__main__':
    import sys
    assert sys.argv[1]=='pilot-worker'
    pilot_worker(read('configs/basketball-rev2/timing-shared-v8.json'),int(sys.argv[2]),float(sys.argv[3]),Path(sys.argv[4]))
