"""Shared static-map initialization, recolored only from reconstruction training images."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np
import pycolmap

from basketball_scene import BasketballScene


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--freeze',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    scene=BasketballScene(a.manifest)
    freeze=json.loads(a.freeze.read_text())
    if scene.manifest['freeze_sha256'] != digest(a.freeze):
        raise ValueError('freeze mismatch')
    root=Path(__file__).resolve().parents[1]
    model=pycolmap.Reconstruction(str(root/freeze['map_path']))
    keys=scene.training_keys(25)
    images={}
    inputs=[]
    for c,f in keys:
        entry=scene.frames[c,f];path=scene.path.parent/entry['path']
        if digest(path)!=entry['sha256']:
            raise ValueError('training image changed')
        images[int(c)]=cv2.cvtColor(cv2.imread(str(path)),cv2.COLOR_BGR2RGB)
        inputs.append(dict(camera_id=c,frame_id=f,sha256=entry['sha256']))
    points,colors=[],[]
    for point in model.points3D.values():
        ids={int(Path(model.images[e.image_id].name).stem.removeprefix('camera')) for e in point.track.elements}
        if not ids<=set(images):
            raise ValueError('map contains held-out camera evidence')
        xyz=point.xyz*freeze['scale']
        samples=[]
        for c in sorted(ids):
            camera=scene.cameras[str(c)]
            q=np.array(camera['world_to_camera_R'])@xyz+camera['world_to_camera_T']
            if q[2]<=0:continue
            uv=np.array(camera['K'])@q;uv=uv[:2]/uv[2]-.5
            x,y=np.round(uv).astype(int)
            if 0<=x<960 and 0<=y<540:samples.append(images[c][y,x])
        if len(samples)>=2:
            points.append(xyz);colors.append(np.median(samples,axis=0).astype(np.uint8))
    xyz=np.array(points,dtype=np.float32);rgb=np.array(colors,dtype=np.uint8)
    if len(xyz)<4 or not np.isfinite(xyz).all():raise ValueError('insufficient static initialization')
    a.output.mkdir(parents=True,exist_ok=False)
    ply=a.output/'initialization.ply'
    with ply.open('w') as stream:
        stream.write(f'ply\nformat ascii 1.0\nelement vertex {len(xyz)}\nproperty float x\nproperty float y\nproperty float z\nproperty uchar red\nproperty uchar green\nproperty uchar blue\nend_header\n')
        for x,c in zip(xyz,rgb):stream.write(' '.join(map(str,[*x,*c]))+'\n')
    archive=a.output/'static-cloud.npz';np.savez(archive,positions=xyz,colors=rgb.astype(np.float32)/255)
    report=dict(schema='basketball-static-initialization/v1',status='prepared',manifest_sha256=scene.sha256,
        source_frame=25,points=len(xyz),inputs=inputs,archive_sha256=digest(archive),ply_sha256=digest(ply),
        freeze_sha256=digest(a.freeze),map_path=freeze['map_path'],
        geometry_policy='accepted static map from separate calibration window; no new pose fitting',
        color_policy='median projected colors from physical training-camera source frame 25 only',
        motion_policy='static zero-velocity prior; no inferred dynamic or temporal ground truth',
        script_sha256=digest(__file__))
    (a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(points=len(xyz),training_images=len(inputs))))


if __name__=='__main__':main()
