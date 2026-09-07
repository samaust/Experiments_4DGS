"""Pinned dense dynamic correspondences and bidirectional fitting-only tracks."""
import argparse
import json
from pathlib import Path
import time
import sys
import numpy as np
from basketball_audit import sha256
from basketball_continuation_audit import CALIBRATION, CALIBRATION_SHA, WORKSPACE, verify_hashes
from basketball_scale import read, write
from basketball_timing import undistort_points


def select_seeds(proposals,p):
    """Confidence-only spatial sampling; never use a timing residual to select."""
    order=sorted(proposals,key=lambda r:(-r['confidence'],r['target_frame'],r['xy_a'][0],r['xy_a'][1]))
    result=[];occupied=set()
    for r in order:
        cell=tuple(np.floor(np.array(r['xy_a'])/p['roma_source_cell_pixels']).astype(int))
        if cell in occupied:continue
        occupied.add(cell);result.append(r)
        if len(result)>=p['roma_max_seeds_per_pair']:break
    return result


def infer(a):
    import cv2
    import torch
    import torchvision
    from PIL import Image
    from edgs_source import load_roma, ROMA_PIN, ROMA_WEIGHTS
    p=read(a.protocol);verify_hashes(p['source_sha256'])
    if sys.version_info[:2]!=(3,14) or torch.__version__!='2.13.0+cu130' or torchvision.__version__!='0.28.0+cu130':
        raise ValueError('required Python/Torch/torchvision runtime changed')
    verify_hashes({str(CALIBRATION):CALIBRATION_SHA})
    source=read(WORKSPACE/'inputs/result.json');lookup={(r['camera_id'],r['source_frame_id']):r for r in source['observations']}
    a.output.mkdir(parents=True,exist_ok=False)
    cfg=dict(protocol_sha256=sha256(a.protocol),adapter_sha256=sha256(__file__),roma_revision=ROMA_PIN,
             weight_sha256=ROMA_WEIGHTS,reference_frame=p['roma_reference_frame'],target_frames=p['roma_target_frames'])
    write(a.output/'config.json',cfg)
    result=dict(status='running',pairs=[],config_sha256=sha256(a.output/'config.json'),image_sha256={},mask_sha256={})
    started=time.monotonic()
    try:
        torch.manual_seed(0);model=load_roma(a.roma,a.weights);torch.cuda.reset_peak_memory_stats()
        result['runtime']=dict(python=sys.version,torch=torch.__version__,torchvision=torchvision.__version__,
                               cuda=torch.version.cuda,gpu=torch.cuda.get_device_name())
        images={};masks={}
        for c in range(34):
            for frame in sorted(set([p['roma_reference_frame']]+p['roma_target_frames'])):
                if frame not in range(50,150):raise ValueError('dense timing frame leakage')
                r=lookup[c,frame];ip=WORKSPACE/'inputs'/(r['stem']+'.png');mp=WORKSPACE/'inputs'/(r['stem']+'-static.png')
                verify_hashes({str(ip):r['image_sha256'],str(mp):r['mask_sha256']})
                images[c,frame]=Image.open(ip).convert('RGB');masks[c,frame]=cv2.imread(str(mp),0)==0
                result['image_sha256'][str(ip)]=r['image_sha256'];result['mask_sha256'][str(mp)]=r['mask_sha256']
        for e in p['graph']:
            ca,cb=e['a'],e['b'];proposals=[]
            for frame in p['roma_target_frames']:
                with torch.inference_mode():
                    warp,confidence=model.match(images[ca,p['roma_reference_frame']],images[cb,frame],device='cuda')
                    xa,xb=model.to_pixel_coordinates(warp.reshape(-1,4),540,960,540,960)
                xa=xa.cpu().numpy()-.5;xb=xb.cpu().numpy()-.5;confidence=confidence.flatten().cpu().numpy()
                good=np.isfinite(xa).all(1)&np.isfinite(xb).all(1)&np.isfinite(confidence)&(confidence>=p['roma_confidence'])
                for xy in [xa,xb]:good&=(xy[:,0]>=8)&(xy[:,0]<952)&(xy[:,1]>=8)&(xy[:,1]<532)
                idx=np.flatnonzero(good);ia=np.rint(xa[idx]).astype(int);ib=np.rint(xb[idx]).astype(int)
                idx=idx[masks[ca,p['roma_reference_frame']][ia[:,1],ia[:,0]]&masks[cb,frame][ib[:,1],ib[:,0]]]
                proposals.extend(dict(xy_a=xa[i].tolist(),xy_b=xb[i].tolist(),confidence=float(confidence[i]),target_frame=frame) for i in idx)
            selected=select_seeds(proposals,p);name=f'pair{ca}-{cb}.json'
            write(a.output/name,dict(a=ca,b=cb,reference_frame=p['roma_reference_frame'],seeds=selected))
            result['pairs'].append(dict(a=ca,b=cb,seeds=len(selected),path=name,sha256=sha256(a.output/name)))
            print('dense seeds',ca,cb,len(selected),flush=True)
        torch.cuda.synchronize();result.update(status='complete',peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                                               peak_reserved_bytes=torch.cuda.max_memory_reserved())
    except BaseException as error:
        result.update(status='failed',error=f'{type(error).__name__}: {error}');raise
    finally:
        result['wall_seconds']=time.monotonic()-started;write(a.output/'result.json',result)


