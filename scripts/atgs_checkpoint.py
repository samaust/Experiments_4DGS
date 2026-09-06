"""Strict preflight for native ATGS directory checkpoints.

These files alone do not establish complete resumability: lifetime data, RNG,
sampler and accumulation state require the eventual training adapter's sidecar.
"""
import hashlib
from pathlib import Path


MODEL_FILES = ('point_cloud.ply', 'mlp_opacity.pth', 'mlp_cov.pth',
               'mlp_color.pth', 'mlp_offset.pth', 'voxel_grid.pth', 'FDHash.pth')
OPTIMIZER_FILES = ('optimizer.pth', 'dy_optimizer.pth')


def capture_auxiliary_state(model):
    """Snapshot plain tensor attributes omitted by nn.Module state dictionaries.

This supplements the native model files; it does not capture gradients or RNG.
"""
    import torch
    tensors = {}
    for name, value in vars(model).items():
        if isinstance(value, torch.Tensor):
            tensors[name] = dict(value=value.detach().cpu().clone(),
                                 parameter=isinstance(value, torch.nn.Parameter),
                                 requires_grad=value.requires_grad)
    return dict(schema='atgs-auxiliary/v1', tensors=tensors,
                time_embedding={k: v.detach().cpu().clone() for k, v in model.time_embedding.state_dict().items()},
                scalars={k: getattr(model, k) for k in ('spatial_lr_scale', 'voxel_size', 'percent_dense')})


def restore_auxiliary_state(model, state, *, device):
    """Restore before training_setup so optimizers bind the restored parameters."""
    import torch
    if model.optimizer is not None:
        raise ValueError('restore auxiliary state before optimizer construction')
    if state.get('schema') != 'atgs-auxiliary/v1':
        raise ValueError('unsupported ATGS auxiliary schema')
    required = {'_anchor', '_offset', '_opacity', '_scaling', '_rotation', '_anchor_feat', 'point_times_list'}
    if not required.issubset(state.get('tensors', {})):
        raise ValueError('missing required ATGS auxiliary tensors')
    if set(state.get('scalars', {})) != {'spatial_lr_scale', 'voxel_size', 'percent_dense'}:
        raise ValueError('missing ATGS auxiliary scalars')
    pending = {}
    for name, item in state['tensors'].items():
        extrema = {'minx', 'miny', 'minz', 'maxx', 'maxy', 'maxz'}
        if name not in extrema and (not hasattr(model, name) or not isinstance(getattr(model, name), (torch.Tensor, type(None)))):
            raise ValueError(f'unexpected auxiliary tensor: {name}')
        value = item['value'].to(device=device).clone()
        if item['parameter']:
            value = torch.nn.Parameter(value, requires_grad=item['requires_grad'])
        else:
            value.requires_grad_(item['requires_grad'])
        pending[name] = value
    model.time_embedding.load_state_dict(state['time_embedding'], strict=True)
    for name, value in pending.items():
        setattr(model, name, value)
    for name, value in state['scalars'].items():
        setattr(model, name, value)


def assert_state_equal(original, restored):
    """Compare nested optimizer state exactly, allowing device relocation."""
    import torch
    if isinstance(original, torch.Tensor):
        if not isinstance(restored, torch.Tensor):
            raise AssertionError('optimizer state tensor type mismatch')
        torch.testing.assert_close(original.cpu(), restored.cpu(), rtol=0, atol=0)
    elif isinstance(original, dict):
        if not isinstance(restored, dict) or original.keys() != restored.keys():
            raise AssertionError('optimizer state keys mismatch')
        for key in original:
            assert_state_equal(original[key], restored[key])
    elif isinstance(original, (tuple, list)):
        if type(original) is not type(restored) or len(original) != len(restored):
            raise AssertionError('optimizer state sequence mismatch')
        for a, b in zip(original, restored):
            assert_state_equal(a, b)
    elif original != restored:
        raise AssertionError('optimizer state value mismatch')


def inspect_native_checkpoint(directory, *, require_optimizers=False, require_auxiliary=False):
    directory = Path(directory).resolve()
    if not directory.is_dir():
        raise ValueError(f'checkpoint directory missing: {directory}')
    names = MODEL_FILES + (OPTIMIZER_FILES if require_optimizers else ())
    if require_auxiliary:
        names += ('auxiliary.pth',)
    result = {}
    for name in names:
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size == 0:
            raise ValueError(f'missing, empty or linked checkpoint component: {name}')
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        result[name] = dict(bytes=path.stat().st_size, sha256=digest)
    return result


