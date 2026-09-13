"""One staged aggregation transaction with explicit evidence eligibility.

Model-assisted annotations measure agreement with their frozen teacher. Unknown
layers never become background truth, static suitability, or temporal identity.
The caller reserves a single aggregate allocation and supplies immutable stage
parents; this module creates fresh checkpoints and never rescans old outputs.
"""
from collections import defaultdict
import time

import numpy as np

from .access import Identity, annotation_identities, output_identities, role, validate_grid
from .config import ROOT
from .contracts import instances as validate_instances, validate_static
from .files import digest, file_record, load_array, object_hash, read_json, safe_path, verify_record, write_json
from .metrics import (boundary_counts, conditional_domain, instance_matching,
                      pixel_counts, pixel_scores, temporal_counts, temporal_groups)
from .selection import combined, select

STRATA = ('all', 'occlusion', 'blur', 'tiny_ball', 'stationary_people', 'spectators', 'shadows', 'changing_displays')
PROXY_SCHEMA = 'vipe-benchmark-automated-annotations/v1'


def _document(record):
    verify_record(record)
    return read_json(record['path'])


def _union(labels, metadata, semantic):
    return np.isin(labels, [int(i) for i, m in metadata.items() if m['class'] == semantic])


def _eligibility(annotation, name, *, proxy):
    if not proxy:
        return True
    value = annotation.get('eligibility', {}).get(name)
    return value is True or (name == 'boundary' and value == 'proxy-only')


def _strata(annotation):
    tags = annotation.get('tags') or {}
    result, unknown = ['all'], []
    for name in STRATA[1:]:
        value = tags.get(name)
        if value is None and name in ('occlusion', 'blur', 'tiny_ball'):
            values = [m.get(name) for m in annotation['instances'].values()]
            value = True if any(v is True for v in values) else False if values and all(v is False for v in values) else None
        if value is True:
            result.append(name)
        elif value is not False:
            unknown.append(name)
    return result, unknown


def _at(mask, uv):
    """Nearest integer-center mask lookup, with outside support excluded."""
    uv = np.asarray(uv, np.float64).reshape(-1, 2)
    finite = np.isfinite(uv).all(1)
    xy = np.rint(np.where(finite[:, None], uv, -1)).astype(int)
    good = finite & (xy[:, 0] >= 0) & (xy[:, 0] < mask.shape[1]) & (xy[:, 1] >= 0) & (xy[:, 1] < mask.shape[0])
    result = np.zeros(len(uv), bool)
    result[good] = mask[xy[good, 1], xy[good, 0]]
    return result


def score_image(prediction, semantics, changing, annotation, layers, *, proxy=False,
                sift=None, observations=None):
    """Raw additive statistics for one prediction context and frozen annotation.

    Strata select complete images containing a reviewed tag, rather than guessing
    an evaluation region from a model's labels. Role domains use annotated roles.
    """
    truth, valid, ignored = (np.asarray(layers[k]) for k in ('instances', 'valid', 'ignored'))
    if truth.dtype != np.int32 or valid.dtype != np.bool_ or ignored.dtype != np.bool_ or any(
            a.shape != prediction.shape for a in (truth, valid, ignored, changing)):
        raise ValueError('annotation/prediction grid or dtype mismatch')
    validate_instances(prediction, semantics, valid, shape=valid.shape)
    if changing.dtype != np.bool_:
        raise ValueError('invalid changing annotation mask')
    domain = valid & ~ignored
    metadata = annotation['instances']
    if set(metadata) != {str(int(i)) for i in np.unique(truth) if i > 0}:
        raise ValueError('annotation semantics incomplete')
    predicted_static = valid & (prediction == 0) & ~changing
    records, matches = [], {}
    strata, unknown = _strata(annotation)

    def add(kind, metric, counts=None, reason=None, evidence=None):
        records.append(dict(kind=kind, metric=metric, counts=counts, status='complete' if counts is not None else 'unverified',
                            reason=reason, strata=strata, unknown_strata=unknown,
                            evidence_kind=evidence or ('model-assisted-proxy' if proxy else 'reviewed-annotation')))

    for semantic, eligibility in (('person', 'person_union'), ('basketball', 'basketball')):
        if not _eligibility(annotation, eligibility, proxy=proxy):
            for kind in ('pixel', 'boundary', 'instance'):
                add(kind, semantic, reason=f'{semantic} reference layer unavailable')
            continue
        p, t = _union(prediction, semantics, semantic), _union(truth, metadata, semantic)
        add('pixel', semantic, pixel_counts(p, t, domain))
        add('boundary', semantic, boundary_counts(p, t, domain) if _eligibility(annotation, 'boundary', proxy=proxy) else None,
            reason=None if _eligibility(annotation, 'boundary', proxy=proxy) else 'boundary reference unavailable')
        pi = [int(i) for i, m in semantics.items() if m['class'] == semantic and ((prediction == int(i)) & domain).any()]
        ti = [int(i) for i, m in metadata.items() if m['class'] == semantic and ((truth == int(i)) & domain).any()]
        matching = instance_matching(prediction, truth, pi, ti, domain)
        matches[semantic] = matching
        add('instance', semantic, {k: matching[k] for k in ('tp', 'fp', 'fn')})
        if semantic == 'person':
            for target in ('player', 'other-person'):
                if not _eligibility(annotation, 'roles', proxy=proxy):
                    add('pixel', target, reason='independently reviewed person roles unavailable')
                    add('role_instance', target, reason='independently reviewed person roles unavailable')
                    continue
                d = conditional_domain(domain, truth, metadata, target)
                role_truth = np.isin(truth, [int(i) for i, m in metadata.items() if m.get('role') == target and
                                          m['class'] == 'person' and not m.get('role_uncertain', False)])
                # role_uncertain explicitly excludes even an inconsistent saved role.
                d &= ~np.isin(truth, [int(i) for i, m in metadata.items() if m.get('role_uncertain', False)])
                add('pixel', target, pixel_counts(p, role_truth, d))
                role_ids = [i for i in ti if metadata[str(i)].get('role') == target and not metadata[str(i)].get('role_uncertain', False)]
                match_role = [r for r in matching['matches'] if r['truth_id'] in role_ids]
                add('role_instance', target, dict(matches=len(match_role), truth=len(role_ids),
                    unmatched_predictions=matching['fp'], matched_iou_sum=sum(r['iou'] for r in match_role)))
        else:
            tiny = [i for i in ti if int(((truth == i) & valid).sum()) <= 100]
            by_truth = {m['truth_id']: m for m in matching['matches']}
            detected, center_error, predicted_area, truth_area = 0, 0., 0, 0
            for i in tiny:
                tmask = (truth == i) & domain
                truth_area += int(((truth == i) & valid).sum())
                if i in by_truth:
                    pmask = (prediction == by_truth[i]['prediction_id']) & domain
                    detected += 1
                    center_error += float(np.linalg.norm(np.mean(np.argwhere(tmask), axis=0) - np.mean(np.argwhere(pmask), axis=0)))
                    predicted_area += int(pmask.sum())
            add('tiny_ball', 'basketball', dict(visible=len(tiny), detected=detected, center_error_sum=center_error,
                predicted_matched_area_sum=predicted_area, truth_visible_area_sum=truth_area))
    if all(_eligibility(annotation, k, proxy=proxy) for k in ('person_union', 'basketball', 'boundary')):
        add('boundary', 'semantic_foreground', boundary_counts(prediction > 0, truth > 0, domain))
    else:
        add('boundary', 'semantic_foreground', reason='both semantic foreground boundary layers required')
    if _eligibility(annotation, 'changing', proxy=proxy):
        add('pixel', 'changing', pixel_counts(changing, layers['changing'], domain))
        add('boundary', 'changing', boundary_counts(changing, layers['changing'], domain))
    else:
        add('pixel', 'changing', reason='independent changing-background reference unavailable')
        add('boundary', 'changing', reason='independent changing-background reference unavailable')
    if _eligibility(annotation, 'static', proxy=proxy) and _eligibility(annotation, 'changing', proxy=proxy):
        foreground = (truth > 0) | layers['changing']
        static_truth = valid & ~foreground
        add('pixel', 'usable_static', pixel_counts(predicted_static, static_truth, domain))
        add('boundary', 'usable_static', boundary_counts(predicted_static, static_truth, domain))
        add('fraction', 'foreground_leakage', dict(numerator=int((predicted_static & foreground & domain).sum()),
                                                 denominator=int((foreground & domain).sum())))
        add('fraction', 'retained_static_area', dict(numerator=int((predicted_static & static_truth & domain).sum()),
                                                   denominator=int((static_truth & domain).sum())))
    else:
        for kind, metric in [('pixel', 'usable_static'), ('boundary', 'usable_static'),
                             ('fraction', 'foreground_leakage'), ('fraction', 'retained_static_area')]:
            add(kind, metric, reason='unknown changing/static layers cannot become static truth')
    add('fraction', 'predicted_static_area', dict(numerator=int((predicted_static & domain).sum()), denominator=int(domain.sum())),
        evidence='descriptive-prediction')
    reviewed = annotation.get('static_feature_review') or []
    audit = {r['index']: r for r in annotation.get('static_feature_locations', [])}
    suitable = [audit[r['index']]['uv'] for r in reviewed if r.get('suitable') is True and r['index'] in audit]
    if suitable:
        add('fraction', 'retained_static_features', dict(numerator=int(_at(predicted_static, suitable).sum()), denominator=len(suitable)),
            evidence='reviewed-static-features')
    else:
        add('fraction', 'retained_static_features', reason='no independently reviewed suitable static feature locations')
    if sift is not None:
        uv = np.asarray(sift)[:, :2]
        eligible = _at(valid, uv)
        kept = eligible & _at(predicted_static, uv)
        cells = np.floor(uv / [240, 135]).astype(int)
        add('fraction', 'automatic_sift_retention', dict(numerator=int(kept.sum()), denominator=int(eligible.sum())), evidence='descriptive-frozen-feature-pool')
        add('fraction', 'automatic_sift_grid_retention', dict(numerator=len(set(map(tuple, cells[kept]))),
            denominator=len(set(map(tuple, cells[eligible])))), evidence='descriptive-frozen-feature-pool')
    if observations is not None:
        eligible = _at(valid, observations)
        kept = eligible & _at(predicted_static, observations)
        add('fraction', 'accepted_map_observation_retention', dict(numerator=int(kept.sum()), denominator=int(eligible.sum())),
            evidence='descriptive-frozen-map-observations')
    return records, matches


