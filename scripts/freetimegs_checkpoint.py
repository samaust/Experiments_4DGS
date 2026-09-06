"""Complete iteration-boundary state for the native ordinary-Adam reproduction."""
from dataclasses import asdict
import os
from pathlib import Path
import tempfile

import torch

from stg_checkpoint import _cpu
from training_rng import capture_rng, restore_rng

PARAMETERS = {'means', 'scales', 'quats', 'opacities', 'sh0', 'shN',
              'times', 'durations', 'velocities'}


def validate_parameters(parameters, sh_degree):
    if set(parameters) != PARAMETERS:
        raise ValueError('missing or unexpected FreeTimeGS parameter groups')
    count = len(parameters['means'])
    shapes = dict(means=(count, 3), scales=(count, 3), quats=(count, 4),
        opacities=(count,), sh0=(count, 1, 3), shN=(count, (sh_degree+1)**2-1, 3),
        times=(count, 1), durations=(count, 1), velocities=(count, 3))
    if count < 4 or any(value.shape != shapes[name] or value.dtype != torch.float32
                        or not torch.isfinite(value).all() for name, value in parameters.items()):
        raise ValueError('invalid FreeTimeGS parameter shape/type/value')


def _device(value, device):
    if isinstance(value, torch.Tensor):
        return value.to(device)
    if isinstance(value, dict):
        return {key: _device(item, device) for key, item in value.items()}
    if isinstance(value, list):
        return [_device(item, device) for item in value]
    if isinstance(value, tuple):
        return tuple(_device(item, device) for item in value)
    return value


def save_checkpoint(path, model, *, iteration, loop_state, provenance):
    validate_parameters(model.splats, model.cfg.sh_degree)
    if set(model.splats) != PARAMETERS or set(model.optimizers) != PARAMETERS:
        raise ValueError('missing or unexpected FreeTimeGS parameter groups')
    for name, parameter in model.splats.items():
        optimizer = model.optimizers[name]
        if parameter.grad is not None:
            raise ValueError('save only after optimizer update and gradient clearing')
        if type(optimizer) is not torch.optim.Adam:
            raise ValueError('expected native ordinary Adam optimizer')
        bound = [p for group in optimizer.param_groups for p in group['params']]
        if len(bound) != 1 or bound[0] is not parameter:
            raise ValueError('optimizer parameter binding mismatch')
    if model.grad_accum.shape != (len(model.splats['means']),):
        raise ValueError('relocation accumulator shape mismatch')
    state = dict(schema='freetimegs-training/v1', iteration=iteration,
        parameters=_cpu(dict(model.splats)), optimizers=_cpu({key: opt.state_dict()
            for key, opt in model.optimizers.items()}),
        schedulers=_cpu([scheduler.state_dict() for scheduler in model.schedulers]),
        config=_cpu(asdict(model.cfg)), strategy_state=_cpu(model.strategy_state),
        grad_accum=_cpu(model.grad_accum), grad_count=model.grad_count,
        loop_state=_cpu(loop_state), provenance=_cpu(provenance),
        source_digests=_cpu(model.source_digests),
        rng=capture_rng(include_cuda=torch.device(model.device).type == 'cuda'))
    path = Path(path)
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=path.name+'.', delete=False) as stream:
        temporary = Path(stream.name)
        torch.save(state, stream)
        stream.flush()
        os.fsync(stream.fileno())
    # Publish without replacing a checkpoint that appeared since the check.
    os.link(temporary, path)
    temporary.unlink()
    directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def restore_checkpoint(path, model, *, provenance):
    state = torch.load(path, map_location='cpu', weights_only=True)
    if state.get('schema') != 'freetimegs-training/v1' or state['provenance'] != provenance:
        raise ValueError('checkpoint schema/provenance mismatch')
    if state['config'] != asdict(model.cfg) or state['source_digests'] != model.source_digests:
        raise ValueError('checkpoint configuration/source mismatch')
    if set(state['parameters']) != PARAMETERS or set(state['optimizers']) != PARAMETERS:
        raise ValueError('incomplete FreeTimeGS checkpoint')
    validate_parameters(state['parameters'], model.cfg.sh_degree)
    count = len(state['parameters']['means'])
    if (count < 4 or state['grad_accum'].shape != (count,) or
            any(len(p) != count or not torch.isfinite(p).all() for p in state['parameters'].values())):
        raise ValueError('invalid parameter/relocation state')
    if len(state['schedulers']) != 1:
        raise ValueError('missing position scheduler')
    model.splats = torch.nn.ParameterDict({name: torch.nn.Parameter(value.to(model.device))
                                           for name, value in state['parameters'].items()})
    model.optimizers = {name: torch.optim.Adam([parameter]) for name, parameter in model.splats.items()}
    model.schedulers = [torch.optim.lr_scheduler.ExponentialLR(
        model.optimizers['means'], gamma=.01 ** (1/model.cfg.max_steps))]
    for name, optimizer in model.optimizers.items():
        optimizer.load_state_dict(state['optimizers'][name])
    model.schedulers[0].load_state_dict(state['schedulers'][0])
    model.strategy_state = _device(state['strategy_state'], model.device)
    model.grad_accum = state['grad_accum'].to(model.device)
    model.grad_count = state['grad_count']
    restore_rng(state['rng'], include_cuda=torch.device(model.device).type == 'cuda')
    return state['iteration'], state['loop_state']
