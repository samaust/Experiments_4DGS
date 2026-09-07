"""Revision-one sharpness-aware static SIFT databases, without pose estimation."""
import argparse
import json
from pathlib import Path
import time
import cv2
import numpy as np
from basketball_audit import sha256
from basketball_focus import sharpness_maps, best_observations
from basketball_geometry import connected_components
from basketball_protocol import TRAINING, PROTOCOL
from basketball_recovery import EARLY, LATE, window_intrinsics
from basketball_static_rig import register_image


def prepare(priors_path, output, frames, dsp=False):
    import pycolmap as colmap
    if colmap.__version__ != '4.2.0':
        raise ValueError('requires pinned PyCOLMAP 4.2.0')
    if tuple(frames) not in (EARLY, LATE, EARLY + LATE):
        raise ValueError('requires predefined fitting windows')
    report = json.loads((priors_path / 'result.json').read_text())
    if report['status'] != 'priors-generated' or report['blockers']:
        raise ValueError('requires complete passing priors')
    Ks = window_intrinsics(report, frames)
    selected = sorted([e for e in report['observations'] if e['camera_id'] in TRAINING and e['source_frame_id'] in frames],
                      key=lambda e: (e['camera_id'], e['source_frame_id']))
    artifacts = json.loads((priors_path / 'artifacts.json').read_text())
    output.mkdir(exist_ok=False)
    images = output / 'images'; images.mkdir()
    masks = output / 'masks'; masks.mkdir()
    merged_images = output / 'merged-images'; merged_images.mkdir()
    extraction = colmap.FeatureExtractionOptions(num_threads=8, use_gpu=False)
    extraction.sift.max_num_features = 16384 if dsp else 8192
    extraction.sift.estimate_affine_shape = dsp
    extraction.sift.domain_size_pooling = dsp
    matching = colmap.FeatureMatchingOptions(num_threads=8, use_gpu=False, guided_matching=dsp)
    config = dict(schema='basketball-static-features/v1', protocol=PROTOCOL, fit_frames=frames,
                  recipe='sharp-dsp' if dsp else 'sharp-sift', priors_sha256=sha256(priors_path / 'result.json'),
                  artifacts_sha256=sha256(priors_path / 'artifacts.json'), adapter_sha256=sha256(__file__),
                  focus_adapter_sha256=sha256('scripts/basketball_focus.py'),
                  extraction=extraction.todict(), matching=matching.todict(), sharpness_percentile=20,
                  min_patch_variance=1e-4, deduplication_pixels=2, seed=0)
    (output / 'config.json').write_text(json.dumps(config, indent=2, default=str) + '\n')
    result = dict(schema='basketball-static-features-result/v1', protocol=PROTOCOL, status='blocked', blockers=[],
                  config_sha256=sha256(output / 'config.json'), features={}, verified_edges=[], source_frames=frames)
    started = time.monotonic()
    try:
        with colmap.Database.open(output / 'per-frame.db') as db:
            for index, entry in enumerate(selected, 1):
                name = entry['stem'] + '.png'; mask = entry['stem'] + '-static.png'
                for artifact in (name, mask):
                    if sha256(priors_path / artifact) != artifacts[artifact]:
                        raise ValueError(f'changed fitting artifact: {artifact}')
                (images / name).symlink_to((priors_path / name).resolve())
                (masks / (name + '.png')).symlink_to((priors_path / mask).resolve())
                register_image(db, colmap, camera_id=entry['camera_id']+1, image_id=index,
                               name=name, K=Ks[entry['camera_id']])
        colmap.set_random_seed(0)
        colmap.extract_features(output / 'per-frame.db', images,
                               reader_options=colmap.ImageReaderOptions(camera_model='PINHOLE', mask_path=masks),
                               extraction_options=extraction, device=colmap.Device.cpu)
        with colmap.Database.open(output / 'per-frame.db') as raw, colmap.Database.open(output / 'merged.db') as merged:
            for camera in TRAINING:
                candidates = []; keys_by_frame = {}; desc_by_frame = {}; raw_count = 0; dtype = None
                for index, entry in enumerate(selected, 1):
                    if entry['camera_id'] != camera:
                        continue
                    frame = entry['source_frame_id']
                    keys = raw.read_keypoints(index); descriptors = raw.read_descriptors(index)
                    keys_by_frame[frame] = keys; desc_by_frame[frame] = descriptors.data; dtype = descriptors.type
                    raw_count += len(keys)
                    gray = cv2.imread(str(priors_path / (entry['stem'] + '.png')), cv2.IMREAD_GRAYSCALE)
                    mask = cv2.imread(str(priors_path / (entry['stem'] + '-static.png')), cv2.IMREAD_GRAYSCALE)
                    distance = cv2.distanceTransform((mask > 0).astype(np.uint8), cv2.DIST_L2, 5)
                    score, variance = sharpness_maps(gray)
                    radii = (np.linalg.svd(keys[:, 2:].reshape(-1, 2, 2), compute_uv=False)[:, 0]
                             if keys.shape[1] == 6 else np.abs(keys[:, 2])) * 6
                    xy = np.floor(keys[:, :2]).astype(int)
                    valid = (xy[:, 0] >= 11) & (xy[:, 0] < 949) & (xy[:, 1] >= 11) & (xy[:, 1] < 529)
                    indices = np.flatnonzero(valid)
                    xx, yy = xy[indices].T
                    indices = indices[(distance[yy, xx] >= np.maximum(8., radii[indices])) & (variance[yy, xx] >= 1e-4)]
                    candidates.extend(dict(score=float(score[xy[i, 1], xy[i, 0]]), frame=frame, index=int(i), uv=keys[i, :2]) for i in indices)
                if not candidates:
                    raise ValueError(f'camera {camera}: no static textured features')
                threshold = float(np.percentile([e['score'] for e in candidates], 20))
                selected_keys = best_observations([e for e in candidates if e['score'] >= threshold])
                keypoints = np.array([keys_by_frame[e['frame']][e['index']] for e in selected_keys], np.float32)
                descriptors = np.array([desc_by_frame[e['frame']][e['index']] for e in selected_keys], np.uint8)
                name = f'camera{camera}.png'
                (merged_images / name).symlink_to((priors_path / f'camera{camera}-frame{frames[0]}.png').resolve())
                register_image(merged, colmap, camera_id=camera+1, image_id=camera+1, name=name, K=Ks[camera])
                merged.write_keypoints(camera+1, keypoints)
                merged.write_descriptors(camera+1, colmap.FeatureDescriptors(dtype, descriptors))
                np.save(output / f'camera{camera}-feature-sources.npy', np.array([[e['frame'], e['index']] for e in selected_keys], np.int32))
                cells = np.floor(keypoints[:, :2] / [240, 135]).astype(int)
                result['features'][str(camera)] = dict(raw=raw_count, static_textured=len(candidates), retained=len(selected_keys),
                    sharpness_threshold=threshold, occupied_grid_cells=len(set(map(tuple, cells))))
        colmap.match_exhaustive(output / 'merged.db', matching_options=matching, device=colmap.Device.cpu)
        with colmap.Database.open(output / 'merged.db') as db:
            for i, camera in enumerate(TRAINING):
                for other in TRAINING[i+1:]:
                    if db.exists_two_view_geometry(camera+1, other+1):
                        g = db.read_two_view_geometry(camera+1, other+1)
                        if len(g.inlier_matches) >= 30:
                            result['verified_edges'].append(dict(cameras=[camera, other], inliers=len(g.inlier_matches), configuration=str(g.config)))
        result['components'] = connected_components(TRAINING, [e['cameras'] for e in result['verified_edges']])
        result['status'] = 'features-generated'
    except BaseException as error:
        result['blockers'].append(f'{type(error).__name__}: {error}')
        raise
    finally:
        result['wall_seconds'] = time.monotonic() - started
        (output / 'result.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--priors', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--window', required=True, choices=['early', 'late', 'pooled'])
    p.add_argument('--dsp', action='store_true')
    a = p.parse_args()
    prepare(a.priors, a.output, {'early': EARLY, 'late': LATE, 'pooled': EARLY+LATE}[a.window], a.dsp)


if __name__ == '__main__':
    main()
