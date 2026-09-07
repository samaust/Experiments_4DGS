"""Localize all four held-out cameras against an immutable training map."""
import argparse
from collections import defaultdict
import json
import shutil
from pathlib import Path
import time
import numpy as np
from basketball_audit import sha256
from basketball_alternatives_protocol import TRAINING,HELD_OUT,PROTOCOL
from basketball_alternatives_colmap import dump
from basketball_alternatives_refine import deduplicate


def held_out_features(inputs,camera,frames):
    import cv2
    prepared=json.loads((inputs/'result.json').read_text())
    entries={(e['camera_id'],e['source_frame_id']):e for e in prepared['observations']}
    sift=cv2.SIFT_create(nfeatures=8192)
    candidates=[];descriptors=[]
    for f in frames:
        e=entries[camera,f];im=inputs/(e['stem']+'.png');mask=inputs/(e['stem']+'-static.png')
        if sha256(im)!=e['image_sha256'] or sha256(mask)!=e['mask_sha256']:
            raise ValueError('changed held-out input')
        gray=cv2.imread(str(im),cv2.IMREAD_GRAYSCALE);m=cv2.imread(str(mask),cv2.IMREAD_GRAYSCALE)
        distance=cv2.distanceTransform((m>0).astype(np.uint8),cv2.DIST_L2,5)
        keys,desc=sift.detectAndCompute(gray,m)
        if desc is None:continue
        for key,d in zip(keys,desc):
            x,y=np.rint(key.pt).astype(int)
            if distance[y,x]<max(8.,3*key.size):continue
            candidates.append(dict(xy=key.pt,frame=f,score=float(key.response),index=len(descriptors)))
            descriptors.append(d)
    selected=deduplicate(sorted(candidates,key=lambda e:(-e['score'],e['frame'],e['index'])))
    return np.array([e['xy'] for e in selected])+.5,np.array([descriptors[e['index']] for e in selected],dtype=np.float32)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map',type=Path,required=True)
    p.add_argument('--features',type=Path,required=True)
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--seed',type=int,default=0)
    a=p.parse_args()
    import cv2
    import pycolmap as cm
    training=json.loads((a.map/'result.json').read_text())
    if training['status']!='complete':raise ValueError('training map incomplete')
    feature_report=json.loads((a.features/'result.json').read_text())
    if feature_report['frames']!=training['frames']:raise ValueError('window mismatch')
    paths=list((a.map/'sparse').glob('*.bin'))+[a.features/'features.db',a.map/'calibration-0.json']
    frozen={str(path):sha256(path) for path in paths}
    model=cm.Reconstruction(a.map/'sparse')
    if sorted(im.camera_id-1 for im in model.images.values())!=list(TRAINING):
        raise ValueError('training map coverage changed')
    a.output.mkdir(parents=True,exist_ok=False)
    # Even opening a PyCOLMAP DB can increment SQLite header counters.
    # Read its private copy so the source evidence stays byte-for-byte frozen.
    shutil.copy2(a.features/'features.db',a.output/'read-only-source-copy.db')
    report=dict(protocol=PROTOCOL,status='running',frames=training['frames'],seed=a.seed,
                frozen_artifact_sha256=frozen,cameras=[],failures=[],adapter_sha256=sha256(__file__))
    start=time.monotonic()
    try:
        with cm.Database.open(a.output/'read-only-source-copy.db') as db:
            galleries=[]
            for c in TRAINING:
                im=model.image(c+1);indices=[];pids=[]
                for i,p2 in enumerate(im.points2D):
                    if p2.has_point3D() and model.point3D(p2.point3D_id).track.length()>=3:
                        indices.append(i);pids.append(p2.point3D_id)
                galleries.append((c,np.asarray(db.read_descriptors(c+1).data)[indices].astype(np.float32),pids))
        for c in HELD_OUT:
            xy,desc=held_out_features(a.inputs,c,training['frames'])
            votes=defaultdict(lambda:defaultdict(list))
            matcher=cv2.BFMatcher(cv2.NORM_L2)
            for other,gallery,pids in galleries:
                if len(gallery)<2:continue
                for pair in matcher.knnMatch(desc,gallery,k=2):
                    if len(pair)!=2:continue
                    m,n=pair
                    if m.distance<.8*n.distance:
                        votes[m.queryIdx][pids[m.trainIdx]].append((other,m.distance))
            matches=[]
            for qi,by_point in votes.items():
                for pid,support in by_point.items():
                    if len(support)>=2:
                        matches.append((len(support),sum(d for _,d in support)/len(support),qi,pid))
            used_query=set();used_points=set();selected=[]
            for _,_,qi,pid in sorted(matches,key=lambda m:(-m[0],m[1],m[2],m[3])):
                if qi in used_query or pid in used_points:continue
                used_query.add(qi);used_points.add(pid);selected.append((qi,pid))
            if len(selected)<100:
                report['failures'].append(f'camera {c}: only {len(selected)} independent multi-camera matches')
                continue
            points2D=np.array([xy[qi] for qi,pid in selected]);points3D=np.array([model.point3D(pid).xyz for qi,pid in selected])
            camera=cm.Camera(model='SIMPLE_RADIAL',width=960,height=540,params=[1152.,480.,270.,0.])
            camera.has_prior_focal_length=False
            estimation=cm.AbsolutePoseEstimationOptions(estimate_focal_length=True)
            estimation.ransac.max_error=3.;estimation.ransac.random_seed=a.seed
            refinement=cm.AbsolutePoseRefinementOptions(refine_focal_length=True,refine_extra_params=True)
            cm.set_random_seed(a.seed)
            estimated=cm.estimate_and_refine_absolute_pose(points2D,points3D,camera,estimation,refinement)
            if estimated is None:
                report['failures'].append(f'camera {c}: PnP failed');continue
            pose=estimated['cam_from_world'];inliers=np.asarray(estimated['inlier_mask'],dtype=bool)
            kept3=points3D[inliers];kept2=points2D[inliers]
            transformed=pose*kept3
            projected=camera.img_from_cam(transformed)
            errors=np.linalg.norm(projected-kept2,axis=1)
            cells={tuple(v) for v in np.floor(kept2/[240.,135.]).astype(int) if np.all((v>=0)&(v<4))}
            K=camera.calibration_matrix();K[:2,2]-=.5;R=pose.rotation.matrix();t=pose.translation
            row=dict(camera_id=c,R=R.tolist(),t=t.tolist(),center=(-R.T@t).tolist(),K=K.tolist(),
                camera_model=camera.model_name,parameters_colmap=camera.params.tolist(),
                independent_static_points=int(inliers.sum()),occupied_grid_cells=len(cells),
                positive_depth_fraction=float(np.mean(transformed[:,2]>0)),
                reprojection_median=float(np.median(errors)),reprojection_p95=float(np.percentile(errors,95)))
            passed=(row['independent_static_points']>=100 and len(cells)>=6 and
                row['positive_depth_fraction']>=.95 and row['reprojection_median']<=1 and
                row['reprojection_p95']<=3 and camera.params[0]>0)
            row['support_passed']=passed
            if not passed:report['failures'].append(f'camera {c}: localization support/reprojection gate failed')
            report['cameras'].append(row)
            np.savez_compressed(a.output/f'camera{c}-observations.npz',points2D=points2D,points3D=points3D,inliers=inliers)
            print(c,int(inliers.sum()),row['reprojection_median'],row['reprojection_p95'],flush=True)
        if any(sha256(path)!=digest for path,digest in frozen.items()):
            raise ValueError('frozen map or training observations changed during localization')
        report['status']='localized' if len(report['cameras'])==4 and not report['failures'] else 'blocked'
        export=dict(schema='basketball-native-calibration/v1',protocol=PROTOCOL,
                    pixel_convention='opencv-integer-centers',pose_convention='world-to-camera',
                    image_size=[960,540],cameras=report['cameras'],complete=len(report['cameras'])==4)
        dump(a.output/'calibration.json',export)
    except BaseException as error:
        report.update(status='failed');report['failures'].append(f'{type(error).__name__}: {error}')
        raise
    finally:
        report['wall_seconds']=time.monotonic()-start;dump(a.output/'result.json',report)


if __name__=='__main__':main()
