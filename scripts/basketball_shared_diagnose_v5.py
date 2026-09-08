"""Hash-bound baseline and preregistered, non-optimizing ray audit for Plan 011."""
import gzip
import inspect
import json
import time
from pathlib import Path
import numpy as np
import scipy
from scipy.optimize._trustregion_constr import tr_interior_point
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_spline_v2 import SplineProblem,project_jacobian,robust_residual_jacobian
from basketball_shared_solver_v4 import ConstrainedProblem as RawProblem
from basketball_shared_solver_v5 import ConstrainedProblem,transform,MARGIN,provenance

ROOT=Path('docs/experiments/basketball-shared-timing-v4')
GROUPS=[2,9,11]
LAGS=[-25.,-20.,-19.,-7.,-6.,-.1,0.,25.]
AMPLITUDES=[10.**e for e in range(0,45,2)]


def compressed_read(path):
    with gzip.open(path,'rt') as stream:return json.load(stream)


def compressed_write(path,value):
    started=time.monotonic()
    with gzip.GzipFile(filename=str(path),mode='wb',mtime=0) as stream:
        stream.write(json.dumps(value,allow_nan=False,separators=(',',':')).encode())
    return dict(path=path.name,sha256=sha256(path),bytes=path.stat().st_size,serialization_seconds=time.monotonic()-started)


def check_deadline(p):
    if time.time()>=p['investigation_started_unix']+1800:raise TimeoutError('30-minute pilot decision deadline')


def baseline(p,output):
    evidence=read(p['v4_evidence'])
    for key in ['source_sha256','artifacts_sha256']:verify_hashes(evidence[key])
    names=['exact-retest.json','initialization-attempts.json','profile-groups.json',
           'coefficient-diagnostics.json','evaluator-freeze.json','verification.json']
    hashes={str(ROOT/name):sha256(ROOT/name) for name in names}
    hashes[str(ROOT.with_suffix('.md'))]=sha256(ROOT.with_suffix('.md'))
    hashes[p['v4_evidence']]=sha256(p['v4_evidence'])
    failed=[];total=0
    for entry in read(ROOT/'profile-groups.json')['groups']:
        check_deadline(p);file=ROOT/entry['path'];hashes[str(file)]=sha256(file)
        if entry['weight']!=0:continue
        state=compressed_read(file)
        for attempts in state['attempts'].values():
            total+=len(attempts);failed.extend(r for r in attempts if not r['valid'])
    summary=dict(total_data_only_attempts=total,failed_data_only_attempts=len(failed),
        median_failed_objective_evaluations=float(np.median([r['nfev'] for r in failed])),
        minimum_failed_normalized_depth=min(r['minimum_normalized_depth'] for r in failed),
        iteration_ceiling=200,independent_distinct_objective_ceiling=200,
        failed_iteration_counts=sorted(set(r['solver_trace'][-1]['iteration'] for r in failed)),
        baseline_optimization_rerun=False,fractional_minus_point_one_reference=None)
    assert total==1836 and len(failed)==1774 and summary['median_failed_objective_evaluations']==197
    assert summary['minimum_failed_normalized_depth']>3.59
    source=Path(inspect.getsourcefile(tr_interior_point));code=source.read_text()
    assert 'f - self.barrier_parameter*np.sum(log_s)' in code
    summary['installed_barrier']=dict(scipy=scipy.__version__,path=str(source),sha256=sha256(source),
        expression='f - self.barrier_parameter*np.sum(log_s)')
    write(output/'baseline.json',summary)
    write(output/'v4-import.json',dict(source_sha256=hashes,old_config_hashes_rewritten=False,
        historical_verification=read(ROOT/'verification.json')['status']))


def fixture(gid,lag,weight,check):
    groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    return SplineProblem([groups[gid]],cameras,{1:0.,2:lag,3:0.},window,10,weight,(1,2),check)


