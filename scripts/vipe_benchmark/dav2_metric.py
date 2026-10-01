"""D7 native Hypersim Small metric depth adapter, preserving the 20 m head."""
from types import SimpleNamespace

import cv2
import numpy as np

from .moge_metric import supplied_horizontal_fov


class DAV2MetricSmallAdapter:
    """Use the pinned metric `infer_image` preprocessing and grid restoration."""
    component = 'D7'

    def __init__(self, runtime):
        if (getattr(runtime, 'encoder', None) != 'vits' or
                getattr(runtime, 'max_depth', None) != 20 or
                getattr(runtime, 'training', False)):
            raise ValueError('D7 requires eval-mode Hypersim Small with max_depth=20')
        parameters = getattr(runtime, 'parameters', None)
        if parameters is not None:
            import torch
            first = next(parameters(), None)
            if first is not None and first.dtype != torch.float32:
                raise ValueError('D7 native model precision must be float32')
        self.runtime = runtime

    def predict(self, rgb, K, image_valid):
        if rgb.shape != (540, 960, 3) or rgb.dtype != np.uint8:
            raise ValueError('D7 requires accepted 960x540 uint8 RGB')
        supplied_horizontal_fov(K, 960, 540)  # Grid check; D7 does not consume FoV.
        if image_valid.shape != rgb.shape[:2] or image_valid.dtype != np.bool_:
            raise ValueError('D7 accepted footprint required')
        bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
        native = np.asarray(self.runtime.infer_image(bgr, input_size=518))
        if native.shape != (540, 960) or native.dtype != np.float32:
            raise ValueError('D7 native infer_image output grid/dtype changed')
        if not np.isfinite(native[image_valid]).all():
            raise ValueError('D7 native output contains nonfinite accepted pixels')
        if ((native[image_valid] <= 0) | (native[image_valid] > 20)).any():
            raise ValueError('D7 native 20 m metric range violated')
        values = native.copy()
        values[~image_valid] = np.nan
        return SimpleNamespace(domain='camera_z_metres', values=values,
            valid=image_valid.copy(), raw_values=native.copy(),
            metadata=dict(component='D7', native_depth_type='camera-z metres',
                conversion_count=0, native_checkpoint='Hypersim Small vits',
                max_depth_metres=20, input_size=518,
                native_processed_size=[924, 518], native_output_size=[960, 540],
                native_resize='lower_bound, multiple of 14, INTER_CUBIC',
                native_normalization='ImageNet mean/std, BGR to RGB in infer_image',
                native_output_interpolation='bilinear align_corners=True',
                native_crop='none', native_precision='float32',
                seed_policy='eval inference; no stochastic sampling'))
