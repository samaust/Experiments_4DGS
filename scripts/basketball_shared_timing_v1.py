"""Bounded Plan007 audit and shared-track admission; no final-frame reader.

The production stages are gated by admission. A scientific blocker is a valid
terminal artifact, never an accepted timing result. Historical code is imported
for its estimator definitions and is never rewritten.
"""
import argparse
from collections import Counter
from pathlib import Path
import shutil
import time

import numpy as np
from scipy.spatial.distance import cdist

from basketball_audit import sha256
from basketball_continuation_audit import CALIBRATION, verify_hashes, verify_membership, PROFILE
from basketball_scale import read, write
from basketball_timing import essential, solve_curve, undistort_points
from basketball_timing_recovery import load_tracks, signed_errors
from basketball_shared_tracks_v1 import extract


def bounded(p):
    if time.time() - p['investigation_started_unix'] > p['maximum_cpu_seconds']:
        raise TimeoutError('four CPU wall-hour investigation budget exhausted')


def validate_config(p):
    expected = dict(schema='basketball-shared-trajectories/v1', target_cameras=list(range(34)),
                    maximum_cpu_seconds=14400, held_out_cameras=[0,10,20,30],
                    minimum_groups_per_half=12, minimum_training_cameras=3, split_seed=0)
    if any(p.get(k) != v for k,v in expected.items()):
        raise ValueError('changed Plan007 invariants')
    if p['roles'] != {'fit':[50,149], 'selection_previously_observed':[150,199], 'final_untouched':[200,249]}:
        raise ValueError('changed role boundaries')
    if p['configurations'] != [dict(knot_spacing_frames=k,acceleration_weight=w) for k in [5,10] for w in [.1,1,10]]:
        raise ValueError('changed six configurations')
    base = read(p['base_frozen_protocol'])
    for k,v in dict(timing_gate_frames=.25, integer_search_radius=25, descriptor_ratio=.8,
                    minimum_pair_tracks=12, bootstrap_resamples=256, bootstrap_seed=0).items():
        if base[k] != v:
            raise ValueError('changed estimator gates')
    return base


def baseline(p):
    validate_config(p)
    verify_hashes(p['source_sha256'])
    old = read(p['audit'])
    if old['status'] != 'passed':
        raise ValueError('provenance predecessor did not pass')
    verify_hashes(old['sha256'])
    verify_hashes({v['path']:v['sha256'] for v in old['videos']})
    verify_membership(read(PROFILE),read(CALIBRATION))
    frozen = read(p['previous_frozen'])
    verify_hashes(frozen['sha256'])
    edges = frozen['edges']
    if len(edges) != 72 or len({(e['a'],e['b']) for e in edges}) != 72:
        raise ValueError('fixed graph changed')
    if {e[k] for e in edges for k in ('a','b')} != set(range(34)):
        raise ValueError('fixed graph camera membership changed')
    return {**old['sha256'], **p['source_sha256'], **frozen['sha256'],
            **{v['path']:v['sha256'] for v in old['videos']}}


def mutual_pairs(a,b,ratio=.8):
    """Both directional ratio tests, plus mutual nearest neighbors."""
    if min(len(a),len(b)) < 2:
        return []
    d = cdist(np.array([t['descriptor'] for t in a]), np.array([t['descriptor'] for t in b]))
    ab = np.argsort(d,axis=1,kind='stable')[:,:2]
    ba = np.argsort(d,axis=0,kind='stable')[:2,:]
    return [(i,int(j)) for i,(j,k) in enumerate(ab)
            if ba[0,j] == i and d[i,j] < ratio*d[i,k] and d[i,j] < ratio*d[ba[1,j],j]]


def common_injections(a,b,deltas,start,end):
    """B_new(f)=B_original(f-delta), with identical saved support for all deltas.

    Trim before resampling so neither interpolation endpoint crosses the window.
    Also trim A; callers separately enforce identical support over lag hypotheses.
    """
    def clip(t):
        use=(t['frames']>=start)&(t['frames']<=end)
        return {k:(v[use] if k in ('frames','xy','normalized') else v) for k,v in t.items()}
    a,b=clip(a),clip(b)
    if not len(a['frames']) or not len(b['frames']):
        return a,[]
    f=b['frames']
    use=(f-max(deltas)>=f[0])&(f-min(deltas)<=f[-1])
    common=f[use]
    shifted=[]
    for delta in deltas:
        row=dict(b,frames=common.copy())
        for key in ('xy','normalized'):
            row[key]=np.column_stack([np.interp(common-delta,f,b[key][:,k]) for k in range(2)])
        shifted.append(row)
    return a,shifted


