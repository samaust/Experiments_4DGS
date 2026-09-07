"""Dynamic-track timing of the immutable Basketball rig; fail closed on ambiguity."""
import argparse
import json
from pathlib import Path
import time
import numpy as np

from basketball_audit import sha256
from basketball_continuation_audit import CALIBRATION, CALIBRATION_SHA, WORKSPACE, verify_hashes
from basketball_scale import read, write


def validate_protocol(path):
    p=read(path)
    if p['calibration_sha256']!=CALIBRATION_SHA or p['reference_camera']!=1:
        raise ValueError('timing reference/calibration changed')
    if any(p[k]!=v for k,v in [('fit_frames',[50,149]),('selection_frames',[150,199]),('validation_frames',[200,249])]):
        raise ValueError('timing frame roles changed')
    if p['timing_gate_frames']!=.25 or p['integer_search_radius']!=25:
        raise ValueError('timing limits changed')
    return p


def undistort_points(xy,camera):
    import cv2
    k=camera['parameters_colmap'][3]
    K=np.array(camera['K'],float)
    return cv2.undistortPoints(np.asarray(xy,np.float64).reshape(-1,1,2),K,
        np.array([k,0.,0.,0.]),criteria=
        (cv2.TERM_CRITERIA_COUNT|cv2.TERM_CRITERIA_EPS,50,1e-12)).reshape(-1,2)


def essential(a,b):
    R=np.array(b['R'])@np.array(a['R']).T
    t=np.array(b['t'])-R@np.array(a['t'])
    tx=np.array([[0,-t[2],t[1]],[t[2],0,-t[0]],[-t[1],t[0],0]])
    return tx@R


def epipolar_pixels(x,y,E,focal):
    x=np.column_stack((x,np.ones(len(x))));y=np.column_stack((y,np.ones(len(y))))
    ex=x@E.T;ey=y@E
    denom=np.sqrt(ex[:,0]**2+ex[:,1]**2+ey[:,0]**2+ey[:,1]**2)
    return np.abs(np.sum(y*ex,axis=1))/np.maximum(denom,1e-12)*focal


def trajectory_cost(a,b,lag,E,focal,min_samples):
    # Both samples must be actual observations inside their declared role.
    times=a['frames'];target=times+lag
    use=(target>=b['frames'][0])&(target<=b['frames'][-1])
    if use.sum()<min_samples:return np.nan
    yy=np.column_stack([np.interp(target[use],b['frames'],b['normalized'][:,i]) for i in range(2)])
    return float(np.median(epipolar_pixels(a['normalized'][use],yy,E,focal)))


def solve_curve(costs,grid,p):
    """Every lag must have the declared support; bootstrap independent tracks."""
    costs=np.asarray(costs,float);grid=np.asarray(grid,float)
    good=np.isfinite(costs).all(axis=1)
    costs=costs[good]
    result=dict(support=int(len(costs)),passed=False,lag=None,blockers=[])
    if len(costs)<p['minimum_pair_tracks']:
        result['blockers']=['insufficient tracks spanning the full search'];return result
    curve=np.median(costs,axis=0);best=int(np.argmin(curve));lag=float(grid[best])
    result.update(lag=lag,grid=grid.tolist(),cost_pixels=curve.tolist(),best_pixels=float(curve[best]))
    if best in (0,len(grid)-1):result['blockers'].append('boundary optimum')
    away=np.abs(grid-lag)>p['optimum_gap_exclusion_frames']
    gap=float(np.min(curve[away])-curve[best]) if away.any() else 0.
    result['optimum_gap_pixels']=gap
    if gap<p['minimum_optimum_gap_pixels']:result['blockers'].append('ambiguous optimum')
    if curve[best]>p['maximum_pair_epipolar_pixels']:result['blockers'].append('epipolar inconsistency')
    rng=np.random.default_rng(p['bootstrap_seed'])
    selected=rng.integers(0,len(costs),(p['bootstrap_resamples'],len(costs)))
    optima=grid[np.argmin(np.median(costs[selected],axis=1),axis=1)]
    interval=np.quantile(optima,[.025,.975]);result['bootstrap_95_frames']=interval.tolist()
    if (interval[1]-interval[0])/2>p['timing_gate_frames']:result['blockers'].append('timing uncertainty')
    result['passed']=not result['blockers']
    return result


