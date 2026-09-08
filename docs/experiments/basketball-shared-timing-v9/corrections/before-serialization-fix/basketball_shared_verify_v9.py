"""Independent physical arithmetic, raw-depth stationarity and numerical-entry verification."""
from pathlib import Path
import numpy as np
from scipy.interpolate import BSpline
from basketball_scale import read,write
from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes
from basketball_shared_accounting_v9 import reconcile
from basketball_shared_diagnose_v9 import make_problem
from basketball_shared_solver_v4 import ConstrainedProblem
from basketball_shared_verify_v5 import objective_depth,verify_partition
from basketball_shared_synthetic_v2 import synthetic


def direct_gradient(problem,x):
    """Differentiate the point loss directly, independently of residual square roots."""
    offsets,coeff=problem.unpack(x);G=np.zeros(len(x));N=problem.n
    for gi,g in enumerate(problem.groups):
        sl=slice(problem.n_offsets+gi*problem.nc*3,problem.n_offsets+(gi+1)*problem.nc*3)
        for obs in g['observations']:
            cam=problem.cameras[obs['camera_id']];t=(obs['frames']-offsets[obs['camera_id']])/25
            B=problem.spline(t);xyz=(B@coeff[gi]*problem.diameter+problem.center)@np.asarray(cam['R']).T+cam['t']
            u=xyz[:,:2]/xyz[:,2,None];k=cam['parameters_colmap'][3];K=np.asarray(cam['K'])
            pred=(u*(1+k*np.sum(u*u,axis=1))[:,None])@K[:2,:2].T+K[:2,2]
            e=pred-obs['xy'];b=2*e/(N*np.sqrt(1+np.sum(e*e,axis=1)))[:,None]
            radial=(1+k*np.sum(u*u,axis=1))[:,None,None]*np.eye(2)+2*k*u[:,:,None]*u[:,None,:]
            perspective=np.zeros((len(t),2,3));perspective[:,0,0]=1/xyz[:,2];perspective[:,1,1]=1/xyz[:,2];perspective[:,:,2]=-u/xyz[:,2,None]
            image=np.einsum('ab,nbc,ncd,de->nae',K[:2,:2],radial,perspective,np.asarray(cam['R']))*problem.diameter
            spatial=np.einsum('na,nab->nb',b,image);G[sl]+=(B.T@spatial).ravel()
            if obs['camera_id'] in problem.index:G[problem.index[obs['camera_id']]]-=np.sum(spatial*(problem.spline.derivative()(t)@coeff[gi]))
        G[sl]+=(2*problem.weight/problem.nacc*problem.accel.T@(problem.accel@coeff[gi])).ravel()
    return G