def pair_costs(a,b,grid,E,focal,minimum,absolute):
    """Vectorized historical scores on one common reference sample set."""
    if not len(a['frames']) or not len(b['frames']):
        return np.full(len(grid),np.nan),0
    t=a['frames']
    use=(t+min(grid)>=b['frames'][0])&(t+max(grid)<=b['frames'][-1])
    n=int(use.sum())
    if n<minimum:
        return np.full(len(grid),np.nan),n
    query=t[use][None,:]+np.asarray(grid)[:,None]
    y=np.stack([np.interp(query,b['frames'],b['normalized'][:,k]) for k in range(2)],axis=-1)
    x=np.broadcast_to(a['normalized'][use],y.shape)
    errors=signed_errors(x.reshape(-1,2),y.reshape(-1,2),E,focal).reshape(len(grid),n)
    if absolute:
        return np.median(np.abs(errors),axis=1),n
    errors-=np.median(errors,axis=1)[:,None]
    return np.sqrt(np.mean(np.where(np.abs(errors)<=1,errors**2,2*np.abs(errors)-1),axis=1)),n


def evaluate_injections(pairs,deltas,grid,E,focal,base,start,end,absolute):
    stacks=[[] for _ in deltas];support=[[] for _ in deltas]
    speeds=[];accelerations=[]
    for a,b in pairs:
        a,shifted=common_injections(a,b,deltas,start,end)
        if len(a['xy'])>2:
            speeds.extend(np.linalg.norm(np.diff(a['xy'],axis=0),axis=1))
            accelerations.extend(np.linalg.norm(np.diff(a['xy'],n=2,axis=0),axis=1))
        for i,bb in enumerate(shifted):
            curve,n=pair_costs(a,bb,grid,E,focal,base['minimum_pair_samples_per_track'],absolute)
            stacks[i].append(curve);support[i].append(n)
    rows=[]
    for delta,costs,counts in zip(deltas,stacks,support):
        r=solve_curve(np.asarray(costs).reshape(-1,len(grid)),grid,base)
        # Point estimates of flat curves are diagnostics, never accepted offsets.
        r.update(injected_delta_frames=delta,reference_samples=counts,
                 median_speed_pixels_per_frame=float(np.median(speeds)) if speeds else None,
                 median_acceleration_pixels_per_frame2=float(np.median(accelerations)) if accelerations else None)
        rows.append(r)
    zero=rows[deltas.index(0)]
    for r in rows:
        identifiable=not any(b in r['blockers'] for b in ['ambiguous optimum','boundary optimum','insufficient tracks spanning the full search'])
        baseline_identifiable=not any(b in zero['blockers'] for b in ['ambiguous optimum','boundary optimum','insufficient tracks spanning the full search'])
        r['relative_recovery_error_frames']=(r['lag']-zero['lag']-r['injected_delta_frames']) if identifiable and baseline_identifiable else None
        interval=r.get('bootstrap_95_frames')
        expected=zero['lag']+r['injected_delta_frames'] if baseline_identifiable else None
        r['conditional_interval_covers_shifted_baseline']=(interval[0]<=expected<=interval[1]) if interval and expected is not None and identifiable else None
    return rows


def synthetic_pairs(motion,noise,delta=0,n=24,length=100):
    """Calibrated rectified cameras, fixed depth; no calibration-cloud inputs.

    CV is analytically unidentifiable after constant residual removal. Varying
    vertical speed provides timing information in the other positive controls.
    Noise is in the declared 960x540 pixel convention.
    """
    K=[[800.,0,479.5],[0,800.,269.5],[0,0,1]]
    cams=[dict(K=K,parameters_colmap=[800,480,270,0.],R=np.eye(3).tolist(),t=[x,0.,0.]) for x in [0.,-1.]]
    rng=np.random.default_rng(0);frames=np.arange(50,50+length,dtype=float);pairs=[]
    for i in range(n):
        def observe(camera,offset):
            t=frames-50-offset
            y=.015*t if motion=='constant_velocity' else (.001*t*t if motion=='acceleration' else .8*np.sin(t/9+i*.03))
            xyz=np.column_stack((np.full(len(t),i*.02),y,np.full(len(t),8.)))
            xy=project(xyz,camera)+rng.normal(0,noise,(len(t),2))
            return dict(frames=frames,xy=xy,normalized=undistort_points(xy,camera),descriptor=np.eye(n)[i])
        pairs.append((observe(cams[0],0),observe(cams[1],delta)))
    return pairs,cams


