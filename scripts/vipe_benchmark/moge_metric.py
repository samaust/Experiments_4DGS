"""Supplied-FoV MoGe metric point-map restoration for D5 and later D6/D8."""
import math
from types import SimpleNamespace

import cv2
import numpy as np


def supplied_horizontal_fov(K, width, height):
    """Derive native MoGe's degree-valued horizontal FoV on its centered grid."""
    matrix = np.asarray(K, np.float64)
    if (matrix.shape != (3, 3) or not np.isfinite(matrix).all() or
            not np.allclose(matrix, [[matrix[0, 0], 0, width / 2],
                                     [0, matrix[0, 0], height / 2],
                                     [0, 0, 1]], rtol=0, atol=1e-6) or matrix[0, 0] <= 0):
        raise ValueError('supplied FoV requires accepted centered pinhole intrinsics')
    return 2 * math.degrees(math.atan(width / (2 * matrix[0, 0])))


def restore_pointmap(points, depth, native_valid, shape, image_valid):
    """Restore camera-z without admitting any invalid bilinear contributors."""
    points = np.asarray(points, np.float32)
    depth = np.asarray(depth, np.float32)
    native_valid = np.asarray(native_valid)
    image_valid = np.asarray(image_valid)
    if (points.ndim != 3 or points.shape[-1] != 3 or depth.shape != points.shape[:2] or
            native_valid.shape != depth.shape or native_valid.dtype != np.bool_ or
            image_valid.shape != shape or image_valid.dtype != np.bool_):
        raise ValueError('native point/depth/valid grid mismatch')
    native_valid = native_valid & np.isfinite(depth) & (depth > 0) & np.isfinite(points).all(axis=-1)
    if native_valid.any() and not np.allclose(points[..., 2][native_valid], depth[native_valid],
                                               rtol=1e-3, atol=1e-4):
        raise ValueError('native point-map camera-z differs from native depth')
    if depth.shape == shape:
        restored_depth = depth.copy()
        restored_points = points.copy()
        restored_valid = native_valid.copy()
        resized = False
    else:
        size = (shape[1], shape[0])
        restored_depth = cv2.resize(np.where(native_valid, depth, 0), size,
                                    interpolation=cv2.INTER_LINEAR)
        restored_points = cv2.resize(np.where(native_valid[..., None], points, 0), size,
                                     interpolation=cv2.INTER_LINEAR)
        support = cv2.resize(native_valid.astype(np.float32), size,
                             interpolation=cv2.INTER_LINEAR)
        restored_valid = support >= 1 - 1e-6
        resized = True
    restored_valid &= image_valid & np.isfinite(restored_depth) & (restored_depth > 0)
    restored_valid &= np.isfinite(restored_points).all(axis=-1)
    values = restored_depth.astype(np.float32)
    values[~restored_valid] = np.nan
    restored_points = restored_points.astype(np.float32)
    restored_points[~restored_valid] = np.nan
    return SimpleNamespace(values=values, valid=restored_valid,
        points=restored_points, resized=resized,
        native_shape=list(depth.shape), output_shape=list(shape))


def _array(value):
    if hasattr(value, 'detach'):
        value = value.detach().cpu().numpy()
    return np.asarray(value)


def _supplied_native_intrinsics(native, K, width, height, label):
    if 'intrinsics' not in native:
        raise ValueError(f'{label} supplied camera intrinsics missing')
    observed = _array(native['intrinsics'])
    expected = np.array([[K[0, 0] / width, 0, .5],
                         [0, K[1, 1] / height, .5], [0, 0, 1]], np.float32)
    if observed.shape != (3, 3) or not np.allclose(observed, expected,
                                                   rtol=1e-4, atol=1e-5):
        raise ValueError(f'{label} returned a predicted camera instead of supplied camera')


