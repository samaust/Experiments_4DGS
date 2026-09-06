"""Verify native loss/update/relocation and complete checkpoint reload on CUDA."""
import argparse
import json
from pathlib import Path
import socket
from types import SimpleNamespace

import torch

from freetimegs_checkpoint import restore_checkpoint, save_checkpoint
from freetimegs_model import NativeFreeTimeModel
from freetimegs_training import load_training


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--checkout', type=Path, default=Path('.local/FreeTimeGsVanilla'))
    parser.add_argument('--torch-cache', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    checkpoint = args.output.with_suffix('.pt')
    if args.output.exists() or checkpoint.exists():
        parser.error('choose new output paths')
    if not (args.torch_cache / 'hub/checkpoints/alexnet-owt-7be5be79.pth').is_file():
        parser.error('cached AlexNet weights required')
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; no CPU fallback permitted')

    def deny_network(*unused, **kwargs):
        raise RuntimeError('network disabled during training-state verification')

    socket.create_connection = deny_network
    socket.socket.connect = deny_network
    socket.socket.connect_ex = deny_network
    torch.hub.set_dir(str(args.torch_cache / 'hub'))
    from torchmetrics.image.lpip import LearnedPerceptualImagePatchSimilarity
    torch.manual_seed(0)
    cfg, _, _ = load_training(args.checkout)
    cfg.init_scale = .3  # Four-point diagnostic only, not the scene preset.
    cfg.relocation_max_ratio = .5  # Exercise relocation with just four points.
    init_data = dict(positions=torch.tensor([[-.2, -.1, 2.], [.2, -.1, 2.2],
                                            [0., .2, 2.4], [.1, .1, 2.8]]),
        colors=torch.rand((4, 3)), times=torch.full((4, 1), .5),
        durations=torch.full((4, 1), .2), velocities=torch.tensor([[.3, 0., 0.]] * 4))
    lpips = LearnedPerceptualImagePatchSimilarity(net_type='alex', normalize=True).cuda()

    def construct():
        value = NativeFreeTimeModel(args.checkout, cfg, init_data, scene_scale=1., device='cuda')
        value.enable_training(args.checkout, scene_scale=1., device='cuda', lpips=lpips)
        return value

    model = construct()
    camera = SimpleNamespace(camtoworlds=torch.eye(4, device='cuda')[None],
        Ks=torch.tensor([[[50., 0., 32.], [0., 50., 32.], [0., 0., 1.]]], device='cuda'),
        width=64, height=64, t=.4, pixels=torch.rand((1, 64, 64, 3), device='cuda'))
    first = model.training_step(0, camera, model.schedulers)
    with torch.no_grad():
        model.splats['opacities'][0] = torch.logit(torch.tensor(.001, device='cuda'))
    model.training_step(100, camera, model.schedulers)
    if torch.sigmoid(model.splats['opacities'][0]).item() < .01:
        raise RuntimeError('native relocation did not revive the dead Gaussian')
    provenance = {'scope': 'synthetic native training-state test'}
    save_checkpoint(checkpoint, model, iteration=101, loop_state={'cursor': 2}, provenance=provenance)
    expected = model.training_step(101, camera, model.schedulers)
    restored = construct()
    iteration, loop = restore_checkpoint(checkpoint, restored, provenance=provenance)
    actual = restored.training_step(iteration, camera, restored.schedulers)
    differences = {}
    for name in model.splats:
        differences[name] = (model.splats[name] - restored.splats[name]).abs().max().item()
        torch.testing.assert_close(model.splats[name], restored.splats[name], rtol=1e-5, atol=1e-6)
    torch.testing.assert_close(expected['loss'], actual['loss'], rtol=1e-5, atol=1e-6)
    torch.testing.assert_close(model.grad_accum, restored.grad_accum, rtol=1e-5, atol=1e-6)
    if model.grad_count != restored.grad_count or loop != {'cursor': 2}:
        raise RuntimeError('checkpoint loop/relocation state mismatch')
    torch.cuda.synchronize()
    report = dict(status='passed', scope='synthetic CUDA training-state check, no scene training',
        source_digests=model.source_digests, device=torch.cuda.get_device_name(),
        first_loss=first['loss'].item(), first_lpips=first['lpips'].item(),
        native_duration_target=cfg.init_duration, relocation_exercised=True,
        next_loss_difference=abs(expected['loss'].item()-actual['loss'].item()),
        next_parameter_max_abs_differences=differences,
        diagnostic_overrides=dict(init_scale=.3, relocation_max_ratio=.5),
        fresh_process_reload=False)
    args.output.write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
