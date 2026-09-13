"""Numeric array contracts and recorded OpenCV-grid transformations."""
import numpy as np

SHAPE = (540, 960)


def footprint(valid, shape=SHAPE):
    if valid.dtype != np.bool_ or valid.shape != shape or not valid.any():
        raise ValueError('invalid boolean image footprint')


def instances(labels, semantics, valid, shape=SHAPE):
    footprint(valid, shape)
    if labels.dtype != np.int32 or labels.shape != shape:
        raise ValueError('instances must be int32 on the image grid')
    if (labels[~valid] != -1).any() or (labels[valid] < 0).any():
        raise ValueError('invalid pixels must be -1; valid pixels must be nonnegative')
    ids = {int(i) for i in np.unique(labels) if i > 0}
    if len(ids) > 255 or (ids and max(ids) > 255):
        raise ValueError('legacy 255-ID capacity exceeded; casting is prohibited')
    if set(semantics) != {str(i) for i in ids}:
        raise ValueError('missing or unused semantic metadata')
    for item in semantics.values():
        if item.get('class') not in ('person', 'basketball'):
            raise ValueError('unresolved semantics cannot become static evidence')
        if not item.get('native_class') or not np.isfinite(item.get('score', np.nan)):
            raise ValueError('native class and finite score required')
    return ids


def static_mask(labels, semantics, changing, valid, shape=SHAPE):
    instances(labels, semantics, valid, shape)
    if changing.shape != shape or changing.dtype != np.bool_:
        raise ValueError('changing regions must be boolean on the image grid')
    return (valid & (labels == 0) & ~changing).astype(np.uint8) * 255


def validate_static(mask, valid, shape=SHAPE):
    footprint(valid, shape)
    if mask.dtype != np.uint8 or mask.shape != shape or not np.isin(mask, [0, 255]).all():
        raise ValueError('static mask must be uint8 0/255; 255 is usable')
    if (mask[~valid] != 0).any():
        raise ValueError('static evidence outside valid footprint')


def depth(depth_z, valid, image_valid, confidence=None, shape=SHAPE):
    footprint(image_valid, shape)
    if depth_z.dtype != np.float32 or depth_z.shape != shape or valid.dtype != np.bool_ or valid.shape != shape:
        raise ValueError('depth requires float32 metres and boolean validity on the image grid')
    if (valid & ~image_valid).any() or not np.isnan(depth_z[~valid]).all():
        raise ValueError('depth validity/NaN contract violated')
    if not np.isfinite(depth_z[valid]).all() or (depth_z[valid] <= 0).any():
        raise ValueError('valid depth must be finite positive camera-z')
    if confidence is not None and (confidence.dtype != np.float32 or confidence.shape != shape):
        raise ValueError('confidence must be float32 on the image grid')


def transform_K(K, scale=(1., 1.), crop=(0., 0.), pad=(0., 0.)):
    """Pixel-center-preserving resize, followed by crop and padding."""
    K = np.asarray(K, np.float64)
    sx, sy = scale
    if K.shape != (3, 3) or not np.isfinite(K).all() or min(sx, sy) <= 0:
        raise ValueError('invalid intrinsic transform')
    A = np.array([[sx, 0, (sx - 1) / 2 - crop[0] + pad[0]],
                  [0, sy, (sy - 1) / 2 - crop[1] + pad[1]], [0, 0, 1]], np.float64)
    return A @ K, A


def renderer_K(K_cv):
    K = np.array(K_cv, dtype=np.float64, copy=True)
    K[:2, 2] += .5
    return K


