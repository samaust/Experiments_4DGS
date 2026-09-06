#!/usr/bin/env python3
"""Fresh-process offline inference from a synthetic ATGS checkpoint."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import runpy
import sys
from types import SimpleNamespace


def verify_inventory(actual, expected):
    if actual != expected:
        raise ValueError('checkpoint inventory differs from recorded evidence')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path('.local/ATGS'))
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--reference', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    from atgs_checkpoint import inspect_native_checkpoint, restore_auxiliary_state
    inventory = inspect_native_checkpoint(args.checkpoint, require_optimizers=True, require_auxiliary=True)
    evidence = json.loads(args.evidence.read_text())
    if evidence.get('status') != 'passed':
        raise ValueError('requires successful checkpoint evidence')
    verify_inventory(inventory, evidence['native_reload']['files'])
    # Install the established network guard before Torch or any CUDA threads.
    guard = runpy.run_path(str(Path(__file__).with_name('offline-python.py')))
    offline = guard['restrict_network']()
    print(json.dumps(offline), flush=True)
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; GPU validation stopped, no CPU fallback')
    sys.path.insert(0, str(args.checkout.resolve()))
    from atgs_config import load_config
    from atgs_scene import make_camera
    from scene.gaussian_model import GaussianModel
    from gaussian_renderer import prefilter_voxel, render
    _, (dataset, hidden, opt, pipe), cfg = load_config(args.checkout)
    state = torch.load(args.checkpoint / 'auxiliary.pth', map_location='cpu', weights_only=True)
    model = GaussianModel(hidden, opt, dataset.feat_dim, 10, dataset.voxel_size,
                          dataset.update_depth, dataset.update_init_factor,
                          dataset.update_hierachy_factor, dataset.use_feat_bank,
                          dataset.appearance_dim, dataset.ratio, dataset.add_opacity_dist,
                          dataset.add_cov_dist, dataset.add_color_dist)
    # Upstream loader asks for a cloud solely to reconstruct the lifetime mask.
    # Obtain it from the checkpoint itself, not the original initialization data.
    cloud = SimpleNamespace(point_times_list=state['tensors']['point_times_list']['value'].numpy())
    model.load_ply_sparse_gaussian(str(args.checkpoint / 'point_cloud.ply'), cloud, [0, 60])
    model.load_model(str(args.checkpoint))
    restore_auxiliary_state(model, state, device='cuda')
    model.mlp_color.eval()
    calibration = dict(width=64, height=64, K=[[60, 0, 29], [0, 60, 30], [0, 0, 1]],
                       world_to_camera_R=[[1, 0, 0], [0, 1, 0], [0, 0, 1]], world_to_camera_T=[0, 0, 0])
    renders = []
    with torch.no_grad():
        for timestamp in (.1, .5, .9):
            camera = make_camera(calibration, timestamp, device='cuda')
            background = torch.zeros(3, device='cuda')
            visible = prefilter_voxel(camera, model, pipe, background)
            image = render(camera, model, pipe, background, iteration=1, visible_mask=visible)['render']
            if image.shape != (3, 64, 64) or not torch.isfinite(image).all():
                raise ValueError('invalid offline image')
            pixels = image.cpu().contiguous().numpy().tobytes()
            renders.append(dict(time=timestamp, shape=list(image.shape), dtype=str(image.dtype),
                                sha256=hashlib.sha256(pixels).hexdigest()))
    sources = {name: hashlib.sha256(Path(sys.modules[name].__file__).read_bytes()).hexdigest()
               for name in ('scene.gaussian_model', 'gaussian_renderer', 'arguments.atgs_cfg',
                            'atgs_config', 'atgs_scene', 'atgs_checkpoint')}
    exact = None
    if args.reference:
        reference = json.loads(args.reference.read_text())
        if (reference.get('status') != 'passed' or reference.get('files') != inventory
                or reference.get('sources') != sources or reference.get('levels') != cfg.levels):
            raise ValueError('reference checkpoint/source/config mismatch')
        exact = reference['renders'] == renders
        if not exact:
            raise ValueError('fresh-process render hashes differ')
    report = dict(status='passed', scope='synthetic offline inference only; no optimizer or sampler resume',
                  process_id=os.getpid(), offline=offline, files=inventory, sources=sources,
                  levels=cfg.levels, renders=renders, reference_exact=exact,
                  device=torch.cuda.get_device_name(), torch_version=torch.__version__)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
