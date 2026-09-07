import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_timing_advertising import appearance_correlation, calibration_xy, check_frames, transition_tiles
from basketball_timing_advertising_package import cycle_diagnostics


class AdvertisingRecoveryTests(unittest.TestCase):
    def test_native_integer_center_conversion(self):
        np.testing.assert_allclose(calibration_xy([[959.5,539.5],[0,0]]),[[479.5,269.5],[-.25,-.25]])

    def test_content_change_terminates_but_brightness_shift_survives(self):
        rng=np.random.default_rng(3); patch=rng.normal(100,20,(15,15))
        self.assertGreater(appearance_correlation(patch,patch*1.2+10),.99)
        self.assertLess(appearance_correlation(patch,rng.normal(100,20,(15,15))),.7)
        self.assertEqual(appearance_correlation(np.ones((15,15)),np.ones((15,15))),-1)

    def test_local_change_does_not_claim_whole_display_switch(self):
        p=dict(transition_channel_difference=25,transition_tile_pixels=30,transition_changed_fraction=.5)
        before=np.zeros((60,90,3)); after=before.copy(); after[:30,:30]=100
        self.assertEqual(transition_tiles(before,after,p),[[0,0]])
        self.assertEqual(transition_tiles(before,before+10,p),[])

    def test_reserved_and_gapped_support_rejected(self):
        check_frames(list(range(50,150)))
        for f in [[49,50],[149,150],[50,52],[]]:
            with self.assertRaises(ValueError): check_frames(f)

    def test_full_rig_cycle_reports_unhidden_closure(self):
        edges=[dict(a=i,b=(i+1)%34,passed=True,lag=.3 if i==10 else 0.) for i in range(34)]
        result=cycle_diagnostics(edges)
        self.assertEqual(result['bridges'],[])
        self.assertEqual(result['reachable_cameras'],list(range(34)))
        self.assertEqual(len(result['cycles']),1)
        self.assertAlmostEqual(result['cycles'][0]['closure_frames'],.3)
        self.assertFalse(result['cycles'][0]['passed'])

    def test_connected_tree_has_no_cycle_support(self):
        edges=[dict(a=i,b=i+1,passed=True,lag=0.) for i in range(33)]
        result=cycle_diagnostics(edges)
        self.assertEqual(len(result['bridges']),33)
        self.assertEqual(result['cycles'],[])


if __name__=='__main__': unittest.main()
