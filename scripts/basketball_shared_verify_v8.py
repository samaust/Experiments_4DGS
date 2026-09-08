"""Independent dense least-squares and physical-geometry supplement verification."""
from pathlib import Path
import numpy as np
from scipy.interpolate import BSpline
from basketball_scale import read,write
from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes
from basketball_shared_diagnose_v5 import compressed_read
from basketball_shared_recovery_v8 import fixture,check
from basketball_shared_solver_v4 import ConstrainedProblem
from basketball_shared_verify_v5 import objective_depth
from basketball_shared_synthetic_v2 import synthetic

def verify_recovery(p,root,output):
    check(p);supp=compressed_read(root/'supplement.json.gz');verify_hashes(supp['implementation_sha256'])
    assert supp['validated_against_actual_multipliers']
    validation=read(root/'returned-validation.json');assert validation['passed'] and len(validation['records'])==288
    groups,cameras,_,_=synthetic('direction_changes',0.,-.1,100,groups=12)
    errors=[]
    for ref in supp['records']:
        check(p);assert sha256(ref['source'])==ref['source_sha256']
        row=next(r for r in compressed_read(ref['source'])['attempts'][ref['lag_key']] if r['start']==ref['start'])
        problem=fixture(ref['group_id'],ref['lag'],1.,lambda:check(p));a=ConstrainedProblem(problem);q=np.asarray(row['x'])/a.scale
        r,J=a.evaluate(q);z,D=a.depth(q);G=np.asarray(2*J.T@r).ravel();n=problem.n_offsets
        I=np.eye(len(q))[:n];C=np.vstack([-D.toarray(),I,-I]);b=np.nextafter(1.,np.inf)
        s=np.r_[z-1e-8,b-q[:n],q[:n]+b]
        A=np.hstack([C,np.diag(s)]);mu=row['solver_trace'][-1]['barrier_parameter']
        # Independent dense SVD solve, without SciPy's projections or recovery assembly.
        v=np.linalg.lstsq(A.T,-np.r_[G,np.full(len(s),-mu)],rcond=None)[0]
        rec=ref['reconstruction'];np.testing.assert_allclose(v,rec['canonical_multipliers'],atol=1e-10,rtol=1e-8)
        vd=-v[:len(z)];vb=np.zeros(len(q));vb[:n]=v[len(z):len(z)+n]-v[len(z)+n:]
        for name,value in [('C_depth',D.T@vd),('C_bounds',vb),('KKT',G+D.T@vd+vb),('complementarity_canonical',v*s)]:
            np.testing.assert_allclose(value,rec[name],atol=1e-10,rtol=1e-8)
        cost,depth=objective_depth(groups,cameras,row,row['x'],ref['lag'])
        np.testing.assert_allclose(cost,rec['objective'],atol=1e-10,rtol=1e-9)
        np.testing.assert_allclose(depth,rec['original_depths'],atol=1e-12,rtol=1e-12)
        np.testing.assert_allclose(np.max(np.abs(G+D.T@vd+vb)),row['optimality'],atol=1e-10,rtol=1e-8)
        errors.append(float(np.max(np.abs(v-rec['canonical_multipliers']))))
    assert len(errors)==9
    write(output,dict(status='passed',historical_states=9,dense_multiplier_maximum_error=max(errors),supplement_sha256=sha256(root/'supplement.json.gz'),verifier_sha256=sha256(__file__)))

