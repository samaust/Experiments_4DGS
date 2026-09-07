"""Frozen full-rig timing selection; final validation remains separately gated."""
import argparse
from pathlib import Path
import shutil
import time
import numpy as np
from basketball_audit import sha256
from basketball_continuation_audit import CALIBRATION,CALIBRATION_SHA,WORKSPACE,verify_hashes
from basketball_scale import read,write
from basketball_timing import graph_offsets,essential,undistort_points,match_tracks,solve_curve,epipolar_pixels
from basketball_timing_advertising import calibration_xy,appearance_correlation
from basketball_timing_recovery import signed_errors


def check_role_frames(frames,start,end):
    if len(frames)==0 or min(frames)<start or max(frames)>end or np.any(np.diff(frames)!=1):
        raise ValueError('reserved frame boundary/gap violation')


def role_cost(a,b,lag,grid,E,focal,start,end,minimum,absolute=False):
    times=a['frames']
    use=(times>=start)&(times<=end)&(times+min(grid)>=max(start,b['frames'][0]))&(times+max(grid)<=min(end,b['frames'][-1]))
    if use.sum()<minimum:return np.nan
    target=times[use]+lag
    yy=np.column_stack([np.interp(target,b['frames'],b['normalized'][:,k]) for k in range(2)])
    if absolute:return float(np.median(epipolar_pixels(a['normalized'][use],yy,E,focal)))
    error=signed_errors(a['normalized'][use],yy,E,focal);residual=error-np.median(error)
    return float(np.sqrt(np.mean(np.where(np.abs(residual)<=1,residual**2,2*np.abs(residual)-1))))


def validate_candidate(result):
    if result['calibration_sha256']!=CALIBRATION_SHA or result['selection_consumed'] or result['final_validation_consumed']:
        raise ValueError('candidate calibration/role violation')
    edges=[e for e in result['edges'] if e['passed']]
    if len({(e['a'],e['b']) for e in edges})!=len(edges):raise ValueError('duplicate candidate edge')
    graph=graph_offsets(edges,tolerance=.25)
    if graph['status']!='passed':raise ValueError('fitting candidate fails full-rig graph gate')
    return edges,graph


