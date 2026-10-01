"""D10 metric offline output is camera z and skips relative alignment."""
from pathlib import Path
import math
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.video_depth import MetricVideoDepthAdapter


class FakeMetricVideo:
    encoder = 'vits'
    metric = True
    training = False

    def __init__(self, value=4.):
        self.value = value
        self.calls = []

    def infer_video_depth(self, frames, target_fps, **options):
        self.calls.append((len(frames), options))
        return np.broadcast_to(np.float32(self.value), frames.shape[:3]), target_fps


class MetricVideoTests(unittest.TestCase):
    def rows(self):
        return [dict(camera=1, frame=frame, role='check', timestamp=frame / 25,
            source_rgb=dict(sha256=str(frame)), source_video=dict(sha256='video'))
            for frame in range(150, 200)]

    def test_off_axis_known_z_stays_four_metres_without_ray_conversion(self):
        runtime = FakeMetricVideo()
        adapter = MetricVideoDepthAdapter(runtime, device='cpu')
        frames = np.broadcast_to(np.zeros((1, 540, 960, 3), np.uint8),
                                 (50, 540, 960, 3))
        result = adapter.infer_context(frames, np.ones((540, 960), bool),
                                       self.rows(), camera=1, role='check')
        self.assertEqual(result.domain, 'camera_z_metres')
        self.assertEqual(result.values[25, 270, 800], 4.)
        self.assertNotEqual(result.values[25, 270, 800], math.hypot(3, 4))
        self.assertEqual(result.metadata['conversion_count'], 0)
        self.assertEqual(result.metadata['native_metric_overlap_alignment'], 'identity')
        self.assertFalse(result.metadata['window_plan']['windows'][1]['relative_alignment'])
        self.assertEqual(runtime.calls[0][0], 50)

    def test_wrong_checkpoint_mode_and_invalid_metric_output_fail(self):
        runtime = FakeMetricVideo()
        runtime.metric = False
        with self.assertRaisesRegex(ValueError, 'metric'):
            MetricVideoDepthAdapter(runtime, device='cpu')
        frames = np.broadcast_to(np.zeros((1, 540, 960, 3), np.uint8),
                                 (50, 540, 960, 3))
        with self.assertRaisesRegex(ValueError, 'metric camera-z'):
            MetricVideoDepthAdapter(FakeMetricVideo(value=np.nan), device='cpu').infer_context(
                frames, np.ones((540, 960), bool), self.rows(), camera=1, role='check')


if __name__ == '__main__':
    unittest.main()
