"""Hash-bound SciPy least-squares diagnostics and observation-only v4 replay."""
import importlib
import inspect
from pathlib import Path
import time
from unittest.mock import patch
import numpy as np
from scipy.sparse import csr_array, eye_array, vstack
from scipy.optimize._trustregion_constr.projections import projections
from scipy.optimize._trustregion_constr.tr_interior_point import BarrierSubproblem
from basketball_audit import sha256
from basketball_scale import read, write
from basketball_continuation_audit import verify_hashes
from basketball_shared_diagnose_v5 import compressed_read, compressed_write
from basketball_shared_solver_v5 import ConstrainedProblem, transform, MARGIN
from basketball_shared_solver_v4 import ConstrainedProblem as RawProblem
from basketball_shared_spline_v2 import SplineProblem
from basketball_shared_synthetic_v2 import synthetic

MODULES=['scipy.optimize._trustregion_constr.'+n for n in ['tr_interior_point','equality_constrained_sqp','projections','canonical_constraint','minimize_trustregion_constr']]+['scipy.optimize._differentiable_functions','scipy.optimize._constraints']

def implementation():
    return {inspect.getfile(importlib.import_module(n)):sha256(inspect.getfile(importlib.import_module(n))) for n in MODULES}

def check(p):
    if time.time()>=p['investigation_started_unix']+1800:raise TimeoutError('30-minute historical recovery deadline')

def fixture(gid,lag,weight,check=lambda:None):
    groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    return SplineProblem([groups[gid]],cameras,{1:0.,2:float(lag),3:0.},window,10,weight,(1,2),check)

def reconstruct(problem,x,mu,raw=False):
    """Recover v=-LS*c, not the central-path approximation mu/slack.

    All inequalities keep feasible: SciPy overwrites each slack with -c(x).
    Canonical order is depth lower, offset interval upper, offset interval lower.
    Bounds are expanded by nextafter in the installed trust-constr driver.
    Rejected steps retain x/v; new barriers recompute the LS solve before callback.
    """
    a=RawProblem(problem) if raw else ConstrainedProblem(problem)
    q=np.asarray(x)/a.scale;r,J=a.evaluate(q);G=np.asarray(2*J.T@r).ravel()
    z,Dz=a.depth(q) if raw else a.raw_depth(q)
    g,gp=(z-MARGIN,np.ones_like(z)) if raw else transform(z-MARGIN)[:2]
    from scipy.sparse import diags
    D=diags(gp)@Dz;n=problem.n_offsets;m=len(g)
    I=eye_array(len(q),format='csr')[:n]
    C=vstack([-D,I,-I],format='csr')
    bound=np.nextafter(1.,np.inf)
    slacks=np.r_[g,bound-q[:n],q[:n]+bound]
    if not np.isfinite(slacks).all() or np.any(slacks<=0):raise ValueError('unrecoverable feasible slacks')
    # Use SciPy's exact sparse ordering and the installed AugmentedSystem LS operator.
    shell=object.__new__(BarrierSubproblem);shell.n_vars=len(q);shell.n_ineq=len(slacks);shell.n_eq=0
    A=shell._assemble_sparse_jacobian(csr_array((0,len(q))),C,slacks)
    _,LS,_=projections(A,'AugmentedSystem')
    v=-LS.dot(np.r_[G,np.full(len(slacks),-mu)])
    vg=-v[:m];vd=vg*gp;vb=np.zeros(len(q));vb[:n]=v[m:m+n]-v[m+n:]
    cd=np.asarray(Dz.T@vd).ravel();kkt=G+cd+vb
    return dict(multipliers_transformed=vg.tolist(),multipliers_depth=vd.tolist(),bound_multipliers=vb.tolist(),
        canonical_multipliers=v.tolist(),slacks=slacks.tolist(),G=G.tolist(),C_depth=cd.tolist(),C_bounds=vb.tolist(),
        KKT=kkt.tolist(),KKT_inf=float(np.linalg.norm(kkt,np.inf)),objective=float(r@r),original_depths=z.tolist(),
        complementarity_original=(vd*(z-MARGIN)).tolist(),complementarity_transformed=(vg*g).tolist(),
        complementarity_canonical=(v*slacks).tolist(),barrier_parameter=mu,raw_depth=raw)

