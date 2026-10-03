"""One-shot D7 native map generation on the accepted scale grid."""
import os
from pathlib import Path
import sys
import time

import numpy as np

from .config import load, training_cameras
from .depth_clips import SCHEMA as CONTEXT_SCHEMA
from .files import object_hash, file_record, load_array, read_json, verify_record, write_json
from .ledger import Ledger


SCHEMA = 'plan069-D7-maps-request/v1'
RESULT = 'plan069-D7-maps-result/v1'
JOB = 'plan069-D7-maps-001'
CLIP_CAMERAS = (1, 11, 21, 31)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _membership(context, inputs):
    cameras = training_cameras(load())
    _require(context.get('schema') == CONTEXT_SCHEMA and
             context.get('inputs') == inputs and
             len(context.get('rows', [])) == 4500 and
             len(context.get('anchors', [])) == 60,
             'complete accepted D7 context required')
    rows = {(row['camera'], row['frame']): row for row in context['rows']}
    _require(len(rows) == 4500 and set(rows) ==
             {(camera, frame) for camera in cameras for frame in range(50, 200)},
             'D7 context membership changed')
    anchors = {(row['camera'], row['frame']): row for row in context['anchors']}
    _require(len(anchors) == 60 and set(anchors) ==
             {(camera, frame) for camera in cameras for frame in (100, 175)},
             'D7 anchor membership changed')
    keys = sorted(anchors, key=lambda key: (key[1], key[0])) + sorted(
        {(camera, frame) for camera in CLIP_CAMERAS for frame in range(150, 200)}
        - set(anchors))
    _require(len(keys) == 256, 'D7 published map workload changed')
    return rows, anchors, keys


def _active_reservation(request, request_path, output):
    _require(request_path is not None and request.get('job_id') == JOB,
             'actual D7 request path and identity required')
    ledger_path = Path(request['ledger_path']).resolve()
    _require(output.resolve() == (ledger_path.parent / 'jobs' / JOB).resolve(),
             'actual D7 output path differs from shared reservation')
    config = dict(load(), new_download_gib_limit=110,
                  new_artifact_disk_gib_limit=210)
    state = Ledger(ledger_path, config).states().get(JOB, {})
    command = state.get('command', [])
    _require(state.get('event') == 'reserve' and
             state.get('evidence', {}).get('request') == file_record(request_path) and
             '--request' in command and '--output' in command and
             command[command.index('--request') + 1] == str(request_path) and
             command[command.index('--output') + 1] == str(output) and
             os.environ.get('VIPE_RESERVATION_START') == str(state.get('monotonic_start')),
             'active exact D7 GPU reservation required')
    return state


def pinned_source_manifest(source):
    """Bind every regular source file with paths relative to a pristine archive."""
    source = Path(source)
    rows = []
    for path in sorted(source.rglob('*')):
        _require(not path.is_symlink(), 'D7 pinned source symlink forbidden')
        if path.is_file():
            record = file_record(path)
            rows.append(dict(path=path.relative_to(source).as_posix(),
                sha256=record['sha256'], bytes=record['bytes']))
    _require(bool(rows), 'D7 pinned source manifest empty')
    return rows


def _native_backend(setup, qualification, output, deadline):
    """Load only the pinned Hypersim Small source and strict checkpoint."""
    import torch
    from .dav2_metric import DAV2MetricSmallAdapter
    from .depth_setup import _unpack_source
    source_archive = verify_record(setup['source_archive'])['path']
    extracted = output / 'verified-source'
    _unpack_source(source_archive, extracted, setup['source_revision'],
                   deadline=deadline)
    _require(qualification.get('source_archive') == setup['source_archive'] and
             qualification.get('source_files') == pinned_source_manifest(extracted),
             'D7 qualification source differs from pristine pinned archive')
    source = extracted / 'metric_depth'
    _require(source.is_dir() and (source / 'depth_anything_v2/dpt.py').is_file(),
             'pinned D7 source tree missing')
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(source))
    try:
        from depth_anything_v2 import dpt
        _require(Path(dpt.__file__).resolve() == (source / 'depth_anything_v2/dpt.py').resolve(),
                 'D7 native module origin differs from pinned source')
        DepthAnythingV2 = dpt.DepthAnythingV2
        model = DepthAnythingV2(encoder='vits', features=64,
            out_channels=[48, 96, 192, 384], max_depth=20)
        weights = torch.load(verify_record(setup['checkpoint'])['path'],
                             map_location='cpu', weights_only=True)
        model.load_state_dict(weights, strict=True)
        _require(torch.cuda.is_available(), 'approved D7 GPU unavailable')
        model = model.to('cuda', dtype=torch.float32).eval()
        return DAV2MetricSmallAdapter(model)
    finally:
        sys.path.pop(0)


