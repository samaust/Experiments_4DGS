"""Accepted scale-grid video context for Plan 069 depth comparisons."""
import hashlib
from pathlib import Path
import subprocess
import time

import numpy as np

from .config import ROOT, training_cameras
from .files import file_record, read_json, verify_record, write_json
from .qualitative_package import publish as publish_package


SCHEMA = 'plan069-depth-context/v1'
CALIBRATION = ROOT / 'docs/experiments/basketball-calibration-alternatives/calibration.json'


def prepare_context(inputs_record, output, config):
    """Bind every permitted source frame and prove both frozen scale-grid anchors."""
    import cv2
    from basketball_scale import undistortion

    verify_record(inputs_record)
    inputs = read_json(inputs_record['path'])
    if inputs.get('schema') != 'vipe-benchmark-inputs/v1' or inputs.get('status') != 'prepared':
        raise ValueError('accepted source input manifest required')
    local_calibration = file_record(CALIBRATION)
    matches = [record for record in inputs.get('source_files', [])
               if record.get('sha256') == local_calibration['sha256'] and
               record.get('bytes') == local_calibration['bytes']]
    if len(matches) != 1:
        raise ValueError('accepted calibration source binding changed')
    calibration = verify_record(matches[0])
    cameras = set(training_cameras(config))
    calibration_rows = {entry['camera_id']: entry for entry in read_json(CALIBRATION)['cameras']}
    if not cameras <= set(calibration_rows):
        raise ValueError('accepted camera calibration missing')
    if any(r.get('identity', {}).get('branch') == 'calibration' and
           r['identity'].get('camera') in cameras and
           type(r['identity'].get('frame')) is int and r['identity']['frame'] >= 200
           for r in inputs.get('rgb', [])):
        raise ValueError('final-window frames are outside the permitted depth context')
    rows = [r for r in inputs.get('rgb', []) if r.get('identity', {}).get('branch') == 'calibration'
            and r['identity'].get('camera') in cameras and 50 <= r['identity'].get('frame', -1) <= 199]
    expected = {(camera, frame) for camera in cameras for frame in range(50, 200)}
    keys = [(r['identity']['camera'], r['identity']['frame']) for r in rows]
    if len(rows) != len(expected) or set(keys) != expected or len(set(keys)) != len(keys):
        raise ValueError('context membership changed or incomplete')
    source_files = inputs['source_files']
    for row in rows:
        frame = row['identity']['frame']
        role = 'fit' if frame <= 149 else 'selection'
        if (row.get('role') != role or row.get('grid') != 'distorted-opencv-integer'
                or row.get('source_video') not in source_files or not Path(row['rgb']['path']).is_file()):
            raise ValueError('context role/grid/video/source binding changed')
    anchor_frames = {config['scale_fit_frame'], config['scale_check_frame']}
    if anchor_frames != {100, 175}:
        raise ValueError('frozen depth anchor frames changed')
    anchors = [r for r in inputs.get('depth', []) if r.get('identity', {}).get('branch') == 'depth'
               and r['identity'].get('camera') in cameras]
    anchor_keys = [(r['identity']['camera'], r['identity']['frame']) for r in anchors]
    if len(anchors) != 60 or set(anchor_keys) != {(c, f) for c in cameras for f in anchor_frames}:
        raise ValueError('anchor membership changed or incomplete')
    by_source = dict(zip(keys, rows))
    by_anchor = dict(zip(anchor_keys, anchors))
    remaps, footprints, verified = {}, {}, []
    for camera in sorted(cameras):
        K, maps = undistortion(calibration_rows[camera])
        remaps[camera] = (K, maps)
        valid = cv2.remap(np.ones((540, 960), np.uint8), *maps,
                          cv2.INTER_NEAREST, borderMode=cv2.BORDER_CONSTANT) > 0
        footprints[camera] = valid
        for frame in sorted(anchor_frames):
            source = by_source[camera, frame]
            anchor = by_anchor[camera, frame]
            if (anchor.get('grid') != 'scale-opencv-integer' or
                    not np.array_equal(anchor['K'], K)):
                raise ValueError('anchor grid/intrinsics changed')
            image = cv2.imread(verify_record(source['rgb'])['path'], cv2.IMREAD_COLOR)
            if image is None or image.shape != (540, 960, 3):
                raise ValueError('accepted source RGB invalid')
            remapped = cv2.remap(image, *maps, cv2.INTER_LINEAR,
                                  borderMode=cv2.BORDER_CONSTANT)
            encoded, payload = cv2.imencode('.png', remapped)
            accepted = verify_record(anchor['rgb'])
            accepted_image = cv2.imread(accepted['path'], cv2.IMREAD_COLOR)
            if accepted_image is None or accepted_image.shape != (540, 960, 3):
                raise ValueError('accepted anchor RGB grid changed')
            with np.load(verify_record(anchor['samples'])['path'], allow_pickle=False) as samples:
                if (not np.array_equal(samples['K'], K) or
                        not np.array_equal(samples['valid'].astype(bool), valid)):
                    raise ValueError('accepted anchor intrinsics/footprint changed')
            if not encoded:
                raise ValueError('decoded anchor diagnostic encoding failed')
            decoded_hash = hashlib.sha256(payload.tobytes()).hexdigest()
            difference = np.abs(remapped.astype(np.int16) - accepted_image.astype(np.int16))
            verified.append(dict(camera=camera, frame=frame, accepted_rgb=accepted,
                source_rgb=source['rgb'], samples=anchor['samples'],
                decoded_remapped_sha256=decoded_hash,
                decoded_drift=dict(matches_accepted_bytes=decoded_hash == accepted['sha256'],
                    max_absolute_pixel_difference=int(difference.max()),
                    changed_pixel_count=int(np.any(difference != 0, axis=2).sum())),
                pixel_source='frozen accepted anchor RGB; no second remap'))
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    masks = {}
    for camera, valid in footprints.items():
        path = output / f'camera{camera}-valid.npy'
        with path.open('xb') as stream:
            np.save(stream, valid, allow_pickle=False)
        masks[camera] = file_record(path)
    context_rows = []
    for camera, frame in sorted(expected):
        row = by_source[camera, frame]
        context_rows.append(dict(camera=camera, frame=frame,
            role='fit' if frame <= 149 else 'check', timestamp=frame / 25,
            source_rgb=by_anchor[camera, frame]['rgb'] if frame in anchor_frames else row['rgb'],
            source_rgb_grid='scale-opencv-integer' if frame in anchor_frames else 'distorted-opencv-integer',
            accepted_anchor=frame in anchor_frames, decoded_source_rgb=row['rgb'],
            source_video=row['source_video'],
            K=remaps[camera][0].tolist(), valid=masks[camera],
            grid='scale-opencv-integer'))
    write_json(output / 'context.json', dict(schema=SCHEMA, inputs=inputs_record,
        calibration=calibration, roles=dict(fit=[50, 149], check=[150, 199]),
        reset_boundaries='each camera and role', rows=context_rows, anchors=verified,
        excluded_cameras=config['held_out_cameras']))
    return file_record(output / 'context.json')


