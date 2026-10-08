"""Extended human metric-depth choice for prospective REVIEW admission only.

Historical S2/D4 scope remains in final_render_contract. This version creates no
ledger event and grants no setup, GPU, training or render execution authority.
"""
import copy
import math

from .files import file_record, object_hash, read_json, verify_record
from .depth_review import METRIC_CANDIDATES
from .final_render_contract import (
    BLOCKERS, COMPOSITIONS, ENDPOINTS, KEYFRAMES, PHASES, PRESET_SOURCE, TRAINING_CAMERAS,
    ReviewAdmission, allocation_specs, initializer_arrays_hash, normalization_matrix,
)

SCHEMA = 'plan069-final-render-request/v1'


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _bound(record):
    _require(isinstance(record, dict) and set(record) == {'path', 'sha256', 'bytes'}, 'exact file record required')
    _require(verify_record(record) == record, 'changed file record path/hash/size')
    return read_json(record['path'])


def compositions(candidate):
    """Keep the selected eligible metric depth fixed across the existing arms."""
    _require(candidate in METRIC_CANDIDATES, 'extended mode requires eligible metric D*; historical D4/relative depth excluded')
    return {arm: dict(value, depth=candidate) for arm, value in COMPOSITIONS.items()}


def parse_request(value):
    """Validate the immutable extended REVIEW request; DO is deliberately absent."""
    _require(value.get('schema') == SCHEMA, 'wrong extended QF request schema')
    _require(value.get('mode') == 'REVIEW' and value.get('record_kind') in ('actual', 'fixture'), 'extended QF is REVIEW only')
    candidate = value.get('depth_candidate')
    _require(value.get('compositions') == compositions(candidate), 'same D* and fixed isolated compositions required')
    _require(type(value.get('seed')) is int and value['seed'] == 0 and type(value.get('iterations')) is int and
             value['iterations'] in ENDPOINTS, 'equal seed and a supported (5000/70000) training endpoint required')
    _require(value.get('preset') == 'default_keyframe' and value.get('preset_source_sha256') == PRESET_SOURCE,
             'frozen preset required')
    _require(value.get('geometry') == dict(keyframes=list(KEYFRAMES), samples_per_edge=5000, neighbors_per_reference=3),
             'frozen full-rig geometry settings required')
    _require(value.get('render') == dict(cameras=[0, 10, 20, 30], frames=list(range(50)), fps=25, resolution=[960, 540]),
             'complete equal held-out render settings required')
    _require(value.get('allocations') == allocation_specs(value['id'], value['iterations']),
             'fresh exact prospective allocations required')
    for name, limit in [('artifact_bytes_limit', 50*2**30), ('device_bytes_limit', 22*2**30), ('cpu_workers_limit', 8)]:
        _require(type(value.get(name)) is int and 0 < value[name] <= limit, 'invalid/excessive ' + name)
    initializer = value['initializer_contract']
    _require(initializer.get('schema') == 'plan069-final-render-initializer/v1' and
             initializer.get('time_formula') == 'frame/50' and
             initializer.get('velocity_units') == 'normalized-scene/normalized-time', 'initializer time/velocity units required')
    normalization_matrix(initializer['normalization'], actual=True)
    if 'voxel_basis' in initializer or 'voxel_basis_source' in initializer:
        _require('voxel_basis' in initializer and set(initializer.get('voxel_basis_source', {})) == {'archive', 'receipt'},
                 'complete voxel basis provenance required')
        for record in [initializer['voxel_basis'], *initializer['voxel_basis_source'].values()]:
            _require(verify_record(record) == record, 'changed voxel basis provenance')
    names = {'proposal', 'source', 'preset', 'runtime', 'config', 'qualification', 'scene_manifest', 'scene_freeze',
             'inputs', 'segmentation_decision', 'depth_decision', 'S2', 'D_fit', 'D_check', 'M0', 'M1', 'M2', 'N0', 'N1', 'N2'}
    bindings = value['bindings']
    _require(set(bindings) == names, 'complete exact extended prerequisite bindings required')
    for record in bindings.values():
        _require(verify_record(record) == record, 'changed bound file record')
    decision = _decision(bindings['depth_decision'])
    _require(decision['status'] == 'ready' and decision['selected_candidate_ids'] == [candidate], 'ready exact extended human D* required')
    proposal = _bound(bindings['proposal'])
    _require(proposal.get('schema') == 'plan069-final-render-review-proposal/v1' and
             proposal.get('mode') == 'REVIEW' and proposal.get('depth_candidate') == candidate and
             proposal.get('record_kind') == value['record_kind'] and
             proposal.get('bindings') == {key: bindings[key] for key in names - {'proposal'}},
             'proposal prerequisite bindings differ')
    _require(proposal.get('settings_sha256') == object_hash({key: item for key, item in value.items() if key != 'bindings'}),
             'proposal fixed settings differ')
    if 'budget_amendment' in value:
        validate_budget_configuration(value, None)
    if value['record_kind'] == 'actual':
        _require(bindings['source'] == file_record(__file__) and bindings['preset']['sha256'] == PRESET_SOURCE,
                 'current extended contract/preset source pins required')
    return copy.deepcopy(value)