def run_d7_maps(request, output, *, backend=None, request_path=None):
    """Publish 60 anchors and 196 clip extras, each with immutable raw depth."""
    import cv2
    from basketball_scale import undistortion
    from .depth_extension import CONFIG, _prediction

    _require(request.get('schema') == SCHEMA and request.get('candidate') == 'D7' and
             request.get('record_kind') in ('fixture', 'actual'),
             'D7 request schema/candidate/origin changed')
    output = Path(output)
    _require(output.name == request.get('job_id') and not output.exists(),
             'immutable D7 map output identity changed or exists')
    verify_record(request['inputs'])
    inputs = read_json(request['inputs']['path'])
    context = read_json(verify_record(request['context'])['path'])
    rows, anchors, keys = _membership(context, request['inputs'])
    depth_rows = inputs.get('depth', [])
    accepted_anchors = {(row['identity']['camera'], row['identity']['frame']): row
        for row in depth_rows
        if row.get('identity', {}).get('branch') == 'depth'}
    _require(len(depth_rows) == len(accepted_anchors) == 60 and
             set(accepted_anchors) == set(anchors),
             'accepted D7 depth anchors changed')
    if request['record_kind'] == 'actual':
        _require(all(row.get('source_rgb_grid') == ('scale-opencv-integer' if
                     (row['camera'], row['frame']) in anchors else 'distorted-opencv-integer') and
                     row.get('accepted_anchor') is ((row['camera'], row['frame']) in anchors)
                     for row in rows.values()), 'D7 exact accepted anchor context required')
        state = _active_reservation(request, request_path, output)
        deadline = state['monotonic_start'] + state['seconds'] - 30
        setup = read_json(verify_record(request['setup'])['path'])
        _require(setup.get('schema') == 'plan069-depth-setup-result/v1' and
                 setup.get('status') == 'complete' and setup.get('candidate') == 'D7',
                 'successful pinned D7 setup required')
        qualification = read_json(verify_record(request['qualification'])['path'])
        _require(qualification.get('setup') == request['setup'] and
                 any(row.get('record') == setup['checkpoint'] for row in qualification.get('assets', [])),
                 'D7 setup checkpoint differs from exact qualification asset')
        _require(backend is None, 'actual D7 cannot inject a fixture backend')
    else:
        _require(backend is not None and request.get('job_id') ==
                 'plan069-D7-maps-fixture-001', 'explicit D7 CPU fixture backend required')
        deadline = time.monotonic() + 1800
    _require(getattr(backend, 'component', 'D7') == 'D7',
             'D7 backend identity changed')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    started = time.monotonic()
    try:
        if request['record_kind'] == 'actual':
            backend = _native_backend(setup, qualification, output, deadline)
        calibration = {row['camera_id']: row for row in read_json(
            verify_record(context['calibration'])['path'])['cameras']}
        remaps = {camera: undistortion(calibration[camera])
                  for camera in {camera for camera, _ in keys}}
        result_rows = []
        from .scale import evaluate
        config = load()
        provenance = dict(inputs=request['inputs'], component='D7',
            component_sha256=object_hash(dict(candidate='D7', setup=request.get('setup'),
                configuration=file_record(CONFIG))))
        fit_predictions, check_predictions = {}, {}
        fit_rows = [accepted_anchors[camera, 100] for camera in training_cameras(config)]
        check_rows = [accepted_anchors[camera, 175] for camera in training_cameras(config)]
        fit = None
        scales = {}
        for camera, frame in keys:
            _require(time.monotonic() < deadline, 'D7 GPU map deadline exceeded')
            source = rows[camera, frame]
            valid = load_array(source['valid'])
            _require(valid.shape == (540, 960) and valid.dtype == np.bool_ and
                     source['grid'] == 'scale-opencv-integer',
                     'D7 accepted scale footprint/grid changed')
            K, maps = remaps[camera]
            _require(np.array_equal(K, source['K']), 'D7 camera intrinsics changed')
            if (camera, frame) in anchors:
                anchor = anchors[camera, frame]
                _require(anchor['accepted_rgb' if source.get('accepted_anchor') else 'source_rgb'] == source['source_rgb'] and
                         anchor['accepted_rgb'] == accepted_anchors[camera, frame]['rgb'] and
                         np.array_equal(accepted_anchors[camera, frame]['K'], K) and
                         accepted_anchors[camera, frame]['grid'] == 'scale-opencv-integer',
                         'D7 frozen anchor binding changed')
                image = cv2.imread(verify_record(anchor['accepted_rgb'])['path'],
                                   cv2.IMREAD_COLOR)
                kind, input_record = 'anchor', anchor['accepted_rgb']
            else:
                distorted = cv2.imread(verify_record(source['source_rgb'])['path'],
                                       cv2.IMREAD_COLOR)
                _require(distorted is not None and distorted.shape == (540, 960, 3),
                         'D7 source frame grid changed')
                image = cv2.remap(distorted, *maps, cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT)
                kind, input_record = 'clip-extra', source['source_rgb']
            _require(image is not None and image.shape == (540, 960, 3),
                     'D7 scale image grid changed')
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            prediction = backend.predict(rgb, K, valid)
            values, accepted, raw, native_points = _prediction(
                prediction, 'camera_z_metres', valid)
            _require(native_points is None, 'D7 must produce camera-z depth only')
            path = output / f'camera{camera}-frame{frame}.npz'
            with path.open('xb') as stream:
                np.savez_compressed(stream, depth=values, valid=accepted,
                                    raw_values=raw)
            result_rows.append(dict(camera=camera, frame=frame, kind=kind,
                role=source['role'], timestamp=source['timestamp'], accepted_anchor=(kind == 'anchor'),
                source_rgb=input_record if kind == 'anchor' else source['source_rgb'], inference_rgb=input_record,
                context=request['context'], inputs=request['inputs'],
                source_rgb_grid=source.get('source_rgb_grid',
                    'scale-opencv-integer' if kind == 'anchor' else 'distorted-opencv-integer'),
                grid='scale-opencv-integer', K=source['K'], domain='camera_z_metres',
                prediction=file_record(path), metadata=prediction.metadata))
            if frame in (100, 175):
                (fit_predictions if frame == 100 else check_predictions)[camera] = file_record(path)
            if len(fit_predictions) == 30 and fit is None:
                fit = evaluate(fit_rows, fit_predictions, config, provenance=provenance)
                fit['component'] = 'D7'
                write_json(output / 'scale-fit.json', fit)
                scales['fit'] = file_record(output / 'scale-fit.json')
                if fit['status'] != 'passed':
                    proof = request.get('qualitative_admission')
                    _require(isinstance(proof, dict),
                        'failed D7 scale fit requires separate qualitative admission')
                    document = read_json(verify_record(proof)['path'])
                    _require(document == dict(schema='plan069-depth-qualitative-admission/v1',
                        record_kind=request['record_kind'], component='D7',
                        inputs=request['inputs'], purpose='qualitative-only', status='admitted'),
                        'D7 qualitative admission binding changed')
            if len(check_predictions) == 30 and 'check' not in scales:
                if fit['status'] == 'passed':
                    check = evaluate(check_rows, check_predictions, config,
                        provenance=provenance, frozen_fit=scales['fit'])
                else:
                    from .depth_metric_scale import selection_support
                    check = selection_support(check_rows, check_predictions, config,
                        provenance=provenance, frozen_fit=scales['fit'])
                check['component'] = 'D7'
                write_json(output / 'scale-check.json', check)
                scales['check'] = file_record(output / 'scale-check.json')
        _require(len(result_rows) == 256, 'incomplete D7 published map count')
        result = dict(schema=RESULT, status='complete',
            record_kind=request['record_kind'], candidate='D7', job_id=request['job_id'],
            context=request['context'], inputs=request['inputs'],
            setup=request.get('setup'), rows=result_rows, scales=scales,
            engineering_eligibility=('passed' if fit['status'] == 'passed' and
                read_json(scales['check']['path'])['status'] == 'passed' else 'blocked'),
            qualitative_admission=request.get('qualitative_admission'),
            anchor_maps=60, clip_extra_maps=196, unique_published_maps=256,
            elapsed_seconds=time.monotonic() - started)
        write_json(output / 'result.json', result)
        return result
    except BaseException as error:
        write_json(output / 'failure.json', dict(schema='plan069-D7-maps-failure/v1',
            status='failed', candidate='D7', job_id=request['job_id'],
            completed_map_rows=len(result_rows) if 'result_rows' in locals() else 0,
            error=f'{type(error).__name__}: {error}',
            elapsed_seconds=time.monotonic() - started))
        raise
