"""Versioned Plan 069 depth requests alongside the frozen D0–D4 workflow."""

import math
from pathlib import Path
import time

import numpy as np
from PIL import Image

from .config import ROOT, training_cameras
from .contracts import depth as validate_metric_depth, footprint
from .files import file_record, load_array, object_hash, read_json, verify_record, write_json
from .qualitative_package import publish as publish_package


REQUEST_SCHEMA = 'plan069-depth-extension-request/v1'
RESULT_SCHEMA = 'plan069-depth-extension-result/v1'
CONFIG = ROOT / 'configs/vipe-alternatives/depth-extension-v1.json'
DOMAINS = {
    'D5': 'camera_z_metres', 'D6': 'camera_z_metres',
    'D7': 'camera_z_metres', 'D8': 'camera_z_metres',
    'D9': 'relative_inverse', 'D10': 'camera_z_metres',
    'D11': 'relative_log',
}


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def _admit(request, output, config, ledger):
    _require(request.get('schema') == REQUEST_SCHEMA, 'depth extension request schema')
    _require(request.get('record_kind') in ('fixture', 'actual'), 'request origin required')
    _require(request.get('component') in DOMAINS, 'unknown depth extension candidate')
    _require(request.get('role') in ('fit', 'check'), 'unsupported depth extension role')
    _require(request.get('id') == f"{request['component']}-{request['role']}-fixture-001"
             if request['record_kind'] == 'fixture' else bool(request.get('id')),
             'request identity does not match declared role/origin')
    _require(Path(output).name == request['id'], 'output identity mismatch')
    _require(type(request.get('max_seconds')) in (int, float) and
             math.isfinite(request['max_seconds']) and 0 < request['max_seconds'] <= 600,
             'invalid CPU fixture deadline')
    for key in ('inputs', 'configuration', 'extension_configuration'):
        verify_record(request[key])
    _require(read_json(request['configuration']['path']) == config,
             'historical configuration differs from accepted protocol')
    _require(file_record(CONFIG) == request['extension_configuration'],
             'extension configuration differs from pinned source')
    extension = read_json(CONFIG)
    _require(extension.get('schema') == 'plan069-depth-extension-config/v1' and
             set(extension.get('candidates', {})) == set(DOMAINS) and
             all(extension['candidates'][key]['domain'] == domain
                 for key, domain in DOMAINS.items()), 'extension identity/domain inventory changed')
    domain = extension['candidates'][request['component']]['domain']
    _require(request['component'] != 'D10',
             'D10 metric admission requires the offline sequence path')
    _require(request['record_kind'] == 'fixture',
             'actual inference requires separately authorized depth allocation')
    _require(ledger.config == config, 'ledger configuration differs')
    events = ledger.events()
    _require(not any(row['event'] == 'reserve' for row in ledger.states(events).values()),
             'active allocated job prevents depth fixture admission')
    _require(ledger.totals(events)['cpu']['elapsed_seconds'] + request['max_seconds']
             <= config['cpu_prepare_score_report_seconds_limit'],
             'CPU preparation allocation exhausted')
    for event in events:
        if event['event'] == 'cpu_preparation_charge':
            receipt = read_json(verify_record(event['evidence'])['path'])
            _require(receipt.get('id') != request['id'], 'depth request identity already consumed')
    inputs = read_json(request['inputs']['path'])
    _require(inputs.get('schema') == 'vipe-benchmark-inputs/v1' and
             isinstance(inputs.get('depth'), list), 'accepted depth inputs required')
    frame = config['scale_fit_frame'] if request['role'] == 'fit' else config['scale_check_frame']
    rows = [row for row in inputs['depth'] if row.get('identity', {}).get('frame') == frame]
    cameras = set(training_cameras(config))
    _require(len(rows) == len(cameras) and
             {row['identity']['camera'] for row in rows} == cameras and
             all(row['identity']['branch'] == 'depth' for row in rows),
             'every training camera requires one accepted depth row')
    if request['role'] == 'fit':
        _require('frozen_fit' not in request, 'fit must not consume a prior scale')
    elif domain == 'camera_z_metres':
        _require('frozen_fit' in request, 'metric check requires frozen fit')
        verify_record(request['frozen_fit'])
        fit = read_json(request['frozen_fit']['path'])
        component_hash = object_hash(dict(component=request['component'],
            candidate=extension['candidates'][request['component']],
            extension_configuration=request['extension_configuration']))
        _require(fit.get('role') == 'fit' and
                 fit.get('component') == request['component'] and
                 fit.get('provenance', {}).get('inputs') == request['inputs'] and
                 fit['provenance'].get('component_sha256') == component_hash,
                 'frozen fit candidate/input binding differs')
        if fit.get('status') != 'passed':
            admission = request.get('qualitative_admission')
            _require(isinstance(admission, dict),
                     'failed fit requires separate qualitative admission')
            verify_record(admission)
            doc = read_json(admission['path'])
            _require(doc == dict(schema='plan069-depth-qualitative-admission/v1',
                record_kind='fixture', component=request['component'], inputs=request['inputs'],
                purpose='qualitative-only', status='admitted'),
                'qualitative scope is not bound to this candidate and inputs')
    return extension['candidates'][request['component']], rows, events


