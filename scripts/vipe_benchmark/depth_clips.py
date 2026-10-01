"""Accepted scale-grid video context for Plan 069 depth comparisons."""
import hashlib
from pathlib import Path

import numpy as np

from .config import ROOT, training_cameras
from .files import file_record, read_json, verify_record, write_json


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
    calibration = file_record(CALIBRATION)
    if calibration not in inputs.get('source_files', []):
        raise ValueError('accepted calibration source binding changed')
    cameras = set(training_cameras(config))
    calibration_rows = {entry['camera_id']: entry for entry in read_json(CALIBRATION)['cameras']}
    if not cameras <= set(calibration_rows):
        raise ValueError('accepted camera calibration missing')
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
            if not encoded or hashlib.sha256(payload.tobytes()).hexdigest() != accepted['sha256']:
                raise ValueError('remapped anchor bytes differ from accepted scale input')
            verified.append(dict(camera=camera, frame=frame, accepted_rgb=accepted,
                                 remapped_sha256=accepted['sha256'], source_rgb=source['rgb']))
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
            source_rgb=row['rgb'], source_video=row['source_video'],
            K=remaps[camera][0].tolist(), valid=masks[camera],
            grid='scale-opencv-integer'))
    write_json(output / 'context.json', dict(schema=SCHEMA, inputs=inputs_record,
        calibration=calibration, roles=dict(fit=[50, 149], check=[150, 199]),
        reset_boundaries='each camera and role', rows=context_rows, anchors=verified,
        excluded_cameras=config['held_out_cameras']))
    return file_record(output / 'context.json')
