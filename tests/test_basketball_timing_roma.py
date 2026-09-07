import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_timing_roma import select_seeds, follow
from basketball_scale import read


class DenseTimingTests(unittest.TestCase):
    def test_confidence_sampling_deduplicates_time_hypotheses(self):
        p=read('configs/basketball-rev2/timing-recovery.json')
        proposals=[dict(xy_a=[20.,20.],xy_b=[30.,30.],confidence=.96,target_frame=75),
                   dict(xy_a=[21.,21.],xy_b=[40.,40.],confidence=.99,target_frame=100),
                   dict(xy_a=[45.,45.],xy_b=[60.,60.],confidence=.97,target_frame=125)]
        selected=select_seeds(proposals,p)
        self.assertEqual(len(selected),2)
        self.assertEqual(selected[0]['target_frame'],100)

    def test_bidirectional_tracks_preserve_original_frame_indices(self):
        import cv2
        cv2.setNumThreads(1)
        rng=np.random.default_rng(0)
        base=rng.integers(0,256,(96,96),dtype=np.uint8)
        images=[cv2.warpAffine(base,np.array([[1,0,.15*(f-100)],[0,1,0]],np.float32),(96,96)) for f in range(50,150)]
        p=read('configs/basketball-rev2/timing-recovery.json')
        xy=follow(images,75,[[48+.15*(75-100),48]],p)[0]
        self.assertTrue(np.isfinite(xy).all())
        self.assertLess(np.max(np.abs(xy[:,0]-(48+.15*(np.arange(50,150)-100)))),.3)
        self.assertLess(np.max(np.abs(xy[:,1]-48)),.3)


if __name__=='__main__':unittest.main()
