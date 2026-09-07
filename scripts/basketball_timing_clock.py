"""Fitting-only green clock change diagnostic; never exports accepted timing."""
import argparse
from pathlib import Path
import time

import numpy as np

from basketball_audit import sha256
from basketball_continuation_audit import CALIBRATION, CALIBRATION_SHA, verify_hashes
from basketball_scale import read, write


def validate_protocol(p):
    if p['fit_frames'] != [50,149] or not 50 <= p['detection_frame'] <= 149:
        raise ValueError('clock locator crosses fitting role boundary')
    if p['integer_search_radius'] != 25:
        raise ValueError('clock integer search changed')


def green_chroma(bgr):
    value=np.asarray(bgr,dtype=float)
    return np.maximum(value[...,1]-np.maximum(value[...,0],value[...,2]),0)


def detect_regions(bgr,p):
    import cv2
    x=np.asarray(bgr,float); b,g,r=x[...,0],x[...,1],x[...,2]
    mask=(g>=p['green_minimum'])&(g>p['green_over_red']*r)&(g>p['green_over_blue']*b)
    connected=cv2.dilate(mask.astype(np.uint8),np.ones(tuple(reversed(p['dilation_pixels'])),np.uint8))
    count,labels,stats,_=cv2.connectedComponentsWithStats(connected)
    candidates=[]
    for i in range(1,count):
        left,top,width,height,_=map(int,stats[i]);support=int(np.sum(mask&(labels==i)))
        if support<p['minimum_green_pixels'] or width>p['maximum_region_dimensions'][0] or height>p['maximum_region_dimensions'][1]:continue
        dark=float((x[top:top+height,left:left+width].max(axis=2)<p.get('dark_background_maximum',100)).mean())
        candidates.append(dict(box=[left,top,width,height],green_pixels=support,dark_fraction=dark))
    if 'minimum_dark_fraction' in p:
        candidates=[c for c in candidates if c['dark_fraction']>=p['minimum_dark_fraction'] and c['green_pixels']>=p['minimum_main_green_pixels']]
        candidates.sort(key=lambda c:(-c['box'][0],-c['green_pixels']))
        for c in candidates:
            left,top,width,height=c['box']
            c['box']=[left,top,min(width+p['right_padding_pixels'],bgr.shape[1]-left),height]
        return candidates
    return sorted(candidates,key=lambda c:(-c['green_pixels'],c['box']))


def change_signal(crops):
    arrays=np.asarray([green_chroma(c) for c in crops])
    return np.sqrt(np.mean(np.diff(arrays,axis=0)**2,axis=(1,2)))


def lag_curve(left,right,p):
    # Signal index zero is the transition from source frame 50 to 51.
    frames=np.arange(p['reference_transition_frames'][0],p['reference_transition_frames'][1]+1)
    grid=np.arange(-p['integer_search_radius'],p['integer_search_radius']+1)
    if frames.min()+grid.min()<51 or frames.max()+grid.max()>149:
        raise ValueError('clock comparison crosses fitting role boundary')
    scales=[float(np.quantile(s,.9)) for s in [left,right]]
    if min(scales)<p['minimum_signal_scale']:
        return dict(status='unsupported',reason='weak display-change signal',normalization=scales)
    a=np.asarray(left)/scales[0];b=np.asarray(right)/scales[1]
    costs=np.array([np.abs(a[frames-51]-b[frames+lag-51]) for lag in grid]).T
    curve=costs.mean(axis=0);index=int(np.argmin(curve));lag=int(grid[index])
    rng=np.random.default_rng(p['bootstrap_seed']);block=p['bootstrap_block_frames'];optima=[]
    for _ in range(p['bootstrap_resamples']):
        starts=rng.integers(0,len(frames)-block+1,int(np.ceil(len(frames)/block)))
        sample=np.concatenate([np.arange(s,s+block) for s in starts])[:len(frames)]
        optima.append(int(grid[np.argmin(costs[sample].mean(axis=0))]))
    interval=np.quantile(optima,[.025,.975]).tolist()
    other=np.delete(curve,index);gap=float(other.min()-curve[index])
    return dict(status='diagnostic_only',lag_frames=lag,bootstrap_95_integer_frames=interval,
                boundary=abs(lag)==p['integer_search_radius'],gap_to_other_integer=gap,
                grid=grid.tolist(),mean_absolute_change_difference=curve.tolist(),normalization=scales,
                fractional_timing_validated=False)


