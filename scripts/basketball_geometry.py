"""Explicit conventions and diagnostics for estimated Basketball calibration."""
import numpy as np
from basketball_protocol import CAMERAS, TRAINING, FIT_FRAMES


def opencv_to_colmap(K):
    """OpenCV integer pixel centers -> COLMAP half-integer pixel centers."""
    result = np.array(K, dtype=float, copy=True)
    result[:2, 2] += .5
    return result


def resize_opencv(K, source_size, target_size):
    """Pixel-center preserving resize, including unequal x/y scale factors."""
    result = opencv_to_colmap(K)
    result[0] *= target_size[0] / source_size[0]
    result[1] *= target_size[1] / source_size[1]
    result[:2, 2] -= .5
    return result


def invert_pose(R, t):
    R, t = np.asarray(R), np.asarray(t)
    return R.T, -R.T @ t


def training_prior_entries(result):
    if result['status'] != 'priors-generated' or result['blockers']:
        raise ValueError('requires completed all-camera priors')
    entries = result['observations']
    frames = result.get('source_frames', FIT_FRAMES)
    if not frames or len(set(frames)) != len(frames) or any(f < 50 or f >= 150 for f in frames):
        raise ValueError('invalid recorded fitting timestamps')
    keys = {(e['camera_id'], e['source_frame_id']) for e in entries}
    expected = {(c, f) for c in CAMERAS for f in frames}
    if keys != expected or len(entries) != len(expected):
        raise ValueError('missing or duplicate prior observations')
    return [e for e in entries if e['camera_id'] in TRAINING]


def connected_components(nodes, edges):
    neighbors = {n: set() for n in nodes}
    for a, b in edges:
        if a not in neighbors or b not in neighbors:
            raise ValueError('edge references unknown camera')
        neighbors[a].add(b)
        neighbors[b].add(a)
    components = []
    unseen = set(nodes)
    while unseen:
        pending = [min(unseen)]
        component = set()
        while pending:
            n = pending.pop()
            if n in component:
                continue
            component.add(n)
            pending.extend(neighbors[n] - component)
        unseen -= component
        components.append(sorted(component))
    return components
