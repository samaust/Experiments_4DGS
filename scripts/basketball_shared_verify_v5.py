"""Independent original-unit, seed, ray, partition and artifact verification for v5."""
import argparse
from collections import Counter
import gzip
import json
from pathlib import Path
import re
import subprocess
import time
import numpy as np
from scipy.interpolate import BSpline
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes


def unpack(path):
    with gzip.open(path,'rt') as stream:return json.load(stream)


def objective_depth(groups,cameras,row,x,lag):
    """Reconstruct from physical geometry, not either constraint adapter."""
    x=np.asarray(x);offsets={1:0.,2:lag,3:float(x[0])};coeff=x[1:].reshape(18,3)
    spline=BSpline(row['knots'],coeff,3,extrapolate=False);depth=[];squared=[]
    for obs in groups[row['group_ids'][0]]['observations']:
        cam=cameras[obs['camera_id']];xyz=spline((obs['frames']-offsets[obs['camera_id']])/25)
        camera=(xyz*row['diameter']+row['center'])@np.asarray(cam['R']).T+cam['t']
        depth.extend(camera[:,2]/row['diameter']);uv=camera[:,:2]/camera[:,2,None]
        radial=1+cam['parameters_colmap'][3]*np.sum(uv**2,axis=1)
        xy=(uv*radial[:,None])@np.asarray(cam['K'])[:2,:2].T+np.asarray(cam['K'])[:2,2]
        squared.extend(np.sum((xy-obs['xy'])**2,axis=1))
    data=float(np.mean(2*(np.sqrt(1+np.asarray(squared))-1)))
    quad=np.arange(25,175,dtype=float)/25
    cost=data+row['weight']*float(np.sum(spline.derivative(2)(quad)**2))/len(quad)
    return cost,np.asarray(depth)


def verify_partition(p):
    root=Path(p['admission']);groups=read(root/'groups.json')['groups'];part=read(root/'partition.json')
    matrix=read(root/'membership.json');support=read(root/'support.json')
    assert Counter(g['split'] for g in groups)==dict(optimization=667,assessment=667)
    assert [g['group_id'] for g in groups]==matrix['group_order']==list(range(1334))
    tracks={c:read(root/f'merged-camera{c}.json')['tracks'] for c in range(34)}
    families=set();sources=set()
    for group in groups:
        assert group['split']==('assessment' if part['assignment'][group['group_id']] else 'optimization')
        for member in group['members']:
            c=member['camera_id'];track=tracks[c][member['track_id']]
            assert min(track['frames'])>=50 and max(track['frames'])<=149
            family=(c,track['duplicate_family_id']);assert family not in families;families.add(family)
            for source in track['source_track_ids']:
                key=(c,source);assert key not in sources;sources.add(key)
    assert len(support['edges'])==len(matrix['edge_order'])==72
    for edge,row,observed in zip(matrix['edge_order'],support['edges'],matrix['matrix']):
        ids=[g['group_id'] for g in groups if {edge['a'],edge['b']}<={m['camera_id'] for m in g['members']}]
        assert ids==row['group_ids'] and [int(i in ids) for i in range(1334)]==observed
        for split,value in [('optimization',0),('assessment',1)]:
            chosen=[i for i in ids if part['assignment'][i]==value]
            assert chosen==row['half_group_ids'][split] and len(chosen)==row[split] and len(chosen)>=19
    return dict(groups=1334,groups_per_half=667,edges=72,minimum_support=19,duplicate_family_and_source_isolation=True)