def compare(problem,row,rec,raw=False):
    a=RawProblem(problem) if raw else ConstrainedProblem(problem);q=np.asarray(row['x'])/a.scale
    r,J=a.evaluate(q);z,Dz=a.depth(q) if raw else a.raw_depth(q)
    vd=np.asarray(row['multipliers_depth']);vb=np.asarray(row['bound_multipliers'])
    original=2*J.T@r+Dz.T@vd+vb
    values={k:row[k] for k in ['multipliers_depth','bound_multipliers']}
    if not raw:values['multipliers_transformed']=row['multipliers_transformed']
    values.update(C_depth=np.asarray(Dz.T@vd),C_bounds=vb,KKT=original,complementarity_original=vd*(z-MARGIN))
    if not raw:values['complementarity_transformed']=np.asarray(row['multipliers_transformed'])*transform(z-MARGIN)[0]
    errors={}
    for k,v in values.items():
        errors[k]=float(np.max(np.abs(np.asarray(rec[k])-v)))
        np.testing.assert_allclose(rec[k],v,atol=1e-10,rtol=1e-8,err_msg=k)
    np.testing.assert_allclose(rec['objective'],row['objective'],atol=1e-10,rtol=1e-9)
    np.testing.assert_allclose(rec['original_depths'],row['normalized_depths'],atol=1e-12,rtol=1e-12)
    np.testing.assert_allclose(rec['KKT_inf'],row['optimality'],atol=1e-10,rtol=1e-8)
    return errors

def capture_solve(problem,seed=None,source_lag=None,endpoint=None):
    """Wrap only minimize's callback/return; immutable v4 receives identical inputs."""
    import basketball_shared_solver_v4 as old
    original=old.minimize;captured={};states=[]
    def observe(*args,**kwargs):
        callback=kwargs['callback']
        def cb(q,state):
            states.append(dict(x=(q*np.r_[np.full(problem.n_offsets,25.),np.ones(len(q)-problem.n_offsets)]).tolist(),
                v=[np.asarray(v).tolist() for v in state.v],barrier_parameter=float(state.barrier_parameter),iteration=int(state.nit)))
            return callback(q,state)
        kwargs['callback']=cb
        result=original(*args,**kwargs)
        captured.update(v=[np.asarray(v).tolist() for v in result.v],x=result.x.tolist())
        return result
    with patch.object(old,'minimize',observe):row=old.solve(problem,seed,source_lag,endpoint)
    if 'v' in captured:
        row['multipliers_depth'],row['bound_multipliers']=captured['v']
    return row,states

def replay_compare(saved,replayed):
    for key in ['status','nfev']:
        if saved[key]!=replayed[key]:raise ValueError('divergent replay '+key)
    if len(saved['solver_trace'])!=len(replayed['solver_trace']):raise ValueError('divergent replay iteration count')
    for key in ['initial_x','x']:
        np.testing.assert_allclose(saved[key],replayed[key],atol=1e-10,rtol=1e-10,err_msg='divergent replay '+key)
    for old,new in zip(saved['solver_trace'],replayed['solver_trace']):
        if old['iteration']!=new['iteration']:raise ValueError('divergent replay iteration')
        np.testing.assert_allclose(old['x'],new['x'],atol=1e-10,rtol=1e-10,err_msg='divergent replay trace')
        for k in ['objective','optimality','min_depth']:
            atol,rtol=(1e-12,1e-12) if k=='min_depth' else (1e-10,1e-9 if k=='objective' else 1e-8)
            np.testing.assert_allclose(old[k],new[k],atol=atol,rtol=rtol,err_msg='divergent replay '+k)
    for k,atol,rtol in [('objective',1e-10,1e-9),('normalized_depths',1e-12,1e-12),('optimality',1e-10,1e-8)]:
        np.testing.assert_allclose(saved[k],replayed[k],atol=atol,rtol=rtol,err_msg='divergent replay '+k)
    if replayed['nfev']>200 or len(replayed['solver_trace'])>200:raise ValueError('replay cap exceeded')

def validate(p,output):
    records=[]
    for version in [5,6]:
        for path in sorted(Path(f'docs/experiments/basketball-shared-timing-v{version}/pilot').glob('weight*-group*.json.gz')):
            data=compressed_read(path)
            for lag,rows in data['attempts'].items():
                for row in rows:
                    check(p);problem=fixture(data['group_id'],lag,data['weight'],lambda:check(p))
                    rec=reconstruct(problem,row['x'],row['solver_trace'][-1]['barrier_parameter'])
                    try:errors=compare(problem,row,rec);passed=True;error=None
                    except AssertionError as e:errors=None;passed=False;error=str(e)
                    records.append(dict(version=version,source=str(path),lag=lag,start=row['start'],passed=passed,errors=errors,error=error))
    assert len(records)==288
    write(output/'returned-validation.json',dict(passed=all(r['passed'] for r in records),records=records,implementation_sha256=implementation()))
    # Raw-depth synthetic validation uses actual multipliers, including callback states.
    raw=[]
    for lag in [0.,-25.]:
        problem=fixture(2,lag,1.,lambda:check(p));row,states=capture_solve(problem)
        rec=reconstruct(problem,row['x'],row['solver_trace'][-1]['barrier_parameter'],True)
        errors=compare(problem,row,rec,True)
        callback_checks=[]
        for s in states:
            check(p);rec=reconstruct(problem,s['x'],s['barrier_parameter'],True)
            np.testing.assert_allclose(rec['multipliers_depth'],s['v'][0],atol=1e-10,rtol=1e-8)
            np.testing.assert_allclose(rec['bound_multipliers'],s['v'][1],atol=1e-10,rtol=1e-8)
            callback_checks.append(s['iteration'])
        raw.append(dict(lag=lag,row=row,captured=states,errors=errors,callback_checks=callback_checks))
    compressed_write(output/'raw-validation.json.gz',dict(records=raw))
    return all(r['passed'] for r in records)