def score_pair(first, second, annotation0, annotation1, associations, layers0, layers1, *, proxy=False):
    """Temporal evidence is unavailable unless identity associations are eligible."""
    eligible = _eligibility(annotation0, 'temporal', proxy=proxy) and _eligibility(annotation1, 'temporal', proxy=proxy)
    eligible &= all(r.get('eligible', not proxy) is True for r in associations)
    records = []
    strata0, unknown0 = _strata(annotation0)
    strata1, unknown1 = _strata(annotation1)
    for semantic in ('person', 'basketball'):
        row = dict(kind='temporal', metric=semantic, strata=sorted(set(strata0) | set(strata1)),
                   unknown_strata=sorted(set(unknown0) | set(unknown1)),
                   evidence_kind='model-assisted-proxy' if proxy else 'reviewed-annotation')
        if not eligible:
            records.append(dict(row, status='unverified', counts=None, reason='independent eligible pair identity associations unavailable'))
            continue
        matches = []
        for pred, annotation, layers in ((first, annotation0, layers0), (second, annotation1, layers1)):
            domain = layers['valid'] & ~layers['ignored']
            pi = [int(i) for i, m in pred['semantics'].items() if m['class'] == semantic and ((pred['labels'] == int(i)) & domain).any()]
            ti = [int(i) for i, m in annotation['instances'].items() if m['class'] == semantic and ((layers['instances'] == int(i)) & domain).any()]
            matches.append(instance_matching(pred['labels'], layers['instances'], pi, ti, domain))
        selected = [a for a in associations if ((a['first_id'] is not None and
            annotation0['instances'][str(a['first_id'])]['class'] == semantic) or (a['second_id'] is not None and
            annotation1['instances'][str(a['second_id'])]['class'] == semantic))]
        for a in selected:
            if a['first_id'] is not None and a['second_id'] is not None and (
                    annotation0['instances'][str(a['first_id'])]['class'] != annotation1['instances'][str(a['second_id'])]['class']):
                raise ValueError('temporal truth identity changes semantic class')
        # Restrict prediction IDs to this semantic class for false-birth and
        # continuation counts; the historical helper expects a class domain.
        predictions = [np.where(_union(p['labels'], p['semantics'], semantic) & l['valid'] & ~l['ignored'], p['labels'], 0)
                       for p, l in ((first, layers0), (second, layers1))]
        raw = temporal_counts(*predictions, layers0['instances'], layers1['instances'], *matches, selected,
                              layers0['valid'] & ~layers0['ignored'], layers1['valid'] & ~layers1['ignored'])
        for key in ('area_change_errors', 'successor_dice'):
            values = [v for v in raw.pop(key) if v is not None]
            raw[key + '_sum'], raw[key + '_count'] = sum(values), len(values)
        records.append(dict(row, status='complete', counts=raw, reason=None))
    return records


def _divide(n, d):
    n, d = np.asarray(n, np.float64), np.asarray(d, np.float64)
    return np.divide(n, d, out=np.full(np.broadcast_shapes(n.shape, d.shape), np.nan), where=d != 0)


def _values(kind, counts):
    if kind == 'pixel':
        t, p, n = (counts[k] for k in ('tp', 'fp', 'fn'))
        return dict(precision=_divide(t, t+p), recall=_divide(t, t+n), iou=_divide(t, t+p+n), dice=_divide(2*t, 2*t+p+n),
                    negative_false_positive_pixels_per_negative_image=_divide(counts['negative_false_positive_pixels'], counts['negative_images']))
    if kind == 'boundary':
        p, r = _divide(counts['matched_prediction'], counts['predicted_boundary']), _divide(counts['matched_truth'], counts['truth_boundary'])
        f = _divide(2*p*r, p+r)
        f = np.where((p == 0) & (r == 0), 0., f)
        # A completely missed/false-positive boundary is a zero F1, not a
        # camera that may be silently dropped from the equal-camera mean.
        one_empty = (np.asarray(counts['predicted_boundary']) == 0) ^ (np.asarray(counts['truth_boundary']) == 0)
        f = np.where(one_empty, 0., f)
        return dict(f1=f, precision=p, recall=r)
    if kind == 'instance':
        return dict(precision=_divide(counts['tp'], counts['tp']+counts['fp']), recall=_divide(counts['tp'], counts['tp']+counts['fn']))
    if kind == 'fraction':
        return dict(fraction=_divide(counts['numerator'], counts['denominator']))
    if kind == 'role_instance':
        matches = counts['matches']
        return dict(recall=_divide(matches, counts['truth']),
                    precision_lower=np.where(matches > 0, _divide(matches, matches+counts['unmatched_predictions']), np.nan),
                    precision_upper=np.where(matches > 0, 1., np.nan), matched_iou=_divide(counts['matched_iou_sum'], matches))
    if kind == 'tiny_ball':
        return dict(recall=_divide(counts['detected'], counts['visible']),
                    center_error_pixels=_divide(counts['center_error_sum'], counts['detected']),
                    matched_predicted_area=_divide(counts['predicted_matched_area_sum'], counts['detected']),
                    visible_truth_area=_divide(counts['truth_visible_area_sum'], counts['visible']))
    if kind == 'temporal':
        return dict(all_successor_recall=_divide(counts['matched_successors'], counts['visible_successors']),
                    id_switch_fraction=_divide(counts['id_switches'], counts['matched_both']),
                    missing_successor_fraction=_divide(counts['missing_successor_matches'], counts['visible_successors']),
                    successor_dice_conditioned_on_keyframe_match=_divide(counts['successor_dice_sum'], counts['successor_dice_count']),
                    area_change_error=_divide(counts['area_change_errors_sum'], counts['area_change_errors_count']))
    raise ValueError('unknown additive metric kind')


