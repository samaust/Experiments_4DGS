"""One bounded preparation pass over frozen historical parents and allowed RGB."""
from pathlib import Path
import shutil
import time

import numpy as np

from .access import Identity, annotation_identities, guard, output_identities, validate_membership
from .annotations import template
from .config import ROOT, counts, training_cameras
from .files import digest, file_record, object_hash, read_json, write_json

AUDIT = ROOT / '.local/calibration/basketball-v1/input-audit.json'
PROCESSED = ROOT / '.local/sync-pivot/basketball-zero/manifest.json'
CALIBRATION = ROOT / 'docs/experiments/basketball-calibration-alternatives/calibration.json'
FREEZE = ROOT / 'docs/research/basketball-sync-pivot/basketball-freeze.json'

EXPOSURES = {
    'docs/experiments/basketball-calibration-alternatives.md': 'Fitting/selection inspected in calibration development; final timestamps previously consumed.',
    'docs/experiments/basketball-calibration-alternatives/selection.json': 'Historical selection, not an untouched test.',
    'docs/experiments/basketball-calibration-alternatives/validation-consumed.json': 'Read marker only; zero new frame-200–249 images/evaluations.',
    'docs/experiments/basketball-rev2/scale-fit.json': 'Frame 100 informed the published fitting estimate.',
    'docs/experiments/basketball-rev2/scale-selection.json': 'Frame 175 is an already used frozen repeatability check.',
    'docs/experiments/basketball-dense-temporal/pilot-review.md': 'Both dense pilots failed the foreground-floater gate; masks included spectators/ball false positives.',
    'docs/experiments/basketball-dense-temporal/visual-assessment.md': 'Prior player/court/display inspection, including frame 22.',
    'docs/experiments/basketball-dense-temporal/report.md': 'Final sparse duration study complete; dense comparison remains incomplete.',
    'scripts/basketball_dense_crossing_audit.py': 'Crossing diagnostics were selected after observing artifacts.',
    'plans/plan_028.md': 'All-times arms included formerly withheld training-camera frames 20–24.',
}


def exposure_history():
    records = []
    for relative, explanation in EXPOSURES.items():
        records.append(dict(**file_record(ROOT / relative), prior_exposure=explanation,
                            current_access='report/source/metadata only; no final-window image access'))
    return dict(schema='vipe-benchmark-exposure/v1', records=records,
                diagnostic_sample='fixed engineering coverage, not random population sampling',
                untouched_external_test=False, new_final_window_image_reads=0)


def _save_array(path, array):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        np.save(stream, array, allow_pickle=False)
    return file_record(path)


def _image(path, bgr):
    import cv2
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or not cv2.imwrite(str(path), bgr):
        raise ValueError('image output exists or could not be written')
    return file_record(path)


def _sift(rgb, output, annotation):
    import cv2
    # Match the existing calibration frontend's fixed 8192 SIFT configuration;
    # retain the full unmasked pool, not only the reviewer-selected audit points.
    keys = cv2.SIFT_create(nfeatures=8192).detect(cv2.cvtColor(rgb, cv2.COLOR_BGR2GRAY), None)
    keys = sorted(keys, key=lambda k: (-k.response, k.pt[0], k.pt[1], k.size, k.angle))
    features = np.asarray([[*k.pt, k.response, k.size, k.angle] for k in keys], np.float64).reshape(-1, 5)
    record = _save_array(output, features)
    chosen, cells = [], set()
    if annotation:
        for index, feature in enumerate(features):
            cell = tuple(np.floor(feature[:2] / [240, 135]).astype(int))
            if cell not in cells:
                cells.add(cell)
                chosen.append(dict(index=index, uv=feature[:2].tolist(), response=float(feature[2]), cell=list(map(int, cell))))
    return record, chosen