def recover(p,output,predecessor):
    manifest=compressed_read(predecessor/'diagnostic-manifest.json.gz');verify_hashes(manifest['source_sha256'])
    bound=read(predecessor/'implementation.json')['source_sha256'];verify_hashes(bound)
    validated=validate(p,output)
    evidence=[];replays=0
    for ref in [r for r in manifest['references'] if r['historical']]:
        check(p);s=manifest['states'][ref['state_key']];data=compressed_read(ref['source'])
        row=next(r for r in data['attempts'][ref['lag_key']] if r['start']==ref['start'])
        problem=fixture(s['group_id'],s['lag'],s['weight'],lambda:check(p))
        rec=reconstruct(problem,s['x'],row['solver_trace'][-1]['barrier_parameter'],True)
        # Trace ownership is necessary in addition to the returned scalar check.
        reason=None
        try:
            if not validated:raise ValueError('288-record multiplier validation failed')
            np.testing.assert_array_equal(row['x'],row['solver_trace'][-1]['x'])
            np.testing.assert_allclose(rec['objective'],row['objective'],atol=1e-10,rtol=1e-9)
            np.testing.assert_allclose(rec['original_depths'],row['normalized_depths'],atol=1e-12,rtol=1e-12)
            np.testing.assert_allclose(rec['KKT_inf'],row['optimality'],atol=1e-10,rtol=1e-8)
            kind='reconstructed'
        except (AssertionError,ValueError) as e:kind='unresolved';reason=str(e)
        record=dict(**ref,group_id=s['group_id'],lag=s['lag'],evidence=kind,reconstruction=rec,reconstruction_rejection=reason)
        if kind=='unresolved':
            check(p);replays+=1
            if replays>9:raise ValueError('historical replay cap')
            init=row['initialization_transfer'];seed=None if row['seed_lag'] is None else init['original_x']
            from basketball_shared_solver_v4 import sanitize
            selected,init_check=sanitize(problem,seed,row['seed_lag'],2)
            np.testing.assert_array_equal(selected,row['initial_x'])
            write(output/f'replay-{replays:02d}-started.json',dict(reference=ref,scheduled=1,executed=None,qualified=None,initial_x=selected.tolist()))
            replayed,states=capture_solve(problem,seed,row['seed_lag'],2)
            compressed_write(output/f'replay-{replays:02d}.json.gz',dict(reference=ref,returned=replayed,captured=states))
            try:
                replay_compare(row,replayed)
                record.update(evidence='replayed',replay_index=replays,supplementary_multipliers=dict(multipliers_depth=replayed['multipliers_depth'],bound_multipliers=replayed['bound_multipliers']))
            except (AssertionError,ValueError) as e:record.update(replay_index=replays,replay_rejection=str(e))
        evidence.append(record)
        compressed_write(output/'supplement-progress.json.gz',dict(records=evidence))
    verify_hashes(bound);verify_hashes(manifest['source_sha256'])
    unresolved=[r for r in evidence if r['evidence']=='unresolved']
    compressed_write(output/'supplement.json.gz',dict(records=evidence,implementation_sha256=bound,validated_against_actual_multipliers=validated))
    write(output/'recovery-decision.json',dict(passed=not unresolved,records=9,reconstructed=sum(r['evidence']=='reconstructed' for r in evidence),replayed=sum(r['evidence']=='replayed' for r in evidence),unresolved=len(unresolved),replay_ledger=dict(scheduled=replays,executed=replays,missing=0,qualified=sum(r['evidence']=='replayed' for r in evidence)),historical_parameters_unchanged=True,historical_seeds_forbidden=True))
    return dict(status='blocked' if unresolved else 'passed',terminal_kind='numerical_failure' if unresolved else None,blockers=[dict(group_id=r['group_id'],lag=r['lag'],reason=r.get('replay_rejection',r['reconstruction_rejection'])) for r in unresolved],historical_replays=replays)
