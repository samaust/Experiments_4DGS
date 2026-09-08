"""Continuous-time Basketball cameras with immutable source and training exclusions."""
import hashlib
import json
from pathlib import Path

import numpy as np

from stg_scene import SelfCapScene
from sync_timing import common_training_keys, normalized_timestamp, validate_timing


def render_calibration(entry, scale):
    """Keep OpenCV K while undistorting, then add half a pixel for rendering."""
    K = np.array(entry['K'], dtype=np.float64)
    if entry['camera_model'] != 'SIMPLE_RADIAL' or K.shape != (3, 3):
        raise ValueError('requires frozen radial Basketball calibration')
    f, cx, cy, k = entry['parameters_colmap']
    if not np.allclose(K, [[f,0,cx-.5],[0,f,cy-.5],[0,0,1]]) or not np.isfinite(scale) or scale <= 0:
        raise ValueError('calibration convention or scale mismatch')
    renderer_K = K.copy()
    renderer_K[:2, 2] += .5
    return dict(K=renderer_K.tolist(), width=960, height=540,
                world_to_camera_R=entry['R'],
                world_to_camera_T=(np.array(entry['t'])*scale).tolist(),
                center=(np.array(entry['center'])*scale).tolist()), K, [k,0.,0.,0.]


class BasketballScene(SelfCapScene):
    def __init__(self, path):
        self.path = Path(path).resolve()
        raw = self.path.read_bytes()
        self.sha256 = hashlib.sha256(raw).hexdigest()
        self.manifest = m = json.loads(raw)
        if m.get('schema') != 'basketball-processed/v1' or m.get('status') != 'prepared':
            raise ValueError('requires completed Basketball scene')
        ids = [str(i) for i in range(34)]
        heldout = ['0','10','20','30']
        if m.get('source_fps') != 25 or m.get('heldout_camera_ids') != heldout:
            raise ValueError('Basketball cadence or split changed')
        if [c['id'] for c in m['cameras']] != ids:
            raise ValueError('Basketball requires original ordered 34-camera rig')
        timing = validate_timing(m['timing'])
        if timing['camera_ids'] != ids or timing['reference_camera'] != '1':
            raise ValueError('timing rig or gauge mismatch')
        if timing['normalization'] != m['time']:
            raise ValueError('shared time normalization mismatch')
        if m.get('temporal_holdout_seconds') != [0.8,1.0]:
            raise ValueError('temporal holdout changed')
        conditions = m['comparison_timings']
        if timing not in conditions:
            raise ValueError('current timing absent from paired exclusion conditions')
        self.cameras = {c['id']:c for c in m['cameras']}
        self.frames = {}
        for c in m['cameras']:
            if c['split'] != ('test' if c['id'] in heldout else 'train'):
                raise ValueError('camera split mismatch')
            if [f['frame_id'] for f in c['frames']] != list(range(50)):
                raise ValueError('reconstruction must use only source frames 0–49')
            for f in c['frames']:
                expected = normalized_timestamp(timing, c['id'], f['frame_id']/25)
                if abs(f['normalized_time']-expected) > 1e-10:
                    raise ValueError('timestamp conversion mismatch')
                self.frames[c['id'], f['frame_id']] = f
        frames = [(c,f,f/25) for c,f in self.frames]
        keys, excluded = common_training_keys(frames, conditions, heldout)
        if m['training_keys'] != [list(k) for k in keys] or m['training_exclusions'] != excluded:
            raise ValueError('union camera/time exclusions mismatch')
        self._training_keys = keys

    def training_keys(self, frame_id=None):
        return [k for k in self._training_keys if frame_id is None or k[1] == frame_id]

    def training_camera(self, key, *, device, load_image=True, full=False):
        if key not in self._training_keys:
            raise ValueError('camera/time holdout cannot be used for training')
        return self.camera(key, device=device, load_image=load_image, full=full)


class FreeTimeBasketballScene(BasketballScene):
    def camera(self, key, *, device, load_image=False):
        from freetimegs_scene import gsplat_camera
        return gsplat_camera(super().camera(key, device=device, load_image=load_image),
                             self.cameras[key[0]])

    def training_camera(self, key, *, device, load_image=True):
        if key not in self._training_keys:
            raise ValueError('camera/time holdout cannot be used for training')
        return self.camera(key, device=device, load_image=load_image)
