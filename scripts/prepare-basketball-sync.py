"""Prepare the fixed reconstruction window; never decode final timing images."""
import argparse
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from basketball_scene import render_calibration
from sync_timing import SCHEMA, CONVENTION, common_training_keys, normalized_timestamp


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def zero_timing(freeze_hash):
    ids = [str(i) for i in range(34)]
    return dict(schema=SCHEMA, convention=CONVENTION, camera_ids=ids,
                reference_camera='1', units='seconds', kind='operational-assumption',
                offset_seconds={c:0. for c in ids}, uncertainty_seconds={c:None for c in ids},
                coverage={'camera_ids':ids}, source_support_seconds={c:[0.,10.] for c in ids},
                source_window_seconds=[0.,2.], normalization={'origin_seconds':0.,'duration_seconds':2.},
                provenance={'freeze_sha256':freeze_hash,'method':'zero-offset control; no physical synchronization claim'})


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--freeze', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    freeze = json.loads(a.freeze.read_text())
    calibration_path = root/freeze['calibration_path']
    if digest(calibration_path) != freeze['calibration_sha256']:
        raise ValueError('frozen calibration changed')
    calibration = json.loads(calibration_path.read_text())
    timing = zero_timing(digest(a.freeze))
    heldout = ['0','10','20','30']
    cameras = []
    a.output.mkdir(parents=True, exist_ok=False)
    for entry, source in zip(calibration['cameras'], freeze['sources']):
        c = str(entry['camera_id'])
        if source['camera_id'] != entry['camera_id']:
            raise ValueError('source/calibration camera ordering mismatch')
        path = root/source['path']
        if digest(path) != source['sha256']:
            raise ValueError('source video changed')
        camera, K, distortion = render_calibration(entry, freeze['scale'])
        camera.update(id=c, split='test' if c in heldout else 'train', frames=[])
        maps = cv2.initUndistortRectifyMap(K, np.array(distortion), None, K, (960,540), cv2.CV_32FC1)
        directory = a.output/'rgb'/c
        directory.mkdir(parents=True)
        capture = cv2.VideoCapture(str(path))
        previous_hash = None
        duplicates = []
        for f in range(50):
            ok, image = capture.read()
            if not ok or image.shape[:2] != (1080,1920):
                raise ValueError(f'invalid native source {c}/{f}')
            native_hash = hashlib.sha256(image.tobytes()).hexdigest()
            if native_hash == previous_hash:
                duplicates.append(f)
            previous_hash = native_hash
            resized = cv2.resize(image, (960,540), interpolation=cv2.INTER_AREA)
            image = cv2.remap(resized, *maps, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
            out = directory/f'{f:06d}.png'
            if not cv2.imwrite(str(out), image):
                raise RuntimeError('failed image write')
            camera['frames'].append(dict(frame_id=f, source_timestamp_seconds=f/25,
                normalized_time=normalized_timestamp(timing,c,f/25),
                path=str(out.relative_to(a.output)), sha256=digest(out)))
        capture.release()
        camera['exact_duplicate_previous_frames_0_49'] = duplicates
        cameras.append(camera)
        print(json.dumps(dict(camera_id=c, prepared_frames=50, exact_duplicates=len(duplicates))),flush=True)
    keys, excluded = common_training_keys([(c['id'],f['frame_id'],f['source_timestamp_seconds'])
                                          for c in cameras for f in c['frames']], [timing], heldout)
    manifest = dict(schema='basketball-processed/v1', status='prepared', cameras=cameras,
                    source_fps=25, heldout_camera_ids=heldout, temporal_holdout_seconds=[.8,1.],
                    timing=timing, comparison_timings=[timing], time=timing['normalization'],
                    training_keys=keys, training_exclusions=excluded,
                    freeze_sha256=digest(a.freeze), script_sha256=digest(__file__),
                    image_policy='area resize 1920x1080 to 960x540; radial undistortion preserving OpenCV K; black borders',
                    pixel_convention='COLMAP continuous: top-left pixel center 0.5',
                    initialization_frame=25)
    (a.output/'manifest.json').write_text(json.dumps(manifest,indent=2,allow_nan=False)+'\n')


if __name__ == '__main__':
    main()