def _mean(values, axis):
    return _divide(np.where(np.isfinite(values), values, 0).sum(axis=axis), np.isfinite(values).sum(axis=axis))


def _number(value):
    return float(value) if np.isfinite(value) else None


def _draws(keys, *, resamples, seed):
    """Same PCG64 camera-then-group draws as metrics.paired_bootstrap."""
    cameras = sorted({c for c, _ in keys})
    positions = {c: [i for i, (camera, _) in enumerate(keys) if camera == c] for c in cameras}
    rng = np.random.Generator(np.random.PCG64(seed))
    weights = np.zeros((resamples, len(cameras), len(keys)), np.int16)
    for b in range(resamples):
        sampled = rng.choice(cameras, len(cameras), replace=True)
        for slot, camera in enumerate(sampled):
            chosen = rng.choice(positions[camera], len(positions[camera]), replace=True)
            weights[b, slot] = np.bincount(chosen, minlength=len(keys))
    return cameras, positions, weights


def balanced_statistics(method_groups, kind, *, resamples=10000, seed=0, draw_cache=None):
    """Pool counts within camera, then equal-camera means and paired intervals."""
    methods = sorted(method_groups)
    if not methods:
        return dict(status='unverified', reason='no complete metric evidence', scores={})
    keys = sorted(method_groups[methods[0]])
    if not keys or any(set(method_groups[m]) != set(keys) for m in methods):
        raise ValueError('paired methods must retain identical camera/temporal groups')
    fields = sorted(method_groups[methods[0]][keys[0]])
    if any(set(r) != set(fields) for m in methods for r in method_groups[m].values()):
        raise ValueError('inconsistent additive statistic fields')
    counts = np.asarray([[[method_groups[m][key][f] for f in fields] for key in keys] for m in methods], np.float64)
    if not np.isfinite(counts).all() or (counts < 0).any():
        raise ValueError('raw counts must be finite and nonnegative')
    cache_key = (tuple(keys), resamples, seed)
    if draw_cache is not None and cache_key in draw_cache:
        cameras, positions, weights = draw_cache[cache_key]
    else:
        cameras, positions, weights = _draws(keys, resamples=resamples, seed=seed)
        if draw_cache is not None:
            draw_cache[cache_key] = cameras, positions, weights
    camera_counts = np.stack([counts[:, positions[c]].sum(axis=1) for c in cameras], axis=1)
    bootstrap = np.einsum('bcg,mgf->mbcf', weights, counts, optimize=True)
    camera_scores = _values(kind, {f: camera_counts[..., i] for i, f in enumerate(fields)})
    boot_scores = _values(kind, {f: bootstrap[..., i] for i, f in enumerate(fields)})
    scores = {}
    for metric, per_camera in camera_scores.items():
        estimate, draws = _mean(per_camera, 1), _mean(boot_scores[metric], 2)
        differences = {}
        for i, a in enumerate(methods):
            for j in range(i+1, len(methods)):
                b = methods[j]
                diff = draws[j] - draws[i]
                defined = diff[np.isfinite(diff)]
                interval = np.quantile(defined, [.025, .975], method='linear').tolist() if len(defined) else None
                differences[f'{b}-{a}'] = dict(estimate=_number(estimate[j] - estimate[i]), interval_95=interval,
                    defined_resamples=len(defined), conclusion='unverified' if interval is None else
                    'inconclusive' if interval[0] <= 0 <= interval[1] else 'nonzero paired difference')
        scores[metric] = dict(estimates={m: _number(estimate[i]) for i, m in enumerate(methods)},
            per_camera={m: {str(c): _number(per_camera[i, j]) for j, c in enumerate(cameras)} for i, m in enumerate(methods)},
            per_camera_extrema={m: [float(np.nanmin(per_camera[i])), float(np.nanmax(per_camera[i]))]
                                if np.isfinite(per_camera[i]).any() else None for i, m in enumerate(methods)},
            undefined_cameras={m: [c for j, c in enumerate(cameras) if not np.isfinite(per_camera[i, j])] for i, m in enumerate(methods)},
            interval_95={m: np.quantile(draws[i, np.isfinite(draws[i])], [.025, .975], method='linear').tolist()
                         if np.isfinite(draws[i]).any() else None for i, m in enumerate(methods)}, differences=differences)
    return dict(status='complete', scores=scores, resamples=resamples, seed=seed, generator='PCG64', quantile='linear',
                pooling='sum counts within each sampled camera, then average defined cameras equally',
                raw_by_camera={m: {str(c): {f: float(camera_counts[i, j, k]) for k, f in enumerate(fields)}
                                   for j, c in enumerate(cameras)} for i, m in enumerate(methods)},
                raw_by_group={m: [dict(camera=c, temporal_group=g, counts=method_groups[m][c, g]) for c, g in keys] for m in methods})


def aggregate_rows(rows, methods, *, resamples=10000):
    """Keep every unavailable class/stratum; never pair mismatched item domains."""
    grouped, frame_sets = defaultdict(list), defaultdict(set)
    for row in rows:
        identity = Identity(**row['identity'])
        frame_sets[identity.branch, role(identity.frame)[0]].add(identity.frame)
    groups = {key: {frame: g[0] for g in temporal_groups(frames) for frame in g} for key, frames in frame_sets.items()}
    for row in rows:
        identity = Identity(**row['identity'])
        branch_role = identity.branch, role(identity.frame)[0]
        for stratum in row['strata']:
            grouped[*branch_role, stratum, row['kind'], row['metric']].append(row)
    comparisons, cache = {}, {}
    for key, items in sorted(grouped.items()):
        branch, window, stratum, kind, metric = key
        required = {Identity(**r['identity']).key() for r in items}
        eligible, missing = {}, {}
        for method in methods:
            selected = [r for r in items if r['method'] == method]
            identities = [Identity(**r['identity']).key() for r in selected]
            if len(identities) != len(set(identities)):
                raise ValueError('duplicate scored method/image/metric context')
            bad = [r for r in selected if r['status'] != 'complete']
            if set(identities) != required or bad:
                missing[method] = dict(status='unverified', reason='incomplete or ineligible common scored item domain',
                    missing_identities=sorted(required-set(identities)), reasons=sorted({r.get('reason') or 'unavailable' for r in bad}))
                continue
            pooled = {}
            for row in selected:
                identity = Identity(**row['identity'])
                group = identity.camera, groups[branch, window][identity.frame]
                target = pooled.setdefault(group, {f: 0 for f in row['counts']})
                for field, value in row['counts'].items():
                    target[field] += value
            if pooled:
                eligible[method] = pooled
            else:
                missing[method] = dict(status='unverified', reason='no scored items in this stratum')
        report = balanced_statistics(eligible, kind, resamples=resamples, draw_cache=cache)
        report.update(ineligible=missing, evidence_kinds=sorted({r['evidence_kind'] for r in items}),
                      scored_contexts_per_method={m: sum(r['method'] == m and r['status'] == 'complete' for r in items) for m in methods})
        comparisons['/'.join(key)] = report
    # Every prescribed stratum is visible even when the reference contains no
    # verified example; missing strata are not zero-valued quality measurements.
    for branch_role in frame_sets:
        for stratum in STRATA:
            prefix = '/'.join((*branch_role, stratum))
            if not any(k.startswith(prefix + '/') for k in comparisons):
                comparisons[prefix] = dict(status='unverified', reason='no reviewed/eligible examples of this stratum', scores={})
    return comparisons


