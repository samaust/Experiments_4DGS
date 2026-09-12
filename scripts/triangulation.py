"""Independent inhomogeneous two-view least squares; derivation: docs/triangulation.md."""
import hashlib
import math
from pathlib import Path

import torch


def solver_metadata(*, dtype=torch.float32):
    """Provenance for newly generated geometry (counts are recorded by callers)."""
    return dict(implementation_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
                solver='local-inhomogeneous-lstsq/v1', dtype=str(dtype), driver='gels',
                rank_rtol=4 * torch.finfo(dtype).eps)


@torch.no_grad()
def triangulate_points(P1, P2, points1, points2, *, device, dtype=torch.float32,
                       rank_rtol=None) -> tuple[torch.Tensor, torch.Tensor]:
    """Solve P=K[R|t] with [N,2] pixels and shared or [N,3,4] projections.

    Inputs are detached and never mutated. Output XYZ and numerical validity keep
    correspondence order on the requested device; rejected XYZ are NaN. No pixel
    shifts or geometric acceptance are applied. Execution failures propagate.
    """
    if dtype not in (torch.float32, torch.float64):
        raise ValueError('dtype must be torch.float32 or torch.float64')
    threshold = 4 * torch.finfo(dtype).eps if rank_rtol is None else float(rank_rtol)
    if not math.isfinite(threshold) or not 0 < threshold < 1:
        raise ValueError('rank_rtol must be finite and strictly between zero and one')
    target = torch.device(device)
    if target.type == 'cuda' and not torch.cuda.is_available():
        raise RuntimeError(f'requested device {target} is unavailable')
    if target.type == 'meta':
        raise ValueError('meta device cannot execute triangulation')

    def convert(value):
        if isinstance(value, torch.Tensor):
            value = value.detach()
        return torch.as_tensor(value, device=target, dtype=dtype)

    points1, points2 = convert(points1), convert(points2)
    if points1.ndim != 2 or points1.shape[1] != 2 or points2.shape != points1.shape:
        raise ValueError('points1 and points2 must have matching [N,2] shapes')
    n = len(points1)
    cameras = []
    for name, value in (('P1', P1), ('P2', P2)):
        camera = convert(value)
        if camera.shape not in ((3, 4), (n, 3, 4)):
            raise ValueError(f'{name} must have shape [3,4] or [N,3,4]')
        if not torch.isfinite(camera).all():
            raise ValueError(f'{name} contains non-finite camera coefficients')
        cameras.append(camera.expand(n, 3, 4))
    xyz = torch.full((n, 3), float('nan'), device=target, dtype=dtype)
    valid = torch.zeros(n, device=target, dtype=torch.bool)
    indices = torch.where(torch.isfinite(points1).all(1) & torch.isfinite(points2).all(1))[0]
    if not len(indices):
        return xyz, valid
    rows = []
    for camera, pixels in zip(cameras, (points1, points2)):
        camera, pixels = camera[indices], pixels[indices]
        rows.append(pixels[:, :, None] * camera[:, None, 2, :] - camera[:, :2, :])
    equations = torch.cat(rows, dim=1)
    finite = torch.isfinite(equations).all(dim=(1, 2))
    equations, indices = equations[finite], indices[finite]
    if not len(indices):
        return xyz, valid
    A, b = equations[:, :, :3], -equations[:, :, 3:4]
    singular = torch.linalg.svdvals(A)
    eligible = torch.isfinite(singular).all(1) & (singular[:, -1] > threshold * singular[:, 0])
    indices = indices[eligible]
    if len(indices):
        solution = torch.linalg.lstsq(A[eligible], b[eligible], driver='gels').solution[:, :, 0]
        finite = torch.isfinite(solution).all(1)
        xyz[indices[finite]] = solution[finite]
        valid[indices[finite]] = True
    return xyz, valid
