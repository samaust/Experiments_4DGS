"""Check the EDGS-pinned indoor RoMa on CUDA using explicit local weights."""
import argparse
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import time


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, required=True)
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('choose a new output file')
    pin = subprocess.check_output(
        ['git', '-C', str(args.checkout), 'rev-parse', 'HEAD'], text=True).strip()
    if pin != '370117431ffc5dc000fb46f6e581b74bdb2c3ff8':
        parser.error('expected EDGS-pinned RoMa revision')
    if subprocess.check_output(['git', '-C', str(args.checkout), 'status',
                                '--porcelain', '--untracked-files=no'], text=True):
        parser.error('modified tracked RoMa source')
    hashes = {
        'roma_indoor.pth': '4d3dca889ae1ef245123dc62aab914475c7bbf41f2c8002606450fb6cf2d91e6',
        'dinov2_vitl14_pretrain.pth': 'd5383ea8f4877b2472eb973e0fd72d557c7da5d3611bd527ceeb1d7162cbf428',
    }
    for name, expected in hashes.items():
        if sha256(args.weights / name) != expected:
            parser.error(f'checkpoint hash mismatch: {name}')

    def deny_network(*unused, **kwargs):
        raise RuntimeError('network disabled during matcher verification')

    socket.create_connection = deny_network
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    import numpy as np
    import torch
    from PIL import Image
    sys.path.insert(0, str(args.checkout.absolute()))
    from romatch import roma_indoor
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; no CPU fallback permitted')
    torch.manual_seed(0)
    torch.cuda.manual_seed_all(0)
    torch.set_float32_matmul_precision('highest')
    torch.cuda.reset_peak_memory_stats()
    start = time.monotonic()
    model = roma_indoor(
        device='cuda',
        weights=torch.load(args.weights / 'roma_indoor.pth', map_location='cpu', weights_only=True),
        dinov2_weights=torch.load(args.weights / 'dinov2_vitl14_pretrain.pth',
                                  map_location='cpu', weights_only=True))
    # Explicit EDGS fast-initializer settings; retain native coarse resolution.
    model.upsample_preds = False
    model.symmetric = False
    model.eval()
    array = np.random.default_rng(0).integers(0, 256, size=(560, 560, 3), dtype=np.uint8)
    sample = Image.fromarray(array)
    with torch.inference_mode():
        warp, certainty = model.match(sample, sample, device='cuda')
    torch.cuda.synchronize()
    if warp.shape != (560, 560, 4) or certainty.shape != (560, 560):
        raise RuntimeError(f'unexpected output shapes: {warp.shape}, {certainty.shape}')
    if not torch.isfinite(warp).all() or not torch.isfinite(certainty).all():
        raise RuntimeError('non-finite matcher output')
    result = dict(status='passed', source_pin=pin, checkpoint_sha256=hashes,
                  device=torch.cuda.get_device_name(0), torch=torch.__version__,
                  wall_seconds=time.monotonic() - start,
                  peak_allocated_bytes=torch.cuda.max_memory_allocated(),
                  warp_shape=list(warp.shape), certainty_shape=list(certainty.shape),
                  mean_certainty=certainty.mean().item(),
                  mean_identity_error_ndc=(warp[..., :2] - warp[..., 2:]).abs().mean().item(),
                  input='seed-0 synthetic random RGB, identical pair',
                  limitations='Kernel smoke check only; no scene geometry or quality validation')
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2)
        stream.write('\n')
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