def validate_scene_bindings(value):
    """Bind full physical similarity, calibrated cameras and two-second units."""
    import numpy as np
    from .final_render_initializer import validate_manifest
    manifest = validate_manifest(value)
    bindings = value['bindings']
    inputs = _bound(bindings['inputs'])
    reference = inputs['reference_geometry']
    freeze = _bound(reference['freeze'])
    origin = _bound(reference['normalization_source'])
    _bound(inputs['map'])
    _require(reference.get('scale') == freeze.get('scale') and
             reference.get('normalization') == origin.get('normalization'), 'historical reference source substitution')
    scene = _bound(bindings['scene_freeze'])
    fit, fit_record = _scale(bindings['D_fit'])
    check, _ = _scale(bindings['D_check'])
    candidate = value['depth_candidate']
    _require(scene.get('schema') == 'plan069-final-render-scene/v1' and scene.get('status') == 'complete' and
             scene.get('depth_component') == candidate and scene.get('scale_evidence') ==
             dict(fit=fit_record, check=_scale(bindings['D_check'])[1]) and scene.get('scale') == fit['scale'] == check['scale'],
             'scene exact D* scale evidence differs')
    _require(scene.get('historical_reference') == reference and scene.get('map') == inputs['map'] and
             manifest.get('freeze_sha256') == reference['freeze']['sha256'], 'scene/manifest map/freeze lineage differs')
    matrix = normalization_matrix(value['initializer_contract']['normalization'], actual=True)
    _require(scene.get('normalization') == matrix.tolist(), 'scene full similarity differs')
    _require(scene.get('units') == dict(normalized_time_seconds=2., frame_seconds=.04,
             velocity='metres/second -> normalization linear map * 2 seconds'), 'scene time/velocity normalization differs')
    source_scale = reference['scale']
    _require(type(source_scale) in (int, float) and math.isfinite(source_scale) and source_scale > 0, 'positive historical camera scale required')
    factor = fit['scale']/source_scale
    original = normalization_matrix(dict(transform=reference['normalization']['transform']), actual=True)
    rebased = original.copy()
    rebased[:, :3] /= factor
    _require(np.allclose(matrix, rebased, atol=1e-8, rtol=1e-8), 'physical rescaling changed historical normalized coordinates')
    _require(set(scene['cameras']) == {str(c) for c in TRAINING_CAMERAS}, 'exact training camera rig required')
    for camera in manifest['cameras']:
        if int(camera['id']) not in TRAINING_CAMERAS:
            continue
        frozen = scene['cameras'][camera['id']]
        K = np.asarray(camera['K'], dtype=np.float64).copy()
        K[:2, 2] -= .5
        _require(camera['width'] == 960 and camera['height'] == 540 and
                 np.asarray(frozen['K']).shape == (3, 3) and np.allclose(frozen['K'], K, atol=1e-8, rtol=1e-10) and
                 np.allclose(frozen['R'], camera['world_to_camera_R'], atol=1e-8, rtol=1e-10) and
                 np.allclose(frozen['t'], np.asarray(camera['world_to_camera_T'])*factor, atol=1e-8, rtol=1e-10) and
                 np.allclose(frozen['center'], np.asarray(camera['center'])*factor, atol=1e-8, rtol=1e-10),
                 'scene calibrated camera or physical scale differs')
    return dict(status='passed', transform=matrix.tolist(), native_execution_qualified=False)


def _scale(record):
    value = _bound(record)
    if value.get('status') == 'complete' and 'scale' in value:
        record = value['scale']
        value = _bound(record)
    _require(value.get('status') == 'passed' and type(value.get('scale')) in (int, float) and
             math.isfinite(value['scale']) and value['scale'] > 0, 'exact passing positive scale receipt required')
    return value, record


