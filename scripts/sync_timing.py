"""Plan 024 timing interchange, with explicit gauge and temporal support.

No dataset access or model fitting occurs at import. Seconds are physical/source
units; a normalized neural-field coordinate is never stored as an offset.
"""
import copy
import math


SCHEMA = 'camera-timing/v1'
CONVENTION = 'corrected_timestamp_seconds = source_timestamp_seconds - offset_seconds'


def _finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _interval(value):
    return (isinstance(value, list) and len(value) == 2 and
            all(_finite(x) for x in value) and value[0] < value[1])


def validate_timing(result):
    """Reject incomplete semantics, nonfinite values and inferred disconnected times."""
    if result.get('schema') != SCHEMA or result.get('units') != 'seconds':
        raise ValueError('unsupported timing schema or units')
    if result.get('convention') != CONVENTION:
        raise ValueError('unsupported offset sign convention')
    ids = result.get('camera_ids', [])
    if not ids or any(not isinstance(c, str) or not c for c in ids) or len(set(ids)) != len(ids):
        raise ValueError('camera IDs must be unique nonempty strings')
    ref = result.get('reference_camera')
    if ref not in ids:
        raise ValueError('reference camera absent')
    offsets = result.get('offset_seconds', {})
    uncertainty = result.get('uncertainty_seconds', {})
    support = result.get('source_support_seconds', {})
    if any(set(x) != set(ids) for x in (offsets, uncertainty, support)):
        raise ValueError('per-camera records must cover every camera ID')
    covered = result.get('coverage', {}).get('camera_ids', [])
    if len(set(covered)) != len(covered) or set(covered) - set(ids) or ref not in covered:
        raise ValueError('invalid coverage')
    if offsets[ref] != 0 or not _finite(offsets[ref]):
        raise ValueError('reference offset must be zero')
    for c in ids:
        o, u = offsets[c], uncertainty[c]
        if (c in covered and not _finite(o)) or (c not in covered and o is not None):
            raise ValueError('coverage and offset availability disagree')
        if u is not None and (not _finite(u) or u < 0 or c not in covered):
            raise ValueError('invalid uncertainty')
        if not _interval(support[c]):
            raise ValueError('invalid source support')
    if not _interval(result.get('source_window_seconds')):
        raise ValueError('missing evidence/source window')
    norm = result.get('normalization', {})
    if not _finite(norm.get('origin_seconds')) or not _finite(norm.get('duration_seconds')) or norm['duration_seconds'] <= 0:
        raise ValueError('invalid shared normalization')
    if result.get('kind') not in ('estimated', 'ground-truth', 'operational-assumption'):
        raise ValueError('timing kind must state evidence strength')
    if not isinstance(result.get('provenance'), dict) or not result['provenance']:
        raise ValueError('missing provenance')
    return result


def corrected_timestamp(result, camera_id, source_seconds):
    validate_timing(result)
    if camera_id not in result['offset_seconds']:
        raise ValueError('unknown camera')
    offset = result['offset_seconds'][camera_id]
    if offset is None:
        raise ValueError('camera disconnected from reference')
    low, high = result['source_support_seconds'][camera_id]
    if not _finite(source_seconds) or not low <= source_seconds < high:
        raise ValueError('timestamp outside supported source interval')
    return source_seconds - offset


def normalized_timestamp(result, camera_id, source_seconds):
    seconds = corrected_timestamp(result, camera_id, source_seconds)
    norm = result['normalization']
    value = (seconds - norm['origin_seconds']) / norm['duration_seconds']
    if not 0 <= value < 1:
        raise ValueError('timestamp outside shared normalization support')
    return value


def source_timestamp(result, camera_id, normalized_time):
    validate_timing(result)
    if not _finite(normalized_time) or not 0 <= normalized_time < 1:
        raise ValueError('normalized timestamp outside support')
    offset = result['offset_seconds'].get(camera_id)
    if offset is None:
        raise ValueError('camera not covered')
    norm = result['normalization']
    value = norm['origin_seconds'] + normalized_time * norm['duration_seconds'] + offset
    corrected_timestamp(result, camera_id, value)
    return value


def rebase_timing(result, reference_camera):
    """Move the gauge and normalization together, preserving normalized times."""
    validate_timing(result)
    shift = result['offset_seconds'].get(reference_camera)
    if shift is None:
        raise ValueError('new reference must belong to covered component')
    out = copy.deepcopy(result)
    out['reference_camera'] = reference_camera
    out['offset_seconds'] = {c: None if o is None else o-shift for c, o in result['offset_seconds'].items()}
    out['normalization']['origin_seconds'] += shift
    if reference_camera != result['reference_camera']:
        # Marginal standard deviations cannot be rebased without covariance.
        out['uncertainty_seconds'] = {c: 0.0 if c == reference_camera else None for c in result['camera_ids']}
        out['provenance']['rebase'] = {'old_reference': result['reference_camera'],
                                      'uncertainty': 'unverified without covariance'}
    return validate_timing(out)


