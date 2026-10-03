"""One admitted native Marigold folder run for 60 anchors and 196 clip extras."""

from pathlib import Path
import sys
import time

import numpy as np

from .config import load
from .depth_clips import materialize_role
from .depth_extension import CONFIG, _prediction
from .depth_single_run import _actual_gate, _input_lineage, _membership
from .files import file_record, load_array, object_hash, read_json, verify_record, write_json
from .marigold_relative import MarigoldLogStage2Adapter, PROFILE
from .native_d11 import CachedD11Runtime, run_folder


SCHEMA = 'plan069-D11-maps-request/v1'
RESULT = 'plan069-D11-maps-result/v1'
JOB = 'plan069-D11-maps-001'
DOMAIN = 'relative_log'
CLIP_CAMERAS = (1, 11, 21, 31)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def run_maps(request, output, *, backend=None, request_path=None):
    """Retain native relative-log outputs without estimating any metric scale."""
    import cv2
    _require(request.get('schema') == SCHEMA and request.get('candidate') == 'D11' and
             request.get('record_kind') in ('fixture', 'actual'),
             'exact D11 map request required')
    output = Path(output)
    _require(output.name == request.get('job_id') and not output.exists(),
             'immutable D11 map output identity changed or exists')
    config = load()
    inputs = read_json(verify_record(request['inputs'])['path'])
    _require(inputs.get('schema') == 'vipe-benchmark-inputs/v1' and
             inputs.get('status') == 'prepared', 'accepted D11 input manifest required')
    context = read_json(verify_record(request['context'])['path'])
    rows, anchors = _membership(context, request['inputs'], config)
    _input_lineage(context, inputs)
    accepted = {(row['identity']['camera'], row['identity']['frame']): row
                for row in inputs['depth']}
    _require(len(inputs['depth']) == len(accepted) == 60 and set(accepted) == set(anchors) and
             all(row['identity']['branch'] == 'depth' for row in inputs['depth']),
             'accepted D11 anchor membership changed')
    if request['record_kind'] == 'actual':
        _require(backend is None, 'actual D11 cannot inject a fixture backend')
        deadline, setup = _actual_gate(request, request_path, output)
    else:
        _require(backend is not None and request['job_id'] == 'plan069-D11-maps-fixture-001',
                 'explicit D11 CPU fixture backend required')
        deadline, setup = time.monotonic() + 1800, None
    images = {}
    for key, anchor in anchors.items():
        source, original = rows[key], accepted[key]
        _require(anchor['source_rgb'] == source['decoded_source_rgb'] and
                 anchor['accepted_rgb'] == source['source_rgb'] == original['rgb'] and
                 original['grid'] == source['grid'] == 'scale-opencv-integer' and
                 np.array_equal(original['K'], source['K']), 'D11 accepted anchor binding changed')
        image = cv2.imread(verify_record(original['rgb'])['path'], cv2.IMREAD_COLOR)
        valid = load_array(original['valid'])
        _require(image is not None and image.shape == (540, 960, 3) and
                 valid.shape == (540, 960) and valid.dtype == np.bool_ and
                 np.array_equal(valid, load_array(source['valid'])),
                 'D11 accepted anchor grid or footprint changed')
        with load_array(original['samples']) as geometry:
            _require(np.array_equal(geometry['K'], original['K']) and
                     np.array_equal(geometry['valid'] > 0, valid),
                     'D11 accepted camera metadata changed')
        images[key] = cv2.cvtColor(image, cv2.COLOR_BGR2RGB), valid
    for camera in CLIP_CAMERAS:
        frames, valid, source_rows = materialize_role(request['context'], camera, 'check')
        _require(frames.shape == (50, 540, 960, 3) and frames.dtype == np.uint8 and
                 valid.shape == (540, 960) and valid.dtype == np.bool_ and
                 [row['frame'] for row in source_rows] == list(range(150, 200)) and
                 all(row == rows[camera, row['frame']] for row in source_rows),
                 'D11 accepted clip context changed')
        for rgb, source in zip(frames, source_rows):
            if source['frame'] != 175:
                images[camera, source['frame']] = rgb, valid
    ordered = sorted(images)
    _require(len(ordered) == 256, 'D11 unique native folder workload changed')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    started, result_rows = time.monotonic(), []
    component_hash = object_hash(dict(component='D11',
        candidate=read_json(CONFIG)['candidates']['D11'], extension_configuration=file_record(CONFIG)))
    native_receipt = None
    try:
        _require(time.monotonic() < deadline, 'D11 preflight exhausted reservation')
        if setup is not None:
            frames = [(f'camera{camera:02d}-frame{frame:03d}', images[camera, frame][0])
                      for camera, frame in ordered]
            predictions = run_folder(setup, frames, output / 'native-folder',
                                     interpreter=sys.executable,
                                     timeout_seconds=deadline - time.monotonic())
            native_receipt = file_record(output / 'native-folder/result.json')
            backend = MarigoldLogStage2Adapter(CachedD11Runtime(predictions))
        _require(getattr(backend, 'component', None) == 'D11', 'D11 backend candidate changed')
        for key in ordered:
            _require(time.monotonic() < deadline, 'D11 output deadline exceeded')
            rgb, valid = images[key]
            source = rows[key]
            prediction = backend.predict(rgb, np.asarray(source['K'], np.float64), valid)
            values, supported, raw, points = _prediction(prediction, DOMAIN, valid)
            _require(points is None and raw.dtype == np.float32 and
                     prediction.metadata.get('profile') == PROFILE,
                     'D11 native relative-log profile changed')
            path = output / f'camera{key[0]}-frame{key[1]}.npz'
            with path.open('xb') as stream:
                np.savez_compressed(stream, depth=values, valid=supported, raw_values=raw)
            result_rows.append(dict(camera=key[0], frame=key[1],
                kind='anchor' if key in anchors else 'clip-extra',
                role=source['role'], timestamp=source['timestamp'], source_rgb=source['source_rgb'],
                source_rgb_grid=source['source_rgb_grid'], accepted_anchor=source['accepted_anchor'],
                inputs=request['inputs'], context=request['context'], K=source['K'],
                grid='scale-opencv-integer', domain=DOMAIN, prediction=file_record(path),
                metadata=prediction.metadata))
        result = dict(schema=RESULT, status='complete', candidate='D11',
            record_kind=request['record_kind'], job_id=request['job_id'],
            inputs=request['inputs'], context=request['context'], setup=request.get('setup'),
            admission=request.get('admission'), rows=result_rows, profile=PROFILE,
            native_result=native_receipt, component_sha256=component_hash,
            anchor_maps=60, clip_extra_maps=196, unique_published_maps=256,
            domain=DOMAIN, engineering_eligibility='not_applicable',
            physical_accuracy='unverified', metric_scale='not_applicable', downstream='blocked',
            elapsed_seconds=time.monotonic() - started)
        _require(time.monotonic() < deadline, 'D11 result deadline exceeded')
        write_json(output / 'result.json', result)
        return result
    except BaseException as error:
        write_json(output / 'failure.json', dict(schema='plan069-D11-maps-failure/v1',
            status='failed', candidate='D11', job_id=request['job_id'],
            completed_map_rows=len(result_rows), error=f'{type(error).__name__}: {error}',
            elapsed_seconds=time.monotonic() - started))
        raise


