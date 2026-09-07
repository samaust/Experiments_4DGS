"""Plan008 native, independently bidirectional seed tracks and checkpoint RootSIFT."""
from collections import Counter
import time
import numpy as np
from basketball_audit import sha256
from basketball_continuation_audit import CALIBRATION, WORKSPACE, verify_hashes
from basketball_scale import read, write
from basketball_timing import undistort_points
from basketball_timing_advertising import calibration_xy, appearance_correlation


def root_descriptor(d):
    d = np.asarray(d, dtype=float)
    return np.sqrt(d / max(d.sum(), 1e-12)).tolist()


def join_branches(seed, backward, forward):
    """Branches exclude the common seed and are ordered away from it."""
    samples = list(reversed(backward)) + [seed] + forward
    frames = [f for f, _ in samples]
    if any(b-a != 1 for a,b in zip(frames, frames[1:])):
        raise ValueError('noncontiguous seed branches')
    return frames, np.array([xy for _,xy in samples])


def follow(images, seed, points, direction, p, check):
    import cv2
    branches = [[] for _ in points]
    live = np.arange(len(points)); xy = np.asarray(points, np.float32).reshape(-1,1,2)
    counts = Counter()
    for frame in range(seed+direction, max(images)+1 if direction>0 else min(images)-1, direction):
        check()
        if not len(live): break
        previous, current = images[frame-direction], images[frame]
        new, status, _ = cv2.calcOpticalFlowPyrLK(previous,current,xy,None,winSize=(31,31),maxLevel=3)
        if new is None:
            counts['lk_failure'] += len(live); live = live[:0]; break
        back, reverse, _ = cv2.calcOpticalFlowPyrLK(current,previous,new,None,winSize=(31,31),maxLevel=3)
        valid = np.zeros(len(live),bool) if back is None else ((status.ravel()>0)&(reverse.ravel()>0)&(np.linalg.norm(back-xy,axis=2).ravel()<=1))
        keep=[]
        for i,idx in enumerate(live):
            pos=new[i,0]
            if not valid[i] or not np.isfinite(pos).all() or not (16<=pos[0]<1904 and 16<=pos[1]<1064):
                counts['lk_failure']+=1; continue
            size=(p['appearance_patch_native_pixels'],)*2
            a=cv2.getRectSubPix(previous,size,tuple(map(float,xy[i,0])))
            b=cv2.getRectSubPix(current,size,tuple(map(float,pos)))
            if appearance_correlation(a,b)<p['minimum_adjacent_patch_correlation']:
                counts['appearance_discontinuity']+=1; continue
            branches[idx].append((frame,pos.copy())); keep.append(i)
        live=live[keep]; xy=new[keep]
    counts['fitting_boundary']=len(live)
    return branches, counts