def _index_results(records, config, *, component=None):
    from .diagnostics import rows_by_identity
    result = {}
    failures = []
    for record in records:
        if record is None:
            failures.append('result file unavailable')
            continue
        if 'path' not in record:
            failures.append(record.get('reason', 'result unavailable'))
            continue
        document = _document(record)
        if document.get('status') != 'complete':
            failures.append(document.get('reason', 'component did not complete'))
            continue
        if component is not None and document.get('component') != component:
            raise ValueError('component result assigned to another method')
        indexed = rows_by_identity(document, config)
        if set(indexed) & set(result):
            raise ValueError('component result files overlap prediction identities')
        result.update(indexed)
    return result, failures


def assemble_final_static(request, output, config, inputs, semantic_results, motion_results):
    """Assemble every primary static output once from frozen S/M artifacts.

    This is derived component output, independent of annotation availability.
    The M0 comparison shares the S0/M0 assembly; it is not serialized twice.
    Reconstruction uses both changing masks from the same explicit tracker pair.
    """
    import cv2
    output = safe_path(output)
    compositions = {**{f'S{i}': (f'S{i}', 'M0') for i in range(5)},
                    'M1': ('S0', 'M1'), 'M2': ('S0', 'M2')}
    expected = output_identities(config, 'calibration') + output_identities(config, 'reconstruction')
    expected_keys = {i.key() for i in expected}
    if len(expected_keys) != len(expected):
        raise ValueError('final static output allocation contains duplicate identities')
    for indexed in [*semantic_results.values(), *motion_results.values()]:
        if set(indexed) - expected_keys:
            raise ValueError('unallocated component identity in final static assembly')
    sources = {Identity(**row['identity']).key(): row for row in inputs['rgb']}
    if len(sources) != len(inputs['rgb']):
        raise ValueError('duplicate source RGB identity in final static assembly')
    totals = {method: dict(expected=len(expected), generated=0, unavailable=0) for method in compositions}
    rows, started = [], time.monotonic()

    def source_for(row):
        identity = Identity(**row['identity'])
        unique = Identity(identity.branch, identity.camera, identity.frame).key()
        if unique not in sources:
            raise ValueError('final static component source RGB is absent from frozen inputs')
        source = sources[unique]
        if row.get('source_rgb_sha256') != source['rgb']['sha256'] or row.get('valid') != source['valid']:
            raise ValueError('final static component changed its source RGB/valid footprint')
        validate_grid(row, source['K'], source['grid'])
        return source

    for identity in expected:
        key = identity.key()
        changing_masks, changing_sources, labels = {}, {}, {}
        motion_keys = [key]
        if identity.branch == 'reconstruction':
            motion_keys = [Identity(identity.branch, identity.camera, frame, identity.pair_start).key()
                           for frame in (identity.pair_start, identity.pair_start + 1)]
        for method, (segmentation_method, motion_method) in compositions.items():
            prediction = semantic_results.get(segmentation_method, {}).get(key)
            changes = motion_results.get(motion_method, {})
            row = dict(method=method, components=[segmentation_method, motion_method], identity=identity.record())
            if prediction is None or any(k not in changes for k in motion_keys):
                row.update(status='unverified', reason='complete segmentation or same-pair changing-mask sources unavailable')
                totals[method]['unavailable'] += 1
                rows.append(row)
                continue
            source = source_for(prediction)
            valid = load_array(source['valid'])
            if segmentation_method not in labels:
                labels[segmentation_method] = load_array(prediction['instances'])
                validate_instances(labels[segmentation_method], prediction['semantics'], valid)
            if motion_method not in changing_masks:
                masks, provenance = [], []
                for motion_key in motion_keys:
                    change_row = changes[motion_key]
                    change_source = source_for(change_row)
                    mask = load_array(change_row['changing'])
                    if mask.dtype != np.bool_ or mask.shape != valid.shape:
                        raise ValueError('final static changing mask has the wrong dtype/grid')
                    validate_grid(change_row, source['K'], source['grid'])
                    masks.append(mask)
                    provenance.append(dict(identity=change_row['identity'], changing=change_row['changing'],
                        source_rgb_sha256=change_source['rgb']['sha256'], valid=change_source['valid'],
                        row_sha256=object_hash(change_row)))
                changing_masks[motion_method] = np.logical_or.reduce(masks)
                changing_sources[motion_method] = provenance
            mask = (valid & (labels[segmentation_method] == 0) & ~changing_masks[motion_method]).astype(np.uint8) * 255
            validate_static(mask, valid)
            path = output / 'final-static' / method / (identity.key() + '.png')
            path.parent.mkdir(parents=True, exist_ok=True)
            success, encoded = cv2.imencode('.png', mask, [cv2.IMWRITE_PNG_COMPRESSION, 3])
            if not success:
                raise ValueError('final static PNG serialization failed')
            with path.open('xb') as stream:
                stream.write(encoded.tobytes())
            segmentation_parent = request['segmentation'][segmentation_method][identity.branch]
            motion_parent = request['motion'][motion_method]
            row.update(status='complete', final_static=file_record(path), source_rgb=source['rgb'],
                source_rgb_sha256=source['rgb']['sha256'], K=source['K'], grid=source['grid'], valid=source['valid'],
                usable_pixels=int((mask > 0).sum()),
                segmentation=dict(component=segmentation_method, result=segmentation_parent,
                    instances=prediction['instances'], semantics_sha256=object_hash(prediction['semantics']),
                    row_sha256=object_hash(prediction)),
                motion=dict(component=motion_method, result=motion_parent, rows=changing_sources[motion_method]))
            totals[method]['generated'] += 1
            rows.append(row)
    generated = sum(r['generated'] for r in totals.values())
    manifest = dict(schema='vipe-benchmark-final-static-masks/v1', status='complete',
        availability='complete' if generated == len(expected) * len(compositions) else 'partial',
        evidence_kind='derived-component-output', human_ground_truth=False,
        formula='255 * valid * (instances == 0) * not(pair-union changing); 0 elsewhere',
        pair_policy='reconstruction unions both changing outputs in the same explicit pair; calibration uses its own changing output',
        inputs=request['inputs'], expected_rows=len(expected) * len(compositions), generated_rows=generated,
        unavailable_rows=len(rows) - generated, methods=totals, rows=rows,
        aliases=dict(M0='S0'), alias_policy='M0 with S0 is the same saved assembly as S0 with M0; no duplicate PNG',
        annotation_independent=True, assembly_wall_seconds=time.monotonic() - started)
    write_json(output / 'final-static-masks.json', manifest)
    return manifest


def _missing_image(annotation, proxy, reason):
    strata, unknown = _strata(annotation)
    required = [('pixel', m) for m in ('person', 'basketball', 'player', 'other-person', 'changing', 'usable_static')]
    required += [('boundary', m) for m in ('person', 'basketball', 'changing', 'usable_static', 'semantic_foreground')]
    required += [('instance', m) for m in ('person', 'basketball')]
    required += [('role_instance', m) for m in ('player', 'other-person')]
    required += [('tiny_ball', 'basketball')]
    required += [('fraction', m) for m in ('foreground_leakage', 'retained_static_area', 'predicted_static_area', 'retained_static_features')]
    if annotation['identity']['branch'] == 'calibration':
        required += [('fraction', m) for m in ('automatic_sift_retention', 'automatic_sift_grid_retention', 'accepted_map_observation_retention')]
    return [dict(kind=kind, metric=metric, counts=None, status='unverified', reason=reason, strata=strata,
                 unknown_strata=unknown, evidence_kind='model-assisted-proxy' if proxy else 'reviewed-annotation') for kind, metric in required]