def _decision(record, *, deep=False, actual=True):
    """The hash-pinned D* decision; deep re-derives it from the whole depth review.

    Deep validation rehashes every review package file (minutes), so it runs at
    REVIEW/DO admission only. Worker, control and acceptance paths rely on the
    immutable pinned record that admission already re-derived.
    """
    if deep:
        from .depth_review import validate_decision
        return validate_decision(record, actual=actual)
    from .depth_review import DECISION_SCHEMA
    decision = _bound(record)
    _require(decision.get('schema') == DECISION_SCHEMA, 'extended depth decision schema')
    return decision


def validate_depth(value):
    """Full D* re-derivation; it reads the shared ledger, so never call it under its lock."""
    _validate_depth(parse_request(value), deep=True)


def _validate_depth(value, *, deep=False):
    bindings = value['bindings']
    decision = _decision(bindings['depth_decision'], deep=deep, actual=value['record_kind'] == 'actual')
    candidate = value['depth_candidate']
    eligibility = decision['engineering_eligibility'][candidate]
    _require(eligibility['eligible'] is True, 'engineering eligible metric depth required')
    # The importer supplies these exact independently verified identities.
    evidence = eligibility['evidence']
    _require(bindings['D_fit'] == evidence['fit'] and bindings['D_check'] == evidence['check'] and
             bindings['inputs'] == evidence['inputs'], 'decision fit/check/accepted input manifest substitution')
    fit, fit_record = _scale(bindings['D_fit'])
    check, _ = _scale(bindings['D_check'])
    _require(fit.get('role') == 'fit' and check.get('role') == 'selection' and
             check.get('frozen_fit') == fit_record and fit['scale'] == check['scale'], 'check did not consume exact frozen passing fit')
    for scale in (fit, check):
        _require(scale.get('component', scale.get('provenance', {}).get('component')) == candidate and
                 scale.get('provenance', {}).get('inputs') == bindings['inputs'], 'scale candidate/input lineage differs')
    _require(fit.get('scale_protocol_sha256') == check.get('scale_protocol_sha256') and
             fit.get('estimator_sha256') == check.get('estimator_sha256') and
             fit['provenance'].get('component_sha256') == check['provenance'].get('component_sha256') and
             all(fit.get(key) for key in ('scale_protocol_sha256', 'estimator_sha256')) and
             bool(fit['provenance'].get('component_sha256')), 'scale estimator/protocol/component provenance differs')


def _coverage(value, events):
    bindings = value['bindings']
    inputs = _bound(bindings['inputs'])
    sources = {}
    for row in inputs['rgb']:
        identity = row['identity']
        key = (identity['branch'], identity['camera'], identity['frame'])
        _require(key not in sources, 'duplicate accepted RGB identity')
        sources[key] = row
    scene = _bound(bindings['scene_freeze'])
    manifest = _bound(bindings['scene_manifest'])
    manifest_frames = {(int(c['id']), f['frame_id']): f for c in manifest['cameras'] for f in c['frames']}
    required = {(c, f, pair) for c in TRAINING_CAMERAS for pair in KEYFRAMES for f in (pair, pair+1)}
    for component in ('S2', 'M0', 'M1', 'M2', 'N0', 'N1', 'N2'):
        result = _bound(bindings[component])
        _require(result.get('status') == 'complete' and result.get('component') == component and
                 any(e.get('event') == 'finish' and e.get('status') == 'complete' and e.get('result') == bindings[component]
                     for e in events), 'complete ledger-bound ' + component + ' result required')
        if value['record_kind'] == 'actual':
            worker = _bound(result['configuration'])
            _require(worker['component'] == component and worker['configuration'] == bindings['config'] and
                     worker['inputs'] == bindings['inputs'], 'native prerequisite configuration/input lineage differs')
        if component.startswith('N'):
            _require(result.get('inputs') == bindings['inputs'], 'neighbor accepted input manifest differs')
            references = [r['reference'] for r in result['records']]
            _require(len(references) == len(set(references)) and set(TRAINING_CAMERAS) <= set(references), 'neighbor full-rig coverage differs')
            for row in result['records']:
                if row['reference'] not in TRAINING_CAMERAS:
                    continue
                neighbors = row['neighbors']
                _require(row['status'] == 'complete' and len(neighbors) == len(set(neighbors)) == 3 and
                         row['reference'] not in neighbors and set(neighbors) <= set(TRAINING_CAMERAS), 'neighbor membership differs')
            continue
        rows = {}
        for row in result['rows']:
            i = row['identity']
            if i['branch'] != 'reconstruction':
                continue
            key = (i['camera'], i['frame'], i['pair_start'])
            _require(key not in rows, 'duplicate native prerequisite identity')
            rows[key] = row
        _require(required <= set(rows), 'missing full-rig native prerequisite coverage')
        for c, f, pair in required:
            row = rows[c, f, pair]
            source = sources.get(('reconstruction', c, f))
            _require(source is not None and row['source_rgb_sha256'] == source['rgb']['sha256'] and
                     row['K'] == source['K'] == scene['cameras'][str(c)]['K'] and
                     row['source_rgb_sha256'] == manifest_frames[c, f]['sha256'] and
                     row['grid'] == source['grid'], 'native prerequisite input geometry differs')
            if value['record_kind'] == 'actual':
                for record in (source['rgb'], row['valid'], row['semantic_static'] if component == 'S2' else row['changing']):
                    _require(verify_record(record) == record, 'native prerequisite bytes changed')
    return 810


