"""Freeze prediction-independent motion-region crops for reconstruction evaluation."""
import argparse
import hashlib
import json
from pathlib import Path
import cv2
import numpy as np


def digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def motion_region(image, background):
    difference=np.max(np.abs(image.astype(np.float32)-background),axis=-1)>25
    opened=cv2.morphologyEx(difference.astype(np.uint8),cv2.MORPH_OPEN,np.ones((5,5),np.uint8))
    count,labels,stats,_=cv2.connectedComponentsWithStats(opened)
    keep=np.zeros_like(opened)
    for i in range(1,count):
        if stats[i,cv2.CC_STAT_AREA]>=64:keep[labels==i]=1
    y,x=np.nonzero(keep)
    if not len(x):return keep,None
    height,width=keep.shape
    x0,x1=max(0,int(x.min())-8),min(width,int(x.max())+9)
    y0,y1=max(0,int(y.min())-8),min(height,int(y.max())+9)
    if x1-x0<32:x0=max(0,min(x0,width-32));x1=x0+32
    if y1-y0<32:y0=max(0,min(y0,height-32));y1=y0+32
    return keep,[x0,y0,x1,y1]


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    m=json.loads(a.manifest.read_text());a.output.mkdir(parents=True,exist_ok=False)
    rows=[];reference_frames=[0,5,10,15,25,30,35,40,45]
    for camera in m['cameras']:
        def read(f):
            entry=camera['frames'][f];path=a.manifest.parent/entry['path']
            if digest(path)!=entry['sha256']:raise ValueError('evaluation input changed')
            return cv2.imread(str(path))
        background=np.median(np.stack([read(f) for f in reference_frames]),axis=0)
        targets=range(50) if camera['split']=='test' else range(20,25)
        for f in targets:
            mask,bbox=motion_region(read(f),background)
            path=a.output/f"{camera['id']}-{f:06d}.png"
            if not cv2.imwrite(str(path),mask*255):raise RuntimeError('mask write failed')
            rows.append(dict(camera=camera['id'],frame_id=f,bbox=bbox,motion_pixels=int(mask.sum()),
                             mask_path=path.name,mask_sha256=digest(path)))
        print(json.dumps(dict(camera=camera['id'],evaluated=len(targets))),flush=True)
    report=dict(schema='basketball-evaluation-regions/v1',manifest_sha256=digest(a.manifest),
        script_sha256=digest(__file__),reference_frames=reference_frames,
        policy='evaluation-only temporal median over nine non-reserved source times per camera; max channel uint8 difference >25, 5x5 opening, components >=64 pixels; motion bounding rectangle padded 8 pixels, minimum 32x32; no predicted image used',
        caveat='motion proxy, not person/ball segmentation ground truth; lighting, compression and display changes may be included; held-out-camera reference images used only to define evaluation regions',
        metrics='full RGB and motion-region crop PSNR/SSIM/LPIPS; empty motion regions reported null, not zero error',frames=rows)
    (a.output/'regions.json').write_text(json.dumps(report,indent=2)+'\n')


if __name__=='__main__':main()
