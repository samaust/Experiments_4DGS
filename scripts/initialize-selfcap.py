#!/usr/bin/env python3
"""Triangulate a training-only SelfCap frame using fixed calibration.

CPU COLMAP preprocessing, separate from model training time. No supplied point
cloud or held-out image enters the reconstruction database.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time


def select_training_frames(manifest, frame_id):
    if not 4120 <= frame_id < 4180:
        raise ValueError('frame must be in the matched SelfCap window [4120, 4180)')
    if manifest.get('schema') != 'selfcap-processed/v1' or manifest.get('status') != 'prepared':
        raise ValueError('requires completed SelfCap processed manifest')
    cameras = [c for c in manifest['cameras'] if c['split'] == 'train']
    if (len(cameras) != 23 or len({c['id'] for c in cameras}) != 23
            or any(c['id'] == '0015' for c in cameras)):
        raise ValueError('invalid training split')
    selected = []
    for camera in cameras:
        frames = [f for f in camera['frames'] if f['frame_id'] == frame_id]
        if len(frames) != 1:
            raise ValueError('selected training frame missing or duplicated')
        selected.append((camera, frames[0]))
    return selected


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--frame-id', type=int, default=4150,
                   help='Source frame in [4120,4180); default retains midpoint initialization')
    a = p.parse_args()
    import numpy as np
    import pycolmap as colmap
    from scipy.spatial.transform import Rotation
    m = json.loads(a.manifest.read_text())
    try:
        selected = select_training_frames(m, a.frame_id)
    except ValueError as error:
        p.error(str(error))
    cameras = [camera for camera, _ in selected]
    if a.output.exists():
        p.error('choose a new output directory')
    a.output.mkdir(parents=True)
    images = a.output/'images'
    images.mkdir()
    sparse = a.output/'input-model'
    sparse.mkdir()
    database_path = a.output/'features.db'
    camera_lines, image_lines, inputs = [], [], []
    started = time.monotonic()
    with colmap.Database.open(database_path) as db:
        for index, (camera, frame) in enumerate(selected, 1):
            source = (a.manifest.parent / frame['path']).resolve()
            if not source.is_relative_to(a.manifest.parent.resolve()):
                raise ValueError('source path escapes processed scene')
            with source.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != frame['sha256']:
                    raise ValueError('source hash mismatch')
            name = camera['id']+'.png'
            (images/name).symlink_to(source)
            K = np.asarray(camera['K'])
            params = [K[0,0], K[1,1], K[0,2], K[1,2]]
            model_camera = colmap.Camera(camera_id=index, model='PINHOLE',
                                         width=camera['width'], height=camera['height'], params=params)
            db.write_camera(model_camera, use_camera_id=True)
            db.write_image(colmap.Image(image_id=index, camera_id=index, name=name), use_image_id=True)
            camera_lines.append(f'{index} PINHOLE {camera["width"]} {camera["height"]} '+
                                ' '.join(map(str, params)))
            quaternion = Rotation.from_matrix(camera['world_to_camera_R']).as_quat()
            pose = [quaternion[3], *quaternion[:3], *camera['world_to_camera_T']]
            image_lines.append(f'{index} '+ ' '.join(map(str, pose)) + f' {index} {name}\n')
            inputs.append(dict(camera_id=camera['id'], image_name=name, **frame))
    (sparse/'cameras.txt').write_text('\n'.join(camera_lines)+'\n')
    (sparse/'images.txt').write_text('\n'.join(image_lines)+'\n')
    (sparse/'points3D.txt').write_text('')
    provenance = dict(manifest=str(a.manifest.resolve()),
                      manifest_sha256=hashlib.sha256(a.manifest.read_bytes()).hexdigest(),
                      inputs=inputs, held_out_excluded=['0015'], pycolmap=colmap.__version__,
                      device='CPU', source_frame=a.frame_id, seed=0,
                      note='Single-frame initialization only; moving matches may be rejected due to fractional camera offsets.')
    (a.output/'inputs.json').write_text(json.dumps(provenance, indent=2)+'\n')
    colmap.set_random_seed(0)
    colmap.extract_features(database_path, images,
        extraction_options=colmap.FeatureExtractionOptions(num_threads=8, use_gpu=False),
        device=colmap.Device.cpu)
    colmap.match_exhaustive(database_path,
        matching_options=colmap.FeatureMatchingOptions(num_threads=8, use_gpu=False),
        device=colmap.Device.cpu)
    reconstruction = colmap.Reconstruction(sparse)
    options = colmap.IncrementalPipelineOptions(num_threads=8, random_seed=0,
        fix_existing_frames=True, ba_refine_focal_length=False,
        ba_refine_principal_point=False, ba_refine_extra_params=False,
        ba_refine_sensor_from_rig=False)
    result = colmap.triangulate_points(reconstruction, database_path, images,
                                       a.output/'triangulated', options=options, refine_intrinsics=False)
    if result.num_points3D() == 0:
        raise RuntimeError('no training-only points triangulated')
    for index, camera in enumerate(cameras, 1):
        actual = result.image(index).cam_from_world()
        assert np.allclose(actual.rotation.matrix(), camera['world_to_camera_R'], atol=1e-6)
        assert np.allclose(actual.translation, camera['world_to_camera_T'], atol=1e-6)
    result.export_PLY(a.output/'initialization.ply')
    errors = [p.error for p in result.points3D.values()]
    report = dict(provenance, points=result.num_points3D(), images=result.num_reg_images(),
                  mean_reprojection_error_pixels=float(np.mean(errors)),
                  wall_seconds=time.monotonic()-started, status='triangulated')
    (a.output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: report[k] for k in ['points','images','mean_reprojection_error_pixels','wall_seconds']}, indent=2))


if __name__ == '__main__':
    main()