def _prediction(prediction, expected_domain, image_valid):
    domain = getattr(prediction, 'domain', None)
    _require(domain == expected_domain, 'native depth domain differs from pinned candidate')
    values = np.asarray(prediction.values)
    valid = np.asarray(prediction.valid)
    raw = np.asarray(prediction.raw_values)
    native_points = getattr(prediction, 'native_points', None)
    _require(values.shape == image_valid.shape and values.dtype == np.float32 and
             valid.shape == image_valid.shape and valid.dtype == np.bool_ and
             raw.shape == image_valid.shape and raw.dtype.kind in 'fiu',
             'native depth arrays have wrong grid or dtype')
    _require(isinstance(prediction.metadata, dict), 'native metadata required')
    if native_points is not None:
        native_points = np.asarray(native_points)
        _require(native_points.shape == (*image_valid.shape, 3) and
                 native_points.dtype == np.float32 and domain == 'camera_z_metres',
                 'native point map grid/domain differs')
    if domain == 'camera_z_metres':
        _require(prediction.metadata.get('native_depth_type') == 'camera-z metres'
                 and prediction.metadata.get('conversion_count', 0) <= 1,
                 'verified camera-z metres and single conversion required')
        validate_metric_depth(values, valid, image_valid)
    else:
        _require(not (valid & ~image_valid).any() and np.isnan(values[~valid]).all()
                 and np.isfinite(values[valid]).all(),
                 'relative depth validity/NaN contract violated')
        if domain == 'relative_inverse':
            _require((values[valid] >= 0).all(), 'relative inverse depth must be nonnegative')
    return values, valid, raw, native_points


def _preview_frame(values, valid, domain, path):
    if domain == 'camera_z_metres':
        normalized = np.clip(values / 20, 0, 1)
        display = dict(domain=domain, range_metres=[0, 20],
                       direction='larger means farther', clipped_above_metres=20,
                       invalid_color='magenta', above_20_metres_color='red')
    else:
        observed = values[valid]
        low, high = float(observed.min()), float(observed.max())
        normalized = (np.full(values.shape, .5, np.float32) if high == low else
                      np.clip((values - low) / (high - low), 0, 1))
        display = dict(domain=domain, normalization_scope='frozen-frame fixture',
                       raw_range=[low, high],
                       direction='larger means nearer' if domain == 'relative_inverse'
                           else 'larger means farther')
        if high == low:
            display['constant_value'] = low
    grey = np.nan_to_num(normalized, nan=0)
    pixels = np.repeat((grey * 255).astype(np.uint8)[..., None], 3, axis=2)
    if domain == 'camera_z_metres':
        pixels[valid & (values > 20)] = [255, 0, 0]
    pixels[~valid] = [255, 0, 255]
    Image.fromarray(pixels, 'RGB').save(path)
    return display