def run(a):
    import cv2
    started=time.monotonic();p=read(a.protocol);validate_protocol(p);audit=read(a.audit)
    if p['fit_frames']!=[50,149] or audit['status']!='passed':raise ValueError('invalid role/provenance')
    verify_hashes(audit['sha256']);verify_hashes({str(CALIBRATION):CALIBRATION_SHA})
    for v in audit['videos']:verify_hashes({v['path']:v['sha256']})
    a.output.mkdir(parents=True,exist_ok=False);cv2.setNumThreads(8)
    provenance={str(a.protocol):sha256(a.protocol),str(a.audit):sha256(a.audit),str(Path(__file__)):sha256(__file__)}
    write(a.output/'frozen.json',dict(protocol=p,sha256=provenance))
    records=[];signals={};previews=[]
    for c in p['camera_ids']:
        v=next(v for v in audit['videos'] if v['camera_id']==c)
        capture=cv2.VideoCapture(v['path']);capture.set(cv2.CAP_PROP_POS_FRAMES,p['detection_frame'])
        ok,frame=capture.read()
        if not ok:raise ValueError('missing fitting detection frame')
        candidates=detect_regions(frame,p)
        if not candidates:
            records.append(dict(camera_id=c,status='unsupported',reason='no automatic clock-color region'));capture.release();continue
        x,y,w,h=candidates[0]['box'];preview=frame.copy()
        cv2.rectangle(preview,(x,y),(x+w,y+h),(0,255,255),3)
        preview=cv2.resize(preview,(640,360));cv2.putText(preview,f'camera {c}',(10,30),0,.8,(0,0,255),2);previews.append(preview)
        capture.set(cv2.CAP_PROP_POS_FRAMES,50);crops=[]
        for f in range(50,150):
            if time.monotonic()-started>p['maximum_cpu_seconds']:raise TimeoutError('clock CPU bound')
            ok,frame=capture.read()
            if not ok or frame.shape[:2]!=(1080,1920):raise ValueError('missing fitting frame or changed dimensions')
            crops.append(frame[y:y+h,x:x+w].copy())
        capture.release();signal=change_signal(crops);signals[c]=signal
        scale=float(np.quantile(signal,.9));events=(np.where(signal/max(scale,1e-12)>=p['event_threshold_normalized'])[0]+51).tolist()
        records.append(dict(camera_id=c,status='diagnostic_only',selected_box=[x,y,w,h],candidates=candidates,
                            source_sha256=v['sha256'],signal=signal.tolist(),normalization=scale,event_frame_labels=events))
        # Preserve every observed digit state; labels are original source frame IDs, not OCR.
        cells=[]
        for i,crop in enumerate(crops):
            cell=np.zeros((90,240,3),np.uint8);display=cv2.resize(crop,(240,65));cell[:65]=display
            cv2.putText(cell,str(i+50),(4,84),0,.5,(255,255,255),1);cells.append(cell)
        cv2.imwrite(str(a.output/f'camera{c}-clock.jpg'),cv2.vconcat([cv2.hconcat(cells[i:i+10]) for i in range(0,100,10)]))
        print('clock',c,'region',[x,y,w,h],'events',len(events),'scale',scale,flush=True)
    if previews:
        rows=[]
        for i in range(0,len(previews),3):
            row=previews[i:i+3]
            while len(row)<3:row.append(np.zeros_like(previews[0]))
            rows.append(cv2.hconcat(row))
        cv2.imwrite(str(a.output/'regions.jpg'),cv2.vconcat(rows))
    edges=[]
    for ca,cb in p['comparison_edges']:
        row=lag_curve(signals[ca],signals[cb],p) if ca in signals and cb in signals else dict(status='unsupported',reason='missing clock region')
        edges.append(dict(a=ca,b=cb,**row));print('edge',ca,cb,row.get('lag_frames'),row.get('bootstrap_95_integer_frames'),flush=True)
    verify_hashes(audit['sha256']);verify_hashes(provenance)
    write(a.output/'result.json',dict(schema='basketball-clock-diagnostic-result/v1',status='inconclusive_for_subframe_timing',
        blockers=['frame-quantized clock transitions do not identify the source of 0.30-frame cycle disagreements',
                  'display face identity, exposure and refresh delays are not calibrated'],
        accepted_offsets=None,camera_blame=None,cameras=records,edges=edges,sha256=provenance,
        calibration_sha256=CALIBRATION_SHA,selection_consumed=False,final_validation_consumed=False,
        wall_seconds=time.monotonic()-started,gpu_seconds=0,
        artifacts_sha256={str(f):sha256(f) for f in sorted(a.output.iterdir())}))
    return 1


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['protocol','audit','output']:parser.add_argument('--'+name,type=Path,required=True)
    raise SystemExit(run(parser.parse_args()))