def materialize_role(context_record, camera, role):
    """Decode one immutable camera/role context on the accepted scale grid."""
    import cv2
    from basketball_scale import undistortion

    verify_record(context_record)
    context = read_json(context_record['path'])
    if context.get('schema') != SCHEMA or role not in ('fit', 'check'):
        raise ValueError('accepted video context/role required')
    expected = list(range(50, 150)) if role == 'fit' else list(range(150, 200))
    rows = [row for row in context['rows'] if row['camera'] == camera and row['role'] == role]
    if len(rows) != len(expected) or [row['frame'] for row in rows] != expected:
        raise ValueError('video context camera/role membership changed')
    calibration = {row['camera_id']: row for row in read_json(
        verify_record(context['calibration'])['path'])['cameras']}
    if camera not in calibration:
        raise ValueError('video context camera calibration missing')
    K, maps = undistortion(calibration[camera])
    if any(not np.array_equal(row['K'], K) or row['grid'] != 'scale-opencv-integer'
           for row in rows):
        raise ValueError('video context scale grid changed')
    valid_record = rows[0]['valid']
    if any(row['valid'] != valid_record for row in rows):
        raise ValueError('video context footprint changed within a role')
    valid = np.load(verify_record(valid_record)['path'], allow_pickle=False)
    if valid.shape != (540, 960) or valid.dtype != np.bool_:
        raise ValueError('video context footprint grid changed')
    inputs = read_json(verify_record(context['inputs'])['path'])
    anchors = {(row['identity']['camera'], row['identity']['frame']): row
               for row in inputs['depth']}
    for row in rows:
        if row['frame'] in (100, 175):
            anchor = anchors.get((camera, row['frame']))
            if (anchor is None or row['source_rgb'] != anchor['rgb'] or
                    not np.array_equal(row['K'], anchor['K'])):
                raise ValueError('accepted anchor source/intrinsics changed')
            with np.load(verify_record(anchor['samples'])['path'], allow_pickle=False) as samples:
                if not np.array_equal(samples['valid'].astype(bool), valid):
                    raise ValueError('accepted anchor footprint changed')
    return np.stack([_source_pixels(row, maps) for row in rows]), valid, rows


