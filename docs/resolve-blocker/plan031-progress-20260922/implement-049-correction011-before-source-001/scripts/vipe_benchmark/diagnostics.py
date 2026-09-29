"""Pair-aware diagnostic RoMa runner using the unchanged local geometry gates.

Production execution is CUDA-only. The small array functions are independent of
model loading so CPU fixtures can check rejection accounting without launching an
unallocated matcher or changing the production solver/device.
"""
from collections import Counter
import time

import numpy as np

from .access import Identity, RGBLoader, guard, validate_grid
from .config import ROOT, training_cameras
from .contracts import instances, SHAPE
from .files import digest, file_record, load_array, object_hash, read_json, safe_path, verify_record, write_json
from .geometry import consumer_camera, scale_scene

REGIONS = {'static': 0, 'person': 1, 'ball': 2, 'foreground': None}
COARSE_ARMS = {**{f'G-S{i}': [f'S{i}', 'D0', 'M0', 'N0'] for i in range(5)},
              **{f'G-M{i}': ['S0', 'D0', f'M{i}', 'N0'] for i in (1, 2)},
              **{f'G-N{i}': ['S0', 'D0', 'M0', f'N{i}'] for i in (1, 2)}}


def contexts(config, *, repeat=False):
    """Canonical historical loop order: pair start, reference, neighbor rank."""
    return [(20, 1)] if repeat else [(t, c) for t in sorted(config['diagnostic_pair_starts'])
                                    for c in sorted(config['diagnostic_cameras'])]


def _document(record):
    verify_record(record)
    return read_json(record['path'])


def rows_by_identity(result, config, *, branch=None):
    if result.get('status') != 'complete':
        raise ValueError('incomplete component result cannot supply geometry/scoring evidence')
    rows = {}
    for row in result['rows']:
        identity = Identity(**row['identity'])
        guard(identity, config)
        if branch is not None and identity.branch != branch:
            continue
        if identity.key() in rows:
            raise ValueError('duplicate pair-specific component identity')
        rows[identity.key()] = row
    return rows


def scene_freeze(inputs, map_data, *, fit=None, check=None, depth_id='D0'):
    """Derive a diagnostic freeze from the accepted raw map and current gates.

    The historical normalization acts on reference-scale physical coordinates.
    Rebase its linear part when the target scale changes. Depth estimates never
    change rotations, intrinsics, sparse support or map observations.
    """
    reference = inputs['reference_geometry']
    verify_record(reference['freeze'])
    verify_record(reference['normalization_source'])
    source_scale = float(reference['scale'])
    target_scale = source_scale
    parents = {}
    if (fit is None) != (check is None):
        raise ValueError('both current depth stages are required for a combined freeze')
    if fit is not None:
        fitting, checking = _document(fit), _document(check)
        if (fitting.get('status') != 'passed' or fitting.get('role') != 'fit' or
                checking.get('status') != 'passed' or checking.get('role') != 'selection' or
                checking.get('frozen_fit') != fit or
                fitting.get('provenance', {}).get('component_sha256') != checking.get('provenance', {}).get('component_sha256') or
                not fitting.get('provenance', {}).get('component_sha256')):
            raise ValueError('combined scale needs matching current passing fit and frozen check')
        for report in (fitting, checking):
            if report.get('scale_protocol_sha256') != digest(ROOT / 'configs/basketball-rev2/scale.json'):
                raise ValueError('scale scientific gates/provenance changed')
            component = report['provenance'].get('component', report['provenance'].get('component_id'))
            if component != depth_id:
                raise ValueError('scale evidence belongs to another depth component')
        target_scale = float(fitting['scale'])
        # A selection report may also contain a diagnostic window estimate; its
        # frozen fit is authoritative, never that descriptive estimate.
        parents = dict(fit=fit, check=check)
    ids = sorted(map(int, map_data['points']))
    raw = np.asarray([map_data['points'][str(i)] for i in ids], np.float64).reshape(-1, 3)
    if not len(raw) or not np.isfinite(raw).all():
        raise ValueError('scene map must contain finite points')
    cameras = {int(c): dict(camera, t=(np.asarray(camera['t']) * source_scale).tolist(),
                           center=(np.asarray(camera['center']) * source_scale).tolist())
               for c, camera in map_data['cameras'].items()}
    normalization = reference['normalization']
    normalization = normalization['transform'] if isinstance(normalization, dict) else normalization
    xyz, cameras, transform, units = scale_scene(raw * source_scale, cameras, normalization,
                                                source_scale, target_scale)
    maximum_error = 0.
    from .neighbors import _project
    for camera_id, camera in cameras.items():
        before, _ = _project(raw, map_data['cameras'][str(camera_id)])
        after, _ = _project(xyz, camera)
        finite = np.isfinite(before).all(1) & np.isfinite(after).all(1)
        if not finite.any():
            raise ValueError('scene camera has no finite projection-invariance evidence')
        error = float(np.max(np.abs(before[finite] - after[finite])))
        maximum_error = max(maximum_error, error)
        if not np.allclose(before[finite], after[finite], atol=1e-6, rtol=1e-12):
            raise ValueError('scene scaling changed camera projections')
    return dict(schema='vipe-benchmark-diagnostic-scene/v1', status='complete', diagnostic_only=True,
                map=inputs['map'], historical_reference=reference, scale=target_scale,
                depth_component=depth_id, scale_evidence=parents, cameras={str(c): r for c, r in cameras.items()},
                point_ids=ids, points=xyz.tolist(), normalization=transform.tolist(), units=units,
                pixel_convention='OpenCV integer K; add 0.5 exactly once at the RoMa boundary',
                projection_max_abs_error_pixels=maximum_error, physical_accuracy='unverified')


