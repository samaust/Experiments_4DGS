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
