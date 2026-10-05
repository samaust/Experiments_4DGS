"""One reserved single-image PointMap workload for D5, D6 and D8."""
import os
import sys
from pathlib import Path
import time

import numpy as np

from .config import load, training_cameras
from .depth_clips import SCHEMA as CONTEXT_SCHEMA, materialize_role
from .depth_extension import CONFIG, _prediction
from .files import file_record, load_array, object_hash, read_json, verify_record, write_json
from .ledger import Ledger
from .scale import evaluate


SCHEMA = 'plan069-depth-single-maps-request/v1'
RESULT = 'plan069-depth-single-maps-result/v1'
CANDIDATES = ('D5', 'D6', 'D8')
CLIP_CAMERAS = (1, 11, 21, 31)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _membership(context, inputs, config):
    cameras = training_cameras(config)
    _require(context.get('schema') == CONTEXT_SCHEMA and context.get('inputs') == inputs
             and len(context.get('rows', [])) == 4500
             and len(context.get('anchors', [])) == 60,
             'complete accepted single-image context required')
    rows = {(row['camera'], row['frame']): row for row in context['rows']}
    anchors = {(row['camera'], row['frame']): row for row in context['anchors']}
    _require(len(rows) == 4500 and set(rows) ==
             {(c, f) for c in cameras for f in range(50, 200)} and len(anchors) == 60
             and set(anchors) == {(c, f) for c in cameras for f in (100, 175)},
             'single-image context membership changed')
    return rows, anchors


def _input_lineage(context, inputs):
    """Bind every permitted context RGB to the immutable accepted input row."""
    decoded = {(r['identity']['camera'], r['identity']['frame']): r
               for r in inputs.get('rgb', []) if r['identity']['branch'] == 'calibration'}
    accepted = {(r['identity']['camera'], r['identity']['frame']): r for r in inputs['depth']}
    for row in context['rows']:
        key = row['camera'], row['frame']
        source = decoded.get(key)
        anchor = key[1] in (100, 175)
        _require(source is not None and row.get('decoded_source_rgb') == source['rgb'] and
                 row.get('source_video') == source['source_video'] and
                 row.get('source_rgb_grid') == ('scale-opencv-integer' if anchor
                     else 'distorted-opencv-integer') and row.get('accepted_anchor') is anchor and
                 row['source_rgb'] == (accepted[key]['rgb'] if anchor else source['rgb']),
                 'accepted single-image RGB source lineage changed')


def _qualitative_admission(request):
    record = request.get('qualitative_admission')
    _require(isinstance(record, dict), 'failed fit requires separate qualitative-only admission')
    document = read_json(verify_record(record)['path'])
    _require(document == dict(schema='plan069-depth-qualitative-admission/v1',
        record_kind=request['record_kind'], component=request['candidate'],
        inputs=request['inputs'], purpose='qualitative-only', status='admitted'),
        'qualitative-only admission differs from candidate or inputs')


