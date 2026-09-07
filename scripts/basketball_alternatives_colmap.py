"""Shared masked SuperPoint/LightGlue frontend; independent COLMAP mappers."""
import argparse
import itertools
import json
from pathlib import Path
import resource
import shutil
import time

import numpy as np
from basketball_audit import sha256
from basketball_alternatives_protocol import TRAINING, PROTOCOL, check_inputs


def dump(path, value):
    path.write_text(json.dumps(value, indent=2, allow_nan=False, default=str)+'\n')


def frontend(inputs, frame, output):
    import cv2
    import torch
    import pycolmap as cm
    from lightglue import SuperPoint, LightGlue
    from lightglue.utils import load_image
    check_inputs(TRAINING, [frame])
    prepared = json.loads((inputs/'result.json').read_text())
    if prepared['status'] != 'prepared':
        raise ValueError('mask preparation did not pass')
    observations = {e['camera_id']: e for e in prepared['observations'] if e['source_frame_id'] == frame}
    output.mkdir(parents=True, exist_ok=False)
    (output/'images').mkdir()
    report = dict(protocol=PROTOCOL, frame=frame, features={}, matches={}, status='running',
                  adapter_sha256=sha256(__file__), input_sha256=sha256(inputs/'result.json'),
                  configuration=dict(superpoint_max_keypoints=4096, lightglue='documented defaults',
                                     mask_clearance_pixels=8, camera_model='SIMPLE_PINHOLE',
                                     initial_focal=1152, prior_focal=False))
    start = time.monotonic()
    try:
        assert torch.cuda.is_available(), 'CUDA required'
        torch.manual_seed(0)
        torch.cuda.reset_peak_memory_stats()
        extractor = SuperPoint(max_num_keypoints=4096).eval().cuda()
        matcher = LightGlue(features='superpoint').eval().cuda()
        features = {}
        with cm.Database.open(output/'features.db') as db:
            for c in TRAINING:
                e = observations[c]
                image_path, mask_path = inputs/(e['stem']+'.png'), inputs/(e['stem']+'-static.png')
                if sha256(image_path) != e['image_sha256'] or sha256(mask_path) != e['mask_sha256']:
                    raise ValueError('changed prepared input')
                name = f'camera{c}.png'
                (output/'images'/name).symlink_to(image_path.resolve())
                mask = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
                distance = cv2.distanceTransform((mask>0).astype(np.uint8), cv2.DIST_L2, 5)
                with torch.inference_mode():
                    feat = extractor.extract(load_image(image_path).cuda(), resize=None)
                xy = feat['keypoints'][0].cpu().numpy()
                ij = np.clip(np.rint(xy).astype(int), [0,0], [959,539])
                keep = torch.from_numpy(distance[ij[:,1],ij[:,0]] >= 8).cuda()
                for key in ('keypoints','keypoint_scores','descriptors'):
                    feat[key] = feat[key][:,keep]
                features[c] = feat
                camera = cm.Camera(camera_id=c+1, model='SIMPLE_PINHOLE', width=960, height=540,
                                   params=[1152.,480.,270.])
                camera.has_prior_focal_length = False
                db.write_camera(camera, use_camera_id=True)
                sensor = cm.sensor_t(cm.SensorType.CAMERA,c+1)
                rig = cm.Rig(rig_id=c+1); rig.add_ref_sensor(sensor)
                db.write_rig(rig,use_rig_id=True)
                db.write_image(cm.Image(image_id=c+1,camera_id=c+1,name=name),use_image_id=True)
                f = cm.Frame(frame_id=c+1,rig_id=c+1); f.add_data_id(cm.data_t(sensor,c+1))
                db.write_frame(f,use_frame_id=True)
                db.write_keypoints(c+1,feat['keypoints'][0].cpu().numpy()+.5)
                report['features'][c] = int(keep.sum())
            for c,d in itertools.combinations(TRAINING,2):
                with torch.inference_mode():
                    matches = matcher(dict(image0=features[c],image1=features[d]))['matches'][0].cpu().numpy()
                db.write_matches(c+1,d+1,matches.astype(np.uint32))
                report['matches'][f'{c}-{d}'] = len(matches)
        (output/'pairs.txt').write_text(''.join(f'camera{c}.png camera{d}.png\n' for c,d in itertools.combinations(TRAINING,2)))
        cm.set_random_seed(0)
        cm.verify_matches(output/'features.db',output/'pairs.txt',cm.TwoViewGeometryOptions())
        report['database_sha256'] = sha256(output/'features.db')
        report['status'] = 'matched'
    except BaseException as error:
        report.update(status='failed',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        report.update(wall_seconds=time.monotonic()-start,
                      peak_host_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,
                      peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                      peak_reserved_bytes=torch.cuda.max_memory_reserved())
        dump(output/'result.json', report)


def export_model(model):
    entries = []
    for im in model.images.values():
        if not im.has_pose:
            continue
        c = int(Path(im.name).stem.removeprefix('camera'))
        if im.camera_id != c+1:
            raise ValueError('physical camera mapping changed')
        pose = im.cam_from_world()
        K = model.camera(im.camera_id).calibration_matrix()
        K[:2,2] -= .5
        entries.append(dict(camera_id=c, R=pose.rotation.matrix().tolist(),
                            t=pose.translation.tolist(), K=K.tolist(),
                            center=im.projection_center().tolist()))
    return sorted(entries,key=lambda e:e['camera_id'])


def mapping(source, method, output, seed=0):
    import pycolmap as cm
    before = json.loads((source/'result.json').read_text())
    if before['status'] != 'matched' or sha256(source/'features.db') != before['database_sha256']:
        raise ValueError('changed or incomplete frontend')
    output.mkdir(parents=True, exist_ok=False)
    shutil.copy2(source/'features.db',output/'mapping.db')
    report = dict(protocol=PROTOCOL, method=method, frame=before.get('frame'),
                  frames=before.get('frames',[before.get('frame')]),seed=seed,status='running',
                  models=[], source_database_sha256=before['database_sha256'],
                  adapter_sha256=sha256(__file__), frontend_wall_seconds=before['wall_seconds'])
    start = time.monotonic()
    try:
        cm.set_random_seed(seed)
        if method == 'global':
            report['view_graph_calibrated'] = cm.calibrate_view_graph(output/'mapping.db')
            options = cm.GlobalPipelineOptions(num_threads=8, random_seed=seed)
            options.mapper.bundle_adjustment.print_summary = True
            models = cm.global_mapping(output/'mapping.db',source/'images',output/'sparse',options)
        else:
            options = cm.IncrementalPipelineOptions(num_threads=8,random_seed=seed)
            models = cm.incremental_mapping(output/'mapping.db',source/'images',output/'sparse',options)
        report['options'] = options.todict()
        for index, model in models.items():
            entries = export_model(model)
            complete = [e['camera_id'] for e in entries] == list(TRAINING)
            prediction = dict(schema='basketball-native-calibration/v1', protocol=PROTOCOL,
                              pixel_convention='opencv-integer-centers', pose_convention='world-to-camera',
                              image_size=[960,540], cameras=entries, complete=complete)
            dump(output/f'calibration-{index}.json',prediction)
            # Reload native export and compare K and poses before accepting conversion.
            reloaded = cm.Reconstruction(output/'sparse'/str(index))
            if export_model(reloaded) != entries:
                raise ValueError('native model reload differs')
            report['models'].append(dict(model_id=index, complete=complete,
                cameras=[e['camera_id'] for e in entries], points=model.num_points3D(),
                mean_reprojection_error=model.compute_mean_reprojection_error()))
        complete = [m for m in report['models'] if m['complete']]
        report['status'] = 'complete' if len(complete)==1 else 'incomplete'
        if len(complete)==1:
            report['model_id'] = complete[0]['model_id']
    except BaseException as error:
        report.update(status='failed',error=f'{type(error).__name__}: {error}')
        raise
    finally:
        report.update(wall_seconds=time.monotonic()-start,
                      peak_host_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        dump(output/'result.json',report)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('stage',choices=['frontend','global','incremental'])
    p.add_argument('--source',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--frame',type=int)
    p.add_argument('--seed',type=int,default=0)
    a = p.parse_args()
    if a.stage=='frontend':
        frontend(a.source,a.frame,a.output)
    else:
        mapping(a.source,a.stage,a.output,a.seed)


if __name__=='__main__':
    main()