def tensor_difference(left, right):
    """Report finite tensor differences without hiding CUDA reduction variability."""
    import torch
    if left.shape != right.shape or left.dtype != right.dtype:
        raise ValueError('tensor structure mismatch')
    if not torch.isfinite(left).all() or not torch.isfinite(right).all():
        raise ValueError('nonfinite comparison input')
    if left.numel() == 0:
        return 0.0
    return (left.detach().double() - right.detach().double()).abs().max().item()


def capture_gradients(model):
    """Copy gradients to CPU with stable optimizer/group/parameter labels."""
    gradients = {}
    for optimizer_name in ('optimizer', 'dy_optimizer'):
        optimizer = getattr(model, optimizer_name)
        for group_index, group in enumerate(optimizer.param_groups):
            label = f"{optimizer_name}/{group_index}:{group.get('name', 'unnamed')}"
            for index, parameter in enumerate(group['params']):
                gradients[f'{label}/{index}'] = (None if parameter.grad is None else
                                                 parameter.grad.detach().cpu().clone())
    return gradients


def compare_gradients(first, second):
    if first.keys() != second.keys():
        raise ValueError('gradient labels mismatch')
    result = {}
    for name, a in first.items():
        b = second[name]
        if (a is None) != (b is None):
            raise ValueError(f'gradient presence mismatch: {name}')
        result[name] = None if a is None else tensor_difference(a, b)
    return result


def probe_repeated_backward(model, *, camera, pipe, background):
    """Same-model control: two backward passes with no intervening update."""
    import torch
    from gaussian_renderer import prefilter_voxel, render
    model.mlp_color.train()
    snapshots, losses = [], []
    parameters = [p for optimizer in (model.optimizer, model.dy_optimizer)
                  for group in optimizer.param_groups for p in group['params']]
    versions = [p._version for p in parameters]
    for _ in range(2):
        for optimizer in (model.optimizer, model.dy_optimizer):
            optimizer.zero_grad(set_to_none=True)
        with torch.random.fork_rng(devices=[background.device.index]):
            visible = prefilter_voxel(camera, model, pipe, background)
            image = render(camera, model, pipe, background, iteration=4, visible_mask=visible)['render']
            loss = (image - .25).square().mean()
            if not torch.isfinite(loss):
                raise ValueError('nonfinite repeated-backward loss')
            loss.backward()
        snapshots.append(capture_gradients(model))
        losses.append(loss.item())
    if [p._version for p in parameters] != versions:
        raise ValueError('repeated backward modified model parameters')
    differences = compare_gradients(*snapshots)
    for optimizer in (model.optimizer, model.dy_optimizer):
        optimizer.zero_grad(set_to_none=True)
    return dict(losses=losses, loss_abs_difference=abs(losses[0] - losses[1]),
                gradient_max_abs_differences=differences,
                exact=losses[0] == losses[1] and all(v in (None, 0.) for v in differences.values()),
                optimizer_updates=0, torch_rng_restored_between_passes=True)


def probe_next_update(model, restored, *, camera, pipe, background, opt):
    """Compare a synthetic fourth update; no RNG/sampler resume claim."""
    import torch
    from gaussian_renderer import prefilter_voxel, render

    control = probe_repeated_backward(model, camera=camera, pipe=pipe, background=background)
    losses, images, gradients = [], [], []
    for current in (model, restored):
        current.mlp_color.train()
        current.update_learning_rate(4, opt, camera.time)
        optimizers = (current.optimizer, current.dy_optimizer)
        for optimizer in optimizers:
            optimizer.zero_grad(set_to_none=True)
        visible = prefilter_voxel(camera, current, pipe, background)
        output = render(camera, current, pipe, background, iteration=4, visible_mask=visible)
        loss = (output['render'] - .25).square().mean()
        if not torch.isfinite(loss):
            raise ValueError('nonfinite next-update loss')
        losses.append(loss.item())
        loss.backward()
        gradients.append(capture_gradients(current))
        for optimizer in optimizers:
            parameters = [p for group in optimizer.param_groups for p in group['params']]
            torch.nn.utils.clip_grad_norm_(parameters, opt.gradient_clip_norm, error_if_nonfinite=True)
            optimizer.step()
        current.mlp_color.eval()
        with torch.no_grad():
            visible = prefilter_voxel(camera, current, pipe, background)
            images.append(render(camera, current, pipe, background, iteration=4, visible_mask=visible)['render'])
    differences = {}
    group_differences = {}
    state_exact = {}
    for name in ('optimizer', 'dy_optimizer'):
        a, b = getattr(model, name), getattr(restored, name)
        assert len(a.param_groups) == len(b.param_groups)
        maximum = 0.
        for group_index, (ga, gb) in enumerate(zip(a.param_groups, b.param_groups)):
            assert len(ga['params']) == len(gb['params'])
            group_maximum = 0.
            for pa, pb in zip(ga['params'], gb['params']):
                group_maximum = max(group_maximum, tensor_difference(pa, pb))
            group_differences[f"{name}/{group_index}:{ga.get('name', 'unnamed')}"] = group_maximum
            maximum = max(maximum, group_maximum)
        differences[name] = maximum
        try:
            assert_state_equal(a.state_dict(), b.state_dict())
            state_exact[name] = True
        except AssertionError:
            state_exact[name] = False
    return dict(losses=losses, loss_abs_difference=abs(losses[0] - losses[1]),
                repeated_backward_control=control,
                gradient_max_abs_differences=compare_gradients(*gradients),
                parameter_group_max_abs_differences=group_differences,
                parameter_max_abs_differences=differences, optimizer_state_exact=state_exact,
                image_max_abs_difference=tensor_difference(*images),
                exact=losses[0] == losses[1] and all(v == 0 for v in differences.values())
                      and all(state_exact.values()) and torch.equal(*images),
                scope='one synthetic next update, same process; differences reported, not assumed zero')