def prepare(output, config, *, exposure):
    import cv2
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    cv2.setNumThreads(min(8, config['cpu_max_workers']))
    audit, processed, calibration = read_json(AUDIT), read_json(PROCESSED), read_json(CALIBRATION)
    freeze = read_json(FREEZE)
    scale_protocol = read_json(ROOT / 'configs/basketball-rev2/scale.json')
    if digest(CALIBRATION) != scale_protocol['calibration_sha256']:
        raise ValueError('accepted calibration hash changed')
    if audit['status'] != 'inputs-verified' or processed['status'] != 'prepared':
        raise ValueError('historical input prerequisite incomplete')
    if processed['source_fps'] != 25 or processed['pixel_convention'] != 'COLMAP continuous: top-left pixel center 0.5':
        raise ValueError('processed frame rate or pixel convention changed')
    cameras = {e['camera_id']: e for e in calibration['cameras']}
    processed_cameras = {int(e['id']): e for e in processed['cameras']}
    if set(cameras) != set(range(34)) or len(calibration['cameras']) != 34 or len(processed_cameras) != 34:
        raise ValueError('full rig membership mismatch')
    if sorted(map(int, processed['heldout_camera_ids'])) != config['held_out_cameras']:
        raise ValueError('processed held-out split mismatch')
    videos = {int(r['camera_id']): r for r in audit['videos']}
    if set(videos) != set(range(34)) or len(audit['videos']) != 34:
        raise ValueError('source-video audit membership mismatch')
    sources = [file_record(AUDIT), file_record(PROCESSED), file_record(CALIBRATION),
               file_record(ROOT / 'configs/basketball-rev2/scale.json')]
    sources += [file_record(FREEZE, processed['freeze_sha256']),
                file_record(ROOT / freeze['scale_path'], freeze['scale_sha256'])]
    if freeze['calibration_sha256'] != digest(CALIBRATION) or freeze['map_path'] != scale_protocol['map']:
        raise ValueError('historical scene freeze/calibration/map mismatch')
    normalization_path = ROOT / '.local/sync-pivot/runs/freetimegs-zero-seed0/worker/training-config.json'
    normalization_parent = normalization_path.with_name('checkpoint-provenance.json')
    normalization_provenance = read_json(normalization_parent)
    sources += [file_record(normalization_parent),
                file_record(normalization_path, normalization_provenance['configuration_sha256'])]
    normalization = read_json(normalization_path)['normalization']
    sources += [file_record(ROOT / 'docs/experiments/basketball-calibration-alternatives/frozen-winner.json')]
    annotation_keys = {i.key() for i in annotation_identities(config)}
    rgb_rows = []
    footprint_records = {}
    for c in range(34):
        source = file_record(videos[c]['path'], videos[c]['sha256'])
        sources.append(source)
        # The audited 250-frame videos are accessed only for frames 50..199.
        # No seek/read operation is issued for the final window.
        capture = cv2.VideoCapture(source['path'], cv2.CAP_FFMPEG,
                                   [cv2.CAP_PROP_N_THREADS, config['cpu_max_workers']])
        try:
            if not capture.isOpened() or not capture.set(cv2.CAP_PROP_POS_FRAMES, 50):
                raise ValueError(f'cannot seek audited video camera {c} to frame 50')
            if abs(capture.get(cv2.CAP_PROP_POS_FRAMES) - 50) > .01:
                raise ValueError('decoder frame seek did not preserve source identity')
            full_valid = _save_array(output / f'valid/calibration-camera{c}.npy', np.ones((540, 960), bool))
            for frame in range(50, 200):
                identity = Identity('calibration', c, frame)
                guard(identity, config, context=True)
                ok, image = capture.read()
                if not ok or image.shape != (1080, 1920, 3):
                    raise ValueError(f'invalid audited video image {c}/{frame}')
                if abs(capture.get(cv2.CAP_PROP_POS_FRAMES) - (frame + 1)) > .01:
                    raise ValueError('source frame identity drift')
                resized = cv2.resize(image, (960, 540), interpolation=cv2.INTER_AREA)
                record = _image(output / f'rgb/calibration/camera{c}/frame{frame}.png', resized)
                row = dict(identity=identity.record(), rgb=record, K=cameras[c]['K'],
                           grid='distorted-opencv-integer', valid=full_valid,
                           source_video=source, role='fit' if frame <= 149 else 'selection',
                           heldout_support='localization-only' if c in config['held_out_cameras'] else 'training-camera',
                           transform=dict(resize='INTER_AREA', native_size=[1920, 1080], output_size=[960, 540],
                                          distortion=cameras[c]['parameters_colmap']))
                if frame in config['fit_snapshots'] + config['selection_snapshots']:
                    row['sift'], row['static_feature_locations'] = _sift(resized,
                        output / f'sift/camera{c}-frame{frame}.npy', identity.key() in annotation_keys)
                rgb_rows.append(row)
        finally:
            capture.release()
        if c in training_cameras(config):
            K = np.array(processed_cameras[c]['K'], np.float64)
            K[:2, 2] -= .5
            if not np.allclose(K, cameras[c]['K'], atol=1e-10, rtol=0):
                raise ValueError('processed RGB K does not match accepted OpenCV calibration')
            for processed_field, field, factor in [('world_to_camera_R', 'R', 1.),
                                                    ('world_to_camera_T', 't', freeze['scale']),
                                                    ('center', 'center', freeze['scale'])]:
                if not np.allclose(processed_cameras[c][processed_field],
                                   np.asarray(cameras[c][field]) * factor, atol=1e-10, rtol=0):
                    raise ValueError('processed scene geometry no longer matches the historical scale')
            radial = cameras[c]['parameters_colmap'][3]
            maps = cv2.initUndistortRectifyMap(K, np.array([radial, 0., 0., 0.]), None, K, (960, 540), cv2.CV_32FC1)
            valid = cv2.remap(np.ones((540, 960), np.uint8), *maps, cv2.INTER_NEAREST,
                              borderMode=cv2.BORDER_CONSTANT) > 0
            valid_record = _save_array(output / f'valid/reconstruction-camera{c}.npy', valid)
            footprint_records[c] = valid_record
            by_frame = {r['frame_id']: r for r in processed_cameras[c]['frames']}
            if len(by_frame) != len(processed_cameras[c]['frames']) or set(by_frame) != set(range(50)):
                raise ValueError('processed RGB duplicate/missing/extra frame IDs')
            for frame in range(50):
                source_frame = by_frame[frame]
                path = (PROCESSED.parent / source_frame['path']).resolve()
                if not path.is_relative_to(PROCESSED.parent.resolve()):
                    raise ValueError('processed image path escaped its manifest directory')
                rgb_rows.append(dict(identity=Identity('reconstruction', c, frame).record(),
                    rgb=file_record(path, source_frame['sha256']), K=K.tolist(),
                    grid='undistorted-opencv-integer', valid=valid_record, role='reconstruction',
                    source_manifest=file_record(PROCESSED), transform=dict(undistortion='frozen SIMPLE_RADIAL RGB remap',
                        source_K=processed_cameras[c]['K'], source_centers='COLMAP +0.5', K_conversion='subtract 0.5 once')))
        print(f'prepared camera {c}: role-bounded calibration and permitted reconstruction RGB', flush=True)
    lookup = {Identity(**r['identity']).key(): r for r in rgb_rows}
    depth_rows = []
    for role_name, frame in [('fit', config['scale_fit_frame']), ('selection', config['scale_check_frame'])]:
        directory = ROOT / f'.local/calibration/basketball-rev2/scale-{role_name}-inputs'
        data, protocol = read_json(directory / 'inputs.json'), read_json(directory / 'protocol.json')
        sources += [file_record(directory / 'inputs.json'), file_record(directory / 'protocol.json', data['protocol_sha256'])]
        if data['calibration_sha256'] != scale_protocol['calibration_sha256'] or protocol['role'] != role_name:
            raise ValueError('prepared depth sample calibration/role mismatch')
        if protocol['protocol_file_sha256'] != digest(ROOT / 'configs/basketball-rev2/scale.json'):
            raise ValueError('prepared samples use different frozen eligibility/gates')
        parent_dir = ROOT / '.local/calibration/basketball-alternatives' / ('inputs' if role_name == 'fit' else 'selection-inputs')
        parent = read_json(parent_dir / 'result.json')
        sources.append(file_record(parent_dir / 'result.json'))
        parent_lookup = {(e['camera_id'], e['source_frame_id']): e for e in parent['observations']}
        for e in data['entries']:
            identity = Identity('depth', e['camera_id'], e['source_frame_id'])
            guard(identity, config)
            if identity.frame != frame:
                raise ValueError('depth role/frame mismatch')
            image = file_record(directory / (e['stem'] + '.png'), e['image_sha256'])
            samples = file_record(directory / (e['stem'] + '-samples.npz'), e['samples_sha256'])
            source_e = parent_lookup[identity.camera, identity.frame]
            source_mask = file_record(parent_dir / (source_e['stem'] + '-static.png'), e['source_mask_sha256'])
            source_rgb = file_record(parent_dir / (source_e['stem'] + '.png'), e['source_image_sha256'])
            if source_rgb['sha256'] != lookup[Identity('calibration', identity.camera, frame).key()]['rgb']['sha256']:
                raise ValueError('new audited decoding differs from the frozen source RGB')
            with np.load(samples['path'], allow_pickle=False) as geom:
                if not {'point_ids', 'xyz', 'uv', 'camera_z', 'K', 'valid'} <= set(geom.files):
                    raise ValueError('missing prepared sparse sample arrays')
                if not np.array_equal(geom['K'], e['K']) or tuple(geom['K'][:2, 2]) != (480., 270.):
                    raise ValueError('scale-grid intrinsics changed')
                if len(set(geom['point_ids'].tolist())) != len(geom['point_ids']):
                    raise ValueError('duplicate prepared point IDs')
                valid_record = _save_array(output / f'valid/depth-camera{identity.camera}-frame{frame}.npy', geom['valid'] > 0)
            depth_rows.append(dict(identity=identity.record(), rgb=image, samples=samples, valid=valid_record,
                                   K=e['K'], grid='scale-opencv-integer', static_mask=source_mask,
                                   source_rgb=source_rgb, prepared_parent=file_record(directory / 'inputs.json'),
                                   eligibility='unchanged verified historical prepared samples'))
    validate_membership(depth_rows, output_identities(config, 'depth'))
    # Freeze the unique map point sets and observation UVs without opening a
    # writable COLMAP database or regenerating calibration/features.
    import pycolmap
    map_dir = ROOT / scale_protocol['map']
    map_sources = [file_record(map_dir / name) for name in ('cameras.bin', 'images.bin', 'points3D.bin')]
    sources += map_sources
    model = pycolmap.Reconstruction(str(map_dir))
    track_sets = {c: set() for c in training_cameras(config)}
    points = {}
    observations = []
    for pid, point in sorted(model.points3D.items()):
        points[int(pid)] = point.xyz.tolist()
        for element in point.track.elements:
            image = model.images[element.image_id]
            c = int(Path(image.name).stem.removeprefix('camera'))
            if c not in track_sets:
                raise ValueError('held-out accepted-map observation')
            track_sets[c].add(int(pid))
            observations.append(dict(camera=c, point_id=int(pid), uv=(image.points2D[element.point2D_idx].xy - .5).tolist()))
    map_record = dict(points={str(k): v for k, v in points.items()},
                      tracks={str(k): sorted(v) for k, v in track_sets.items()},
                      cameras={str(c): cameras[c] for c in track_sets}, footprints={str(c): v for c, v in footprint_records.items()},
                      observations=observations, source_files=map_sources,
                      projection_grid='undistorted-opencv-integer; use supplied camera K and footprint',
                      observation_grid='historical distorted feature coordinates; project XYZ for N2')
    write_json(output / 'map.json', map_record)
    if len(rgb_rows) != counts(config)['motion_rgb'] or len(lookup) != len(rgb_rows):
        raise ValueError('RGB counts/collisions differ from the fixed protocol')
    inputs = dict(schema='vipe-benchmark-inputs/v1', status='prepared', rgb=rgb_rows, depth=depth_rows,
                  map=file_record(output / 'map.json'), source_files=sources, counts=counts(config),
                  reference_geometry=dict(freeze=file_record(FREEZE), scale=freeze['scale'],
                                          normalization=normalization,
                                          normalization_source=file_record(normalization_path)),
                  exposure_history=exposure, decoder=dict(opencv=cv2.__version__,
                      build_information=cv2.getBuildInformation(), input_order='camera, role, frame',
                      sift='OpenCV SIFT nfeatures=8192, otherwise defaults, full unmasked pool'),
                  annotation_selected_features=sum(len(r.get('static_feature_locations', [])) for r in rgb_rows))
    write_json(output / 'inputs.json', inputs)
    annotation = template(inputs, config)
    write_json(output / 'annotation-template.json', annotation)
    pack = output / 'annotation-images'
    pack.mkdir()
    for row in annotation['images']:
        identity = Identity(**row['identity'])
        target = pack / (identity.key().replace('/', '-') + '.png')
        with Path(row['rgb']['path']).open('rb') as source, target.open('xb') as dest:
            shutil.copyfileobj(source, dest)
        if digest(target) != row['rgb']['sha256']:
            raise ValueError('annotation export differs from frozen RGB')
    result = dict(status='complete', inputs=file_record(output / 'inputs.json'),
                  annotation_template=file_record(output / 'annotation-template.json'),
                  annotation_images=len(annotation['images']), reviewed_images=0,
                  wall_seconds=time.monotonic() - start, counts=counts(config))
    write_json(output / 'result.json', result)
    return result