def project(xyz,camera):
    cam=np.asarray(xyz)@np.asarray(camera['R']).T+camera['t']
    uv=cam[:,:2]/cam[:,2,None]
    uv*=1+camera['parameters_colmap'][3]*np.sum(uv**2,axis=1)[:,None]
    K=np.asarray(camera['K'])
    return uv@K[:2,:2].T+K[:2,2]


def audit(p,output,base):
    tracks=load_tracks(Path(p['prior_tracks']))
    track_hashes={}
    for f in sorted(Path(p['prior_tracks']).glob('*.json')):
        track_hashes[str(f)]=sha256(f)
    cams={c['camera_id']:c for c in read(CALIBRATION)['cameras']}
    edges=read(p['previous_frozen'])['edges'];rows=[]
    # Existing matching policy for the baseline, not revised mutual-ratio groups.
    from basketball_timing import match_tracks
    for edge in edges:
        bounded(p)
        ca,cb=edge['a'],edge['b'];E=essential(cams[ca],cams[cb]);focal=np.mean([cams[c]['K'][0][0] for c in [ca,cb]])
        pairs=[(tracks[ca][i],tracks[cb][j]) for i,j in match_tracks(tracks[ca],tracks[cb],base)]
        for start,end in p['audit_windows']:
            for absolute in [True,False]:
                # Full range cannot support either short-window score. This is
                # deliberately not replaced by a smaller qualifying search.
                grid=np.arange(-25,26,dtype=float)
                result=evaluate_injections(pairs,p['injections'],grid,E,focal,base,start,end,absolute)
                rows.append(dict(a=ca,b=cb,window=[start,end],estimator='absolute' if absolute else 'temporal_bias',
                                 search='full_unchanged',qualifies_timing=False,injections=result))
                # Predeclared local diagnostic only, retaining all score gates.
                grid=np.round(np.arange(max(-25,edge['lag']-p['diagnostic_search_radius']),min(25,edge['lag']+p['diagnostic_search_radius'])+.025,.05),8)
                result=evaluate_injections(pairs,p['injections'],grid,E,focal,base,start,end,absolute)
                rows.append(dict(a=ca,b=cb,window=[start,end],estimator='absolute' if absolute else 'temporal_bias',
                                 search='local_nonqualifying',qualifies_timing=False,injections=result))
        print('audit edge',ca,cb,flush=True)
    synthetic=[];safeguards=[]
    for motion in ['constant_velocity','acceleration','direction_changes']:
        for noise in [0,.25,.5]:
            bounded(p)
            # Known offsets are generated in 3D before observation, unlike the
            # real-data relative resampling tests.
            for delta in p['injections']:
                pairs,cameras=synthetic_pairs(motion,noise,delta)
                E=essential(*cameras)
                for length in [25,50,100]:
                    for absolute in [True,False]:
                        grid=np.unique(np.r_[np.arange(-25,26),np.round(np.arange(-1,1.001,.05),8)])
                        curves=[];counts=[]
                        for aa,bb in pairs:
                            aa,bs=common_injections(aa,bb,[0],50,49+length)
                            curve,count=pair_costs(aa,bs[0],grid,E,800,base['minimum_pair_samples_per_track'],absolute)
                            curves.append(curve);counts.append(count)
                        r=solve_curve(curves,grid,base)
                        eligible=r['lag'] is not None and not any(x in r['blockers'] for x in ['ambiguous optimum','boundary optimum'])
                        interval=r.get('bootstrap_95_frames')
                        r.update(motion=motion,noise_pixels=noise,known_offset_frames=delta,length=length,
                                 estimator='absolute' if absolute else 'temporal_bias',reference_samples=counts,
                                 absolute_recovery_error_frames=r['lag']-delta if eligible else None,
                                 interval_covers_truth=bool(interval[0]<=delta<=interval[1]) if eligible and interval else None)
                        synthetic.append(r)
                        if noise==0 and length==100:
                            if motion=='constant_velocity' and not absolute:
                                safeguards.append(not r['passed'] and 'ambiguous optimum' in r['blockers'])
                            elif motion!='constant_velocity' or absolute:
                                safeguards.append(eligible and abs(r['lag']-delta)<=.05+1e-9)
    write(output/'real-audit.json',dict(rows=rows,source_sha256=track_hashes,
        interpretation='Saved mixed-resolution baseline tracks; relative shifts are not absolute ground truth. Local diagnostics cannot admit timing.'))
    write(output/'synthetic-audit.json',dict(rows=synthetic,safeguards_passed=all(safeguards),safeguard_count=len(safeguards),
        analytic='Rectified cameras and constant depth: e(f,lag)=focal*vy*(lag-delta)/(sqrt(2)*depth), independent of f. Subtracting each track median makes every lag cost zero.'))
    return dict(status='passed' if all(safeguards) else 'blocked',
                blockers=[] if all(safeguards) else ['failed synthetic safeguards'],
                real_curves=len(rows)*len(p['injections']),synthetic_curves=len(synthetic),
                interpretation='Audit completion only; old estimator unsupported on short windows, no timing accepted.')


