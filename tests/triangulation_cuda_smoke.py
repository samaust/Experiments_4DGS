"""Plan 029: one 15,000-correspondence CUDA validation, no inference/training."""
import argparse
import json
from pathlib import Path
import platform
import subprocess
import time

import numpy as np
import torch

from test_triangulation import fixture, reference
from triangulation import solver_metadata, triangulate_points


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    assert platform.python_version_tuple()[:2] == ('3', '14')
    assert torch.__version__ == '2.13.0+cu130'
    assert torch.cuda.is_available(), 'actual CUDA execution is required'
    assert torch.cuda.device_count() == 1, 'expose exactly one GPU'
    _, P, uv = fixture(15000)
    uv = (uv + np.random.default_rng(292).normal(0, .15, uv.shape)).astype(np.float32)
    uv[:, -1] = np.nan
    uv[1, -2] = uv[0, -2]
    expected, A, b = reference(P, uv[:, :-2])
    torch.cuda.synchronize()
    torch.cuda.reset_peak_memory_stats()
    started = time.perf_counter()
    xyz, valid = triangulate_points(*P, *uv, device='cuda:0', dtype=torch.float32)
    torch.cuda.synchronize()
    elapsed = time.perf_counter()-started
    peak = torch.cuda.max_memory_allocated()
    actual = xyz.cpu().numpy()[:-2]
    assert valid[:-2].all() and not valid[-2:].any()
    assert torch.isnan(xyz[-2:]).all()
    np.testing.assert_allclose(actual, expected, rtol=2e-4, atol=2e-4)
    residual = np.linalg.norm(np.einsum('nij,nj->ni', A, actual)-b, axis=1)
    best = np.linalg.norm(np.einsum('nij,nj->ni', A, expected)-b, axis=1)
    # Residuals carry pixel-equation units; near-zero minima need a scale-aware
    # roundoff bound, unlike the plan's XYZ tolerance for well-conditioned points.
    scale = np.linalg.norm(A, axis=(1, 2))*np.linalg.norm(expected, axis=1) + np.linalg.norm(b, axis=1)
    residual_excess = np.maximum(residual-best, 0)/scale
    assert residual_excess.max() <= 4*np.finfo(np.float32).eps
    report = dict(schema='triangulation-cuda-validation/v1', status='passed',
        python=platform.python_version(), pytorch=torch.__version__, cuda_runtime=torch.version.cuda,
        device=torch.cuda.get_device_name(0), device_count=torch.cuda.device_count(),
        driver=subprocess.check_output(['nvidia-smi', '--query-gpu=driver_version', '--format=csv,noheader'], text=True).strip(),
        geometry_source=solver_metadata(), correspondences=15000, accepted=int(valid.sum()),
        rejected=int((~valid).sum()), max_xyz_difference=float(np.abs(actual-expected).max()),
        max_residual_difference=float(np.abs(residual-best).max()),
        max_scaled_residual_excess=float(residual_excess.max()),
        scaled_residual_limit=float(4*np.finfo(np.float32).eps),
        synchronized_seconds=elapsed, peak_allocated_bytes=peak,
        seed=292, reference='independently assembled NumPy float64 lstsq, quantized float32 inputs',
        timing_scope='single cold helper call including input transfers, screening, solve and synchronization',
        limits=dict(gpus=1, invocation_timeout_seconds=300, inference=0, training=0))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    serialized = json.dumps(report, indent=2)+'\n'
    with args.output.open('x') as stream:
        stream.write(serialized)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
