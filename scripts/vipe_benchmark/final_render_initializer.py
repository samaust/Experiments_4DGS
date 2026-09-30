"""Pure prospective QF full-rig geometry assembly; no native or ledger dispatch.

A returned CPU receipt is not a job authorization, native qualification or actual
final render. Historical dense-fusion validators retain their original contracts.
"""
from dataclasses import dataclass
import math

import numpy as np

from .files import object_hash, read_json, verify_record
from .final_render_contract import (COMPOSITIONS, KEYFRAMES, TRAINING_CAMERAS,
    initializer_arrays_hash, normalization_matrix, parse_request, validate_processed_manifest_binding)

NATIVE = ('positions', 'colors', 'velocities', 'times', 'durations')
SIDECARS = ('region', 'velocity_valid')


@dataclass(frozen=True)
class GeometryInput:
    arm: str
    record_kind: str
    scene: dict
    rows: tuple[dict, ...]
    provenance: dict


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _bound(record):
    _require(verify_record(record) == record, 'changed input record path/hash/size')
    return read_json(record['path'])


def _arrays(record):
    _require(verify_record(record) == record, 'changed observation archive')
    with np.load(record['path'], allow_pickle=False) as archive:
        return {key: archive[key].copy() for key in archive.files}


def validate_manifest(request):
    """Check accepted zero-offset timing and union training exclusions, CPU only."""
    manifest = validate_processed_manifest_binding(request)
    _require(manifest.get('schema') == 'basketball-processed/v1' and manifest.get('status') == 'prepared' and
        manifest.get('source_fps') == 25 and manifest.get('heldout_camera_ids') == ['0', '10', '20', '30'] and
        manifest.get('temporal_holdout_seconds') == [.8, 1.], 'accepted Basketball manifest required')
    from sync_timing import common_training_keys, normalized_timestamp, validate_timing
    timing = validate_timing(manifest['timing'])
    _require(timing['camera_ids'] == [str(c) for c in range(34)] and timing['reference_camera'] == '1' and
        all(offset == 0 for offset in timing['offset_seconds'].values()) and
        timing['normalization'] == manifest['time'] == dict(origin_seconds=0., duration_seconds=2.),
        'frame/50 requires frozen zero-offset two-second timing')
    _require(timing in manifest['comparison_timings'], 'current timing absent from exclusion union')
    cameras = manifest['cameras']
    _require([c['id'] for c in cameras] == timing['camera_ids'], 'manifest camera coverage/order differs')
    frames = []
    for camera in cameras:
        identity = camera['id']
        _require(camera['split'] == ('train' if int(identity) in TRAINING_CAMERAS else 'test') and
            [f['frame_id'] for f in camera['frames']] == list(range(50)), 'manifest heldout/frame coverage differs')
        for frame in camera['frames']:
            f = frame['frame_id']
            _require(math.isclose(frame['normalized_time'], normalized_timestamp(timing, identity, f/25),
                rel_tol=0, abs_tol=1e-10), 'manifest normalized timestamp differs')
            frames.append((identity, f, f/25))
    retained, excluded = common_training_keys(frames, manifest['comparison_timings'], manifest['heldout_camera_ids'])
    _require(manifest['training_keys'] == [list(k) for k in retained] and manifest['training_exclusions'] == excluded,
        'manifest union training exclusions differ')
    required = {(str(c), f) for c in TRAINING_CAMERAS for pair in KEYFRAMES for f in (pair, pair+1)}
    _require(required <= set(retained), 'requested full-rig pair consumes heldout/unsupported observation')
    return manifest