def _package(request, output, rows, predictions, worker, ledger_outcome):
    component = request['component']
    visible = [row for row in sorted(rows, key=lambda row: row['identity']['camera'])
               if predictions[row['identity']['camera']][1].any()]
    first = visible[0] if visible else sorted(rows, key=lambda row: row['identity']['camera'])[0]
    camera, frame = first['identity']['camera'], first['identity']['frame']
    role = 'calibration' if frame == 100 else 'selection'
    selection = dict(id=f'camera{camera}-{role}-{frame}', kind='frame', role=role,
                     camera_id=str(camera), frame_ids=[frame], timestamps=[frame / 25])
    source = first['rgb']
    with Image.open(verify_record(source)['path']) as image:
        image.load()
        _require(image.size == (960, 540), 'accepted RGB grid differs')
    values, valid, _, _ = predictions[camera]
    preview = output / 'preview.png'
    display = (_preview_frame(values, valid, worker['domain'], preview) if visible else
               dict(domain=worker['domain'], status='no-valid-pixels'))
    media = lambda record: dict(selection_id=selection['id'], kind='frame',
        frame_ids=[frame], timestamps=[frame / 25], camera_id=str(camera),
        resolution=[960, 540], record=record, source_input=source)
    origin = dict(source_result=file_record(output / 'result.json'),
                  ledger_outcome=ledger_outcome,
                  configuration=file_record(output / 'request.json'))
    manifest = dict(schema='plan067-qualitative-package/v1',
        id=request['id'] + '-preview', mode='qualitative', record_kind='fixture',
        bindings=dict(source=file_record(output / 'source.py'),
            config=request['configuration'], inputs=request['inputs'],
            amendment=file_record(ROOT / 'docs/specs/plan031-execution/depth-comparison-extension.md')),
        settings=dict(fps=25, resolution=[960, 540], color_handling='sRGB',
            crop=[0, 0, 960, 540], detail_regions=[], depth_display=display),
        selections=[selection],
        candidates=[
            dict(id='source-rgb', label='Accepted source RGB', is_control=True,
                 stage='accepted input', output_type='reference', status='available',
                 reason='', provenance=dict(origin), media=[media(source)]),
            dict(id=component, label=f'{component} {worker["domain"]}',
                 is_control=False, stage='depth component diagnostic',
                 output_type='component', status='available' if visible else 'unavailable',
                 reason='' if visible else 'No valid depth pixels in any training camera',
                 provenance=origin, media=[media(file_record(preview))] if visible else []),
        ])
    published = publish_package(manifest, output / 'package')
    return published['package']