def validate_result(result, request):
    """Recheck exact frozen map membership, provenance and nonmetric domain."""
    context = read_json(verify_record(request['context'])['path'])
    sources, anchors = _membership(context, request['inputs'], load())
    _input_lineage(context, read_json(verify_record(request['inputs'])['path']))
    expected = set(anchors) | {(camera, frame) for camera in CLIP_CAMERAS for frame in range(150, 200)}
    rows = result.get('rows', [])
    keys = [(row['camera'], row['frame']) for row in rows]
    component_hash = object_hash(dict(component='D11', candidate=read_json(CONFIG)['candidates']['D11'],
                                     extension_configuration=file_record(CONFIG)))
    _require(result.get('schema') == RESULT and result.get('status') == 'complete' and
             result.get('candidate') == 'D11' and result.get('record_kind') == request['record_kind'] and
             result.get('job_id') == request['job_id'] and result.get('profile') == PROFILE and
             all(result.get(field) == request.get(field) for field in ('inputs', 'context', 'setup', 'admission')) and
             len(keys) == len(set(keys)) == 256 and set(keys) == expected and
             result.get('anchor_maps') == 60 and result.get('clip_extra_maps') == 196 and
             result.get('unique_published_maps') == 256 and result.get('domain') == DOMAIN and
             result.get('component_sha256') == component_hash and result.get('scales') is None and
             result.get('metric_scale') == result.get('engineering_eligibility') == 'not_applicable' and
             result.get('downstream') == 'blocked' and result.get('physical_accuracy') == 'unverified',
             'complete nonmetric D11 result membership/provenance required')
    for key, row in zip(keys, rows):
        source = sources[key]
        _require(row.get('kind') == ('anchor' if key in anchors else 'clip-extra') and
                 row.get('domain') == DOMAIN and row.get('grid') == 'scale-opencv-integer' and
                 row.get('inputs') == request['inputs'] and row.get('context') == request['context'] and
                 all(row.get(field) == source[field] for field in
                     ('source_rgb', 'source_rgb_grid', 'accepted_anchor', 'K', 'role', 'timestamp')) and
                 row.get('metadata', {}).get('profile') == PROFILE,
                 'D11 frozen row source or native profile changed')
        with load_array(row['prediction']) as data:
            _require(set(data.files) == {'depth', 'valid', 'raw_values'} and
                     data['depth'].shape == data['valid'].shape == data['raw_values'].shape == (540, 960) and
                     data['depth'].dtype == data['raw_values'].dtype == np.float32 and
                     data['valid'].dtype == np.bool_ and np.isnan(data['depth'][~data['valid']]).all() and
                     np.isfinite(data['depth'][data['valid']]).all() and
                     np.array_equal(data['valid'], load_array(source['valid']) & np.isfinite(data['raw_values'])) and
                     np.array_equal(data['depth'][data['valid']], data['raw_values'][data['valid']]),
                     'D11 saved native relative-log array changed')
    if request['record_kind'] == 'actual':
        native = read_json(verify_record(result['native_result'])['path'])
        setup = read_json(verify_record(request['setup'])['path'])
        _require(native.get('schema') == 'plan069-D11-native-folder-result/v1' and
                 native.get('status') == 'complete' and native.get('profile') == PROFILE and
                 native.get('setup_source') == setup['native_source'] and
                 native.get('source_manifest') == setup['source_manifest'] and
                 native.get('native_qualification') == setup['runtime']['native_qualification'] and
                 [row['id'] for row in native.get('predictions', [])] ==
                     [f'camera{camera:02d}-frame{frame:03d}' for camera, frame in sorted(expected)],
                 'D11 single native folder result binding changed')
        saved = {f"camera{row['camera']:02d}-frame{row['frame']:03d}": row for row in rows}
        for row in native['predictions']:
            raw = load_array(row['prediction'])
            with load_array(saved[row['id']]['prediction']) as data:
                _require(raw.shape == (540, 960) and raw.dtype == np.float32 and
                         np.array_equal(raw, data['raw_values'], equal_nan=True),
                         'D11 saved values differ from native folder prediction')