class Components:
    def __init__(self,nodes):
        self.parent={n:n for n in nodes}

    def root(self,n):
        while self.parent[n]!=n:
            self.parent[n]=self.parent[self.parent[n]];n=self.parent[n]
        return n

    def union(self,a,b):
        a,b=self.root(a),self.root(b)
        self.parent[max(a,b)]=min(a,b)

    def groups(self):
        groups={}
        for n in sorted(self.parent):
            groups.setdefault(self.root(n),[]).append(n)
        return list(groups.values())


def merge_duplicates(tracks,camera,p):
    comp=Components(range(len(tracks)))
    for i,a in enumerate(tracks):
        for j in range(i+1,len(tracks)):
            b=tracks[j]
            _,ia,ib=np.intersect1d(a['frames'],b['frames'],return_indices=True)
            if len(ia)>=p['duplicate_overlap_samples'] and np.max(np.linalg.norm(a['xy'][ia]-b['xy'][ib],axis=1))<=p['duplicate_maximum_distance_pixels']:
                comp.union(i,j)
    merged=[]
    for members in comp.groups():
        longest=min(members,key=lambda i:(-len(tracks[i]['frames']),i))
        values={}
        for i in members:
            for f,xy in zip(tracks[i]['frames'],tracks[i]['xy']):
                values.setdefault(int(f),[]).append(xy)
        frames=np.array(sorted(values))
        if np.any(np.diff(frames)!=1):
            raise ValueError('duplicate merge produced frame gap')
        xy=np.array([np.mean(values[f],axis=0) for f in frames])
        merged.append(dict(frames=frames,xy=xy,normalized=undistort_points(xy,camera),
                           descriptor=tracks[longest]['descriptor'],source_track_ids=members))
    return merged


def build_groups(tracks,edges,p):
    nodes=[(c,i) for c in sorted(tracks) for i in range(len(tracks[c]))]
    comp=Components(nodes);matches=[]
    for edge in edges:
        a,b=edge['a'],edge['b']
        pairs=mutual_pairs(tracks[a],tracks[b])
        for i,j in pairs:
            comp.union((a,i),(b,j))
        matches.append(dict(a=a,b=b,pairs=[list(pair) for pair in pairs]))
    groups=[];rejected=[]
    for members in comp.groups():
        cameras=[c for c,_ in members]
        reason=None
        if len(set(cameras))!=len(cameras):
            reason='conflicting camera trajectories'
        elif len(set(cameras)-set(p['held_out_cameras']))<p['minimum_training_cameras']:
            reason='fewer than three training cameras'
        row=dict(members=[dict(camera_id=c,track_id=i) for c,i in members])
        if reason:
            rejected.append(dict(**row,reason=reason))
        else:
            groups.append(dict(**row,group_id=len(groups)))
    order=np.random.default_rng(p['split_seed']).permutation(len(groups))
    for i,index in enumerate(order):
        groups[index]['split']='optimization' if i%2==0 else 'assessment'
    support=[]
    for edge in edges:
        a,b=edge['a'],edge['b'];counts=Counter()
        ids={split:[] for split in ['optimization','assessment']}
        for group in groups:
            cameras={m['camera_id'] for m in group['members']}
            if {a,b}<=cameras:
                counts[group['split']]+=1;ids[group['split']].append(group['group_id'])
        support.append(dict(a=a,b=b,optimization=counts['optimization'],assessment=counts['assessment'],
                            group_ids=ids,passed=all(counts[s]>=p['minimum_groups_per_half'] for s in ids)))
    return groups,rejected,matches,support


def serial_track(t):
    return {k:v.tolist() if isinstance(v,np.ndarray) else v for k,v in t.items()}


