"""Bounded CPU rendering of frozen anchor maps for the depth comparison."""
from copy import deepcopy
from pathlib import Path
import time

import numpy as np
from PIL import Image

from .config import load, training_cameras
from .depth_aggregate import (ANCHOR_FRAMES, CANDIDATES, CLIP_CANDIDATES, DOMAINS,
                              _clips, _native_result, _record, _require)
from .depth_extension import _preview_frame
from .files import file_record, read_json, verify_record, write_json
from .budgets import budget_snapshot, directory_bytes


REQUEST = 'plan069-depth-anchor-preview-request/v1'
RESULT = 'plan069-depth-anchor-preview-result/v1'
ACCOUNTING = 'plan069-depth-anchor-preview-accounting/v1'
PREVIEW_REVISION = '002'


def _historical_rows(slot, candidate, accepted, ledger=None):
    rows = {}
    events = ledger.events() if ledger is not None else []
    for role, frame in (('fit', 100), ('check', 175)):
        record = slot['evidence']['historical_' + role]
        result = _record(record)
        config = _record(result['configuration'])
        _require(result.get('component') == candidate and result.get('status') == 'complete' and
                 config.get('role') == role, 'completed historical anchor result required')
        if ledger is not None:
            _require(any(event.get('event') == 'finish' and event.get('status') == 'complete' and
                         event.get('job_id') == candidate + '-' + role and event.get('result') == record
                         for event in events), 'historical anchors absent from accepted ledger')
        for row in result['rows']:
            key = (row['identity']['camera'], row['identity']['frame'])
            _require(key in accepted and key[1] == frame and key not in rows and
                     row.get('grid') == 'scale-opencv-integer' and
                     row.get('source_rgb_sha256') == accepted[key]['sha256'],
                     'historical anchor source/grid/membership changed')
            rows[key] = row['depth']
    _require(set(rows) == set(accepted), '60 historical anchors required')
    return rows


