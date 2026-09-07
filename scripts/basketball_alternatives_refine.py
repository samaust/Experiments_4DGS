"""Common fixed-rig static-window feature pooling and robust bundle adjustment."""
import argparse
import json
from pathlib import Path
import resource
import shutil
import time
import numpy as np
from basketball_audit import sha256
from basketball_alternatives_protocol import TRAINING, PROTOCOL, EARLY, LATE, check_inputs
from basketball_alternatives_colmap import dump, export_model
from basketball_alternatives_compare import load_export


def deduplicate(candidates, radius=2.):
    """Greedy spatial NMS across timestamps, including neighboring bin borders."""
    grid={};out=[]
    for item in candidates:
        xy=np.asarray(item['xy']);cell=tuple(np.floor(xy/radius).astype(int))
        neighbors=[p for dx in (-1,0,1) for dy in (-1,0,1)
                   for p in grid.get((cell[0]+dx,cell[1]+dy),[])]
        if any(np.linalg.norm(xy-p)<radius for p in neighbors):
            continue
        grid.setdefault(cell,[]).append(xy);out.append(item)
    return out


def frontend(inputs, frames, output, sharp):
    import cv2
    import pycolmap as cm
    from basketball_static_rig import register_image
    from basketball_focus import sharpness_maps
    check_inputs(TRAINING,frames)
    if tuple(frames) not in (EARLY,LATE):
        raise ValueError('only the declared independent five-frame windows')
    prepared=json.loads((inputs/'result.json').read_text())
    if prepared['status']!='prepared':
        raise ValueError('requires prepared static inputs')
    entries={(e['camera_id'],e['source_frame_id']):e for e in prepared['observations']}
    output.mkdir(parents=True,exist_ok=False);(output/'images').mkdir()
    report=dict(protocol=PROTOCOL,frames=frames,sharp=sharp,status='running',features={},
                adapter_sha256=sha256(__file__),input_sha256=sha256(inputs/'result.json'),
                dedup_radius_pixels=2.,sharpness_percentile=20 if sharp else None)
    start=time.monotonic()
    try:
        sift=cv2.SIFT_create(nfeatures=8192)
        with cm.Database.open(output/'features.db') as db:
            for c in TRAINING:
                candidates=[];descriptors=[]
                for f in frames:
                    e=entries[c,f];image=inputs/(e['stem']+'.png');mask=inputs/(e['stem']+'-static.png')
                    if sha256(image)!=e['image_sha256'] or sha256(mask)!=e['mask_sha256']:
                        raise ValueError('changed fitting inputs')
                    gray=cv2.imread(str(image),cv2.IMREAD_GRAYSCALE)
                    m=cv2.imread(str(mask),cv2.IMREAD_GRAYSCALE)
                    distance=cv2.distanceTransform((m>0).astype(np.uint8),cv2.DIST_L2,5)
                    keys,desc=sift.detectAndCompute(gray,m)
                    score,variance=sharpness_maps(gray)
                    if desc is None:
                        continue
                    for k,d in zip(keys,desc):
                        x,y=np.rint(k.pt).astype(int)
                        if distance[y,x]<max(8.,3*k.size):
                            continue
                        if sharp and variance[y,x]<1e-4:
                            continue
                        candidates.append(dict(frame=f,xy=k.pt,size=k.size,angle=k.angle,
                                               score=float(score[y,x]) if sharp else float(k.response),
                                               index=len(descriptors)))
                        descriptors.append(d)
                if not candidates:
                    raise ValueError(f'no static features for {c}')
                if sharp:
                    threshold=np.percentile([e['score'] for e in candidates],20)
                    candidates=[e for e in candidates if e['score']>=threshold]
                selected=deduplicate(sorted(candidates,key=lambda e:(-e['score'],e['frame'],e['index'])))
                name=f'camera{c}.png'
                (output/'images'/name).symlink_to((inputs/(entries[c,frames[0]]['stem']+'.png')).resolve())
                K=np.array([[1152.,0,480],[0,1152.,270],[0,0,1]])
                register_image(db,cm,camera_id=c+1,image_id=c+1,name=name,K=K)
                camera=db.read_camera(c+1);camera.has_prior_focal_length=False;db.update_camera(camera)
                keys=np.array([[*e['xy'],e['size']/2,np.deg2rad(e['angle'])] for e in selected],dtype=np.float32)
                keys[:,:2]+=.5
                db.write_keypoints(c+1,keys)
                d=np.array([descriptors[e['index']] for e in selected],dtype=np.uint8)
                db.write_descriptors(c+1,cm.FeatureDescriptors(cm.FeatureExtractorType.SIFT,d))
                dump(output/f'camera{c}-observations.json',selected)
                report['features'][c]=len(selected)
        cm.set_random_seed(0)
        cm.match_exhaustive(output/'features.db',matching_options=cm.FeatureMatchingOptions(num_threads=8,use_gpu=False),device=cm.Device.cpu)
        report.update(status='matched',database_sha256=sha256(output/'features.db'))
    except BaseException as error:
        report.update(status='failed',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        report.update(wall_seconds=time.monotonic()-start,peak_host_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        dump(output/'result.json',report)


def support(model):
    rows=[]
    for c in TRAINING:
        im=model.image(c+1);camera=model.camera(c+1);pose=im.cam_from_world()
        errors=[];positive=[];cells=set();independent=set();partners=set()
        for p2 in im.points2D:
            if not p2.has_point3D():
                continue
            point=model.point3D(p2.point3D_id)
            others={el.image_id-1 for el in point.track.elements if el.image_id!=c+1}
            if len(others)<2:
                continue
            xyz=pose*point.xyz
            positive.append(xyz[2]>0)
            projected=camera.img_from_cam(xyz)
            if projected is None:
                continue
            errors.append(float(np.linalg.norm(projected-p2.xy)))
            independent.add(p2.point3D_id);partners.update(others)
            cell=np.floor(p2.xy/[240.,135.]).astype(int)
            if np.all((cell>=0)&(cell<4)):
                cells.add(tuple(cell))
        rows.append(dict(camera_id=c,independent_static_points=len(independent),other_cameras=len(partners),
                         occupied_grid_cells=len(cells),positive_depth_fraction=float(np.mean(positive)) if positive else 0.,
                         reprojection_median=float(np.median(errors)) if errors else None,
                         reprojection_p95=float(np.percentile(errors,95)) if errors else None))
    return rows


def refine(source, native, output, policy, seed):
    import pycolmap as cm
    report_source=json.loads((source/'result.json').read_text())
    if report_source['status']!='matched' or sha256(source/'features.db')!=report_source['database_sha256']:
        raise ValueError('invalid pooled observations')
    load_export(native)
    values=json.loads(native.read_text())
    output.mkdir(parents=True,exist_ok=False)
    # PyCOLMAP triangulation updates database cameras. Keep pooled evidence immutable.
    shutil.copy2(source/'features.db',output/'triangulation.db')
    report=dict(protocol=PROTOCOL,policy=policy,seed=seed,frames=report_source['frames'],
                sharp=report_source['sharp'],status='running',native_sha256=sha256(native),
                source_database_sha256=report_source['database_sha256'],adapter_sha256=sha256(__file__))
    start=time.monotonic()
    try:
        model=cm.Reconstruction()
        for e in values['cameras']:
            c=e['camera_id'];K=np.array(e['K']);K[:2,2]+=.5
            if policy=='fixed':
                name='PINHOLE';params=[K[0,0],K[1,1],K[0,2],K[1,2]]
            else:
                name='SIMPLE_RADIAL' if policy=='radial' else 'SIMPLE_PINHOLE'
                params=[float((K[0,0]+K[1,1])/2),480.,270.]+([0.] if policy=='radial' else [])
            camera=cm.Camera(camera_id=c+1,model=name,width=960,height=540,params=params)
            model.add_camera(camera)
            rig=cm.Rig(rig_id=c+1);rig.add_ref_sensor(cm.sensor_t(cm.SensorType.CAMERA,c+1));model.add_rig(rig)
            pose=cm.Rigid3d(cm.Rotation3d(np.array(e['R'])),np.array(e['t']))
            model.add_image_with_trivial_frame(cm.Image(image_id=c+1,camera_id=c+1,name=f'camera{c}.png'),pose)
        initial={c:cam.params.copy() for c,cam in model.cameras.items()}
        cm.set_random_seed(seed)
        options=cm.IncrementalPipelineOptions(num_threads=8,random_seed=seed,extract_colors=False,
            ba_refine_focal_length=False,ba_refine_principal_point=False,ba_refine_extra_params=False)
        model=cm.triangulate_points(model,output/'triangulation.db',source/'images',output/'triangulated',
                                    options=options,refine_intrinsics=False)
        ba=cm.BundleAdjustmentOptions(refine_focal_length=policy!='fixed',refine_principal_point=False,
                                       refine_extra_params=policy=='radial',print_summary=True)
        ba.ceres.loss_function_type=cm.LossFunctionType.SOFT_L1
        ba.ceres.loss_function_scale=1.
        ba.ceres.solver_options.num_threads=8
        ba.ceres.solver_options.max_num_iterations=200
        cm.bundle_adjustment(model,ba)
        if policy=='fixed' and any(not np.array_equal(initial[c],cam.params) for c,cam in model.cameras.items()):
            raise ValueError('fixed intrinsics changed')
        for c,cam in model.cameras.items():
            if policy!='fixed' and not np.array_equal(cam.params[1:3],[480.,270.]):
                raise ValueError('principal point changed')
        (output/'sparse').mkdir();model.write(output/'sparse')
        entries=export_model(model)
        value=dict(schema='basketball-native-calibration/v1',protocol=PROTOCOL,complete=True,
                   pixel_convention='opencv-integer-centers',pose_convention='world-to-camera',
                   image_size=[960,540],cameras=entries)
        # Distortion is explicit; the common JSON K does not silently undistort observations.
        for e in value['cameras']:
            cam=model.camera(e['camera_id']+1)
            e.update(camera_model=cam.model_name,parameters_colmap=cam.params.tolist())
        dump(output/'calibration-0.json',value)
        load_export(output/'calibration-0.json')
        original_support=support(model);reloaded=cm.Reconstruction(output/'sparse')
        reloaded_support=support(reloaded)
        reprojection_delta=max((abs(a[k]-b[k]) for a,b in zip(original_support,reloaded_support)
            for k in ('reprojection_median','reprojection_p95') if a[k] is not None and b[k] is not None),default=0.)
        if reprojection_delta>1e-8 or export_model(model)!=export_model(reloaded):
            raise ValueError('reloaded reprojection or pose differs')
        if sha256(source/'features.db')!=report_source['database_sha256']:
            raise ValueError('pooled source database changed')
        report.update(status='complete',model_id=0,per_camera_support=reloaded_support,
                      points=model.num_points3D(),options=ba.todict(),reload_reprojection_max_delta=reprojection_delta)
    except BaseException as error:
        report.update(status='failed',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        report.update(wall_seconds=time.monotonic()-start,peak_host_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        dump(output/'result.json',report)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['frontend','refine'])
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--frames',nargs='+',type=int)
    p.add_argument('--sharp',action='store_true')
    p.add_argument('--native',type=Path)
    p.add_argument('--policy',choices=['fixed','focal','radial'])
    p.add_argument('--seed',type=int,default=0)
    a=p.parse_args()
    if a.stage=='frontend':frontend(a.source,a.frames,a.output,a.sharp)
    else:refine(a.source,a.native,a.output,a.policy,a.seed)


if __name__=='__main__':main()
