"""Load released EDGS geometry helpers without importing its Gaussian trainer.

The external checkout retains its non-commercial license. This loader does not
redistribute the extracted source; source and license hashes identify execution.
"""
import ast
import hashlib
from pathlib import Path

import torch


def load_geometry(checkout):
    checkout = Path(checkout)
    source = checkout / 'source/corr_init.py'
    license_path = checkout / 'LICENSE.txt'
    names = {'prepare_tensor', 'triangulate_points', 'pairwise_distances',
             'k_closest_vectors'}
    tree = ast.parse(source.read_text())
    selected = [node for node in tree.body
                if isinstance(node, ast.FunctionDef) and node.name in names]
    if len(selected) != len(names) or {node.name for node in selected} != names:
        raise ValueError('required EDGS geometry helpers missing or duplicated')
    module = ast.Module(body=selected, type_ignores=[])
    namespace = {'torch': torch}
    evidence = {
        'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
        'license_sha256': hashlib.sha256(license_path.read_bytes()).hexdigest(),
        'geometry_ast_sha256': hashlib.sha256(ast.dump(module).encode()).hexdigest(),
    }
    exec(compile(module, str(source), 'exec'), namespace)
    return {name: namespace[name] for name in names}, evidence


def calibrated_projection(intrinsics, world_to_camera):
    """Pack pixel-space K[R|t] for EDGS's row-vector triangulation helper.

    Upstream solves using column 2 but computes errors using column 3. Both
    columns must represent camera depth for a calibrated pinhole projection.
    This is not a graphics near/far clip-space matrix. Pixel coordinates and
    error thresholds must use the same processed-image calibration convention.
    """
    intrinsics = torch.as_tensor(intrinsics)
    world_to_camera = torch.as_tensor(world_to_camera, device=intrinsics.device,
                                      dtype=intrinsics.dtype)
    if intrinsics.shape != (3, 3) or world_to_camera.shape != (4, 4):
        raise ValueError('expected 3x3 intrinsics and 4x4 world-to-camera matrix')
    if not intrinsics.is_floating_point():
        raise ValueError('floating-point calibration required')
    if not torch.isfinite(intrinsics).all() or not torch.isfinite(world_to_camera).all():
        raise ValueError('non-finite camera calibration')
    if not torch.allclose(intrinsics[2], intrinsics.new_tensor([0., 0., 1.])):
        raise ValueError('expected pinhole intrinsic bottom row')
    if not torch.allclose(world_to_camera[3], intrinsics.new_tensor([0., 0., 0., 1.])):
        raise ValueError('expected homogeneous world-to-camera transform')
    projection = intrinsics @ world_to_camera[:3]
    return torch.cat((projection.T, projection[2, :, None]), dim=1)