def render(request, output, *, ledger=None):
    """Render 60 immutable PNGs; charge admitted work or expose elapsed CPU on errors."""
    _require(request.get('schema') == REQUEST and request.get('record_kind') in ('actual', 'fixture'),
             'anchor preview request origin required')
    _require(request.get('preview_revision') == PREVIEW_REVISION,
             'current anchor preview revision 002 required')
    candidate = request['candidate']
    _require(candidate in CANDIDATES, 'unknown anchor preview candidate')
    output = Path(output)
    _require(not output.exists(), 'immutable anchor preview output exists')
    seconds = request['max_seconds']
    maximum = request['max_artifact_bytes']
    _require(type(seconds) in (int, float) and np.isfinite(seconds) and 0 < seconds <= 600 and
             type(maximum) is int and 0 < maximum <= 256 * 2**20,
             'bounded anchor preview CPU/disk allocation required')
    started = time.monotonic()
    deadline = started + seconds
    # Unadmitted proof failures never write or mutate the ledger. Their measured
    # CPU duration is returned on the exception for the trusted caller to charge.
    try:
        actual, raw_anchors = _prepare(request, output, ledger, candidate, seconds, maximum)
        full_guard, output_guard = _publication_guards(actual, candidate, ledger, output)
        _require(time.monotonic() < deadline, 'anchor preview CPU deadline during proof verification')
    except BaseException as error:
        error.anchor_preview_elapsed_seconds = time.monotonic() - started
        raise
    try:
        output_guard(2**20)
        output.mkdir(parents=True, exist_ok=False)
        write_json(output / 'request.json', request)
        anchors = []
        retained = 0
        for row in raw_anchors:
            _require(time.monotonic() < deadline, 'anchor preview CPU deadline')
            with Image.open(verify_record(row['source_rgb'])['path']) as image:
                _require(image.size == (960, 540) and image.mode == 'RGB', 'accepted anchor RGB grid changed')
                image.load()
            with np.load(verify_record(row['prediction'])['path'], allow_pickle=False) as prediction:
                key = 'depth' if DOMAINS[candidate] == 'camera_z_metres' else 'relative'
                values, valid = prediction[key], prediction['valid']
                _require(values.shape == valid.shape == (540, 960) and values.dtype == np.float32 and
                         valid.dtype == np.bool_ and valid.any() and np.isfinite(values[valid]).all() and
                         np.isnan(values[~valid]).all(), 'frozen anchor depth/validity contract changed')
                if DOMAINS[candidate] == 'camera_z_metres':
                    _require((values[valid] > 0).all(), 'metric anchor depth must be positive')
                path = output / f"camera{row['camera']}-frame{row['frame']}.png"
                # PNG's worst-case RGB bytes plus encoder/metadata headroom.
                output_guard(960 * 540 * 3 + 2**20)
                display = _preview_frame(values, valid, DOMAINS[candidate], path)
                output_guard()
                if DOMAINS[candidate] == 'camera_z_metres':
                    display.update(normalization_scope='one frozen anchor frame',
                                   invalid_color='magenta', above_20_metres_color='red')
                else:
                    display['normalization_scope'] = 'one frozen anchor frame'
                    display['units'] = 'relative arbitrary values'
                preview = file_record(path)
                retained += preview['bytes']
                _require(directory_bytes(output) <= maximum and time.monotonic() < deadline,
                         'anchor preview CPU/disk bound exceeded')
                anchors.append(dict(row, record=preview, display=display))
        result = dict(schema=RESULT, status='complete', record_kind=request['record_kind'], candidate=candidate,
                      preview_revision=PREVIEW_REVISION,
                      context=request['context'], inputs=request['inputs'], config=request['config'],
                      slot=request['slot'], anchors=anchors, source_rgb=[row['source_rgb'] for row in anchors],
                      rendered_frames=60, elapsed_seconds=time.monotonic() - started,
                      artifact_bytes=retained, physical_accuracy='unverified', human_review='pending',
                      sources=dict(builder=file_record(__file__),
                                   renderer=file_record(Path(__file__).with_name('depth_extension.py'))))
        output_guard(2**20)
        write_json(output / 'result.json', result)
        output_guard()
        _require(directory_bytes(output) <= maximum and time.monotonic() < deadline,
                 'anchor preview CPU/disk bound exceeded')
        if actual:
            _require(budget_snapshot(ledger.path.parent)['artifact_bytes'] <=
                     ledger.config['new_artifact_disk_gib_limit'] * 2**30, 'anchor cumulative artifact cap exceeded')
            # Full scan once at terminal publication; its CPU cost is measured.
            # Reserve bounded receipt space before the no-download full check.
            output_guard(2**20)
            full_guard()
            accounting = dict(schema=ACCOUNTING, status='complete', candidate=candidate,
                              result=file_record(output / 'result.json'), elapsed_seconds=time.monotonic() - started)
            write_json(output / 'cpu-accounting.json', accounting)
            output_guard()
            _require(directory_bytes(output) <= maximum and time.monotonic() < deadline,
                     'anchor preview CPU/disk bound exceeded')
            ledger.charge_cpu_preparation(accounting['elapsed_seconds'], file_record(output / 'cpu-accounting.json'))
        return result
    except BaseException as error:
        failure = dict(schema=ACCOUNTING, status='failed', candidate=candidate,
                       error=f'{type(error).__name__}: {error}', elapsed_seconds=time.monotonic() - started)
        error.anchor_preview_elapsed_seconds = failure['elapsed_seconds']
        try:
            write_json(output / 'cpu-failure.json', failure)
        except OSError as receipt_error:
            error.add_note(f'CPU failure receipt could not be written: {receipt_error}')
        else:
            if actual:
                ledger.charge_cpu_preparation(failure['elapsed_seconds'], file_record(output / 'cpu-failure.json'))
        raise