def verify_escape(p,output):
    """Unchanged v5 verifier's analytical audit, with the fresh outer deadline."""
    root=Path('docs/experiments/basketball-shared-timing-v5')
    groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    unpack=compressed_read
    pm=read(root/'diagnose-final/pilot-manifest.json');verify_hashes(pm['source_sha256'])
    assert pm['groups']==[2,9,11] and pm['lags']==[-25.,-20.,-19.,-7.,-6.,-.1,0.,25.]
    assert pm['scheduled_attempts']==144 and len(pm['historical'])==12
    verify_hashes({r['path']:r['sha256'] for r in pm['historical']})
    rays=unpack(root/'diagnose-final/escape-audit.json.gz')['records'];assert len(rays)==len(pm['rays'])==172
    assert sum(len(r['probes']) for r in rays)==3956
    # Independently evaluate homogeneous projective limits with scalar BSpline trajectories.
    max_limit_error=0.;finite_precision_rows=0;endpoint_checks=[]
    for ray,row in zip(pm['rays'],rays):
        check(p);gid=ray['group_id'];base=np.asarray(ray['base']);delta=np.asarray(ray['direction'])
        from basketball_shared_spline_v2 import basis
        knots=basis(window,10)[0].t
        co=BSpline(knots,base[1:].reshape(18,3),3);dc=BSpline(knots,delta[1:].reshape(18,3),3)
        camera_centers=np.array([-np.asarray(c['R']).T@c['t'] for c in cameras.values()]);center=camera_centers.mean(axis=0)
        diameter=float(np.max(np.linalg.norm(camera_centers[:,None]-camera_centers[None,:],axis=2)))
        errors=[];slopes=[];static_depth=[];zero=True;transition=0.
        for obs in groups[gid]['observations']:
            cam=cameras[obs['camera_id']];off=ray['offsets'][str(obs['camera_id'])]
            t=(obs['frames']-off)/25;xyz=(co(t)*diameter+center)@np.asarray(cam['R']).T+cam['t']
            motion=dc(t)*diameter@np.asarray(cam['R']).T
            zero=zero and bool(np.all(motion==0));slopes.extend(motion[:,2])
            static_depth.extend(xyz[motion[:,2]==0,2]/diameter)
            uv=xyz[:,:2]/xyz[:,2,None];moving=motion[:,2]!=0
            if moving.any():transition=max(transition,float(np.max(np.abs(xyz[moving,2]/motion[moving,2]))))
            uv[moving]=motion[moving,:2]/motion[moving,2,None]
            pred=(uv*(1+cam['parameters_colmap'][3]*np.sum(uv**2,axis=1))[:,None])@np.asarray(cam['K'])[:2,:2].T+np.asarray(cam['K'])[:2,2]
            errors.extend(np.sum((pred-obs['xy'])**2,axis=1))
        data_limit=float(np.mean(2*(np.sqrt(1+np.asarray(errors))-1)));limit=data_limit
        quad=np.arange(25,175)/25
        limit+=ray['weight']*float(np.sum(co.derivative(2)(quad)**2))/len(quad)
        if row['original_objective_limit'] is not None:
            max_limit_error=max(max_limit_error,abs(limit-row['original_objective_limit']))
            np.testing.assert_allclose(limit,row['original_objective_limit'],rtol=1e-9,atol=1e-10)
        feasible=min(slopes)>=0 and (not static_depth or min(static_depth)>=1e-8)
        assert feasible==row['ray_eventually_depth_feasible']
        classification=row['classification']
        if classification=='exactly_unsupported_invariant':assert zero and ray['weight']==0
        elif classification=='infeasible_ray':assert not feasible
        elif classification=='observable_limit_worse_than_feasible_finite':
            assert limit>row['finite_feasible_reference']+1e-6+1e-4*max(abs(limit),abs(row['finite_feasible_reference']))
        else:raise AssertionError('unresolved audited direction')
        assert [r['amplitude'] for r in row['probes']]==pm['amplitudes']
        finite_precision_rows+=int(ray['weight']!=0 and row['probes'][-1]['acceleration_cost']>1e10)
        if feasible and row['limit_exists']:
            endpoint=row['probes'][-1];gap=abs(endpoint['data_objective']-data_limit)
            tolerance=1e-6+1e-4*max(abs(data_limit),abs(endpoint['data_objective']))
            if gap>tolerance:
                # Near-knot samples can need amplitudes larger than the diagnostic cap.
                # This follows from z(a)=z0+a*dz; no new ray or amplitude is evaluated.
                assert transition/endpoint['amplitude']>1e-3
            endpoint_checks.append(dict(ray_id=row['ray_id'],data_limit=data_limit,
                final_amplitude=endpoint['amplitude'],data_objective=endpoint['data_objective'],absolute_gap=gap,
                within_tolerance=gap<=tolerance,largest_depth_transition_amplitude=transition,
                explanation='finite endpoint agrees' if gap<=tolerance else 'weak individual sample depth slope delays asymptotics beyond the fixed probe range'))
    write(output,dict(status='passed',analytical_rays=172,probes=3956,ray_grid_enlarged=False,maximum_limit_error=max_limit_error,finite_endpoint_checks=endpoint_checks,finite_precision_rows=finite_precision_rows,source_verifier_sha256=sha256('scripts/basketball_shared_verify_v5.py')))

def verify_package(root,output):
    import re,time
    p=read('configs/basketball-rev2/timing-shared-v8.json')
    if output.exists():raise FileExistsError('fresh verification output required')
    stages={}
    for f in sorted(root.glob('*/result.json')):
        r=read(f);verify_hashes(r['source_sha256']);verify_hashes(r['artifacts_sha256']);stages[r['stage']]=r['status']
        assert r['accepted_timing'] is None and r['candidate_offsets'] is None and r['final_protocol'] is None
        assert not r['selection_consumed_this_attempt'] and not r['final_validation_consumed']
    old=read('docs/experiments/basketball-shared-timing-v7/evidence.json');verify_hashes(old['source_sha256']);verify_hashes(old['artifacts_sha256'])
    markers=read('docs/experiments/basketball-shared-timing-v6/verification-final.json')['markers'];verify_hashes(markers)
    logs={};tests={}
    for name in ['v8','basketball','budget','selfcap']:
        f=root/f'{name}-tests.log';t=f.read_text();assert re.search(r'\nOK\s*$',t),name
        tests[name]=int(re.search(r'Ran (\d+) tests?',t).group(1));logs[str(f)]=sha256(f)
    elapsed=time.time()-p['investigation_started_unix'];assert elapsed<14400
    write(output,dict(status='passed',stage_statuses=stages,tests=tests,test_logs_sha256=logs,markers=markers,immutable_v2_v7_hashes_verified=True,elapsed_seconds=elapsed,within_four_hours=True,verifier_sha256=sha256(__file__),accepted_timing=None))

if __name__=='__main__':
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();verify_package(args.root,args.output)