def bind_rays(p):
    rays=[]
    for weight in [1.,0.]:
        for gid in GROUPS:
            for lag in LAGS:
                check_deadline(p);prob=fixture(gid,lag,weight,lambda:check_deadline(p))
                direction=np.zeros_like(prob.x0);direction[prob.n_offsets+2::3]=1.
                rays.append(dict(kind='uniform_z',group_id=gid,lag=lag,weight=weight,
                    base=prob.x0.tolist(),direction=direction.tolist(),offsets=prob.unpack(prob.x0)[0]))
    historical=[]
    for index in range(12):
        file=ROOT/f'rejected-{index:02d}.json.gz';raw=compressed_read(file)
        historical.append(dict(path=str(file),sha256=sha256(file),saved_probe_count=len(raw['probes'])))
        states=raw['states']
        for origin,source,base_name in [('seed','source_seed','source_cold'),('final','destination_final','destination_cold')]:
            base=np.asarray(states[base_name]['x']);delta=np.asarray(states[source]['x'])-base
            for block in raw['suspect_blocks']:
                vector=delta[1+3*block:1+3*block+3];norm=float(np.linalg.norm(vector))
                if norm==0:continue
                for fixed,lag in [('source',raw['source_lag']),('destination',raw['lag'])]:
                    for sign in [-1,1]:
                        direction=np.zeros_like(base);direction[1+3*block:1+3*block+3]=sign*vector/norm
                        rays.append(dict(kind='saved_block',record=index,origin=origin,fixed=fixed,block=block,sign=sign,
                            group_id=raw['group_id'],lag=lag,weight=0.,base=base.tolist(),direction=direction.tolist(),
                            offsets={1:0.,2:lag,3:float(base[0])},saved_displacement_norm=norm))
    return rays,historical


def ray_limit(prob,base,direction):
    """Fixed-offset projective ray limit; exact support checked by knot intervals."""
    offsets,coeff=prob.unpack(base);_,delta=prob.unpack(direction)
    assert np.all(direction[:prob.n_offsets]==0)
    errors=[];feasible=True;exists=True;observable=False;weak=False;exact_zero=True;depth0=[];dzs=[]
    for gi,group in enumerate(prob.groups):
        for obs in group['observations']:
            cam=prob.cameras[obs['camera_id']];times=(obs['frames']-offsets[obs['camera_id']])/25
            B=prob.spline(times);xyz=B@coeff[gi];motion=B@delta[gi]
            active=np.flatnonzero(np.any(delta[gi]!=0,axis=1))
            # Zero support is certified using compact support, not a small gradient.
            for col in active:
                if np.any(B[:,col]!=0) or np.any((times>prob.spline.t[col])&(times<prob.spline.t[col+4])):exact_zero=False
            norms=np.linalg.norm(B,axis=0);threshold=max(B.shape)*np.finfo(float).eps*max(norms)
            weak=weak or bool(np.any((norms[active]>0)&(norms[active]<threshold)))
            camera_xyz=(xyz*prob.diameter+prob.center)@np.asarray(cam['R']).T+cam['t']
            growth=motion*prob.diameter@np.asarray(cam['R']).T
            depth0.extend(camera_xyz[:,2]/prob.diameter);dzs.extend(growth[:,2]/prob.diameter)
            moving=np.any(growth!=0,axis=1);observable=observable or bool(moving.any())
            feasible=feasible and bool(np.all(growth[:,2]>=0) and np.all(camera_xyz[growth[:,2]==0,2]/prob.diameter>=MARGIN))
            flat=moving&(growth[:,2]==0)
            if flat.any():exists=False
            uv=camera_xyz[:,:2]/camera_xyz[:,2,None]
            changing=growth[:,2]!=0;uv[changing]=growth[changing,:2]/growth[changing,2,None]
            radial=1+cam['parameters_colmap'][3]*np.sum(uv**2,axis=1)
            pred=(uv*radial[:,None])@np.asarray(cam['K'])[:2,:2].T+np.asarray(cam['K'])[:2,2]
            errors.extend(pred-obs['xy'])
    acc=prob.accel@coeff[0];acc_direction=prob.accel@delta[0]
    # Constant coefficient translation has zero second derivative in exact arithmetic.
    invariant_acc=bool(np.all(delta[0]==delta[0,0])) or bool(np.all(acc_direction==0))
    if prob.weight and not invariant_acc:exists=False
    r=robust_residual_jacobian(np.asarray(errors),prob.n)[0]
    limit=float(np.sum(r*r)+prob.weight*np.sum(acc*acc)/prob.nacc) if exists else None
    return dict(original_objective_limit=limit,limit_exists=exists,ray_eventually_depth_feasible=feasible,
        observable=observable,weak_support=weak,exactly_unsupported=bool(exact_zero and (not prob.weight or invariant_acc)),
        acceleration_invariant_exact=invariant_acc,finite_precision_acceleration_direction_norm=float(np.linalg.norm(acc_direction)),
        initial_minimum_depth=float(min(depth0)),minimum_depth_slope=float(min(dzs)))


