"""Manifest-native STG cameras; load only requested images onto the GPU.

Calibration uses COLMAP continuous coordinates (top-left pixel center 0.5).
The native rasterizer converts NDC to zero-based pixel indices, so projected
indices equal COLMAP coordinates minus 0.5. No calibration recentering occurs.
"""
import hashlib
import json
import math
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image
import torch


def make_camera(calibration, timestamp, *, device, full=False, name='', uid=0):
    K = np.asarray(calibration['K'], dtype=np.float64)
    R = np.asarray(calibration['world_to_camera_R'], dtype=np.float64)
    T = np.asarray(calibration['world_to_camera_T'], dtype=np.float64)
    width, height = calibration['width'], calibration['height']
    if width <= 0 or height <= 0 or not 0 <= timestamp < 1:
        raise ValueError('invalid dimensions or normalized timestamp')
    if (K.shape != (3, 3) or not np.isfinite(K).all() or
            K[0, 0] <= 0 or K[1, 1] <= 0 or
            not np.allclose(K[2], [0, 0, 1]) or K[0, 1] != 0 or K[1, 0] != 0):
        raise ValueError('expected finite skew-free pinhole intrinsics')
    if (R.shape != (3, 3) or T.shape != (3,) or not np.isfinite(T).all() or
            not np.allclose(R.T @ R, np.eye(3), atol=1e-6) or
            not np.isclose(np.linalg.det(R), 1)):
        raise ValueError('invalid world-to-camera pose')
    world_view = np.eye(4)
    world_view[:3, :3], world_view[:3, 3] = R, T
    near, far = .01, 100.
    projection = np.zeros((4, 4))
    projection[0, 0], projection[1, 1] = 2*K[0, 0]/width, 2*K[1, 1]/height
    projection[0, 2], projection[1, 2] = 2*K[0, 2]/width-1, 2*K[1, 2]/height-1
    projection[2, 2] = (far+near)/(far-near)
    projection[2, 3], projection[3, 2] = -far*near/(far-near), 1
    view = SimpleNamespace(
        R=R.T, T=T, uid=uid, colmap_id=uid, image_name=name,
        timestamp=float(timestamp), image_width=width, image_height=height,
        FoVx=2*math.atan(width/(2*K[0, 0])), FoVy=2*math.atan(height/(2*K[1, 1])),
        znear=near, zfar=far, original_image=None,
        world_view_transform=torch.tensor(world_view.T, dtype=torch.float32, device=device),
        projection_matrix=torch.tensor(projection.T, dtype=torch.float32, device=device),
        camera_center=torch.tensor(-R.T@T, dtype=torch.float32, device=device),
        rays=None, rayo=None, rayd=None)
    view.full_proj_transform = view.world_view_transform @ view.projection_matrix
    if full:
        y, x = torch.meshgrid(torch.arange(height, device=device, dtype=torch.float32),
                              torch.arange(width, device=device, dtype=torch.float32), indexing='ij')
        directions = torch.stack(((x+.5-K[0, 2])/K[0, 0],
                                  (y+.5-K[1, 2])/K[1, 1], torch.ones_like(x)), -1)
        directions = directions @ torch.tensor(R, dtype=torch.float32, device=device)
        view.rayd = torch.nn.functional.normalize(directions, dim=-1).permute(2, 0, 1)[None]
        view.rayo = view.camera_center[:, None, None].expand(3, height, width)[None]
        view.rays = torch.cat((view.rayo, view.rayd), dim=1)
    return view


class SelfCapScene:
    def __init__(self, path):
        self.path = Path(path).resolve()
        data = self.path.read_bytes()
        self.sha256 = hashlib.sha256(data).hexdigest()
        self.manifest = json.loads(data)
        m = self.manifest
        if m.get('schema') != 'selfcap-processed/v1' or m.get('status') != 'prepared':
            raise ValueError('requires a completed SelfCap manifest')
        cameras = m['cameras']
        if (len(cameras) != 24 or len({c['id'] for c in cameras}) != 24 or
                [c['id'] for c in cameras if c['split'] == 'test'] != ['0015'] or
                sum(c['split'] == 'train' for c in cameras) != 23):
            raise ValueError('invalid SelfCap camera split')
        self.cameras = {c['id']: c for c in cameras}
        self.frames = {}
        for c in cameras:
            if [f['frame_id'] for f in c['frames']] != list(range(4120, 4180)):
                raise ValueError('invalid SelfCap frame selection')
            for f in c['frames']:
                seconds = f['frame_id']/m['source_fps'] - c['synchronization_offset_seconds']
                expected = (seconds-m['time']['origin_seconds'])/m['time']['duration_seconds']
                if not 0 <= expected < 1 or abs(f['normalized_time']-expected) > 1e-10:
                    raise ValueError('inconsistent corrected timestamp')
                self.frames[c['id'], f['frame_id']] = f

    def training_keys(self, frame_id=None):
        # Batch by source frame, never by floating-point timestamp equality.
        # Each selected camera still renders at its own corrected timestamp.
        return [key for key in self.frames if self.cameras[key[0]]['split'] == 'train'
                and (frame_id is None or key[1] == frame_id)]

    def camera(self, key, *, device, full=False, load_image=False):
        c, f = self.cameras[key[0]], self.frames[key]
        view = make_camera(c, f['normalized_time'], device=device, full=full,
                           name=f'{key[0]}/{key[1]:06d}', uid=int(key[0]))
        if load_image:
            path = (self.path.parent/f['path']).resolve()
            if not path.is_relative_to(self.path.parent):
                raise ValueError('image path escapes processed scene')
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != f['sha256']:
                    raise ValueError('processed image hash mismatch')
            with Image.open(path) as image:
                if image.mode != 'RGB' or image.size != (c['width'], c['height']):
                    raise ValueError('processed image format mismatch')
                pixels = np.array(image, copy=True)
            view.original_image = torch.from_numpy(pixels).permute(2, 0, 1).to(device).float()/255
        return view

    def sweep_camera(self, index, *, device, full=False):
        sweep = self.manifest['sweep']
        c = dict(self.cameras[sweep['start_camera']], **sweep['poses'][index])
        return make_camera(c, sweep['normalized_time'], device=device, full=full,
                           name=f'sweep/{index:02d}', uid=index)
