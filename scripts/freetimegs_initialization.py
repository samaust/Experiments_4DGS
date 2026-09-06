"""Training-only sparse temporal initialization using the reproduction's KNN helper."""
import ast
import hashlib
import json
from pathlib import Path

import numpy as np
from scipy.spatial import cKDTree


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_velocity_helper(checkout):
    path = Path(checkout) / 'src/combine_frames_fast_keyframes.py'
    functions = [n for n in ast.parse(path.read_text()).body
                 if isinstance(n, ast.FunctionDef) and n.name == 'compute_velocity_knn']
    if len(functions) != 1:
        raise ValueError('native velocity helper missing or duplicated')
    selected = ast.Module(body=functions, type_ignores=[])
    namespace = dict(np=np, cKDTree=cKDTree)
    exec(compile(selected, str(path), 'exec'), namespace)
    return namespace['compute_velocity_knn'], hashlib.sha256(ast.dump(selected).encode()).hexdigest()


def load_cloud(directory, scene, frame_id):
    from plyfile import PlyData
    directory = Path(directory)
    evidence = json.loads((directory / 'result.json').read_text())
    if (evidence.get('status') != 'triangulated' or evidence.get('manifest_sha256') != scene.sha256
            or evidence.get('source_frame') != frame_id):
        raise ValueError('cloud manifest, frame or status mismatch')
    inputs = evidence.get('inputs', [])
    keys = [(item['camera_id'], item['frame_id']) for item in inputs]
    expected = set(scene.training_keys(frame_id))
    if len(keys) != 23 or set(keys) != expected:
        raise ValueError('cloud training split mismatch')
    for item, key in zip(inputs, keys):
        if item['sha256'] != scene.frames[key]['sha256']:
            raise ValueError('cloud image digest mismatch')
    vertices = PlyData.read(str(directory / 'initialization.ply'))['vertex']
    points = np.column_stack([vertices[n] for n in ('x', 'y', 'z')]).astype(np.float32)
    colors = np.column_stack([vertices[n] for n in ('red', 'green', 'blue')]).astype(np.float32) / 255
    if (len(points) < 4 or not np.isfinite(points).all() or not np.isfinite(colors).all()
            or (colors < 0).any() or (colors > 1).any()):
        raise ValueError('invalid sparse cloud')
    times = [scene.frames[key]['normalized_time'] for key in keys]
    return points, colors, dict(frame_id=frame_id, directory=str(directory.absolute()),
        ply_sha256=digest(directory / 'initialization.ply'),
        evidence_sha256=digest(directory / 'result.json'), points=len(points),
        normalized_time=float(np.mean(times)),
        input_time_range=[min(times), max(times)])


def assemble_initialization(checkout, scene, clouds):
    """Use every fifth frame and its successor; never infer a missing next cloud."""
    keyframes = list(range(4120, 4180, 5))
    required = {frame for key in keyframes for frame in (key, key + 1)}
    if set(clouds) != required:
        raise ValueError('requires exactly all keyframe and next-frame clouds')
    velocity, helper_digest = load_velocity_helper(checkout)
    loaded = {frame: load_cloud(clouds[frame], scene, frame) for frame in sorted(required)}
    arrays = {name: [] for name in ('positions', 'colors', 'velocities', 'times', 'durations', 'has_velocity')}
    dt = 1. / (scene.manifest['source_fps'] * scene.manifest['time']['duration_seconds'])
    if not np.isfinite(dt) or dt <= 0:
        raise ValueError('invalid normalized frame interval')
    for frame in keyframes:
        points, colors, evidence = loaded[frame]
        successor, _, next_evidence = loaded[frame + 1]
        if not np.isclose(next_evidence['normalized_time'] - evidence['normalized_time'], dt):
            raise ValueError('inconsistent corrected frame interval')
        displacement, valid = velocity(points, successor, max_distance=.5, k=1, n_workers=8)
        values = dict(positions=points, colors=colors, velocities=displacement / dt,
                      times=np.full((len(points), 1), evidence['normalized_time'], dtype=np.float32),
                      durations=np.full((len(points), 1), 3 * 5 * dt, dtype=np.float32),
                      has_velocity=valid)
        for name, value in values.items():
            arrays[name].append(value)
    arrays = {name: np.concatenate(values) for name, values in arrays.items()}
    report = dict(schema='freetimegs-sparse-initialization/v1', manifest_sha256=scene.sha256,
                  helper_ast_sha256=helper_digest, keyframe_step=5, duration_gap_multiplier=3,
                  max_match_distance=.5, normalized_frame_interval=dt,
                  points=len(arrays['positions']), valid_velocity_points=int(arrays['has_velocity'].sum()),
                  clouds=[loaded[f][2] for f in sorted(required)],
                  limitations=['Sparse COLMAP geometry, not dense ROMA initialization.',
                               'KNN displacements are estimates, not tracked correspondences.',
                               'Cloud time is mean corrected training-camera time; fractional offsets remain.'])
    return arrays, report