def admit_review(value, ledger, storage, *, deep=True):
    """Read-only proposal admission; no reservation, dispatch or DO authority.

    deep=False is only for callers that already re-derived the D* decision
    outside the ledger lock (DO reservation), because that re-derivation reads
    the shared ledger.
    """
    request = parse_request(value)
    bindings = request['bindings']
    actual = request['record_kind'] == 'actual'
    segmentation = _bound(bindings['segmentation_decision'])
    _require(segmentation.get('schema') == 'plan067-qualitative-decision/v1' and segmentation.get('status') == 'ready' and
             segmentation.get('selected_candidate_ids') == ['S2'] and segmentation.get('actual_human_review') is actual,
             'exact ready S2 decision required')
    if actual:
        from .final_render_contract import FROZEN_SCOPE, ROOT
        relative, sha256, size = FROZEN_SCOPE['segmentation_decision']
        _require(bindings['segmentation_decision'] == dict(path=str((ROOT/relative).resolve()), sha256=sha256, bytes=size),
                 'frozen human S2 decision differs')
    else:
        _require(segmentation.get('record_kind') == 'fixture', 'fixture S2 decision label required')
    qualification = _bound(bindings['qualification'])
    if actual:
        from .s1_validation_contract import validate_wrapper
        validate_wrapper(qualification, qualification['semantic_amendment'], bindings['config'])
    else:
        _require(qualification.get('status') == 'passed' and qualification.get('record_kind') == 'fixture', 'passing fixture qualification required')
    _validate_depth(request, deep=deep)
    validate_scene_bindings(request)
    events = ledger.events()
    validate_budget_configuration(request, ledger.config)
    _require(not any(state['event'] == 'reserve' for state in ledger.states(events).values()), 'active allocation blocks REVIEW admission')
    ids = {allocation['id'] for allocation in request['allocations']}
    consumed = {event.get('job_id') for event in events if event.get('event') in
                ('reserve', 'finish', 'account', 'checkpoint', 'checkpoint_resume')}
    _require(not ids & consumed, 'consumed prospective identity cannot be reused')
    coverage = _coverage(request, events)
    totals = ledger.totals(events)
    gpu = sum(a['seconds'] for a in request['allocations'] if a['resource'] == 'gpu')
    cpu = sum(a['seconds'] for a in request['allocations'] if a['resource'] == 'cpu')
    for resource, seconds, key in [('gpu', gpu, 'gpu_total_seconds_limit'),
                                   ('cpu', cpu, 'cpu_prepare_score_report_seconds_limit'),
                                   ('setup', 0, 'setup_wall_seconds_limit')]:
        _require(totals[resource]['elapsed_seconds'] + totals[resource]['reserved_seconds'] + seconds <= ledger.config[key],
                 resource.upper() + ' cumulative ceiling exhausted')
    _require(request['cpu_workers_limit'] <= ledger.config['cpu_max_workers'] and
             request['device_bytes_limit'] <= ledger.config['gpu_peak_device_gib_limit']*2**30, 'worker/device ceiling exceeded')
    for key in ('artifact_bytes', 'download_bytes', 'free_disk_bytes'):
        _require(type(storage[key]) is int and storage[key] >= 0, 'invalid live storage reading')
    _require(storage['artifact_bytes'] + request['artifact_bytes_limit'] <= ledger.config['new_artifact_disk_gib_limit']*2**30,
             'artifact cumulative ceiling exhausted')
    _require(storage['free_disk_bytes'] >= request['artifact_bytes_limit'], 'insufficient free disk')
    _require(storage['download_bytes'] <= ledger.config['new_download_gib_limit']*2**30, 'download cumulative ceiling exhausted')
    return ReviewAdmission(object_hash(request), coverage, gpu, cpu, False, BLOCKERS)