def validate_scene(request, record):
    """Check an exact D4 scene against accepted cameras, time and normalization."""
    scene = _bound(record)
    contract = request['initializer_contract']
    matrix = normalization_matrix(contract['normalization'], actual=request['record_kind'] == 'actual')
    _require(scene.get('schema') == 'vipe-benchmark-diagnostic-scene/v1' and scene.get('status') == 'complete'
        and scene.get('depth_component') == 'D4' and scene.get('normalization') == matrix.tolist(),
        'scene D4 identity/normalization differs')
    units = scene['units']
    _require(units.get('normalized_time_seconds') == 2. and units.get('frame_seconds') == .04 and
        units.get('velocity') == 'metres/second -> normalization linear map * 2 seconds', 'scene time/velocity units differ')
    fit = _bound(request['bindings']['D4_fit']); check = _bound(request['bindings']['D4_check'])
    fitting = _bound(fit['scale']); checking = _bound(check['scale'])
    _require(fitting.get('status') == checking.get('status') == 'passed' and
        fitting.get('scale') == checking.get('scale') == scene.get('scale') and
        scene.get('scale_evidence') == dict(fit=fit['scale'], check=check['scale']), 'scene lacks exact passing D4 scale evidence')
    manifest = validate_manifest(request)
    cameras = manifest['cameras']
    _require(set(scene['cameras']) == {str(c) for c in TRAINING_CAMERAS}, 'scene must contain exactly training cameras')
    inputs = _bound(request['bindings']['inputs'])
    reference = inputs['reference_geometry']
    historical_freeze = _bound(reference['freeze'])
    normalization_source = _bound(reference['normalization_source'])
    _bound(inputs['map'])
    _require(reference.get('scale') == historical_freeze.get('scale') and
        reference.get('normalization') == normalization_source.get('normalization'),
        'historical reference differs from verified sources')
    _require(scene.get('historical_reference') == reference and scene.get('map') == inputs['map'] and
        manifest.get('freeze_sha256') == reference['freeze']['sha256'], 'scene/manifest accepted map/freeze lineage differs')
    source_scale = inputs['reference_geometry']['scale']; target_scale = scene['scale']
    _require(type(source_scale) in (int, float) and math.isfinite(source_scale) and source_scale > 0 and
        type(target_scale) in (int, float) and math.isfinite(target_scale) and target_scale > 0, 'finite positive camera scale required')
    factor = target_scale/source_scale
    original = np.asarray(inputs['reference_geometry']['normalization']['transform'], np.float64)
    _require(original.shape == (4,4) and np.isfinite(original).all(), 'finite historical normalization required')
    rebased = original.copy(); rebased[:, :3] /= factor
    _require(np.allclose(matrix, rebased, atol=1e-8, rtol=1e-8), 'historical normalized coordinates changed under physical rescaling')
    for camera in cameras:
        if int(camera['id']) not in TRAINING_CAMERAS:
            continue
        frozen = scene['cameras'][camera['id']]
        K = np.asarray(camera['K'], np.float64).copy(); K[:2, 2] -= .5
        _require(camera['width'] == 960 and camera['height'] == 540 and
            np.asarray(frozen['K']).shape == (3, 3) and np.allclose(frozen['K'], K, atol=1e-8, rtol=1e-10) and
            np.allclose(frozen['R'], camera['world_to_camera_R'], atol=1e-8, rtol=1e-10) and
            np.allclose(frozen['t'], np.asarray(camera['world_to_camera_T'])*factor, atol=1e-8, rtol=1e-10) and
            np.allclose(frozen['center'], np.asarray(camera['center'])*factor, atol=1e-8, rtol=1e-10),
            'scene camera calibration or physical scale differs from accepted manifest')
    return scene, matrix


