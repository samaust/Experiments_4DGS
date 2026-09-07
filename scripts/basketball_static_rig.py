"""Training-only masked SIFT reconstruction with one pose per physical camera.

Merge static feature observations across fitting timestamps into one virtual
image per physical camera. This is calibration geometry, never initialization.
"""
import argparse
import json
from pathlib import Path
import time
import numpy as np
from basketball_audit import sha256
from basketball_geometry import opencv_to_colmap, training_prior_entries, connected_components
from basketball_protocol import TRAINING, HELD_OUT, EXCLUDED, PROTOCOL


def register_image(db, colmap, *, camera_id, image_id, name, K, model_name='PINHOLE'):
    if not db.exists_camera(camera_id):
        params = ([K[0,0], K[1,1], K[0,2], K[1,2]] if model_name=='PINHOLE'
                  else [float((K[0,0]+K[1,1])/2), K[0,2], K[1,2], 0., 0.])
        camera = colmap.Camera(camera_id=camera_id, model=model_name, width=960, height=540,params=params)
        camera.has_prior_focal_length = True
        db.write_camera(camera, use_camera_id=True)
        rig = colmap.Rig(rig_id=camera_id)
        rig.add_ref_sensor(colmap.sensor_t(colmap.SensorType.CAMERA, camera_id))
        db.write_rig(rig, use_rig_id=True)
    db.write_image(colmap.Image(image_id=image_id, camera_id=camera_id, name=name), use_image_id=True)
    frame = colmap.Frame(frame_id=image_id, rig_id=camera_id)
    frame.add_data_id(colmap.data_t(colmap.sensor_t(colmap.SensorType.CAMERA, camera_id), image_id))
    db.write_frame(frame, use_frame_id=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--priors', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--fit-frames', nargs='+', type=int, default=[50,75,100,125,149])
    p.add_argument('--camera-model', choices=['PINHOLE','RADIAL'], default='PINHOLE')
    a = p.parse_args()
    if not a.fit_frames or len(set(a.fit_frames)) != len(a.fit_frames) or any(f not in [50,75,100,125,149] for f in a.fit_frames):
        p.error('independent windows must use unique recorded fitting timestamps')
    import cv2
    import pycolmap as colmap
    if colmap.__version__ != '4.2.0':
        raise ValueError('requires pinned PyCOLMAP 4.2.0')
    priors = json.loads((a.priors/'result.json').read_text())
    selected = [e for e in training_prior_entries(priors) if e['source_frame_id'] in a.fit_frames]
    a.output.mkdir(exist_ok=False)
    images = a.output/'images'; images.mkdir()
    masks = a.output/'masks'; masks.mkdir()
    merged_images = a.output/'merged-images'; merged_images.mkdir()
    raw_db = a.output/'per-frame.db'
    merged_db = a.output/'merged.db'
    config = dict(schema='basketball-static-rig/v1', protocol=PROTOCOL,
                  cameras=list(TRAINING), excluded_cameras=list(EXCLUDED), held_out_excluded=list(HELD_OUT),
                  fit_frames=a.fit_frames, seed=0, matcher='masked-SIFT', max_features_per_image=8192,
                  feature_static_support_radius='max(8 pixels, 6 * SIFT scale)',
                  deduplication_pixels=2, min_verified_pair_inliers=30,
                  pose_policy='one virtual image/pose and one intrinsic per physical camera',
                  camera_model=a.camera_model, max_mapping_seconds=600,
                  priors_sha256=sha256(a.priors/'result.json'), adapter_sha256=sha256(__file__))
    (a.output/'config.json').write_text(json.dumps(config,indent=2)+'\n')
    report = dict(schema='basketball-static-rig-result/v1', status='blocked', blockers=[],
                  config_sha256=sha256(a.output/'config.json'), protocol=PROTOCOL,
                  inputs=[], features={}, verified_edges=[], models=[])
    started=time.monotonic()
    try:
        Ks={c:opencv_to_colmap(np.median([e['K_960x540'] for e in selected if e['camera_id']==c],axis=0)) for c in TRAINING}
        with colmap.Database.open(raw_db) as db:
            for index,e in enumerate(selected,1):
                name=e['stem']+'.png'
                source=a.priors/name
                mask=a.priors/(e['stem']+'-static.png')
                (images/name).symlink_to(source.resolve())
                (masks/(name+'.png')).symlink_to(mask.resolve())
                register_image(db,colmap,camera_id=e['camera_id']+1,image_id=index,name=name,K=Ks[e['camera_id']],model_name=a.camera_model)
                report['inputs'].append(dict(image_id=index, **e, image_sha256=sha256(source),mask_sha256=sha256(mask)))
        colmap.set_random_seed(0)
        colmap.extract_features(raw_db,images,
            reader_options=colmap.ImageReaderOptions(camera_model=a.camera_model,mask_path=masks),
            extraction_options=colmap.FeatureExtractionOptions(num_threads=8,use_gpu=False),device=colmap.Device.cpu)
        with colmap.Database.open(raw_db) as raw, colmap.Database.open(merged_db) as merged:
            for c in TRAINING:
                all_keys=[]; all_desc=[]; provenance=[]; occupied=set(); dtype=None
                for e in report['inputs']:
                    if e['camera_id']!=c: continue
                    keypoints=raw.read_keypoints(e['image_id'])
                    descriptors=raw.read_descriptors(e['image_id'])
                    dtype=descriptors.type
                    mask=cv2.imread(str(a.priors/(e['stem']+'-static.png')),cv2.IMREAD_GRAYSCALE)
                    distance=cv2.distanceTransform((mask>0).astype(np.uint8),cv2.DIST_L2,5)
                    for index,key in enumerate(keypoints):
                        # COLMAP keypoints have half-integer pixel centers.
                        x,y=np.floor(key[:2]).astype(int)
                        if not (0<=x<960 and 0<=y<540): continue
                        if distance[y,x]<max(8.,6.*float(key[2])): continue
                        cell=tuple(np.floor(key[:2]/2).astype(int))
                        if cell in occupied: continue
                        occupied.add(cell)
                        all_keys.append(key);all_desc.append(descriptors.data[index]);provenance.append([e['source_frame_id'],index])
                if not all_keys: raise ValueError(f'camera {c}: no static SIFT features')
                image_id=c+1
                name=f'camera{c}.png'
                (merged_images/name).symlink_to((a.priors/f'camera{c}-frame100.png').resolve())
                register_image(merged,colmap,camera_id=image_id,image_id=image_id,name=name,K=Ks[c],model_name=a.camera_model)
                merged.write_keypoints(image_id,np.asarray(all_keys,dtype=np.float32))
                merged.write_descriptors(image_id,colmap.FeatureDescriptors(dtype,np.asarray(all_desc,dtype=np.uint8)))
                np.save(a.output/f'camera{c}-feature-sources.npy',np.array(provenance,dtype=np.int32))
                report['features'][str(c)]=len(all_keys)
        colmap.match_exhaustive(merged_db,matching_options=colmap.FeatureMatchingOptions(num_threads=8,use_gpu=False),device=colmap.Device.cpu)
        with colmap.Database.open(merged_db) as db:
            for i,c in enumerate(TRAINING):
                for other in TRAINING[i+1:]:
                    if not db.exists_two_view_geometry(c+1,other+1): continue
                    geom=db.read_two_view_geometry(c+1,other+1)
                    if len(geom.inlier_matches)>=30:
                        report['verified_edges'].append(dict(cameras=[c,other],inliers=len(geom.inlier_matches),configuration=str(geom.config)))
        report['components']=connected_components(TRAINING,[e['cameras'] for e in report['verified_edges']])
        options=colmap.IncrementalPipelineOptions(num_threads=8,random_seed=0,min_model_size=3,
                  max_num_models=3,ba_refine_focal_length=True,ba_refine_principal_point=False,
                  ba_refine_extra_params=(a.camera_model=='RADIAL'),max_runtime_seconds=600,extract_colors=False)
        models=colmap.incremental_mapping(merged_db,merged_images,a.output/'sparse',options=options)
        for model_id,model in models.items():
            ba=colmap.BundleAdjustmentOptions(refine_focal_length=True,refine_principal_point=True,refine_extra_params=(a.camera_model=='RADIAL'))
            ba.ceres.loss_function_type=colmap.LossFunctionType.SOFT_L1
            ba.ceres.loss_function_scale=1.0
            ba.ceres.solver_options.num_threads=8
            ba.ceres.solver_options.max_solver_time_in_seconds=120
            colmap.bundle_adjustment(model,options=ba)
            model.write(a.output/'sparse'/str(model_id))
            registered=sorted(image.camera_id-1 for image in model.images.values() if image.has_pose)
            report['models'].append(dict(model_id=model_id,cameras=registered,points=model.num_points3D(),
                                        mean_reprojection_error=model.compute_mean_reprojection_error()))
        complete=[m for m in report['models'] if m['cameras']==list(TRAINING)]
        if len(report['components'])!=1 or len(complete)!=1:
            report['blockers'].append('SIFT did not recover one connected complete training rig; bounded dense fallback permitted')
        else:
            report['model_id']=complete[0]['model_id']
            report['status']='candidate-rig'
    except BaseException as error:
        report['blockers'].append(f'{type(error).__name__}: {error}')
        raise
    finally:
        report['wall_seconds']=time.monotonic()-started
        (a.output/'result.json').write_text(json.dumps(report,indent=2)+'\n')
    return bool(report['blockers'])


if __name__=='__main__':
    raise SystemExit(main())