def run(request, output, config, *, backend, ledger):
    """Execute one CPU fixture through worker, scale, ledger and review package."""
    output = Path(output)
    candidate, rows, events = _admit(request, output, config, ledger)
    _require(getattr(backend, 'component', request['component']) == request['component'],
             'native adapter candidate differs from request')
    _require(not output.exists(), 'immutable depth output already exists')
    start = time.monotonic()
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    with (output / 'source.py').open('xb') as stream:
        stream.write(Path(__file__).read_bytes())
    write_json(output / 'ledger-prefix.json', dict(events=events))
    charged_elapsed = 0.
    try:
        import cv2
        predictions, result_rows, arrays = {}, [], {}
        domain = candidate['domain']
        for row in sorted(rows, key=lambda item: item['identity']['camera']):
            _require(time.monotonic() - start < request['max_seconds'],
                     'depth fixture deadline exceeded')
            camera = row['identity']['camera']
            image = cv2.imread(verify_record(row['rgb'])['path'], cv2.IMREAD_COLOR)
            _require(image is not None and image.shape[:2] == (540, 960),
                     'accepted RGB grid differs')
            rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image_valid = load_array(row['valid'])
            footprint(image_valid)
            prediction = backend.predict(rgb, np.asarray(row['K'], np.float64), image_valid)
            values, valid, raw, native_points = _prediction(prediction, domain, image_valid)
            path = output / f'camera{camera}-frame{row["identity"]["frame"]}.npz'
            with path.open('xb') as stream:
                np.savez_compressed(stream, **({'depth': values} if domain == 'camera_z_metres'
                    else {'relative': values}), valid=valid, raw_values=raw,
                    **({'native_points': native_points} if native_points is not None else {}))
            record = file_record(path)
            predictions[camera] = record
            arrays[camera] = (values, valid, raw, native_points)
            result_rows.append(dict(identity=row['identity'], source_rgb=row['rgb'],
                source_rgb_sha256=row['rgb']['sha256'], K=row['K'], grid=row['grid'],
                context=dict(camera=camera, role=request['role'],
                    source_frames=[row['identity']['frame']], input_manifest=request['inputs']),
                depth=record, domain=domain, metadata=prediction.metadata))
        component_hash = object_hash(dict(component=request['component'],
            candidate=candidate, extension_configuration=request['extension_configuration']))
        result = dict(schema=RESULT_SCHEMA, status='complete', record_kind='fixture',
            id=request['id'], component=request['component'], role=request['role'],
            domain=domain, rows=result_rows, configuration=file_record(output / 'request.json'),
            input_manifest=request['inputs'], component_sha256=component_hash)
        if domain == 'camera_z_metres':
            from .scale import evaluate
            fit = read_json(request['frozen_fit']['path']) if 'frozen_fit' in request else None
            if fit is not None and fit.get('status') != 'passed':
                check_diagnostics = evaluate(rows, predictions,
                    dict(config, scale_fit_frame=config['scale_check_frame']),
                    provenance=dict(inputs=request['inputs'],
                        component_sha256=component_hash, component=request['component']))
                scale = dict(status='blocked', role='selection', scale=None,
                    blockers=['No passing frozen fit; qualitative-only admission'],
                    fit_blockers=fit.get('blockers', []),
                    fit_cameras=fit.get('cameras', []),
                    check_blockers=check_diagnostics.get('blockers', []),
                    cameras=check_diagnostics['cameras'],
                    frozen_fit=request['frozen_fit'], provenance=dict(inputs=request['inputs'],
                        component_sha256=component_hash))
            else:
                scale = evaluate(rows, predictions, config,
                    provenance=dict(inputs=request['inputs'],
                        component_sha256=component_hash, component=request['component']),
                    frozen_fit=request.get('frozen_fit'))
            scale['component'] = request['component']
            write_json(output / 'scale.json', scale)
            result['scale'] = file_record(output / 'scale.json')
        else:
            result['scale_status'] = 'not_metric'
        result['eligibility'] = dict(commercial='unverified', runtime='fixture-only',
            metric_scale=scale['status'] if domain == 'camera_z_metres' else 'not_applicable',
            downstream='blocked')
        write_json(output / 'result.json', result)
        inference_elapsed = time.monotonic() - start
        _require(inference_elapsed <= request['max_seconds'], 'depth fixture deadline exceeded')
        charge = ledger.charge_cpu_preparation(inference_elapsed,
            file_record(output / 'result.json'))
        charged_elapsed = inference_elapsed
        write_json(output / 'ledger-outcome.json', charge)
        package = _package(request, output, rows, arrays, result,
            file_record(output / 'ledger-outcome.json'))
        elapsed = time.monotonic() - start
        _require(elapsed <= request['max_seconds'], 'depth fixture deadline exceeded')
        receipt = dict(schema='plan069-depth-extension-transaction/v1',
            status='complete', record_kind='fixture', id=request['id'],
            worker=file_record(output / 'result.json'), package=package,
            elapsed_seconds=elapsed)
        write_json(output / 'transaction.json', receipt)
        ledger.charge_cpu_preparation(elapsed - charged_elapsed,
            file_record(output / 'transaction.json'))
        return receipt
    except BaseException as error:
        elapsed = time.monotonic() - start
        write_json(output / 'failure.json', dict(schema='plan069-depth-extension-failure/v1',
            status='failed', id=request['id'], error=f'{type(error).__name__}: {error}',
            elapsed_seconds=elapsed))
        ledger.charge_cpu_preparation(max(0., elapsed - charged_elapsed),
            file_record(output / 'failure.json'))
        raise
