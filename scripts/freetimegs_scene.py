"""Shared SelfCap manifest cameras in the FreeTimeGsVanilla/gsplat layout."""
from types import SimpleNamespace

import torch

from stg_scene import SelfCapScene


def gsplat_camera(view, calibration):
    """Convert validated native camera tensors; preserve continuous intrinsics."""
    world_to_camera = view.world_view_transform.T.contiguous()
    camera_to_world = torch.linalg.inv(world_to_camera)
    intrinsic = torch.tensor(calibration['K'], dtype=world_to_camera.dtype,
                             device=world_to_camera.device)
    image = view.original_image
    return SimpleNamespace(
        camtoworlds=camera_to_world[None], viewmats=world_to_camera[None],
        Ks=intrinsic[None], width=view.image_width, height=view.image_height,
        t=view.timestamp, name=view.image_name,
        # Native trainer uses batch x height x width x RGB in [0,1].
        pixels=None if image is None else image.permute(1, 2, 0)[None].contiguous())


class FreeTimeSelfCapScene(SelfCapScene):
    def camera(self, key, *, device, load_image=False):
        view = super().camera(key, device=device, load_image=load_image)
        return gsplat_camera(view, self.cameras[key[0]])

    def training_camera(self, key, *, device, load_image=True):
        if self.cameras[key[0]]['split'] != 'train':
            raise ValueError('held-out camera cannot be used for training')
        return self.camera(key, device=device, load_image=load_image)

    def sweep_camera(self, index, *, device):
        view = super().sweep_camera(index, device=device)
        sweep = self.manifest['sweep']
        calibration = dict(self.cameras[sweep['start_camera']], **sweep['poses'][index])
        return gsplat_camera(view, calibration)