def segmentation_control(baseline_rows, candidate_rows):
    """S1/S0 output/processor differences, without treating S0 as annotation."""
    fields = ('detector_rgb', 'detector_raw_token_logits', 'detector_raw_boxes_cxcywh',
              'detector_selected_boxes_xyxy', 'detector_selected_scores')
    result = []
    for key in sorted(set(baseline_rows) | set(candidate_rows)):
        a, b = baseline_rows.get(key), candidate_rows.get(key)
        if a is None or b is None:
            result.append(dict(identity=(a or b)['identity'], status='unverified', reason='matching complete S0/S1 output unavailable'))
            continue
        if a['identity'] != b['identity'] or a.get('source_rgb_sha256') != b.get('source_rgb_sha256') or a['K'] != b['K'] or a['grid'] != b['grid']:
            raise ValueError('standalone segmentation control requires the same source image/grid')
        pa, pb = load_array(a['instances']), load_array(b['instances'])
        if pa.shape != pb.shape or not np.array_equal(pa < 0, pb < 0):
            raise ValueError('standalone control valid footprints differ')
        valid = pa >= 0
        row = dict(identity=a['identity'], status='complete', compared_valid_pixels=int(valid.sum()),
                   instance_id_pixel_disagreements=int(((pa != pb) & valid).sum()),
                   semantic_union_disagreements={s: int(((_union(pa, a['semantics'], s) != _union(pb, b['semantics'], s)) & valid).sum())
                                                for s in ('person', 'basketball')},
                   primary=a['instances'], standalone=b['instances'], intermediate_arrays={})
        metadata0, metadata1 = a.get('metadata', {}), b.get('metadata', {})
        row['processors'] = dict(S0={k: metadata0.get(k) for k in ('actual_processed_shape', 'detector_preprocess', 'phrase_policy', 'merge', 'native_phrases')},
                                 S1={k: metadata1.get(k) for k in ('detector', 'merge', 'detections')})
        keyframe = a['identity'].get('pair_start') in (None, a['identity']['frame'])
        if not keyframe:
            row['intermediate_arrays'] = dict(status='not-applicable', reason='successor propagates keyframe state; no new detector forward pass',
                S0_source_frame=metadata0.get('diagnostics_source_frame'), S1_source_frame=metadata1.get('diagnostics_source_frame'))
        elif not a.get('diagnostics') or not b.get('diagnostics'):
            row['intermediate_arrays'] = dict(status='unverified', reason='actual S0/S1 numeric intermediate artifacts unavailable')
        else:
            with load_array(a['diagnostics']) as da, load_array(b['diagnostics']) as db:
                for field in fields:
                    if field not in da.files or field not in db.files:
                        row['intermediate_arrays'][field] = dict(status='unverified', reason='one or both native arrays absent')
                        continue
                    x, y = da[field], db[field]
                    record = dict(S0_shape=list(x.shape), S1_shape=list(y.shape), S0_dtype=str(x.dtype), S1_dtype=str(y.dtype))
                    if x.shape != y.shape:
                        record.update(status='unverified', reason='native grids/query counts differ; no interpolation or guessed association added')
                    elif field.startswith('detector_selected'):
                        # Detection order/phrase policy can change. Expose native
                        # rows without guessing an equivalence between boxes.
                        record.update(status='recorded', S0=x.tolist(), S1=y.tolist(),
                                      interpretation='native detection order; no inferred cross-implementation box association')
                    else:
                        good = np.isfinite(x) & np.isfinite(y)
                        difference = y[good].astype(np.float64)-x[good].astype(np.float64)
                        record.update(status='complete', compared_elements=int(good.sum()),
                            S0_nonfinite=int((~np.isfinite(x)).sum()), S1_nonfinite=int((~np.isfinite(y)).sum()),
                            mean_abs_difference=float(np.abs(difference).mean()) if len(difference) else None,
                            max_abs_difference=float(np.abs(difference).max()) if len(difference) else None)
                    row['intermediate_arrays'][field] = record
            row['intermediate_sources'] = dict(S0=a['diagnostics'], S1=b['diagnostics'])
        result.append(row)
    return dict(schema='vipe-benchmark-segmentation-control/v1', status='complete' if result else 'unverified', rows=result,
                reason=None if result else 'no complete source outputs available',
                interpretation='implementation/output differences only; S0 is a comparator, not ground truth; numeric local IDs are arbitrary')


