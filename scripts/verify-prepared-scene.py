#!/usr/bin/env python3
"""Validate SelfCap prepared geometry, timing, splits, PNG dimensions and hashes."""
import argparse
import hashlib
import json
from pathlib import Path


def verify(path):
    import numpy as np
    from PIL import Image
    manifest = json.loads(path.read_text())
    if manifest.get('schema') != 'selfcap-processed/v1' or manifest.get('status') != 'prepared':
        raise ValueError('expected a completed SelfCap preprocessing manifest')
    cameras = manifest['cameras']
    ids = [c['id'] for c in cameras]
    assert len(ids) == len(set(ids)) == 24
    assert [c['id'] for c in cameras if c['split'] == 'test'] == ['0015']
    assert sum(c['split'] == 'train' for c in cameras) == 23
    start, end = manifest['frames']
    assert [start, end] == [4120, 4180]
    count = 0
    for camera in cameras:
        R, T, center = (np.asarray(camera[k]) for k in ['world_to_camera_R', 'world_to_camera_T', 'center'])
        assert np.allclose(R.T @ R, np.eye(3), atol=1e-6)
        assert np.isclose(np.linalg.det(R), 1)
        assert np.allclose(R @ center + T, 0, atol=1e-6)
        K = np.asarray(camera['K'])
        assert np.isfinite(K).all() and K[0, 0] > 0 and K[1, 1] > 0
        assert np.allclose(K[2], [0, 0, 1])
        assert [f['frame_id'] for f in camera['frames']] == list(range(start, end))
        for frame in camera['frames']:
            timestamp = frame['frame_id']/manifest['source_fps'] - camera['synchronization_offset_seconds']
            assert np.isclose(frame['timestamp_seconds'], timestamp, rtol=0, atol=1e-10)
            expected = (timestamp-manifest['time']['origin_seconds'])/manifest['time']['duration_seconds']
            assert abs(frame['normalized_time'] - expected) < 1e-10
            assert 0 <= expected < 1
            image_path = (path.parent / frame['path']).resolve()
            assert image_path.is_relative_to(path.parent.resolve())
            with Image.open(image_path) as image:
                assert image.size == (camera['width'], camera['height'])
                assert image.mode == 'RGB'
            with image_path.open('rb') as stream:
                assert hashlib.file_digest(stream, 'sha256').hexdigest() == frame['sha256']
            count += 1
    sweep = manifest['sweep']
    assert len(sweep['poses']) == 20
    test = next(c for c in cameras if c['id'] == sweep['start_camera'])
    nearest = min((c for c in cameras if c['split'] == 'train'),
                  key=lambda c: np.linalg.norm(np.asarray(c['center']) - test['center']))
    assert sweep['end_camera'] == nearest['id']
    for pose, target in [(sweep['poses'][0], test), (sweep['poses'][-1], nearest)]:
        for key in ['world_to_camera_R', 'world_to_camera_T']:
            assert np.allclose(pose[key], target[key], atol=1e-6)
    for pose in sweep['poses']:
        R = np.asarray(pose['world_to_camera_R'])
        assert np.allclose(R.T @ R, np.eye(3), atol=1e-6) and np.isclose(np.linalg.det(R), 1)
    return dict(images=count, held_out_images=end-start, training_images=count-(end-start),
                sweep_poses=20, nearest_training_camera=nearest['id'], status='passed')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('manifest', type=Path)
    a = p.parse_args()
    print(json.dumps(verify(a.manifest), indent=2))
