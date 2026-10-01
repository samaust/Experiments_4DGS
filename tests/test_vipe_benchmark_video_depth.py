"""Native offline video context stays within one camera and one role."""
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.video_depth import VideoDepthAdapter, native_window_plan


class FakeOfflineRuntime:
    encoder = 'vits'
    metric = False
    training = False

    def __init__(self):
        self.calls = []
        self.resets = []

    def reset(self, camera, role):
        self.resets.append((camera, role))

    def infer_video_depth(self, frames, target_fps, **options):
        self.calls.append((frames.shape, target_fps, options))
        return np.broadcast_to(np.float32(.4),
            (len(frames), frames.shape[1], frames.shape[2])), target_fps


class VideoDepthTests(unittest.TestCase):
    def setUp(self):
        self.runtime = FakeOfflineRuntime()
        self.adapter = VideoDepthAdapter(self.runtime, device='cpu')
        self.footprint = np.ones((540, 960), bool)
        self.footprint[0, 0] = False

    def rows(self, camera, first, last):
        return [dict(camera=camera, frame=frame,
            role='fit' if frame <= 149 else 'check', timestamp=frame / 25,
            source_rgb=dict(sha256=f'rgb-{camera}-{frame}'),
            source_video=dict(sha256=f'video-{camera}'))
            for frame in range(first, last + 1)]

    def test_native_window_boundaries_and_padding_match_pinned_offline_mode(self):
        self.assertEqual([row['start'] for row in native_window_plan(22)['windows']], [0])
        self.assertEqual([row['start'] for row in native_window_plan(32)['windows']], [0, 22])
        self.assertEqual(native_window_plan(32)['pad_frames'], 22)
        self.assertEqual(native_window_plan(32)['windows'][1]['reused_previous_keyframes'],
            [0, 12, 24, 25, 26, 27, 28, 29, 30, 31])
        self.assertEqual(native_window_plan(32)['windows'][1]['interpolated_overlap_frames'], 8)
        self.assertEqual([row['start'] for row in native_window_plan(50)['windows']], [0, 22, 44])
        self.assertEqual(native_window_plan(50)['pad_frames'], 26)
        self.assertEqual([row['start'] for row in native_window_plan(100)['windows']],
            [0, 22, 44, 66, 88])
        self.assertEqual(native_window_plan(100)['pad_frames'], 20)

    def test_role_context_reset_lineage_and_relative_values(self):
        frames = np.broadcast_to(np.zeros((1, 540, 960, 3), np.uint8),
                                 (50, 540, 960, 3))
        rows = self.rows(1, 150, 199)
        output = self.adapter.infer_context(frames, self.footprint, rows,
                                            camera=1, role='check')
        self.assertEqual(self.runtime.resets, [(1, 'check')])
        self.assertEqual(self.runtime.calls[0][1], 25)
        self.assertEqual(self.runtime.calls[0][2]['input_size'], 518)
        self.assertFalse(self.runtime.calls[0][2]['fp32'])
        self.assertEqual(output.domain, 'relative_inverse')
        self.assertEqual(output.values.shape, (50, 540, 960))
        self.assertTrue(np.isnan(output.values[0, 0, 0]))
        self.assertEqual(output.values[25, 270, 480], .4)
        self.assertEqual(output.metadata['window_plan']['windows'][-1]['start'], 44)
        self.assertEqual(output.metadata['context_frames'], list(range(150, 200)))
        changed = list(rows)
        changed[0] = dict(changed[0], source_rgb=dict(sha256='changed'))
        second = self.adapter.infer_context(frames, self.footprint, changed,
                                             camera=1, role='check')
        self.assertNotEqual(output.metadata['context_sha256'],
                            second.metadata['context_sha256'])

    def test_missing_frame_or_cross_role_context_is_rejected_before_native_call(self):
        frames = np.broadcast_to(np.zeros((1, 540, 960, 3), np.uint8),
                                 (50, 540, 960, 3))
        with self.assertRaisesRegex(ValueError, 'context identity'):
            self.adapter.infer_context(frames, self.footprint,
                self.rows(1, 150, 198), camera=1, role='check')
        with self.assertRaisesRegex(ValueError, 'context identity'):
            self.adapter.infer_context(frames, self.footprint,
                self.rows(1, 100, 149), camera=1, role='check')
        self.assertEqual(self.runtime.calls, [])


if __name__ == '__main__':
    unittest.main()