def graph_offsets(edges,cameras=tuple(range(34)),reference=1,tolerance=.25):
    accepted=[e for e in edges if e.get('passed')]
    neighbors={c:set() for c in cameras}
    for e in accepted:
        a,b=e['a'],e['b'];neighbors[a].add(b);neighbors[b].add(a)
    def reachable(start,omit=None):
        seen=set();todo=[start]
        while todo:
            c=todo.pop()
            if c in seen:continue
            seen.add(c)
            todo.extend(n for n in neighbors[c] if frozenset((c,n))!=omit)
        return seen
    missing=sorted(set(cameras)-reachable(reference))
    if missing:
        return dict(status='blocked',blockers=['disconnected accepted timing graph'],unreachable_cameras=missing,
                    accepted_edges=len(accepted),offsets=None)
    bridges=[(e['a'],e['b']) for e in accepted if len(reachable(reference,frozenset((e['a'],e['b']))))<len(cameras)]
    if bridges:
        return dict(status='blocked',blockers=['timing graph has unvalidated bridge edges'],bridges=bridges,offsets=None)
    # Test actual signed cycle closure before least squares can distribute an
    # inconsistent cycle over several individually small edge residuals.
    directed={}
    for e in accepted:
        directed[e['a'],e['b']]=e['lag'];directed[e['b'],e['a']]=-e['lag']
    tree_offsets={reference:0.};pending=[reference];tree_edges=set()
    while pending:
        c=pending.pop(0)
        for n in sorted(neighbors[c]):
            if n not in tree_offsets:
                tree_offsets[n]=tree_offsets[c]+directed[c,n]
                tree_edges.add(frozenset((c,n)));pending.append(n)
    closures=[abs(tree_offsets[e['b']]-tree_offsets[e['a']]-e['lag'])
              for e in accepted if frozenset((e['a'],e['b'])) not in tree_edges]
    free=[c for c in cameras if c!=reference];index={c:i for i,c in enumerate(free)}
    A=np.zeros((len(accepted),len(free)));y=[]
    for i,e in enumerate(accepted):
        if e['a']!=reference:A[i,index[e['a']]]=-1
        if e['b']!=reference:A[i,index[e['b']]]=1
        y.append(e['lag'])
    x=np.linalg.lstsq(A,np.array(y),rcond=None)[0];residual=np.abs(A@x-y)
    offsets={reference:0.,**{c:float(x[index[c]]) for c in free}}
    blockers=[]
    if max(closures,default=0)>tolerance or np.max(residual)>tolerance:
        blockers.append('inconsistent timing cycles')
    if max(abs(v) for v in offsets.values())>=25:
        blockers.append('reference-relative offset reaches search boundary')
    passed=not blockers
    return dict(status='passed' if passed else 'blocked',blockers=blockers,
                offsets=offsets if passed else None,diagnostic_offsets=offsets,
                max_edge_fit_residual_frames=float(residual.max()),
                max_cycle_closure_frames=float(max(closures,default=0)),accepted_edges=len(accepted))


def camera_graph(p):
    import pycolmap as cm
    cams={e['camera_id']:e for e in read(CALIBRATION)['cameras']}
    model=cm.Reconstruction('.local/calibration/basketball-alternatives/incremental-ba-radial-early-seed0-iter1000/sparse')
    xyz=np.array([v.xyz for v in model.points3D.values()]);visible={}
    for c,e in cams.items():
        point=xyz@np.array(e['R']).T+e['t']
        camera=cm.Camera(model=e['camera_model'],params=e['parameters_colmap'],width=960,height=540)
        uv=camera.img_from_cam(point)-.5
        visible[c]=(point[:,2]>0)&np.isfinite(uv).all(axis=1)&(uv[:,0]>=8)&(uv[:,0]<952)&(uv[:,1]>=8)&(uv[:,1]<532)
    edges={}
    for a in range(34):
        candidates=[]
        for b in range(34):
            if a==b:continue
            overlap=int(np.sum(visible[a]&visible[b]))
            if overlap>=p['minimum_static_overlap_points']:
                distance=float(np.linalg.norm(np.array(cams[a]['center'])-cams[b]['center']))
                candidates.append((distance,b,overlap))
        for distance,b,overlap in sorted(candidates)[:p['graph_neighbors']]:
            key=tuple(sorted((a,b)))
            edges[key]=dict(a=key[0],b=key[1],shared_static_points=overlap,center_distance=distance)
    return [edges[k] for k in sorted(edges)]


