"""Independent evidence arithmetic and immutable-admission verification for Plan 012."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import time
import numpy as np
from basketball_audit import sha256
from basketball_scale import read, write
from basketball_continuation_audit import verify_hashes
from basketball_shared_diagnose_v5 import compressed_read
from basketball_shared_verify_v5 import objective_depth, verify_partition
from basketball_shared_synthetic_v2 import synthetic


def verify(root, output):
    if output.exists():
        raise FileExistsError('fresh verification output required')
    config = read('configs/basketball-rev2/timing-shared-v6.json')
    manifest = compressed_read(root/'prepare/diagnostic-manifest.json.gz')
    verify_hashes(manifest['source_sha256'])
    for stage in ['prepare', 'diagnose', 'pilot', 'package']:
        result = read(root/stage/'result.json')
        verify_hashes(result['source_sha256']); verify_hashes(result['artifacts_sha256'])
    decision = read(root/'diagnose/diagnostic-decision.json')
    assert decision['manifest_sha256'] == sha256(root/'prepare/diagnostic-manifest.json.gz')
    groups, cameras, _, _ = synthetic('direction_changes', 0., -.1, 100, groups=12)
    references = {r['reference']: r for r in manifest['references']}
    original = {}; checked = 0; returned = 0; stable = 0; probes = 0; levels = 0; witnesses = set()
    maximum_objective_error = 0.; maximum_depth_error = 0.; gradient_error = 0.; kkt_error = 0.
    for artifact in decision['artifacts']:
        path = root/'diagnose'/artifact['path']; assert sha256(path) == artifact['sha256']
        for record in compressed_read(path)['records']:
            reference = references[record['reference']]; state = manifest['states'][reference['state_key']]
            raw = bytes.fromhex(state['parameter_bytes_le_hex'])
            import hashlib
            assert hashlib.sha256(raw).hexdigest() == state['parameter_sha256']
            np.testing.assert_array_equal(np.frombuffer(raw, dtype='<f8'), state['x'])
            if reference['source'] not in original:
                original[reference['source']] = compressed_read(reference['source'])
            row = next(r for r in original[reference['source']]['attempts'][reference['lag_key']] if r['start'] == reference['start'])
            cost, depth = objective_depth(groups, cameras, row, state['x'], state['lag'])
            analysis = record['analysis']; stat = analysis['stationarity']
            np.testing.assert_allclose(cost, analysis['objective'], rtol=1e-9, atol=1e-10)
            np.testing.assert_allclose(depth, stat['original_depths'], rtol=1e-12, atol=1e-12)
            maximum_objective_error = max(maximum_objective_error, abs(cost-analysis['objective']))
            maximum_depth_error = max(maximum_depth_error, float(np.max(np.abs(depth-stat['original_depths']))))
            # Independently differentiate the direct robust point loss through camera
            # geometry and spline basis, without using the robust residual Jacobian.
            from scipy.interpolate import BSpline
            basis = BSpline(row['knots'], np.eye(18), 3, extrapolate=False)
            coeff = np.asarray(state['x'][1:]).reshape(18,3)
            offsets = {1:0., 2:state['lag'], 3:state['x'][0]}; G = np.zeros(55)
            observations = groups[state['group_id']]['observations']; N = sum(len(o['frames']) for o in observations)
            for obs in observations:
                cam = cameras[obs['camera_id']]; t = (obs['frames']-offsets[obs['camera_id']])/25
                B = basis(t); xyz = (B@coeff*row['diameter']+row['center'])@np.asarray(cam['R']).T+cam['t']
                u = xyz[:,:2]/xyz[:,2,None]; k = cam['parameters_colmap'][3]; K = np.asarray(cam['K'])
                pred = (u*(1+k*np.sum(u*u,axis=1))[:,None])@K[:2,:2].T+K[:2,2]
                e = pred-obs['xy']; b = 2*e/(N*np.sqrt(1+np.sum(e*e,axis=1)))[:,None]
                radial = (1+k*np.sum(u*u,axis=1))[:,None,None]*np.eye(2)+2*k*u[:,:,None]*u[:,None,:]
                perspective = np.zeros((len(t),2,3));perspective[:,0,0]=1/xyz[:,2];perspective[:,1,1]=1/xyz[:,2]
                perspective[:,:,2]=-u/xyz[:,2,None]
                image_jac = np.einsum('ab,nbc,ncd,de->nae',K[:2,:2],radial,perspective,np.asarray(cam['R']))*row['diameter']
                spatial = np.einsum('na,nab->nb',b,image_jac)
                G[1:] += (B.T@spatial).ravel()
                if obs['camera_id'] == 3:
                    G[0] -= np.sum(spatial*(basis.derivative()(t)@coeff))
            A = basis.derivative(2)(np.arange(25,175)/25)
            G[1:] += (2*state['weight']/150*A.T@(A@coeff)).ravel()
            np.testing.assert_allclose(G, analysis['analytic_gradient'], rtol=1e-9, atol=1e-10)
            gradient_error=max(gradient_error,float(np.max(np.abs(G-analysis['analytic_gradient']))))
            if reference['label'] == 'returned':
                returned += 1
                kkt = G+stat['C_depth']+np.asarray(stat['C_bounds'])
                np.testing.assert_allclose(kkt, stat['KKT'], rtol=1e-8, atol=1e-10)
                kkt_error=max(kkt_error,abs(np.max(np.abs(kkt))-row['optimality']))
                mu=stat['barrier_parameter']; s=depth-1e-8; g=s/np.hypot(1,s)
                vd=np.asarray(row['multipliers_depth']); vg=np.asarray(row['multipliers_transformed'])
                np.testing.assert_allclose(vd,vg/(1+s*s)**1.5,rtol=1e-12,atol=1e-12)
                np.testing.assert_allclose(stat['complementarity_transformed'],vg*g,rtol=1e-12,atol=1e-12)
                np.testing.assert_allclose(stat['complementarity_original'],vd*s,rtol=1e-12,atol=1e-12)
            else:
                assert not stat['multiplier_KKT_available'] and 'KKT' not in stat
            for p in analysis['probes']:
                probes += 1; levels += len(p['levels'])
                assert [v['nominal_step'] for v in p['levels']] == [1e-3,1e-4,1e-5,1e-6]
                v=np.asarray(p['vector']);np.testing.assert_allclose(v@v,1.,atol=1e-12)
                for level in p['levels']:
                    assert 0 <= level['halvings'] <= 20
                    assert level['actual_step'] == level['nominal_step']*2**-level['halvings']
                if p['selected'] is not None:
                    stable += 1; selected=p['selected']; level=p['levels'][selected['level']]
                    previous=p['levels'][level['predecessor_level']]
                    assert max(level['actual_step'],previous['actual_step'])/min(level['actual_step'],previous['actual_step'])>=2
                    u=np.asarray(level['action']);up=np.asarray(previous['action']);GN=np.asarray(p['GN_action'])
                    E=float(np.max(np.abs(u-up)));M=float(np.max(np.abs(u-GN)));rho=M/max(np.max(np.abs(u)),np.max(np.abs(GN)),1e-12)
                    assert E <= 1e-7+1e-3*max(np.max(np.abs(u)),np.max(np.abs(up)))
                    np.testing.assert_allclose([E,M,rho],[selected[k] for k in ['E','M','rho']],rtol=1e-12,atol=1e-12)
                    screen=bool(rho>=.1 and M>10*E+1e-7)
                    assert selected['missing_curvature_screen']==screen
                    if screen and reference['label']=='returned' and not reference['saved_valid'] and not p['exactly_data_null'] and any(s=='gradient' or s.startswith('saved_step') for s in p['labels']):
                        witnesses.add(reference['group_id'])
            checked += 1
    assert checked == 432 and returned == 144
    assert sorted(witnesses) == sorted(int(k) for k in decision['witnesses'])
    if decision['passed']:
        assert witnesses == {2,9,11} and not decision['derivative_discrepancies']
    pilot_checks = verify_pilot(root, groups, cameras)
    terminal = read(root/'package/result.json')
    assert terminal['accepted_timing'] is None and terminal['candidate_offsets'] is None
    assert not terminal['selection_consumed_this_attempt'] and not terminal['final_validation_consumed']
    markers={str(f):sha256(f) for f in Path('.local/calibration/basketball-rev2').rglob('*consumed*.json')}
    assert list(markers)==['.local/calibration/basketball-rev2/timing-selection/run/selection-consumed.json']
    tests={};logs={}
    for name in ['basketball','budget','selfcap']:
        f=root/('basketball-final-tests.log' if name=='basketball' else f'{name}-tests.log'); text=f.read_text();assert re.search(r'\nOK\s*$',text)
        tests[name]=int(re.search(r'Ran (\d+) tests?',text).group(1));logs[str(f)]=sha256(f)
    docs=['docs/contender-experiments.md','docs/experiments/contender-summary.md',
          'docs/experiments/basketball-rev2.md','docs/experiments/basketball-shared-timing-v6.md']
    links=0
    for name in docs:
        file=Path(name)
        for link in re.findall(r'\]\(([^)]+)\)',file.read_text()):
            link=link.split('#')[0]
            if not link or '://' in link:continue
            links+=1;assert (file.parent/link).resolve()==output.resolve() or (file.parent/link).exists(),(name,link)
    subprocess.run(['git','diff','--check'],check=True);subprocess.run(['git','diff','--cached','--check'],check=True)
    elapsed=time.time()-config['investigation_started_unix'];assert elapsed<14400
    write(output,dict(status='passed',verifier_sha256=sha256(__file__),diagnostic_decision_sha256=sha256(root/'diagnose/diagnostic-decision.json'),
          partition=verify_partition(config),pilot=pilot_checks,references=checked,returned_states=returned,probes=probes,ladder_levels=levels,
          stable_probes=stable,maximum_original_objective_error=maximum_objective_error,maximum_original_depth_error=maximum_depth_error,
          maximum_independent_direct_loss_gradient_error=gradient_error,maximum_original_KKT_norm_error=kkt_error,
          tests=tests,test_logs_sha256=logs,historical_hashes_verified=True,markers=markers,documentation_links=links,
          docs_sha256={f:sha256(f) for f in docs},working_tree_diff_check='passed',staged_diff_check='passed',
          elapsed_seconds=elapsed,within_four_hours=True,accepted_timing=None))

def verify_pilot(root, groups, cameras):
    from basketball_shared_solver_v4 import ConstrainedProblem as Original
    from basketball_shared_spline_v2 import SplineProblem
    from basketball_shared_solver_v3 import objective_agreement
    decision=read(root/'pilot/pilot-decision.json')
    freeze=read(root/'pilot/exact-policy-freeze.json');verify_hashes(freeze['source_sha256'])
    validation=read(root/'exact-hessian-validation.json');verify_hashes(validation['source_sha256'])
    assert validation['passed'] and validation['escape_verified']
    attempts=0;qualified=0;seeds=0;max_kkt_error=0.;max_cost_error=0.;comparisons=[];transfers=[]
    for artifact in decision['artifacts']:
        path=root/'pilot'/artifact['path'];assert sha256(path)==artifact['sha256'];state=compressed_read(path)
        gid=state['group_id'];weight=state['weight']
        v5=compressed_read(Path('docs/experiments/basketball-shared-timing-v5/pilot')/artifact['path'])
        v4=compressed_read(Path('docs/experiments/basketball-shared-timing-v4')/f'{"regularized" if weight else "data_only"}-group{gid:02d}.json.gz')
        for lag,rows in state['attempts'].items():
            assert [r['start'] for r in rows]==['cold','ascending','descending']
            costs=[]
            for row in rows:
                attempts+=1;qualified+=row['valid']
                assert row['nfev']<=200 and row['solver_trace'][-1]['iteration']<=200
                assert row['objective_hessian_calls']>=row['objective_hessian_assemblies']>0
                problem=SplineProblem([groups[gid]],cameras,{1:0.,2:float(lag),3:0.},row['window'],10,weight,(1,2))
                a=Original(problem);q=np.asarray(row['x'])/a.scale;r,J=a.evaluate(q);z,D=a.depth(q)
                objective,depth=objective_depth(groups,cameras,row,row['x'],float(lag))
                np.testing.assert_allclose(objective,row['objective'],rtol=1e-9,atol=1e-10)
                np.testing.assert_allclose(depth,row['normalized_depths'],rtol=1e-12,atol=1e-12)
                costs.append(objective);max_cost_error=max(max_cost_error,abs(objective-row['objective']))
                vd=np.asarray(row['multipliers_depth']);vg=np.asarray(row['multipliers_transformed']);s=depth-1e-8
                np.testing.assert_allclose(vd,vg/(1+s*s)**1.5,rtol=1e-12,atol=1e-12)
                KKT=np.asarray(2*J.T@r+D.T@vd+row['bound_multipliers']).ravel()
                optimality=float(np.max(np.abs(KKT)));np.testing.assert_allclose(optimality,row['optimality'],rtol=1e-8,atol=1e-10)
                max_kkt_error=max(max_kkt_error,abs(optimality-row['optimality']))
                if row['valid']:
                    assert row['converged'] and optimality<=1e-6 and min(depth)>1e-7 and not row['boundary_cameras']
                init=row['initialization_transfer'];np.testing.assert_array_equal(init['cold_x'],problem.x0)
                original=np.asarray(init['original_x']);sanitized=original.copy()
                if row['start']!='cold':
                    source=next(r for r in state['attempts'][str(float(row['seed_lag']))] if r['start']==row['seed_start'])
                    assert source['valid'];np.testing.assert_array_equal(original,source['x'])
                    assert row['seed_problem_key']==row['problem_key']==state['problem_key'];seeds+=1
                for block in init['replaced_blocks']:
                    i=1+3*block['block'];sanitized[i:i+3]=problem.x0[i:i+3]
                np.testing.assert_array_equal(sanitized,init['sanitized_x'])
                f=init['blend_fraction'];expected=problem.x0 if f==0 else sanitized if f==1 else problem.x0+f*(sanitized-problem.x0)
                np.testing.assert_array_equal(expected,row['initial_x'])
                _,initial_depth=objective_depth(groups,cameras,row,expected,float(lag));assert min(initial_depth)>2e-8
            refs=[r['objective'] for old in [v4,v5] for r in old['attempts'].get(str(float(lag)),[]) if r['valid']]
            ref=min(refs) if refs else None;best=min(costs)
            comparisons.append(dict(group_id=gid,weight=weight,lag=float(lag),agreement=all(objective_agreement(costs[0],v) for v in costs),
                                    no_worse=ref is None or best<=ref or objective_agreement(best,ref)))
        source,destination,direction=(-20.,-19.,'ascending') if gid==2 else (-6.,-7.,'descending')
        row=next(r for r in state['attempts'][str(destination)] if r['start']==direction)
        transfers.append(bool(row['valid'] and row['seed_lag']==source))
    assert attempts==144 and qualified==decision['qualified']==94
    assert [r['agreement'] for r in comparisons]==[r['three_start_agreement'] for r in decision['comparisons']]
    assert [r['no_worse'] for r in comparisons]==[r['no_worse'] for r in decision['comparisons']]
    assert transfers==[r['verified'] for r in decision['required_transfers']]
    return dict(attempts=attempts,qualified=qualified,seed_checks=seeds,maximum_original_cost_error=max_cost_error,
                maximum_original_KKT_error=max_kkt_error,three_start_disagreements=sum(not r['agreement'] for r in comparisons),
                qualified_reference_failures=sum(not r['no_worse'] for r in comparisons),required_transfers=transfers,
                exact_hessian_policy_hashes_verified=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();verify(a.root,a.output)
