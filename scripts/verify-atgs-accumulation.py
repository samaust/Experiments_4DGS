#!/usr/bin/env python3
"""Synthetic GPU partial-accumulation restore using native ATGS update helpers."""
import argparse
import hashlib
import io
import json
import os
from pathlib import Path
import runpy
import sys
import subprocess
from types import SimpleNamespace


def write_report(path, report):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x') as output:
        json.dump(report, output, indent=2, allow_nan=False)
        output.write('\n')
    print(json.dumps(report, indent=2))


def compare_continuation(reference, resumed):
    """Require identical discrete continuation, report numerical loss drift."""
    for field in ('key', 'target'):
        expected = [r[field] for r in reference['records']]
        actual = [r[field] for r in resumed['records']]
        # JSON round trips turn key tuples into lists.
        if json.dumps(expected) != json.dumps(actual):
            raise ValueError(f'resumed {field} sequence mismatch')
    for field in ('iteration', 'micro_steps', 'encoder_visits', 'update_count', 'last_update_iteration'):
        if reference['loop'][field] != resumed['loop'][field]:
            raise ValueError(f'resumed loop {field} mismatch')
    if reference['warmup'] != resumed['warmup']:
        raise ValueError('resumed warmup mismatch')
    return [abs(a['loss'] - b['loss']) for a, b in zip(reference['records'], resumed['records'])]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path('.local/ATGS'))
    parser.add_argument('--checkpoint', type=Path)
    parser.add_argument('--evidence', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--bundle', type=Path, help='save and resume a new on-disk bundle instead of an in-memory supplement')
    parser.add_argument('--resume-bundle', type=Path, help='resume an existing bundle in this fresh process with network disabled')
    parser.add_argument('--reference', type=Path, help='successful bundle probe or fresh-resume report')
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    if args.bundle is not None and (args.bundle.exists() or args.bundle.is_symlink()):
        raise FileExistsError(args.bundle)
    if args.resume_bundle and (args.bundle or not args.reference):
        parser.error('--resume-bundle requires --reference and excludes --bundle')
    if args.reference and not args.resume_bundle:
        parser.error('--reference requires --resume-bundle')
    if not args.resume_bundle and (not args.checkpoint or not args.evidence):
        parser.error('--checkpoint and --evidence required unless resuming a bundle')
    if args.resume_bundle and (args.checkpoint or args.evidence):
        parser.error('--resume-bundle does not use --checkpoint or --evidence')
    offline = None
    if args.resume_bundle:
        guard = runpy.run_path(str(Path(__file__).with_name('offline-python.py')))
        offline = guard['restrict_network']()
        print(json.dumps(offline), flush=True)
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; accumulation validation stopped, no CPU fallback')
    from atgs_checkpoint import inspect_native_checkpoint, restore_auxiliary_state, tensor_difference
    from atgs_loop_state import capture_loop_state, restore_loop_state, parameters
    from atgs_sampler import ManifestBalancedSampler
    from atgs_update import load_update_helpers
    inventory = None
    if not args.resume_bundle:
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
    resolved, (dataset, hidden, opt, pipe), cfg = load_config(args.checkout)
    helpers, helper_hash = load_update_helpers(args.checkout)
    auxiliary = None if args.resume_bundle else torch.load(args.checkpoint / 'auxiliary.pth', map_location='cpu', weights_only=True)

    def load_model(directory=args.checkpoint, auxiliary_state=auxiliary):
        model = GaussianModel(hidden, opt, dataset.feat_dim, 10, dataset.voxel_size,
                              dataset.update_depth, dataset.update_init_factor, dataset.update_hierachy_factor,
                              dataset.use_feat_bank, dataset.appearance_dim, dataset.ratio,
                              dataset.add_opacity_dist, dataset.add_cov_dist, dataset.add_color_dist)
        cloud = SimpleNamespace(point_times_list=auxiliary_state['tensors']['point_times_list']['value'].numpy())
        model.load_ply_sparse_gaussian(str(directory / 'point_cloud.ply'), cloud, [0, 60])
        model.load_model(str(directory))
        restore_auxiliary_state(model, auxiliary_state, device='cuda')
        model.training_setup(opt, 1, str(directory))
        model.mlp_color.train()
        return model

    keys = [('synthetic', i) for i in range(3)]
    scene = SimpleNamespace(sha256='synthetic-three-encoder-probe', training_keys=lambda: keys,
                            cameras={'synthetic': {'split': 'train'}},
                            frames={key: {'normalized_time': t} for key, t in zip(keys, (.1, .5, .9))})
    calibration = dict(width=64, height=64, K=[[60, 0, 29], [0, 60, 30], [0, 0, 1]],
                       world_to_camera_R=[[1, 0, 0], [0, 1, 0], [0, 0, 1]], world_to_camera_T=[0, 0, 0])
    background = torch.zeros(3, device='cuda')

    def bundle_provenance():
        def digest(value):
            return hashlib.sha256(json.dumps(value, sort_keys=True, allow_nan=False).encode()).hexdigest()
        revision = subprocess.check_output(['git', '-C', str(args.checkout), 'rev-parse', 'HEAD'], text=True).strip()
        fixture = dict(keys=keys, times=[scene.frames[key]['normalized_time'] for key in keys],
                       calibration=calibration)
        return dict(manifest_sha256=digest(fixture), source_revision=revision,
                    config_sha256=digest(vars(resolved)), helper_ast_sha256=helper_hash)

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

    if args.resume_bundle:
        from atgs_bundle import load_bundle_supplements
        saved_auxiliary, saved_loop, record = load_bundle_supplements(
            args.resume_bundle, expected_provenance=bundle_provenance())
        reference = json.loads(args.reference.read_text())
        if reference.get('status') != 'passed' or reference.get('bundle') != record:
            raise ValueError('reference bundle mismatch')
        restored = load_model(args.resume_bundle, saved_auxiliary)
        sampler = ManifestBalancedSampler(scene, cfg.levels, seed=999)
        loop = restore_loop_state(restored, sampler, saved_loop)
        resumed = finish(restored, sampler, loop)
        loss_differences = compare_continuation(reference['resumed'], resumed)
        hashes = {}
        for name, parameter in parameters(restored).items():
            if not torch.isfinite(parameter).all():
                raise ValueError('nonfinite resumed parameter')
            hashes[name] = hashlib.sha256(parameter.detach().cpu().contiguous().numpy().tobytes()).hexdigest()
        exact = None if 'parameter_sha256' not in reference else reference['parameter_sha256'] == hashes
        report = dict(status='passed', scope='fresh-process offline synthetic accumulation resume',
                      process_id=os.getpid(), offline=offline, bundle=record, resumed=resumed,
                      reference_loss_abs_differences=loss_differences, parameter_sha256=hashes,
                      reference_parameters_exact=exact, device=torch.cuda.get_device_name())
        write_report(args.output, report)
        return

    original = load_model()
    sampler = ManifestBalancedSampler(scene, cfg.levels)
    # This fixture starts from a checkpoint with three completed synthetic updates.
    loop = dict(iteration=3, micro_steps=0, encoder_visits={}, update_count=3,
                last_update_iteration=3, ema_loss=0.)
    microstep(original, sampler, loop)
    bundle_record = None
    if args.bundle is not None:
        from atgs_bundle import save_bundle, load_bundle_supplements
        provenance = bundle_provenance()
        bundle_record = save_bundle(args.bundle, original, sampler, loop, provenance)
    else:
        buffer = io.BytesIO()
        torch.save(capture_loop_state(original, sampler, loop), buffer)
    uninterrupted = finish(original, sampler, loop)
    if args.bundle is not None:
        saved_auxiliary, saved_loop, verified = load_bundle_supplements(
            args.bundle, expected_provenance=provenance)
        if verified != bundle_record:
            raise ValueError('saved bundle record changed')
        restored = load_model(args.bundle, saved_auxiliary)
    else:
        restored = load_model()
        buffer.seek(0)
        saved_loop = torch.load(buffer, weights_only=True)
    restored_sampler = ManifestBalancedSampler(scene, cfg.levels, seed=999)
    restored_loop = restore_loop_state(restored, restored_sampler, saved_loop)
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
    report['bundle'] = bundle_record
    report['resume_storage'] = 'on-disk bundle' if args.bundle is not None else 'in-memory supplement'
    write_report(args.output, report)


if __name__ == '__main__':
    main()