def extract(p, audit, output, check):
    import cv2
    started=time.monotonic(); base=read(p['base_frozen_protocol'])
    folder=output/'tracks'; folder.mkdir()
    entries=read(WORKSPACE/'inputs/result.json')['observations']
    # Filter BEFORE nearest-mask lookup: no reserved-role mask may enter fitting.
    masks={(e['camera_id'],e['source_frame_id']):e for e in entries if 50<=e['source_frame_id']<=149}
    cams={e['camera_id']:e for e in read(CALIBRATION)['cameras']}
    provenance={}; records=[]
    cv2.setNumThreads(8); cv2.setRNGSeed(0)
    sift=cv2.SIFT_create(nfeatures=p['sift_features'])
    for c in p['target_cameras']:
        check(); video=next(v for v in audit['videos'] if v['camera_id']==c)
        capture=cv2.VideoCapture(video['path'],cv2.CAP_FFMPEG,[cv2.CAP_PROP_N_THREADS,1])
        if not capture.isOpened(): raise ValueError('video open failed: '+video['path'])
        images={}
        try:
            capture.set(cv2.CAP_PROP_POS_FRAMES,50)
            for frame in range(50,150):
                check(); ok,bgr=capture.read()
                if not ok or list(bgr.shape[1::-1])!=p['native_dimensions']:
                    raise ValueError('missing frame or changed dimensions')
                images[frame]=cv2.cvtColor(bgr,cv2.COLOR_BGR2GRAY)
        finally:
            capture.release()
        kept=[]; seeds=[]; counts=Counter()
        for seed in p['seed_frames']:
            check()
            nearest=min((f for cam,f in masks if cam==c),key=lambda f:(abs(f-seed),f))
            entry=masks[c,nearest]; path=WORKSPACE/'inputs'/(entry['stem']+'-static.png')
            verify_hashes({str(path):entry['mask_sha256']}); provenance[str(path)]=entry['mask_sha256']
            mask=cv2.resize(255-cv2.imread(str(path),0),(1920,1080),interpolation=cv2.INTER_NEAREST)
            kp,desc=sift.detectAndCompute(images[seed],mask)
            occupied=np.zeros((1080,1920),bool); picked=[]; spacing=p['seed_spacing_native_pixels']
            for i in sorted(range(len(kp)),key=lambda i:(-kp[i].response,i)):
                x,y=np.round(kp[i].pt).astype(int)
                if kp[i].size>40 or not (16<=x<1904 and 16<=y<1064) or occupied[y,x]: continue
                picked.append(i); occupied[y-spacing:y+spacing+1,x-spacing:x+spacing+1]=True
                if len(picked)>=p['maximum_tracks_per_seed']: break
            points=[kp[i].pt for i in picked]
            backward,bc=follow(images,seed,points,-1,p,check)
            forward,fc=follow(images,seed,points,1,p,check)
            counts.update(bc); counts.update(fc); counts['seeded_tracks']+=len(picked)
            seed_counts=Counter(seeded=len(picked)); checkpoint_jobs={}
            for n,i in enumerate(picked):
                frames,native=join_branches((seed,points[n]),backward[n],forward[n]); xy=calibration_xy(native)
                if len(frames)<base['minimum_track_length']:
                    counts['length_rejected']+=1; seed_counts['length_rejected']+=1; continue
                if np.linalg.norm(np.ptp(xy,axis=0))<base['minimum_track_motion_pixels'] or np.median(np.linalg.norm(np.diff(xy,axis=0),axis=1))<base['minimum_median_track_speed_pixels']:
                    counts['motion_rejected']+=1; seed_counts['motion_rejected']+=1; continue
                sid=f'camera{c}-seed{seed}-keypoint{i}'
                checkpoints=[dict(frame=seed,descriptor=root_descriptor(desc[i]),source_track_id=sid,kind='seed')]
                for frame in frames:
                    if frame==seed or (frame-seed)%10: continue
                    pos=native[frame-frames[0]]
                    key=cv2.KeyPoint(float(pos[0]),float(pos[1]),kp[i].size,kp[i].angle,kp[i].response,kp[i].octave,len(kept))
                    checkpoint_jobs.setdefault(frame,[]).append(key)
                kept.append(dict(source_track_id=sid,seed_frame=seed,keypoint_index=i,keypoint_scale=kp[i].size,
                    keypoint_orientation=kp[i].angle,keypoint_octave=kp[i].octave,frames=frames,xy=xy.tolist(),
                    normalized=undistort_points(xy,cams[c]).tolist(),descriptor_checkpoints=checkpoints))
                seed_counts['retained']+=1
            for frame,keys in sorted(checkpoint_jobs.items()):
                check(); computed,descriptors=sift.compute(images[frame],keys)
                counts['descriptor_checkpoint_failure']+=len(keys)-len(computed)
                if descriptors is None: continue
                for key,d in zip(computed,descriptors):
                    target=kept[key.class_id]
                    target['descriptor_checkpoints'].append(dict(frame=frame,descriptor=root_descriptor(d),source_track_id=target['source_track_id'],kind='checkpoint'))
            seeds.append(dict(seed_frame=seed,mask_frame=nearest,counts=dict(seed_counts),backward=dict(bc),forward=dict(fc)))
        for t in kept: t['descriptor_checkpoints'].sort(key=lambda d:d['frame'])
        dest=folder/f'camera{c}-tracks.json'
        write(dest,dict(camera_id=c,role='fit',frames=[50,149],tracks=kept))
        counts['retained_tracks']=len(kept)
        records.append(dict(camera_id=c,tracks=len(kept),counts=dict(counts),seeds=seeds,sha256=sha256(dest)))
        write(folder/f'progress-camera{c}.json',dict(camera_id=c,record=records[-1],source_sha256=provenance))
        print('native bidirectional tracks',c,len(kept),'seeded',counts['seeded_tracks'],flush=True)
    write(folder/'result.json',dict(status='complete',role='fit',cameras=records,source_sha256=provenance,wall_seconds=time.monotonic()-started))
    return folder