def _actual_gate(request, request_path, output):
    """Rehash admitted qualification and source/assets before constructing models."""
    from .depth_admission import review as admit
    from .moge_setup import source_tree_records
    candidate = request['candidate']
    job = f'plan069-{candidate}-maps-001'
    _require(request_path is not None and request['job_id'] == job,
             'actual request path and exact map identity required')
    request_path = Path(request_path).resolve()
    ledger_path = Path(request['ledger_path']).resolve()
    _require(output.resolve() == ledger_path.parent / 'jobs' / job,
             'actual output differs from shared reservation')
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    ledger = Ledger(ledger_path, config)
    events = ledger.events()
    state = ledger.states(events).get(job, {})
    command = state.get('command', [])
    _require(state.get('event') == 'reserve' and
             state.get('evidence', {}).get('request') == file_record(request_path) and
             state.get('evidence', {}).get('executable') == file_record(sys.executable) and
             state.get('evidence', {}).get('admission') == request['admission'] and
             '--request' in command and '--output' in command and
             command[command.index('--request') + 1] == str(request_path) and
             command[command.index('--output') + 1] == str(output.resolve()) and
             os.environ.get('VIPE_RESERVATION_START') == str(state.get('monotonic_start')),
             'active exact single-image GPU reservation required')
    deadline = state['monotonic_start'] + state['seconds'] - 30
    _require(time.monotonic() < deadline, 'single-image reservation deadline exhausted')
    review = read_json(verify_record(request['review'])['path'])
    proposal = next(r for r in review['proposals'] if r['candidate'] == candidate)
    authorization = read_json(verify_record(request['authorization'])['path'])
    grant = next(r for r in authorization['candidate_approvals'] if r['candidate'] == candidate)
    admission = read_json(verify_record(request['admission'])['path'])
    qualified = read_json(verify_record(request['qualification'])['path'])
    _require(admission.get('schema') == 'plan069-depth-admission-result/v1' and
             admission.get('status') == 'passed' and admission.get('candidate') == candidate and
             admission.get('proposal_sha256') == object_hash(proposal) and
             all(admission.get(k) == request[k] for k in
                 ('review', 'authorization', 'source_review', 'qualification')) and
             all(admission.get(k) == qualified.get(k) for k in ('commercial', 'assets', 'runtime')),
             'exact admitted proposal and qualification binding required')
    completed_setup = admission.get('completed_setup')
    if completed_setup is not None:
        _require(completed_setup == request['setup'],
                 'worker setup differs from credited admission')
    _require(completed_setup is not None,
             'new native slot requires completed setup stage proof')
    live = admission['live']
    blockers = admit(proposal, config=config, commercial=qualified['commercial'],
        assets=qualified['assets'], runtime=qualified['runtime'], live=live,
        source_review=request['source_review'], approval=grant,
        cap_amendment=authorization['cap_amendment'], cap_approval=authorization['cap_approval'],
        ledger_head_sha256=live['ledger_head_sha256'], now_unix=live['sampled_unix'],
        completed_setup=completed_setup, setup_events=events, run_root=ledger_path.parent)
    _require(not blockers, 'native qualification changed: ' + '; '.join(blockers))
    if completed_setup is not None:
        from .budgets import budget_snapshot
        from .depth_map_allowance import check_slot_byte_budget
        allocation_events = [event for event in events if event.get('event') == 'depth_attempt_authorized'
                             and event.get('candidate') == candidate]
        _require(len(allocation_events) == 1, 'exact map slot byte authorization required')
        check_slot_byte_budget(proposal, allocation_events[0]['slot_byte_budget'],
                               ledger_path.parent, budget_snapshot(ledger_path.parent))
    setup = read_json(verify_record(request['setup'])['path'])
    recovered = setup.get('schema') == 'plan069-depth-setup-recovery-result/v1'
    if recovered:
        from .setup_recovery_core import accepted_setup
        _, setup_job = accepted_setup(candidate, request['setup'], events, ledger_path.parent)
    _require(setup.get('schema') in ('plan069-depth-setup-result/v1', 'plan069-depth-setup-recovery-result/v1') and
             setup.get('status') == 'complete' and setup.get('record_kind') == 'actual' and
             setup.get('candidate') == candidate and setup.get('job_id') ==
                 (setup_job if recovered else f'plan069-{candidate}-setup-001') and
             (recovered or (setup.get('review') == request['review'] and
                            setup.get('authorization') == request['authorization'])) and
             setup.get('source_revision') == proposal['candidate_config']['code']['revision'] and
             setup.get('weight_revision') == proposal['candidate_config']['weights']['revision'],
             'successful exact native setup required')
    runtime = read_json(verify_record(qualified['runtime']['receipt'])['path'])
    _require(runtime.get('setup') == request['setup'] and
             runtime.get('python_executable') == str(Path(sys.executable).absolute()),
             'runtime qualification must bind exact setup and interpreter')
    verify_record(setup['source_archive'])
    if candidate in ('D5', 'D6'):
        _require(source_tree_records(setup['source_dir']) == setup.get('source_tree'),
                 'native source tree differs from accepted setup')
        assets = qualified['assets']
        _require(len(assets) == 1 and assets[0]['path'] == 'model.pt' and
                 assets[0]['record'] == verify_record(setup['checkpoint']),
                 'qualified MoGe checkpoint differs from setup')
    else:
        _require(setup.get('assets') == qualified['assets'], 'qualified PointMap assets differ')
        verify_record(setup['native_source'])
    return deadline, setup



def _check_actual_slot(request):
    if request['record_kind'] != 'actual':
        return
    from .budgets import budget_snapshot
    from .depth_map_allowance import check_slot_byte_budget
    ledger_path = Path(request['ledger_path']).resolve()
    events = Ledger(ledger_path, load()).events()
    allocations = [event for event in events if event.get('event') == 'depth_attempt_authorized'
                   and event.get('candidate') == request['candidate']]
    _require(len(allocations) == 1, 'exact whole-slot map authorization required')
    budget = allocations[0].get('slot_byte_budget')
    if budget is None:
        _require(request['candidate'] not in (*CANDIDATES,'D11'), 'new native slot whole-slot byte proof required')
        return
    review = read_json(verify_record(request['review'])['path'])
    proposal = next(row for row in review['proposals'] if row['candidate'] == request['candidate'])
    check_slot_byte_budget(proposal, budget, ledger_path.parent, budget_snapshot(ledger_path.parent))



