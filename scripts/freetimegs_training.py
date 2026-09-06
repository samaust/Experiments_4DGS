"""Extract the audited reproduction's preset and complete optimization step."""
import ast
from dataclasses import dataclass, field
import hashlib
import math
from pathlib import Path
import typing

import numpy as np
import torch

SOURCE_SHA256 = 'fc3e4320da73a470d0a16bcb5803f84d1bda5bdeafb000fcc39e022fbcfaaeb4'


def load_training(checkout):
    from fused_ssim import fused_ssim
    from gsplat.strategy import DefaultStrategy, MCMCStrategy
    from gsplat.strategy.ops import _update_param_with_optimizer, remove
    path = Path(checkout) / 'src/simple_trainer_freetime_4d_pure_relocation.py'
    source = path.read_bytes()
    if hashlib.sha256(source).hexdigest() != SOURCE_SHA256:
        raise ValueError('FreeTimeGS training source changed; audit required')
    tree = ast.parse(source)
    config = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'Config')
    presets = [n for n in ast.walk(tree) if isinstance(n, ast.Assign)
               and any(isinstance(t, ast.Name) and t.id == 'configs' for t in n.targets)]
    if len(presets) != 1:
        raise ValueError('ambiguous native presets')
    runner = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == 'FreeTime4DRunner')
    names = {'relocate_gaussians', 'prune_gaussians', 'budget_prune_gaussians'}
    methods = [n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name in names]
    train = next(n for n in runner.body if isinstance(n, ast.FunctionDef) and n.name == 'train')
    loops = [n for n in train.body if isinstance(n, ast.For)
             and isinstance(n.target, ast.Name) and n.target.id == 'step']
    if len(loops) != 1 or len(methods) != 3:
        raise ValueError('unexpected native training structure')
    body = loops[0].body
    start = next(i for i, n in enumerate(body) if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == 'progress' for t in n.targets))
    stop = next(i for i, n in enumerate(body) if isinstance(n, ast.Assign)
                and any(isinstance(t, ast.Name) and t.id == 'phase' for t in n.targets))
    # Only inputs and the iteration-boundary return are adapted. All loss,
    # annealing, optimization, relocation and pruning statements remain native.
    wrapper = ast.parse('''
def training_step(self, step, camera, schedulers):
    cfg = self.cfg
    device = self.device
    max_steps = cfg.max_steps
    camtoworlds, Ks, pixels = camera.camtoworlds, camera.Ks, camera.pixels
    height, width, t = camera.height, camera.width, camera.t
    in_settling = step < cfg.densification_start_step
    in_refinement = not in_settling
''').body[0]
    wrapper.body.extend(body[start:stop])
    wrapper.body.extend(ast.parse('''
return dict(loss=loss.detach(), l1=l1_loss.detach(), ssim=ssim_val.detach(),
            lpips=lpips_loss.detach(), duration_regularization=duration_reg_loss.detach(),
            velocity_lr=vel_lr, points=len(self.splats['means']))
''').body)
    module = ast.Module(body=[config, presets[0], *methods, wrapper], type_ignores=[])
    ast.fix_missing_locations(module)
    namespace = dict(vars(typing), __name__=__name__, dataclass=dataclass, field=field,
        torch=torch, Tensor=torch.Tensor, math=math, np=np, F=torch.nn.functional,
        fused_ssim=fused_ssim, DefaultStrategy=DefaultStrategy, MCMCStrategy=MCMCStrategy,
        _update_param_with_optimizer=_update_param_with_optimizer, remove=remove)
    exec(compile(module, str(path), 'exec'), namespace)
    cfg = namespace['configs']['default_keyframe'][1]
    cfg.adjust_steps(cfg.steps_scaler)
    return cfg, {name: namespace[name] for name in names | {'training_step'}}, dict(
        source_sha256=SOURCE_SHA256, training_ast_sha256=hashlib.sha256(ast.dump(module).encode()).hexdigest())
