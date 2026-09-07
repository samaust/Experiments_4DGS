import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_geometry import opencv_to_colmap, resize_opencv, invert_pose, training_prior_entries, connected_components
from basketball_protocol import CAMERAS, TRAINING, EXCLUDED, HELD_OUT


class GeometryTests(unittest.TestCase):
    def test_pixel_center_resize_ray_invariance(self):
        K = np.array([[850., 0, 501.3], [0, 870., 281.4], [0, 0, 1]])
        point = np.array([173.2, 293.1, 1.])
        ray = np.linalg.solve(K, point)
        self.assertTrue(np.allclose(np.linalg.solve(opencv_to_colmap(K), point+[.5,.5,0]), ray))
        scaled = (point[:2]+.5)*[.5,.6]-.5
        self.assertTrue(np.allclose(np.linalg.solve(resize_opencv(K, (1000,500), (500,300)), [*scaled,1]), ray))

    def test_pose_inversion(self):
        R = np.array([[0.,-1,0],[1,0,0],[0,0,1]])
        t = np.array([1.,2,3])
        inv_R, center = invert_pose(R, t)
        self.assertTrue(np.allclose(R @ center+t, 0))
        point = np.array([5.,6,7])
        self.assertTrue(np.allclose(inv_R @ (R @ point+t)+center, point))

    def test_training_geometry_excludes_held_out(self):
        result = {'status':'priors-generated','blockers':[], 'observations':[
            {'camera_id':c,'source_frame_id':f} for c in CAMERAS for f in [50,75,100,125,149]]}
        selected = training_prior_entries(result)
        self.assertEqual(len(selected), len(TRAINING)*5)
        self.assertFalse(set(EXCLUDED+HELD_OUT) & {e['camera_id'] for e in selected})
        result['observations'][0]['source_frame_id'] = 25
        with self.assertRaises(ValueError):
            training_prior_entries(result)

    def test_disconnected_and_unknown_camera(self):
        self.assertEqual(connected_components([1,2,3], [(1,2)]), [[1,2],[3]])
        self.assertEqual(connected_components([1,2,3], [(1,3),(3,2)]), [[1,2,3]])
        with self.assertRaises(ValueError):
            connected_components([1,2,3], [(0,1)])


if __name__ == '__main__':
    unittest.main()