def coverage(uv, region, accepted=None):
    """4x4 reference/candidate coverage, with RoMa centers restored to OpenCV."""
    uv, region = np.asarray(uv), np.asarray(region)
    accepted = np.ones(len(region), bool) if accepted is None else np.asarray(accepted, bool)
    cv = uv - .5
    inside = np.isfinite(cv).all(1) & (cv[:, 0] >= 0) & (cv[:, 0] < 960) & (cv[:, 1] >= 0) & (cv[:, 1] < 540)
    cells = np.floor(np.where(inside[:, None], cv, 0) / [240, 135]).astype(int)
    result = {}
    for name, value in REGIONS.items():
        chosen = inside & accepted & ((region > 0) if value is None else region == value)
        hist = Counter(map(tuple, cells[chosen]))
        result[name] = dict(cells=[list(map(int, c)) for c in sorted(hist)], occupied_cells=len(hist),
                            cell_counts=[dict(cell=list(map(int, c)), points=hist[c]) for c in sorted(hist)])
    return result


def _quantiles(values):
    values = np.asarray(values)
    values = values[np.isfinite(values)]
    return dict(count=len(values), min=float(values.min()) if len(values) else None,
                median=float(np.median(values)) if len(values) else None,
                p95=float(np.quantile(values, .95, method='linear')) if len(values) else None)


