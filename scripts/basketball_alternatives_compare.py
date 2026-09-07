"""Compare complete Plan 006 exports under one training-derived similarity."""
import argparse
import json
from pathlib import Path
import numpy as np
from scipy.spatial.transform import Rotation
from basketball_alternatives_protocol import TRAINING, HISTORICAL, SNAPSHOT_PAIRS, rank_complete
from basketball_pose_stability import similarity
from basketball_audit import sha256


def load_export(path, expected=TRAINING, *, require_positive_focal=True):
    value=json.loads(path.read_text())
    if value.get('image_size') != [960,540]:
        raise ValueError('unconverted image geometry')
    if value.get('pose_convention')!='world-to-camera' or value.get('pixel_convention')!='opencv-integer-centers':
        raise ValueError('unconverted pose/pixel convention')
    entries=value['cameras']
    if len(entries)!=len(expected) or {e['camera_id'] for e in entries}!=set(expected):
        raise ValueError('incomplete/duplicate/unexpected cameras')
    by_id={e['camera_id']:e for e in entries}
    centers=[];rotations=[]
    for c in expected:
        e=by_id[c]
        R,t,K,C=map(np.asarray,(e['R'],e['t'],e['K'],e['center']))
        if R.shape!=(3,3) or K.shape!=(3,3) or t.shape!=(3,) or C.shape!=(3,):
            raise ValueError('invalid calibration shapes')
        if not all(np.isfinite(v).all() for v in (R,t,K,C)):
            raise ValueError('nonfinite calibration')
        if not np.allclose(R@R.T,np.eye(3),atol=1e-4) or not np.isclose(np.linalg.det(R),1,atol=1e-4):
            raise ValueError('invalid rotation')
        if (require_positive_focal and min(K[0,0],K[1,1])<=0) or not np.allclose(C,-R.T@t,rtol=1e-4,atol=1e-4):
            raise ValueError(f'camera {c}: invalid focal or inverted pose')
        centers.append(C);rotations.append(R)
    return np.array(centers),np.array(rotations)


def frozen_errors(reference, other, transform, diameter):
    """Also used for held-outs: never fit a new transform inside this function."""
    C,R=reference;D,S=other
    scale,Q,t=transform
    aligned=scale*D@Q.T+t
    angles=Rotation.from_matrix((S@Q.T)@R.transpose(0,2,1)).magnitude()*180/np.pi
    return angles,np.linalg.norm(aligned-C,axis=1)/diameter


def compare(reference, other):
    C,R=reference;D,S=other
    transform=similarity(D,C)
    diameter=float(np.linalg.norm(C[:,None]-C[None,:],axis=-1).max())
    angles,centers=frozen_errors(reference,other,transform,diameter)
    scale,Q,t=transform
    per_camera=[dict(camera_id=c,rotation_degrees=float(angles[i]),center_fraction=float(centers[i]))
                for i,c in enumerate(TRAINING)]
    historical=[e for e in per_camera if e['camera_id'] in HISTORICAL]
    return dict(max_rotation_degrees=float(angles.max()),max_center_fraction=float(centers.max()),
                alignment=dict(scale=scale,rotation=Q.tolist(),translation=t.tolist(),diameter=diameter),
                per_camera=per_camera,historical_common=dict(
                    cameras=list(HISTORICAL),max_rotation_degrees=max(e['rotation_degrees'] for e in historical),
                    max_center_fraction=max(e['center_fraction'] for e in historical)),
                passed=bool(angles.max()<=.5 and centers.max()<=.01))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--workspace',type=Path,required=True)
    p.add_argument('--methods',nargs='+',required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    results=[]
    for method in a.methods:
        for pair in SNAPSHOT_PAIRS:
            row=dict(method=method,frames=pair,cameras=list(TRAINING),complete=False)
            folders=[a.workspace/f'{method}-{frame}' for frame in pair]
            reports=[json.loads((f/'result.json').read_text()) if (f/'result.json').exists() else None for f in folders]
            row['run_statuses']=[r['status'] if r else 'not-run' for r in reports]
            if all(r and r['status']=='complete' for r in reports):
                paths=[f/f"calibration-{r['model_id']}.json" for f,r in zip(folders,reports)]
                try:
                    row.update(compare(*(load_export(path) for path in paths)))
                    row.update(complete=True,export_sha256=[sha256(path) for path in paths],
                               wall_seconds=sum(r['wall_seconds']+r.get('frontend_wall_seconds',0) for r in reports))
                except ValueError as error:
                    row['error']=str(error)
                    # Diagnostic poses are still reported for full-coverage models
                    # with invalid K, but these rows remain ineligible to rank.
                    try:
                        row.update(compare(*(load_export(path,require_positive_focal=False) for path in paths)))
                        row['passed']=False
                        row['diagnostic_only']=True
                    except ValueError:
                        pass
            results.append(row)
    output=dict(schema='basketball-alternatives-screening/v1',pairs=results,ranking=rank_complete(results),
                evidence_type='repeatability; not ground-truth calibration accuracy')
    a.output.write_text(json.dumps(output,indent=2,allow_nan=False)+'\n')
    print(json.dumps(output['ranking'],indent=2))


if __name__=='__main__':
    main()
