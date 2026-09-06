#!/usr/bin/env python3
"""Render every SelfCap held-out sample and shared sweep from a training checkpoint."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkout', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--checkpoint', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--benchmark', action='store_true')
    a = p.parse_args()
    if a.output.exists():
        p.error('choose a new output directory')
    started = time.monotonic()
    import torch
    from torchvision.utils import save_image
    from stg_scene import SelfCapScene
    from stg_checkpoint import restore_checkpoint
    root = a.checkout.resolve()
    sys.path[:0] = [str(root), str(root/'thirdparty/gaussian_splatting')]
    from helper_train import getrenderpip, trbfunction
    from thirdparty.gaussian_splatting.scene.ourslite import GaussianModel as Lite
    from thirdparty.gaussian_splatting.scene.oursfull import GaussianModel as Full
    scene = SelfCapScene(a.manifest)
    state = torch.load(a.checkpoint, map_location='cpu', weights_only=True)
    provenance = state['provenance']
    if provenance['files'].get(str(a.manifest.resolve())) != scene.sha256:
        p.error('checkpoint was trained against a different manifest')
    # Check every pinned component, including the adapted training implementation.
    for filename, expected in provenance['files'].items():
        with Path(filename).open('rb') as stream:
            if hashlib.file_digest(stream, 'sha256').hexdigest() != expected:
                p.error('checkpoint source/input provenance changed: '+filename)
    full = state['variant'] == 'full'
    model = Full(3, 'sandwich') if full else Lite(3)
    iteration, _, _ = restore_checkpoint(a.checkpoint, model, variant=state['variant'],
                                         provenance=provenance, device='cuda')
    if full:
        model.rgbdecoder.eval()
    render, settings, rasterizer = getrenderpip('train_ours_full' if full else 'train_ours_lite')
    background = torch.zeros(9 if full else 3, device='cuda')
    a.output.mkdir(parents=True)
    records = []
    with torch.no_grad():
        def pixels(view):
            return render(view, model, None, background, basicfunction=trbfunction,
                          GRsetting=settings, GRzer=rasterizer)['render']

        for key in scene.frames:
            if scene.cameras[key[0]]['split'] != 'test':
                continue
            view = scene.camera(key, device='cuda', full=full)
            output = pixels(view)
            if not torch.isfinite(output).all():
                raise RuntimeError('nonfinite rendered pixels')
            destination = a.output/'images'/key[0]/f'{key[1]:06d}.png'
            destination.parent.mkdir(parents=True, exist_ok=True)
            save_image(output.clamp(0, 1), destination)
            records.append(dict(camera=key[0], frame_id=key[1], normalized_time=view.timestamp,
                path=str(destination.relative_to(a.output)),
                sha256=hashlib.sha256(destination.read_bytes()).hexdigest()))
            del output, view
        (a.output/'sweep').mkdir()
        for index in range(20):
            view = scene.sweep_camera(index, device='cuda', full=full)
            output = pixels(view)
            if not torch.isfinite(output).all():
                raise RuntimeError('nonfinite sweep pixels')
            save_image(output.clamp(0, 1), a.output/'sweep'/f'{index:05d}.png')
            del output, view
        benchmark = None
        if a.benchmark:
            camera_id = scene.manifest['sweep']['start_camera']
            view = scene.camera((camera_id, 4150), device='cuda', full=full)
            for _ in range(10):
                pixels(view)
            durations = []
            for _ in range(100):
                torch.cuda.synchronize()
                tick = time.perf_counter()
                pixels(view)
                torch.cuda.synchronize()
                durations.append(time.perf_counter()-tick)
            benchmark = dict(warmups=10, timed_renders=100, seconds=durations,
                fps=100/sum(durations), excludes='camera setup, loading, saving and encoding',
                camera=camera_id, frame_id=4150,
                dimensions=[view.image_width, view.image_height])
    with a.checkpoint.open('rb') as stream:
        checkpoint_sha = hashlib.file_digest(stream, 'sha256').hexdigest()
    report = dict(iteration=iteration, model=state['variant'], manifest_sha256=scene.sha256,
        checkpoint_sha256=checkpoint_sha, checkpoint_bytes=a.checkpoint.stat().st_size,
        renderer='native training rasterizer in no_grad mode',
        incomplete_training=iteration < state['training_args']['iterations'],
        frames=records, sweep=scene.manifest['sweep'], benchmark=benchmark,
        wall_seconds=time.monotonic()-started, gpu=torch.cuda.get_device_name(),
        network_isolation='not enforced by this command')
    (a.output/'render.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(dict(iteration=iteration, held_out_frames=len(records), sweep_poses=20,
                         fps=benchmark['fps'] if benchmark else None), indent=2))


if __name__ == '__main__':
    main()