def evaluate_edge(xyz, numerical, all_uv, ids, pair, cameras, labels, changing):
    """Apply historical gates unchanged; retain every attempted point's reasons."""
    from basketball_temporal_geometry import geometry_gate, labels_at, project, projection
    xyz, numerical, all_uv = np.asarray(xyz), np.asarray(numerical, bool), np.asarray(all_uv)
    if len(ids) != 4 or len(set(ids)) != 4 or pair not in (1, 2, 3):
        raise ValueError('reference and three distinct supporting cameras are required')
    if xyz.shape != (len(numerical), 3) or all_uv.shape != (4, len(xyz), 2):
        raise ValueError('candidate geometry array shape mismatch')
    P = np.asarray([projection(consumer_camera(cameras[c])) for c in ids])
    centers = np.asarray([cameras[c]['center'] for c in ids])
    geometric, diagnostic = geometry_gate(xyz, all_uv[[0, pair]], P[[0, pair]], centers[[0, pair]])
    sampled_labels = np.asarray([labels_at(labels[c]['labels'], uv) for c, uv in zip(ids, all_uv)])
    semantic = np.full(sampled_labels.shape, -1, np.int8)
    semantic[sampled_labels == 0] = 0
    for k, c in enumerate(ids):
        for label, meta in labels[c]['semantics'].items():
            semantic[k, sampled_labels[k] == int(label)] = {'person': 1, 'basketball': 2}[meta['class']]
    region = semantic[0]
    support = np.zeros(sampled_labels.shape, bool)
    for k in range(4):
        projected, depth = project(xyz, P[k])
        support[k] = np.isfinite(projected).all(1) & (depth > 0)
        support[k] &= np.linalg.norm(projected - all_uv[k], axis=1) <= 2
        support[k] &= (semantic[k] == region) & (sampled_labels[k] >= 0)
    foreground = region > 0
    static_clear = np.ones(len(xyz), bool)
    for k in (0, pair):
        static_clear &= foreground | (labels_at(changing[ids[k]], all_uv[k]) == 0)
    masks = dict(numerical=numerical,
                 finite_positive=np.isfinite(xyz).all(1) & np.isfinite(diagnostic['depth']).all(0) &
                                 (diagnostic['depth'] > 0).all(0),
                 reprojection=np.isfinite(diagnostic['reprojection']).all(0) &
                              (diagnostic['reprojection'] <= 2).all(0),
                 parallax=np.isfinite(diagnostic['angle']) & (diagnostic['angle'] >= 1),
                 reference_neighbor_semantic_support=support[0] & support[pair],
                 foreground_three_camera_support=~foreground | (support.sum(0) >= 3),
                 pair_static_clearance=static_clear)
    good = numerical & geometric & support[0] & support[pair]
    good &= (~foreground | (support.sum(0) >= 3)) & static_clear
    cumulative = np.ones(len(xyz), bool)
    stages = {}
    for name, passed in masks.items():
        rejected = cumulative & ~passed
        cumulative &= passed
        stages[name] = dict(rejected=int(rejected.sum()), remaining=int(cumulative.sum()),
                            rejected_by_class={key: int((rejected & ((region > 0) if value is None else region == value)).sum())
                                               for key, value in REGIONS.items()})
    if not np.array_equal(cumulative, good):
        raise ValueError('diagnostic accounting diverged from historical geometry gate')
    classes = {}
    for name, value in REGIONS.items():
        chosen = (region > 0) if value is None else region == value
        kept = chosen & good
        classes[name] = dict(attempted=int(chosen.sum()), accepted=int(kept.sum()),
                             accepted_fraction=float(kept.sum() / chosen.sum()) if chosen.any() else None,
                             supporting_camera_histogram={str(i): int((kept & (support.sum(0) == i)).sum()) for i in range(5)},
                             parallax_degrees=_quantiles(diagnostic['angle'][kept]))
    record = dict(sampled=len(xyz), accepted=int(good.sum()), invalid_reference_samples=int((region < 0).sum()),
                  stages=stages, classes=classes,
                  reference_coverage=coverage(all_uv[0], region, good),
                  candidate_coverage=coverage(all_uv[pair], region, good),
                  attempted_reference_coverage=coverage(all_uv[0], region),
                  attempted_candidate_coverage=coverage(all_uv[pair], region),
                  attempted_parallax_degrees=_quantiles(diagnostic['angle']))
    arrays = dict(candidate_world_positions=xyz, numerical_valid=numerical, accepted=good,
                  candidate_uv=all_uv, candidate_region=region, candidate_support=support,
                  candidate_instance_labels=sampled_labels, parallax_degrees=diagnostic['angle'],
                  **{f'gate_{k}': v for k, v in masks.items()})
    return arrays, record