def mask_stage(request, output, config):
    inputs, annotations = _document(request['inputs']), _document(request['annotations'])
    if annotations.get('schema') not in ('vipe-benchmark-annotations/v1', PROXY_SCHEMA):
        raise ValueError('unknown annotation schema cannot be assumed to be human truth')
    proxy = annotations.get('schema') == PROXY_SCHEMA
    if proxy and (annotations.get('evidence_kind') != 'model-assisted-proxy' or annotations.get('human_ground_truth') is not False):
        raise ValueError('automated labels cannot claim human ground truth')
    if annotations.get('status') not in ('reviewed', 'complete', 'reviewed-adjudicated', 'reviewed-proxy'):
        raise ValueError('annotation import/review must finish before scoring')
    if proxy:
        if not request.get('amendment'):
            raise ValueError('proxy scoring requires the saved user-directed amendment')
        policy = _document(request['amendment'])
        if policy.get('schema') != 'vipe-benchmark-automated-annotation-policy/v1' or policy.get('human_ground_truth') is not False:
            raise ValueError('invalid proxy authorization policy')
        if annotations.get('policy') != request['amendment']:
            raise ValueError('annotations and scoring must bind the same frozen amendment')
    expected = {i.key() for i in annotation_identities(config)}
    annotated = {Identity(**r['identity']).key(): r for r in annotations['images']}
    if set(annotated) != expected or len(annotated) != len(annotations['images']):
        raise ValueError('all 232 unique frozen annotation images are required')
    semantic_class_presence = dict(person=False, basketball=False)
    for row in annotations['images']:
        identity = Identity(**row['identity'])
        if identity.branch == 'calibration' and role(identity.frame)[0] == 'selection':
            with load_array(row['final_layers']) as layers:
                domain = layers['valid'] & ~layers['ignored']
                for semantic, eligibility in (('person', 'person_union'), ('basketball', 'basketball')):
                    if _eligibility(row, eligibility, proxy=proxy):
                        semantic_class_presence[semantic] |= bool((_union(layers['instances'], row['instances'], semantic) & domain).any())
    rgb = {Identity(**r['identity']).key(): r for r in inputs['rgb']}
    map_data = _document(inputs['map'])
    semantic_results, motion_results, failures = {}, {}, {}
    for i in range(5):
        method = f'S{i}'
        branches = request.get('segmentation', {}).get(method, {})
        semantic_results[method], failures[method] = _index_results(
            [branches.get('calibration'), branches.get('reconstruction')], config, component=method)
    for i in range(3):
        method = f'M{i}'
        motion_results[method], failures[method] = _index_results([request.get('motion', {}).get(method)], config, component=method)
    assemble_final_static(request, output, config, inputs, semantic_results, motion_results)
    methods = [f'S{i}' for i in range(5)] + [f'M{i}' for i in range(3)]
    pairs = {(r['camera'], r['pair_start']): r for r in annotations['pairs']}
    expected_contexts = [Identity(**r['identity']) for r in annotations['images'] if r['identity']['branch'] == 'calibration']
    expected_contexts += [Identity('reconstruction', camera, frame, start) for camera in config['diagnostic_cameras']
                         for start in config['pair_starts'] for frame in (start, start+1)]
    raw, count_images = [], set()
    for method in methods:
        seg_method, motion_method = (method, 'M0') if method.startswith('S') else ('S0', method)
        predictions, changes = semantic_results[seg_method], motion_results[motion_method]
        pair_cache, scored_pairs = {}, set()
        for identity in sorted(expected_contexts, key=lambda i: i.key()):
            key = identity.key()
            unique = Identity(identity.branch, identity.camera, identity.frame).key()
            annotation, source = annotated[unique], rgb[unique]
            if key not in predictions or key not in changes:
                raw.extend(dict(r, method=method, identity=identity.record()) for r in
                           _missing_image(annotation, proxy, 'segmentation or fixed motion output missing for this required context'))
                continue
            row = predictions[key]
            for candidate in (row, changes[key]):
                if candidate.get('source_rgb_sha256', candidate.get('rgb_sha256')) != source['rgb']['sha256']:
                    raise ValueError('scored output does not bind the frozen source RGB')
                validate_grid(candidate, source['K'], source['grid'])
            for field in ('rgb', 'K', 'grid', 'valid'):
                if annotation[field] != source[field]:
                    raise ValueError('annotation and prediction source coordinates/provenance differ')
            with load_array(annotation['final_layers']) as archive:
                layers = {k: archive[k] for k in archive.files}
            valid = load_array(source['valid'])
            if not np.array_equal(valid, layers['valid']):
                raise ValueError('annotation footprint changed')
            labels, changing = load_array(row['instances']), load_array(changes[key]['changing'])
            if identity.branch == 'reconstruction':
                other = Identity(identity.branch, identity.camera,
                    identity.pair_start + (identity.frame == identity.pair_start), identity.pair_start).key()
                # Pair-static evidence uses the union for both members. The
                # semantic prediction still has its full tracker-pair identity.
                if other not in changes:
                    raw.extend(dict(r, method=method, identity=identity.record()) for r in
                               _missing_image(annotation, proxy, 'other pair member motion output missing'))
                    continue
                changing = changing | load_array(changes[other]['changing'])
            sift = load_array(source['sift']) if source.get('sift') else None
            observations = [r['uv'] for r in map_data['observations'] if r['camera'] == identity.camera] if identity.branch == 'calibration' else None
            scored, _ = score_image(labels, row['semantics'], changing, annotation, layers,
                                    proxy=proxy, sift=sift, observations=observations)
            for statistic in scored:
                raw.append(dict(statistic, method=method, identity=identity.record()))
            count_images.add(unique)
            if identity.branch == 'reconstruction':
                pair_key = identity.camera, identity.pair_start
                pair_cache.setdefault(pair_key, {})[identity.frame] = (dict(labels=labels, semantics=row['semantics']), annotation, layers)
                if len(pair_cache[pair_key]) == 2:
                    first, second = (pair_cache[pair_key][f] for f in (identity.pair_start, identity.pair_start+1))
                    temporal = score_pair(first[0], second[0], first[1], second[1], pairs[pair_key]['associations'], first[2], second[2], proxy=proxy)
                    start = Identity(identity.branch, identity.camera, identity.pair_start, identity.pair_start)
                    raw.extend(dict(r, method=method, identity=start.record()) for r in temporal)
                    scored_pairs.add(pair_key)
                    del pair_cache[pair_key]
        for pair_key, pair_row in pairs.items():
            if pair_key in scored_pairs:
                continue
            camera, frame = pair_key
            identity = Identity('reconstruction', camera, frame, frame)
            annotation = annotated[Identity('reconstruction', camera, frame).key()]
            strata, unknown = _strata(annotation)
            raw.extend(dict(kind='temporal', metric=semantic, status='unverified', counts=None,
                reason='one or both required pair predictions unavailable', method=method, identity=identity.record(),
                strata=strata, unknown_strata=unknown, evidence_kind='model-assisted-proxy' if proxy else 'reviewed-annotation')
                for semantic in ('person', 'basketball'))
    write_json(output / 'raw-counts.json', dict(schema='vipe-benchmark-raw-counts/v1', rows=raw, source_request=request))
    comparisons = aggregate_rows(raw, methods)
    write_json(output / 'segmentation-control.json', segmentation_control(semantic_results['S0'], semantic_results['S1']))
    result = dict(schema='vipe-benchmark-mask-metrics/v1', status='complete', comparisons=comparisons,
                  evidence_kind='model-assisted-proxy' if proxy else 'reviewed-annotation', human_ground_truth=not proxy,
                  annotations=request['annotations'], amendment=request.get('amendment'), raw_counts=file_record(output/'raw-counts.json'),
                  generated_primary_mask_rows=sum(len(v) for v in semantic_results.values()),
                  generated_primary_mask_rows_scope='complete validated component results; incomplete job output counts remain in the ledger',
                  scored_unique_annotation_images=len(count_images), expected_unique_annotation_images=232,
                  generated_primary_mask_ceiling=6750, methods=methods, component_failures=failures,
                  semantic_class_presence=semantic_class_presence,
                  segmentation_control=file_record(output / 'segmentation-control.json'),
                  final_static_masks=file_record(output / 'final-static-masks.json'),
                  statement='Only matching frozen annotation identities are scored; paired tracker contexts are retained and grouped.',
                  strata_scope='full images with an eligible reviewed tag; unknown tags excluded',
                  physical_accuracy='unverified')
    write_json(output / 'mask-metrics.json', result)
    return result


def scale_status(stages, component):
    """Passing current file evidence only; absent cameras/checks stay explicit."""
    result = dict(component=component, fit='unverified', check='unverified', physical_accuracy='unverified', reasons=[])
    documents = {}
    for stage in ('fit', 'check'):
        record = stages.get(stage)
        if not record or 'path' not in record:
            result['reasons'].append(f'{stage}: ' + (record or {}).get('reason', 'no current evidence'))
            continue
        document = _document(record)
        documents[stage] = document
        result[stage] = document.get('status', 'unverified')
        result[stage+'_hash'] = record['sha256']
        result[stage+'_record'] = record
        if document.get('role') != ('fit' if stage == 'fit' else 'selection'):
            result[stage] = 'unverified'
            result['reasons'].append(f'{stage}: wrong scale role')
        if document.get('scale_protocol_sha256') != digest(ROOT / 'configs/basketball-rev2/scale.json'):
            result[stage] = 'unverified'
            result['reasons'].append(f'{stage}: missing/changed scientific gate hash')
        provenance = document.get('provenance', {})
        if provenance.get('component', provenance.get('component_id')) != component or not provenance.get('component_sha256'):
            result[stage] = 'unverified'
            result['reasons'].append(f'{stage}: candidate provenance missing or mismatched')
    if 'check' in documents:
        if documents['check'].get('frozen_fit') != stages.get('fit') or (
                documents['check'].get('provenance', {}).get('component_sha256') !=
                documents.get('fit', {}).get('provenance', {}).get('component_sha256')):
            result['check'] = 'unverified'
            result['reasons'].append('check does not bind this unchanged candidate fit')
    result['eligible'] = result['fit'] == result['check'] == 'passed'
    return result