def bilinear_valid(values, valid, map_x, map_y):
    """Use the historical INTER_LINEAR kernel and reject invalid weighted support.

    Some OpenCV backends quantize interpolation coordinates to 1/32 pixels;
    others retain sub-table weights. Remapping an invalidity indicator with the
    same kernel tests its actual nonzero weights, including border contributors.
    """
    import cv2
    values, valid = np.asarray(values), np.asarray(valid)
    if values.shape != valid.shape or valid.dtype != np.bool_ or values.ndim != 2:
        raise ValueError('invalid source depth grid')
    mx, my = np.asarray(map_x, np.float32), np.asarray(map_y, np.float32)
    if mx.shape != my.shape or mx.ndim != 2:
        raise ValueError('remap grids must have identical two-dimensional shapes')
    source_good = valid & np.isfinite(values) & (values > 0)
    sampled = cv2.remap(np.where(source_good, values, 0).astype(np.float32), mx, my,
                        cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    invalid_weight = cv2.remap((~source_good).astype(np.float32), mx, my,
                               cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=1)
    good = np.isfinite(mx) & np.isfinite(my) & (invalid_weight == 0) & np.isfinite(sampled) & (sampled > 0)
    sampled[~good] = np.nan
    return sampled, good


def sample_depth(values, valid, uv):
    uv = np.asarray(uv, np.float64)
    if uv.ndim != 2 or uv.shape[1] != 2:
        raise ValueError('sparse sample UV shape')
    if not len(uv):
        return np.empty(0, np.float32), np.empty(0, bool)
    values, good = bilinear_valid(values, valid, uv[:, 0:1], uv[:, 1:2])
    return values.ravel(), good.ravel()


def ray_range_to_z(distance, K):
    y, x = np.indices(distance.shape, dtype=np.float64)
    rays = np.stack((x, y, np.ones_like(x)), -1) @ np.linalg.inv(np.asarray(K, np.float64)).T
    rays /= rays[..., 2:3]
    return (distance / np.linalg.norm(rays, axis=-1)).astype(np.float32)


def metric_depth(raw, method, *, processed_K=None, already_metric=False):
    """One conversion at the explicit native-output boundary, never in resampling."""
    raw = np.asarray(raw)
    factor = 1.
    if method in ('D0', 'D1', 'D4'):
        if not already_metric:
            raise ValueError('native camera-z metric output required')
    elif method in ('D2', 'D3'):
        if already_metric:
            raise ValueError('canonical focal conversion would be applied twice')
        K = np.asarray(processed_K, np.float64)
        if K.shape != (3, 3) or not np.isfinite(K).all() or min(K[0, 0], K[1, 1]) <= 0:
            raise ValueError('actual processed intrinsics required')
        factor = float((K[0, 0] + K[1, 1]) / 600 if method == 'D2' else K[0, 0] / 1000)
    else:
        raise ValueError('unknown depth component')
    converted = (raw * factor).astype(np.float32)
    valid = np.isfinite(converted) & (converted > 0)
    converted[~valid] = np.nan
    return converted, valid, dict(focal_conversion_count=int(method in ('D2', 'D3')),
        factor=factor, native_nonfinite=int((~np.isfinite(raw)).sum()),
        native_nonpositive=int((np.isfinite(raw) & (raw <= 0)).sum()))


def merge_logits(logits, detections, valid):
    """S2/S4 original-grid logits; detector score/index break exact ties."""
    logits = np.asarray(logits)
    if logits.shape != (len(detections), *valid.shape) or len(detections) > 255:
        raise ValueError('logit shape or object capacity violation')
    if not np.isfinite(logits).all():
        raise ValueError('nonfinite mask logits')
    order = sorted(range(len(detections)), key=lambda i: (-detections[i]['score'], detections[i]['index']))
    labels = np.zeros(valid.shape, np.int32)
    best = np.zeros(valid.shape, np.float32)
    suppressed = []
    semantics = {}
    ids = [d['id'] for d in detections]
    if len(set(ids)) != len(ids) or any(type(i) is not int or not 1 <= i <= 255 for i in ids):
        raise ValueError('invalid pair-local detection IDs')
    for i in order:
        d = detections[i]
        if d['class'] not in ('person', 'basketball'):
            raise ValueError('missing normalized detection semantics')
        take = valid & (logits[i] > best)
        labels[take] = d['id']
        best[take] = logits[i][take]
    labels[~valid] = -1
    for i, d in enumerate(detections):
        suppressed.append(dict(id=d['id'], pixels=int((valid & (logits[i] > 0) & (labels != d['id'])).sum())))
        if np.any(labels == d['id']):
            semantics[str(d['id'])] = d.copy()
    instances(labels, semantics, valid, valid.shape)
    return labels, semantics, suppressed
