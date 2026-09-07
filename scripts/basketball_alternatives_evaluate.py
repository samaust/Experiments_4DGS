"""Measure reserved-frame reprojection without fitting cameras or geometry."""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import sqlite3
import time
import numpy as np
from basketball_audit import sha256
from basketball_alternatives_protocol import CAMERAS,TRAINING
from basketball_alternatives_colmap import dump
from basketball_alternatives_compare import load_export
from basketball_alternatives_localize import held_out_features
from basketball_alternatives_refine import deduplicate


def galleries(model, database):
    """Read-only SQLite access; exclude training points with <1° parallax."""
    eligible=set()
    for pid,point in model.points3D.items():
        if point.track.length()<3:continue
        C=np.array([model.image(el.image_id).projection_center() for el in point.track.elements])
        rays=point.xyz-C;length=np.linalg.norm(rays,axis=1)
        if np.any(length<=0):continue
        rays/=length[:,None]
        if np.min(rays@rays.T)<=np.cos(np.deg2rad(1.)):eligible.add(pid)
    out=[]
    with sqlite3.connect(database.resolve().as_uri()+'?mode=ro',uri=True) as db:
        for c in TRAINING:
            rows,cols,blob=db.execute('SELECT rows,cols,data FROM descriptors WHERE image_id=?',(c+1,)).fetchone()
            desc=np.frombuffer(blob,dtype=np.uint8).reshape(rows,cols)
            indices=[];pids=[]
            for index,p2 in enumerate(model.image(c+1).points2D):
                if p2.has_point3D() and p2.point3D_id in eligible:
                    indices.append(index);pids.append(p2.point3D_id)
            xy=np.array([model.image(c+1).points2D[i].xy for i in indices])
            out.append((c,desc[indices].astype(np.float32),pids,xy))
    return out


def correspondences(desc,xy,gallery,exclude_camera=None):
    import cv2
    votes=defaultdict(lambda:defaultdict(list));matcher=cv2.BFMatcher(cv2.NORM_L2)
    for c,descriptors,pids,other_xy in gallery:
        if c==exclude_camera or len(descriptors)<2:continue
        candidates=[]
        for pair in matcher.knnMatch(desc,descriptors,k=2):
            if len(pair)!=2:continue
            m,n=pair
            if m.distance<.8*n.distance:
                candidates.append(m)
        if len(candidates)<8:continue
        # Estimate only an image-pair correspondence filter. No tested K, pose,
        # 3D projection or reprojection residual enters this verification.
        first=np.array([xy[m.queryIdx] for m in candidates])
        second=np.array([other_xy[m.trainIdx] for m in candidates])
        cv2.setRNGSeed(0)
        _,inliers=cv2.findFundamentalMat(first,second,cv2.USAC_MAGSAC,1.,.999,10000)
        if inliers is None:continue
        for m,keep in zip(candidates,inliers.ravel()):
            if keep:votes[m.queryIdx][pids[m.trainIdx]].append(m.distance)
    choices=[(len(v),float(np.mean(v)),qi,pid) for qi,ps in votes.items() for pid,v in ps.items() if len(v)>=2]
    used_q=set();used_p=set();out=[]
    for _,_,qi,pid in sorted(choices,key=lambda x:(-x[0],x[1],x[2],x[3])):
        if qi not in used_q and pid not in used_p:
            out.append((qi,pid));used_q.add(qi);used_p.add(pid)
    return out


def temporal_anchor(model,gallery,camera,held_out,fit_inputs):
    """Training-window 2D observations, independent of tested projections."""
    if camera in TRAINING:
        _,desc,pids,xy=next(g for g in gallery if g[0]==camera)
        return desc,pids,xy
    from scipy.spatial import cKDTree
    report=json.loads((held_out/'result.json').read_text())
    if report['status']!='localized':raise ValueError('unverified held-out anchors')
    xy,desc=held_out_features(fit_inputs,camera,report['frames'])
    saved=np.load(held_out/f'camera{camera}-observations.npz')
    keep=saved['inliers'];points=saved['points3D'][keep];observed=saved['points2D'][keep]
    distance,index=cKDTree(xy).query(observed)
    if np.max(distance)>1e-6:raise ValueError('held-out anchor feature changed')
    by_xyz={tuple(p.xyz):pid for pid,p in model.points3D.items()}
    eligible={pid for _,_,ids,_ in gallery for pid in ids}
    ids=[by_xyz[tuple(p)] for p in points]
    chosen=[i for i,pid in enumerate(ids) if pid in eligible]
    return desc[index[chosen]],[ids[i] for i in chosen],observed[chosen]