def associate(p,output,base):
    folder=extract(p,read(p['audit']),output)
    raw=load_tracks(folder);cams={c['camera_id']:c for c in read(CALIBRATION)['cameras']}
    tracks={};counts=[]
    for c,items in sorted(raw.items()):
        bounded(p)
        tracks[c]=merge_duplicates(items,cams[c],p)
        counts.append(dict(camera_id=c,raw_tracks=len(items),merged_tracks=len(tracks[c])))
    edges=read(p['previous_frozen'])['edges']
    groups,rejected,matches,support=build_groups(tracks,edges,p)
    for c,items in tracks.items():
        write(output/f'merged-camera{c}.json',dict(camera_id=c,role='fit',frames=[50,149],
              source_sha256={str(folder/f'camera{c}-tracks.json'):sha256(folder/f'camera{c}-tracks.json')},
              tracks=[serial_track(t) for t in items]))
    write(output/'groups.json',dict(groups=groups,rejected=rejected,matches=matches,
                                    split_seed=0,unit='entire multiview group'))
    write(output/'support.json',dict(edges=support,cameras=counts))
    failed=[e for e in support if not e['passed']]
    return dict(status='blocked' if failed else 'passed',blockers=['inadequate multiview support'] if failed else [],
                eligible_groups=len(groups),rejected_components=len(rejected),
                rejected_reasons=dict(Counter(r['reason'] for r in rejected)),
                failed_edges=failed,passed_edges=len(support)-len(failed),cameras=counts,
                model_configurations_fitted=0)


def predecessor(path,config_sha,stages):
    result=read(path/'result.json')
    if result['config_sha256']!=config_sha or result['stage'] not in stages:
        raise ValueError('predecessor configuration or stage mismatch')
    verify_hashes(result['artifacts_sha256'])
    verify_hashes(result['source_sha256'])
    return result


def run(a):
    started=time.monotonic();p=read(a.config);base=validate_config(p);config_sha=sha256(a.config)
    prior=None
    if a.stage!='audit':
        if a.predecessor is None:
            raise ValueError('hashed predecessor required')
        prior=predecessor(a.predecessor,config_sha,{'associate','audit'} if a.stage=='package' else {'audit'} if a.stage=='associate' else {'associate','fit','assess'})
        if a.stage!='package' and prior['status']!='passed':
            raise ValueError('blocked predecessor: '+', '.join(prior['blockers']))
    if a.stage in ('fit','assess','select'):
        raise ValueError('production stages deferred at Plan007 admission blocker; no qualifying implementation or offsets')
    bounded(p)
    sources=baseline(p)
    sources.update({str(a.config):config_sha,**{str(f):sha256(f) for f in [Path(__file__),Path('scripts/basketball_shared_tracks_v1.py')]}})
    if prior:
        sources[str(a.predecessor/'result.json')]=sha256(a.predecessor/'result.json')
    a.output.mkdir(parents=True,exist_ok=False)
    write(a.output/'frozen.json',dict(config=p,config_sha256=config_sha,source_sha256=sources))
    try:
        if a.stage=='audit':
            result=audit(p,a.output,base)
        elif a.stage=='associate':
            result=associate(p,a.output,base)
        else:
            if prior['status']!='blocked':
                raise ValueError('package requires evidenced terminal blocker')
            for name in ['support.json','groups.json']:
                source=a.predecessor/name
                if source.exists():shutil.copyfile(source,a.output/name)
            result=dict(status='blocked',blockers=prior['blockers'],blocked_stage=prior['stage'],
                        predecessor_sha256=sha256(a.predecessor/'result.json'))
        verify_hashes(sources)
    except TimeoutError as error:
        result=dict(status='blocked',blockers=[str(error)])
    result.update(schema='basketball-shared-timing-stage/v1',stage=a.stage,config_sha256=config_sha,
                  source_sha256=sources,wall_seconds=time.monotonic()-started,
                  investigation_elapsed_seconds=time.time()-p['investigation_started_unix'],gpu_seconds=0,
                  candidate_offsets=None,accepted_timing=None,
                  roles=p['roles'],selection_previously_consumed=True,selection_consumed_this_attempt=False,
                  final_validation_consumed=False,
                  artifacts_sha256={str(f):sha256(f) for f in sorted(a.output.rglob('*.json'))})
    write(a.output/'result.json',result)
    print('stage',a.stage,result['status'],result['blockers'],flush=True)
    return int(result['status']=='blocked')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=['audit','associate','fit','assess','select','package'])
    parser.add_argument('--config',type=Path,required=True)
    parser.add_argument('--predecessor',type=Path)
    parser.add_argument('--output',type=Path,required=True)
    raise SystemExit(run(parser.parse_args()))