class MoGe2Adapter:
    """Call the pinned v2 native `infer` once per accepted scale-grid RGB frame."""
    def __init__(self, runtime):
        if getattr(runtime, 'training', False):
            raise ValueError('MoGe-2 native runtime must be in eval mode')
        self.runtime = runtime
        self.component = 'D5'

    def _infer(self, image, fov):
        return self.runtime.infer(image, fov_x=fov, resolution_level=9,
            force_projection=True, apply_mask=True, use_fp16=True)

    def _validate_native(self, native, K, width, height):
        _supplied_native_intrinsics(native, K, width, height, 'MoGe-2')

    def predict(self, rgb, K, image_valid):
        import torch
        if rgb.shape != (540, 960, 3) or rgb.dtype != np.uint8:
            raise ValueError('D5 requires accepted 960x540 uint8 RGB')
        fov = supplied_horizontal_fov(K, rgb.shape[1], rgb.shape[0])
        image = torch.from_numpy(np.ascontiguousarray(rgb)).permute(2, 0, 1).float().div(255)
        native = self._infer(image, fov)
        if not {'points', 'depth', 'mask'} <= set(native):
            raise ValueError('native MoGe-2 point/depth/mask outputs required')
        self._validate_native(native, K, rgb.shape[1], rgb.shape[0])
        points = _array(native['points']).astype(np.float32)
        depth = _array(native['depth']).astype(np.float32)
        mask = _array(native['mask'])
        if mask.dtype != np.bool_:
            raise ValueError('native MoGe-2 mask must be boolean')
        restored = restore_pointmap(points, depth, mask, rgb.shape[:2], image_valid)
        if restored.resized:
            raise ValueError('MoGe-2 native infer must restore to the supplied input grid')
        return SimpleNamespace(domain='camera_z_metres', values=restored.values,
            valid=restored.valid, raw_values=depth, native_points=points,
            metadata=dict(native_depth_type='camera-z metres', conversion_count=0,
                fov_x_degrees=fov, native_shape=restored.native_shape,
                output_shape=restored.output_shape, native_point_map=True,
                native_mask=True, input_normalization='RGB float32 / 255; CHW',
                native_resolution_level=9, native_force_projection=True,
                native_apply_mask=True, native_use_fp16=True,
                native_resize='internal interpolation to input grid; no adapter pad/crop',
                seed_policy='eval inference; no stochastic sampling'))


class MoGe3Adapter(MoGe2Adapter):
    """Pinned v3 model with supplied FoV and exactly three sparse refinements."""
    def __init__(self, runtime):
        super().__init__(runtime)
        self.component = 'D6'

    def _infer(self, image, fov):
        return self.runtime.infer(image, fov_x=fov, resolution_level=9,
            force_projection=True, apply_mask=True, refine_steps=3,
            return_per_step=False, use_fp16=False)

    def _validate_native(self, native, K, width, height):
        _supplied_native_intrinsics(native, K, width, height, 'MoGe-3')

    def predict(self, rgb, K, image_valid):
        output = super().predict(rgb, K, image_valid)
        if not output.valid.any():
            raise ValueError('MoGe-3 returned no valid metric depth')
        output.metadata.update(native_refine_steps=3, native_return_per_step=False,
                               native_use_fp16=False, component='D6')
        return output


POINTMAP_PIN = ('yjh001/metricanything_student_pointmap@'
                '8f1f08c53c683d4e19864601dfaf78515f29a63b')


class MetricAnythingPointMapAdapter(MoGe2Adapter):
    """MetricAnything's bundled MoGe-2 student and exact PointMap weights."""
    def __init__(self, runtime, checkpoint_identity):
        if checkpoint_identity != POINTMAP_PIN:
            raise ValueError('D8 requires exact MetricAnything Student PointMap checkpoint')
        super().__init__(runtime)
        self.component = 'D8'
        self.checkpoint_identity = checkpoint_identity

    def _validate_native(self, native, K, width, height):
        _supplied_native_intrinsics(native, K, width, height, 'MetricAnything PointMap')

    def predict(self, rgb, K, image_valid):
        output = super().predict(rgb, K, image_valid)
        output.metadata.update(component='D8', checkpoint_identity=self.checkpoint_identity,
            bundled_runtime='MetricAnything student_pointmap/moge/model/v2.py')
        return output