def probe_native_reload(model, factory, cloud, directory, *, camera, pipe, background, restore_auxiliary=False, opt=None, next_update=False):
    """Synthetic in-process model reload probe, not a resume implementation.

Uses a supplied cloud for upstream lifetime reconstruction and writes only a
new explicit directory. Supplemental tensors and optimizers are restored only
when restore_auxiliary is explicitly selected. No sampler/RNG state is restored.
"""
    import torch
    from gaussian_renderer import prefilter_voxel, render

    directory = Path(directory)
    directory.mkdir(parents=True, exist_ok=False)
    model.save_ply(str(directory / 'point_cloud.ply'))
    model.save_mlp_checkpoints(str(directory))
    model.save_optimizer(str(directory))
    if restore_auxiliary:
        torch.save(capture_auxiliary_state(model), directory / 'auxiliary.pth')
    files = inspect_native_checkpoint(directory, require_optimizers=True, require_auxiliary=restore_auxiliary)
    restored = factory()
    restored.load_ply_sparse_gaussian(str(directory / 'point_cloud.ply'), cloud, [0, 60])
    restored.load_model(str(directory))
    if restore_auxiliary:
        state = torch.load(directory / 'auxiliary.pth', map_location='cpu', weights_only=True)
        restore_auxiliary_state(restored, state, device='cuda')
        restored.training_setup(opt, 1, str(directory))
        assert_state_equal(model.optimizer.state_dict(), restored.optimizer.state_dict())
        assert_state_equal(model.dy_optimizer.state_dict(), restored.dy_optimizer.state_dict())
        for name, item in state['tensors'].items():
            value = getattr(restored, name)
            torch.testing.assert_close(value.cpu(), item['value'], rtol=0, atol=0)
            assert value.requires_grad == item['requires_grad']
    restored.mlp_color.eval()
    model.mlp_color.eval()
    with torch.no_grad():
        def draw(current):
            visible = prefilter_voxel(camera, current, pipe, background)
            return render(camera, current, pipe, background, iteration=1, visible_mask=visible)['render']
        reference, reloaded = draw(model), draw(restored)
    torch.testing.assert_close(reference, reloaded, rtol=0, atol=0)
    # Surface losses that an image-only equality test would otherwise miss.
    omitted = {}
    for name in ('_offset', '_opacity', 'point_times_list'):
        original, loaded = getattr(model, name), getattr(restored, name)
        omitted[name] = dict(original_shape=list(original.shape), reloaded_shape=list(loaded.shape),
                             equal=original.shape == loaded.shape and torch.equal(original, loaded))
    next_result = None
    if next_update:
        next_result = probe_next_update(model, restored, camera=camera, pipe=pipe, background=background, opt=opt)
    return dict(scope='native in-process inference reload, supplied lifetime cloud; not resumable',
                next_update=next_result,
                files=files, max_abs_difference=(reference - reloaded).abs().max().item(),
                auxiliary_tensors=omitted, anchor_requires_grad=restored._anchor.requires_grad,
                optimizers_restored=restore_auxiliary, auxiliary_restored=restore_auxiliary,
                optimizer_state_exact=restore_auxiliary,
                optimizer_states_nonempty=bool(model.optimizer.state) and bool(model.dy_optimizer.state),
                fresh_process=False, offline_enforced=False)
