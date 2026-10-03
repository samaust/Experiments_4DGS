"""Fail-closed assembly of the extended depth comparison for human review.

This consumes immutable result records. It never infers a successful attempt from
a missing file, a fixture receipt, or a preview package.
"""

from pathlib import Path

from .config import training_cameras
from .files import file_record, read_json, verify_record
from .qualitative_package import publish as publish_package


SCHEMA = 'plan069-depth-aggregate-request/v1'
CANDIDATES = ('D0', 'D1', 'D2', 'D3', 'D4', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11')
ADDITIONS = CANDIDATES[5:]
CLIP_CANDIDATES = ('D2', *ADDITIONS)
DOMAINS = {key: 'camera_z_metres' for key in CANDIDATES}
DOMAINS.update(D9='relative_inverse', D11='relative_log')
CLIP_CAMERAS = (1, 11, 21, 31)
CLIP_FRAMES = list(range(150, 200))
ANCHOR_FRAMES = (100, 175)
EVIDENCE = ('generation', 'runtime', 'assets', 'commercial', 'ledger', 'resources')


def _require(ok, message):
    if not ok:
        raise ValueError(message)


def _record(record):
    _require(type(record) is dict and set(record) == {'path', 'sha256', 'bytes'},
             'exact file record required')
    _require(verify_record(record) == record, 'file record bytes/path mismatch')
    return read_json(record['path'])


def _selection(camera, frame=None):
    if frame is None:
        frames = CLIP_FRAMES
        return dict(id=f'camera{camera}-selection-150-199', kind='clip',
                    role='selection', camera_id=str(camera), frame_ids=frames,
                    timestamps=[f / 25 for f in frames])
    return dict(id=f'camera{camera}-' + ('calibration' if frame == 100 else 'selection') + f'-{frame}',
                kind='frame', role='calibration' if frame == 100 else 'selection',
                camera_id=str(camera), frame_ids=[frame], timestamps=[frame / 25])


def _anchors(rows, cameras, candidate, *, source=False):
    """Check exact identity, source grid and published map count before media read."""
    _require(type(rows) is list and len(rows) == 60, f'{candidate}: 60 anchors required')
    expected = {(camera, frame) for camera in cameras for frame in ANCHOR_FRAMES}
    identities = [(row.get('camera'), row.get('frame')) for row in rows]
    _require(len(set(identities)) == 60 and set(identities) == expected,
             f'{candidate}: anchor membership changed')
    media = []
    for row in sorted(rows, key=lambda item: (item['camera'], item['frame'])):
        _require(row.get('grid') == 'scale-opencv-integer' and row.get('domain') ==
                 ('rgb' if source else DOMAINS[candidate]),
                 f'{candidate}: anchor grid/domain changed')
        verify_record(row['source_rgb'])
        verify_record(row['record'])
        selection = _selection(row['camera'], row['frame'])
        media.append(dict(selection_id=selection['id'], kind='frame',
                          camera_id=str(row['camera']), frame_ids=selection['frame_ids'],
                          timestamps=selection['timestamps'], resolution=[960, 540],
                          record=row['record'], source_input=row['source_rgb'],
                          **({'depth_display': row['display']} if 'display' in row else {})))
    return media


def _verify_published_clips(package):
    # Reuse the publisher's live ledger and admission checks. A copied manifest
    # or a terminal disposition must never substitute for completed inference.
    from .depth_clips import validate_actual_depth_package
    validate_actual_depth_package(package)


def _verify_historical_anchors(native_record, historical_records):
    from .config import load
    from .ledger import Ledger
    root = Path(native_record['path']).resolve().parents[2]
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    events = Ledger(root / 'ledger.jsonl', config).events()
    for role, record in historical_records.items():
        _require(any(event.get('event') == 'finish' and event.get('status') == 'complete' and
                     event.get('job_id') == 'D2-' + role and event.get('result') == record
                     for event in events), 'D2: historical anchor result absent from accepted ledger')


def _verify_preview_charge(source_result, accounting_record):
    from .config import load
    from .ledger import Ledger
    root = Path(source_result['path']).resolve().parents[2]
    config = dict(load(), new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
    accounting = _record(accounting_record)
    _require(any(event.get('event') == 'cpu_preparation_charge' and
                 event.get('evidence') == accounting_record and
                 event.get('elapsed_seconds') == accounting.get('elapsed_seconds')
                 for event in Ledger(root / 'ledger.jsonl', config).events()),
             'anchor preview CPU charge absent from live ledger')


def _anchor_previews(slot, candidate, context, inputs, config):
    record = slot.get('anchor_previews')
    receipt = _record(record)
    accounting_record = slot['evidence']['anchor_preview_accounting']
    accounting = _record(accounting_record)
    # Completed receipts may bind identical frozen configuration bytes in a
    # different worktree. Verify both paths before comparing content identity.
    preview_config = verify_record(receipt['config'])
    aggregate_config = verify_record(config)
    _require(preview_config == receipt['config'] and aggregate_config == config,
             'anchor preview config record bytes/path mismatch')
    _require(receipt.get('schema') == 'plan069-depth-anchor-preview-result/v1' and
             receipt.get('record_kind') == 'actual' and receipt.get('status') == 'complete' and
             receipt.get('candidate') == candidate and receipt.get('context') == context and
             receipt.get('inputs') == inputs and
             all(preview_config[key] == aggregate_config[key] for key in ('sha256', 'bytes')) and
             receipt.get('anchors') == slot['anchors'] and
             receipt.get('rendered_frames') == 60 and
             receipt.get('sources') == dict(
                 builder=file_record(Path(__file__).with_name('depth_anchor_previews.py')),
                 renderer=file_record(Path(__file__).with_name('depth_extension.py'))) and
             receipt.get('slot', {}).get('provenance') == slot['provenance'] and
             receipt['slot'].get('evidence') == {key: value for key, value in slot['evidence'].items()
                 if key != 'anchor_preview_accounting'} and
             receipt['slot'].get('clips') == slot.get('clips') and
             accounting.get('schema') == 'plan069-depth-anchor-preview-accounting/v1' and
             accounting.get('status') == 'complete' and accounting.get('candidate') == candidate and
             accounting.get('result') == record,
             f'{candidate}: actual charged anchor preview receipt required')
    _verify_preview_charge(slot['provenance']['source_result'], accounting_record)


def _native_result(slot, candidate, context, inputs, cameras):
    record = slot['provenance']['source_result']
    _require(slot['evidence'].get('generation') == record and
             slot['evidence'].get('ledger') == slot['provenance']['ledger_outcome'],
             f'{candidate}: generation/ledger provenance differs')
    result = _record(record)
    schemas = {'D2': 'plan069-d2-maps-result/v1',
               'D7': 'plan069-D7-maps-result/v1',
               'D11': 'plan069-D11-maps-result/v1',
               'D9': 'plan069-video-depth-result/v1',
               'D10': 'plan069-video-depth-result/v1'}
    schema = schemas.get(candidate, 'plan069-depth-single-maps-result/v1')
    _require(result.get('schema') == schema and result.get('status') == 'complete' and
             result.get('record_kind') == 'actual' and
             result.get('candidate', result.get('component')) == candidate and
             result.get('context') == context,
             f'{candidate}: actual completed native result required')
    if candidate != 'D2':
        _require(result.get('inputs', result.get('original_inputs')) == inputs,
                 f'{candidate}: native input binding changed')
    rows = result.get('rows', [])
    expected_clips = {(camera, frame) for camera in CLIP_CAMERAS for frame in CLIP_FRAMES}
    expected_anchors = {(camera, frame) for camera in cameras for frame in ANCHOR_FRAMES}
    expected = expected_clips if candidate == 'D2' else expected_clips | expected_anchors
    identities = [(row['camera'], row['frame']) for row in rows]
    _require(len(identities) == len(expected) and set(identities) == expected,
             f'{candidate}: native map membership changed')
    native = dict(zip(identities, rows))
    for row in rows:
        _require(row.get('domain') == DOMAINS[candidate],
                 f'{candidate}: native depth domain changed')
        verify_record(row.get('prediction', row.get('depth')))
        verify_record(row['source_rgb'])
    anchors = native
    if candidate == 'D2':
        _require(result.get('new_maps') == 196 and result.get('reused_anchors') == 4 and
                 all(row.get('reused_anchor') is (row['frame'] == 175) for row in rows),
                 'D2: frozen anchor reuse count changed')
        anchors = {}
        historical_records = {role: slot['evidence']['historical_' + role]
                              for role in ('fit', 'check')}
        _verify_historical_anchors(record, historical_records)
        for role, frame in (('fit', 100), ('check', 175)):
            historical_record = historical_records[role]
            historical = _record(historical_record)
            configuration = _record(historical['configuration'])
            _require(historical.get('status') == 'complete' and historical.get('component') == 'D2' and
                     configuration.get('role') == role and len(historical.get('rows', [])) == 30,
                     'D2: complete historical fit/check anchors required')
            if role == 'check':
                _require(result.get('historical_check') == historical_record,
                         'D2: frozen historical check result changed')
            for row in historical['rows']:
                identity = row['identity']
                key = (identity['camera'], identity['frame'])
                _require(identity['frame'] == frame and key not in anchors,
                         'D2: historical anchor membership changed')
                _require(row.get('grid') == 'scale-opencv-integer',
                         'D2: historical anchor grid changed')
                anchors[key] = dict(prediction=row['depth'], source_rgb_sha256=row['source_rgb_sha256'])
        _require(set(anchors) == expected_anchors, 'D2: historical anchor membership changed')
    for row in slot['anchors']:
        original = anchors[row['camera'], row['frame']]
        _require(row['prediction'] == original.get('prediction', original.get('depth')),
                 f'{candidate}: anchor differs from completed native result')
        _require(original.get('source_rgb_sha256') == row['source_rgb']['sha256'] if candidate == 'D2'
                 else original.get('source_rgb') == row['source_rgb'],
                 f'{candidate}: native anchor source differs from accepted context')
    eligibility = 'ineligible' if candidate in ('D9', 'D11') else 'unverified'
    if candidate in ('D5', 'D6', 'D7', 'D8', 'D10'):
        scales = result.get('scales', result.get('scale', {}))
        _require(set(scales) == {'fit', 'check'}, f'{candidate}: frozen scale receipts required')
        fit, check = _record(scales['fit']), _record(scales['check'])
        _require(fit.get('component') == candidate and check.get('component') == candidate and
                 fit.get('role') == 'fit' and check.get('role') == 'selection' and
                 check.get('frozen_fit') == scales['fit'] and
                 fit.get('status') in ('passed', 'blocked') and
                 check.get('status') in ('passed', 'blocked'),
                 f'{candidate}: frozen fit/check scale lineage changed')
        eligibility = 'passed' if fit['status'] == check['status'] == 'passed' else 'blocked'
        claimed = (result.get('eligibility', {}).get('metric_scale') if candidate == 'D10'
                   else result.get('engineering_eligibility'))
        _require(claimed == eligibility, f'{candidate}: scale disposition manufactures eligibility')
        _require(slot['evidence'].get('scale') == scales['check'],
                 f'{candidate}: scale evidence differs from frozen check')
    return record, native, eligibility


def _clips(record, candidate, context, anchors, native_result, native_rows, finish):
    receipt = _record(record)
    _require(receipt.get('schema') == 'plan069-depth-clips-result/v1' and
             receipt.get('status') == 'complete' and receipt.get('record_kind') == 'actual' and
             receipt.get('candidate') == candidate and receipt.get('context') == context and
             receipt.get('clips') == 4 and receipt.get('new_map_identities') == 196,
             f'{candidate}: actual four-clip receipt required')
    package = _record(receipt['package'])
    _require(package.get('bindings', {}).get('depth_context') == context and
             package['bindings'].get('depth_result') == native_result and
             package['bindings'].get('depth_finish') == finish,
             f'{candidate}: clip package native/context binding changed')
    _verify_published_clips(package)
    _require(package.get('schema') == 'plan067-qualitative-package/v1' and
             package.get('record_kind') == 'actual' and
             package.get('settings', {}).get('fps') == 25 and
             package['settings'].get('resolution') == [960, 540],
             f'{candidate}: actual 25-fps clip package required')
    selections = [_selection(camera) for camera in CLIP_CAMERAS]
    _require(package.get('selections') == selections, f'{candidate}: clip views/frames changed')
    by_id = {item['id']: item for item in package['candidates']}
    _require(set(by_id) == {'source-rgb', candidate}, f'{candidate}: clip candidate set changed')
    anchor_maps = {(row['camera'], row['frame']): row['prediction'] for row in anchors}
    for key in by_id:
        _require(by_id[key]['status'] == 'available' and len(by_id[key]['media']) == 4,
                 f'{candidate}: four complete clips required')
        for item, selection in zip(by_id[key]['media'], selections):
            _require(item['kind'] == 'clip' and item['selection_id'] == selection['id'] and
                     item['frame_ids'] == selection['frame_ids'] and
                     item['timestamps'] == selection['timestamps'] and
                     item['camera_id'] == selection['camera_id'] and
                     item['resolution'] == [960, 540],
                     f'{candidate}: clip frame/time/view mismatch')
            verify_record(item['record'])
            lineage = item.get('source_images' if key == 'source-rgb' else 'source_maps')
            _require(type(lineage) is list and len(lineage) == 50,
                     f'{candidate}: 50 source records per clip required')
            for source in lineage:
                verify_record(source)
            if key == candidate:
                camera = int(selection['camera_id'])
                _require(lineage == [native_rows[camera, frame].get('prediction',
                    native_rows[camera, frame].get('depth')) for frame in CLIP_FRAMES],
                    f'{candidate}: clip maps differ from completed native result')
                _require(lineage[25] == anchor_maps[camera, 175],
                         f'{candidate}: frame-175 map differs from frozen anchor')
    display = package['settings']['depth_display']
    _require(display.get('domain') == DOMAINS[candidate] and
             set(display.get('per_clip', {})) == {row['id'] for row in selections},
             f'{candidate}: depth domain/normalization lineage changed')
    if candidate in ('D9', 'D11'):
        _require(display.get('normalization_scope') == 'whole 50-frame clip' and
                 display.get('units') == 'relative arbitrary values' and
                 'range_metres' not in display,
                 f'{candidate}: relative depth display implies metric scale')
    else:
        _require(display.get('range_metres') == [0, 20] and
                 display.get('invalid_color') == 'magenta' and
                 display.get('above_20_metres_color') == 'red',
                 f'{candidate}: metric display range changed')
    return by_id['source-rgb']['media'], by_id[candidate]['media'], display


def assemble(request):
    """Construct an exact viewer manifest; missing attempts stay visibly pending."""
    _require(request.get('schema') == SCHEMA and request.get('record_kind') == 'actual',
             'actual aggregate request required')
    for name in ('config', 'inputs', 'amendment', 'context', 'source'):
        _record(request['bindings'][name]) if name == 'context' else verify_record(request['bindings'][name])
    context_record = request['bindings']['context']
    context = read_json(context_record['path'])
    cameras = sorted(training_cameras(read_json(request['bindings']['config']['path'])))
    _require(context.get('schema') == 'plan069-depth-context/v1' and
             context.get('inputs') == request['bindings']['inputs'] and
             len(context.get('anchors', [])) == 60 and
             {(row['camera'], row['frame']) for row in context['anchors']} ==
             {(camera, frame) for camera in cameras for frame in ANCHOR_FRAMES},
             'accepted 60-anchor context required')
    slots = request.get('candidates')
    _require(type(slots) is dict and set(slots) == set(CANDIDATES),
             'all D0–D11 dispositions required')
    selections = [_selection(camera, frame) for camera in cameras for frame in ANCHOR_FRAMES]
    selections += [_selection(camera) for camera in CLIP_CAMERAS]
    source_anchors = [dict(camera=row['camera'], frame=row['frame'],
                           grid='scale-opencv-integer', domain='rgb',
                           source_rgb=row['accepted_rgb'], record=row['accepted_rgb'])
                      for row in context['anchors']]
    source_media = _anchors(source_anchors, cameras, 'source-rgb', source=True)
    accepted_sources = {(row['camera'], row['frame']): row['accepted_rgb']
                        for row in context['anchors']}
    candidates = []
    source_clips = None
    for candidate in CANDIDATES:
        slot = slots[candidate]
        status = slot.get('status')
        _require(status in ('available', 'failed', 'blocked', 'unavailable', 'missing'),
                 f'{candidate}: unknown disposition')
        _require(type(slot.get('reason')) is str and
                 (status == 'available' or bool(slot['reason'].strip())),
                 f'{candidate}: missing disposition reason')
        evidence = slot.get('evidence', {})
        _require(type(evidence) is dict, f'{candidate}: evidence map required')
        for record in evidence.values():
            _record(record)
        media = []
        eligibility = 'unverified'
        if status == 'available':
            _require(set(EVIDENCE) <= set(evidence),
                     f'{candidate}: generation/runtime/asset/commercial/ledger/resource evidence required')
            if candidate in ADDITIONS:
                _require('scale' in evidence or candidate in ('D9', 'D11'),
                         f'{candidate}: metric scale disposition required')
            anchors = slot.get('anchors')
            media = _anchors(anchors, cameras, candidate)
            _require(all(row['source_rgb'] == accepted_sources[row['camera'], row['frame']]
                         for row in anchors), f'{candidate}: anchor source differs from accepted context')
            if candidate in CLIP_CANDIDATES:
                _require(all('prediction' in row for row in anchors),
                         f'{candidate}: raw anchor map lineage required')
                for row in anchors:
                    verify_record(row['prediction'])
                native_result, native_rows, eligibility = _native_result(
                    slot, candidate, context_record, request['bindings']['inputs'], cameras)
                clips_source, clips_depth, display = _clips(
                    slot['clips'], candidate, context_record, anchors, native_result, native_rows,
                    slot['provenance']['ledger_outcome'])
                media += clips_depth
                if source_clips is None:
                    source_clips = clips_source
                else:
                    _require([item['record'] for item in source_clips] ==
                             [item['record'] for item in clips_source],
                             f'{candidate}: source RGB clip bytes differ')
            _anchor_previews(slot, candidate, context_record, request['bindings']['inputs'],
                             request['bindings']['config'])
            _require(len(media) <= 64, f'{candidate}: published media bound exceeded')
            _require(all(key in slot.get('provenance', {}) for key in
                         ('source_result', 'ledger_outcome', 'configuration')),
                     f'{candidate}: package provenance missing')
            for record in slot['provenance'].values():
                verify_record(record)
        elif status != 'missing':
            terminal = _record(slot['terminal_authorization'])
            _require(terminal.get('candidate') == candidate and
                     terminal.get('status') == status and
                     terminal.get('authorized') is True,
                     f'{candidate}: authorized terminal disposition required')
        candidates.append(dict(id=candidate, label=candidate + ' ' + DOMAINS[candidate],
            is_control=candidate == 'D0', stage='depth component diagnostic',
            output_type='component', status=status, reason=slot['reason'],
            provenance=slot.get('provenance', {}), media=media,
            engineering_eligibility=eligibility, physical_accuracy='unverified',
            **({'depth_display': display} if status == 'available' and candidate in CLIP_CANDIDATES else {})))
    _require(source_clips is not None or all(slots[key]['status'] != 'available'
             for key in CLIP_CANDIDATES), 'available clip arm must provide source RGB')
    source = dict(id='source-rgb', label='Accepted source RGB', is_control=True,
                  stage='accepted input', output_type='reference', status='available',
                  reason='', provenance=request['source_provenance'],
                  media=source_media + (source_clips or []))
    for name in ('source_result', 'ledger_outcome', 'configuration'):
        verify_record(source['provenance'][name])
    return dict(schema='plan067-qualitative-package/v1',
        id=request['id'], mode='qualitative', record_kind='actual',
        review_status='awaiting_human_review',
        bindings=dict(request['bindings']),
        settings=dict(fps=25, resolution=[960, 540], color_handling='sRGB',
            crop=[0, 0, 960, 540], detail_regions=[
                dict(id='center', crop=[240, 135, 480, 270]),
                dict(id='left', crop=[0, 135, 480, 270]),
                dict(id='right', crop=[480, 135, 480, 270])]),
        selections=selections, candidates=[source, *candidates])


def validate_actual_package(manifest, *, deadline=None):
    """Rebuild from the immutable request; reject substituted media or receipts."""
    request_record = manifest['bindings']['depth_aggregate_request']
    request = _record(request_record)
    expected = assemble(request)
    expected['bindings']['depth_aggregate_request'] = request_record
    _require(manifest == expected, 'depth aggregate differs from immutable receipts')
    _require(all(slot['status'] != 'missing' for slot in request['candidates'].values()),
             'pending depth slots cannot be published as complete')
    return {'actual_lineage': 'verified'}


def publish(request_record, output, *, deadline=None):
    """Publish once after every slot has actual output or authorized disposition."""
    request = _record(request_record)
    manifest = assemble(request)
    manifest['bindings']['depth_aggregate_request'] = request_record
    _require(all(slot['status'] != 'missing' for slot in request['candidates'].values()),
             'pending depth slots cannot be published as complete')
    return publish_package(manifest, Path(output), deadline=deadline)
