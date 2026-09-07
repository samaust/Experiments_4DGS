"""Compare independently reconstructed fitting windows after a single Sim(3)."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from basketball_audit import sha256
from basketball_protocol import TRAINING, PROTOCOL


def similarity(source, target):
    source,target=np.asarray(source,dtype=float),np.asarray(target,dtype=float)
    if source.shape!=target.shape or source.ndim!=2 or source.shape[1]!=3 or len(source)<3:
        raise ValueError('need at least three paired camera centers')
    x,y=source-source.mean(0),target-target.mean(0)
    U,S,Vt=np.linalg.svd(x.T@y)
    sign=np.ones(3);sign[-1]=np.linalg.det(Vt.T@U.T)
    Q=Vt.T@np.diag(sign)@U.T
    if np.sum(x*x)<=1e-12 or S[1]<=1e-10*S[0]:
        raise ValueError('degenerate camera-center alignment')
    scale=float(np.sum(S*sign)/np.sum(x*x))
    return scale,Q,target.mean(0)-scale*Q@source.mean(0)


def compare_poses(reference_centers,reference_rotations,other_centers,other_rotations):
    reference_centers=np.asarray(reference_centers)
    scale,Q,t=similarity(other_centers,reference_centers)
    aligned_centers=scale*np.asarray(other_centers)@Q.T+t
    aligned_rotations=np.asarray(other_rotations)@Q.T
    center_error=np.linalg.norm(aligned_centers-reference_centers,axis=1)
    diameter=float(np.max(np.linalg.norm(reference_centers[:,None]-reference_centers[None,:],axis=-1)))
    angles=Rotation.from_matrix(aligned_rotations@np.asarray(reference_rotations).transpose(0,2,1)).magnitude()*180/np.pi
    return dict(scale=scale,rotation=Q.tolist(),translation=t.tolist(),rig_diameter=diameter,
                rotation_degrees=angles.tolist(),center_fraction_of_diameter=(center_error/diameter).tolist(),
                passed=bool(np.all(angles<=.5) and np.all(center_error/diameter<=.01)))


def load_candidate(folder):
    import pycolmap
    report=json.loads((folder/'result.json').read_text())
    if report['status']!='candidate-rig':
        raise ValueError(f'{folder}: no complete candidate')
    model=pycolmap.Reconstruction(folder/'sparse'/str(report['model_id']))
    centers=[];rotations=[]
    for camera in TRAINING:
        image=model.image(camera+1)
        pose=image.cam_from_world()
        centers.append(-pose.rotation.matrix().T@pose.translation)
        rotations.append(pose.rotation.matrix())
    return np.array(centers),np.array(rotations)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--reference',type=Path,required=True)
    p.add_argument('--other',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    ref=load_candidate(a.reference);other=load_candidate(a.other)
    result=compare_poses(*ref,*other)
    result.update(schema='basketball-pose-stability/v1',protocol=PROTOCOL,cameras=list(TRAINING),
                  reference=str(a.reference),other=str(a.other),
                  reference_result_sha256=sha256(a.reference/'result.json'),other_result_sha256=sha256(a.other/'result.json'),
                  adapter_sha256=sha256(__file__),rotation_limit_degrees=.5,center_limit_fraction=.01)
    with a.output.open('x') as f: json.dump(result,f,indent=2);f.write('\n')
    print('max rotation',max(result['rotation_degrees']),'max center fraction',max(result['center_fraction_of_diameter']))
    return not result['passed']


if __name__=='__main__': raise SystemExit(main())