def verify(root,output):
    if output.exists():raise FileExistsError('fresh verification output required')
    p=read('configs/basketball-rev2/timing-shared-v5.json');evidence=read(root/'evidence.json')
    verify_hashes(evidence['source_sha256']);verify_hashes(evidence['artifacts_sha256'])
    assert evidence['report_script_sha256']==sha256('scripts/basketball_shared_report_v5.py')
    for original,entry in evidence['portable_sources'].items():
        assert sha256(root/entry['path'])==entry['sha256']==sha256(original)
    for name in ['prior_evidence','v4_evidence']:
        historical=read(p[name])
        for key in ['source_sha256','immutable_sha256','artifact_sha256','artifacts_sha256','test_logs_sha256']:
            if key in historical:verify_hashes(historical[key])
    verify_hashes(read(root/'prepare-final/v4-import.json')['source_sha256'])
    manifest=read(root/'prepare-final/cross-version-manifest.json')
    assert manifest['new_config_sha256']==sha256('configs/basketball-rev2/timing-shared-v5.json')
    assert manifest['predecessor_config_sha256']==sha256(p['prior_config']) and not manifest['old_config_hashes_rewritten']
    partition=verify_partition(p)
    controls=read(root/'prepare-final/controls-reuse.json')['controls'];assert len(controls)==1890
    verify_hashes({r['path']:r['sha256'] for r in controls})
    for row in controls:
        saved=read(row['path'])
        assert all(saved[k]==row[k] for k in ['configuration','motion','length','noise_pixels','known_offset_frames'])
        assert len(saved['result']['starts'])==3
    from basketball_shared_synthetic_v2 import synthetic
    from basketball_shared_solver_v3 import objective_agreement
    groups,cameras,truth,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    assert truth=={1:0.,2:-.1,3:-.2}
    assert all(np.array_equal(c['R'],np.eye(3)) and c['t'][1:]==[0.,0.] for c in cameras.values())
    pm=read(root/'diagnose-final/pilot-manifest.json');verify_hashes(pm['source_sha256'])
    assert pm['groups']==[2,9,11] and pm['lags']==[-25.,-20.,-19.,-7.,-6.,-.1,0.,25.]
    assert pm['scheduled_attempts']==144 and len(pm['historical'])==12
    verify_hashes({r['path']:r['sha256'] for r in pm['historical']})
    rays=unpack(root/'diagnose-final/escape-audit.json.gz')['records'];assert len(rays)==len(pm['rays'])==172
    assert sum(len(r['probes']) for r in rays)==3956
    # Independently evaluate homogeneous projective limits with scalar BSpline trajectories.
    max_limit_error=0.;finite_precision_rows=0;endpoint_checks=[]
    for ray,row in zip(pm['rays'],rays):
        gid=ray['group_id'];base=np.asarray(ray['base']);delta=np.asarray(ray['direction'])
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
    attempts=0;qualified=0;optimality_error=0.;seed_checks=0
    pilot=read(root/'pilot/pilot-decision.json')
    for artifact in pilot['artifacts']:
        path=root/'pilot'/artifact['path'];assert sha256(path)==artifact['sha256']
        state=unpack(path);assert state['group_id'] in pm['groups'];assert set(map(float,state['attempts']))==set(pm['lags'])
        from basketball_shared_profiles_v5 import problem_key
        assert state['problem_key']==problem_key(groups[state['group_id']],cameras,dict(a=1,b=2),window,10,state['weight'],'pilot')
        for lag,rows in state['attempts'].items():
            lag=float(lag);assert [r['start'] for r in rows]==pm['starts']
            for row in rows:
                attempts+=1;qualified+=int(row['valid'])
                if 'x' not in row:assert not row['valid'];continue
                assert len(row['x'])==55 and row['nfev']<=200
                objective,depth=objective_depth(groups,cameras,row,row['x'],lag)
                np.testing.assert_allclose(objective,row['objective'],rtol=1e-8,atol=1e-10)
                np.testing.assert_allclose(depth,row['normalized_depths'],rtol=1e-10,atol=1e-10)
                assert np.min(depth)>1e-8 and abs(row['x'][0])<=25
                s=depth-1e-8;gp=1/np.hypot(1,s)**3
                np.testing.assert_allclose(s/np.hypot(1,s),row['transformed_slacks'],atol=1e-12)
                if row['multipliers_depth'] is not None:
                    vd=np.asarray(row['multipliers_depth']);vg=np.asarray(row['multipliers_transformed'])
                    np.testing.assert_allclose(vd,vg*gp,rtol=1e-12,atol=1e-12)
                    np.testing.assert_allclose(vd*s,row['complementarity_original'],atol=1e-12)
                    np.testing.assert_allclose(vg*s/np.hypot(1,s),row['complementarity_transformed'],atol=1e-12)
                    assert np.isfinite(vd).all() and np.isfinite(gp).all() and np.all(gp>0)
                    from basketball_shared_spline_v2 import SplineProblem
                    from basketball_shared_solver_v4 import ConstrainedProblem as Original
                    problem=SplineProblem([groups[state['group_id']]],cameras,{1:0.,2:lag,3:0.},window,10,state['weight'],(1,2))
                    original=Original(problem);q=np.asarray(row['x'])/original.scale
                    residual,J=original.evaluate(q);z,D=original.depth(q)
                    gradient=2*J.T@residual+D.T@vd+row['bound_multipliers'];optimality=float(np.max(np.abs(gradient)))
                    optimality_error=max(optimality_error,abs(optimality-row['optimality']))
                    np.testing.assert_allclose(optimality,row['optimality'],rtol=1e-8,atol=1e-10)
                if row['valid']:
                    assert row['converged'] and row['optimality']<=1e-6 and min(depth)>1e-7 and not row['boundary_cameras']
                init=row['initialization_transfer'];cold=np.asarray(init['cold_x']);sanitized=np.asarray(init['original_x'])
                from basketball_shared_spline_v2 import SplineProblem
                cold_problem=SplineProblem([groups[state['group_id']]],cameras,{1:0.,2:lag,3:0.},window,10,state['weight'],(1,2))
                np.testing.assert_array_equal(cold,cold_problem.x0)
                if row['start']!='cold':
                    source=next(r for r in state['attempts'][str(row['seed_lag'])] if r['start']==row['seed_start'])
                    assert source['valid'] and init['original_x']==source['x']
                    assert row['seed_problem_key']==row['problem_key']==state['problem_key'];seed_checks+=1
                    basis=BSpline(row['knots'],np.eye(18),3,extrapolate=False)
                    offsets={1:0.,2:row['seed_lag'],3:source['x'][0]}
                    B=np.vstack([basis((obs['frames']-offsets[obs['camera_id']])/25) for obs in groups[state['group_id']]['observations']])
                    norms=np.linalg.norm(B,axis=0);threshold=max(B.shape)*np.finfo(float).eps*max(norms)
                    A=basis.derivative(2)(np.arange(25,175)/25);an=np.linalg.norm(A,axis=0);at=max(A.shape)*np.finfo(float).eps*max(an)
                    unsupported=np.flatnonzero((norms<threshold)&((an<at)|(state['weight']==0))).tolist()
                    assert [b['block'] for b in init['replaced_blocks']]==unsupported
                for block in init['replaced_blocks']:
                    i=1+3*block['block'];sanitized[i:i+3]=cold[i:i+3]
                np.testing.assert_array_equal(sanitized,init['sanitized_x'])
                fraction=init['blend_fraction'];expected=cold if fraction==0 else sanitized if fraction==1 else cold+fraction*(sanitized-cold)
                np.testing.assert_array_equal(expected,row['initial_x'])
                _,initial_depth=objective_depth(groups,cameras,row,expected,lag);assert min(initial_depth)>2e-8
                assert all(t['min_depth']>=1e-8 for t in row['solver_trace'])
    assert attempts==pilot['attempts']==144
    assert qualified==144-len(pilot['failures'])
    terminal=read(root/'result.json');assert terminal['accepted_timing'] is None and terminal['candidate_offsets'] is None
    assert not terminal['selection_consumed_this_attempt'] and not terminal['final_validation_consumed']
    markers=sorted(str(f) for f in Path('.local/calibration/basketball-rev2').rglob('*consumed*.json'))
    assert markers==['.local/calibration/basketball-rev2/timing-selection/run/selection-consumed.json']
    tests={};logs={}
    for name in ['basketball','budget','selfcap']:
        f=root/f'{name}-tests.log';text=f.read_text();assert re.search(r'\nOK\s*$',text)
        tests[name]=int(re.search(r'Ran (\d+) tests?',text).group(1));logs[str(f)]=sha256(f)
    docs=['docs/contender-experiments.md','docs/experiments/contender-summary.md','docs/experiments/basketball-rev2.md',
          'docs/experiments/basketball-shared-timing-v5.md'];links=0
    for name in docs:
        file=Path(name)
        for link in re.findall(r'\]\(([^)]+)\)',file.read_text()):
            link=link.split('#')[0]
            if not link or '://' in link:continue
            links+=1;assert (file.parent/link).resolve()==output.resolve() or (file.parent/link).exists(),(name,link)
    subprocess.run(['git','diff','--check'],check=True);subprocess.run(['git','diff','--cached','--check'],check=True)
    elapsed=time.time()-p['investigation_started_unix'];assert elapsed<14400
    write(output,dict(status='passed',evidence_sha256=sha256(root/'evidence.json'),verifier_sha256=sha256(__file__),
        partition=partition,controls_hashes_and_recipes=1890,analytical_ray_limits=172,diagnostic_probes=3956,
        maximum_analytical_limit_disagreement=max_limit_error,finite_endpoint_limit_checks=endpoint_checks,finite_precision_constant_acceleration_growth_rays=finite_precision_rows,
        pilot_attempts=attempts,pilot_qualified=qualified,seed_checks=seed_checks,maximum_original_optimality_disagreement=optimality_error,
        tests=tests,test_logs_sha256=logs,historical_hashes_verified=True,markers=markers,documentation_links=links,
        docs_sha256={f:sha256(f) for f in docs},working_tree_diff_check='passed',staged_diff_check='passed',
        elapsed_seconds=elapsed,within_four_hours=True,accepted_timing=None))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--evidence',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args();verify(args.evidence,args.output)
