import sys
import unittest
from pathlib import Path
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_timing_clock import green_chroma, detect_regions, change_signal, lag_curve, validate_protocol
from basketball_scale import read


class ClockTests(unittest.TestCase):
    def setUp(self):
        self.p=read(Path(__file__).resolve().parents[1]/'configs/basketball-rev2/timing-clock.json')

    def test_green_display_not_white_or_red(self):
        np.testing.assert_allclose(green_chroma([[[0,200,0],[200,200,200],[0,0,200]]]),[[200,0,0]])

    def test_automatic_region_and_content_changes(self):
        image=np.zeros((1080,1920,3),np.uint8);image[80:100,100:180,1]=200
        regions=detect_regions(image,self.p)
        self.assertEqual(regions[0]['green_pixels'],1600)
        signal=change_signal([image[:120,:200],image[:120,:200],np.zeros((120,200,3),np.uint8)])
        self.assertEqual(signal[0],0);self.assertGreater(signal[1],0)

    def test_integer_lag_sign_and_no_fractional_claim(self):
        rng=np.random.default_rng(8);a=rng.uniform(0,20,99);b=rng.uniform(0,20,99);b[3:]=a[:-3]
        result=lag_curve(a,b,self.p)
        self.assertEqual(result['lag_frames'],3)
        self.assertFalse(result['fractional_timing_validated'])
        self.assertEqual(result['bootstrap_95_integer_frames'],[3,3])

    def test_dark_display_filter_rejects_court_logo(self):
        p=read(Path(__file__).resolve().parents[1]/'configs/basketball-rev2/timing-clock-display.json')
        image=np.full((1080,1920,3),180,np.uint8)
        image[80:100,900:1100]=[70,160,70]
        image[70:115,90:260]=0
        image[80:100,100:140]=[0,200,0]
        regions=detect_regions(image,p)
        self.assertEqual(len(regions),1)
        self.assertLess(regions[0]['box'][0],200)

    def test_periodicity_is_ambiguous(self):
        signal=np.tile([0.,20.,0.,0.,20.],20)[:99]
        result=lag_curve(signal,signal,self.p)
        self.assertAlmostEqual(result['gap_to_other_integer'],0.)

    def test_role_boundary_and_weak_signal(self):
        signal=np.zeros(99)
        self.assertEqual(lag_curve(signal,signal,self.p)['status'],'unsupported')
        self.p['reference_transition_frames']=[75,124]
        with self.assertRaises(ValueError):lag_curve(signal,signal,self.p)

    def test_detection_frame_cannot_open_reserved_data(self):
        validate_protocol(self.p)
        for f in [49,150,200]:
            self.p['detection_frame']=f
            with self.assertRaises(ValueError):validate_protocol(self.p)


if __name__=='__main__':unittest.main()
