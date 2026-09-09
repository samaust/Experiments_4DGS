"""Retain adjacent observations and native KNN motion diagnostics, never identity claims."""
import argparse
from functools import lru_cache
import json
from pathlib import Path

import numpy as np
from PIL import Image

from basketball_study import MANIFEST, ROOT, digest, training_key, write_new
from basketball_temporal_geometry import projection, track_lk
from freetimegs_initialization import load_velocity_helper


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--cloud', type=Path, required=True)
    p.add_argument('--masks', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.mkdir(parents=True, exist_ok=False)
    manifest = json.loads(MANIFEST.read_text())
    cameras = {int(c['id']): c for c in manifest['cameras']}
    result = json.loads((a.cloud / 'result.json').read_text())
    native, native_hash = load_velocity_helper(ROOT / '.local/FreeTimeGsVanilla')
    @lru_cache(maxsize=8)
    def image(camera, frame):
        training_key(camera, frame)
        entry = cameras[camera]['frames'][frame]
        path = MANIFEST.parent / entry['path']
        if digest(path) != entry['sha256']:
            raise ValueError('changed source image')
        return np.array(Image.open(path).convert('RGB'))
    records = []
    for record in result['records']:
        if 'path' not in record:
            continue
        source = a.cloud / record['path']
        if digest(source) != record['sha256']:
            raise ValueError('changed source cloud')
        arrays = dict(np.load(source, allow_pickle=False))
        selected = np.flatnonzero(arrays['region'] > 0)
        frame = record['frame']
        endpoints, validity = [], []
        for k, c in enumerate(arrays['camera_ids']):
            masks = [np.load(a.masks / f'camera{c}-frame{f}.npy', allow_pickle=False) for f in (frame, frame+1)]
            if len(selected):
                uv, valid = track_lk(image(int(c), frame), image(int(c), frame+1), arrays['uv'][k, selected], *masks)
            else:
                uv, valid = np.empty((0, 2)), np.empty(0, bool)
            endpoints.append(uv)
            validity.append(valid & arrays['support'][k, selected])
        path = a.output / record['path']
        np.savez_compressed(path, source_indices=selected, endpoint_uv=np.array(endpoints),
                            lk_valid=np.array(validity), camera_ids=arrays['camera_ids'])
        measured = arrays['velocity_valid'] & (arrays['region'] == 1)
        starts = arrays['positions'][measured]
        displacements = arrays['velocities'][measured]*.02
        diagnostic = dict(points=len(starts), scope='within this retained pair cloud; tracked endpoints form comparison pool')
        if len(starts):
            knn, valid = native(starts, starts+displacements, max_distance=.5, k=1, n_workers=1)
            errors = np.linalg.norm(knn-displacements, axis=1)
            diagnostic.update(valid=int(valid.sum()), median_displacement_difference=float(np.median(errors[valid])) if valid.any() else None,
                              p95_displacement_difference=float(np.quantile(errors[valid], .95)) if valid.any() else None)
        instances = []
        for k, c in enumerate(arrays['camera_ids']):
            for label in np.unique(arrays['instance_labels'][k]):
                supported = (arrays['region'] == 1) & arrays['support'][k] & (arrays['instance_labels'][k] == label)
                if label > 0 and supported.any():
                    instances.append(dict(camera=int(c), instance=int(label), points=int(supported.sum()),
                                          measured_motion_points=int((supported & measured).sum())))
        records.append(dict(frame=frame, reference=record['reference'], other=record['other'],
                            archive=path.name, sha256=digest(path), instances=instances, native_knn=diagnostic))
    write_new(a.output / 'result.json', dict(schema='basketball-temporal-motion-audit/v1',
        cloud_sha256=digest(a.cloud / 'result.json'), records=records,
        native_helper_ast_sha256=native_hash, native_helper_sha256=digest(ROOT / '.local/FreeTimeGsVanilla/src/combine_frames_fast_keyframes.py'),
        interpretation='KNN displacement is a diagnostic only; temporal identity requires image tracking and geometric validation'))


if __name__ == '__main__':
    main()