class NativeBackend:
    """Pinned CUDA matcher and float32 solver; no reduced-device fallback."""
    def __init__(self, checkout, weights):
        import torch
        from edgs_source import load_roma
        self.torch = torch
        if not torch.cuda.is_available():
            raise PermissionError('CUDA device access unavailable; geometry has no CPU fallback')
        try:
            torch.cuda.init()
        except RuntimeError as error:
            raise PermissionError(f'CUDA driver/device initialization failed: {error}') from error
        torch.manual_seed(0)
        torch.cuda.reset_peak_memory_stats()
        self.peak_observed_device_bytes = 0
        self.model, self.loading = self.measured(lambda: load_roma(safe_path(checkout), safe_path(weights)))

    def measured(self, function):
        torch = self.torch
        torch.cuda.synchronize()
        started = time.monotonic()
        a, b = torch.cuda.Event(enable_timing=True), torch.cuda.Event(enable_timing=True)
        a.record()
        value = function()
        b.record()
        torch.cuda.synchronize()
        elapsed = time.monotonic() - started
        free, total = torch.cuda.mem_get_info()
        self.peak_observed_device_bytes = max(self.peak_observed_device_bytes, total - free)
        return value, dict(wall_seconds=elapsed, cuda_seconds=a.elapsed_time(b) / 1000.)

    def match(self, first, second):
        from PIL import Image
        def call():
            with self.torch.inference_mode():
                warp, confidence = self.model.match(Image.fromarray(first), Image.fromarray(second), device='cuda')
            return warp.cpu().numpy(), confidence.cpu().numpy()
        return self.measured(call)

    def crop(self, warp, probability, images, labels, ids):
        from .geometry import crop_warp
        return self.measured(lambda: crop_warp(self.model, warp, probability, images[ids[0]], images[ids[1]],
                                              labels[ids[0]]['labels'], labels[ids[1]]['labels'],
                                              labels[ids[0]]['semantics'], labels[ids[1]]['semantics']))

    def triangulate(self, P0, P1, uv0, uv1):
        from triangulation import triangulate_points
        def call():
            xyz, numerical = triangulate_points(P0, P1, uv0, uv1, device='cuda', dtype=self.torch.float32)
            return xyz.cpu().numpy(), numerical.cpu().numpy()
        return self.measured(call)

    def resources(self):
        return dict(peak_allocated_bytes=self.torch.cuda.max_memory_allocated(),
                    peak_reserved_bytes=self.torch.cuda.max_memory_reserved(),
                    peak_observed_device_bytes=self.peak_observed_device_bytes,
                    total_device_peak_status='supervisor samples are required; phase-boundary observations are a lower bound')


def _neighbor_rows(document):
    if 'records' in document:
        rows = document['records']
        result = {str(r['reference']): r for r in rows}
        if len(result) != len(rows):
            raise ValueError('duplicate neighbor reference')
        return result
    return document.get('references', document.get('rankings', document.get('neighbors', {})))


def _union_context(edges, frame, reference, neighbors):
    result = dict(pair_start=frame, reference=reference, neighbors=neighbors, status='complete', classes={})
    for name in REGIONS:
        covered, marginal = set(), []
        for edge in edges:
            cells = set(map(tuple, edge['reference_coverage'][name]['cells']))
            marginal.append(dict(other=edge['other'], new_cells=len(cells - covered)))
            covered |= cells
        result['classes'][name] = dict(reference_cells=[list(c) for c in sorted(covered)],
                                       occupied_reference_cells=len(covered), marginal_coverage=marginal,
                                       attempted=sum(e['classes'][name]['attempted'] for e in edges),
                                       accepted=sum(e['classes'][name]['accepted'] for e in edges),
                                       velocity_valid=sum(e['classes'][name].get('velocity_valid', 0) for e in edges))
    result['matching_wall_seconds'] = sum(e['matching']['wall_seconds'] + e.get('cropping', {}).get('wall_seconds', 0) for e in edges)
    return result


def summarize(records, context_rows, expected_contexts):
    complete = [c for c in context_rows if c['status'] == 'complete']
    by_camera = {}
    for camera in sorted({c for _, c in expected_contexts}):
        rows = [r for r in complete if r['reference'] == camera]
        attempted = sum(r['classes']['foreground']['attempted'] for r in rows)
        accepted = sum(r['classes']['foreground']['accepted'] for r in rows)
        by_camera[str(camera)] = dict(contexts=len(rows),
            foreground_reference_cells=float(np.mean([r['classes']['foreground']['occupied_reference_cells'] for r in rows])) if rows else None,
            accepted_foreground_fraction=accepted / attempted if attempted else None,
            attempted_foreground=attempted, accepted_foreground=accepted,
            matching_wall_seconds=sum(r['matching_wall_seconds'] for r in rows))
    means = {k: float(np.mean([r[k] for r in by_camera.values() if r[k] is not None]))
             if any(r[k] is not None for r in by_camera.values()) else None
             for k in ('foreground_reference_cells', 'accepted_foreground_fraction', 'matching_wall_seconds')}
    directed = {(r['pair_start'], r['reference'], r['other']) for r in records}
    reciprocal = sum((t, b, a) in directed for t, a, b in directed)
    return dict(**means, per_camera=by_camera,
                all_references_have_three_neighbors=len(complete) == len(expected_contexts),
                expected_contexts=len(expected_contexts), complete_contexts=len(complete),
                full_image_matches=len(records), crop_matches=sum(r.get('crop_matches', 0) for r in records),
                synchronized_cuda_seconds=sum(sum(r.get(k, {}).get('cuda_seconds', 0.) for k in ('matching', 'cropping', 'triangulation')) for r in records),
                reciprocal_directed_edges=reciprocal, reciprocal_pairs=reciprocal // 2,
                cache_across_arms=False, potential_reciprocal_cache_reuse=reciprocal // 2,
                classes={name: dict(attempted=sum(r['classes'][name]['attempted'] for r in records),
                                    accepted=sum(r['classes'][name]['accepted'] for r in records),
                                    velocity_valid=sum(r['classes'][name].get('velocity_valid', 0) for r in records))
                         for name in REGIONS},
                neighbor_failures=[r for r in context_rows if r['status'] != 'complete'])


