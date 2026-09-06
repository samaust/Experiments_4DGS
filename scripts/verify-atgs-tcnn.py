#!/usr/bin/env python3
"""Validate an ATGS-shaped tiny-cuda-nn hash MLP on CUDA, including reload."""
import argparse
import copy
import json
from pathlib import Path
import time


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    if a.output.exists():
        p.error('refusing to overwrite output')
    import torch
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; GPU validation stopped, no CPU fallback')
    import tinycudann as tcnn
    torch.manual_seed(0)
    config = dict(n_input_dims=4, n_output_dims=32,
        encoding_config=dict(otype='HashGrid', n_levels=16, n_features_per_level=8,
            log2_hashmap_size=19, base_resolution=16, per_level_scale=2.0),
        network_config=dict(otype='FullyFusedMLP', activation='ReLU',
            output_activation='ReLU', n_neurons=128, n_hidden_layers=1))
    start = time.monotonic()
    model = tcnn.NetworkWithInputEncoding(**config)
    optimizer = torch.optim.Adam(model.parameters(), lr=.0002)
    x = torch.rand((256, 4), device='cuda')
    target = torch.rand((256, 32), device='cuda')

    def step(net, opt):
        opt.zero_grad(set_to_none=True)
        output = net(x)
        loss = (output.float()-target).square().mean()
        assert torch.isfinite(output).all() and torch.isfinite(loss)
        loss.backward()
        assert all(p.grad is not None and torch.isfinite(p.grad).all() for p in net.parameters())
        opt.step()
        opt.zero_grad(set_to_none=True)
        return float(loss.detach())

    first_loss = step(model, optimizer)
    weights = copy.deepcopy(model.state_dict())
    opt_state = copy.deepcopy(optimizer.state_dict())
    restored = tcnn.NetworkWithInputEncoding(**config)
    restored.load_state_dict(weights)
    restored_opt = torch.optim.Adam(restored.parameters(), lr=.0002)
    restored_opt.load_state_dict(opt_state)
    with torch.no_grad():
        error = float((model(x).float()-restored(x).float()).abs().max())
    original_loss = step(model, optimizer)
    restored_loss = step(restored, restored_opt)
    parameter_error = max(float((x-y).detach().abs().max()) for x, y in
                          zip(model.parameters(), restored.parameters()))
    torch.cuda.synchronize()
    assert error == 0, 'in-process hash model reload output mismatch'
    assert all(torch.isfinite(p).all() for p in restored.parameters())
    report = dict(status='passed', gpu=torch.cuda.get_device_name(), torch=torch.__version__,
        module=tcnn.__file__, config=config, first_loss=first_loss,
        resumed_loss_difference=abs(original_loss-restored_loss),
        reload_output_max_abs_difference=error, next_step_parameter_max_abs_difference=parameter_error,
        peak_allocated_bytes=torch.cuda.max_memory_allocated(), wall_seconds=time.monotonic()-start,
        note='Synthetic single-encoder CUDA check, not ATGS training or a fresh-process offline reload. '
             'Atomic gradient accumulation may cause next-step numerical differences.')
    with a.output.open('x') as stream:
        stream.write(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
