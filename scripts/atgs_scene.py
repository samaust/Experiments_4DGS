"""ATGS camera interface over the shared, validated SelfCap manifest.

This supplies cameras only; anchor lifetime and checkpoint adapters are separate.
The 3DGS rasterizer receives off-center intrinsics through the full projection.
"""
from stg_scene import SelfCapScene, make_camera as make_shared_camera


def adapt_camera(view):
    """Add ATGS fields without re-synchronizing or rescaling normalized time."""
    view.time = view.timestamp
    view.mask = None
    view.depth = None
    view.image_path = None  # Author filename-based sync must remain disabled.
    # Keep ATGS's depth convention while preserving the shared x/y projection.
    view.projection_matrix = view.projection_matrix.clone()
    view.projection_matrix[2, 2] = view.zfar / (view.zfar - view.znear)
    view.full_proj_transform = view.world_view_transform @ view.projection_matrix
    return view


def make_camera(calibration, timestamp, *, device, name='', uid=0):
    return adapt_camera(make_shared_camera(calibration, timestamp, device=device,
                                           name=name, uid=uid))


class ATGSSelfCapScene(SelfCapScene):
    def camera(self, key, *, device, load_image=False):
        return adapt_camera(super().camera(key, device=device, load_image=load_image))

    def sweep_camera(self, index, *, device):
        return adapt_camera(super().sweep_camera(index, device=device))
