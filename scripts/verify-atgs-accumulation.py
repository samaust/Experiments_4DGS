#!/usr/bin/env python3
"""Synthetic GPU partial-accumulation restore using native ATGS update helpers."""
import argparse
import io
import json
from pathlib import Path
import sys
from types import SimpleNamespace


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path('.local/ATGS'))
    parser.add_argument('--checkpoint', type=Path, required=True)
    parser.add_argument('--evidence', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; accumulation validation stopped, no CPU fallback')
    from atgs_checkpoint import inspect_native_checkpoint, restore_auxiliary_state, tensor_difference
    from atgs_loop_state import capture_loop_state, restore_loop_state, parameters
    from atgs_sampler import ManifestBalancedSampler
    from atgs_update import load_update_helpers
    inventory = inspect_native_checkpoint(args.checkpoint, require_optimizers=True, require_auxiliary=True)
    evidence = json.loads(args.evidence.read_text())
    if evidence.get('status') != 'passed' or inventory != evidence['native_reload']['files']:
        raise ValueError('checkpoint evidence mismatch')
    if evidence.get('synthetic_optimizer_updates') != 3:
        raise ValueError('probe requires a three-update synthetic checkpoint')
    sys.path.insert(0, str(args.checkout.resolve()))
    from atgs_config import load_config
    from atgs_scene import make_camera
    from scene.gaussian_model import GaussianModel
    from gaussian_renderer import prefilter_voxel, render
    _, (dataset, hidden, opt, pipe), cfg = load_config(args.checkout)
    helpers, helper_hash = load_update_helpers(args.checkout)
    auxiliary = torch.load(args.checkpoint / 'auxiliary.pth', map_location='cpu', weights_only=True)

    def load_model():
        model = GaussianModel(hidden, opt, dataset.feat_dim, 10, dataset.voxel_size,
                              dataset.update_depth, dataset.update_init_factor, dataset.update_hierachy_factor,
                              dataset.use_feat_bank, dataset.appearance_dim, dataset.ratio,
                              dataset.add_opacity_dist, dataset.add_cov_dist, dataset.add_color_dist)
        cloud = SimpleNamespace(point_times_list=auxiliary['tensors']['point_times_list']['value'].numpy())
        model.load_ply_sparse_gaussian(str(args.checkpoint / 'point_cloud.ply'), cloud, [0, 60])
        model.load_model(str(args.checkpoint))
        restore_auxiliary_state(model, auxiliary, device='cuda')
        model.training_setup(opt, 1, str(args.checkpoint))
        model.mlp_color.train()
        return model

    keys = [('synthetic', i) for i in range(3)]
    scene = SimpleNamespace(sha256='synthetic-three-encoder-probe', training_keys=lambda: keys,
                            cameras={'synthetic': {'split': 'train'}},
                            frames={key: {'normalized_time': t} for key, t in zip(keys, (.1, .5, .9))})
    calibration = dict(width=64, height=64, K=[[60, 0, 29], [0, 60, 30], [0, 0, 1]],
                       world_to_camera_R=[[1, 0, 0], [0, 1, 0], [0, 0, 1]], world_to_camera_T=[0, 0, 0])
    background = torch.zeros(3, device='cuda')

    def microstep(model, sampler, loop):
        key = next(sampler)
        timestamp = scene.frames[key]['normalized_time']
        camera = make_camera(calibration, timestamp, device='cuda')
        loop['iteration'] += 1
        model.update_learning_rate(loop['iteration'], opt, timestamp)
        visible = prefilter_voxel(camera, model, pipe, background)
        image = render(camera, model, pipe, background, iteration=loop['iteration'], visible_mask=visible)['render']
        target = .25 + .01 * torch.rand((), device='cuda')
        loss = (image - target).square().mean()
        if not torch.isfinite(loss):
            raise ValueError('nonfinite accumulation loss')
        loss.backward()
        if any(p.grad is not None and not torch.isfinite(p.grad).all() for p in parameters(model).values()):
            raise ValueError('nonfinite accumulation gradient')
        encoder = model.dynamic_module.routing_encoder_id(timestamp)
        loop['encoder_visits'][encoder] = loop['encoder_visits'].get(encoder, 0) + 1
        loop['micro_steps'] += 1
        loop['ema_loss'] = .4 * loss.item() + .6 * loop['ema_loss']
        return dict(key=key, target=target.item(), loss=loss.item())

    def finish(model, sampler, loop):
        records = []
        while len(loop['encoder_visits']) < cfg.levels:
            records.append(microstep(model, sampler, loop))
        counter = dict(count=loop['update_count'], iteration=loop['iteration'])
        norms, warmup = helpers['step_accumulated_gradients'](
            model, opt, loop['micro_steps'], loop['encoder_visits'], counter)
        loop.update(micro_steps=0, encoder_visits={}, update_count=counter['count'],
                    last_update_iteration=loop['iteration'])
        return dict(records=records, warmup=warmup, gradient_norms=norms, loop=loop)

    original = load_model()
    sampler = ManifestBalancedSampler(scene, cfg.levels)
    # This fixture starts from a checkpoint with three completed synthetic updates.
    loop = dict(iteration=3, micro_steps=0, encoder_visits={}, update_count=3,
                last_update_iteration=3, ema_loss=0.)
    microstep(original, sampler, loop)
    buffer = io.BytesIO()
    torch.save(capture_loop_state(original, sampler, loop), buffer)
    uninterrupted = finish(original, sampler, loop)
    restored = load_model()
    restored_sampler = ManifestBalancedSampler(scene, cfg.levels, seed=999)
    buffer.seek(0)
    restored_loop = restore_loop_state(restored, restored_sampler, torch.load(buffer, weights_only=True))
    resumed = finish(restored, restored_sampler, restored_loop)
    assert [r['key'] for r in uninterrupted['records']] == [r['key'] for r in resumed['records']]
    assert [r['target'] for r in uninterrupted['records']] == [r['target'] for r in resumed['records']]
    assert uninterrupted['warmup'] == resumed['warmup']
    a, b = parameters(original), parameters(restored)
    differences = {name: tensor_difference(a[name], b[name]) for name in a}
    report = dict(status='passed', scope='synthetic partial accumulation; finite differences reported',
                  helper_ast_sha256=helper_hash, uninterrupted=uninterrupted, resumed=resumed,
                  parameter_max_abs_differences=differences,
                  parameters_exact=all(v == 0 for v in differences.values()),
                  device=torch.cuda.get_device_name(), checkpoint_files=inventory)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open('x') as output:
        json.dump(report, output, indent=2)
        output.write('\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