def compare_depth(first, second, sample_row):
    """Matched-grid depth and frozen sparse per-camera scale-ratio differences.

    Used for R-D and D1/D0 controls. This computes descriptive ratios only; it
    neither evaluates an extra full rig nor refits/changes the frozen estimate.
    """
    from .contracts import depth as validate_depth, sample_depth
    if first['identity'] != second['identity'] or first['identity'] != sample_row['identity']:
        raise ValueError('depth comparison requires exactly matching frozen image identities')
    for row in (first, second):
        if row.get('source_rgb_sha256', row.get('rgb_sha256')) != sample_row['rgb']['sha256']:
            raise ValueError('depth control source RGB changed')
        validate_grid(row, sample_row['K'], sample_row['grid'])
    with load_array(first['depth']) as a, load_array(second['depth']) as b, load_array(sample_row['samples']) as geometry:
        image_valid = geometry['valid'] > 0
        for archive in (a, b):
            validate_depth(archive['depth'], archive['valid'], image_valid, shape=image_valid.shape)
        good = a['valid'] & b['valid']
        differences = b['depth'][good].astype(np.float64) - a['depth'][good]
        z0, v0 = sample_depth(a['depth'], a['valid'], geometry['uv'])
        z1, v1 = sample_depth(b['depth'], b['valid'], geometry['uv'])
        map_valid = np.isfinite(geometry['camera_z']) & (geometry['camera_z'] > 0)
        v0, v1 = v0 & map_valid, v1 & map_valid
        paired = v0 & v1
        ratios = [values[valid] / geometry['camera_z'][valid] for values, valid in ((z0, v0), (z1, v1))]
        medians = [float(np.exp(np.median(np.log(r)))) if len(r) else None for r in ratios]
        paired_difference = (z1[paired] - z0[paired]) / geometry['camera_z'][paired]
        return dict(status='complete', identity=first['identity'], primary_depth=first['depth'], compared_depth=second['depth'],
            validity_disagreement=int((a['valid'] != b['valid']).sum()), compared_pixels=int(good.sum()),
            mean_abs_depth=float(np.abs(differences).mean()) if len(differences) else None,
            max_abs_depth=float(np.abs(differences).max()) if len(differences) else None,
            mean_signed_depth_difference=float(differences.mean()) if len(differences) else None,
            sparse_samples=sample_row['samples'], sparse_primary_valid=int(v0.sum()), sparse_compared_valid=int(v1.sum()),
            sparse_common_valid=int(paired.sum()), sparse_validity_disagreement=int((v0 != v1).sum()),
            primary_camera_scale_ratio=medians[0], compared_camera_scale_ratio=medians[1],
            camera_scale_ratio_difference=medians[1]-medians[0] if all(v is not None for v in medians) else None,
            camera_scale_ratio_relative_difference=medians[1]/medians[0]-1 if all(v is not None for v in medians) else None,
            mean_abs_paired_sample_scale_ratio_difference=float(np.abs(paired_difference).mean()) if len(paired_difference) else None,
            depth_units='camera-z metres', physical_accuracy='unverified', full_rig_scale_evaluations=0,
            interpretation='candidate validity affects its own support; shared samples remain frozen')


def compare_depth_control(baseline, candidate, inputs):
    """D1/D0 matched RGB comparison with all required cameras accounted for."""
    baseline, candidate, inputs = _document(baseline), _document(candidate), _document(inputs)
    if baseline.get('component') != 'D0' or candidate.get('component') != 'D1':
        raise ValueError('standalone depth control must compare D0 with D1')
    base = {Identity(**r['identity']).key(): r for r in baseline.get('rows', [])}
    new = {Identity(**r['identity']).key(): r for r in candidate.get('rows', [])}
    frames = {r['identity']['frame'] for r in baseline.get('rows', []) + candidate.get('rows', [])}
    if len(frames) != 1 or not frames <= {100, 175}:
        raise ValueError('depth control requires one matching prescribed fit/check frame')
    expected = [r for r in inputs['depth'] if r['identity']['frame'] in frames]
    result = []
    for row in sorted(expected, key=lambda r: r['identity']['camera']):
        key = Identity(**row['identity']).key()
        if key not in base or key not in new or baseline.get('status') != 'complete' or candidate.get('status') != 'complete':
            result.append(dict(status='unverified', identity=row['identity'], reason='matching complete D0/D1 depth output unavailable'))
        else:
            result.append(compare_depth(base[key], new[key], row))
    return dict(status='complete', rows=result, metric_accuracy='unverified', full_rig_scale_evaluations=0,
                interpretation='standalone dependency-removal control; ratios are not extra fits or replacement selection')


def _estimate(metrics, kind, metric, score, method):
    report = metrics['comparisons'].get(f'calibration/selection/all/{kind}/{metric}', {})
    return report.get('scores', {}).get(score, {}).get('estimates', {}).get(method)


def geometry_metrics(records, config, *, combined_slots=None):
    """Consume every isolated/combined slot, retaining partial contexts visibly."""
    from .diagnostics import COARSE_ARMS, REGIONS, contexts
    names = list(COARSE_ARMS) if combined_slots is None else ['C0', 'C1', 'C2', 'C3']
    slots, rows = {}, []
    expected = contexts(config)
    for name in names:
        record = records.get(name)
        doc = None
        if record and 'path' in record:
            doc = _document(record)
            reuse = doc.get('job_id') != name
            if reuse and (combined_slots is None or doc.get('job_id') not in combined_slots or
                    doc.get('components') != combined_slots[name]['components'] or
                    combined_slots[doc['job_id']]['components'] != combined_slots[name]['components']):
                raise ValueError('geometry evidence belongs to another arm without identical frozen composition')
            slots[name] = dict(status=doc.get('status', 'unverified'), result=record, summary=doc.get('summary'),
                               reason=doc.get('reason'), reused_from=doc.get('job_id') if reuse else None)
        else:
            slots[name] = dict(status='unverified', reason=(record or {}).get('reason', 'geometry result unavailable'))
        by_context = {(r['pair_start'], r['reference']): r for r in (doc or {}).get('contexts', [])}
        if len(by_context) != len((doc or {}).get('contexts', [])) or set(by_context)-set(expected):
            raise ValueError('duplicate or extra diagnostic geometry context')
        for frame, camera in expected:
            context = by_context.get((frame, camera), {})
            valid = context.get('status') == 'complete'
            identity = Identity('reconstruction', camera, frame, frame)
            for region in REGIONS:
                values = context.get('classes', {}).get(region, {})
                statistics = {'accepted_'+region: ('accepted', 'attempted'),
                              'velocity_valid_'+region: ('velocity_valid', 'accepted')}
                if region == 'static':
                    del statistics['velocity_valid_static']
                for metric, (numerator, denominator) in statistics.items():
                    counts = dict(numerator=values[numerator], denominator=values[denominator]) if valid and numerator in values and denominator in values else None
                    rows.append(dict(method=name, identity=identity.record(), kind='fraction', metric=metric,
                        status='complete' if counts is not None else 'unverified', counts=counts, strata=['all'],
                        reason=None if counts is not None else context.get('reason', 'geometry context/metric unavailable'), evidence_kind='diagnostic-geometry'))
                counts = dict(numerator=values['occupied_reference_cells'], denominator=1) if valid and 'occupied_reference_cells' in values else None
                rows.append(dict(method=name, identity=identity.record(), kind='fraction', metric='reference_cells_'+region,
                    status='complete' if counts is not None else 'unverified', counts=counts, strata=['all'],
                    reason=None if counts is not None else 'accepted reference-cell evidence unavailable', evidence_kind='diagnostic-geometry'))
            counts = dict(numerator=context['matching_wall_seconds'], denominator=1) if valid and 'matching_wall_seconds' in context else None
            rows.append(dict(method=name, identity=identity.record(), kind='fraction', metric='matching_wall_seconds_per_context',
                status='complete' if counts is not None else 'unverified', counts=counts, strata=['all'],
                reason=None if counts is not None else 'matching timing unavailable', evidence_kind='measured-resource-cost'))
    return dict(schema='vipe-benchmark-geometry-metrics/v1', status='complete', slots=slots,
                comparisons=aggregate_rows(rows, names), physical_accuracy='unverified',
                interpretation='acceptance, support and coverage are diagnostic geometry, not verified physical correctness')


