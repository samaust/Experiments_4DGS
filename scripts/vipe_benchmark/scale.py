"""Neutral adapter to the unchanged equal-camera scale estimator."""
import numpy as np

from .config import ROOT, training_cameras
from .contracts import depth as validate_depth, sample_depth
from .files import digest, file_record, load_array, read_json


def evaluate(rows, predictions, config, *, provenance, frozen_fit=None):
    from basketball_scale import scale_statistics
    p = read_json(ROOT / 'configs/basketball-rev2/scale.json')
    required = set(training_cameras(config))
    if len(rows) != len(required) or {r['identity']['camera'] for r in rows} != required:
        raise ValueError('every training camera must appear exactly once')
    if set(predictions) != required:
        raise ValueError('a failed camera cannot be silently dropped')
    frames = {r['identity']['frame'] for r in rows}
    expected_frame = config['scale_check_frame'] if frozen_fit is not None else config['scale_fit_frame']
    if frames != {expected_frame}:
        raise ValueError('scale fit/check role mismatch')
    frozen = None
    if frozen_fit is not None:
        fit = read_json(frozen_fit['path'])
        file_record(frozen_fit['path'], frozen_fit['sha256'])
        if (fit.get('status') != 'passed' or fit.get('role') != 'fit' or
                fit['provenance']['component_sha256'] != provenance['component_sha256'] or
                fit['scale_protocol_sha256'] != digest(ROOT / 'configs/basketball-rev2/scale.json')):
            raise ValueError('frozen fit is incomplete, changed or belongs to another candidate')
        frozen = fit['scale']
    samples, missing = [], []
    for row in sorted(rows, key=lambda r: r['identity']['camera']):
        c = row['identity']['camera']
        with load_array(row['samples']) as geom, load_array(predictions[c]) as output:
            z, valid = output['depth'], output['valid']
            image_valid = geom['valid'] > 0
            validate_depth(z, valid, image_valid)
            if not np.allclose(geom['K'], row['K'], atol=0, rtol=0):
                raise ValueError('depth sample intrinsic provenance mismatch')
            values, good = sample_depth(z, valid, geom['uv'])
            good &= np.isfinite(geom['camera_z']) & (geom['camera_z'] > 0)
            cells = np.floor(geom['uv'][good] / [240, 135]).astype(int)
            if not good.any():
                missing.append(f'camera {c}: zero valid depth support')
            samples.append(dict(camera_id=c, ratios=values[good] / geom['camera_z'][good],
                                cells=len(set(map(tuple, cells))),
                                positive_depth_fraction=float(valid[image_valid].mean())))
    # The old pure estimator raises on zero ratios. Preserve that failed camera;
    # there is no legitimate global estimate to bootstrap after omitting it.
    result = (dict(status='blocked', blockers=missing, scale=frozen,
                   cameras=[dict(camera_id=s['camera_id'], points=len(s['ratios']),
                                 occupied_grid_cells=s['cells'],
                                 positive_depth_fraction=s['positive_depth_fraction']) for s in samples])
              if missing else scale_statistics(samples, p, frozen))
    result.update(role='selection' if frozen_fit else 'fit', provenance=provenance,
                  scale_protocol_sha256=digest(ROOT / 'configs/basketball-rev2/scale.json'),
                  estimator_sha256=digest(ROOT / 'scripts/basketball_scale.py'),
                  frozen_fit=frozen_fit, physical_accuracy='unverified')
    return result