def _npz_write_bound(*arrays):
    """Array payload plus ample NPY/ZIP/DEFLATE overhead before opening output."""
    payload = sum(array.nbytes for array in arrays)
    return (payload * 101 + 99) // 100 + 2**20

def _actual_output_guard(request, output):
    """Use bounded map-directory scans between full admission/terminal checks."""
    if request['record_kind'] != 'actual':
        return lambda additional_bytes=0: None
    from .budgets import directory_bytes
    from .depth_map_allowance import owned_slot_bytes
    root = Path(request['ledger_path']).resolve().parent
    allocations = [event for event in Ledger(root / 'ledger.jsonl', load()).events()
                   if event.get('event') == 'depth_attempt_authorized' and
                   event.get('candidate') == request['candidate']]
    _require(len(allocations) == 1, 'exact whole-slot map authorization required')
    budget = allocations[0].get('slot_byte_budget')
    if budget is None:
        _require(request['candidate'] not in (*CANDIDATES,'D11'), 'new native slot whole-slot byte proof required')
        return lambda additional_bytes=0: None
    review = read_json(verify_record(request['review'])['path'])
    proposal = next(row for row in review['proposals'] if row['candidate'] == request['candidate'])
    other_owned = owned_slot_bytes(root, request['candidate']) - directory_bytes(output)
    available = proposal['allocation']['artifact_bytes'] - budget['shared_setup_artifact_bytes'] - other_owned

    def check(additional_bytes=0):
        _require(type(additional_bytes) is int and additional_bytes >= 0 and
                 directory_bytes(output) + additional_bytes <= available,
                 'next map output exceeds remaining whole-slot artifact headroom')
    check()
    return check

def _native_backend(candidate, setup_record):
    if candidate in ('D5', 'D6'):
        from .moge_native import load_adapter
        return load_adapter(candidate, setup_record)
    from .native_d8 import load as load_pointmap
    return load_pointmap(read_json(verify_record(setup_record)['path']))