def verify_row(ref,row):
    if not row.get('executed',True):
        assert not row['valid'] and row.get('x') is None
        return dict(passed=True,executed=False,KKT=None)
    ledger=reconcile(row['accounting']);assert row['nfev']==ledger['states'] and row['iterations']<=200
    if row.get('x') is None:
        assert not row['valid']
        return dict(passed=True,executed=True,KKT=None,accounting=ledger)
    p=make_problem(ref);x=np.asarray(row['x']);a=ConstrainedProblem(p);q=x/a.scale
    r,J=a.evaluate(q);z,D=a.depth(q);G=direct_gradient(p,x)
    groups,cameras,_,_=synthetic('direction_changes',0.,-.1,100,groups=12)
    jointx=np.r_[ref['offset'],x] if 'offset' in ref else x
    cost,depth=objective_depth(groups,cameras,row,jointx,ref['lag'])
    np.testing.assert_allclose(cost,row['objective'],atol=1e-10,rtol=1e-9)
    np.testing.assert_allclose(depth,row['normalized_depths'],atol=1e-12,rtol=1e-12)
    np.testing.assert_allclose(G,row['G'],atol=1e-10,rtol=1e-8)
    np.testing.assert_allclose(G,2*J.T@r,atol=1e-10,rtol=1e-8)
    opt=None
    if row.get('multipliers_depth') is not None:
        Cd=np.asarray(D.T@row['multipliers_depth']).ravel();Cb=np.asarray(row['bound_multipliers']);KKT=G+Cd+Cb
        np.testing.assert_allclose(Cd,row['C_depth'],atol=1e-10,rtol=1e-8)
        np.testing.assert_allclose(Cb,row['C_bounds'],atol=1e-10,rtol=1e-8)
        np.testing.assert_allclose(KKT,row['KKT'],atol=1e-10,rtol=1e-8);opt=float(np.linalg.norm(KKT,np.inf))
        np.testing.assert_allclose(opt,row['optimality'],atol=1e-10,rtol=1e-8)
    if row['valid']:assert row['converged'] and opt is not None and opt<=1e-6 and min(depth)>1e-7 and not row['boundary_cameras']
    states={s['identity']:s for s in row['accounting']['states']};s=states[row['returned_state']]
    assert np.asarray(x,dtype='<f8').tobytes().hex()==s['physical_hex']
    if 'offset' in ref:
        joint=make_problem({k:v for k,v in ref.items() if k!='offset'});ja=ConstrainedProblem(joint);jq=jointx/ja.scale;jr,jJ=ja.evaluate(jq);jz,jD=ja.depth(jq)
        omitted=float((2*jJ.T@jr)[0]/25)
        np.testing.assert_allclose(omitted,row['omitted_camera_offset_objective_derivative_per_frame'],atol=1e-10,rtol=1e-8)
        if row.get('multipliers_depth') is not None:
            omitted_kkt=float((2*jJ.T@jr+jD.T@row['multipliers_depth'])[0]/25)
            np.testing.assert_allclose(omitted_kkt,row['omitted_camera_offset_lagrangian_derivative_per_frame'],atol=1e-10,rtol=1e-8)
        assert not row['joint_qualified']
    return dict(passed=True,executed=True,KKT=opt,objective=cost,minimum_depth=float(min(depth)),accounting=ledger,
                maximum_gradient_error=float(np.max(np.abs(G-row['G']))))


def verify_package(root,output):
    import re,time
    from basketball_shared_diagnose_v5 import compressed_read
    p=read('configs/basketball-rev2/timing-shared-v9.json');elapsed=time.time()-p['investigation_started_unix'];assert elapsed<5400
    # Original pre-outage stage is preserved with its exact source snapshots, not rebound to the restarted config.
    prior=read(root/'prepare/result.json');restart=root/'restart'
    for f,h in prior['source_sha256'].items():
        replacement=restart/Path(f).name
        assert sha256(replacement if replacement.exists() else f)==h
    verify_hashes(prior['artifacts_sha256'])
    stages={}
    for name in ['prepare-resumed','account','diagnose','adapt','benchmark','package']:
        f=root/name/'result.json'
        if not f.exists():continue
        r=read(f);verify_hashes(r['source_sha256']);verify_hashes(r['artifacts_sha256']);stages[name]=r['status']
    admission=read(root/'prepare-resumed/admission.json');verify_hashes(admission['source_sha256']);verify_hashes(admission['installed_solver_sha256']);verify_hashes(admission['markers'])
    partition=verify_partition(p)
    all_rows=[];details=[]
    for folder in [root/'adapt',root/'benchmark']:
        for f in sorted(folder.glob('*/*-attempts.json.gz')):
            data=compressed_read(f)
            for item in data['records']:
                proof=verify_row(item['reference'],item['row']);all_rows.append(item['row']);details.append(dict(source=str(f),id=item['id'],verification=proof))
    logs={}
    for name in ['basketball','budget','selfcap','v9']:
        f=root/f'{name}-tests.log';s=f.read_text();assert re.search(r'\nOK\s*$',s),name
        logs[name]=dict(tests=int(re.search(r'Ran (\d+) tests?',s).group(1)),path=str(f),sha256=sha256(f))
    assert len(all_rows)<=520
    write(output,dict(status='passed',stage_statuses=stages,attempt_records=len(all_rows),executed=sum(r.get('executed',True) for r in all_rows),qualified=sum(r['valid'] for r in all_rows),
        entry_verification=details,tests=logs,partition=partition,markers=admission['markers'],inherited_hashes_verified=True,elapsed_seconds=time.time()-p['investigation_started_unix'],
        accepted_timing=None,production_candidate=None,final_validation_protocol=None,verifier_sha256=sha256(__file__)))
