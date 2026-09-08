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
from basketball_shared_solver_v6 import solve,provenance
from basketball_shared_synthetic_v2 import synthetic


def canonical(value):
    if isinstance(value,np.ndarray):return value.tolist()
    if isinstance(value,np.generic):return value.item()
    raise TypeError(type(value).__name__)


def problem_key(group,cameras,edge,window,spacing,weight,role):
    return hashlib.sha256(json.dumps(dict(observations=group,calibration=cameras,edge=edge,
        window=window,spacing=spacing,weight=weight,role=role,solver=provenance(),derivative_sources={f:sha256(f) for f in ['scripts/basketball_shared_solver_v6.py','scripts/basketball_shared_spline_v2.py']}),
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
    except (InsufficientSupport,ValueError,FloatingPointError) as error:
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


def costs(states,grid,direction=None):
    result=[]
    for state in states:
        values=[]
        for lag in grid:
            candidates=state['attempts'][float(lag)] if direction is None else [state[direction].get(float(lag),{})]
            valid=[r['objective'] for r in candidates if r.get('valid')]
            values.append(min(valid) if valid else None)
        result.append(values)
    return result


def summaries(states,grid,minimum_groups,sweep_limit,fixed_ids=None):
    directions={d:curve_summary(costs(states,grid,d),grid,minimum_groups) for d in ['ascending','descending']}
    result=curve_summary(costs(states,grid),grid,minimum_groups)
    lags=[r['lag'] for r in directions.values()]
    agreement=None if any(l is None for l in lags) else abs(lags[0]-lags[1])
    result.update(sweeps=directions,sweep_disagreement_frames=agreement,sweep_limit_frames=sweep_limit,
                  group_ids=[s['group_id'] for s in states],group_profile_costs=costs(states,grid),
                  directional_group_costs={d:costs(states,grid,d) for d in directions})
    if not all(r['passed'] for r in directions.values()) or agreement is None or agreement>sweep_limit:
        result['blockers'].append('incomplete, unqualified or inconsistent directional profiles')
    if fixed_ids is not None:
        supported=[s['group_id'] for s,good in zip(states,result['support_mask']) if good]
        if supported!=fixed_ids:result['blockers'].append('fixed group support lost during refinement')
        for direction,row in directions.items():
            supported=[s['group_id'] for s,good in zip(states,row['support_mask']) if good]
            if supported!=fixed_ids:result['blockers'].append(direction+' fixed group support lost')
    result['passed']=not result['blockers']
    return result


def basin_grid(summary,grid,step,competing=False):
    """Union basins from retained-best and both directional aggregate profiles."""
    points=list(grid)
    for row in [summary,*summary['sweeps'].values()]:
        if row['lag'] is None:continue
        c=np.asarray(row['cost_pixels'])
        if np.ptp(c)<=1e-8:continue
        indices=[i for i in range(len(grid)) if (i==0 or c[i]<=c[i-1]) and (i==len(grid)-1 or c[i]<=c[i+1])
                 and (not competing or c[i]<=min(c)+.05)]
        radius=.05 if competing else 1.
        for i in indices:points.extend(np.arange(max(-25,grid[i]-radius),min(25,grid[i]+radius)+step/2,step))
    return np.unique(np.round(points,8))


def independent_edge(groups,cameras,edge,window,spacing,weight,check=lambda:None,
                     minimum_groups=12,workers=8,deadline=None,sweep_limit=.25,role='synthetic',output=None):
    if not 1<=workers<=8:raise ValueError('CPU worker limit exceeded')
    selected=[g for g in groups if {edge['a'],edge['b']}<={o['camera_id'] for o in g['observations']}]
    outputs={};traces=[]
    executor=ProcessPoolExecutor(max_workers=workers,mp_context=multiprocessing.get_context('spawn')) if workers>1 else None
    try:
        for label,penalty in [('regularized',weight),('data_only',0.)]:
            states=[None]*len(selected);grid=np.arange(-25,26,dtype=float);fixed_ids=[g['group_id'] for g in selected]
            for round_id in range(3):
                check();jobs=[(g,cameras,edge,window,spacing,penalty,role,grid,state,deadline) for g,state in zip(selected,states)]
                states=list(executor.map(group_job,jobs)) if executor else [group_job(job) for job in jobs]
                summary=summaries(states,grid,minimum_groups,sweep_limit,fixed_ids)
                # Membership is fixed before any solve, including each direction.
                if output is not None:
                    write(output/f'{label}-round{round_id}.json',dict(summary=summary,grid=grid.tolist(),states=states))
                if round_id==2 or summary['lag'] is None:break
                refined=basin_grid(summary,grid,.05 if round_id==0 else .01,round_id==1)
                if len(refined)==len(grid):break
                grid=refined
            outputs[label]=summary
            traces.append(dict(weight=penalty,states=states))
        return dict(a=edge['a'],b=edge['b'],window=list(window),spacing=spacing,weight=weight,
                    passed=all(r['passed'] for r in outputs.values()),profiles=outputs,optimizer_traces=traces,
                    production_state_used=False,cache_scope='mathematically identical group/edge/window/role/penalty only')
    finally:
        if executor:executor.shutdown(wait=True,cancel_futures=True)


def decision(motion,length,noise,truth,result,minimum_groups=12):
    numerical=any(r['support']<minimum_groups or any(s['support']<minimum_groups for s in r['sweeps'].values()) for r in result['profiles'].values())
    errors=[None if r['lag'] is None else abs(r['lag']-truth) for r in result['profiles'].values()]
    negative=motion in ['stationary','epipolar_direction']
    identified=result['profiles']['data_only']['passed']
    if negative:passed=not numerical and not result['passed']
    elif noise==0:
        required=length==100 or identified
        passed=not required or (result['passed'] and all(e is not None and e<=.05 for e in errors))
    else:passed=not numerical and (not result['passed'] or all(e is not None and e<=.25 for e in errors))
    return dict(safeguard_passed=bool(passed),terminal_kind=None if passed else 'numerical_failure' if numerical else 'scientific_rejection',
                absolute_errors_frames=errors,numerical_evidence_complete=not numerical,data_only_identified=identified,
                estimator_qualified=result['passed'],recovery_limit_frames=.05 if noise==0 else .25)


def safeguard(p,output):
    # Freeze complete profile implementation before the first scientific profile.
    sources={f:sha256(f) for f in ['scripts/basketball_shared_profiles_v6.py','scripts/basketball_shared_solver_v6.py']}
    write(output/'evaluator-freeze.json',dict(source_sha256=sources,solver=provenance(),frozen_unix=time.time(),
        policy='integer cold then ascending then descending; refinement cold/lower ascending/upper descending; no tuning'))
    deadline=p['investigation_started_unix']+5400
    def check():
        if time.time()>=deadline:raise TimeoutError('90-minute exact failing-control retest deadline')
    groups,cameras,truth,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    folder=output/'exact-retest';folder.mkdir()
    result=independent_edge(groups,cameras,dict(a=1,b=2),window,10,1.,check,
                            deadline=deadline,sweep_limit=.05,output=folder)
    row=decision('direction_changes',100,0.,truth[2],result)
    write(folder/'result.json',dict(**row,result=result))
    from basketball_continuation_audit import verify_hashes
    verify_hashes(sources)
    if not row['safeguard_passed']:
        return dict(status='blocked',terminal_kind=row['terminal_kind'],blockers=['exact 12-group noiseless direction-change retest failed'],
                    exact_retest=row,independent_matrix_complete=False,independent_controls_attempted=0,planned_independent_controls=117,
                    targeted_controls_attempted=0,planned_targeted_controls=3)
    return matrix(p,output,sources)


def matrix(p,output,sources):
    """All independent controls rerun, including previously passing cases."""
    deadline=p['investigation_started_unix']+13200
    def check():
        if time.time()>=deadline:raise TimeoutError('safeguard matrix deadline')
    targeted=[]
    old=read(Path(p['controls'])/'synthetic-summary.json')
    for target in old['targeted_controls']:
        i=target['optimizer_case_id'];check()
        recipe=read(Path(p['controls'])/'optimizer-controls'/f'case{i:04d}.json')
        folder=output/f'targeted{i:04d}';folder.mkdir()
        groups,cameras,truth,window=synthetic(recipe['motion'],recipe['noise_pixels'],recipe['known_offset_frames'],recipe['length'],groups=3)
        c=recipe['configuration']
        result=independent_edge(groups,cameras,dict(a=1,b=2),window,c['knot_spacing_frames'],c['acceleration_weight'],check,
            minimum_groups=3,workers=3,deadline=deadline,sweep_limit=.05,output=folder)
        row=decision(recipe['motion'],recipe['length'],recipe['noise_pixels'],truth[2],result,3)
        # When independently identifiable, every unchanged production start must recover too.
        if row['data_only_identified'] and any(e>.05 for e in recipe['absolute_errors_frames']):
            row.update(safeguard_passed=False,terminal_kind='scientific_rejection')
        targeted.append(dict(optimizer_case_id=i,**row));write(folder/'result.json',dict(**row,result=result))
        if not row['safeguard_passed']:
            return dict(status='blocked',terminal_kind=row['terminal_kind'],blockers=[f'targeted case {i} failed'],
                        targeted_controls=targeted,targeted_controls_attempted=len(targeted),planned_targeted_controls=3,
                        independent_matrix_complete=False,independent_controls_attempted=0,planned_independent_controls=117)
    cases=[];rows=[]
    for length in [100,50,25]:
        for noise in [0.,.25,.5]:
            for delta in p['injections']:
                cases.append(dict(motion=['constant_velocity','acceleration','direction_changes'][len(cases)%3],length=length,noise=noise,delta=delta,weight=1.))
    for motion in ['stationary','epipolar_direction']:
        for weight in [.1,1.,10.]:
            for length in [100,50,25]:
                for noise in [0.,.25,.5]:cases.append(dict(motion=motion,length=length,noise=noise,delta=.25,weight=weight))
    for i,case in enumerate(cases):
        check();folder=output/f'independent{i:03d}';folder.mkdir()
        groups,cameras,truth,window=synthetic(case['motion'],case['noise'],case['delta'],case['length'],groups=12)
        result=independent_edge(groups,cameras,dict(a=1,b=2),window,10,case['weight'],check,
            deadline=deadline,sweep_limit=.05 if case['noise']==0 else .25,output=folder)
        row=dict(case_id=i,**case,**decision(case['motion'],case['length'],case['noise'],truth[2],result));rows.append(row)
        write(folder/'result.json',dict(**row,result=result));write(output/'matrix-progress.json',dict(cases=rows))
        if not row['safeguard_passed']:
            return dict(status='blocked',terminal_kind=row['terminal_kind'],blockers=[f'independent case {i} failed'],
                        independent_matrix_complete=False,independent_controls_attempted=len(rows),planned_independent_controls=117,
                        targeted_controls_attempted=len(targeted),planned_targeted_controls=3)
    from basketball_continuation_audit import verify_hashes
    verify_hashes(sources)
    return dict(status='passed',terminal_kind=None,blockers=[],targeted_controls=targeted,
                targeted_controls_attempted=len(targeted),planned_targeted_controls=3,
                independent_matrix_complete=True,independent_controls_attempted=len(rows),planned_independent_controls=117)
