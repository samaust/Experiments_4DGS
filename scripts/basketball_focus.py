"""Static-patch focus screening and deterministic local feature quality."""
import argparse
import json
from pathlib import Path
import cv2
import numpy as np
from basketball_audit import sha256
from basketball_protocol import CAMERAS, PROTOCOL
from basketball_recovery import EARLY, LATE


def sharpness_maps(gray):
    gray = gray.astype(np.float32) / 255.
    mean = cv2.boxFilter(gray, -1, (21, 21))
    variance = np.maximum(0., cv2.boxFilter(gray * gray, -1, (21, 21)) - mean * mean)
    laplacian = cv2.Laplacian(gray, cv2.CV_32F)
    score = cv2.boxFilter(laplacian * laplacian, -1, (21, 21)) / (variance + 1e-6)
    return score, variance


def support_radius(key):
    if len(key) == 6:
        scale = np.linalg.svd(np.asarray(key[2:]).reshape(2, 2), compute_uv=False)[0]
    else:
        scale = abs(float(key[2]))
    return max(8., 6. * scale)


def best_observations(candidates):
    """Candidates contain score, frame, index and COLMAP uv; stable spatial dedup."""
    occupied = set()
    selected = []
    for candidate in sorted(candidates, key=lambda e: (-e['score'], e['frame'], e['index'])):
        cell = tuple(np.floor(np.asarray(candidate['uv']) / 2).astype(int))
        if cell not in occupied:
            occupied.add(cell)
            selected.append(candidate)
    return selected


def sustained(values, threshold):
    count = 0
    for value in values:
        count = count + 1 if value is not None and abs(value - 1.) > threshold else 0
        if count >= 3:
            return True
    return False


def screen_camera(folder, camera, artifacts):
    planned_frames = EARLY + LATE
    frames = []
    missing = []
    observations = []
    images = {}
    masks = {}
    for frame in planned_frames:
        stem = f'camera{camera}-frame{frame}'
        names = [stem + '.png', stem + '-static.png']
        if any(name not in artifacts for name in names):
            missing.append(frame)
            continue
        for name in names:
            if sha256(folder / name) != artifacts[name]:
                raise ValueError(f'changed focus input: {name}')
        images[frame] = cv2.imread(str(folder / names[0]), cv2.IMREAD_GRAYSCALE)
        masks[frame] = cv2.erode(cv2.imread(str(folder / names[1]), cv2.IMREAD_GRAYSCALE), np.ones((23, 23), np.uint8))
        frames.append(frame)
    if len(frames) < 4:
        return dict(camera=camera, status='inconclusive', reason='fewer than four masked fitting samples', missing_frames=missing)
    reference = images[frames[0]]
    points = cv2.goodFeaturesToTrack(reference, maxCorners=2000, qualityLevel=.01,
                                    minDistance=8, mask=masks[frames[0]], blockSize=7)
    if points is None or len(points) < 100:
        return dict(camera=camera, status='inconclusive', reason='fewer than 100 reference static patches')
    ref_score, ref_variance = sharpness_maps(reference)
    for frame in frames:
        target = images[frame]
        tracked, forward, _ = cv2.calcOpticalFlowPyrLK(reference, target, points, None)
        back, backward, _ = cv2.calcOpticalFlowPyrLK(target, reference, tracked, None)
        xy = np.rint(tracked[:, 0]).astype(int)
        good = (forward[:, 0] > 0) & (backward[:, 0] > 0) & (np.linalg.norm(back[:, 0] - points[:, 0], axis=1) <= .5)
        good &= (xy[:, 0] >= 11) & (xy[:, 0] < 949) & (xy[:, 1] >= 11) & (xy[:, 1] < 529)
        indices = np.flatnonzero(good)
        indices = indices[masks[frame][xy[indices, 1], xy[indices, 0]] > 0]
        entry = dict(frame=frame, tracked=len(indices), reference_patches=len(points), sharpness_ratio=None, scale_ratio=None)
        if len(indices) >= 100:
            H, inliers = cv2.findHomography(points[indices, 0], tracked[indices, 0], cv2.RANSAC, 1.)
            if H is not None:
                indices = indices[inliers.ravel().astype(bool)]
                entry['aligned_patches'] = len(indices)
                if len(indices) >= 100:
                    source_xy = np.rint(points[indices, 0]).astype(int)
                    target_xy = xy[indices]
                    score, variance = sharpness_maps(target)
                    rs = ref_score[source_xy[:, 1], source_xy[:, 0]]
                    ts = score[target_xy[:, 1], target_xy[:, 0]]
                    usable = (ref_variance[source_xy[:, 1], source_xy[:, 0]] >= 1e-4) & (variance[target_xy[:, 1], target_xy[:, 0]] >= 1e-4) & (rs > 1e-8)
                    if np.count_nonzero(usable) >= 100:
                        entry['sharpness_ratio'] = float(np.median(ts[usable] / rs[usable]))
                    anchor = np.array([[[480., 270.], [481., 270.], [480., 271.]]], dtype=np.float64)
                    transformed = cv2.perspectiveTransform(anchor, H)[0]
                    J = (transformed[1:] - transformed[0]).T
                    det = np.linalg.det(J)
                    if det > 0:
                        entry['scale_ratio'] = float(np.sqrt(det))
                    projected = cv2.perspectiveTransform(points[indices], H)[:, 0]
                    entry['median_alignment_error_pixels'] = float(np.median(np.linalg.norm(projected - tracked[indices, 0], axis=1)))
        observations.append(entry)
    focus_flag = sustained([e['sharpness_ratio'] for e in observations], .3)
    scale_flag = sustained([e['scale_ratio'] for e in observations], .01)
    incomplete = bool(missing) or any(e['sharpness_ratio'] is None or e['scale_ratio'] is None for e in observations)
    return dict(camera=camera, status='inconclusive' if incomplete else 'flagged' if focus_flag or scale_flag else 'no-sustained-change-detected',
                focus_flag=focus_flag, scale_flag=scale_flag, observations=observations, missing_frames=missing)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--priors', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    cv2.setRNGSeed(0)
    artifacts = json.loads((a.priors / 'artifacts.json').read_text())
    result = dict(schema='basketball-focus-screen/v1', protocol=PROTOCOL, frames=EARLY + LATE,
                  adapter_sha256=sha256(__file__), artifacts_sha256=sha256(a.priors / 'artifacts.json'),
                  interpretation='diagnostic screening only; not proof of physical focus or zoom changes',
                  cameras=[screen_camera(a.priors, c, artifacts) for c in CAMERAS])
    with a.output.open('x') as out:
        json.dump(result, out, indent=2, allow_nan=False)


if __name__ == '__main__':
    main()