def _geometry(request, arm, record):
    value = _bound(record); composition = COMPOSITIONS[arm]
    names = {'S2', 'D4_fit', 'D4_check', composition['motion'], composition['neighbors']}
    _require(value.get('schema') == 'plan067-final-render-geometry/v1' and value.get('status') == 'complete' and
        value.get('arm') == arm and value.get('record_kind') == request['record_kind'] and
        value.get('request_sha256') == object_hash(request) and value.get('composition') == composition and
        value.get('prerequisites') == {k: request['bindings'][k] for k in names}, 'full-rig QF geometry provenance differs')
    if request['record_kind'] == 'actual' or 'scene_freeze' in request['bindings']:
        _require(value['scene'] == request['bindings'].get('scene_freeze'), 'geometry scene differs from admitted bound scene')
    scene, matrix = validate_scene(request, value['scene'])
    neighbors = _bound(request['bindings'][composition['neighbors']])
    _require(neighbors.get('status') == 'complete' and neighbors.get('component') == composition['neighbors'] and
        neighbors.get('inputs') == request['bindings']['inputs'], 'neighbor native result/input binding differs')
    neighbor_map = {}
    for row in neighbors['records']:
        c = row['reference']; selected = row['neighbors']
        _require(type(c) is int and c in TRAINING_CAMERAS and c not in neighbor_map and row['status'] == 'complete' and
            len(selected) == len(set(selected)) == 3 and c not in selected and
            all(type(other) is int and other in TRAINING_CAMERAS for other in selected), 'invalid full-rig neighbor membership')
        neighbor_map[c] = selected
    _require(set(neighbor_map) == set(TRAINING_CAMERAS), 'neighbor rig coverage differs')
    expected = {(frame, camera, other) for frame in KEYFRAMES for camera in TRAINING_CAMERAS for other in neighbor_map[camera]}
    inputs = _bound(request['bindings']['inputs'])
    accepted = {}
    for row in inputs['rgb']:
        identity = row['identity']
        key = (identity['camera'], identity['frame'])
        if identity['branch'] == 'reconstruction':
            _require(key not in accepted, 'duplicate accepted RGB source')
            accepted[key] = row
    manifest = _bound(request['bindings']['scene_manifest'])
    manifest_frames = {(int(c['id']), f['frame_id']): f for c in manifest['cameras'] for f in c['frames']}
    source_rows = {}
    for name in ('S2', composition['motion']):
        native = _bound(request['bindings'][name])
        _require(native.get('status') == 'complete' and native.get('component') == name, 'native prerequisite incomplete/wrong component')
        indexed = {}
        for row in native['rows']:
            identity = row['identity']
            if identity['branch'] != 'reconstruction':
                continue
            key = (identity['camera'], identity['frame'], identity['pair_start'])
            _require(key not in indexed, 'duplicate native source identity')
            indexed[key] = row
        source_rows[name] = indexed
    seen = set(); verified_sources = set()
    for row in value['rows']:
        key = (row['pair_start'], row['reference'], row['other'])
        _require(all(type(k) is int for k in key) and key in expected and key not in seen, 'duplicate/heldout/wrong full-rig edge')
        seen.add(key)
        frame, camera, _ = key; cameras = [camera, *neighbor_map[camera]]
        hashes = {}
        for name, indexed in source_rows.items():
            keys = [(c, f, frame) for c in cameras for f in (frame, frame+1)]
            _require(all(k in indexed for k in keys), 'missing exact native source rows')
            for c, f, pair in keys:
                source = accepted.get((c, f)); native = indexed[(c, f, pair)]
                _require(source is not None and native['source_rgb_sha256'] == source['rgb']['sha256'] ==
                    manifest_frames[(c, f)]['sha256'] and native['K'] == source['K'] == scene['cameras'][str(c)]['K'] and
                    native['grid'] == source['grid'], 'native/accepted/manifest source calibration differs')
                if request['record_kind'] == 'actual':
                    for artifact in (source['rgb'], native['valid'], native['semantic_static'] if name == 'S2' else native['changing']):
                        identity = object_hash(artifact)
                        if identity not in verified_sources:
                            verify_record(artifact); verified_sources.add(identity)
            hashes[name] = [object_hash(indexed[k]) for k in keys]
        _require(row.get('source_rows') == hashes, 'edge source identity/row provenance differs')
    _require(seen == expected, 'full-rig geometry coverage incomplete; diagnostic subset cannot supply initialization')
    return GeometryInput(arm, value['record_kind'], scene, tuple(value['rows']), value), matrix, neighbor_map


