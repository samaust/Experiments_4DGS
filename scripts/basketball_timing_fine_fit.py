"""Fine-grid epipolar timing with frozen disjoint-track consistency checks."""
import time
import numpy as np
from basketball_audit import sha256
from basketball_continuation_audit import CALIBRATION, CALIBRATION_SHA, verify_hashes
from basketball_scale import read,write
from basketball_timing import essential,solve_curve,match_tracks
from basketball_timing_recovery import load_tracks,temporal_cost,signed_errors


def refinement_grid(lag,step):
    if not 0<step<=.05:raise ValueError('invalid fractional resolution')
    return np.unique(np.round(np.r_[np.arange(-25,26),np.arange(max(-25,lag-1),min(25,lag+1)+step/2,step)],8))


def replace_edges(prior,new,target):
    keys=[(e['a'],e['b']) for e in new]
    if len(keys)!=len(set(keys)) or set(keys)!=target:raise ValueError('target edge membership changed')
    old={(e['a'],e['b']) for e in prior}
    if not target<=old:raise ValueError('replacement target absent from old graph')
    return sorted([e for e in prior if (e['a'],e['b']) not in target]+new,key=lambda e:(e['a'],e['b']))


def subset_check(costs,grid,p):
    order=np.random.default_rng(p['subset_seed']).permutation(len(costs))
    groups=[order[::2],order[1::2]];results=[]
    q=dict(p,minimum_pair_tracks=p['subset_minimum_tracks'])
    for group in groups:
        result=solve_curve(costs[group],grid,q)
        # Subsets measure independent point-estimate consistency. Full-pair
        # bootstrap uncertainty remains the unchanged acceptance requirement.
        result['consistency_eligible']=result['lag'] is not None and not any(
            b!='timing uncertainty' for b in result['blockers'])
        result['indices']=group.tolist();results.append(result)
    difference=abs(results[0]['lag']-results[1]['lag']) if all(r['lag'] is not None for r in results) else None
    passed=all(r['consistency_eligible'] for r in results) and difference<=p['timing_gate_frames']
    return dict(passed=passed,lag_difference_frames=difference,groups=results)


def fit(a):
    p=read(a.protocol);verify_hashes(p['source_sha256']);verify_hashes({str(CALIBRATION):CALIBRATION_SHA})
    if p['timing_gate_frames']!=.25 or p['integer_search_radius']!=25:raise ValueError('timing gate changed')
    tracks=load_tracks(a.tracks);cams={e['camera_id']:e for e in read(CALIBRATION)['cameras']}
    started=time.monotonic();edges=[];integer=np.arange(-25,26,dtype=float)
    for e in p['graph']:
        if time.monotonic()-started>p['maximum_cpu_seconds_per_stage']:raise TimeoutError('fine-fit CPU bound')
        ca,cb=e['a'],e['b'];E=essential(cams[ca],cams[cb]);focal=np.mean([cams[c]['K'][0][0] for c in (ca,cb)])
        pairs=match_tracks(tracks[ca],tracks[cb],p)
        def compute(grid):
            return np.array([[temporal_cost(tracks[ca][i],tracks[cb][j],lag,E,focal,p) for lag in grid] for i,j in pairs]).reshape(len(pairs),len(grid))
        costs=compute(integer);valid=np.isfinite(costs).all(axis=1);coarse=solve_curve(costs[valid],integer,p)
        row=dict(e,pair_tracks=len(pairs),integer=coarse,passed=False,lag=None)
        if coarse['lag'] is not None and abs(coarse['lag'])<25:
            grid=refinement_grid(coarse['lag'],p['fractional_step_frames']);fine=compute(grid)[valid]
            refined=solve_curve(fine,grid,p);biases=[]
            for i,j in np.array(pairs,dtype=int)[valid]:
                ta,tb=tracks[ca][i],tracks[cb][j];t=ta['frames'];use=(t>=tb['frames'][0]+25)&(t<=tb['frames'][-1]-25)
                yy=np.column_stack([np.interp(t[use]+refined['lag'],tb['frames'],tb['normalized'][:,k]) for k in range(2)])
                biases.append(float(np.median(signed_errors(ta['normalized'][use],yy,E,focal))))
            median_bias=float(np.median(np.abs(biases))) if biases else None
            if median_bias is None or median_bias>p['bias_limit_pixels']:
                refined['passed']=False;refined['blockers'].append('original spatial epipolar support fails')
            subsets=subset_check(fine,grid,p)
            if not subsets['passed']:
                refined['passed']=False;refined['blockers'].append('disjoint track groups disagree or lack identifiable support')
            row.update(refined=refined,subsets=subsets,passed=refined['passed'],lag=refined['lag'],median_absolute_bias_pixels=median_bias)
        edges.append(row)
        print('fine edge',ca,cb,'support',coarse['support'],'lag',row['lag'],'passed',row['passed'],flush=True)
    write(a.output,dict(schema='basketball-fine-timing-fit/v1',edges=edges,status='passed' if all(e['passed'] for e in edges) else 'blocked',
        wall_seconds=time.monotonic()-started,source_sha256=p['source_sha256'],protocol_sha256=sha256(a.protocol),
        tracks_sha256=sha256(a.tracks/'result.json'),calibration_sha256=CALIBRATION_SHA,
        selection_consumed=False,final_validation_consumed=False))