def compare_geometry(primary, repeat):
    """Acceptance changes on the prescribed three edges, without re-selection."""
    if 'path' in primary:
        primary = _document(primary)
    if 'path' in repeat:
        repeat = _document(repeat)
    if primary.get('status') != 'complete' or primary.get('job_id') != 'G-S0' or repeat.get('job_id') != 'R-G':
        raise ValueError('geometry repeat comparison requires the original coarse reference and R-G')
    key = lambda r: (r['pair_start'], r['reference'], r['other'])
    baseline = {key(r): r for r in primary['rows']}
    if len(repeat['rows']) != 3 or len({key(r) for r in repeat['rows']}) != 3 or any(
            r['pair_start'] != 20 or r['reference'] != 1 for r in repeat['rows']):
        raise ValueError('R-G must contain exactly its prescribed three directed edges')
    edges = []
    for row in repeat['rows']:
        if key(row) not in baseline:
            raise ValueError('repeat edge absent from its baseline')
        original = baseline[key(row)]
        with load_array(original['artifact']) as a, load_array(row['artifact']) as b:
            common = a['candidate_uv'].shape == b['candidate_uv'].shape and np.array_equal(a['candidate_uv'][0], b['candidate_uv'][0])
            acceptance = int((a['accepted'] != b['accepted']).sum()) if common else None
            numerical = int((a['numerical_valid'] != b['numerical_valid']).sum()) if common else None
            edges.append(dict(pair_start=20, reference=1, other=row['other'], baseline=original['artifact'], repeat=row['artifact'],
                original_samples=len(a['accepted']), repeated_samples=len(b['accepted']),
                original_accepted=int(a['accepted'].sum()), repeated_accepted=int(b['accepted'].sum()),
                accepted_count_difference=int(b['accepted'].sum())-int(a['accepted'].sum()),
                same_sampled_reference_coordinates=common, acceptance_disagreements=acceptance,
                numerical_validity_disagreements=numerical,
                pointwise_comparison_status='complete' if common else 'unverified: sampled reference coordinates differ',
                class_acceptance_difference={name: row['classes'][name]['accepted']-original['classes'][name]['accepted'] for name in REGIONS}))
    return dict(status='complete', evidence_kind='repeatability-diagnostic', edges=edges,
                used_for_selection=False, physical_accuracy='unverified',
                sampling='restore the primary context PCG64 state in a fresh process')


