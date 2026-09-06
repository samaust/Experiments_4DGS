"""Supplemental ATGS loop state, restored after model and optimizer loading.

Captures unaveraged gradients at completed microstep boundaries. This is not
a standalone model checkpoint or a training loop implementation.
"""
import copy
import math

import torch

from training_rng import capture_rng, restore_rng


def parameters(model):
    result = {}
    seen = set()
    for name in ('optimizer', 'dy_optimizer'):
        optimizer = getattr(model, name)
        if optimizer is None:
            raise ValueError('model optimizers must be initialized')
        for group_index, group in enumerate(optimizer.param_groups):
            for index, parameter in enumerate(group['params']):
                if id(parameter) in seen:
                    raise ValueError('duplicate optimizer parameter')
                seen.add(id(parameter))
                result[f"{name}/{group_index}:{group.get('name', 'unnamed')}/{index}"] = parameter
    return result


def validate_loop(loop, encoders):
    required = {'iteration', 'micro_steps', 'encoder_visits', 'update_count',
                'last_update_iteration', 'ema_loss'}
    if set(loop) != required:
        raise ValueError('loop state fields mismatch')
    for name in ('iteration', 'micro_steps', 'update_count', 'last_update_iteration'):
        if type(loop[name]) is not int or loop[name] < 0:
            raise ValueError('invalid loop counter')
    if any(loop[k] > loop['iteration'] for k in ('micro_steps', 'update_count', 'last_update_iteration')):
        raise ValueError('inconsistent loop counters')
    visits = loop['encoder_visits']
    if not isinstance(visits, dict) or any(type(k) is not int or not 0 <= k < encoders
            or type(v) is not int or v <= 0 for k, v in visits.items()):
        raise ValueError('invalid encoder visits')
    if sum(visits.values()) != loop['micro_steps']:
        raise ValueError('encoder visits do not sum to microsteps')
    if not isinstance(loop['ema_loss'], (int, float)) or not math.isfinite(loop['ema_loss']):
        raise ValueError('invalid EMA loss')


def capture_loop_state(model, sampler, loop, *, include_cuda=True):
    validate_loop(loop, len(sampler.buckets))
    entries = {}
    for name, parameter in parameters(model).items():
        gradient = parameter.grad
        if gradient is not None and (not parameter.requires_grad or not torch.isfinite(gradient).all()):
            raise ValueError('invalid accumulated gradient')
        entries[name] = dict(shape=list(parameter.shape), dtype=str(parameter.dtype),
                             requires_grad=parameter.requires_grad,
                             gradient=None if gradient is None else gradient.detach().cpu().clone())
    if loop['micro_steps'] == 0 and any(item['gradient'] is not None for item in entries.values()):
        raise ValueError('update-boundary gradients must be cleared')
    return dict(schema='atgs-loop/v1', loop=copy.deepcopy(loop),
                sampler=sampler.state_dict(), rng=capture_rng(include_cuda=include_cuda), parameters=entries)


def restore_loop_state(model, sampler, state, *, include_cuda=True):
    if state.get('schema') != 'atgs-loop/v1':
        raise ValueError('unsupported loop state schema')
    validate_loop(state['loop'], len(sampler.buckets))
    current = parameters(model)
    if current.keys() != state['parameters'].keys():
        raise ValueError('optimizer parameter labels mismatch')
    pending = {}
    for name, parameter in current.items():
        item = state['parameters'][name]
        if (item['shape'] != list(parameter.shape) or item['dtype'] != str(parameter.dtype)
                or item['requires_grad'] != parameter.requires_grad):
            raise ValueError(f'optimizer parameter topology mismatch: {name}')
        gradient = item['gradient']
        if gradient is not None:
            if (not isinstance(gradient, torch.Tensor) or gradient.shape != parameter.shape
                    or gradient.dtype != parameter.dtype or not parameter.requires_grad
                    or not torch.isfinite(gradient).all()):
                raise ValueError(f'invalid saved gradient: {name}')
            gradient = gradient.to(parameter.device).clone()
        pending[name] = gradient
    if state['loop']['micro_steps'] == 0 and any(g is not None for g in pending.values()):
        raise ValueError('update-boundary gradients must be cleared')
    # Validate the sampler without advancing or altering the live one.
    candidate = copy.deepcopy(sampler)
    candidate.load_state_dict(state['sampler'])
    restore_rng(state['rng'], include_cuda=include_cuda)
    sampler.load_state_dict(candidate.state_dict())
    for name, parameter in current.items():
        parameter.grad = pending[name]
    return copy.deepcopy(state['loop'])