def run(a):
    import cv2
    started=time.monotonic();p=read(a.protocol);audit=read(a.audit)
    if p['role']!='selection' or p['role_frames']!=[150,199] or p['seed_frames']!=[150,160] or audit['status']!='passed':
        raise ValueError('selection role/provenance changed')
    verify_hashes(audit['sha256']);verify_hashes({str(CALIBRATION):CALIBRATION_SHA})
    for v in audit['videos']:verify_hashes({v['path']:v['sha256']})
    previous=read(p['prior_graph']);verify_hashes(previous['sha256']);verify_hashes(previous['artifacts_sha256'])
    edges,candidate=validate_candidate(previous)
    base=read(p['base_frozen_protocol']);verify_hashes(base['source_sha256'])
    if base['timing_gate_frames']!=.25:raise ValueError('timing gate changed')
    base.update(minimum_track_length=p['minimum_track_length'],optimum_gap_exclusion_frames=p['selection_optimum_gap_exclusion_frames'])
    provenance={str(a.protocol):sha256(a.protocol),str(a.audit):sha256(a.audit),str(Path(__file__)):sha256(__file__),
                p['prior_graph']:sha256(p['prior_graph']),p['base_frozen_protocol']:sha256(p['base_frozen_protocol'])}
    for name in ['basketball_timing','basketball_timing_advertising','basketball_timing_recovery']:
        path='scripts/'+name+'.py';provenance[path]=sha256(path)
    a.output.mkdir(parents=True,exist_ok=False)
    write(a.output/'frozen.json',dict(protocol=p,edges=edges,candidate=candidate,sha256=provenance))
    write(a.output/'selection-consumed.json',dict(role='selection',frozen_sha256=sha256(a.output/'frozen.json')))
    folder=a.output/'tracks';folder.mkdir();start,end=p['role_frames']
    prior=Path(p['prior_tracks']);prior_result=read(prior/'result.json')
    masks={(e['camera_id'],e['source_frame_id']):e for e in read(WORKSPACE/'inputs/result.json')['observations']}
    if any(f<50 or f>149 for _,f in masks):raise ValueError('mask source crosses fitting role')
    cams={e['camera_id']:e for e in read(CALIBRATION)['cameras']}
    cv2.setNumThreads(8); cv2.setRNGSeed(0)
    sift = cv2.SIFT_create(nfeatures=p['sift_features'])
    records = []; events = []; cuts = {}
    for row in sorted(prior_result['cameras'], key=lambda r:r['camera_id']):
        c = row['camera_id']; old = prior/f'camera{c}-tracks.json'
        verify_hashes({str(old):row['sha256']})
        dest = folder/old.name
        if c not in p['target_cameras']:
            shutil.copyfile(old, dest); records.append(row); continue
        v = next(v for v in audit['videos'] if v['camera_id'] == c)
        capture = cv2.VideoCapture(v['path']); capture.set(cv2.CAP_PROP_POS_FRAMES,start)
        live = []; finished = []; previous = None; tiny = []; cuts[c] = 0
        for frame in range(start,end+1):
            if time.monotonic()-started > p['maximum_cpu_seconds']:
                raise TimeoutError('native tracking CPU bound')
            ok,bgr = capture.read()
            if not ok or list(bgr.shape[1::-1]) != p['native_dimensions']:
                raise ValueError('missing frame or changed dimensions')
            tiny.append(cv2.resize(bgr,(960,540),interpolation=cv2.INTER_AREA))
            gray = cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY)
            if previous is not None and live:
                oldxy = np.array([t['xy'][-1] for t in live],np.float32).reshape(-1,1,2)
                new,status,_ = cv2.calcOpticalFlowPyrLK(previous,gray,oldxy,None,winSize=(p['lk_window_native_pixels'],)*2,maxLevel=3)
                back,reverse,_ = cv2.calcOpticalFlowPyrLK(gray,previous,new,None,winSize=(p['lk_window_native_pixels'],)*2,maxLevel=3)
                valid = (status.ravel()>0)&(reverse.ravel()>0)&(np.linalg.norm(back-oldxy,axis=2).ravel()<=p['maximum_forward_backward_native_pixels'])
                updated = []; size = (p['appearance_patch_native_pixels'],)*2
                for i,t in enumerate(live):
                    xy = new[i,0]
                    good = valid[i] and np.isfinite(xy).all() and 16<=xy[0]<1904 and 16<=xy[1]<1064
                    if good:
                        first = cv2.getRectSubPix(previous,size,tuple(map(float,oldxy[i,0])))
                        second = cv2.getRectSubPix(gray,size,tuple(map(float,xy)))
                        good = appearance_correlation(first,second)>=p['minimum_adjacent_patch_correlation']
                        cuts[c] += int(not good)
                    if good:
                        t['frames'].append(frame); t['xy'].append(xy.copy()); updated.append(t)
                    else:
                        finished.append(t)
                live = updated
            if frame in p['seed_frames']:
                nearest = min((f for cam,f in masks if cam==c),key=lambda f:(abs(f-frame),f))
                entry = masks[c,nearest]; path = WORKSPACE/'inputs'/(entry['stem']+'-static.png')
                verify_hashes({str(path):entry['mask_sha256']}); provenance[str(path)] = entry['mask_sha256']
                mask = cv2.resize(255-cv2.imread(str(path),0),(1920,1080),interpolation=cv2.INTER_NEAREST)
                kp,desc = sift.detectAndCompute(gray,mask)
                occupied = np.zeros(gray.shape,bool); spacing = p['seed_spacing_native_pixels']
                def occupy(xy):
                    x,y = np.round(xy).astype(int)
                    occupied[max(0,y-spacing):min(1080,y+spacing+1),max(0,x-spacing):min(1920,x+spacing+1)] = True
                for t in live: occupy(t['xy'][-1])
                count = 0
                for i in sorted(range(len(kp)),key=lambda i:-kp[i].response):
                    xy = np.array(kp[i].pt); x,y = np.round(xy).astype(int)
                    if kp[i].size>40 or not (16<=x<1904 and 16<=y<1064) or occupied[y,x]: continue
                    d = desc[i].astype(float); d = np.sqrt(d/max(d.sum(),1e-12))
                    live.append(dict(frames=[frame],xy=[xy],descriptor=d)); occupy(xy); count += 1
                    if count>=p['maximum_tracks_per_seed']: break
            previous = gray
        capture.release(); finished.extend(live); kept = []
        for t in finished:
            check_role_frames(t['frames'],start,end); xy = calibration_xy(t['xy'])
            if len(xy)<base['minimum_track_length']: continue
            if np.linalg.norm(np.ptp(xy,axis=0))<base['minimum_track_motion_pixels'] or np.median(np.linalg.norm(np.diff(xy,axis=0),axis=1))<base['minimum_median_track_speed_pixels']: continue
            kept.append(dict(frames=t['frames'],xy=xy.tolist(),normalized=undistort_points(xy,cams[c]).tolist(),descriptor=t['descriptor'].tolist()))
        write(dest,dict(camera_id=c,role='selection',tracks=kept))
        records.append(dict(camera_id=c,tracks=len(kept),sha256=sha256(dest)))
        print('native tracks',c,len(kept),'appearance cuts',cuts[c],flush=True)
    write(folder/'result.json',dict(status='complete',role='selection',cameras=records))
    tracks={}
    for row in records:
        c=row['camera_id'];items=read(folder/f'camera{c}-tracks.json')['tracks']
        for t in items:
            for k in ['frames','xy','normalized','descriptor']:t[k]=np.asarray(t[k])
            check_role_frames(t['frames'],start,end)
        tracks[c]=items
    if set(tracks)!=set(range(34)):raise ValueError('selection rig incomplete')
    evaluated=[]
    for edge in edges:
        ca,cb=edge['a'],edge['b'];E=essential(cams[ca],cams[cb]);focal=np.mean([cams[c]['K'][0][0] for c in [ca,cb]])
        pairs=match_tracks(tracks[ca],tracks[cb],base)
        radius=p['selection_search_radius'];grid=np.round(np.arange(edge['lag']-radius,edge['lag']+radius+.005,.01),8)
        absolute=edge.get('source')=='sift-absolute'
        def evaluate(lo,hi,minimum):
            costs=np.array([[role_cost(tracks[ca][i],tracks[cb][j],lag,grid,E,focal,lo,hi,minimum,absolute) for lag in grid] for i,j in pairs]).reshape(len(pairs),len(grid))
            return solve_curve(costs,grid,base)
        full=evaluate(start,end,base['minimum_pair_samples_per_track'])
        biases=[]
        if full['lag'] is not None:
            for i,j in pairs:
                ta,tb=tracks[ca][i],tracks[cb][j];times=ta['frames']
                use=(times+min(grid)>=max(start,tb['frames'][0]))&(times+max(grid)<=min(end,tb['frames'][-1]))
                if use.sum()<base['minimum_pair_samples_per_track']:continue
                target=times[use]+full['lag']
                yy=np.column_stack([np.interp(target,tb['frames'],tb['normalized'][:,k]) for k in range(2)])
                biases.append(float(np.median(signed_errors(ta['normalized'][use],yy,E,focal))))
        full['median_absolute_spatial_bias_pixels']=float(np.median(np.abs(biases))) if biases else None
        if not biases or full['median_absolute_spatial_bias_pixels']>base['bias_limit_pixels']:
            full['passed']=False;full['blockers'].append('original spatial support fails')
        halves=[evaluate(start,174,p['minimum_half_samples']),evaluate(175,end,p['minimum_half_samples'])]
        difference=abs(halves[0]['lag']-halves[1]['lag']) if all(h['lag'] is not None for h in halves) else None
        disagreement=abs(full['lag']-edge['lag']) if full['lag'] is not None else None
        passed=full['passed'] and all(h['passed'] for h in halves) and difference<=.25 and disagreement<=.25
        evaluated.append(dict(a=ca,b=cb,frozen_lag=edge['lag'],lag=full['lag'],passed=passed,
                              full=full,halves=halves,half_disagreement_frames=difference,fitting_disagreement_frames=disagreement))
        print('selection',ca,cb,'lag',full['lag'],'passed',passed,flush=True)
    graph=graph_offsets(evaluated,tolerance=.25)
    failed=[(e['a'],e['b']) for e in evaluated if not e['passed']]
    if failed:graph.update(status='blocked',offsets=None,blockers=graph['blockers']+['frozen selection edges fail'])
    verify_hashes(audit['sha256']);verify_hashes(provenance)
    write(a.output/'result.json',dict(**graph,edges=evaluated,failed_edges=failed,calibration_sha256=CALIBRATION_SHA,
        selection_consumed=True,final_validation_consumed=False,sha256=provenance,gpu_seconds=0,
        wall_seconds=time.monotonic()-started,artifacts_sha256={str(f):sha256(f) for f in sorted(a.output.rglob('*.json'))}))
    return graph['status']!='passed'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['protocol','audit','output']:parser.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(run(parser.parse_args()))