def run_maps(request, output, *, backend=None, request_path=None):
    """Fit frame100 first, then frozen check anchors and 196 unique clip extras."""
    import cv2
    candidate = request.get('candidate')
    _require(request.get('schema') == SCHEMA and candidate in CANDIDATES
             and request.get('record_kind') in ('fixture', 'actual'),
             'single-image map request schema/candidate/origin changed')
    config = load()
    output = Path(output)
    _require(output.name == request.get('job_id') and not output.exists(),
             'immutable single-image map output identity changed or exists')
    inputs = read_json(verify_record(request['inputs'])['path'])
    _require(inputs.get('schema') == 'vipe-benchmark-inputs/v1'
             and inputs.get('status') == 'prepared', 'accepted input manifest required')
    context = read_json(verify_record(request['context'])['path'])
    rows, anchors = _membership(context, request['inputs'], config)
    _input_lineage(context, inputs)
    input_anchors = {(r['identity']['camera'], r['identity']['frame']): r
                     for r in inputs['depth']}
    _require(len(inputs['depth']) == len(input_anchors) == 60 and
             set(input_anchors) == set(anchors) and
             all(r['identity']['branch'] == 'depth' for r in inputs['depth']), 'accepted depth anchor membership changed')
    extension = read_json(CONFIG)
    component_hash = object_hash(dict(component=candidate,
        candidate=extension['candidates'][candidate], extension_configuration=file_record(CONFIG)))
    if request['record_kind'] == 'actual':
        _require(backend is None, 'actual maps cannot inject a fixture backend')
        deadline, _ = _actual_gate(request, request_path, output)
    else:
        _require(backend is not None and request['job_id'] ==
                 f'plan069-{candidate}-maps-fixture-001', 'explicit CPU fixture backend required')
        deadline = time.monotonic() + 1800
    if backend is not None:
        _require(getattr(backend, 'component', None) == candidate, 'backend candidate differs')
    # Validate every accepted anchor before any constructor or inference.
    images = {}
    for key, anchor in anchors.items():
        source, accepted = rows[key], input_anchors[key]
        _require(anchor['source_rgb'] == source.get('decoded_source_rgb', source['source_rgb']) and
                 anchor['accepted_rgb'] == accepted['rgb'] and source['source_rgb'] == accepted['rgb'] and
                 accepted['grid'] == source['grid'] == 'scale-opencv-integer' and
                 np.array_equal(accepted['K'], source['K']), 'frozen anchor binding changed')
        image = cv2.imread(verify_record(accepted['rgb'])['path'], cv2.IMREAD_COLOR)
        _require(image is not None and image.shape == (540, 960, 3), 'accepted anchor grid changed')
        valid = load_array(accepted['valid'])
        _require(valid.shape == (540, 960) and valid.dtype == np.bool_ and
                 np.array_equal(valid, load_array(source['valid'])), 'accepted footprint changed')
        with load_array(accepted['samples']) as geometry:
            _require(np.array_equal(geometry['K'], accepted['K']) and
                     np.array_equal(geometry['valid'] > 0, valid) and
                     geometry['uv'].ndim == 2 and geometry['uv'].shape[1] == 2 and
                     geometry['camera_z'].shape == (len(geometry['uv']),) and
                     np.isfinite(geometry['uv']).all(), 'accepted scale sample geometry changed')
        images[key] = (cv2.cvtColor(image, cv2.COLOR_BGR2RGB), valid)
    # Materialize and validate clip context before loading any native model.
    clips = {}
    for camera in CLIP_CAMERAS:
        frames, valid, source_rows = materialize_role(request['context'], camera, 'check')
        _require(frames.shape == (50, 540, 960, 3) and frames.dtype == np.uint8 and
                 valid.shape == (540, 960) and valid.dtype == np.bool_ and
                 [r['frame'] for r in source_rows] == list(range(150, 200)) and
                 all(r == rows[camera, r['frame']] for r in source_rows),
                 'accepted clip context changed')
        clips[camera] = frames, valid, source_rows
    from .moge_metric import supplied_horizontal_fov
    for camera in training_cameras(config):
        supplied_horizontal_fov(np.asarray(rows[camera, 100]['K']), 960, 540)
    output_guard = _actual_output_guard(request, output)
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    started = time.monotonic()
    result_rows = []
    provenance = dict(inputs=request['inputs'], component_sha256=component_hash, component=candidate)
    try:
        _require(time.monotonic() < deadline, 'single-image preflight exhausted reservation')
        if request['record_kind'] == 'actual':
            backend = _native_backend(candidate, request['setup'])
        _require(getattr(backend, 'component', None) == candidate, 'native candidate differs')
        def infer(key, rgb, valid, kind):
            output_guard()
            _require(time.monotonic() < deadline, 'single-image GPU map deadline exceeded')
            source = rows[key]
            prediction = backend.predict(rgb, np.asarray(source['K'], np.float64), valid)
            _require(time.monotonic() < deadline, 'single-image native call exceeded deadline')
            values, accepted, raw, points = _prediction(prediction, 'camera_z_metres', valid)
            _require(points is not None, 'single-image candidate requires native PointMap')
            path = output / f'camera{key[0]}-frame{key[1]}.npz'
            output_guard(_npz_write_bound(values, accepted, raw, points))
            with path.open('xb') as stream:
                np.savez_compressed(stream, depth=values, valid=accepted,
                                    raw_values=raw, native_points=points)
            record = file_record(path)
            result_rows.append(dict(camera=key[0], frame=key[1], kind=kind,
                role=source['role'], timestamp=source['timestamp'],
                source_rgb=source['source_rgb'],
                source_rgb_grid=source.get('source_rgb_grid',
                    'scale-opencv-integer' if kind == 'anchor' else 'distorted-opencv-integer'),
                inference_rgb=(anchors[key]['accepted_rgb']
                    if kind == 'anchor' else source['source_rgb']),
                context=request['context'], inputs=request['inputs'],
                grid='scale-opencv-integer', K=source['K'], domain='camera_z_metres',
                prediction=record, metadata=prediction.metadata))
            return record
        cameras = training_cameras(config)
        fit_predictions = {c: infer((c, 100), *images[c, 100], 'anchor') for c in cameras}
        fit = evaluate([input_anchors[c, 100] for c in cameras], fit_predictions,
                       config, provenance=provenance)
        fit['component'] = candidate
        write_json(output / 'scale-fit.json', fit)
        fit_record = file_record(output / 'scale-fit.json')
        if fit['status'] != 'passed':
            _qualitative_admission(request)
        check_predictions = {c: infer((c, 175), *images[c, 175], 'anchor') for c in cameras}
        if fit['status'] == 'passed':
            check = evaluate([input_anchors[c, 175] for c in cameras], check_predictions,
                             config, provenance=provenance, frozen_fit=fit_record)
        else:
            from .depth_metric_scale import selection_support
            check = selection_support([input_anchors[c, 175] for c in cameras], check_predictions,
                                      config, provenance=provenance, frozen_fit=fit_record)
        check['component'] = candidate
        write_json(output / 'scale-check.json', check)
        for camera in CLIP_CAMERAS:
            frames, valid, source_rows = clips[camera]
            for rgb, source in zip(frames, source_rows):
                key = camera, source['frame']
                if key[1] != 175:
                    infer(key, rgb, valid, 'clip-extra')
        _require(len(result_rows) == 256, 'incomplete single-image map workload')
        result = dict(schema=RESULT, status='complete', record_kind=request['record_kind'],
            candidate=candidate, job_id=request['job_id'], context=request['context'],
            inputs=request['inputs'], setup=request.get('setup'), admission=request.get('admission'),
            rows=result_rows, anchor_maps=60, clip_extra_maps=196, unique_published_maps=256,
            component_sha256=component_hash,
            scales=dict(fit=fit_record, check=file_record(output / 'scale-check.json')),
            engineering_eligibility='passed' if fit['status'] == check['status'] == 'passed' else 'blocked',
            physical_accuracy='unverified', elapsed_seconds=time.monotonic() - started)
        write_json(output / 'result.json', result)
        _check_actual_slot(request)
        return result
    except BaseException as error:
        write_json(output / 'failure.json', dict(schema='plan069-depth-single-maps-failure/v1',
            status='failed', candidate=candidate, job_id=request['job_id'],
            completed_map_rows=len(result_rows), error=f'{type(error).__name__}: {error}',
            elapsed_seconds=time.monotonic() - started))
        raise