def finalist_stage(request, output, config):
    masks = _document(request['mask_metrics'])
    if masks.get('status') != 'complete':
        raise ValueError('mask metrics must freeze before finalist selection')
    s_rows, m_rows = {}, {}
    for method in (f'S{i}' for i in range(1, 5)):
        # Boundary tie evidence is the semantic foreground union's equal-camera
        # boundary F1; it is not fabricated by averaging absent semantic classes.
        values = dict(person_dice=_estimate(masks, 'pixel', 'person', 'dice', method),
                      ball_dice=_estimate(masks, 'pixel', 'basketball', 'dice', method),
                      leakage=_estimate(masks, 'fraction', 'foreground_leakage', 'fraction', method),
                      retained_static_features=_estimate(masks, 'fraction', 'retained_static_features', 'fraction', method),
                      boundary_f1=_estimate(masks, 'boundary', 'semantic_foreground', 'f1', method))
        s_rows[method] = dict(status='complete', **values)
    for method in (f'M{i}' for i in range(3)):
        m_rows[method] = dict(status='complete', static_dice=_estimate(masks, 'pixel', 'usable_static', 'dice', method),
            leakage=_estimate(masks, 'fraction', 'foreground_leakage', 'fraction', method),
            retained_static_features=_estimate(masks, 'fraction', 'retained_static_features', 'fraction', method))
    # Absence is an annotation property. Failed candidate predictions cannot
    # manufacture the original protocol's missing-semantic-class default.
    missing_class = any(masks.get('semantic_class_presence', {}).get(k) is False for k in ('person', 'basketball'))
    finalists = dict(S=select('S', s_rows, missing_semantic_class=missing_class), M=select('M', m_rows))
    if masks.get('evidence_kind') == 'model-assisted-proxy':
        amendment = request.get('amendment', masks.get('amendment'))
        if not amendment:
            raise ValueError('proxy defaults require explicit saved authorization')
        policy = _document(amendment)
        if policy.get('selection', {}).get('segmentation') != 'original tuple where all required proxy terms are defined on common frozen domain; otherwise explicit S2 unverified baseline default' or (
                policy.get('selection', {}).get('motion') != 'M0 predeclared baseline default if independent changing/static evidence is unavailable, never labeled a measured winner'):
            raise ValueError('unexpected policy; default rules require a recorded amendment')
        if not any(all(v is not None for k, v in row.items() if k != 'status') for row in s_rows.values()):
            finalists['S'] = dict(status='unverified', selected='S2', ranking=[], ineligible=finalists['S'].get('ineligible', {}),
                reason='authorized S2 baseline default: required proxy tuple terms unavailable', amendment=amendment)
        if not any(row['static_dice'] is not None for row in m_rows.values()):
            finalists['M'] = dict(status='unverified', selected='M0', ranking=[],
                reason='authorized M0 baseline default: independent changing/static evidence unavailable', amendment=amendment)
    n_rows, geometry = {}, {}
    for i in range(3):
        job, method = ('G-S0' if i == 0 else f'G-N{i}'), f'N{i}'
        record = request.get('geometry', {}).get(job)
        if not record or 'path' not in record:
            n_rows[method] = dict(status='blocked', reason=(record or {}).get('reason', 'coarse geometry evidence unavailable'))
            continue
        doc = _document(record)
        if doc.get('job_id') != job:
            raise ValueError('neighbor ranking received the wrong isolated geometry arm')
        geometry[job] = record
        n_rows[method] = dict(doc.get('summary', {}), status=doc.get('status', 'unverified'), reason=doc.get('reason', 'incomplete geometry'))
        if n_rows[method].get('expected_contexts') != 64 or n_rows[method].get('full_image_matches') != 192:
            n_rows[method].update(status='blocked', reason='full 64-context/192-edge coarse diagnostic set unavailable')
    finalists['N'] = select('N', n_rows)
    if config:
        all_geometry = geometry_metrics(request.get('geometry', {}), config)
        write_json(output / 'geometry-metrics.json', all_geometry)
    depth_controls = {}
    for stage in ('fit', 'check'):
        control = request.get('depth_controls', {}).get(stage, {})
        if all(control.get(k) and 'path' in control[k] for k in ('baseline', 'candidate')) and request.get('inputs'):
            depth_controls[stage] = compare_depth_control(control['baseline'], control['candidate'], request['inputs'])
        else:
            depth_controls[stage] = dict(status='unverified', reason='matching complete D0/D1 result records unavailable')
    write_json(output / 'depth-control.json', depth_controls)
    gates = {f'D{i}': scale_status(request.get('scales', {}).get(f'D{i}', {}), f'D{i}') for i in range(5)}
    components = request.get('components', {})
    if 'path' in components:
        components = _document(components)
        components = components.get('components', components)
    result = dict(schema='vipe-benchmark-finalists/v1', status='frozen', finalists=finalists,
                  selection_evidence=dict(S=s_rows, M=m_rows, N=n_rows), depth_gates=gates,
                  combined=combined(finalists, gates, components), mask_metrics=request['mask_metrics'], geometry=geometry,
                  source_request=request, precision='round selection scores to 12 decimals; lower ID breaks final ties',
                  physical_accuracy='unverified', evidence_kind=masks.get('evidence_kind', 'unverified'),
                  depth_control=file_record(output / 'depth-control.json'))
    if config:
        result['isolated_geometry_metrics'] = file_record(output / 'geometry-metrics.json')
    write_json(output / 'finalists.json', result)
    return result


def final_stage(request, output, config):
    frozen = _document(request['finalists'])
    if frozen.get('status') != 'frozen':
        raise ValueError('combined summaries require the immutable finalist checkpoint')
    combined_results = {}
    for slot in ('C0', 'C1', 'C2', 'C3'):
        record = request.get('combined', {}).get(slot)
        eligible = frozen['combined'][slot]
        if not record or 'path' not in record:
            combined_results[slot] = dict(status='blocked' if eligible['status'] != 'eligible' else 'unverified',
                reasons=eligible.get('reasons', []) + [(record or {}).get('reason', 'combined result unavailable')], components=eligible['components'])
            continue
        doc = _document(record)
        reused = doc.get('job_id') != slot
        if doc.get('components') != eligible['components'] or (reused and (
                doc.get('job_id') not in frozen['combined'] or
                frozen['combined'][doc['job_id']]['components'] != eligible['components'])):
            raise ValueError('combined evidence differs from the frozen slot')
        combined_results[slot] = dict(status=doc['status'], result=record, summary=doc.get('summary'), reason=doc.get('reason'),
                                      reused_from=doc.get('job_id') if reused else None)
    repeats = {}
    for repeat in ('R-S', 'R-D', 'R-G'):
        record = request.get('repeats', {}).get(repeat)
        repeats[repeat] = (dict(status='unverified', reason=(record or {}).get('reason', 'repeat comparison unavailable'))
                           if not record or 'path' not in record else dict(result=record, **_document(record)))
    result = dict(schema='vipe-benchmark-final-aggregation/v1', status='complete', finalists=request['finalists'],
                  combined=combined_results, repeats=repeats, mask_metrics=frozen['mask_metrics'],
                  physical_accuracy='unverified', evidence_kind=frozen['evidence_kind'],
                  interpretation='isolated arms measure component effects; combined arms include interactions; repeats do not select methods',
                  scientific_completion='unverified; the separate matrix and success-criteria assessment determines benchmark completion')
    result['isolated_geometry_metrics'] = frozen.get('isolated_geometry_metrics')
    result['depth_control'] = frozen.get('depth_control')
    if config:
        write_json(output / 'combined-geometry-metrics.json', geometry_metrics(request.get('combined', {}), config, combined_slots=frozen['combined']))
        result['combined_geometry_metrics'] = file_record(output / 'combined-geometry-metrics.json')
    write_json(output / 'aggregate-final.json', result)
    return result


def run(request, output, config):
    output = safe_path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = dict(status='incomplete', stage=request['stage'], request_sha256=object_hash(request))
    try:
        operation = {'masks': mask_stage, 'finalists': finalist_stage, 'final': final_stage}[request['stage']]
        evidence = operation(request, output, config)
        artifact = {'masks': 'mask-metrics.json', 'finalists': 'finalists.json', 'final': 'aggregate-final.json'}[request['stage']]
        result.update(status='complete', evidence=file_record(output / artifact), evidence_status=evidence['status'])
        if request['stage'] == 'masks':
            result['final_static_masks'] = evidence['final_static_masks']
        return result
    except BaseException as error:
        result.update(status='failed', reason=f'{type(error).__name__}: {error}')
        raise
    finally:
        result['wall_seconds'] = time.monotonic() - started
        write_json(output / 'result.json', result)
