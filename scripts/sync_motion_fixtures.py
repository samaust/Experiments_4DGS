"""Independent analytic-camera controls, not video-interpolation ground truth."""
import argparse
import json
from pathlib import Path

import numpy as np
from scipy.interpolate import PchipInterpolator
from scipy.optimize import minimize_scalar

from sync_timing import robust_offsets


def trajectory(t, stationary=False):
    t = np.asarray(t)[:, None]
    phase = np.arange(7)[None, :] * .41
    if stationary:
        t = t * 0
    return np.stack(np.broadcast_arrays(.4*np.sin(t+phase),
        .3*np.sin(1.7*t+phase)+.06*t*t, 3+.1*np.cos(.7*t+phase)), axis=-1)


def project(xyz, center_x):
    local = xyz - np.array([center_x, 0, 0])
    return 700 * local[..., :2] / local[..., 2:] + np.array([480, 270])


def estimate(source1, pixels1, source2, pixels2, window):
    # Cameras are rectified horizontal stereo: epipolar error is vertical error.
    # This estimator interpolates measurements; its ground truth was generated
    # independently by trajectory(physical_time), never by shifting video frames.
    valid = (source1 >= window[0]) & (source1 < window[1])
    t, y = source1[valid], pixels1[valid, :, 1]
    other = PchipInterpolator(source2, pixels2[:, :, 1], axis=0, extrapolate=False)

    def energy(offset):
        residual = y-other(t+offset)
        finite = np.isfinite(residual)
        if finite.sum() < residual.size/2:
            return float('inf')
        return float(np.nanmedian(residual**2))

    grid = np.linspace(-.1, .1, 201)
    values = np.array([energy(o) for o in grid])
    if np.ptp(values) < 1e-12:
        return {'offset_seconds': None, 'reason': 'stationary-unidentifiable'}
    k = int(np.argmin(values))
    if k in (0, len(grid)-1):
        return {'offset_seconds': None, 'reason': 'search-boundary'}
    fit = minimize_scalar(energy, bounds=(grid[k-1], grid[k+1]), method='bounded',
                          options={'xatol': 1e-10})
    return {'offset_seconds': float(fit.x), 'median_epipolar_squared_pixels': float(fit.fun),
            'reason': 'estimated'}


def run():
    source = np.arange(0, 4, .01)
    truth = .013
    cases = {}
    for name in ['fractional', 'stationary', 'occlusion', 'incorrect-correspondence', 'dropped-frames', 'clock-rate-mismatch']:
        second = source.copy()
        if name == 'dropped-frames':
            second = second[np.arange(len(second)) % 7 != 0]
        rate = 1.02 if name == 'clock-rate-mismatch' else 1.0
        p1 = project(trajectory(source, name == 'stationary'), 0)
        physical2 = (second-truth)/rate
        p2 = project(trajectory(physical2, name == 'stationary'), .7)
        if name == 'occlusion':
            p1[(source > 1.1) & (source < 1.4), :3] = np.nan
        if name == 'incorrect-correspondence':
            p2[:, 0] = p2[::-1, 0]
        early = estimate(source, p1, second, p2, (.2, 1.8))
        late = estimate(source, p1, second, p2, (2.1, 3.7))
        cases[name] = {'truth_offset_at_zero_seconds': truth, 'clock_rate': rate,
                       'early': early, 'late': late}
        if early['offset_seconds'] is not None and late['offset_seconds'] is not None:
            cases[name]['window_disagreement_seconds'] = abs(early['offset_seconds']-late['offset_seconds'])
            if rate == 1:
                cases[name]['absolute_errors_seconds'] = [abs(x['offset_seconds']-truth) for x in [early, late]]
    # Constant-velocity motion along horizontal epipolar lines is ambiguous,
    # even though the object moves; vertical image coordinates stay constant.
    moving = np.stack([source, np.zeros_like(source), np.full_like(source, 3)], axis=-1)[:, None]
    moving2 = moving.copy(); moving2[:, 0, 0] -= truth
    cases['epipolar-direction-ambiguity'] = estimate(source, project(moving, 0), source, project(moving2, .7), (.2, 3.7))
    cases['disconnected-graph'] = robust_offsets(['1', '2', '3', '4'], '1',
        [{'i': '1', 'j': '2', 'delta_seconds': -truth},
         {'i': '3', 'j': '4', 'delta_seconds': .02}], huber_seconds=.001)
    return {'schema': 'sync-analytic-fixtures/v1', 'ground_truth': 'independent continuous analytic 3D motion and pinhole projection',
            'sample_rate_hz': 100, 'units': 'seconds', 'seed': None,
            'scope': 'CPU interface/identifiability controls; not VisualSync or Sync-NeRF benchmark results',
            'cases': cases}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    result = run()
    args.output.write_text(json.dumps(result, indent=2, allow_nan=False)+'\n')