def temporal_correspondences(desc,xy,anchor):
    """Static track continuation: appearance plus <=8px measured 2D motion."""
    import cv2
    descriptors,pids,previous=anchor
    if len(descriptors)<2 or len(desc)==0:return []
    matcher=cv2.BFMatcher(cv2.NORM_L2)
    choices=[]
    for pair in matcher.knnMatch(desc,descriptors,k=2):
        if len(pair)!=2:continue
        m,n=pair
        if m.distance<.8*n.distance and np.linalg.norm(xy[m.queryIdx]-previous[m.trainIdx])<=8.:
            choices.append((m.distance,m.queryIdx,pids[m.trainIdx]))
    out=[];used_q=set();used_p=set()
    for _,qi,pid in sorted(choices):
        if qi not in used_q and pid not in used_p:
            out.append((qi,pid));used_q.add(qi);used_p.add(pid)
    return out


def validate_frozen(frozen_path,calibration,prepared,hashes):
    frozen=json.loads(frozen_path.read_text())
    if frozen.get('status')!='frozen' or not frozen.get('selection_passed'):
        raise ValueError('winner has not passed selection')
    if frozen['calibration_sha256']!=sha256(calibration):raise ValueError('changed winner')
    if prepared['frozen_winner_sha256']!=sha256(frozen_path):
        raise ValueError('validation inputs were prepared for another winner')
    if frozen['frozen_artifact_sha256']!=hashes:raise ValueError('changed frozen map or anchors')
    if frozen['evaluation_adapter_sha256']!=sha256(__file__):raise ValueError('changed validation policy')


