"""Independent Plan 014 development arithmetic and accounting, after computation."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='1'
import argparse
from pathlib import Path
import time
import numpy as np
from basketball_scale import read,write
from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes
from basketball_shared_diagnose_v5 import compressed_read
from basketball_shared_verify_v5 import objective_depth
from basketball_shared_solver_v3 import objective_agreement
from basketball_shared_solver_v4 import ConstrainedProblem
from basketball_shared_recovery_v8 import fixture
from basketball_shared_synthetic_v2 import synthetic


def verify(root,output):
    if output.exists():raise FileExistsError('fresh independent verification required')
    policy=read('configs/basketball-rev2/timing-shared-v8.json')
    def check():
        if time.time()>=policy['investigation_started_unix']+14400:raise TimeoutError('packaging verification deadline')
    groups,cameras,_,_=synthetic('direction_changes',0.,-.1,100,groups=12)
    runtimes=[];all_rows=[];max_cost=max_kkt=max_depth=0.;preserved=recovered=0;ratios=[];recoveries=set();agreements=[];transfers=[];reference_comparisons=[]
    for path in sorted((root/'condition').glob('weight*-group*.json.gz')):
        state=compressed_read(path);gid=state['group_id'];weight=state['weight']
        old=compressed_read(f'docs/experiments/basketball-shared-timing-v6/pilot/weight{weight}-group{gid:02d}.json.gz')
        for lag,rows in state['attempts'].items():
            check();all_rows.extend(rows);problem=fixture(gid,lag,weight,check)
            for row,before in zip(rows,old['attempts'][lag]):
                assert row['start']==before['start']
                runtimes.append(dict(group_id=gid,weight=weight,lag=float(lag),start=row['start'],v6_wall_seconds=before['wall_seconds'],v8_wall_seconds=row['wall_seconds']))
                cost,depth=objective_depth(groups,cameras,row,row['x'],float(lag))
                np.testing.assert_allclose(cost,row['objective'],atol=1e-10,rtol=1e-9)
                np.testing.assert_allclose(depth,row['normalized_depths'],atol=1e-12,rtol=1e-12)
                a=ConstrainedProblem(problem);q=np.asarray(row['x'])/a.scale;r,J=a.evaluate(q);z,D=a.depth(q)
                opt=None
                if row['multipliers_depth'] is not None:
                    kkt=np.asarray(2*J.T@r+D.T@row['multipliers_depth']+row['bound_multipliers'])
                    opt=float(np.max(np.abs(kkt)))
                    np.testing.assert_allclose(kkt,row['KKT'],atol=1e-10,rtol=1e-8)
                    np.testing.assert_allclose(opt,row['optimality'],atol=1e-10,rtol=1e-8)
                    max_kkt=max(max_kkt,abs(opt-row['optimality']))
                if row['valid']:assert row['converged'] and opt<=1e-6 and min(depth)>1e-7 and not row['boundary_cameras']
                assert row['nfev']==len(row['state_ledger'])<=200 and len(row['solver_trace'])<=200
                assert row['state_ledger'][0]['first']=='cold_transform'
                raw=bytes.fromhex(row['transform_bytes_le_hex']);import hashlib
                assert hashlib.sha256(raw).hexdigest()==row['transform_sha256']
                P=np.frombuffer(raw,dtype='<f8').reshape(len(q),len(q))
                np.testing.assert_allclose(P@row['conditioned_y'],q,atol=1e-10,rtol=1e-10)
                assert row['gtol']==1e-6/max(1.,float(np.linalg.norm(np.linalg.inv(P).T,np.inf)))
                max_cost=max(max_cost,abs(cost-row['objective']));max_depth=max(max_depth,float(np.max(np.abs(depth-row['normalized_depths']))))
                if before['valid']:preserved+=int(row['valid'] and (cost<=before['objective'] or objective_agreement(cost,before['objective'])))
                else:
                    ratios.append(float('inf') if opt is None else opt/before['optimality'])
                    if row['valid']:recovered+=1;recoveries.add(gid)
            values=[r['objective'] for r in rows]
            agreements.append(dict(group_id=gid,weight=weight,lag=float(lag),agree=all(objective_agreement(values[0],v) for v in values)))
        source,dest,direction=(-20.,-19.,'ascending') if gid==2 else (-6.,-7.,'descending')
        row=next(r for r in state['attempts'][str(dest)] if r['start']==direction)
        transfers.append(dict(group_id=gid,weight=weight,source=source,destination=dest,direction=direction,qualified=row['valid'] and row['seed_lag']==source))
    historical=compressed_read(root/'prepare/diagnostic-manifest.json.gz')['historical']
    for ref in historical:
        state=compressed_read(root/f'condition/weight1.0-group{ref["group_id"]:02d}.json.gz')
        values=[r['objective'] for r in state['attempts'][str(ref['lag'])] if r['valid']]
        best=min(values) if values else None
        reference_comparisons.append(dict(**ref,new_best=best,no_worse=best is not None and (best<=ref['objective'] or objective_agreement(best,ref['objective']))))
    decision=read(root/'condition/conditioning-decision.json')
    assert len(all_rows)==144 and decision['qualified']==sum(r['valid'] for r in all_rows)
    assert decision['preserved']==preserved and decision['recovered']==recovered
    np.testing.assert_allclose(decision['median_failed_KKT_ratio'],np.median(ratios),atol=1e-12,rtol=1e-12)
    assert decision['passed']==(preserved==94 and recovered>=25 and recoveries=={2,9,11} and np.median(ratios)<=.1 and not decision['issues'])
    scalar_count=qualified=conditional=0;scalar_max_cost=scalar_max_kkt=scalar_max_depth=0.;complete=0
    for f in sorted((root/'basins').glob('weight*-group*-lag*.json.gz')):
        s=compressed_read(f);complete+=int(s['complete']);gid=s['group_id'];lag=s['lag'];weight=s['weight']
        curves={d:{float(x):r for x,r in c.items()} for d,c in s['curves'].items()}
        assert len({tuple(sorted(c)) for c in curves.values()})==1
        for direction,curve in curves.items():
            for offset,row in curve.items():
                check();scalar_count+=1;qualified+=int(row['valid'])
                if not row['executed']:continue
                conditional+=1
                if 'x' not in row:
                    assert not row['valid'] and row['nfev']==0
                    continue
                physical=np.r_[offset,row['x']]
                cost,depth=objective_depth(groups,cameras,row,physical,lag)
                np.testing.assert_allclose(cost,row['objective'],atol=1e-10,rtol=1e-9)
                np.testing.assert_allclose(depth,row['normalized_depths'],atol=1e-12,rtol=1e-12)
                problem=fixture(gid,lag,weight,check);a=ConstrainedProblem(problem);q=physical/a.scale;r,J=a.evaluate(q);z,D=a.depth(q)
                G=np.asarray(2*J.T@r).ravel();np.testing.assert_allclose(G[0]/25,row['omitted_camera_offset_objective_derivative_per_frame'],atol=1e-10,rtol=1e-8)
                if row['multipliers_depth'] is not None:
                    kkt=G+D.T@row['multipliers_depth'];opt=float(np.max(np.abs(kkt[1:])))
                    np.testing.assert_allclose(opt,row['optimality'],atol=1e-10,rtol=1e-8)
                    np.testing.assert_allclose(kkt[0]/25,row['omitted_camera_offset_lagrangian_derivative_per_frame'],atol=1e-10,rtol=1e-8)
                    scalar_max_kkt=max(scalar_max_kkt,abs(opt-row['optimality']))
                if row['valid']:assert row['converged'] and row['optimality']<=1e-6 and min(depth)>1e-7
                assert not row['joint_qualified'] and row['nfev']<=200 and len(row['solver_trace'])<=200
                scalar_max_cost=max(scalar_max_cost,abs(cost-row['objective']));scalar_max_depth=max(scalar_max_depth,float(np.max(np.abs(depth-row['normalized_depths']))))
        if s['complete']:
            grid=sorted(curves['cold']);initial=[float(x) for x in range(-25,26)]
            from basketball_shared_scalar_search_v8 import refinement
            coarse={d:{x:curve[x] for x in initial} for d,curve in curves.items()}
            fine=refinement(coarse,.05);assert fine==s['fine_added']
            second={d:{x:curve[x] for x in [*initial,*fine]} for d,curve in curves.items()}
            final=refinement(second,.01,True);assert final==s['final_added']
            assert set(grid)==set(initial+fine+final)
            assert s['scheduled']==3*len(grid)
    check()
    write(output,dict(status='passed',verifier_sha256=sha256(__file__),conditioning=dict(attempts=len(all_rows),preserved=preserved,recovered=recovered,median_failed_KKT_ratio=float(np.median(ratios)),maximum_cost_error=max_cost,maximum_depth_error=max_depth,maximum_KKT_error=max_kkt,runtime_comparisons=runtimes,three_start_comparisons=agreements,required_transfers=transfers,historical_reference_comparisons=reference_comparisons),scalar=dict(completed_profiles=complete,retained_path_records=scalar_count,retained_executed_fits=conditional,retained_qualified=qualified,maximum_cost_error=scalar_max_cost,maximum_depth_error=scalar_max_depth,maximum_KKT_error=scalar_max_kkt),elapsed_seconds=time.time()-policy['investigation_started_unix']))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();verify(a.root,a.output)
