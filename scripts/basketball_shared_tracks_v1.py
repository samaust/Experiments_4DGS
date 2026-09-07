"""Plan007 versioned native fitting extractor; fixed 50..149 access only."""
import time
import numpy as np
from basketball_audit import sha256
from basketball_continuation_audit import CALIBRATION, WORKSPACE, verify_hashes
from basketball_scale import read, write
from basketball_timing import undistort_points
from basketball_timing_advertising import calibration_xy, appearance_correlation, check_frames


def extract(p, audit, output):
    import cv2
    started = time.monotonic()
    base = read(p['base_frozen_protocol'])
    folder = output / 'tracks'
    folder.mkdir()
    provenance = {}
    prior_result = dict(cameras=[dict(camera_id=c) for c in range(34)])
    masks = {(e['camera_id'], e['source_frame_id']): e for e in read(WORKSPACE/'inputs/result.json')['observations']}
    cams = {e['camera_id']: e for e in read(CALIBRATION)['cameras']}
    cv2.setNumThreads(8); cv2.setRNGSeed(0)
    sift = cv2.SIFT_create(nfeatures=p['sift_features'])
    records = []; events = []; cuts = {}
    for row in sorted(prior_result['cameras'], key=lambda r:r['camera_id']):
        c = row['camera_id']
        dest = folder/f'camera{c}-tracks.json'
        v = next(v for v in audit['videos'] if v['camera_id'] == c)
        capture = cv2.VideoCapture(v['path']); capture.set(cv2.CAP_PROP_POS_FRAMES,50)
        live = []; finished = []; previous = None; cuts[c] = 0
        for frame in range(50,150):
            if time.time()-p['investigation_started_unix'] > p['maximum_cpu_seconds']:
                raise TimeoutError('native tracking CPU bound')
            ok,bgr = capture.read()
            if not ok or list(bgr.shape[1::-1]) != p['native_dimensions']:
                raise ValueError('missing frame or changed dimensions')
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
        print('native tracks',c,len(kept),'appearance cuts',cuts[c],flush=True)
    write(folder/'result.json',dict(status='complete',role='fit',cameras=records,wall_seconds=time.monotonic()-started,source_sha256=provenance,extraction_policy='native masked SIFT/LK appearance continuity for all34'))
    return folder
