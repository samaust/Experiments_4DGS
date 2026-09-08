"""Admission and signed original-coordinate saved-state diagnosis; never fits."""
from pathlib import Path
import time
import numpy as np
from basketball_audit import sha256
from basketball_scale import read, write
from basketball_continuation_audit import verify_hashes
from basketball_shared_diagnose_v5 import compressed_read, compressed_write
from basketball_shared_curvature_v6 import snapshots, parameter_hash, DiagnosticProblem, stationarity, deterministic_svd, recent_steps
from basketball_shared_solver_v6 import support
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_spline_v2 import SplineProblem
from basketball_shared_verify_v5 import objective_depth, verify_partition
from basketball_shared_verify_v6 import verify_pilot
ROOT=Path('docs/experiments/basketball-shared-timing-v6')

def check(p):
    if time.time() >= p['investigation_started_unix']+1800: raise TimeoutError('30-minute admission/diagnosis deadline')

def prepare(p, output):
    check(p); hashes={}
    for f in sorted(ROOT.rglob('*')):
        if f.is_file(): hashes[str(f)]=sha256(f)
    for f in [ROOT/'evidence.json', ROOT/'prepare/cross-version-manifest.json',ROOT/'pilot/exact-policy-freeze.json',ROOT/'exact-hessian-validation.json',ROOT/'verification-final.json']:
        r=read(f)
        for key in ['source_sha256','artifacts_sha256','test_logs_sha256','markers','docs_sha256']:
            if key in r: verify_hashes(r[key]);hashes.update(r[key])
    old=read('configs/basketball-rev2/timing-shared-v6.json')
    for key in ['fit_frames','target_cameras','held_out_cameras','configurations','injections','audit_windows','roles','previous_frozen','admission','controls','independent_solver','independent_initialization','source_sha256']:
        if p[key]!=old[key]:raise ValueError('inherited policy changed: '+key)
    verify_hashes(p['source_sha256']); hashes.update(p['source_sha256'])
    groups,cameras,_,_=synthetic('direction_changes',0.,-.1,100,groups=12)
    baseline=verify_pilot(ROOT,groups,cameras);check(p)
    manifest=dict(states={},references=[],historical=[],source_sha256=hashes,missing=[],namespace='v7-diagnose',frozen_unix=time.time())
    rows_all=[]
    def add(row,path,lag,gid,weight,label_prefix=''):
        snaps = [dict(label='returned', index=None, x=row['x'], sha256=parameter_hash(row['x']))] if label_prefix else snapshots(row)
        for snap in snaps:
            if label_prefix and snap['label']!='returned':continue
            key=f'{weight}/{gid}/{lag}/{snap["sha256"]}'
            manifest['states'].setdefault(key,dict(x=snap['x'],parameter_sha256=snap['sha256'],parameter_bytes_le_hex=np.asarray(snap['x'],dtype='<f8').tobytes().hex(),group_id=gid,weight=weight,lag=float(lag)))
            manifest['references'].append(dict(state_key=key,source=str(path),source_sha256=sha256(path),lag_key=lag,start=row['start'],label=snap['label'],index=snap['index'],historical=bool(label_prefix),saved_valid=row['valid']))
    for path in sorted((ROOT/'pilot').glob('*.json.gz')):
        state=compressed_read(path);gid=state['group_id'];weight=state['weight']
        for lag,rows in state['attempts'].items():
            for row in rows:
                rows_all.append(dict(group_id=gid,weight=weight,lag=float(lag),start=row['start'],valid=row['valid'],optimality=row['optimality'],iterations=row['solver_trace'][-1]['iteration']))
                try:add(row,path,lag,gid,weight)
                except (ValueError,KeyError) as e:manifest['missing'].append(str(e))
    comparisons=read(ROOT/'pilot/pilot-decision.json')['comparisons']
    failures=[r for r in comparisons if not r['no_worse']]
    assert {(r['group_id'],float(r['lag']),r['weight']) for r in failures}=={(g,l,1.) for g in [2,9,11] for l in [-25.,-20.,-19.]}
    for f in failures:
        gid=f['group_id'];lag=str(float(f['lag']));candidates=[]
        paths=[Path(f'docs/experiments/basketball-shared-timing-v4/regularized-group{gid:02d}.json.gz'),Path(f'docs/experiments/basketball-shared-timing-v5/pilot/weight1.0-group{gid:02d}.json.gz')]
        for path in paths:
            hashes[str(path)]=sha256(path)
            candidates.extend((r['objective'],str(path),r) for r in compressed_read(path)['attempts'].get(lag,[]) if r['valid'])
        _,path,row=min(candidates,key=lambda x:x[:2]);add(row,Path(path),lag,gid,1.,'historical')
        manifest['historical'].append(dict(group_id=gid,lag=float(lag),source=path,start=row['start'],objective=row['objective'],nuisance_offset=row['x'][0]))
        absent=[k for k in ['multipliers_depth','bound_multipliers'] if row.get(k) is None]
        if absent:manifest['missing'].append(dict(group_id=gid,lag=float(lag),source=path,start=row['start'],fields=absent,reason='lowest qualified historical returned state lacks saved multipliers'))
    baseline.update(regularized_qualified=sum(r['valid'] for r in rows_all if r['weight']),data_only_qualified=sum(r['valid'] for r in rows_all if not r['weight']),failed_iterations=sorted({r['iterations'] for r in rows_all if not r['valid']}),attempts_detail=rows_all)
    assert baseline['regularized_qualified']==72 and baseline['data_only_qualified']==22 and baseline['failed_iterations']==[200]
    assert baseline['three_start_disagreements']==5 and baseline['qualified_reference_failures']==9 and baseline['required_transfers']==[True]*3+[False]*3
    manifest['source_sha256']=hashes
    write(output/'baseline.json',baseline)
    compressed_write(output/'diagnostic-manifest.json.gz',manifest)
    write(output/'cross-version-manifest.json',dict(source_sha256=hashes,partition=verify_partition(p),authoritative_solver=read(ROOT/'pilot/exact-policy-freeze.json')['solver'],generic_workflow_solver_metadata_authoritative=False))
    write(output/'experiments-freeze.json',dict(policy=p['v7'],groups=p['pilot_groups'],lags=p['pilot_lags'],conditioning_attempts=144,scalar_initial_attempts=7344,historical_states_diagnostic_only=True))
    return dict(status='passed',terminal_kind=None,blockers=[],evidence_complete=not manifest['missing'],missing_evidence=manifest['missing'],scientific_continuation_permitted=not manifest['missing'])

