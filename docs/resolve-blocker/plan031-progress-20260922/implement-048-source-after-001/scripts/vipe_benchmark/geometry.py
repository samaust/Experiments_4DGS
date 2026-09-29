"""Diagnostic camera/scene transformations and reused geometry interfaces."""
import numpy as np

from .contracts import renderer_K


def scale_scene(points, cameras, normalization, source_scale, target_scale):
    if not np.isfinite([source_scale, target_scale]).all() or min(source_scale, target_scale) <= 0:
        raise ValueError('invalid scene scale')
    factor = target_scale / source_scale
    scaled = np.asarray(points, np.float64) * factor
    transformed = {}
    for c, camera in cameras.items():
        transformed[c] = dict(camera, t=(np.asarray(camera['t']) * factor).tolist(),
                              center=(np.asarray(camera['center']) * factor).tolist())
    transform = np.array(normalization, np.float64, copy=True)
    if transform.shape != (4, 4):
        raise ValueError('normalization must be homogeneous 4x4')
    transform[:, :3] /= factor
    before = np.asarray(points) @ np.asarray(normalization)[:3, :3].T + np.asarray(normalization)[:3, 3]
    after = scaled @ transform[:3, :3].T + transform[:3, 3]
    if not np.allclose(before, after, atol=1e-10, rtol=1e-12):
        raise ValueError('physical-to-normalized coordinate relationship changed')
    return scaled, transformed, transform, dict(factor=factor,
        world_distance_units='metres at target scale; physical accuracy remains unverified',
        normalized_time_seconds=2., frame_seconds=.04,
        velocity='metres/second -> normalization linear map * 2 seconds')


def consumer_camera(camera):
    return dict(K=renderer_K(camera['K']).tolist(), world_to_camera_R=camera['R'],
                world_to_camera_T=camera['t'], center=camera['center'])


def coarse_samples(confidence, labels, semantics, count, rng):
    # Importing the source module does not call its production CLI, training
    # membership guards, model loader or paths.
    from basketball_temporal_cloud import balanced_samples
    phrases = {str(i): r['class'] for i, r in semantics.items()}
    confidence = np.array(confidence, copy=True).reshape(-1)
    confidence[np.asarray(labels).ravel() < 0] = 0
    selected = balanced_samples(confidence, np.asarray(labels).ravel(), phrases, count, rng)
    return selected, dict(requested=count, obtained=len(selected), shortage=count - len(selected))


def crop_warp(model, warp, confidence, image0, image1, labels0, labels1, semantics0, semantics1):
    from basketball_temporal_cloud import person_crop_warp
    from .contracts import instances
    for labels, semantics in [(labels0, semantics0), (labels1, semantics1)]:
        instances(labels, semantics, labels >= 0)
    return person_crop_warp(model, warp, confidence, image0, image1, labels0, labels1,
                            {i: r['class'] for i, r in semantics0.items()},
                            {i: r['class'] for i, r in semantics1.items()})