def validate_initializer(value, arm, receipt, arrays):
    """Check selected-depth native-array provenance at the CPU adapter boundary."""
    request = parse_request(value)
    _require(arm in compositions(request['depth_candidate']), 'unknown extended initializer arm')
    _validate_depth(request)
    validate_scene_bindings(request)
    expected = dict(request['initializer_contract'], arm=arm, composition=request['compositions'][arm])
    _require({key: receipt.get(key) for key in expected} == expected, 'initializer arm/isolation/normalization/units differ')
    from basketball_dense_fusion import validate
    validate(arrays)
    _require(set(receipt) == set(expected) | {'arrays_sha256', 'prerequisites', 'scene_manifest'}, 'complete initializer provenance receipt required')
    _require(receipt['arrays_sha256'] == initializer_arrays_hash(arrays), 'initializer arrays changed')
    composition = request['compositions'][arm]
    names = {'S2', 'D_fit', 'D_check', 'depth_decision', composition['motion'], composition['neighbors']}
    _require(receipt['prerequisites'] == {name: request['bindings'][name] for name in names} and
             receipt['scene_manifest'] == request['bindings']['scene_manifest'], 'initializer prerequisite lineage differs')
    return dict(schema='plan069-final-render-initializer-validation/v1', status='passed', arm=arm,
                point_count=len(arrays['positions']), request_sha256=object_hash(request),
                native_adapter_qualified=False, execution_authorized=False)