def diagnose(p,output):
    rays,historical=bind_rays(p)
    manifest=dict(groups=GROUPS,lags=LAGS,weights=[1.,0.],scheduled_problems=48,scheduled_attempts=144,
        starts=['cold','ascending','descending'],amplitudes=AMPLITUDES,rays=rays,historical=historical,
        solver=provenance(),source_sha256={f:sha256(f) for f in ['scripts/basketball_shared_solver_v5.py',
        'scripts/basketball_shared_profiles_v5.py','scripts/basketball_shared_diagnose_v5.py','scripts/basketball_shared_pilot_v5.py']},
        frozen_unix=time.time(),cache_role='pilot; disjoint from diagnostic and qualification',mu=.1)
    write(output/'pilot-manifest.json',manifest)
    records=[];baseline_cache={}
    for i,ray in enumerate(rays):
        check_deadline(p);prob=fixture(ray['group_id'],ray['lag'],ray['weight'],lambda:check_deadline(p))
        base=np.asarray(ray['base']);direction=np.asarray(ray['direction']);limit=ray_limit(prob,base,direction)
        key=(ray['weight'],ray['group_id'])
        if key not in baseline_cache:
            label='regularized' if ray['weight'] else 'data_only'
            baseline_cache[key]=compressed_read(ROOT/f'{label}-group{ray["group_id"]:02d}.json.gz')
        old=baseline_cache[key]['attempts'].get(str(float(ray['lag'])),[])
        qualified=[r['objective'] for r in old if r['valid']]
        finite=float(prob.evaluate(base)[0]@prob.evaluate(base)[0])
        depth=RawProblem(prob).depth(base/RawProblem(prob).scale)[0]
        # A stalled state is not a certified minimum, but is still an available feasible finite value.
        available=[r['objective'] for r in old if r.get('minimum_normalized_depth',0)>MARGIN
                   and r.get('objective') is not None and np.isfinite(r['objective'])
                   and all(abs(float(v))<=25 for v in r.get('offsets',{}).values())]
        references=available+([finite] if np.min(depth)>MARGIN else [])
        reference=min(references) if references else None
        if limit['exactly_unsupported']:classification='exactly_unsupported_invariant'
        elif not limit['ray_eventually_depth_feasible']:
            classification='infeasible_ray'  # Analytic negative depth slope rules out feasible escape.
        elif reference is not None and limit['original_objective_limit'] is not None and limit['original_objective_limit']>reference+1e-6+1e-4*max(reference,abs(limit['original_objective_limit'])):
            classification='observable_limit_worse_than_feasible_finite'
        else:classification='unresolved_observable_escape'
        probes=[];adapter=ConstrainedProblem(prob);raw=RawProblem(prob)
        for amplitude in AMPLITUDES:
            check_deadline(p);x=base+amplitude*direction
            try:
                residual,_=prob.evaluate(x);objective=float(residual@residual);z,_=raw.depth(x/raw.scale)
                g,first,second,flags=transform(z-MARGIN);positive=bool(np.all(z>MARGIN))
                probes.append(dict(amplitude=amplitude,objective=objective,data_objective=float(np.sum(residual[:2*prob.n]**2)),min_depth=float(min(z)),max_depth=float(max(z)),
                    raw_barrier=objective-.1*float(np.sum(np.log(z-MARGIN))) if positive else None,
                    bounded_barrier=objective-.1*float(np.sum(np.log(g))) if positive else None,
                    transformation=flags,finite=bool(np.isfinite(objective)),
                    acceleration_cost=float(prob.weight*np.sum((prob.accel@prob.unpack(x)[1][0])**2)/prob.nacc)))
            except FloatingPointError as error:probes.append(dict(amplitude=amplitude,error=str(error)))
        records.append(dict(ray_id=i,**limit,classification=classification,finite_feasible_reference=reference,
            qualified_v4_reference=min(qualified) if qualified else None,
            available_v4_finite_reference=min(available) if available else None,cold_is_not_claimed_optimal=True,probes=probes))
    artifact=compressed_write(output/'escape-audit.json.gz',dict(records=records))
    unresolved=[r['ray_id'] for r in records if r['classification']=='unresolved_observable_escape']
    write(output/'escape-decision.json',dict(rays=len(records),unresolved=unresolved,artifact=artifact,
        finite_audit_not_global_certificate=True,mathematical_argument='docs/experiments/basketball-shared-timing-v5.md',
        resolved=not unresolved,uniform_z_barrier_unbounded_exact=True))
    check_deadline(p)
    return dict(status='blocked' if unresolved else 'passed',terminal_kind='numerical_failure' if unresolved else None,
        blockers=['escape audit unresolved rays: '+str(unresolved)] if unresolved else [],pilot_scheduled_attempts=144,pilot_attempted=0)
