import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_eval_masks import motion_region

class RegionTests(unittest.TestCase):
    def test_static_scene_and_compression_noise_have_no_region(self):
        bg=np.full((100,100,3),100,dtype=np.uint8)
        mask,bbox=motion_region(bg+20,bg)
        self.assertIsNone(bbox);self.assertEqual(mask.sum(),0)

    def test_motion_crop_is_bounded_and_preserves_foreground(self):
        bg=np.zeros((100,100,3),np.uint8);image=bg.copy();image[30:50,40:60]=200
        mask,bbox=motion_region(image,bg)
        self.assertEqual(bbox,[32,22,68,58]);self.assertEqual(mask.sum(),400)
        image=bg.copy();image[:10,:10]=200
        _,bbox=motion_region(image,bg)
        self.assertEqual(bbox,[0,0,32,32])
