"""Fail-closed assembly of the extended depth comparison for human review.

This consumes immutable result records. It never infers a successful attempt from
a missing file, a fixture receipt, or a preview package.
"""

from pathlib import Path

from .config import training_cameras
from .files import read_json, verify_record
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
                          record=row['record'], source_input=row['source_rgb']))
    return media


def _clips(record, candidate, context, anchors):
    receipt = _record(record)
    _require(receipt.get('schema') == 'plan069-depth-clips-result/v1' and
             receipt.get('status') == 'complete' and receipt.get('record_kind') == 'actual' and
             receipt.get('candidate') == candidate and receipt.get('context') == context and
             receipt.get('clips') == 4 and receipt.get('new_map_identities') == 196,
             f'{candidate}: actual four-clip receipt required')
    package = _record(receipt['package'])
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
                clips_source, clips_depth, display = _clips(
                    slot['clips'], candidate, context_record, anchors)
                media += clips_depth
                if source_clips is None:
                    source_clips = clips_source
                else:
                    _require([item['record'] for item in source_clips] ==
                             [item['record'] for item in clips_source],
                             f'{candidate}: source RGB clip bytes differ')
            _require(len(media) <= 64, f'{candidate}: published media bound exceeded')
            _require(all(key in slot.get('provenance', {}) for key in
                         ('source_result', 'ledger_outcome', 'configuration')),
                     f'{candidate}: package provenance missing')
            for record in slot['provenance'].values():
                verify_record(record)
            if candidate in ADDITIONS:
                result = _record(slot['provenance']['source_result'])
                _require(result.get('record_kind') == 'actual' and
                         result.get('status') == 'complete' and
                         result.get('component') == candidate,
                         f'{candidate}: actual completed native result required')
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
