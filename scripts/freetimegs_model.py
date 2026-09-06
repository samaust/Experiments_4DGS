"""Thin binding of existing FreeTimeGsVanilla model construction and rendering."""
from types import MethodType

from freetimegs_source import load_initializer, load_temporal_methods


class NativeFreeTimeModel:
    def __init__(self, checkout, cfg, init_data, *, scene_scale, device):
        initialize, init_digest = load_initializer(checkout)
        methods, render_digest = load_temporal_methods(checkout, include_render=True)
        self.cfg = cfg
        self.splats, self.optimizers = initialize(cfg, init_data, scene_scale, device)
        self.source_digests = dict(initializer=init_digest, render=render_digest)
        for name, function in methods.items():
            setattr(self, name, MethodType(function, self))

    def render(self, camera, *, sh_degree):
        return self.rasterize_splats(camera.camtoworlds, camera.Ks,
                                     camera.width, camera.height, camera.t, sh_degree)

    def enable_training(self, checkout, *, scene_scale, device, lpips):
        import torch
        from freetimegs_training import load_training
        _, methods, evidence = load_training(checkout)
        self.source_digests.update(evidence)
        self.scene_scale, self.device, self.lpips = scene_scale, device, lpips
        self.cfg.strategy.check_sanity(self.splats, self.optimizers)
        self.strategy_state = self.cfg.strategy.initialize_state(scene_scale=scene_scale)
        self.grad_accum = torch.zeros(len(self.splats['means']), device=device)
        self.grad_count = 0
        for name, method in methods.items():
            setattr(self, name, MethodType(method, self))
        self.schedulers = [torch.optim.lr_scheduler.ExponentialLR(
            self.optimizers['means'], gamma=.01 ** (1/self.cfg.max_steps))]
