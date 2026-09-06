"""Load released EDGS geometry helpers without importing its Gaussian trainer.

The external checkout retains its non-commercial license. This loader does not
redistribute the extracted source; source and license hashes identify execution.
"""
import ast
import hashlib
from pathlib import Path
import socket
import subprocess
import sys

import torch


ROMA_PIN = '370117431ffc5dc000fb46f6e581b74bdb2c3ff8'
ROMA_WEIGHTS = {
    'roma_indoor.pth': '4d3dca889ae1ef245123dc62aab914475c7bbf41f2c8002606450fb6cf2d91e6',
    'dinov2_vitl14_pretrain.pth': 'd5383ea8f4877b2472eb973e0fd72d557c7da5d3611bd527ceeb1d7162cbf428',
}


def load_roma(checkout, weights):
    """Load the pinned released matcher offline on CUDA, with no fallback."""
    checkout, weights = Path(checkout), Path(weights)
    pin = subprocess.check_output(['git', '-C', str(checkout), 'rev-parse', 'HEAD'],
                                  text=True).strip()
    if pin != ROMA_PIN:
        raise ValueError('expected EDGS-pinned RoMa revision')
    if subprocess.check_output(['git', '-C', str(checkout), 'status', '--porcelain',
                                '--untracked-files=no'], text=True):
        raise ValueError('modified tracked RoMa source')
    for name, expected in ROMA_WEIGHTS.items():
        with (weights / name).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                raise ValueError(f'checkpoint hash mismatch: {name}')

    def deny_network(*unused, **kwargs):
        raise RuntimeError('network disabled during matcher execution')

    socket.create_connection = deny_network
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    if 'romatch' in sys.modules:
        raise RuntimeError('load pinned RoMa in a fresh process')
    sys.path.insert(0, str(checkout.absolute()))
    from romatch import roma_indoor
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; no CPU fallback permitted')
    torch.set_float32_matmul_precision('highest')
    model = roma_indoor(device='cuda',
        weights=torch.load(weights / 'roma_indoor.pth', map_location='cpu', weights_only=True),
        dinov2_weights=torch.load(weights / 'dinov2_vitl14_pretrain.pth',
                                  map_location='cpu', weights_only=True))
    model.upsample_preds = False
    model.symmetric = False
    return model.eval()


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