def diagnose(p,output,predecessor):
    manifest=compressed_read(predecessor/'diagnostic-manifest.json.gz');verify_hashes(manifest['source_sha256'])
    groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    cache={};results=[];max_cost=0.;max_depth=0.
    for ref in manifest['references']:
        check(p);s=manifest['states'][ref['state_key']];source=ref['source']
        if source not in cache:cache[source]=compressed_read(source)
        row=next(r for r in cache[source]['attempts'][ref['lag_key']] if r['start']==ref['start'])
        problem=SplineProblem([groups[s['group_id']]],cameras,{1:0.,2:s['lag'],3:0.},window,10,s['weight'],(1,2),lambda:check(p))
        a=DiagnosticProblem(problem);q=np.asarray(s['x'])/a.scale;r,J,G=a.evaluate(q)
        cost,depth=objective_depth(groups,cameras,row,s['x'],s['lag'])
        if ref['historical'] and row.get('multipliers_depth') is None:
            stat=historical_stationarity(a,q,G,row)
        else:stat=stationarity(a,q,G,row,ref['label'],ref['index'])
        saved=row if ref['index'] is None else row['solver_trace'][ref['index']]
        np.testing.assert_allclose(cost,saved['objective'],rtol=1e-9,atol=1e-10)
        np.testing.assert_allclose(cost,r@r,rtol=1e-9,atol=1e-10);np.testing.assert_allclose(depth,stat['original_depths'],rtol=1e-12,atol=1e-12)
        max_cost=max(max_cost,abs(cost-r@r));max_depth=max(max_depth,float(np.max(np.abs(depth-stat['original_depths']))))
        spectra={}
        for label,jac in [('data',J[:problem.n*2]),('objective_coefficients',J[:,problem.n_offsets:])]:
            sv,V,tol,sub=deterministic_svd(jac);vector=q if label=='data' else q[problem.n_offsets:]
            spectra[label]=dict(singular_values=sv.tolist(),rank_threshold=tol,rank=int(sum(sv>tol)),subspaces=sub,parameter_projections=(V@vector).tolist(),gradient_projections=(V@(G if label=='data' else G[problem.n_offsets:])).tolist(),exact_zero_columns=np.flatnonzero(np.all(jac==0,axis=0)).tolist())
        offsets,coeff=problem.unpack(np.asarray(s['x']));observed=[]
        for obs in problem.groups[0]['observations']:
            t=(obs['frames']-offsets[obs['camera_id']])/25
            observed.append(dict(camera_id=obs['camera_id'],xyz=(problem.spline(t)@coeff[0]).tolist()))
        steps=recent_steps(row,ref['index'],a.scale)
        results.append(dict(**ref,group_id=s['group_id'],weight=s['weight'],lag=s['lag'],objective=cost,nuisance_offset=s['x'][0],stationarity=stat,spectra=spectra,support=support(problem,np.asarray(s['x'])),observed=observed,coefficient_norm=float(np.linalg.norm(q[problem.n_offsets:])),saved_steps=[dict(q_step=v.tolist(),observable_linear_change=(J[:problem.n*2]@v).tolist()) for v in steps],trust_radius=saved.get('trust_radius',row['solver_trace'][-1]['trust_radius']),barrier_parameter=stat['barrier_parameter']))
    pairs=[]
    for old in [r for r in results if r['historical']]:
        returned=[r for r in results if not r['historical'] and r['label']=='returned' and (r['group_id'],r['weight'],r['lag'])==(old['group_id'],old['weight'],old['lag'])]
        new=min(returned,key=lambda r:r['objective'])
        pairs.append(dict(group_id=old['group_id'],lag=old['lag'],reference_state=old['state_key'],v6_state=new['state_key'],reference_cost=old['objective'],v6_cost=new['objective'],reference_nuisance=old['nuisance_offset'],v6_nuisance=new['nuisance_offset'],nuisance_separation=abs(old['nuisance_offset']-new['nuisance_offset']),trajectory_difference_norm=float(np.linalg.norm(np.concatenate([np.asarray(a['xyz'])-b['xyz'] for a,b in zip(old['observed'],new['observed'])]))),reference_kkt=old['stationarity'].get('KKT_inf'),reference_saved_kkt=old['stationarity'].get('saved_KKT_inf'),v6_kkt=new['stationarity']['KKT_inf']))
    compressed_write(output/'states.json.gz',dict(records=results))
    assert len(results)==441 and len(pairs)==9
    # Reuse the exact checked v5 analytical audit without constructing new rays.
    write(output/'escape-reuse.json',dict(status='unassessed',reason='missing required returned multipliers blocks scientific continuation; no reuse invoked',prior_verification_sha256=sha256(ROOT/'v5-reuse-verification.json'),ray_grid_enlarged=False))
    decision=dict(passed=not manifest['missing'],blockers=manifest['missing'],references=441,attempt_references=432,historical_references=9,maximum_objective_error=max_cost,maximum_depth_error=max_depth,pairs=pairs,interpretation='Separated stationary states support different nuisance basins, not certified global minima. Full spectra, support, saved motion and signed barrier terms do not establish conditioning efficacy.',intermediate_multiplier_KKT='unavailable: callbacks omit multipliers',scientific_fits=0)
    write(output/'diagnostic-decision.json',decision)
    return dict(status='blocked' if manifest['missing'] else 'passed',terminal_kind='numerical_failure' if manifest['missing'] else None,blockers=manifest['missing'])


def historical_stationarity(a,q,gradient,row):
    """v4 used raw depth bounds: its barrier is not the v5/v6 barrier."""
    depth,Dz=a.a.raw_depth(q);mu=row['solver_trace'][-1]['barrier_parameter']
    barrier=np.asarray(-mu*Dz.T@(1/(depth-1e-8))).ravel()
    b=np.zeros_like(q);free=q[:a.p.n_offsets]
    b[:len(free)]=mu*(1/(1-free)-1/(1+free))
    return dict(original_depths=depth.tolist(),G=gradient.tolist(),G_inf=float(np.max(np.abs(gradient))),
                B_depth=barrier.tolist(),B_depth_inf=float(np.max(np.abs(barrier))),B_bounds=b.tolist(),B_bounds_inf=float(np.max(np.abs(b))),
                barrier_parameter=mu,barrier_form='v4 raw-depth inequality',multiplier_KKT_available=False,
                multiplier_KKT_reason='v4 did not serialize returned multipliers; required evidence missing',
                C_depth=None,C_bounds=None,KKT=None,KKT_inf=None,saved_KKT_inf=row['optimality'],
                saved_KKT_independently_recomputed=False)
