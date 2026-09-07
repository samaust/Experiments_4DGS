"""Native tracking and fine fractional timing on the ten inconsistent-loop edges."""
import argparse
from pathlib import Path
import shutil
import time
from types import SimpleNamespace

import numpy as np

from basketball_audit import sha256
from basketball_continuation_audit import CALIBRATION, CALIBRATION_SHA, WORKSPACE, verify_hashes
from basketball_scale import read, write
from basketball_timing import undistort_points, graph_offsets
from basketball_timing_fine_fit import fit, replace_edges


def calibration_xy(xy):
    return (np.asarray(xy, dtype=float) + .5) / 2 - .5


def appearance_correlation(a, b):
    x = np.asarray(a, float).ravel(); y = np.asarray(b, float).ravel()
    x -= x.mean(); y -= y.mean()
    denominator = np.linalg.norm(x) * np.linalg.norm(y)
    return float(x @ y / denominator) if denominator > 1e-6 else -1.


def transition_tiles(before, after, p):
    """Persistent color changes, not a semantic advertising or timing detector."""
    changed = np.max(np.abs(before.astype(float)-after.astype(float)), axis=2) >= p['transition_channel_difference']
    h, w = changed.shape; n = p['transition_tile_pixels']
    if h % n or w % n:
        raise ValueError('transition grid does not divide image')
    fractions = changed.reshape(h//n, n, w//n, n).mean(axis=(1, 3))
    return np.argwhere(fractions >= p['transition_changed_fraction']).tolist()


def check_frames(frames):
    if len(frames) == 0 or min(frames) < 50 or max(frames) > 149 or np.any(np.diff(frames) != 1):
        raise ValueError('fitting frame boundary or gap violation')


def run(a):
    import cv2
    started = time.monotonic()
    p = read(a.protocol); audit = read(a.audit)
    if p['fit_frames'] != [50, 149] or audit['status'] != 'passed':
        raise ValueError('invalid fitting role/provenance')
    verify_hashes(audit['sha256']); verify_hashes({str(CALIBRATION): CALIBRATION_SHA})
    for v in audit['videos']:
        verify_hashes({v['path']: v['sha256']})
    base = read(p['base_frozen_protocol']); verify_hashes(base['source_sha256'])
    if base['timing_gate_frames'] != .25 or base['integer_search_radius'] != 25:
        raise ValueError('changed timing gate')
    prior_graph = read(p['prior_graph'])
    if prior_graph['calibration_sha256'] != CALIBRATION_SHA or prior_graph['selection_consumed'] or prior_graph['final_validation_consumed']:
        raise ValueError('invalid prior graph')
    a.output.mkdir(exist_ok=False, parents=True)
    provenance = {str(a.protocol): sha256(a.protocol), str(a.audit): sha256(a.audit),
                  str(Path(__file__)): sha256(__file__), p['base_frozen_protocol']: sha256(p['base_frozen_protocol']),
                  p['prior_graph']: sha256(p['prior_graph'])}
    write(a.output/'frozen.json', dict(protocol=p, sha256=provenance))
    target = {tuple(e) for e in p['target_edges']}
    base['graph'] = [e for e in base['graph'] if (e['a'], e['b']) in target]
    if len(base['graph']) != len(target):
        raise ValueError('target edge lacks verified geometric overlap')
    base.update({k:p[k] for k in ['fractional_step_frames','subset_minimum_tracks','subset_seed']})
    provenance['scripts/basketball_timing_fine_fit.py']=sha256('scripts/basketball_timing_fine_fit.py')
    base['source_sha256'].update(provenance)
    write(a.output/'fit-protocol.json', base)
    folder = a.output/'tracks'; folder.mkdir()
    prior = Path(p['prior_tracks']); prior_result = read(prior/'result.json')
    provenance[str(prior/'result.json')] = sha256(prior/'result.json')
    masks = {(e['camera_id'], e['source_frame_id']): e for e in read(WORKSPACE/'inputs/result.json')['observations']}
    cams = {e['camera_id']: e for e in read(CALIBRATION)['cameras']}
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
        capture = cv2.VideoCapture(v['path']); capture.set(cv2.CAP_PROP_POS_FRAMES,50)
        live = []; finished = []; previous = None; tiny = []; cuts[c] = 0
        for frame in range(50,150):
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
            check_frames(t['frames']); xy = calibration_xy(t['xy'])
            if len(xy)<base['minimum_track_length']: continue
            if np.linalg.norm(np.ptp(xy,axis=0))<base['minimum_track_motion_pixels'] or np.median(np.linalg.norm(np.diff(xy,axis=0),axis=1))<base['minimum_median_track_speed_pixels']: continue
            kept.append(dict(frames=t['frames'],xy=xy.tolist(),normalized=undistort_points(xy,cams[c]).tolist(),descriptor=t['descriptor'].tolist()))
        write(dest,dict(camera_id=c,role='fit',tracks=kept))
        records.append(dict(camera_id=c,tracks=len(kept),sha256=sha256(dest)))
        for i in range(3,97):
            before=np.median(tiny[i-3:i],axis=0); after=np.median(tiny[i:i+3],axis=0)
            tiles=transition_tiles(before,after,p)
            if len(tiles)>=p['transition_minimum_tiles']:
                events.append(dict(camera_id=c,source_frame_id=50+i,changed_tiles=tiles))
        print('native tracks',c,len(kept),'appearance cuts',cuts[c],flush=True)
    write(folder/'result.json',dict(status='complete',role='fit',cameras=records,wall_seconds=time.monotonic()-started))
    write(a.output/'transitions.json',dict(role='fit',candidates=events,appearance_cuts=cuts,
          interpretation='Unclassified persistent image changes; not matched advertising events; no timing offsets inferred'))
    fit(SimpleNamespace(protocol=a.output/'fit-protocol.json',tracks=folder,stage='sift-temporal-bias',output=a.output/'fit.json'))
    fitted=read(a.output/'fit.json'); edges=replace_edges(prior_graph['edges'],fitted['edges'],target)
    result=graph_offsets(edges,tolerance=.25)
    failed=[(e['a'],e['b']) for e in fitted['edges'] if not e['passed']]
    if failed:
        result.update(status='blocked',offsets=None,blockers=result['blockers']+['new target edges fail fitting acceptance'],failed_target_edges=failed)
    write(a.output/'result.json',dict(**result,edges=edges,calibration_sha256=CALIBRATION_SHA,
          selection_consumed=False,final_validation_consumed=False,wall_seconds=time.monotonic()-started,
          gpu_seconds=0,sha256=provenance,artifacts_sha256={str(f):sha256(f) for f in sorted(a.output.rglob('*.json'))},
          interpretation='Fine native target replacement; no prior target fallback, cycle pruning or clock constraints'))
    verify_hashes(audit['sha256']); verify_hashes(provenance)
    print(result,flush=True)
    return result['status']!='passed'


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['protocol','audit','output']: parser.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(run(parser.parse_args()))
