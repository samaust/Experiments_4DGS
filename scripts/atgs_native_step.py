"""Native hash/3DGS ATGS training callbacks over shared scene cameras."""
import ast
import hashlib
from math import exp
from pathlib import Path

import torch
import torch.nn.functional as F
from torch.autograd import Variable


def load_loss_helpers(checkout):
    """Extract only native L1/SSIM; avoid module-level CUDA metric allocation."""
    path = Path(checkout) / 'utils/loss_utils.py'
    names = ('l1_loss', 'gaussian', 'create_window', 'ssim', '_ssim')
    functions = {node.name: node for node in ast.parse(path.read_text()).body
                 if isinstance(node, ast.FunctionDef) and node.name in names}
    if set(functions) != set(names):
        raise ValueError('required upstream loss helpers missing')
    selected = ast.Module(body=[functions[name] for name in names], type_ignores=[])
    namespace = dict(torch=torch, F=F, Variable=Variable, exp=exp)
    exec(compile(selected, str(path), 'exec'), namespace)
    return namespace, hashlib.sha256(ast.dump(selected).encode()).hexdigest()


class NativeTrainingStep:
    def __init__(self, *, scene, opt, pipe, cfg, background, render, prefilter,
                 losses, updates, testing_iterations=(), saving_iterations=()):
        if not cfg.hash or cfg.primitive_type != '3dgs':
            raise ValueError('native callback requires hash/3DGS configuration')
        self.scene, self.opt, self.pipe = scene, opt, pipe
        self.background, self.render, self.prefilter = background, render, prefilter
        self.losses, self.updates = losses, updates
        self.boundaries = set(testing_iterations) | set(saving_iterations)
        self.last_metrics = None

    def statistics_active(self, iteration):
        return self.opt.start_stat < iteration < self.opt.update_until

    def densification_due(self, iteration):
        return (self.statistics_active(iteration) and iteration >= self.opt.update_from
                and iteration % self.opt.update_interval == 0)

    def force_update_due(self, iteration):
        return iteration in self.boundaries or self.densification_due(iteration)

    def __call__(self, model, key, iteration):
        camera = self.scene.camera(key, device=self.background.device, load_image=True)
        return self.camera_step(model, camera, iteration)

    def camera_step(self, model, camera, iteration):
        model.update_learning_rate(iteration, self.opt, camera.time)
        visible = self.prefilter(camera, model, self.pipe, self.background)
        output = self.render(camera, model, self.pipe, self.background, iteration=iteration,
                             visible_mask=visible, retain_grad=0 <= iteration < self.opt.update_until)
        image = output['render']
        target = camera.original_image.to(image.device)
        if image.shape != target.shape or not torch.isfinite(target).all():
            raise ValueError('invalid native training target')
        l1 = self.losses['l1_loss'](image, target)
        ssim = 1. - self.losses['ssim'](image, target)[0]
        scaling = output['scaling'].prod(dim=1).mean()
        loss = (1. - self.opt.lambda_dssim) * l1 + self.opt.lambda_dssim * ssim + .01 * scaling
        if not torch.isfinite(loss):
            raise ValueError('nonfinite native loss; discard live accumulation and reload checkpoint')
        loss.backward()
        self.updates['sanitize_accumulated_gradients']([model.optimizer, model.dy_optimizer])
        with torch.no_grad():
            if self.statistics_active(iteration):
                model.training_statis(output['neural_points'], output['viewspace_points'],
                                      output['neural_opacity'], output['visibility_filter'],
                                      output['selection_mask'], visible)
        self.last_metrics = dict(loss=loss.item(), l1=l1.item(), ssim_loss=ssim.item(),
                                 scaling_reg=scaling.item())
        return model.dynamic_module.routing_encoder_id(camera.time), loss.item()

    def update(self, model, micro_steps, visits, counter):
        return self.updates['step_accumulated_gradients'](model, self.opt, micro_steps, visits, counter)

    def after_microstep(self, model, iteration, updated):
        with torch.no_grad():
            if self.densification_due(iteration):
                if not updated:
                    raise ValueError('densification requires a completed optimizer update')
                model.adjust_anchor(iteration, check_interval=self.opt.update_interval,
                                    success_threshold=self.opt.success_threshold,
                                    grad_threshold=self.opt.densify_grad_threshold,
                                    min_opacity=self.opt.min_opacity)
            if iteration == self.opt.update_until:
                for name in ('opacity_accum', 'offset_gradient_accum', 'offset_denom',
                             'grad_max', 'grad_max_points'):
                    if hasattr(model, name):
                        delattr(model, name)
            if iteration % 100 == 0:
                torch.cuda.empty_cache()
