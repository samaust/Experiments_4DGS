import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('initialize_selfcap',
    Path(__file__).resolve().parents[1] / 'scripts/initialize-selfcap.py')
initialization = importlib.util.module_from_spec(spec)
spec.loader.exec_module(initialization)


class InitializationFrameTests(unittest.TestCase):
    def manifest(self):
        return dict(schema='selfcap-processed/v1', status='prepared', cameras=[
            dict(id=f'{i:04d}', split='test' if i == 15 else 'train',
                 frames=[dict(frame_id=f) for f in (4120, 4150, 4179)])
            for i in range(24)])

    def test_selected_frame_and_exclusion(self):
        for frame in (4120, 4150, 4179):
            selected = initialization.select_training_frames(self.manifest(), frame)
            self.assertEqual(len(selected), 23)
            self.assertTrue(all(c['id'] != '0015' and f['frame_id'] == frame for c, f in selected))

    def test_invalid_frame_or_split_rejected(self):
        for frame in (4119, 4180):
            with self.assertRaisesRegex(ValueError, 'window'):
                initialization.select_training_frames(self.manifest(), frame)
        data = self.manifest()
        data['cameras'][0]['id'] = '0001'
        with self.assertRaisesRegex(ValueError, 'split'):
            initialization.select_training_frames(data, 4150)

    def test_missing_and_duplicate_frames_rejected(self):
        data = self.manifest()
        data['cameras'][0]['frames'] = []
        with self.assertRaisesRegex(ValueError, 'missing or duplicated'):
            initialization.select_training_frames(data, 4150)
        data['cameras'][0]['frames'] = [dict(frame_id=4150)] * 2
        with self.assertRaisesRegex(ValueError, 'missing or duplicated'):
            initialization.select_training_frames(data, 4150)
