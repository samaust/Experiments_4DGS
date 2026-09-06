"""Weights-only-loadable RNG snapshots for resumable training adapters."""
import random

import numpy as np
import torch


def capture_rng(*, include_cuda=True):
    if include_cuda and not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; RNG capture stopped, no CPU fallback')
    numpy_state = np.random.get_state()
    return dict(schema='training-rng/v1', python=random.getstate(),
                numpy=dict(algorithm=numpy_state[0], keys=torch.from_numpy(numpy_state[1].astype(np.int64)),
                           position=numpy_state[2], has_gauss=numpy_state[3], cached_gaussian=numpy_state[4]),
                torch_cpu=torch.get_rng_state().clone(),
                torch_cuda=[value.clone() for value in torch.cuda.get_rng_state_all()] if include_cuda else [])


def restore_rng(state, *, include_cuda=True):
    if state.get('schema') != 'training-rng/v1':
        raise ValueError('unsupported RNG schema')
    cuda_states = state['torch_cuda']
    if include_cuda:
        if not torch.cuda.is_available():
            raise RuntimeError('CUDA unavailable; RNG restore stopped, no CPU fallback')
        if len(cuda_states) != torch.cuda.device_count():
            raise ValueError('CUDA RNG device-count mismatch')
    elif cuda_states:
        raise ValueError('refusing to discard saved CUDA RNG state')
    numpy = state['numpy']
    keys = numpy['keys']
    if keys.dtype != torch.int64 or keys.shape != (624,) or (keys < 0).any() or (keys > 2**32 - 1).any():
        raise ValueError('invalid NumPy RNG keys')
    numpy_state = (numpy['algorithm'], keys.cpu().numpy().astype(np.uint32),
                   numpy['position'], numpy['has_gauss'], numpy['cached_gaussian'])
    # Validate CPU states before changing any process-global generator.
    random.Random().setstate(state['python'])
    np.random.RandomState().set_state(numpy_state)
    torch.Generator(device='cpu').set_state(state['torch_cpu'].cpu())
    for index, value in enumerate(cuda_states):
        torch.Generator(device=f'cuda:{index}').set_state(value.cpu())
    random.setstate(state['python'])
    np.random.set_state(numpy_state)
    torch.set_rng_state(state['torch_cpu'].cpu())
    if include_cuda:
        torch.cuda.set_rng_state_all([value.cpu() for value in cuda_states])
