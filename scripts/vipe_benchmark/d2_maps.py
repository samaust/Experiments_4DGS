"""Generate D2's 196 missing matched-clip maps; reuse four frozen anchors."""

from pathlib import Path
import time

import numpy as np

from .backends import AssetBundle
from .contracts import depth as validate_depth
from .depth_clips import SCHEMA, materialize_role
from .d2_preflight import SCHEMA as PREFLIGHT_SCHEMA
from .files import file_record, read_json, verify_record, write_json


REQUEST_SCHEMA = 'plan069-d2-maps-request/v1'
RESULT_SCHEMA = 'plan069-d2-maps-result/v1'
CAMERAS = (1, 11, 21, 31)
FRAMES = range(150, 200)


def _require(condition, message):
    if not condition:
        raise ValueError(message)


def run(request, output, *, backend, load_role=materialize_role,
        reservation_check=None):
    """Run one bounded worker; caller owns the serial GPU reservation.

    ``reservation_check`` must verify the exact active ledger reservation for
    actual work. Fixtures pass a fake backend and need no GPU.
    """
    start = time.monotonic()
    _require(request.get('schema') == REQUEST_SCHEMA and
             request.get('job_id') == 'plan069-D2-maps-001' and
             request.get('candidate') == 'D2' and
             request.get('record_kind') in ('fixture', 'actual') and
             request.get('max_seconds') == 3600,
             'exact bounded D2 map request required')
    if request['record_kind'] == 'actual':
        _require(reservation_check is not None and reservation_check(request, output),
                 'actual D2 maps require active exact supervision')
    _require(Path(output).name == request['job_id'], 'D2 output identity changed')
    preflight = read_json(verify_record(request['preflight'])['path'])
    _require(preflight.get('schema') == PREFLIGHT_SCHEMA and
             preflight.get('status') == 'cpu_preflight_passed' and
             preflight.get('candidate') == 'D2' and
             preflight.get('proposal_sha256') == request.get('proposal_sha256') and
             preflight.get('assets') == request.get('assets_record'),
             'D2 CPU preflight does not bind exact proposal/assets')
    assets = read_json(verify_record(request['assets_record'])['path'])
    bundle = AssetBundle('D2', assets)
    _require(preflight['checkpoint'] in bundle.records['da3_snapshot']['files'] and
             preflight['runtime'] == request.get('runtime') and
             getattr(backend, 'component', 'D2') == 'D2',
             'D2 source, runtime or model binding changed')
    historical = read_json(verify_record(request['historical_check'])['path'])
    _require(historical.get('status') == 'complete' and historical.get('component') == 'D2' and
             len(historical.get('rows', [])) == 30,
             'completed frozen D2 check required')
    context = read_json(verify_record(request['context'])['path'])
    _require(context.get('schema') == SCHEMA and
             context.get('inputs') == request.get('inputs') and
             len(context.get('rows', [])) == 4500,
             'accepted full depth context required')
    by_key = {(row['camera'], row['frame']): row for row in context['rows']}
    _require(len(by_key) == 4500 and
             all((camera, frame) in by_key for camera in CAMERAS for frame in FRAMES),
             'D2 clip context identities changed')
    anchors = {row['identity']['camera']: row for row in historical['rows']
               if row['identity']['frame'] == 175 and row['identity']['camera'] in CAMERAS}
    _require(set(anchors) == set(CAMERAS), 'four frozen D2 check anchors required')
    output = Path(output)
    _require(not output.exists(), 'immutable D2 maps output already exists')
    output.mkdir(parents=True, exist_ok=False)
    write_json(output / 'request.json', request)
    rows = []
    try:
        for camera in CAMERAS:
            images, valid, role_rows = load_role(request['context'], camera, 'check')
            _require(images.shape == (50, 540, 960, 3) and
                     valid.shape == (540, 960) and valid.dtype == np.bool_ and
                     [row['frame'] for row in role_rows] == list(FRAMES),
                     'D2 decoded selection role changed')
            anchor = anchors[camera]
            for index, frame in enumerate(FRAMES):
                _require(time.monotonic() - start < request['max_seconds'],
                         'D2 attempt wall deadline exceeded')
                source = by_key[camera, frame]
                _require(source == role_rows[index] and source['role'] == 'check' and
                         source['grid'] == 'scale-opencv-integer',
                         'D2 source context differs from decoded role')
                if frame == 175:
                    _require(anchor['depth'] == verify_record(anchor['depth']) and
                             anchor['source_rgb_sha256'] == source['source_rgb']['sha256'] and
                             anchor['grid'] == source['grid'] and
                             np.array_equal(anchor['K'], source['K']),
                             'frozen D2 anchor lineage differs')
                    prediction = anchor['depth']
                    reused = True
                else:
                    estimate = backend.predict(images[index], np.asarray(source['K'], np.float64), valid)
                    _require(estimate.depth.shape == valid.shape and
                             estimate.depth.dtype == np.float32 and
                             estimate.valid.dtype == np.bool_ and
                             estimate.valid.shape == valid.shape and
                             isinstance(estimate.raw_depth, np.ndarray) and
                             estimate.raw_depth.dtype.kind == 'f' and
                             estimate.raw_depth.ndim == 2,
                             'D2 native output grid or dtype changed')
                    validate_depth(estimate.depth, estimate.valid, valid)
                    destination = output / f'camera{camera}-frame{frame}.npz'
                    with destination.open('xb') as stream:
                        np.savez_compressed(stream, depth=estimate.depth, valid=estimate.valid,
                            raw_depth=estimate.raw_depth)
                    prediction = file_record(destination)
                    reused = False
                rows.append(dict(camera=camera, frame=frame, role='check',
                    source_rgb=source['source_rgb'], inputs=context['inputs'],
                    grid=source['grid'], domain='camera_z_metres',
                    settings=historical['component_sha256'], prediction=prediction,
                    reused_anchor=reused))
        _require(len(rows) == 200 and sum(not row['reused_anchor'] for row in rows) == 196,
                 'D2 workload differs from four clips and 196 new maps')
        result = dict(schema=RESULT_SCHEMA, status='complete', candidate='D2',
            record_kind=request['record_kind'], job_id=request['job_id'],
            context=request['context'], historical_check=request['historical_check'],
            preflight=request['preflight'], proposal_sha256=request['proposal_sha256'],
            rows=rows, clips=4, new_maps=196, reused_anchors=4,
            elapsed_seconds=time.monotonic() - start)
        write_json(output / 'result.json', result)
        return result
    except BaseException as error:
        write_json(output / 'failure.json', dict(schema=RESULT_SCHEMA, status='failed',
            candidate='D2', job_id=request['job_id'], completed_rows=len(rows),
            error=f'{type(error).__name__}: {error}',
            elapsed_seconds=time.monotonic() - start))
        raise
