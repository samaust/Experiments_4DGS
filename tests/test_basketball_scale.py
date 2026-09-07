import copy
import json
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_scale import scale_statistics, undistortion, protocol
from basketball_continuation_audit import TRAINING, CALIBRATION


class ScaleTests(unittest.TestCase):
    def setUp(self):
        self.p=protocol('configs/basketball-rev2/scale.json')
        self.samples=[dict(camera_id=c,ratios=np.full(200,3.),cells=8,positive_depth_fraction=1.) for c in TRAINING]

    def test_known_global_scale_with_point_outliers(self):
        for s in self.samples:
            s['ratios'][:30]=300.
        r=scale_statistics(self.samples,self.p)
        self.assertEqual(r['status'],'passed')
        self.assertAlmostEqual(r['scale'],3.)
        self.assertLess(r['relative_halfwidth'],1e-10)

    def test_camera_bias_and_reserved_drift_are_blockers(self):
        self.samples[0]['ratios']*=2
        self.assertEqual(scale_statistics(self.samples,self.p)['status'],'blocked')
        self.samples[0]['ratios']/=2
        r=scale_statistics(self.samples,self.p,frozen_scale=2.5)
        self.assertEqual(r['scale'],2.5)
        self.assertIn('reserved-frame scale disagreement exceeds frozen limit',r['blockers'])

    def test_support_leakage_and_nonfinite_rejected(self):
        self.samples[0]['cells']=2
        self.assertEqual(scale_statistics(self.samples,self.p)['status'],'blocked')
        self.samples[0]['camera_id']=0
        with self.assertRaises(ValueError):scale_statistics(self.samples,self.p)
        self.samples[0]['camera_id']=1;self.samples[0]['ratios'][0]=np.nan
        with self.assertRaises(ValueError):scale_statistics(self.samples,self.p)

    def test_actual_radial_camera_remap_matches_native_projection(self):
        import pycolmap as cm
        for e in json.loads(CALIBRATION.read_text())['cameras']:
            K,(mx,my)=undistortion(e)
            native=cm.Camera(model=e['camera_model'],params=e['parameters_colmap'],width=960,height=540)
            uv=np.array([(x,y) for x in [1,200,480,700,958] for y in [1,135,270,400,538]])
            rays=np.column_stack((uv,np.ones(len(uv))))@np.linalg.inv(K).T
            distorted=native.img_from_cam(rays)-.5
            actual=np.column_stack((mx[uv[:,1],uv[:,0]],my[uv[:,1],uv[:,0]]))
            self.assertLess(np.max(np.abs(distorted-actual)),4e-5)
            self.assertEqual(tuple(K[:2,2]),(480.,270.))


if __name__=='__main__':unittest.main()
