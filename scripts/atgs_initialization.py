"""Training-only midpoint geometry adapted to ATGS initial-anchor semantics."""
import hashlib
import json
from pathlib import Path


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_initialization(directory, scene):
    directory = Path(directory)
    result = json.loads((directory / 'result.json').read_text())
    if result.get('status') != 'triangulated' or result.get('manifest_sha256') != scene.sha256:
        raise ValueError('initialization manifest/status mismatch')
    inputs = result.get('inputs', [])
    expected = set(scene.training_keys(4150))
    actual = [(item['camera_id'], item['frame_id']) for item in inputs]
    if set(actual) != expected or len(actual) != len(expected):
        raise ValueError('initialization training split mismatch')
    for item, key in zip(inputs, actual):
        if item['sha256'] != scene.frames[key]['sha256']:
            raise ValueError('initialization input image digest mismatch')
    return dict(ply_sha256=digest(directory / 'initialization.ply'),
                evidence_sha256=digest(directory / 'result.json'))


def load_initial_cloud(directory, scene, cloud_type):
    import numpy as np
    from plyfile import PlyData
    validate_initialization(directory, scene)
    vertices = PlyData.read(str(Path(directory) / 'initialization.ply'))['vertex']
    xyz = np.column_stack([vertices[name] for name in ('x', 'y', 'z')]).astype(np.float32)
    colors = np.column_stack([vertices[name] for name in ('red', 'green', 'blue')]).astype(np.float32) / 255
    if len(xyz) < 2 or not np.isfinite(xyz).all() or not np.isfinite(colors).all():
        raise ValueError('invalid initialization points')
    # Native ATGS treats frame-zero initial anchors as present for all times.
    # This is a lifetime convention, not a claim of frame-zero reconstruction.
    lifetimes = np.zeros((len(xyz), 60), dtype=bool)
    lifetimes[:, 0] = True
    cloud = cloud_type(xyz, colors, np.zeros_like(xyz), None, lifetimes, None)
    centers = np.array([c['center'] for c in scene.cameras.values() if c['split'] == 'train'])
    extent = float(np.linalg.norm(centers - centers.mean(0), axis=1).max() * 1.1)
    if not np.isfinite(extent) or extent <= 0:
        raise ValueError('invalid training camera extent')
    return cloud, extent