def _prepare(request, output, ledger, candidate, seconds, maximum):
    """Verify provenance before any output or ledger mutation."""
    config = read_json(verify_record(request['config'])['path'])
    context = _record(request['context'])
    cameras = sorted(training_cameras(config))
    accepted = {(row['camera'], row['frame']): row['accepted_rgb'] for row in context['anchors']}
    _require(context.get('schema') == 'plan069-depth-context/v1' and context.get('inputs') == request['inputs'] and
             len(context['anchors']) == 60 and set(accepted) ==
             {(camera, frame) for camera in cameras for frame in ANCHOR_FRAMES},
             'accepted 60-anchor context required')
    slot = deepcopy(request['slot'])
    _require(slot.get('status') == 'available', 'only available candidates have anchor previews')
    _require('anchors' not in slot and 'anchor_previews' not in slot and
             'anchor_preview_accounting' not in slot.get('evidence', {}),
             'anchor preview input slot must contain only generation/clip evidence')
    actual = request['record_kind'] == 'actual'
    if actual:
        _require(ledger is not None and config == load() and
                 ledger.config == dict(config, new_download_gib_limit=110, new_artifact_disk_gib_limit=210) and
                 output.parent == ledger.path.parent / 'jobs' and
                 output.name == f'plan069-{candidate}-anchor-previews-{PREVIEW_REVISION}',
                 'actual anchor previews require shared ledger output/configuration')
        _require(not any(row.get('event') == 'reserve' for row in ledger.states().values()),
                 'active attempt prevents anchor CPU rendering')
        _require(ledger.totals()['cpu']['elapsed_seconds'] + seconds <=
                 config['cpu_prepare_score_report_seconds_limit'], 'anchor CPU allocation exhausted')
        _require(budget_snapshot(ledger.path.parent)['artifact_bytes'] + maximum <=
                 ledger.config['new_artifact_disk_gib_limit'] * 2**30, 'anchor artifact allocation exhausted')
    if candidate in ('D0', 'D1', 'D2', 'D3', 'D4'):
        predictions = _historical_rows(slot, candidate, accepted, ledger if actual else None)
    else:
        native = _record(slot['provenance']['source_result'])
        predictions = {(row['camera'], row['frame']): row.get('prediction', row.get('depth'))
                       for row in native['rows'] if row['frame'] in ANCHOR_FRAMES}
        _require(set(predictions) == set(accepted), '60 native anchors required')
    raw_anchors = [dict(camera=camera, frame=frame, grid='scale-opencv-integer', domain=DOMAINS[candidate],
                        source_rgb=accepted[camera, frame], prediction=prediction, record=prediction)
                   for (camera, frame), prediction in sorted(predictions.items())]
    slot['anchors'] = raw_anchors
    if actual and candidate in CLIP_CANDIDATES:
        native_record, native_rows, _ = _native_result(slot, candidate, request['context'], request['inputs'], cameras)
        _clips(slot['clips'], candidate, request['context'], raw_anchors, native_record,
               native_rows, slot['provenance']['ledger_outcome'])
    return actual, raw_anchors

def _publication_guards(actual, candidate, ledger, output):
    """Use full initial/final scans and cheap output-only checks between writes."""
    if not actual or candidate not in ('D5', 'D6', 'D8', 'D11'):
        return (lambda: None), (lambda additional_bytes=0: None)
    from .depth_map_allowance import historical_slot_byte_guard
    from .depth_single_run import _actual_output_guard
    # Factory checks all retained revisions and forbids missing D11 slot proof.
    full = historical_slot_byte_guard(ledger, candidate)
    allocations = [event for event in ledger.events()
                   if event.get('event') == 'depth_attempt_authorized' and
                   event.get('candidate') == candidate]
    _require(len(allocations) == 1, 'exact whole-slot preview authorization required')
    lightweight = _actual_output_guard(dict(record_kind='actual', candidate=candidate,
        ledger_path=str(ledger.path), review=allocations[0]['review']), output)
    return full, lightweight


def aggregate_request(template, preview_records):
    """Attach actual preview receipts to explicit slots; missing slots stay pending."""
    request = deepcopy(template)
    _require(request.get('schema') == 'plan069-depth-aggregate-request/v1' and
             request.get('record_kind') == 'actual' and set(request['candidates']) == set(CANDIDATES),
             'explicit actual aggregate slot template required')
    for candidate, record in preview_records.items():
        _require(candidate in CANDIDATES, 'unknown anchor preview slot')
        receipt = _record(record)
        slot = request['candidates'][candidate]
        _require(receipt.get('schema') == RESULT and receipt.get('status') == 'complete' and
                 receipt.get('record_kind') == 'actual' and
                 receipt.get('preview_revision') == PREVIEW_REVISION and receipt.get('candidate') == candidate and
                 receipt.get('context') == request['bindings']['context'] and
                 receipt.get('inputs') == request['bindings']['inputs'] and
                 receipt.get('slot') == slot and receipt.get('rendered_frames') == 60,
                 'actual anchor preview receipt differs from aggregate slot')
        accounting = file_record(Path(record['path']).parent / 'cpu-accounting.json')
        slot['anchors'] = receipt['anchors']
        slot['anchor_previews'] = record
        slot['evidence']['anchor_preview_accounting'] = accounting
    return request


def main():
    import argparse
    from .ledger import Ledger
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--ledger', required=True)
    args = parser.parse_args()
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    render(read_json(args.request), args.output, ledger=Ledger(args.ledger, config))


if __name__ == '__main__':
    main()
