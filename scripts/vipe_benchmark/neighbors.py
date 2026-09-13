"""Deterministic N0/N1/N2 on one immutable training-only point-ID map."""
import numpy as np


def _project(xyz, camera):
    xyz_cam = np.asarray(xyz, np.float64) @ np.asarray(camera['R'], np.float64).T + camera['t']
    q = xyz_cam @ np.asarray(camera['K'], np.float64).T
    with np.errstate(divide='ignore', invalid='ignore'):
        uv = q[:, :2] / q[:, 2:3]
    return uv, xyz_cam[:, 2]


def _inside(uv, z, valid):
    finite = np.isfinite(uv).all(1) & np.isfinite(z) & (z > 0)
    xy = np.floor(np.where(finite[:, None], uv, -1)).astype(int)
    inside = finite & (uv[:, 0] >= 0) & (uv[:, 0] < valid.shape[1]) & (uv[:, 1] >= 0) & (uv[:, 1] < valid.shape[0])
    ids = np.flatnonzero(inside)
    inside[ids] &= valid[xy[ids, 1], xy[ids, 0]]
    return inside


def eligible_support(reference, other, tracks, points, cameras, footprints):
    ids = sorted(tracks[reference] & tracks[other])
    if not ids:
        return dict(points=set(), reference_cells=set(), candidate_cells=set(), median_sin=0.)
    xyz = np.asarray([points[i] for i in ids], np.float64)
    uv0, z0 = _project(xyz, cameras[reference])
    uv1, z1 = _project(xyz, cameras[other])
    rays0, rays1 = xyz - cameras[reference]['center'], xyz - cameras[other]['center']
    with np.errstate(invalid='ignore', divide='ignore'):
        cosine = np.sum(rays0 * rays1, axis=1) / (np.linalg.norm(rays0, axis=1) * np.linalg.norm(rays1, axis=1))
    angle = np.arccos(np.clip(cosine, -1, 1))
    good = _inside(uv0, z0, footprints[reference]) & _inside(uv1, z1, footprints[other])
    good &= np.isfinite(angle) & (angle >= np.deg2rad(1.))
    return dict(points={ids[i] for i in np.flatnonzero(good)},
                reference_cells=set(map(tuple, np.floor(uv0[good] / [240, 135]).astype(int))),
                candidate_cells=set(map(tuple, np.floor(uv1[good] / [240, 135]).astype(int))),
                median_sin=float(np.median(np.sin(angle[good]))) if good.any() else 0.)


def rank(method, reference, tracks, *, training, points=None, cameras=None, footprints=None):
    if set(tracks) != set(training) or reference not in training or len(set(training)) != len(training):
        raise ValueError('neighbor map must contain exactly the training camera IDs')
    tracks = {c: set(t) for c, t in tracks.items()}
    candidates = []
    support = {}
    for other in sorted(training):
        if other == reference:
            continue
        count = len(tracks[reference] & tracks[other])
        union = len(tracks[reference] | tracks[other])
        if not count:
            continue
        candidates.append(dict(camera=other, shared=count, jaccard=count / union))
        if method == 'N2':
            support[other] = eligible_support(reference, other, tracks, points, cameras, footprints)
    if method == 'N0':
        candidates.sort(key=lambda r: (-r['shared'], r['camera']))
    elif method == 'N1':
        candidates.sort(key=lambda r: (-r['jaccard'], -r['shared'], r['camera']))
    elif method != 'N2':
        raise ValueError('unknown neighbor method')
    selected, rounds = [], []
    covered_cells, covered_points = set(), set()
    for _ in range(3):
        available = [r for r in candidates if r['camera'] not in selected and
                     (method != 'N2' or support[r['camera']]['points'])]
        if not available:
            return dict(status='blocked', neighbors=[], partial_neighbors=selected,
                        reason='fewer than three positive-support eligible training neighbors', rounds=rounds)
        if method == 'N2':
            scores = []
            for r in available:
                s = support[r['camera']]
                score = (len(s['reference_cells'] - covered_cells), len(s['points'] - covered_points),
                         len(s['candidate_cells']), round(s['median_sin'], 12), round(r['jaccard'], 12),
                         r['shared'], -r['camera'])
                scores.append((score, r))
            scores.sort(key=lambda x: x[0], reverse=True)
            chosen = scores[0][1]
            rounds.append([dict(camera=r['camera'], score=list(score)) for score, r in scores])
            covered_cells |= support[chosen['camera']]['reference_cells']
            covered_points |= support[chosen['camera']]['points']
        else:
            chosen = available[0]
        selected.append(chosen['camera'])
    return dict(status='complete', neighbors=selected, candidates=candidates, rounds=rounds,
                occupied_reference_cells=len(covered_cells) if method == 'N2' else None,
                covered_point_ids=sorted(covered_points) if method == 'N2' else None)
