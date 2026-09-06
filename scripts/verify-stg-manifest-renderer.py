#!/usr/bin/env python3
"""Synthetic native rasterizer forward/backward through full-size manifest cameras.

No image-fitting loss or experiment optimizer steps: this is compatibility
validation outside the training budget, not a trained-scene result.
"""
import argparse
import json
from pathlib import Path
import sys

import numpy as np
import torch
from stg_scene import SelfCapScene


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--checkout', type=Path, required=True)
    p.add_argument('--manifest', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        p.error('choose a new output directory')
    root = args.checkout.resolve()
    sys.path[:0] = [str(root), str(root/'thirdparty/gaussian_splatting')]
    from helper_train import getrenderpip, trbfunction
    from thirdparty.gaussian_splatting.scene.ourslite import GaussianModel as Lite
    from thirdparty.gaussian_splatting.scene.oursfull import GaussianModel as Full
    from utils.graphics_utils import BasicPointCloud
    from torchvision.utils import save_image
    scene = SelfCapScene(args.manifest)
    assert len(scene.training_keys()) == 1380
    assert len(scene.training_keys(4150)) == 23
    assert not any(k[0] == '0015' for k in scene.training_keys())
    args.output.mkdir(parents=True)
    reports = {}
    for variant, cls in [('lite', Lite), ('full', Full)]:
        torch.manual_seed(0)
        rng = np.random.default_rng(0)
        key = ('0000', 4150)
        c = scene.cameras[key[0]]
        camera = scene.camera(key, device='cuda', full=variant == 'full')
        local = rng.uniform([-.4, -.3, 2], [.4, .3, 2.5], (64, 3))
        world = (local-np.array(c['world_to_camera_T']))@np.array(c['world_to_camera_R'])
        cloud = BasicPointCloud(points=world.astype(np.float32),
            colors=rng.uniform(.2, .8, (64, 3)).astype(np.float32),
            normals=np.zeros((64, 3)), times=np.full((64, 1), .3, dtype=np.float32))
        model = cls(3, 'sandwich') if variant == 'full' else cls(3)
        model.create_from_pcd(cloud, 1.)
        if variant == 'full':
            model.rgbdecoder.cuda()
        render, settings, rasterizer = getrenderpip('train_ours_'+variant)
        result = render(camera, model, None,
            torch.zeros(9 if variant == 'full' else 3, device='cuda'),
            basicfunction=trbfunction, GRsetting=settings, GRzer=rasterizer)
        pixels = result['render']
        assert pixels.shape == (3, c['height'], c['width'])
        assert torch.isfinite(pixels).all() and pixels.std() > 0
        pixels.square().mean().backward()
        gradients = {name: bool(getattr(model, name).grad is not None and
                     torch.isfinite(getattr(model, name).grad).all())
                     for name in ['_xyz', '_features_dc', '_motion', '_omega',
                                  '_trbf_center', '_trbf_scale', '_rotation', '_scaling', '_opacity']}
        if variant == 'full':
            gradients['_features_t'] = bool(model._features_t.grad is not None and
                                            torch.isfinite(model._features_t.grad).all())
            gradients['decoder'] = all(v.grad is not None and torch.isfinite(v.grad).all()
                                       for v in model.rgbdecoder.parameters())
            gradients['decoder'] = bool(gradients['decoder'])
        assert all(gradients.values()), gradients
        torch.cuda.synchronize()
        save_image(pixels.detach().clamp(0, 1), args.output/(variant+'.png'))
        reports[variant] = dict(dimensions=[c['width'], c['height']],
            finite_gradients=gradients, timestamp=camera.timestamp,
            visible_points=int(result['visibility_filter'].sum()))
        del pixels, result, model, camera
        torch.cuda.empty_cache()
    report = dict(scope='synthetic native rasterizer, not scene training',
                  gpu=torch.cuda.get_device_name(), manifest_sha256=scene.sha256, results=reports)
    (args.output/'result.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
