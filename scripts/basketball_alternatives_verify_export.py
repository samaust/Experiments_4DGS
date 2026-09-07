"""Reproject saved observations after reloading an exported calibration.

Reads no reserved images and fits nothing; this verifies artifact serialization,
not another final-validation evaluation or candidate selection.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from basketball_alternatives_compare import load_export
from basketball_alternatives_protocol import CAMERAS
from basketball_alternatives_colmap import dump
from basketball_audit import sha256


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--calibration',type=Path,required=True)
    p.add_argument('--map',type=Path,required=True)
    p.add_argument('--observations',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    import pycolmap as cm
    load_export(a.calibration,expected=CAMERAS)
    value=json.loads(a.calibration.read_text());model=cm.Reconstruction(a.map)
    record=dict(calibration_sha256=sha256(a.calibration),cameras=[],status='verified',
                evidence_type='saved-observation serialization check; no final images read')
    for entry in value['cameras']:
        c=entry['camera_id'];path=a.observations/f'camera{c}-observations.npy'
        obs=np.load(path)
        points=np.array([model.point3D(int(pid)).xyz for pid in obs[:,1]])
        camera=cm.Camera(model=entry['camera_model'],params=entry['parameters_colmap'],width=960,height=540)
        K=camera.calibration_matrix();K[:2,2]-=.5
        if not np.allclose(K,entry['K'],atol=1e-8) or not np.isfinite(camera.params).all():
            raise ValueError('camera model disagrees with exported K')
        grid=np.array([(x,y) for x in np.linspace(.5,959.5,17) for y in np.linspace(.5,539.5,9)])
        normalized=camera.cam_from_img(grid)
        rays=np.column_stack((normalized,np.ones(len(grid))))
        roundtrip=np.linalg.norm(camera.img_from_cam(rays)-grid,axis=1)
        if not np.isfinite(roundtrip).all() or roundtrip.max()>1e-6:
            raise ValueError(f'camera {c}: image-wide distortion inversion failed')
        pose=cm.Rigid3d(cm.Rotation3d(np.array(entry['R'])),np.array(entry['t']))
        errors=np.linalg.norm(camera.img_from_cam(pose*points)-obs[:,2:4],axis=1)
        if not np.isfinite(errors).all() or not np.allclose(errors,obs[:,4],rtol=0,atol=1e-8):
            raise ValueError(f'camera {c}: saved and reloaded reprojections disagree')
        record['cameras'].append(dict(camera_id=c,observations=len(obs),
            max_error_delta_pixels=float(np.max(np.abs(errors-obs[:,4]))),observations_sha256=sha256(path),
            max_distortion_roundtrip_pixels=float(roundtrip.max())))
    record['max_error_delta_pixels']=max(r['max_error_delta_pixels'] for r in record['cameras'])
    dump(a.output,record);print(record['status'],record['max_error_delta_pixels'])


if __name__=='__main__':main()
