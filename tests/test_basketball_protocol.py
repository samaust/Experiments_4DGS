import json
import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_protocol import CAMERAS, TRAINING, HELD_OUT, EXCLUDED, manifest_protocol
from basketball_vipe_pilot import fitting_frame


class ProtocolTests(unittest.TestCase):
    def test_excluded_camera_is_not_renumbered_or_loaded(self):
        self.assertEqual(len(CAMERAS),24)
        self.assertEqual(len(TRAINING),21)
        self.assertEqual(HELD_OUT,(0,10,30))
        self.assertEqual(EXCLUDED,(4,5,8,11,15,16,17,18,20,23))
        self.assertEqual(max(CAMERAS),33)
        for all_priors in [True,False]:
            for camera in EXCLUDED:
                with self.assertRaises(ValueError): fitting_frame(camera,100,all_priors=all_priors)

    def test_expected_image_counts_and_profile(self):
        protocol=manifest_protocol()
        self.assertEqual(len(CAMERAS)*50,protocol['images'])
        self.assertEqual(len(TRAINING)*50,protocol['training_images'])
        self.assertEqual(len(HELD_OUT)*50,protocol['held_out_images'])
        profile=json.loads((Path(__file__).resolve().parents[1]/'configs/scene-manifest.vru-basketball-dg.json').read_text())
        self.assertEqual({int(c['id']) for c in profile['cameras']},set(CAMERAS))
        self.assertEqual({int(c['id']) for c in profile['cameras'] if c['role']=='training'},set(TRAINING))


if __name__=='__main__': unittest.main()
