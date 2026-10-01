"""Pinned Marigold V2 Log-stage2 relative-log image adapter (D11)."""

from types import SimpleNamespace

import numpy as np


# Native scripts/infer.py, inference_depth.yaml and component_loader.py at the
# pinned source revision define this profile. The runtime owns native resizing
# to a multiple of 16 and restoration to the original 960x540 grid.
SOURCE_REVISION = 'bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85'
ADAPTER_REVISION = 'cdf9810fb690886391a63aec012b5f501064fb0d'
BASE_REVISION = 'd3968ef930e841f4c73640fb8afa3b306a78167e'
PROFILE = dict(
    modality='depth', checkpoint='depth/Log-stage2',
    base='Qwen/Qwen-Image-Edit-2509',
    prompt='qwen_edit_2509_qwen_depth_realimg512',
    seed=2025, steps=1, guidance_scale=1.0, timestep=0.499,
    transformer_quantization='4bit-nf4', compute_dtype='bfloat16',
    vae_dtype='bfloat16',
    resize='ReshapeToMultiple(16, Lanczos), then linear restore to original grid',
    output='mean of decoded RGB channels; affine-invariant log depth',
)


class MarigoldLogStage2Adapter:
    """Call one persistent pinned native runtime once for each independent RGB.

    The runtime must expose ``profile`` and ``infer_image(rgb, *, seed)``.
    ``infer_image`` returns the native float32 saved prediction after the pinned
    repository's original-grid restoration. It must retain the model in memory
    across calls; loading and quantization belong to a separately admitted setup.
    """

    component = 'D11'

    def __init__(self, runtime):
        if getattr(runtime, 'profile', None) != PROFILE:
            raise ValueError('D11 runtime differs from pinned Log-stage2/Qwen four-bit profile')
        if getattr(runtime, 'training', False):
            raise ValueError('D11 runtime must be in inference mode')
        self.runtime = runtime

    def predict(self, rgb, K, image_valid):
        if rgb.shape != (540, 960, 3) or rgb.dtype != np.uint8:
            raise ValueError('D11 requires accepted 960x540 uint8 RGB')
        if np.asarray(K).shape != (3, 3) or not np.isfinite(K).all():
            raise ValueError('D11 requires accepted finite camera metadata')
        if image_valid.shape != rgb.shape[:2] or image_valid.dtype != np.bool_:
            raise ValueError('D11 requires accepted boolean image validity')
        raw = np.asarray(self.runtime.infer_image(rgb, seed=PROFILE['seed']))
        if raw.shape != image_valid.shape or raw.dtype != np.float32:
            raise ValueError('D11 native prediction must restore float32 to accepted grid')
        valid = image_valid & np.isfinite(raw)
        values = raw.copy()
        values[~valid] = np.nan
        return SimpleNamespace(domain='relative_log', values=values, valid=valid,
            raw_values=raw.copy(), metadata=dict(
                native_depth_type='affine-invariant log depth',
                checkpoint='depth/Log-stage2', source_revision=SOURCE_REVISION,
                adapter_revision=ADAPTER_REVISION, base_revision=BASE_REVISION,
                profile=PROFILE.copy(), native_shape=list(raw.shape),
                output_shape=list(values.shape), independent_image=True,
                metric_scale='not_applicable', downstream='blocked'))