def consume_validation(frozen_path,output):
    # Single final evaluation, even if it fails; no metric fishing.
    with frozen_path.with_name('validation-consumed.json').open('x') as stream:
        json.dump(dict(frozen_winner_sha256=sha256(frozen_path),output=str(output)),stream)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--map',type=Path,required=True)
    p.add_argument('--features',type=Path,required=True)
    p.add_argument('--calibration',type=Path,required=True)
    p.add_argument('--inputs',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--role',choices=['selection','validation'],required=True)
    p.add_argument('--frozen-winner',type=Path)
    p.add_argument('--temporal-anchors',type=Path,help='verified fitting held-out localization directory')
    p.add_argument('--fit-inputs',type=Path)
    a=p.parse_args()
    import pycolmap as cm
    prepared=json.loads((a.inputs/'result.json').read_text())
    if prepared['status']!='prepared' or prepared['role']!=a.role:
        raise ValueError('wrong/unprepared reserved frame inputs')
    frames=prepared['source_frames']
    bounds=range(150,200) if a.role=='selection' else range(200,250)
    if any(f not in bounds for f in frames):raise ValueError('frame-role leakage')
    calibration=json.loads(a.calibration.read_text())
    load_export(a.calibration,expected=CAMERAS)
    by_camera={e['camera_id']:e for e in calibration['cameras']}
    if len(calibration['cameras'])!=34 or set(by_camera)!=set(CAMERAS):
        raise ValueError('requires a complete 34-camera export')
    for e in calibration['cameras']:
        camera=cm.Camera(model=e['camera_model'],params=e['parameters_colmap'],width=960,height=540)
        K=camera.calibration_matrix();K[:2,2]-=.5
        if not np.allclose(K,e['K'],atol=1e-8):raise ValueError('exported K/model parameters disagree')
    paths=list(a.map.glob('*.bin'))+[a.features/'features.db',a.calibration]
    if a.temporal_anchors:
        if a.fit_inputs is None:raise ValueError('temporal anchors require fitting inputs')
        fit=json.loads((a.fit_inputs/'result.json').read_text())
        fit_frames=fit.get('source_frames',sorted({e['source_frame_id'] for e in fit['observations']}))
        if fit.get('role','fit')!='fit' or not fit_frames or any(f not in range(50,150) for f in fit_frames):
            raise ValueError('temporal anchors must originate in fitting frames')
        paths+=list(a.temporal_anchors.glob('camera*-observations.npz'))+[a.temporal_anchors/'result.json']
    hashes={str(p):sha256(p) for p in paths}
    if a.role=='validation':
        if a.frozen_winner is None:raise ValueError('final validation requires frozen winner')
        validate_frozen(a.frozen_winner,a.calibration,prepared,hashes)
        consume_validation(a.frozen_winner,a.output)
    a.output.mkdir(parents=True,exist_ok=False)
    report=dict(role=a.role,frames=frames,status='running',cameras=[],frozen_artifact_sha256=hashes,
                adapter_sha256=sha256(__file__),input_sha256=sha256(a.inputs/'result.json'),
                correspondence_policy='descriptor ratio .8; independent image-pair fundamental USAC_MAGSAC 1px seed0; consensus from >=2 other training cameras; no calibration-reprojection-based rejection',
                independent_support='unique training point IDs across timestamps; repeated reprojections retained in error distribution')
    if a.temporal_anchors:
        report['correspondence_policy']='static temporal track continuation: descriptor ratio .8 and <=8px displacement from measured fitting 2D anchor; map tracks supported by >=2 other training cameras; no calibration-reprojection-based rejection'
    start=time.monotonic()
    try:
        model=cm.Reconstruction(a.map);gallery=galleries(model,a.features/'features.db')
        for c in CAMERAS:
            anchor=temporal_anchor(model,gallery,c,a.temporal_anchors,a.fit_inputs) if a.temporal_anchors else None
            e=by_camera[c]
            camera=cm.Camera(model=e['camera_model'],params=e['parameters_colmap'],width=960,height=540)
            pose=cm.Rigid3d(cm.Rotation3d(np.array(e['R'])),np.array(e['t']))
            all_errors=[];all_depth=[];unique=set();cells=set();observations=[];world=[]
            for f in frames:
                xy,desc=held_out_features(a.inputs,c,[f])
                matches=temporal_correspondences(desc,xy,anchor) if anchor is not None else correspondences(desc,xy,gallery,exclude_camera=c)
                if not matches:continue
                points2=np.array([xy[qi] for qi,pid in matches]);points3=np.array([model.point3D(pid).xyz for qi,pid in matches])
                camera_points=pose*points3
                projected=camera.img_from_cam(camera_points)
                errors=np.linalg.norm(projected-points2,axis=1)
                all_errors.extend(errors);all_depth.extend(camera_points[:,2]>0)
                unique.update(pid for qi,pid in matches);world.extend(points3)
                for (qi,pid),uv,error in zip(matches,points2,errors):
                    observations.append([f,pid,float(uv[0]),float(uv[1]),float(error)])
                    cell=np.floor(uv/[240.,135.]).astype(int)
                    if np.all((cell>=0)&(cell<4)):cells.add(tuple(cell))
            finite=bool(all_errors) and bool(np.isfinite(all_errors).all())
            spatially_unique=deduplicate([dict(xy=r[2:4]) for r in observations])
            independent=min(len(unique),len(spatially_unique))
            row=dict(camera_id=c,independent_static_points=independent,unique_map_points=len(unique),
                     reprojection_observations=len(all_errors),
                     occupied_grid_cells=len(cells),positive_depth_fraction=float(np.mean(all_depth)) if all_depth else 0.,
                     reprojection_median=float(np.median(all_errors)) if finite else None,
                     reprojection_p95=float(np.percentile(all_errors,95)) if finite else None)
            if len(world)>=3:
                points=np.array(world);d=np.linalg.norm(points-np.median(points,axis=0),axis=1)
                core=points[d<=np.percentile(d,95)]
                s=np.linalg.svd(core-core.mean(0),compute_uv=False)
                row['robust_nonplanarity_ratio']=float(s[-1]/s[0]) if s[0]>0 else 0.
            else:row['robust_nonplanarity_ratio']=0.
            row['passed']=bool(finite and independent>=100 and len(cells)>=6 and
                row['positive_depth_fraction']>=.95 and row['reprojection_median']<=1 and row['reprojection_p95']<=3 and
                row['robust_nonplanarity_ratio']>=.01 and camera.params[0]>0)
            report['cameras'].append(row)
            np.save(a.output/f'camera{c}-observations.npy',np.array(observations))
            print(c,row['reprojection_median'],row['reprojection_p95'],len(unique),row['passed'],flush=True)
        if any(sha256(path)!=digest for path,digest in hashes.items()):raise ValueError('frozen artifacts changed')
        report['status']='passed' if all(r['passed'] for r in report['cameras']) else 'failed-gates'
    except BaseException as error:
        report.update(status='failed',error=f'{type(error).__name__}: {error}');raise
    finally:
        report['wall_seconds']=time.monotonic()-start;dump(a.output/'result.json',report)


if __name__=='__main__':main()
