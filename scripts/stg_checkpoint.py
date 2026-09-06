"""Iteration-boundary STG state, unlike upstream's incomplete capture tuple.

Call only after optimizer.step()/zero_grad(), before sampling the next batch.
The caller must save its sampler/EMS state in loop_state and separately maintain
a durable attempt-time ledger: checkpoint elapsed time cannot account for crashes.
"""
from argparse import Namespace
import os
from pathlib import Path
import random
import tempfile

import numpy as np
import torch


PARAMETERS = ('_xyz', '_features_dc', '_scaling', '_rotation', '_opacity',
              '_motion', '_omega', '_trbf_center', '_trbf_scale')
BUFFERS = ('max_radii2D', 'xyz_gradient_accum', 'denom')
SETTINGS = ('active_sh_degree', 'max_sh_degree', 'spatial_lr_scale', 'percent_dense',
            'trbfslinit', 'preprocesspoints', 'addsphpointsscale', 'raystart',
            'maxx', 'minx', 'maxy', 'miny', 'maxz', 'minz',
            'omegamask', 'maskforems', 'distancetocamera', 'ts')


def _cpu(value):
    if isinstance(value, np.generic):
        return _cpu(value.item())
    if isinstance(value, torch.Tensor):
        return value.detach().cpu().clone()
    if isinstance(value, dict):
        return {k: _cpu(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_cpu(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_cpu(v) for v in value)
    if value is None or type(value) in (str, int, float, bool):
        return value
    raise TypeError(f'Unsupported checkpoint value: {type(value).__name__}')


def save_checkpoint(path, model, *, variant, training_args, iteration,
                    loop_state, provenance):
    """Atomically publish a weights_only-compatible checkpoint; preserve prior file."""
    if variant not in ('lite', 'full'):
        raise ValueError('variant must be lite or full')
    names = PARAMETERS + (('_features_t',) if variant == 'full' else ())
    parameters = {name: getattr(model, name) for name in names}
    decoder = model.rgbdecoder if variant == 'full' else None
    if variant == 'full' and decoder is None:
        raise ValueError('missing full STG decoder')
    all_params = list(parameters.values()) + (list(decoder.parameters()) if decoder is not None else [])
    if any(p.grad is not None and torch.count_nonzero(p.grad).item() for p in all_params):
        raise ValueError('checkpoint requires a completed iteration with cleared gradients')
    if model.optimizer is None:
        raise ValueError('missing optimizer')
    optimized = [p for g in model.optimizer.param_groups for p in g['params']]
    if {id(p) for p in optimized} != {id(p) for p in all_params}:
        raise ValueError('optimizer parameters differ from checkpoint representation')
    numpy_rng = np.random.get_state()
    state = dict(schema='stg-training/v1', variant=variant, iteration=iteration,
                 parameters=_cpu(parameters), buffers=_cpu({k: getattr(model, k) for k in BUFFERS}),
                 settings=_cpu({k: getattr(model, k) for k in SETTINGS if hasattr(model, k)}),
                 decoder=_cpu(decoder.state_dict()) if decoder is not None else None,
                 optimizer=_cpu(model.optimizer.state_dict()), training_args=_cpu(vars(training_args)),
                 loop_state=_cpu(loop_state), provenance=_cpu(provenance),
                 rng=dict(python=random.getstate(), torch=torch.get_rng_state(),
                          numpy=[numpy_rng[0], numpy_rng[1].tolist(), *numpy_rng[2:]],
                          cuda=torch.cuda.get_rng_state_all() if torch.cuda.is_initialized() else []))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name+'.', delete=False) as stream:
        temporary = Path(stream.name)
        torch.save(state, stream)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def restore_checkpoint(path, model, *, variant, provenance, device):
    """Restore into a fresh matching model; reconstruct upstream LR scheduler."""
    state = torch.load(path, map_location='cpu', weights_only=True)
    if state.get('schema') != 'stg-training/v1' or state.get('variant') != variant:
        raise ValueError('checkpoint schema/representation mismatch')
    if state['provenance'] != provenance:
        raise ValueError('checkpoint provenance mismatch')
    names = PARAMETERS + (('_features_t',) if variant == 'full' else ())
    if set(state['parameters']) != set(names) or set(state['buffers']) != set(BUFFERS):
        raise ValueError('missing or unexpected model state')
    if variant == 'full' and state['decoder'] is None:
        raise ValueError('missing full STG decoder')
    if state['rng']['cuda'] and torch.cuda.device_count() != len(state['rng']['cuda']):
        raise ValueError('CUDA device count changed since checkpoint')
    for key, value in state['settings'].items():
        setattr(model, key, value.to(device) if isinstance(value, torch.Tensor) else value)
    for key, value in state['parameters'].items():
        setattr(model, key, torch.nn.Parameter(value.to(device)))
    if variant == 'full':
        model.rgbdecoder.to(device).load_state_dict(state['decoder'], strict=True)
    model.training_setup(Namespace(**state['training_args']))
    for key, value in state['buffers'].items():
        setattr(model, key, value.to(device))
    model.optimizer.load_state_dict(state['optimizer'])
    # Full's batching cache is normally initialized by create_from_pcd(),
    # which restoration deliberately bypasses. Caches start empty at a boundary.
    model.rgb_grd = ({name: torch.zeros_like(value) for name, value in
                      model.rgbdecoder.named_parameters() if value.requires_grad}
                     if variant == 'full' else {})
    # These are render-derived caches, not durable training state.
    for key in ('delta_t', 'trbfoutput', 'computedtrbfscale', 'computedopacity', 'computedscales'):
        setattr(model, key, None)
    random.setstate(state['rng']['python'])
    nr = state['rng']['numpy']
    np.random.set_state((nr[0], np.asarray(nr[1], dtype=np.uint32), *nr[2:]))
    torch.set_rng_state(state['rng']['torch'])
    if state['rng']['cuda']:
        torch.cuda.set_rng_state_all(state['rng']['cuda'])
    return state['iteration'], state['loop_state'], Namespace(**state['training_args'])