def common_training_keys(frames, conditions, held_out, reserved=(0.8, 1.0)):
    """Union exclusion on source image keys, including unsupported timestamps.

    frames consists of (camera_id, source_frame_id, source_seconds). Never use
    this to remove held-out evaluation targets; its output is training-only.
    """
    if not conditions or not _interval(list(reserved)):
        raise ValueError('conditions and a nonempty temporal holdout are required')
    for condition in conditions:
        validate_timing(condition)
    if any(c['normalization'] != conditions[0]['normalization'] or
           c['reference_camera'] != conditions[0]['reference_camera'] or
           c['camera_ids'] != conditions[0]['camera_ids'] for c in conditions[1:]):
        raise ValueError('conditions must share camera IDs, reference and normalization')
    retained, excluded = [], []
    seen = set()
    for c, frame_id, seconds in frames:
        key = (c, frame_id)
        if key in seen:
            raise ValueError('duplicate source image')
        seen.add(key)
        reasons = []
        if c in held_out:
            reasons.append('held-out-camera')
        for index, condition in enumerate(conditions):
            try:
                corrected = corrected_timestamp(condition, c, seconds)
                normalized_timestamp(condition, c, seconds)
                if reserved[0] <= corrected < reserved[1]:
                    reasons.append(f'temporal-holdout-condition-{index}')
            except ValueError:
                reasons.append(f'unsupported-condition-{index}')
        if reasons:
            excluded.append({'camera_id': c, 'source_frame_id': frame_id, 'reasons': reasons})
        else:
            retained.append(key)
    return retained, excluded


def robust_offsets(camera_ids, reference_camera, edges, *, huber_seconds, iterations=50):
    """Fit o_i-o_j=delta_seconds; disconnected components stay unclaimed.

    Pair rejection is upstream. Huber weighting cannot validate a bridge, infer
    an absent connection, or establish physical accuracy without ground truth.
    """
    import numpy as np
    import networkx as nx

    if (len(set(camera_ids)) != len(camera_ids) or reference_camera not in camera_ids or
            not _finite(huber_seconds) or huber_seconds <= 0 or iterations < 1):
        raise ValueError('invalid graph settings')
    graph = nx.Graph()
    graph.add_nodes_from(camera_ids)
    for e in edges:
        i, j, d = e['i'], e['j'], e['delta_seconds']
        if i not in camera_ids or j not in camera_ids or i == j or not _finite(d) or graph.has_edge(i, j):
            raise ValueError('invalid or duplicate edge')
        graph.add_edge(i, j)
    component = nx.node_connected_component(graph, reference_camera)
    unknowns = [c for c in camera_ids if c in component and c != reference_camera]
    idx = {c: k for k, c in enumerate(unknowns)}
    relevant = [e for e in edges if e['i'] in component and e['j'] in component]
    a = np.zeros((len(relevant), len(unknowns)))
    b = np.array([e['delta_seconds'] for e in relevant])
    for row, e in enumerate(relevant):
        for c, sign in ((e['i'], 1), (e['j'], -1)):
            if c in idx:
                a[row, idx[c]] = sign
    offsets = {c: None for c in camera_ids}
    offsets[reference_camera] = 0.0
    residuals = []
    if unknowns:
        x = np.linalg.lstsq(a, b, rcond=None)[0]
        for _ in range(iterations):
            residual = a @ x-b
            weights = np.sqrt(np.minimum(1, huber_seconds / np.maximum(np.abs(residual), 1e-15)))
            updated = np.linalg.lstsq(a * weights[:, None], b * weights, rcond=None)[0]
            change = np.max(np.abs(updated-x))
            x = updated
            if change < 1e-12:
                break
        offsets.update({c: float(x[k]) for c, k in idx.items()})
        residuals = [dict(e, residual_seconds=float(r)) for e, r in zip(relevant, a @ x-b)]
    return {'offset_seconds': offsets, 'coverage': [c for c in camera_ids if c in component],
            'components': [sorted(c) for c in nx.connected_components(graph)],
            'bridges': [list(e) for e in nx.bridges(graph)], 'edge_residuals': residuals,
            'uncertainty_seconds': {c: 0.0 if c == reference_camera else None for c in camera_ids}}