def assemble(request, arm, geometry_record, width_record):
    """Validate future full-rig rows and return native arrays with a CPU receipt.

    This pure worker boundary creates no output directory or ledger event. The
    separately authorized caller owns CPU allocation, publication and cleanup.
    """
    parse_request(request)
    _require(arm in COMPOSITIONS, 'unknown QF arm')
    validate_processed_manifest_binding(request)
    geometry, matrix, neighbors = _geometry(request, arm, geometry_record)
    width = _bound(width_record)
    _require(width.get('schema') == 'plan067-final-render-voxel-width/v1' and
        width.get('record_kind') == request['record_kind'] and width.get('rule') == 'half median positive nearest-neighbor distance' and
        width.get('request_sha256') == object_hash(request) and width.get('scene') == geometry.provenance['scene'] and
        width.get('basis') == request['initializer_contract'].get('voxel_basis') and
        width.get('source') == request['initializer_contract'].get('voxel_basis_source'), 'voxel basis/scene/request lineage differs')
    from basketball_dense_fusion import fuse, validate, voxel_width
    basis = _arrays(width['basis'])
    _require(set(basis) == {'normalized_positions'}, 'explicit normalized static voxel basis required')
    source = width['source']; origin = _bound(source['receipt']); prior = _arrays(source['archive'])
    inputs = _bound(request['bindings']['inputs']); reference = inputs['reference_geometry']
    _bound(reference['freeze'])
    _require(origin.get('schema') == 'basketball-static-initialization/v1' and origin.get('status') == 'prepared' and
        origin.get('manifest_sha256') == request['bindings']['scene_manifest']['sha256'] and
        origin.get('freeze_sha256') == reference['freeze']['sha256'] and
        origin.get('archive_sha256') == source['archive']['sha256'] and origin.get('source_frame') == 25, 'voxel basis origin differs from accepted static prior')
    positions = prior['positions']
    _require(positions.ndim == 2 and positions.shape[1] == 3 and np.isfinite(positions).all(), 'finite static prior positions required')
    _require(type(origin.get('points')) is int and origin['points'] == len(positions), 'static prior point-count provenance differs')
    manifest = validate_manifest(request)
    source_frames = {(c['id'],f['frame_id']):f for c in manifest['cameras'] for f in c['frames']}
    _require(isinstance(origin.get('inputs'),list) and (bool(origin['inputs']) or request['record_kind']=='fixture'), 'static prior input provenance missing')
    seen_prior = set()
    for row in origin['inputs']:
        camera = row['camera_id']; key = (camera,row['frame_id'])
        _require(camera in {str(c) for c in TRAINING_CAMERAS} and row['frame_id']==25 and key not in seen_prior and
            row['sha256'] == source_frames[key]['sha256'], 'static prior source camera/time differs')
        seen_prior.add(key)
    normalized = (positions*(geometry.scene['scale']/reference['scale']) @ matrix[:3,:3].T + matrix[:3,3]).astype(np.float32)
    scene_scale = reference['normalization']['scene_scale']
    _require(type(scene_scale) in (int,float) and math.isfinite(scene_scale) and scene_scale > 0, 'positive historical scene scale required')
    normalized = normalized[np.linalg.norm(normalized,axis=1) < 5*scene_scale]
    _require(basis['normalized_positions'].shape == normalized.shape and
        np.allclose(basis['normalized_positions'], normalized, rtol=1e-5, atol=1e-6), 'normalized voxel basis does not derive from bound static prior')
    _require(type(width['width']) in (float, int) and math.isfinite(width['width']) and
        math.isclose(width['width'], voxel_width(basis['normalized_positions']), rel_tol=1e-10, abs_tol=1e-12),
        'voxel width differs from bound static-basis rule')
    chunks = []; sources = []; offset = 0
    for row in sorted(geometry.rows, key=lambda r: (r['pair_start'], r['reference'], neighbors[r['reference']].index(r['other']))):
        arrays = _arrays(row['artifact'])
        _require(set(NATIVE+SIDECARS+('world_positions', 'world_velocities', 'camera_ids')) <= set(arrays), 'geometry observation arrays incomplete')
        count = len(arrays['positions'])
        if count:
            validate(arrays)
        _require(arrays['world_positions'].shape == (count, 3) and np.isfinite(arrays['world_positions']).all() and
            arrays['positions'].shape == (count, 3) and np.allclose(arrays['positions'],
                arrays['world_positions'] @ matrix[:3, :3].T + matrix[:3, 3], rtol=1e-5, atol=1e-6),
            'physical-to-normalized positions differ')
        _require(arrays['world_velocities'].shape == (count,3) and np.isfinite(arrays['world_velocities']).all() and
            np.allclose(arrays['velocities'], arrays['world_velocities'] @ matrix[:3,:3].T * 2., rtol=1e-5, atol=1e-6),
            'physical metres/second to normalized-time velocities differ')
        _require(arrays['camera_ids'].dtype.kind in 'iu' and arrays['camera_ids'].tolist() ==
            [row['reference'], *neighbors[row['reference']]], 'observation camera membership/order differs')
        _require(arrays['times'].shape == (count, 1) and
            np.all(arrays['times'] == np.float32(row['pair_start']/50)), 'observation normalized frame time differs')
        chunks.append({k: arrays[k] for k in NATIVE+SIDECARS})
        sources.append(dict(edge=[row['pair_start'], row['reference'], row['other']], artifact=row['artifact'],
            offset=offset, count=count, source_rows=row['source_rows']))
        offset += count
    _require(offset > 0, 'empty full-rig initialization')
    observations = {k: np.concatenate([c[k] for c in chunks]) for k in NATIVE+SIDECARS}
    static = observations['region'] == 0
    xyz, rgb, mapping, voxels = fuse(observations['positions'][static], observations['colors'][static], width['width'])
    n = len(xyz); centers = np.asarray(KEYFRAMES, np.float32)/50
    arrays = dict(positions=np.tile(xyz, (9, 1)), colors=np.tile(rgb, (9, 1)),
        velocities=np.zeros((n*9, 3), np.float32), times=np.repeat(centers, n)[:, None],
        durations=np.full((n*9, 1), .2, np.float32), region=np.zeros(n*9, np.int32), velocity_valid=np.zeros(n*9, bool))
    arrays = {k: np.concatenate([v, observations[k][~static]]) for k, v in arrays.items()}
    arrays['physical_static_id'] = np.concatenate([np.tile(np.arange(n), 9), np.full((~static).sum(), -1)])
    arrays['foreground_observation_id'] = np.concatenate([np.full(n*9, -1), np.flatnonzero(~static)])
    validate(arrays)
    composition = COMPOSITIONS[arm]
    names = {'S2','D4_fit','D4_check',composition['motion'],composition['neighbors']}
    initializer_receipt = dict(request['initializer_contract'], arm=arm,composition=composition,
        arrays_sha256=initializer_arrays_hash(arrays), prerequisites={name:request['bindings'][name] for name in names},
        scene_manifest=request['bindings']['scene_manifest'])
    receipt = dict(schema='plan067-final-render-assembly-result/v1', status='complete', record_kind=request['record_kind'],
        arm=arm, composition=COMPOSITIONS[arm], request_sha256=object_hash(request), geometry=geometry_record,
        scene=geometry.provenance['scene'], scene_manifest=request['bindings']['scene_manifest'], voxel_width=width_record,
        normalization=request['initializer_contract']['normalization'], velocity_units='normalized-scene/normalized-time',
        time_formula='frame/50', coverage_edges=len(geometry.rows), physical_static_points=n, temporal_static_copies=9*n,
        foreground_observations=int((~static).sum()), total_gaussians=len(arrays['positions']),
        arrays_sha256=initializer_arrays_hash(arrays), initializer_receipt=initializer_receipt, sources=sources, execution_authorized=False, native_adapter_qualified=False,
        identities='semantic regions and view-local labels only; not verified cross-camera identities',
        static_fusion_mapping_sha256=initializer_arrays_hash(dict(mapping=mapping, voxels=voxels)))
    return arrays, receipt