def validate_budget_configuration(value, config):
    """Accept only the separately approved caps over original science.

    The configuration bound to historical worker requests and qualification is
    unchanged. This approval supplies resource caps only, never native authority.
    Returns the amended configuration; config=None only derives it.
    """
    baseline_record = value['bindings']['config']
    baseline = _bound(baseline_record)
    bound = value.get('budget_amendment')
    if bound is None:
        _require(config is None or config == baseline, 'ledger allocation configuration differs; approved budget amendment required')
        return baseline
    _require(type(bound) is dict and set(bound) in ({'amendment', 'authorization'}, {'amendment', 'authorization', 'artifact_extension'}),
             'exact budget amendment and authorization records required')
    amendment = _bound(bound['amendment'])
    authorization = _bound(bound['authorization'])
    _require(baseline.get('new_download_gib_limit') == 60 and baseline.get('new_artifact_disk_gib_limit') == 150,
             'budget amendment requires historical 60/150 caps')
    expected = dict(schema='plan069-depth-cap-amendment/v1', status='REVIEW',
        historical_configuration={key: baseline_record[key] for key in ('sha256', 'bytes')},
        new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    _require(amendment == expected, 'exact 110/210 budget amendment differs from historical configuration')
    _require(authorization.get('schema') == 'plan069-depth-user-authorization/v1' and authorization.get('status') == 'DO' and
             authorization.get('cap_amendment') == bound['amendment'] and authorization.get('cap_approval') ==
             dict(schema='plan069-depth-cap-approval/v1', status='approved', amendment_sha256=object_hash(amendment)),
             'exact approved budget authorization required')
    if value['record_kind'] == 'actual':
        _require({key: baseline_record[key] for key in ('sha256', 'bytes')} ==
                 dict(sha256='298e0a3a6c6c30b92dbfd7c8fa55a3dfbca1dff801a67c0830cf47db0bd9f823', bytes=2625),
                 'actual historical configuration pin differs')
        _require({key: bound['authorization'][key] for key in ('sha256', 'bytes')} ==
                 dict(sha256='6026870067801494627766daeaaa1708e8bef89f87f241aa30162a66952938be', bytes=3190),
                 'actual budget approval is not the recorded user authorization')
    else:
        _require(authorization.get('record_kind') == 'fixture', 'budget authorization fixture label required')
    caps = dict(new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    if 'artifact_extension' in bound:
        caps = _artifact_extension(value, bound)
    if config is not None:
        _require(config == dict(baseline, **caps), 'ledger configuration differs outside exact approved budget caps')
    return dict(baseline, **caps)


def amended_configuration(value):
    """The ledger configuration a request's approved budget records establish."""
    return validate_budget_configuration(value, None)


# The user-approved final-render cap extensions, by amendment schema:
# v1 210 -> 260 GiB artifacts (AskUserQuestion, 2026-10-05);
# v2 260 -> 380 GiB artifacts and the GPU limit for 70k-step training (2026-10-07;
# the GPU limit was raised again to 252,000 s on 2026-10-08, which supersedes it).
ARTIFACT_EXTENSION_AUTHORIZATION = dict(sha256='5a6db07ea5918ecc1895e71adf59efb304093b8193f724b2e7251b16be2b7aa8', bytes=762)
LONG_TRAINING_EXTENSION_AUTHORIZATION = dict(sha256='fb580a7bb04adac730fe431bfa795ddd231d243bca49f04cac7c920d92fe1efb', bytes=1102)
LONG_TRAINING_ARTIFACT_GIB = 380


def _artifact_extension(value, bound):
    """Chain one approved final-render cap extension onto the 110/210 amendment.

    v1 raises artifacts to 260 GiB. v2 chains on the exact v1 extension and raises
    artifacts to 380 GiB and the cumulative GPU limit to its approved value.
    Returns the amended ledger caps.
    """
    extension = bound['artifact_extension']
    _require(type(extension) is dict and set(extension) == {'amendment', 'authorization'},
             'exact artifact extension amendment and authorization records required')
    amendment = _bound(extension['amendment'])
    authorization = _bound(extension['authorization'])
    v2 = amendment.get('schema') == 'plan069-final-render-cap-amendment/v2'
    _require(amendment.get('schema') in ('plan069-final-render-cap-amendment/v1', 'plan069-final-render-cap-amendment/v2') and
             amendment.get('status') == 'REVIEW' and
             amendment.get('base_amendment') == bound['amendment'] and amendment.get('new_download_gib_limit') == 110 and
             amendment.get('new_artifact_disk_gib_limit') == (LONG_TRAINING_ARTIFACT_GIB if v2 else 260),
             'exact final-render artifact extension differs')
    caps = dict(new_download_gib_limit=110, new_artifact_disk_gib_limit=amendment['new_artifact_disk_gib_limit'])
    if v2:
        _require(value.get('iterations') == 70000, 'v2 artifact extension covers only the 70k training endpoint')
        previous = amendment.get('previous_extension')
        _require(type(previous) is dict and set(previous) == {'amendment', 'authorization'},
                 'v2 artifact extension must chain the exact v1 extension')
        _require(_artifact_extension(value, dict(bound, artifact_extension=previous)) ==
                 dict(new_download_gib_limit=110, new_artifact_disk_gib_limit=260) and
                 _bound(previous['amendment']).get('schema') == 'plan069-final-render-cap-amendment/v1',
                 'v2 artifact extension must chain the exact v1 extension')
        baseline = _bound(value['bindings']['config'])
        gpu = amendment.get('new_gpu_total_seconds_limit')
        _require(type(gpu) is int and baseline['gpu_total_seconds_limit'] < gpu <= 3*baseline['gpu_total_seconds_limit'],
                 'v2 artifact extension requires a bounded GPU limit raise')
        caps['gpu_total_seconds_limit'] = gpu
    _require(authorization.get('schema') == 'plan069-final-render-cap-authorization/v1' and authorization.get('status') == 'DO' and
             authorization.get('amendment') == extension['amendment'] and
             authorization.get('approval') == dict(status='approved', amendment_sha256=object_hash(amendment)),
             'exact approved artifact extension authorization required')
    if value['record_kind'] == 'actual':
        pinned = LONG_TRAINING_EXTENSION_AUTHORIZATION if v2 else ARTIFACT_EXTENSION_AUTHORIZATION
        _require(pinned is not None and {key: extension['authorization'][key] for key in ('sha256', 'bytes')} == pinned,
                 'actual artifact extension is not the recorded user authorization')
    else:
        _require(authorization.get('record_kind') == 'fixture', 'artifact extension authorization fixture label required')
    return caps
