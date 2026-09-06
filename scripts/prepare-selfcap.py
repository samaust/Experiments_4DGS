#!/usr/bin/env python3
"""Prepare calibrated SelfCap dance1 PNGs with COLMAP undistortion.

Run in stg-colmap. Output must be new. Source frame IDs are unchanged;
fractional synchronization offsets are retained in timestamp metadata.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--videos', type=Path, required=True)
    parser.add_argument('--calibration', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--calibration-only', action='store_true')
    args = parser.parse_args()
    import cv2
    import numpy as np
    import pycolmap
    from scipy.spatial.transform import Rotation, Slerp

    started = time.monotonic()
    if args.output.exists():
        parser.error('choose a new output directory')
    offsets = json.loads((args.calibration / 'sync.json').read_text())
    intri = cv2.FileStorage(str(args.calibration / 'intri.yml'), cv2.FILE_STORAGE_READ)
    extri = cv2.FileStorage(str(args.calibration / 'extri.yml'), cv2.FILE_STORAGE_READ)
    names = intri.getNode('names')
    ids = [names.at(i).string() for i in range(names.size())]
    if set(ids) != set(offsets) or '0015' not in ids or len(ids) != 24:
        raise ValueError('unexpected camera/synchronization membership')
    if not all(np.isfinite(value) for value in offsets.values()):
        raise ValueError('nonfinite synchronization offset')
    start, end, fps = 4120, 4180, 60
    # The common domain contains every corrected sample, including early views.
    origin = start / fps - max(offsets.values())
    duration = (end - start) / fps + max(offsets.values()) - min(offsets.values())
    options = pycolmap.UndistortCameraOptions(blank_pixels=0)
    cameras = []
    for camera_id in ids:
        K = intri.getNode('K_' + camera_id).mat()
        D = intri.getNode('D_' + camera_id).mat().ravel()
        R = extri.getNode('Rot_' + camera_id).mat()
        T = extri.getNode('T_' + camera_id).mat().ravel()
        width = int(intri.getNode('W_' + camera_id).real())
        height = int(intri.getNode('H_' + camera_id).real())
        if not np.allclose(R.T @ R, np.eye(3), atol=1e-6) or not np.isclose(np.linalg.det(R), 1):
            raise ValueError('invalid rotation: ' + camera_id)
        if len(D) != 5 or D[4] != 0:
            raise ValueError('nonzero k3 requires a different COLMAP camera model')
        camera = pycolmap.Camera(model='OPENCV', width=width, height=height,
                                 params=[K[0, 0], K[1, 1], K[0, 2], K[1, 2], *D[:4]])
        undistorted = pycolmap.undistort_camera(options, camera)
        out_width, out_height = round(undistorted.width * 0.5), round(undistorted.height * 0.5)
        processed_K = undistorted.calibration_matrix()
        processed_K[0] *= out_width / undistorted.width
        processed_K[1] *= out_height / undistorted.height
        video = args.videos / (camera_id + '.mp4')
        capture = cv2.VideoCapture(str(video))
        if not capture.isOpened():
            raise ValueError('cannot open ' + str(video))
        if (int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))) != (width, height):
            raise ValueError('video/calibration dimensions differ')
        if not np.isclose(capture.get(cv2.CAP_PROP_FPS), fps) or capture.get(cv2.CAP_PROP_FRAME_COUNT) < end:
            raise ValueError('unexpected FPS or insufficient frames')
        frames = []
        if not args.calibration_only:
            folder = args.output / 'images' / camera_id
            folder.mkdir(parents=True)
            capture.set(cv2.CAP_PROP_POS_FRAMES, start)
            if int(capture.get(cv2.CAP_PROP_POS_FRAMES)) != start:
                raise ValueError('video seek did not reach selected start frame')
            for frame_id in range(start, end):
                ok, bgr = capture.read()
                if not ok:
                    raise ValueError(f'failed decoding {camera_id}/{frame_id}')
                bitmap = pycolmap.Bitmap.from_array(cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB))
                rgb, target_camera = pycolmap.undistort_image(options, bitmap, camera)
                pixels = cv2.resize(rgb.to_array(), (out_width, out_height), interpolation=cv2.INTER_AREA)
                path = folder / f'{frame_id:06d}.png'
                if not cv2.imwrite(str(path), cv2.cvtColor(pixels, cv2.COLOR_RGB2BGR)):
                    raise OSError('failed writing ' + str(path))
                timestamp = frame_id / fps - offsets[camera_id]
                frames.append(dict(frame_id=frame_id, timestamp_seconds=timestamp,
                                   normalized_time=(timestamp-origin)/duration,
                                   path=path.relative_to(args.output).as_posix(), sha256=digest(path)))
        capture.release()
        cameras.append(dict(id=camera_id, split='test' if camera_id == '0015' else 'train',
                            source_video=str(video.resolve()), source_video_sha256=digest(video),
                            source_K=K.tolist(), distortion=D.tolist(),
                            world_to_camera_R=R.tolist(), world_to_camera_T=T.tolist(),
                            center=(-R.T @ T).tolist(), K=processed_K.tolist(),
                            width=out_width, height=out_height, frames=frames,
                            synchronization_offset_seconds=offsets[camera_id]))
        print(camera_id, out_width, out_height, len(frames), flush=True)
    intri.release()
    extri.release()
    heldout = next(c for c in cameras if c['split'] == 'test')
    nearest = min((c for c in cameras if c['split'] == 'train'),
                  key=lambda c: np.linalg.norm(np.array(c['center']) - heldout['center']))
    rotations = Rotation.from_matrix([np.array(c['world_to_camera_R']).T for c in (heldout, nearest)])
    path = []
    for fraction, rotation in zip(np.linspace(0, 1, 20), Slerp([0, 1], rotations)(np.linspace(0, 1, 20)).as_matrix()):
        center = (1-fraction)*np.array(heldout['center']) + fraction*np.array(nearest['center'])
        path.append(dict(world_to_camera_R=rotation.T.tolist(),
                         world_to_camera_T=(-rotation.T @ center).tolist()))
    report = dict(schema='selfcap-processed/v1', status='calibration-only' if args.calibration_only else 'prepared',
                  frames=[start, end], source_fps=fps, cameras=cameras,
                  calibration={p.name: digest(p) for p in (args.calibration / n for n in ['intri.yml', 'extri.yml', 'sync.json'])},
                  time=dict(origin_seconds=origin, duration_seconds=duration,
                            formula='(frame_id / fps - camera_offset_seconds - origin_seconds) / duration_seconds'),
                  undistortion=dict(implementation='pycolmap', version=pycolmap.__version__, blank_pixels=0,
                                    resize='OpenCV INTER_AREA 0.5; rounded output dimensions'),
                  sweep=dict(start_camera='0015', end_camera=nearest['id'], poses=path,
                             intrinsics_camera='0015', frame_id=4150,
                             normalized_time=(4150/fps-offsets['0015']-origin)/duration),
                  initialization='not generated; supplied point clouds excluded pending held-out leakage audit',
                  wall_seconds=time.monotonic()-started)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / 'manifest.json').write_text(json.dumps(report, indent=2, allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
