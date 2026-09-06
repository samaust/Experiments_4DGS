"""Native coordinate normalization and duration loading for the shared profile."""
import ast
import hashlib
import json
from pathlib import Path

import numpy as np
import torch

from freetimegs_initialization import digest, load_cloud
from freetimegs_scene import FreeTimeSelfCapScene


def load_normalization(checkout):
    path = Path(checkout) / 'datasets/normalize.py'
    names = {'similarity_from_cameras', 'align_principle_axes', 'transform_points', 'transform_cameras'}
    functions = [node for node in ast.parse(path.read_text()).body
                 if isinstance(node, ast.FunctionDef) and node.name in names]
    if len(functions) != 4 or {node.name for node in functions} != names:
        raise ValueError('native normalization helpers missing or duplicated')
    module = ast.Module(body=functions, type_ignores=[])
    namespace = {'np': np}
    exec(compile(module, str(path), 'exec'), namespace)
    return {name: namespace[name] for name in names}, dict(source_sha256=digest(path),
        normalization_ast_sha256=hashlib.sha256(ast.dump(module).encode()).hexdigest())


def normalize_camera(camera, transform, helper):
    converted = helper(transform, camera.camtoworlds.detach().cpu().numpy())
    camera.camtoworlds = torch.as_tensor(converted, device=camera.Ks.device, dtype=camera.Ks.dtype)
    camera.viewmats = torch.linalg.inv(camera.camtoworlds)
    return camera


class NormalizedFreeTimeScene(FreeTimeSelfCapScene):
    def __init__(self, manifest, transform, transform_cameras):
        super().__init__(manifest)
        self.transform = np.asarray(transform, dtype=np.float32)
        self.transform_cameras = transform_cameras

    def camera(self, key, *, device, load_image=False):
        return normalize_camera(super().camera(key, device=device, load_image=load_image),
                                self.transform, self.transform_cameras)

    def sweep_camera(self, index, *, device):
        return normalize_camera(super().sweep_camera(index, device=device),
                                self.transform, self.transform_cameras)


def prepare_training_inputs(checkout, scene, directory, reference_cloud):
    directory = Path(directory)
    report = json.loads((directory / 'result.json').read_text())
    archive = directory / 'initialization.npz'
    if (report.get('status') != 'prepared' or report.get('schema') != 'freetimegs-edgs-initialization/v1'
            or report.get('manifest_sha256') != scene.sha256 or report.get('archive_sha256') != digest(archive)):
        raise ValueError('dense temporal initialization provenance mismatch')
    with np.load(archive, allow_pickle=False) as values:
        data = {key: values[key].copy() for key in ('positions', 'colors', 'velocities', 'times', 'durations')}
    for name, value in data.items():
        width = 1 if name in ('times', 'durations') else 3
        if (value.shape != (report['points'], width) or value.dtype != np.float32
                or not np.isfinite(value).all()):
            raise ValueError(f'invalid initialization array: {name}')
    if ((data['colors'] < 0).any() or (data['colors'] > 1).any() or
            (data['times'] < 0).any() or (data['times'] >= 1).any() or (data['durations'] <= 0).any()):
        raise ValueError('invalid initialization colors/times/durations')
    helpers, source = load_normalization(checkout)
    points, _, reference = load_cloud(reference_cloud, scene, 4150)
    keys = sorted(scene.training_keys(4150))
    cameras = np.concatenate([scene.camera(key, device='cpu').camtoworlds.numpy() for key in keys])
    T1 = helpers['similarity_from_cameras'](cameras)
    T2 = helpers['align_principle_axes'](helpers['transform_points'](T1, points))
    transform = T2 @ T1
    cameras = helpers['transform_cameras'](transform, cameras)
    centers = cameras[:, :3, 3]
    scene_scale = float(np.linalg.norm(centers-centers.mean(0), axis=1).max()) * 1.1
    data['positions'] = helpers['transform_points'](transform, data['positions'])
    data['velocities'] = data['velocities'] @ transform[:3, :3].T
    # Native keyframe loader replaces combiner durations. Use corrected-profile
    # time units rather than re-normalizing the manifest to nominal frame count.
    dt = 1/(scene.manifest['source_fps'] * scene.manifest['time']['duration_seconds'])
    if report['keyframe_step'] != 5 or not np.isclose(report['normalized_frame_interval'], dt):
        raise ValueError('initialization keyframe/time mapping mismatch')
    duration = 2 * report['keyframe_step'] * dt
    data['durations'] = np.full_like(data['durations'], duration)
    valid = np.linalg.norm(data['positions'], axis=1) < 5 * scene_scale
    if int(valid.sum()) < 4:
        raise ValueError('insufficient points after native distance filtering')
    data = {key: torch.from_numpy(value[valid].copy()) for key, value in data.items()}
    evidence = dict(transform=transform.tolist(), scene_scale=scene_scale, source=source,
        reference_cloud=reference, initialization_sha256=digest(archive),
        initialization_report_sha256=digest(directory / 'result.json'),
        points_before=report['points'], points_after=int(valid.sum()),
        resolved_duration=duration, normalized_frame_interval=dt,
        adaptations=['native normalization fitted to training cameras and audited training-only midpoint SfM',
                     'preserve corrected manifest times and normalized-time velocities',
                     'native two-gap duration override expressed in corrected manifest time units'])
    normalized = NormalizedFreeTimeScene(scene.path, transform, helpers['transform_cameras'])
    return normalized, data, evidence