def run(request, output, config):
    """Execute exactly one reserved geometry arm in its fresh worker process.

    The caller's supervisor owns attempts, deadline, device exclusivity and total
    device memory. Every dependency is an explicit hash-bound file record.
    """
    from basketball_temporal_cloud import balanced_samples, query_warp
    from basketball_temporal_geometry import labels_at, projection, track_lk, velocity_from_support
    from triangulation import solver_metadata
    from edgs_source import ROMA_PIN, ROMA_WEIGHTS
    output = safe_path(output)
    output.mkdir(parents=True, exist_ok=False)
    started = time.monotonic()
    result = dict(schema='vipe-benchmark-geometry/v1', status='incomplete', job_id=request['job_id'],
                  rows=[], contexts=[], diagnostic_only=True, physical_accuracy='unverified')
    backend = None
    try:
        job_id = request['job_id']
        repeat = job_id == 'R-G'
        cropped = job_id in ('C0', 'C1', 'C2', 'C3')
        if not cropped and job_id not in COARSE_ARMS and not repeat:
            raise ValueError('not a preregistered geometry job')
        if cropped:
            finalists = _document(request['finalists'])
            slot = finalists['combined'][job_id]
            if slot['status'] != 'eligible':
                raise ValueError('combined slot lacks eligible frozen component evidence')
            components = slot['components']
        else:
            components = COARSE_ARMS['G-S0' if repeat else job_id]
        inputs, seg, motion, neighbors = [_document(request[k]) for k in ('inputs', 'segmentation', 'motion', 'neighbors')]
        for doc, component in ((seg, components[0]), (motion, components[2]), (neighbors, components[3])):
            if doc.get('status') != 'complete' or doc.get('component', doc.get('method')) != component:
                raise ValueError('geometry prerequisite incomplete or belongs to another component')
        map_data = _document(inputs['map'])
        scene = scene_freeze(inputs, map_data, fit=request.get('scale_fit') if cropped else None,
                             check=request.get('scale_check') if cropped else None, depth_id=components[1])
        if cropped and not scene['scale_evidence']:
            raise ValueError('combined arm cannot reuse a historical passing scale')
        write_json(output / 'scene-freeze.json', scene)
        result['scene'] = file_record(output / 'scene-freeze.json')
        cameras = {int(c): r for c, r in scene['cameras'].items()}
        if set(cameras) != set(training_cameras(config)):
            raise ValueError('scene must contain exactly training cameras')
        labels_by_key = rows_by_identity(seg, config, branch='reconstruction')
        motion_by_key = rows_by_identity(motion, config, branch='reconstruction')
        loader = RGBLoader(inputs['rgb'], config)
        ranked = _neighbor_rows(neighbors)
        expected = contexts(config, repeat=repeat)
        frozen_config = dict(schema='vipe-benchmark-geometry-config/v1', request=request, components=components,
            mode='person-cropped' if cropped else 'coarse', contexts=[list(x) for x in expected],
            seed=0, loop_order='pair_start, reference, selected neighbor order', samples_per_neighbor=5000,
            geometry_source=solver_metadata(), adapter_sha256=digest(__file__),
            pure_gate_sha256=digest(ROOT / 'scripts/basketball_temporal_geometry.py'),
            crop_sampling_source_sha256=digest(ROOT / 'scripts/basketball_temporal_cloud.py'),
            roma_pin=ROMA_PIN, roma_weights=ROMA_WEIGHTS, reprojection_pixels=2, parallax_degrees=1,
            foreground_cameras=3, lk_roundtrip_pixels=1, scene=result['scene'], result_cache_across_arms=False)
        if config['samples_per_neighbor'] != 5000 or config['neighbors_per_reference'] != 3 or config['seed'] != 0:
            raise ValueError('geometry sampling allocation changed')
        write_json(output / 'config.json', frozen_config)
        result['configuration'] = file_record(output / 'config.json')
        rng = np.random.Generator(np.random.PCG64(0))
        if repeat:
            primary = _document(request['repeat_source'])
            if primary.get('status') != 'complete' or primary.get('job_id') != 'G-S0':
                raise ValueError('R-G requires its completed coarse reference source')
            primary_request = _document(primary['configuration'])['request']
            for parent in ('inputs', 'segmentation', 'motion', 'neighbors', 'roma'):
                if request[parent] != primary_request[parent]:
                    raise ValueError('geometry repeat inputs differ from its primary source')
            source_context = [r for r in primary['contexts'] if r['pair_start'] == 20 and r['reference'] == 1]
            if len(source_context) != 1 or source_context[0].get('status') != 'complete' or not source_context[0].get('sampling_rng_state'):
                raise ValueError('geometry repeat lacks original context sampling state')
            rng.bit_generator.state = source_context[0]['sampling_rng_state']
            result['repeat_source'] = request['repeat_source']
        backend = NativeBackend(**request['roma'])
        if request.get('runtime'):
            import sys
            import torchvision
            actual = dict(python=f'{sys.version_info.major}.{sys.version_info.minor}',
                          torch=backend.torch.__version__, torchvision=torchvision.__version__, numpy=np.__version__)
            if any(actual.get(k) != v for k, v in request['runtime']['versions'].items()):
                raise ValueError('geometry runtime differs from its frozen target')
            result['runtime'] = dict(versions=actual, inventory=verify_record(request['runtime']['inventory']))
        result['loading'] = backend.loading
        input_files = {}
        for frame, reference in expected:
            sampling_state = rng.bit_generator.state
            rank = ranked.get(str(reference), {})
            if not isinstance(rank, dict):
                raise ValueError('neighbor evidence must retain status and positive-support ranking')
            others = rank.get('neighbors', []) if isinstance(rank, dict) else []
            if (rank.get('status') != 'complete' or len(others) != 3 or len(set(others)) != 3 or
                    reference in others or any(c not in cameras for c in others)):
                result['contexts'].append(dict(pair_start=frame, reference=reference, status='blocked',
                    reason='fewer than three distinct positive-support training neighbors', neighbor_evidence=rank))
                continue
            ids = [reference] + others
            images, successor, labels, next_labels, changing = {}, {}, {}, {}, {}
            for c in ids:
                masks, changes = [], []
                for f in (frame, frame + 1):
                    identity = Identity('reconstruction', c, f, frame)
                    key = identity.key()
                    source, mask_row, motion_row = loader.row(identity), labels_by_key[key], motion_by_key[key]
                    for row in (mask_row, motion_row):
                        if row.get('source_rgb_sha256', row.get('rgb_sha256')) != source['rgb']['sha256']:
                            raise ValueError('component source RGB differs from immutable manifest')
                        validate_grid(row, cameras[c]['K'], source['grid'])
                    valid, mask = load_array(source['valid']), load_array(mask_row['instances'])
                    semantics = {k: mask_row['semantics'][k] for k in sorted(mask_row['semantics'], key=int)}
                    instances(mask, semantics, valid)
                    change = load_array(motion_row['changing'])
                    if change.dtype != np.bool_ or change.shape != SHAPE:
                        raise ValueError('changing output contract failed')
                    masks.append(dict(labels=mask, semantics=semantics))
                    changes.append(change)
                    rgb = loader.load(identity)
                    (images if f == frame else successor)[c] = rgb
                    for record in (source['rgb'], source['valid'], mask_row['instances'], motion_row['changing']):
                        input_files[record['path']] = record['bytes']
                labels[c], next_labels[c] = masks
                changing[c] = changes[0] | changes[1]
            P = np.asarray([projection(consumer_camera(cameras[c])) for c in ids])
            centers = np.asarray([cameras[c]['center'] for c in ids])
            warps, candidates = {}, []
            for pair, other in enumerate(others, 1):
                (warp, confidence), matching = backend.match(images[reference], images[other])
                if warp.ndim != 3 or warp.shape[2] != 4 or confidence.shape != warp.shape[:2]:
                    raise ValueError('native RoMa warp/confidence grid contract failed')
                crops, cropping = [], dict(wall_seconds=0., cuda_seconds=0.)
                if cropped:
                    (warp, confidence, crops), cropping = backend.crop(warp, confidence, images, labels, [reference, other])
                    if len(crops) > 255 or len({r['source_instance'] for r in crops}) != len(crops):
                        raise ValueError('person crop cap or one-per-person rule exceeded')
                    write_json(output / f'pair{frame}-ref{reference}-other{other}-crops.json', crops)
                warps[other] = warp
                uv0 = (warp[..., :2].reshape(-1, 2) + 1) * [480, 270]
                probability = confidence.reshape(-1).copy()
                probability[~np.isfinite(probability)] = 0
                probability[probability > backend.model.sample_thresh] = 1
                sampled_labels = labels_at(labels[reference]['labels'], uv0)
                probability[sampled_labels < 0] = 0
                chosen = balanced_samples(probability, sampled_labels,
                    {k: v['class'] for k, v in labels[reference]['semantics'].items()}, 5000, rng)
                uv1 = (warp[..., 2:].reshape(-1, 2)[chosen] + 1) * [480, 270]
                candidates.append((pair, uv0[chosen], uv1, matching, cropping, crops))
            context_edges = []
            for pair, uv0, uv1, matching, cropping, crops in candidates:
                other = ids[pair]
                (xyz, numerical), triangulation_time = backend.triangulate(P[0], P[pair], uv0, uv1)
                all_uv = np.asarray([uv0] + [uv1 if c == other or not len(uv0) else query_warp(warps[c], uv0) for c in others])
                arrays, record = evaluate_edge(xyz, numerical, all_uv, ids, pair, cameras, labels, changing)
                kept = arrays['accepted']
                X, UV, support = xyz[kept], all_uv[:, kept], arrays['candidate_support'][:, kept]
                region = arrays['candidate_region'][kept]
                velocity, measured = np.zeros_like(X), np.zeros(len(X), bool)
                fg = np.flatnonzero(region > 0)
                lk_counts = {}
                if len(fg):
                    endpoints, valid = [], []
                    for k, c in enumerate(ids):
                        end, ok = track_lk(images[c], successor[c], UV[k, fg], labels[c]['labels'], next_labels[c]['labels'])
                        endpoints.append(end)
                        valid.append(ok & support[k, fg])
                        lk_counts[str(c)] = dict(attempted=len(fg), lk_valid=int(ok.sum()), supported_valid=int(valid[-1].sum()))
                    velocity[fg], measured[fg] = velocity_from_support(X[fg], np.asarray(endpoints), P, centers,
                        np.asarray(valid), ids, np.asarray(scene['normalization']), scene['units']['normalized_time_seconds'])
                transform = np.asarray(scene['normalization'])
                xy = np.floor(UV[0]).astype(int)
                colors = images[reference][xy[:, 1].clip(0, 539), xy[:, 0].clip(0, 959)] / 255.
                arrays.update(world_positions=X, positions=(X @ transform[:3, :3].T + transform[:3, 3]).astype(np.float32),
                    velocities=velocity.astype(np.float32), velocity_valid=measured, uv=UV, support=support,
                    region=region, camera_ids=np.asarray(ids), colors=colors.astype(np.float32),
                    times=np.full((len(X), 1), frame / 50, np.float32), durations=np.full((len(X), 1), .2, np.float32))
                archive = output / f'pair{frame}-ref{reference}-other{other}.npz'
                with archive.open('xb') as stream:
                    np.savez_compressed(stream, **arrays)
                raw_overlap = next((r for r in rank.get('candidates', []) if r['camera'] == other), None)
                record.update(pair_start=frame, reference=reference, other=other, artifact=file_record(archive),
                    sampling=dict(requested=5000, obtained=len(xyz), shortage=5000-len(xyz)),
                    matching=matching, cropping=cropping, triangulation=triangulation_time,
                    crop_matches=sum('target_instance' in r for r in crops), lk=lk_counts,
                    raw_normalized_overlap=raw_overlap or dict(status='unverified', reason='neighbor raw/Jaccard evidence missing'))
                for name, value in REGIONS.items():
                    chosen = (region > 0) if value is None else region == value
                    n = int(chosen.sum())
                    record['classes'][name].update(velocity_valid=int((chosen & measured).sum()),
                        velocity_valid_fraction=float((chosen & measured).sum()/n) if n and name != 'static' else None,
                        unsupported_motion=int((chosen & ~measured).sum()) if name != 'static' else 0)
                result['rows'].append(record)
                context_edges.append(record)
                with (output / 'records.jsonl').open('a') as stream:
                    from .files import canonical
                    stream.write(canonical(record) + '\n')
            context_record = _union_context(context_edges, frame, reference, others)
            context_record['sampling_rng_state'] = sampling_state
            result['contexts'].append(context_record)
            if request.get('runtime') and 'loaded_files' not in result['runtime']:
                from .runtime_capture import loaded_runtime
                result['runtime']['loaded_files'] = loaded_runtime(output / 'loaded-runtime.json')
            print(f'{job_id}: completed pair {frame}, reference {reference}', flush=True)
        result['summary'] = summarize(result['rows'], result['contexts'], expected)
        result['input_bytes_unique'] = sum(input_files.values())
        result['status'] = 'complete' if result['summary']['all_references_have_three_neighbors'] else 'blocked'
        if result['status'] != 'complete':
            result['reason'] = 'one or more diagnostic references lack three eligible neighbors'
        result['component'] = components[3]
        result['components'] = components
        if repeat and result['status'] == 'complete':
            result['repeat'] = compare_geometry(primary, result)
        return result
    except BaseException as error:
        result['status'] = 'failed'
        result['reason'] = f'{type(error).__name__}: {error}'
        raise
    finally:
        result['wall_seconds'] = time.monotonic() - started
        result['resources'] = backend.resources() if backend else dict(status='unverified', reason='backend did not finish loading')
        result['output_bytes_before_result'] = sum(p.stat().st_size for p in output.iterdir() if p.is_file())
        write_json(output / 'result.json', result)