def follow(gray,anchor,points,p):
    """Tracks are contiguous; a failed consistency check terminates that direction."""
    import cv2
    points=np.asarray(points,np.float32).reshape(-1,1,2)
    out=np.full((len(points),100,2),np.nan,np.float32);out[:,anchor-50]=points[:,0]
    for direction in [-1,1]:
        active=np.ones(len(points),bool);previous=points.copy();prevframe=anchor
        for frame in range(anchor+direction,50-1 if direction<0 else 150,direction):
            idx=np.flatnonzero(active)
            if not len(idx):break
            old=previous[idx]
            new,status,_=cv2.calcOpticalFlowPyrLK(gray[prevframe-50],gray[frame-50],old,None,winSize=(21,21),maxLevel=3)
            back,reverse,_=cv2.calcOpticalFlowPyrLK(gray[frame-50],gray[prevframe-50],new,None,winSize=(21,21),maxLevel=3)
            xy=new[:,0]
            good=(status.ravel()>0)&(reverse.ravel()>0)&np.isfinite(xy).all(1)&(np.linalg.norm(back-old,axis=2).ravel()<=p['maximum_forward_backward_pixels'])
            good&=(xy[:,0]>=8)&(xy[:,0]<952)&(xy[:,1]>=8)&(xy[:,1]<532)
            active[idx[~good]]=False;previous[idx[good]]=new[good];out[idx[good],frame-50]=xy[good]
            prevframe=frame
    return out


def track(a):
    import cv2
    p=read(a.protocol);audit=read(a.audit);seeds=read(a.seeds/'result.json');cfg=read(a.seeds/'config.json')
    if audit['status']!='passed' or seeds['status']!='complete':raise ValueError('incomplete upstream gate')
    if cfg['protocol_sha256']!=sha256(a.protocol) or cfg['adapter_sha256']!=sha256(__file__):raise ValueError('changed dense configuration')
    verify_hashes(audit['sha256']);verify_hashes(p['source_sha256']);verify_hashes(seeds['image_sha256']);verify_hashes(seeds['mask_sha256'])
    scheduled={c:[] for c in range(34)}
    for r in seeds['pairs']:
        path=a.seeds/r['path'];verify_hashes({str(path):r['sha256']});record=read(path);ca,cb=record['a'],record['b']
        for i,s in enumerate(record['seeds']):
            key=f'{ca}-{cb}-{i}'
            scheduled[ca].append(dict(pair_key=key,other_camera=cb,frame=record['reference_frame'],xy=s['xy_a']))
            scheduled[cb].append(dict(pair_key=key,other_camera=ca,frame=s['target_frame'],xy=s['xy_b']))
    a.output.mkdir(parents=True,exist_ok=False);cv2.setNumThreads(p['cpu_threads']);cv2.setRNGSeed(0)
    cams={e['camera_id']:e for e in read(CALIBRATION)['cameras']};started=time.monotonic();results=[]
    for v in audit['videos']:
        if time.monotonic()-started>p['maximum_cpu_seconds_per_stage']:raise TimeoutError('dense tracking CPU bound')
        c=v['camera_id'];verify_hashes({v['path']:v['sha256']})
        capture=cv2.VideoCapture(v['path']);capture.set(cv2.CAP_PROP_POS_FRAMES,50);gray=[]
        for frame in range(50,150):
            ok,image=capture.read()
            if not ok:raise ValueError(f'missing fitting frame {c}/{frame}')
            gray.append(cv2.cvtColor(cv2.resize(image,(960,540),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY))
        capture.release();kept=[]
        for anchor in sorted({s['frame'] for s in scheduled[c]}):
            if anchor not in range(50,150):raise ValueError('seed frame leakage')
            items=[s for s in scheduled[c] if s['frame']==anchor]
            trajectories=follow(gray,anchor,[s['xy'] for s in items],p)
            for item,trajectory in zip(items,trajectories):
                valid=np.isfinite(trajectory).all(1);frames=np.flatnonzero(valid)+50;xy=trajectory[valid]
                if len(frames)<p['minimum_track_length']:continue
                if np.any(np.diff(frames)!=1):raise ValueError('noncontiguous optical flow')
                if np.linalg.norm(np.ptp(xy,axis=0))<p['minimum_track_motion_pixels'] or np.median(np.linalg.norm(np.diff(xy,axis=0),axis=1))<p['minimum_median_track_speed_pixels']:continue
                kept.append(dict(pair_key=item['pair_key'],other_camera=item['other_camera'],frames=frames.tolist(),xy=xy.tolist(),normalized=undistort_points(xy,cams[c]).tolist()))
        path=a.output/f'camera{c}-tracks.json';write(path,dict(camera_id=c,role='fit',tracks=kept))
        results.append(dict(camera_id=c,tracks=len(kept),sha256=sha256(path)));print('dense tracks',c,len(kept),flush=True)
    write(a.output/'result.json',dict(status='complete',role='fit',cameras=results,wall_seconds=time.monotonic()-started,
        protocol_sha256=sha256(a.protocol),seeds_sha256=sha256(a.seeds/'result.json'),adapter_sha256=sha256(__file__)))


def main():
    p=argparse.ArgumentParser(description=__doc__);sub=p.add_subparsers(dest='mode',required=True)
    q=sub.add_parser('infer')
    for k in ['protocol','roma','weights','output']:q.add_argument('--'+k,type=Path,required=True)
    q=sub.add_parser('track')
    for k in ['protocol','audit','seeds','output']:q.add_argument('--'+k,type=Path,required=True)
    a=p.parse_args();return {'infer':infer,'track':track}[a.mode](a)


if __name__=='__main__':raise SystemExit(main())