def track(a):
    import cv2
    p=validate_protocol(a.protocol);audit=read(a.audit)
    if audit['status']!='passed':raise ValueError('input provenance has not passed')
    verify_hashes(audit['sha256'])
    if a.role!='fit':raise ValueError('reserved tracking requires a frozen fit and separate validation implementation')
    a.output.mkdir(parents=True,exist_ok=False)
    frozen=dict(p,protocol_file_sha256=sha256(a.protocol),adapter_sha256=sha256(__file__),role=a.role,
                audit_sha256=sha256(a.audit),graph=camera_graph(p))
    write(a.output/'protocol.json',frozen)
    cv2.setNumThreads(p['cpu_threads']);cv2.setRNGSeed(0)
    source=read(WORKSPACE/'inputs/result.json')
    mask_entries={(e['camera_id'],e['source_frame_id']):e for e in source['observations']}
    cams={e['camera_id']:e for e in read(CALIBRATION)['cameras']}
    sift=cv2.SIFT_create(nfeatures=p['sift_features'])
    start,end=p['fit_frames'];started=time.monotonic();results=[]
    for video in audit['videos']:
        c=video['camera_id'];verify_hashes({video['path']:video['sha256']})
        capture=cv2.VideoCapture(video['path']);capture.set(cv2.CAP_PROP_POS_FRAMES,start)
        live=[];finished=[];previous=None
        for frame in range(start,end+1):
            if time.monotonic()-started>p['maximum_tracking_wall_seconds']:raise TimeoutError('frozen tracking CPU limit')
            ok,bgr=capture.read()
            if not ok:raise ValueError(f'missing frame {c}/{frame}')
            gray=cv2.cvtColor(cv2.resize(bgr,(960,540),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY)
            if previous is not None and live:
                old=np.array([t['xy'][-1] for t in live],np.float32).reshape(-1,1,2)
                new,status,_=cv2.calcOpticalFlowPyrLK(previous,gray,old,None,winSize=(p['lk_window'],)*2,maxLevel=p['lk_pyramid_levels'])
                back,reverse,_=cv2.calcOpticalFlowPyrLK(gray,previous,new,None,winSize=(p['lk_window'],)*2,maxLevel=p['lk_pyramid_levels'])
                valid=(status.ravel()>0)&(reverse.ravel()>0)&(np.linalg.norm(back-old,axis=2).ravel()<=p['maximum_forward_backward_pixels'])
                updated=[]
                for i,t in enumerate(live):
                    xy=new[i,0]
                    if valid[i] and np.isfinite(xy).all() and 8<=xy[0]<952 and 8<=xy[1]<532:
                        t['frames'].append(frame);t['xy'].append(xy.copy());updated.append(t)
                    else:finished.append(t)
                live=updated
            if frame in p['seed_frames']:
                nearest=min((f for cam,f in mask_entries if cam==c),key=lambda f:(abs(f-frame),f))
                item=mask_entries[c,nearest];path=WORKSPACE/'inputs'/(item['stem']+'-static.png')
                verify_hashes({str(path):item['mask_sha256']})
                dynamic=255-cv2.imread(str(path),0)
                keypoints,descriptors=sift.detectAndCompute(gray,dynamic)
                points=[t['xy'][-1] for t in live];count=0
                for i in sorted(range(len(keypoints)),key=lambda i:-keypoints[i].response):
                    kp=keypoints[i];xy=np.array(kp.pt)
                    if kp.size>20 or (points and min(np.linalg.norm(xy-q) for q in points)<p['seed_spacing_pixels']):continue
                    d=descriptors[i].astype(float);d=np.sqrt(d/max(d.sum(),1e-12))
                    live.append(dict(frames=[frame],xy=[xy],descriptor=d));points.append(xy);count+=1
                    if count>=p['maximum_tracks_per_seed']:break
            previous=gray
        capture.release();finished.extend(live);kept=[]
        for t in finished:
            xy=np.array(t['xy']);speed=np.linalg.norm(np.diff(xy,axis=0),axis=1)
            if len(xy)<p['minimum_track_length']:continue
            if np.linalg.norm(np.ptp(xy,axis=0))<p['minimum_track_motion_pixels'] or np.median(speed)<p['minimum_median_track_speed_pixels']:continue
            normalized=undistort_points(xy,cams[c])
            kept.append(dict(frames=t['frames'],xy=xy.tolist(),normalized=normalized.tolist(),descriptor=t['descriptor'].tolist()))
        path=a.output/f'camera{c}-tracks.json';write(path,dict(camera_id=c,role='fit',tracks=kept))
        results.append(dict(camera_id=c,tracks=len(kept),sha256=sha256(path)))
        print('tracks',c,len(kept),flush=True)
    write(a.output/'result.json',dict(status='complete',cameras=results,role='fit',wall_seconds=time.monotonic()-started,
        protocol_sha256=sha256(a.output/'protocol.json'),adapter_sha256=sha256(__file__)))


def match_tracks(a,b,p):
    if len(a)<2 or len(b)<2:return []
    da=np.array([t['descriptor'] for t in a]);db=np.array([t['descriptor'] for t in b])
    distances=np.linalg.norm(da[:,None]-db[None,:],axis=2)
    order=np.argsort(distances,axis=1);reverse=np.argmin(distances,axis=0)
    return [(i,int(j)) for i,(j,k) in enumerate(order[:,:2]) if reverse[j]==i and distances[i,j]<p['descriptor_ratio']*distances[i,k]]


def fit(a):
    p=read(a.tracks/'protocol.json');result=read(a.tracks/'result.json')
    verify_hashes({str(a.tracks/'protocol.json'):result['protocol_sha256']})
    if result['status']!='complete' or result['role']!='fit' or p['adapter_sha256']!=sha256(__file__):
        raise ValueError('incomplete or changed fitting tracks')
    tracks={};cameras={e['camera_id']:e for e in read(CALIBRATION)['cameras']}
    verify_hashes({str(CALIBRATION):CALIBRATION_SHA})
    for row in result['cameras']:
        c=row['camera_id'];path=a.tracks/f'camera{c}-tracks.json';verify_hashes({str(path):row['sha256']})
        tracks[c]=read(path)['tracks']
        for t in tracks[c]:
            for k in ['frames','xy','normalized','descriptor']:t[k]=np.array(t[k])
            if any(f<50 or f>149 for f in t['frames']) or np.any(np.diff(t['frames'])!=1):raise ValueError('track role/gap violation')
    if set(tracks)!=set(range(34)):raise ValueError('missing camera tracks')
    edges=[];radius=p['integer_search_radius'];integer=np.arange(-radius,radius+1,dtype=float)
    for edge in p['graph']:
        ca,cb=edge['a'],edge['b'];E=essential(cameras[ca],cameras[cb])
        focal=np.mean([cameras[c]['K'][0][0] for c in [ca,cb]])
        matches=match_tracks(tracks[ca],tracks[cb],p)
        compute=lambda grid:np.array([[trajectory_cost(tracks[ca][i],tracks[cb][j],d,E,focal,p['minimum_pair_samples_per_track']) for d in grid] for i,j in matches]).reshape(len(matches),len(grid))
        costs=compute(integer)
        eligible=np.isfinite(costs).all(axis=1)
        # Correspondence rejection uses the entire fitting search, never reserved observations.
        if len(costs):eligible &= np.nanmin(costs,axis=1)<=p['maximum_pair_epipolar_pixels']
        filtered=costs[eligible];coarse=solve_curve(filtered,integer,p)
        out=dict(edge,descriptor_matches=len(matches),integer=coarse,passed=False,lag=None)
        if coarse['lag'] is not None and abs(coarse['lag'])<radius:
            local=np.arange(coarse['lag']-1,coarse['lag']+1.00001,p['fractional_step_frames'])
            grid=np.unique(np.round(np.concatenate((integer,local)),8))
            refined=solve_curve(compute(grid)[eligible],grid,p)
            out.update(refined=refined,passed=refined['passed'],lag=refined['lag'])
        else:out['blockers']=coarse['blockers']
        edges.append(out);print('edge',ca,cb,'matches',len(matches),'lag',out['lag'],'passed',out['passed'],flush=True)
    graph=graph_offsets(edges,tolerance=p['timing_gate_frames'])
    write(a.output,dict(schema='basketball-timing-fit/v1',**graph,edges=edges,
        tracks_sha256=sha256(a.tracks/'result.json'),protocol_sha256=sha256(a.tracks/'protocol.json'),
        adapter_sha256=sha256(__file__),calibration_sha256=CALIBRATION_SHA,
        offset_convention=p['offset_convention'],selection_consumed=False,final_validation_consumed=False))
    return graph['status']!='passed'


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='command',required=True)
    q=sub.add_parser('track');q.add_argument('--protocol',type=Path,required=True);q.add_argument('--audit',type=Path,required=True)
    q.add_argument('--role',choices=['fit','selection','validation'],default='fit');q.add_argument('--output',type=Path,required=True)
    q=sub.add_parser('fit');q.add_argument('--tracks',type=Path,required=True);q.add_argument('--output',type=Path,required=True)
    a=p.parse_args();return dict(track=track,fit=fit)[a.command](a)


if __name__=='__main__':raise SystemExit(main())
