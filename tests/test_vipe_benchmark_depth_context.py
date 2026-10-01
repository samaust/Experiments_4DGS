"""The added temporal context must preserve the frozen scale-grid anchors."""
from pathlib import Path
import sys
import tempfile
import unittest

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_scale import undistortion
from vipe_benchmark.config import ROOT, load, training_cameras
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.depth_clips import prepare_context


class DepthContextTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.config = load()
        calibration = ROOT / 'docs/experiments/basketball-calibration-alternatives/calibration.json'
        cameras = {entry['camera_id']: entry for entry in read_json(calibration)['cameras']}
        image = np.full((540, 960, 3), [27, 100, 170], np.uint8)
        cv2.imwrite(str(self.root / 'distorted.png'), image)
        distorted = file_record(self.root / 'distorted.png')
        (self.root / 'source.mp4').write_bytes(b'fixture-video-identity')
        video = file_record(self.root / 'source.mp4')
        rgb, depth = [], []
        for camera in training_cameras(self.config):
            K, maps = undistortion(cameras[camera])
            remapped = cv2.remap(image, *maps, cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT)
            anchor = self.root / f'camera{camera}-anchor.png'
            cv2.imwrite(str(anchor), remapped)
            for frame in range(50, 200):
                rgb.append(dict(identity=dict(branch='calibration', camera=camera, frame=frame),
                    rgb=distorted, source_video=video, role='fit' if frame <= 149 else 'selection',
                    grid='distorted-opencv-integer'))
            for frame in (100, 175):
                depth.append(dict(identity=dict(branch='depth', camera=camera, frame=frame),
                    rgb=file_record(anchor), K=K.tolist(), grid='scale-opencv-integer'))
        self.rows = rgb
        self.inputs = dict(schema='vipe-benchmark-inputs/v1', status='prepared',
            rgb=rgb, depth=depth, source_files=[file_record(calibration), video])
        write_json(self.root / 'inputs.json', self.inputs)
        self.record = file_record(self.root / 'inputs.json')

    def tearDown(self):
        self.temporary.cleanup()

    def test_context_matches_both_anchors_and_retains_all_frames(self):
        record = prepare_context(self.record, self.root / 'context', self.config)
        context = read_json(record['path'])
        self.assertEqual(context['schema'], 'plan069-depth-context/v1')
        self.assertEqual(context['inputs'], self.record)
        self.assertEqual(len(context['rows']), 30 * 150)
        self.assertEqual(len(context['anchors']), 60)
        self.assertEqual(context['roles']['fit'], [50, 149])
        self.assertEqual(context['roles']['check'], [150, 199])
        self.assertEqual({row['camera'] for row in context['rows']},
                         set(training_cameras(self.config)))
        self.assertEqual(context['anchors'][0]['remapped_sha256'],
                         context['anchors'][0]['accepted_rgb']['sha256'])

    def test_missing_context_and_changed_anchor_are_rejected(self):
        missing = dict(self.inputs, rgb=self.rows[:-1])
        write_json(self.root / 'missing.json', missing)
        with self.assertRaisesRegex(ValueError, 'context membership'):
            prepare_context(file_record(self.root / 'missing.json'), self.root / 'missing', self.config)
        changed_depth = list(self.inputs['depth'])
        cv2.imwrite(str(self.root / 'wrong-anchor.png'), np.zeros((540, 960, 3), np.uint8))
        changed_depth[0] = dict(changed_depth[0], rgb=file_record(self.root / 'wrong-anchor.png'))
        write_json(self.root / 'changed.json', dict(self.inputs, depth=changed_depth))
        with self.assertRaisesRegex(ValueError, 'anchor bytes'):
            prepare_context(file_record(self.root / 'changed.json'), self.root / 'changed', self.config)


if __name__ == '__main__':
    unittest.main()
