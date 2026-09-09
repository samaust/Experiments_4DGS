"""Pixel-center geometry and motion gates for Plan 026 Basketball initialization."""
import numpy as np


def crop_to_image(uv, box, size):
    """RoMa continuous crop pixel centers to full continuous image coordinates."""
    x0, y0, x1, y1 = box
    width, height = size
    if width <= 0 or height <= 0 or x1 <= x0 or y1 <= y0:
        raise ValueError('invalid crop mapping')
    return np.asarray(uv) * [(x1-x0)/width, (y1-y0)/height] + [x0, y0]


def projection(camera):
    return np.asarray(camera['K']) @ np.column_stack((camera['world_to_camera_R'], camera['world_to_camera_T']))


def project(points, P):
    q = np.column_stack((points, np.ones(len(points)))) @ np.asarray(P).T
    with np.errstate(divide='ignore', invalid='ignore'):
        uv = q[:, :2]/q[:, 2:3]
    return uv, q[:, 2]


def triangulate(uvs, projections):
    """Batched DLT over the same supporting cameras, continuous pixel coordinates."""
    uvs, projections = np.asarray(uvs), np.asarray(projections)
    if uvs.ndim != 3 or uvs.shape[2] != 2 or projections.shape != (uvs.shape[0], 3, 4):
        raise ValueError('expected views x points x 2 and views x 3 x 4')
    rows = []
    for uv, P in zip(uvs, projections):
        rows.extend((uv[:, 0, None]*P[2]-P[0], uv[:, 1, None]*P[2]-P[1]))
    matrix = np.stack(rows, axis=1)
    finite = np.isfinite(matrix).all(axis=(1, 2))
    result = np.full((uvs.shape[1], 3), np.nan)
    if finite.any():
        _, _, v = np.linalg.svd(matrix[finite])
        with np.errstate(divide='ignore', invalid='ignore'):
            result[finite] = v[:, -1, :3]/v[:, -1, 3:4]
    return result


def geometry_gate(points, uvs, projections, centers):
    points, uvs = np.asarray(points), np.asarray(uvs)
    good = np.isfinite(points).all(axis=1)
    errors, depths = [], []
    for uv, P in zip(uvs, projections):
        predicted, depth = project(points, P)
        error = np.linalg.norm(predicted-uv, axis=1)
        good &= np.isfinite(error) & (error <= 2) & (depth > 0)
        errors.append(error)
        depths.append(depth)
    rays = points[None]-np.asarray(centers)[:, None]
    with np.errstate(invalid='ignore', divide='ignore'):
        rays = rays/np.linalg.norm(rays, axis=2, keepdims=True)
    angle = np.zeros(len(points))
    for i in range(len(centers)):
        for j in range(i):
            angle = np.maximum(angle, np.degrees(np.arccos(np.clip((rays[i]*rays[j]).sum(1), -1, 1))))
    good &= np.isfinite(angle) & (angle >= 1)
    return good, dict(reprojection=np.asarray(errors), depth=np.asarray(depths), angle=angle)


def labels_at(labels, uv):
    uv = np.asarray(uv)
    finite = np.isfinite(uv).all(axis=1)
    xy = np.floor(np.where(finite[:, None], uv, -1)).astype(int)
    good = finite & (xy[:, 0] >= 0) & (xy[:, 0] < labels.shape[1]) & (xy[:, 1] >= 0) & (xy[:, 1] < labels.shape[0])
    result = np.full(len(uv), -1, dtype=int)
    result[good] = labels[xy[good, 1], xy[good, 0]]
    return result


def track_lk(image0, image1, uv, labels0, labels1):
    import cv2
    # OpenCV LK takes zero-indexed pixel centers; RoMa/K use centers at .5.
    p = (np.asarray(uv)-.5).astype(np.float32).reshape(-1, 1, 2)
    options = dict(winSize=(31, 31), maxLevel=3,
                   criteria=(cv2.TERM_CRITERIA_EPS | cv2.TERM_CRITERIA_COUNT, 30, .01))
    gray0, gray1 = [cv2.cvtColor(im, cv2.COLOR_RGB2GRAY) for im in (image0, image1)]
    q, status1, _ = cv2.calcOpticalFlowPyrLK(gray0, gray1, p, None, **options)
    back, status0, _ = cv2.calcOpticalFlowPyrLK(gray1, gray0, q, None, **options)
    endpoint = q[:, 0]+.5
    first, second = labels_at(labels0, uv), labels_at(labels1, endpoint)
    valid = (status0[:, 0] > 0) & (status1[:, 0] > 0)
    valid &= np.linalg.norm(back[:, 0]-p[:, 0], axis=1) <= 1
    valid &= (first > 0) & (first == second) & np.isfinite(endpoint).all(axis=1)
    return endpoint, valid


def velocity_from_support(start, endpoints, projections, centers, valid, camera_ids, transform, duration_seconds=2.):
    """Require three distinct agreeing cameras; unsupported motion is flagged zero."""
    if len(set(camera_ids)) != len(camera_ids):
        raise ValueError('duplicate camera support')
    velocity = np.zeros_like(start)
    measured = np.zeros(len(start), dtype=bool)
    for i in range(len(start)):
        support = np.flatnonzero(valid[:, i])
        if len(support) < 3:
            continue
        P = np.asarray(projections)[support]
        uv = endpoints[support, i:i+1]
        end = triangulate(uv, P)
        good, _ = geometry_gate(end, uv, P, np.asarray(centers)[support])
        if good[0]:
            velocity[i] = (end[0]-start[i]) @ np.asarray(transform)[:3, :3].T * duration_seconds/.04
            measured[i] = np.isfinite(velocity[i]).all()
    velocity[~measured] = 0
    return velocity, measured