def _source_pixels(row, maps):
    """Use the identical explicit RGB source for inference and displayed clips."""
    import cv2
    is_anchor = row['frame'] in (100, 175)
    expected_grid = 'scale-opencv-integer' if is_anchor else 'distorted-opencv-integer'
    if (row.get('source_rgb_grid') != expected_grid or
            row.get('accepted_anchor') is not is_anchor):
        raise ValueError('source RGB grid/accepted anchor binding changed')
    image = cv2.imread(verify_record(row['source_rgb'])['path'], cv2.IMREAD_COLOR)
    if image is None or image.shape != (540, 960, 3):
        raise ValueError('accepted video source frame invalid')
    if not is_anchor:
        image = cv2.remap(image, *maps, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def _validate_source_lineage(context):
    """Bind displayed/inferred pixels to accepted inputs, including anchor reuse."""
    inputs = read_json(verify_record(context['inputs'])['path'])
    decoded = {(row['identity']['camera'], row['identity']['frame']): row
               for row in inputs['rgb'] if row['identity']['branch'] == 'calibration'}
    anchors = {(row['identity']['camera'], row['identity']['frame']): row
               for row in inputs['depth'] if row['identity']['branch'] == 'depth'}
    proofs = {(row['camera'], row['frame']): row for row in context['anchors']}
    for row in context['rows']:
        key = row['camera'], row['frame']
        source = decoded.get(key)
        is_anchor = key[1] in (100, 175)
        grid = 'scale-opencv-integer' if is_anchor else 'distorted-opencv-integer'
        if (source is None or row.get('decoded_source_rgb') != source['rgb'] or
                row.get('source_video') != source['source_video'] or
                row.get('source_rgb_grid') != grid or
                row.get('accepted_anchor') is not is_anchor):
            raise ValueError('depth context decoded source lineage changed')
        if not is_anchor:
            if row['source_rgb'] != source['rgb']:
                raise ValueError('depth context source RGB changed')
            continue
        anchor, proof = anchors.get(key), proofs.get(key)
        if (anchor is None or proof is None or row['source_rgb'] != anchor['rgb'] or
                proof.get('accepted_rgb') != anchor['rgb'] or
                proof.get('source_rgb') != source['rgb'] or
                proof.get('samples') != anchor['samples'] or
                not np.array_equal(row['K'], anchor['K'])):
            raise ValueError('depth context accepted anchor binding changed')
        verify_record(anchor['rgb'])
        with np.load(verify_record(anchor['samples'])['path'], allow_pickle=False) as samples:
            valid = np.load(verify_record(row['valid'])['path'], allow_pickle=False)
            if (not np.array_equal(samples['K'], row['K']) or
                    not np.array_equal(samples['valid'].astype(bool), valid)):
                raise ValueError('depth context accepted anchor footprint changed')


def _clip_pixels(values, valid, domain, bounds):
    if domain == 'camera_z_metres':
        if not np.isfinite(values[valid]).all() or (values[valid] <= 0).any():
            raise ValueError('metric clip requires positive finite camera-z metres')
    elif not np.isfinite(values[valid]).all():
        raise ValueError('relative clip contains nonfinite valid pixels')
    low, high = bounds
    if low == high:
        normalized = np.full(values.shape, .5, np.float32)
    else:
        normalized = np.clip((np.nan_to_num(values, nan=low) - low) / (high - low), 0, 1)
    pixels = np.stack((normalized * 255, (1 - np.abs(normalized * 2 - 1)) * 255,
                       (1 - normalized) * 255), axis=-1).astype(np.uint8)
    pixels[~valid] = [255, 0, 255]
    if domain == 'camera_z_metres':
        pixels[valid & (values > 20)] = [255, 0, 0]
    return pixels


def _encode_video(path, frames, deadline):
    command = ['ffmpeg', '-v', 'error', '-threads', '1', '-f', 'rawvideo',
        '-pixel_format', 'rgb24', '-video_size', '960x540', '-framerate', '25',
        '-i', '-', '-frames:v', '50', '-c:v', 'libx264', '-preset', 'ultrafast',
        '-crf', '25', '-threads', '1', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', str(path)]
    process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                               stderr=subprocess.PIPE)
    try:
        count = 0
        for frame in frames:
            if time.monotonic() >= deadline or frame.shape != (540, 960, 3) or frame.dtype != np.uint8:
                raise ValueError('clip deadline or frame grid violated')
            process.stdin.write(frame.tobytes())
            count += 1
        if count != 50:
            raise ValueError('clip requires exactly 50 frames')
        process.stdin.close()
        process.stdin = None
        _, error = process.communicate(timeout=max(.001, deadline - time.monotonic()))
        if process.returncode:
            raise ValueError(f'ffmpeg clip encode failed: {error.decode(errors="replace")}')
    except BaseException:
        process.kill()
        process.communicate()
        raise
    return file_record(path)


def publish_fixture_clips(context_record, candidate, domain, map_rows, anchor_records,
                          output, provenance, *, max_seconds=120,
                          record_kind='fixture', resource_guard=None):
    """Publish matched clips from independently bound raw map records."""
    import cv2
    from basketball_scale import undistortion

    start = time.monotonic()
    deadline = start + max_seconds
    verify_record(context_record)
    context = read_json(context_record['path'])
    if context.get('schema') != SCHEMA or candidate not in ('D2', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11'):
        raise ValueError('accepted depth context/candidate required')
    expected_domain = ('relative_inverse' if candidate == 'D9' else
                       'relative_log' if candidate == 'D11' else 'camera_z_metres')
    if domain != expected_domain:
        raise ValueError('candidate domain changed')
    if candidate == 'D10':
        release = read_json(ROOT / 'configs/vipe-alternatives/depth-extension-v1.json')
        convention = release['candidates']['D10'].get('convention', {})
        if convention.get('kind') != 'camera_z' or convention.get('conversion_count') != 0:
            raise ValueError('D10 camera-z convention unverified')
    if record_kind not in ('fixture', 'actual'):
        raise ValueError('depth clip record kind required')
    for key in ('source_result', 'configuration', 'ledger_outcome'):
        verify_record(provenance[key])
    if record_kind == 'actual':
        verify_record(provenance['admission'])
    if candidate == 'D2' and record_kind == 'actual':
        verify_record(provenance['historical_result'])
    cameras = (1, 11, 21, 31)
    expected = {(camera, frame) for camera in cameras for frame in range(150, 200)}
    context_rows = {(row['camera'], row['frame']): row for row in context['rows']}
    if not expected <= set(context_rows) or len(context_rows) != 4500:
        raise ValueError('full accepted context required for clips')
    if record_kind == 'actual':
        from .ledger import Ledger
        from .config import load
        completed = read_json(provenance['ledger_outcome']['path'])
        result = read_json(provenance['source_result']['path'])
        if result.get('context') != context_record:
            raise ValueError('actual depth result context binding changed')
        _validate_source_lineage(context)
        admission = read_json(provenance['admission']['path'])
        run_root = Path(provenance['source_result']['path']).resolve().parents[2]
        effective = dict(load(), new_download_gib_limit=110,
                         new_artifact_disk_gib_limit=210)
        events = Ledger(run_root / 'ledger.jsonl', effective).events()
        if (completed not in events or completed.get('event') != 'finish' or
                completed.get('status') != 'complete' or
                completed.get('result') != provenance['source_result'] or
                result.get('status') != 'complete' or
                result.get('record_kind') != 'actual' or
                result.get('candidate', result.get('component')) != candidate or
                admission.get('schema') != 'plan069-depth-admission-result/v1' or
                admission.get('candidate') != candidate or
                admission.get('status') != 'passed'):
            raise ValueError('actual depth clips require admitted ledger-complete map result')
        native_rows = {(row['camera'], row['frame']): row for row in result['rows']}
        if not expected <= set(native_rows):
            raise ValueError('actual map result lacks complete clip rows')
    keys = [(row['camera'], row['frame']) for row in map_rows]
    if len(keys) != 200 or set(keys) != expected or len(set(keys)) != len(keys):
        raise ValueError('four complete unique 50-frame maps required')
    if set(anchor_records) != set(cameras):
        raise ValueError('four historical check anchors required')
    rows = dict(zip(keys, map_rows))
    settings = {row['settings'] for row in map_rows}
    if len(settings) != 1 or not next(iter(settings)):
        raise ValueError('one exact candidate setting required')
    if candidate == 'D2':
        historical_record = (provenance['historical_result'] if record_kind == 'actual'
                             else provenance['source_result'])
        historical = read_json(historical_record['path'])
        historical_rows = {(row['identity']['camera'], row['identity']['frame']): row
                           for row in historical.get('rows', [])}
        if (historical.get('component') != 'D2' or historical.get('status') != 'complete' or
                historical.get('component_sha256') != next(iter(settings)) or
                historical.get('configuration') != provenance['configuration'] or
                not {(camera, 175) for camera in cameras} <= set(historical_rows)):
            raise ValueError('historical D2 result/settings binding required')
        for camera in cameras:
            accepted = historical_rows[camera, 175]
            if (accepted['depth'] != anchor_records[camera] or
                    accepted['grid'] != 'scale-opencv-integer' or
                    accepted['source_rgb_sha256'] != context_rows[camera, 175]['source_rgb']['sha256'] or
                    not np.array_equal(accepted['K'], context_rows[camera, 175]['K'])):
                raise ValueError('historical D2 anchor grid/source/output changed')
    for key, row in rows.items():
        source = context_rows[key]
        if record_kind == 'actual':
            native = native_rows[key]
            if (native.get('prediction', native.get('depth')) != row['prediction'] or
                    native.get('source_rgb') != row['source_rgb']):
                raise ValueError('actual clip map differs from completed native result')
        if (row['source_rgb'] != source['source_rgb'] or row['inputs'] != context['inputs'] or
                row['grid'] != 'scale-opencv-integer' or row['domain'] != domain or
                row.get('reused_anchor') is not (key[1] == 175)):
            raise ValueError('clip map source/context/role binding changed')
        if key[1] == 175 and row['prediction'] != anchor_records[key[0]]:
            raise ValueError('frame-175 anchor reuse differs from accepted result')
    output = Path(output)
    if resource_guard is not None:
        resource_guard()
    output.mkdir(parents=True, exist_ok=False)
    calibration_rows = {entry['camera_id']: entry for entry in read_json(context['calibration']['path'])['cameras']}
    selections, rgb_media, depth_media, normalization = [], [], [], {}
    map_cache = {}
    for camera in cameras:
        selection = dict(id=f'camera{camera}-selection-150-199', kind='clip', role='selection',
            camera_id=str(camera), frame_ids=list(range(150, 200)),
            timestamps=[frame / 25 for frame in range(150, 200)])
        selections.append(selection)
        K, maps = undistortion(calibration_rows[camera])
        if not np.array_equal(K, context_rows[camera, 175]['K']):
            raise ValueError('clip remap differs from context scale grid')
        samples = []
        for frame in range(150, 200):
            record = rows[camera, frame]['prediction']
            cache_key = (record['sha256'], record['path'])
            if cache_key not in map_cache:
                verify_record(record)
                with np.load(record['path'], allow_pickle=False) as data:
                    key = 'depth' if domain == 'camera_z_metres' else 'relative'
                    value, valid = data[key].copy(), data['valid'].copy()
                if value.shape != (540, 960) or value.dtype != np.float32 or valid.shape != value.shape or valid.dtype != np.bool_:
                    raise ValueError('clip map grid/dtype invalid')
                if not np.isnan(value[~valid]).all():
                    raise ValueError('clip map invalid pixels must be NaN')
                map_cache[cache_key] = (value, valid)
            value, valid = map_cache[cache_key]
            if (valid & ~np.load(context_rows[camera, frame]['valid']['path'], allow_pickle=False)).any():
                raise ValueError('clip map exceeds accepted footprint')
            samples.append((value, valid))
        observed = np.concatenate([value[valid] for value, valid in samples])
        if not len(observed):
            raise ValueError('all-invalid clip is unavailable, not a continuous comparison')
        bounds = (0., 20.) if domain == 'camera_z_metres' else (float(observed.min()), float(observed.max()))
        normalization[selection['id']] = dict(raw_range=list(bounds),
            constant_value=bounds[0] if bounds[0] == bounds[1] else None,
            invalid_pixels=sum(int((~valid).sum()) for _, valid in samples),
            above_20_metres=sum(int((valid & (value > 20)).sum()) for value, valid in samples)
                if domain == 'camera_z_metres' else None)
        def source_frames():
            for frame in range(150, 200):
                yield _source_pixels(context_rows[camera, frame], maps)
        def depth_frames():
            for value, valid in samples:
                yield _clip_pixels(value, valid, domain, bounds)
        if resource_guard is not None:
            resource_guard()
        source_video = _encode_video(output / f'camera{camera}-source.mp4', source_frames(), deadline)
        if resource_guard is not None:
            resource_guard()
        depth_video = _encode_video(output / f'camera{camera}-{candidate}.mp4', depth_frames(), deadline)
        if resource_guard is not None:
            resource_guard()
        common = dict(selection_id=selection['id'], kind='clip', camera_id=str(camera),
            frame_ids=selection['frame_ids'], timestamps=selection['timestamps'], resolution=[960, 540])
        rgb_media.append(dict(common, record=source_video,
            source_images=[context_rows[camera, f]['source_rgb'] for f in range(150, 200)]))
        depth_media.append(dict(common, record=depth_video,
            source_maps=[rows[camera, f]['prediction'] for f in range(150, 200)]))
    display = (dict(domain=domain, range_metres=[0, 20], invalid_color='magenta',
                    above_20_metres_color='red', direction='larger means farther',
                    per_clip=normalization) if domain == 'camera_z_metres' else
               dict(domain=domain, units='relative arbitrary values',
                    direction='larger means nearer' if domain == 'relative_inverse'
                        else 'larger means farther', normalization_scope='whole 50-frame clip',
                    per_clip=normalization))
    manifest = dict(schema='plan067-qualitative-package/v1', mode='qualitative',
        record_kind=record_kind, id=f'{candidate}-matched-clips-{record_kind}',
        bindings=dict(source=file_record(__file__), config=provenance['configuration'],
            inputs=context['inputs'],
            amendment=file_record(ROOT / 'docs/specs/plan031-execution/depth-comparison-extension.md')),
        settings=dict(fps=25, resolution=[960, 540], color_handling='sRGB',
            crop=[0, 0, 960, 540], detail_regions=[
                dict(id='center', crop=[240, 135, 480, 270]),
                dict(id='left', crop=[0, 135, 480, 270]),
                dict(id='right', crop=[480, 135, 480, 270])], depth_display=display),
        selections=selections, candidates=[
            dict(id='source-rgb', label='Accepted source RGB', is_control=True,
                stage='accepted input', output_type='reference', status='available',
                reason='', provenance=provenance, media=rgb_media),
            dict(id=candidate, label=f'{candidate} {domain}', is_control=False,
                stage='depth component diagnostic', output_type='component', status='available',
                reason='', provenance=provenance, media=depth_media)])
    if record_kind == 'actual':
        manifest['bindings'].update(depth_context=context_record,
            depth_result=provenance['source_result'],
            depth_admission=provenance['admission'],
            depth_finish=provenance['ledger_outcome'])
    package = publish_package(manifest, output / 'package', deadline=deadline)['package']
    receipt = dict(schema='plan069-depth-clips-result/v1', status='complete',
        record_kind=record_kind, candidate=candidate, context=context_record,
        package=package, clips=4, new_map_identities=196,
        display=display, elapsed_seconds=time.monotonic() - start)
    write_json(output / 'result.json', receipt)
    return receipt


def validate_actual_depth_package(manifest):
    """Bind Plan 069 actual media to an admitted, ledger-finished map result."""
    from .ledger import Ledger
    from .config import load

    bindings = manifest['bindings']
    for key in ('depth_context', 'depth_result', 'depth_admission', 'depth_finish'):
        verify_record(bindings[key])
    context = read_json(bindings['depth_context']['path'])
    result = read_json(bindings['depth_result']['path'])
    if result.get('context') != bindings['depth_context']:
        raise ValueError('actual depth result context binding changed')
    admission = read_json(bindings['depth_admission']['path'])
    finish = read_json(bindings['depth_finish']['path'])
    run_root = Path(bindings['depth_result']['path']).resolve().parents[2]
    effective = dict(load(), new_download_gib_limit=110,
                     new_artifact_disk_gib_limit=210)
    if finish not in Ledger(run_root / 'ledger.jsonl', effective).events():
        raise ValueError('actual depth package finish absent from live ledger')
    candidates = manifest['candidates']
    if (context.get('schema') != SCHEMA or len(context.get('rows', [])) != 4500 or
            len(candidates) != 2 or candidates[0]['id'] != 'source-rgb' or
            candidates[1]['id'] not in ('D2', 'D5', 'D6', 'D7', 'D8', 'D9', 'D10', 'D11')):
        raise ValueError('actual depth package context or candidate membership changed')
    candidate = candidates[1]['id']
    if (manifest.get('id') != f'{candidate}-matched-clips-actual' or
            result.get('status') != 'complete' or
            result.get('record_kind') != 'actual' or
            result.get('candidate', result.get('component')) != candidate or
            finish.get('event') != 'finish' or finish.get('status') != 'complete' or
            finish.get('result') != bindings['depth_result'] or
            admission.get('schema') != 'plan069-depth-admission-result/v1' or
            admission.get('status') != 'passed' or admission.get('candidate') != candidate):
        raise ValueError('actual depth package lacks admitted completed map result')
    expected = {(camera, frame) for camera in (1, 11, 21, 31)
                for frame in range(150, 200)}
    sources = {(row['camera'], row['frame']): row for row in context['rows']}
    rows = {(row['camera'], row['frame']): row for row in result['rows']}
    if len(sources) != 4500 or not expected <= set(sources) or not expected <= set(rows):
        raise ValueError('actual depth package lacks complete source/map context')
    if len(rows) != len(result['rows']):
        raise ValueError('actual depth package contains duplicate map rows')
    _validate_source_lineage(context)
    for key in expected:
        if rows[key].get('source_rgb') != sources[key]['source_rgb']:
            raise ValueError('actual depth map source RGB lineage changed')
    selections = {(int(row['camera_id']), tuple(row['frame_ids']))
                  for row in manifest['selections']}
    if selections != {(camera, tuple(range(150, 200)))
                      for camera in (1, 11, 21, 31)}:
        raise ValueError('actual depth package clip selections changed')
    for candidate_row in candidates:
        if (len(candidate_row['media']) != 4 or
                {int(media['camera_id']) for media in candidate_row['media']} !=
                {1, 11, 21, 31}):
            raise ValueError('actual depth package requires four matched clips')
    for media in candidates[0]['media']:
        camera = int(media['camera_id'])
        images = [sources[camera, frame]['source_rgb']
                  for frame in range(150, 200)]
        if media.get('source_images') != images:
            raise ValueError('actual source clip lineage changed')
        for image in images:
            verify_record(image)
    for media in candidates[1]['media']:
        camera = int(media['camera_id'])
        maps = [rows[camera, frame].get('prediction',
                rows[camera, frame].get('depth')) for frame in range(150, 200)]
        if media.get('source_maps') != maps:
            raise ValueError('actual depth clip map lineage changed')
        for record in maps:
            verify_record(record)
    for candidate_row in candidates:
        provenance = candidate_row['provenance']
        if (provenance.get('source_result') != bindings['depth_result'] or
                provenance.get('ledger_outcome') != bindings['depth_finish'] or
                provenance.get('admission') != bindings['depth_admission'] or
                provenance.get('configuration') != bindings['config']):
            raise ValueError('actual depth package provenance changed')
