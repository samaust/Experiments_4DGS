"""Selection support diagnostics after an explicitly admitted failed metric fit."""
import numpy as np

from .config import ROOT, training_cameras
from .contracts import depth as validate_depth, sample_depth
from .files import digest, load_array, read_json, verify_record


def selection_support(rows, predictions, config, *, provenance, frozen_fit):
    """Report support for all check cameras without estimating any replacement scale."""
    fit = read_json(verify_record(frozen_fit)['path'])
    verify_record(provenance['inputs'])
    required = set(training_cameras(config))
    if (fit.get('status') == 'passed' or fit.get('role') != 'fit' or
            fit.get('provenance') != provenance or
            fit.get('scale_protocol_sha256') != digest(ROOT / 'configs/basketball-rev2/scale.json') or
            len(rows) != len(required) or {r['identity']['camera'] for r in rows} != required or
            set(predictions) != required or
            {r['identity']['frame'] for r in rows} != {config['scale_check_frame']}):
        raise ValueError('failed frozen fit and complete bound check cameras required')
    cameras = []
    for row in sorted(rows, key=lambda r: r['identity']['camera']):
        camera = row['identity']['camera']
        with load_array(row['samples']) as geometry, load_array(predictions[camera]) as output:
            depth, valid = output['depth'], output['valid']
            image_valid = geometry['valid'] > 0
            validate_depth(depth, valid, image_valid)
            if not np.array_equal(geometry['K'], row['K']):
                raise ValueError('check support camera intrinsics changed')
            _, good = sample_depth(depth, valid, geometry['uv'])
            good &= np.isfinite(geometry['camera_z']) & (geometry['camera_z'] > 0)
            cells = np.floor(geometry['uv'][good] / [240, 135]).astype(int)
            cameras.append(dict(camera_id=camera, sampled_valid_points=int(good.sum()),
                occupied_grid_cells=len(set(map(tuple, cells))),
                positive_depth_fraction=float(valid[image_valid].mean())))
    return dict(status='blocked', role='selection', scale=None,
        blockers=['No passing frozen fit; qualitative-only admission'],
        fit_blockers=fit.get('blockers', []), fit_cameras=fit.get('cameras', []),
        cameras=cameras, diagnostics='support-only; no selection scale estimated',
        frozen_fit=frozen_fit, provenance=provenance,
        scale_protocol_sha256=digest(ROOT / 'configs/basketball-rev2/scale.json'),
        estimator_sha256=digest(ROOT / 'scripts/basketball_scale.py'),
        physical_accuracy='unverified')