def validate_result(result, request):
    """Check the complete immutable map/scale result at finish and publication."""
    config = load()
    candidate = request['candidate']
    context = read_json(verify_record(request['context'])['path'])
    sources, anchors = _membership(context, request['inputs'], config)
    expected = set(anchors) | {(c, f) for c in CLIP_CAMERAS for f in range(150, 200)}
    rows = result.get('rows', [])
    keys = [(r['camera'], r['frame']) for r in rows]
    _require(result.get('schema') == RESULT and result.get('status') == 'complete' and
             result.get('record_kind') == request['record_kind'] and
             result.get('candidate') == candidate and result.get('job_id') == request['job_id'] and
             all(result.get(k) == request.get(k) for k in ('inputs', 'context', 'setup', 'admission')) and
             len(keys) == len(set(keys)) == 256 and set(keys) == expected and
             result.get('anchor_maps') == 60 and result.get('clip_extra_maps') == 196 and
             result.get('unique_published_maps') == 256,
             'complete single-image result membership/provenance required')
    for key, row in zip(keys, rows):
        source = sources[key]
        _require(row['kind'] == ('anchor' if key in anchors else 'clip-extra') and
                 row['domain'] == 'camera_z_metres' and row['grid'] == 'scale-opencv-integer' and
                 row['inputs'] == request['inputs'] and row['context'] == request['context'] and
                 row['source_rgb'] == source['source_rgb'] and
                 row.get('source_rgb_grid') == source['source_rgb_grid'] and row['K'] == source['K'] and
                 row['role'] == source['role'] and row['timestamp'] == source['timestamp'],
                 'single-image result row source or grid changed')
        verify_record(row['prediction'])
    scales = result['scales']
    fit = read_json(verify_record(scales['fit'])['path'])
    check = read_json(verify_record(scales['check'])['path'])
    provenance = dict(inputs=request['inputs'], component=candidate,
                      component_sha256=result['component_sha256'])
    expected_hash = object_hash(dict(component=candidate,
        candidate=read_json(CONFIG)['candidates'][candidate], extension_configuration=file_record(CONFIG)))
    _require(result['component_sha256'] == expected_hash and
             fit.get('component') == check.get('component') == candidate and
             fit.get('role') == 'fit' and check.get('role') == 'selection' and
             fit.get('provenance') == check.get('provenance') == provenance and
             check.get('frozen_fit') == scales['fit'], 'frozen scale result binding changed')
    if fit['status'] != 'passed':
        _qualitative_admission(request)
        _require(check['status'] == 'blocked' and check.get('scale') is None,
                 'failed fit cannot acquire a check scale')
    else:
        _require(check.get('scale') == fit['scale'], 'selection cannot refit scale')
    eligibility = 'passed' if fit['status'] == check['status'] == 'passed' else 'blocked'
    _require(result.get('engineering_eligibility') == eligibility and
             result.get('physical_accuracy') == 'unverified', 'scale eligibility changed')
