"""Independent artifact/partition reconstruction for the Plan010 terminal blocker."""
import argparse
from collections import Counter
from pathlib import Path
import re
import subprocess
import time
from urllib.parse import unquote
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes

DOCS=['docs/contender-experiments.md','docs/experiments/basketball-shared-timing-v4.md','docs/experiments/basketball-rev2.md',
      'docs/experiments/contender-summary.md',*[f'docs/experiments/{n}.md' for n in
      ['006-stg-full','007-freetimegs','008-moe-gs','009-atgs','010-freetimegs-plus-plus']]]


def verify(a):
    if a.output.exists():raise FileExistsError('fresh verification output required')
    p=read(a.config);evidence=read(a.evidence/'evidence.json')
    assert time.time()<p['investigation_started_unix']+14400
    verify_hashes(evidence['source_sha256']);verify_hashes(evidence['artifacts_sha256'])
    assert sha256('scripts/basketball_shared_report_v4.py')==evidence['report_script_sha256']
    prior=read(p['prior_evidence'])
    assert sha256(p['prior_evidence'])==evidence['historical_evidence_sha256']
    for k in ['source_sha256','immutable_sha256','artifact_sha256','test_logs_sha256']:verify_hashes(prior[k])
    manifest=read(a.evidence/'cross-version-manifest.json');verify_hashes(manifest['source_sha256'])
    assert manifest['old_config_hashes_rewritten'] is False
    assert manifest['predecessor_config_sha256']==sha256(p['prior_config'])
    assert manifest['new_config_sha256']==sha256(a.config)
    admission=Path(p['admission']);groups=read(admission/'groups.json')['groups']
    matrix=read(admission/'membership.json');partition=read(admission/'partition.json');support=read(admission/'support.json')
    assignment=partition['assignment'];tracks={c:read(admission/f'merged-camera{c}.json')['tracks'] for c in range(34)}
    seen_sources=set();seen_families=set()
    assert len(groups)==1334 and Counter(g['split'] for g in groups)==dict(optimization=667,assessment=667)
    assert [g['group_id'] for g in groups]==matrix['group_order']==list(range(1334))
    for g in groups:
        cameras=[m['camera_id'] for m in g['members']]
        assert len(cameras)==len(set(cameras)) and len(set(cameras)-{0,10,20,30})>=3
        assert g['split']==('assessment' if assignment[g['group_id']] else 'optimization')
        for m in g['members']:
            c=m['camera_id'];t=tracks[c][m['track_id']]
            assert min(t['frames'])>=50 and max(t['frames'])<=149
            family=(c,t['duplicate_family_id']);assert family not in seen_families;seen_families.add(family)
            for source in t['source_track_ids']:
                key=(c,source);assert key not in seen_sources;seen_sources.add(key)
    assert len(matrix['edge_order'])==len(support['edges'])==72
    half_min=1334
    for i,(edge,row) in enumerate(zip(matrix['edge_order'],support['edges'])):
        assert (edge['a'],edge['b'])==(row['a'],row['b'])
        membership=[int({edge['a'],edge['b']}<={m['camera_id'] for m in g['members']}) for g in groups]
        assert membership==matrix['matrix'][i]
        ids=[j for j,v in enumerate(membership) if v];assert ids==row['group_ids']
        for value,role in [(0,'optimization'),(1,'assessment')]:
            chosen=[j for j in ids if assignment[j]==value]
            assert chosen==row['half_group_ids'][role] and len(chosen)==row[role]
            half_min=min(half_min,len(chosen))
    assert half_min==19
    reuse=read(a.evidence/'controls-reuse.json')['controls'];assert len(reuse)==1890
    verify_hashes({r['path']:r['sha256'] for r in reuse})
    for r in reuse:
        old=read(r['path'])
        assert all(old[k]==r[k] for k in ['configuration','motion','length','noise_pixels','known_offset_frames'])
        assert r['independent_qualification']=='requires v4 reassessment'
    import gzip
    import json
    import numpy as np
    from scipy.interpolate import BSpline
    from basketball_shared_synthetic_v2 import synthetic
    from basketball_shared_spline_v2 import SplineProblem
    from basketball_shared_solver_v3 import objective_agreement
    from basketball_shared_solver_v4 import MARGIN,QUALIFICATION_DEPTH
    old=read(p['diagnostic_evidence'])
    assert sha256(p['diagnostic_evidence'])==evidence['v3_evidence_sha256']
    for key in ['source_sha256','artifacts_sha256']:verify_hashes(old[key])
    diagnostic=read(a.evidence/'coefficient-diagnostics.json')
    assert len(diagnostic['attempts'])==12
    assert sum(r['probes'] for r in diagnostic['attempts'])==2852
    for entry in diagnostic['attempts']:
        with gzip.open(a.evidence/entry['portable_full_evidence'],'rt') as stream:raw_diagnostic=json.load(stream)
        assert len(raw_diagnostic['probes'])==len(entry['probe_details'])
        assert entry['states']['destination_final']['min_normalized_depth']<0
        for probe in entry['probe_details']:
            if 'objective' in probe:
                assert probe['agrees_with_baseline']==objective_agreement(probe['objective'],probe['baseline_objective'])
                assert probe['agrees_with_saved']==objective_agreement(probe['objective'],probe['saved_objective'])
    exact=read(a.evidence/'exact-retest.json');profiles=exact['profiles']
    portable=read(a.evidence/'profile-groups.json')['groups'];traces=[]
    for weight in [1.,0.]:
        states=[]
        for entry in portable:
            if entry['weight']!=weight:continue
            with gzip.open(a.evidence/entry['path'],'rt') as stream:state=json.load(stream)
            for direction in ['cold','ascending','descending']:
                state[direction]={lag:next(r for r in rows if r['start']==direction) for lag,rows in state['attempts'].items()}
            states.append(state)
        traces.append(dict(weight=weight,states=states))
    raw=dict(optimizer_traces=traces)
    assert not exact['safeguard_passed'] and exact['terminal_kind']=='numerical_failure'
    groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    failures=[];attempt_count=0;cold_states={}
    for trace in raw['optimizer_traces']:
        assert [s['group_id'] for s in trace['states']]==list(range(12))
        label='data_only' if trace['weight']==0 else 'regularized'
        profile=profiles[label]
        for state in trace['states']:
            gid=state['group_id'];all_lags=sorted(map(float,state['attempts']))
            assert set(range(-25,26))<=set(all_lags)
            assert min(all_lags)==-25 and max(all_lags)==25
            for lag,attempts in state['attempts'].items():
                assert len(attempts)==3 and [r['start'] for r in attempts]==['cold','ascending','descending']
                for r in attempts:
                    attempt_count+=1
                    assert r['problem_key']==state['problem_key']
                    assert r['seed_problem_key'] in [None,state['problem_key']]
                    assert r.get('nfev',0)<=200
                    if r.get('x') is not None:
                        assert r['offsets']['1']==0. and r['offsets']['2']==float(lag)
                        assert len(r['x'])==55 and len(r['coefficients'][0])==18
                        spline=BSpline(r['knots'],np.asarray(r['coefficients'][0]),3,extrapolate=False)
                        depths=[];squared_errors=[]
                        for o in groups[gid]['observations']:
                            camera=cameras[o['camera_id']]
                            xyz=spline((np.asarray(o['frames'])-r['offsets'][str(o['camera_id'])])/25)
                            world=xyz*r['diameter']+r['center']
                            camera_xyz=world@np.asarray(camera['R']).T+camera['t']
                            depths.extend(camera_xyz[:,2]/r['diameter'])
                            uv=camera_xyz[:,:2]/camera_xyz[:,2,None]
                            radial=1+camera['parameters_colmap'][3]*np.sum(uv**2,axis=1)
                            predicted=(uv*radial[:,None])@np.asarray(camera['K'])[:2,:2].T+np.asarray(camera['K'])[:2,2]
                            squared_errors.extend(np.sum((predicted-o['xy'])**2,axis=1))
                        np.testing.assert_allclose(depths,r['normalized_depths'],rtol=1e-10,atol=1e-10)
                        objective=float(np.mean(2*(np.sqrt(1+np.asarray(squared_errors))-1)))
                        if trace['weight']:
                            quadrature=np.arange(window[0]-25,window[1]+26,dtype=float)/25
                            objective+=trace['weight']*float(np.sum(spline.derivative(2)(quadrature)**2))/len(quadrature)
                        np.testing.assert_allclose(objective,r['objective'],rtol=1e-8,atol=1e-10)
                        assert min(depths)>=MARGIN
                        if r['valid']:
                            assert r['converged'] and r['optimality']<=1e-6 and r['constraint_violation']==0
                            assert min(depths)>QUALIFICATION_DEPTH and not r['boundary_cameras']
                        assert all(t['min_depth']>=MARGIN for t in r['solver_trace'])
                        init=r['initialization_transfer'];cold=np.asarray(init['cold_x']);sanitized=np.asarray(init['original_x'])
                        assert len(cold)==len(sanitized)==55
                        cold_key=(trace['weight'],gid,float(lag))
                        if cold_key not in cold_states:
                            cold_problem=SplineProblem([groups[gid]],cameras,{1:0.,2:float(lag),3:0.},window,10,trace['weight'],(1,2))
                            cold_states[cold_key]=cold_problem.x0.copy()
                        np.testing.assert_array_equal(cold,cold_states[cold_key])
                        if r['start']=='cold':assert r['seed_lag'] is None and r['seed_start'] is None
                        else:
                            seeds=state['attempts'][str(r['seed_lag'])]
                            seed=next(v for v in seeds if v['start']==r['seed_start'])
                            assert seed['valid'] and init['original_x']==seed['x']
                            assert init['source_lag']==r['seed_lag'] and init['destination_lag']==float(lag)
                            basis=BSpline(r['knots'],np.eye(18),3,extrapolate=False)
                            offsets={1:0.,2:r['seed_lag'],3:seed['x'][0]}
                            B=np.vstack([basis((np.asarray(o['frames'])-offsets[o['camera_id']])/25) for o in groups[gid]['observations']])
                            norms=np.linalg.norm(B,axis=0);threshold=max(B.shape)*np.finfo(float).eps*max(norms)
                            A=basis.derivative(2)(np.arange(window[0]-25,window[1]+26)/25)
                            an=np.linalg.norm(A,axis=0);at=max(A.shape)*np.finfo(float).eps*max(an)
                            unsupported=np.flatnonzero((norms<threshold)&((an<at)|(trace['weight']==0))).tolist()
                            assert [b['block'] for b in init['replaced_blocks']]==unsupported
                            np.testing.assert_array_equal(norms,init['source_support'][0]['data_norms'])
                            if float(lag) not in range(-25,26):
                                assert (r['seed_lag']<float(lag) if r['start']=='ascending' else r['seed_lag']>float(lag))
                        for block in init['replaced_blocks']:
                            start=1+3*block['block'];sanitized[start:start+3]=cold[start:start+3]
                        np.testing.assert_array_equal(sanitized,init['sanitized_x'])
                        fraction=init['blend_fraction'];assert fraction in [2.**-k for k in range(21)]+[0.]
                        expected=cold if fraction==0 else sanitized if fraction==1 else cold+fraction*(sanitized-cold)
                        np.testing.assert_array_equal(expected,r['initial_x'])
                        assert init['checks'][-1]['valid']
                    if not r['valid']:failures.append(dict(group_id=gid,weight=trace['weight'],lag=float(lag),start=r['start'],
                        nfev=r.get('nfev'),message=r.get('message') or r.get('error')))
            for direction in [None,'ascending','descending']:
                costs=profile['group_profile_costs'] if direction is None else profile['directional_group_costs'][direction]
                for lag,reported in zip(profile.get('grid',all_lags),costs[gid]):
                    candidates=state['attempts'][str(lag)] if direction is None else [state[direction][str(lag)]]
                    valid=[r['objective'] for r in candidates if r['valid']]
                    assert reported==(min(valid) if valid else None)
    assert failures
    terminal=read(a.evidence/'result.json')
    assert terminal['status']=='blocked' and terminal['terminal_kind']=='numerical_failure'
    assert terminal['candidate_offsets'] is None and terminal['accepted_timing'] is None
    markers=sorted(str(f) for f in Path('.local/calibration/basketball-rev2').rglob('*consumed*.json'))
    assert markers==['.local/calibration/basketball-rev2/timing-selection/run/selection-consumed.json']
    broken=[];links=0
    for name in DOCS:
        file=Path(name)
        for link in re.findall(r'\]\(([^)]+)\)',file.read_text()):
            link=link.split('#')[0]
            if not link or '://' in link or link.startswith('mailto:'):continue
            target=(file.parent/unquote(link.strip('<>'))).resolve();links+=1
            if target!=a.output.resolve() and not target.exists():broken.append(dict(source=name,target=str(target)))
    assert not broken,broken
    tests={};logs={}
    for name in ['basketball','budget','selfcap']:
        file=a.logs/f'{name}-tests.log';text=file.read_text()
        assert re.search(r'\nOK\s*$',text) and 'FAILED (' not in text
        tests[name]=int(re.search(r'Ran (\d+) tests?',text).group(1));logs[str(file)]=sha256(file)
    subprocess.run(['git','diff','--check'],check=True)
    subprocess.run(['git','diff','--cached','--check'],check=True)
    elapsed=time.time()-p['investigation_started_unix'];assert elapsed<14400
    write(a.output,dict(status='passed',evidence_sha256=sha256(a.evidence/'evidence.json'),
        verification_script_sha256=sha256(__file__),tests=tests,test_logs_sha256=logs,
        regression_source_sha256={str(f):sha256(f) for pattern in ['test_basketball*.py','test_*budget*.py','test_selfcap*.py'] for f in Path('tests').glob(pattern)},
        all_artifact_and_historical_hashes_verified=True,production_controls_verified=1890,
        groups=1334,groups_per_half=667,edges_reconstructed=72,minimum_groups_per_edge_per_half=half_min,
        no_source_track_or_duplicate_family_leakage=True,failed_attempts=failures,
        diagnosed_v3_rejections=12,independent_returned_depths_verified=True,
        initialization_and_cache_provenance_verified=True,deterministic_seed_sanitation_verified=True,
        timing_consumption_markers=markers,documentation_links=links,broken_links=broken,
        documentation_sha256={n:sha256(n) for n in DOCS},working_tree_diff_check='passed',staged_diff_check='passed',
        elapsed_including_verification_seconds=elapsed,within_four_hours=True,
        accepted_timing=None,selection_consumed_this_attempt=False,final_validation_consumed=False))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['config','evidence','logs','output']:parser.add_argument('--'+key,type=Path,required=True)
    verify(parser.parse_args())
