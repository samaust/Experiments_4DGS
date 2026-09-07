import unittest
from pathlib import Path
import sys
import numpy as np
from scipy.spatial.transform import Rotation
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_pose_stability import compare_poses,similarity


class PoseStabilityTests(unittest.TestCase):
    def test_known_similarity_preserves_camera_pose(self):
        centers=np.array([[1.,0,0],[0,2,0],[0,0,3],[-1,-1,-1]])
        rotations=Rotation.from_euler('xyz',[[0,0,0],[10,20,30],[5,6,7],[9,8,7]],degrees=True).as_matrix()
        Q=Rotation.from_euler('xyz',[10,5,20],degrees=True).as_matrix()
        shifted=centers@Q.T*3+[5,6,7]
        result=compare_poses(shifted,rotations@Q.T,centers,rotations)
        self.assertTrue(result['passed'])
        self.assertAlmostEqual(result['scale'],3)

    def test_pose_change_fails(self):
        centers=np.array([[1.,0,0],[0,2,0],[0,0,3],[-1,-1,-1]])
        rotations=np.repeat(np.eye(3)[None],4,axis=0)
        changed=rotations.copy();changed[0]=Rotation.from_euler('x',1,degrees=True).as_matrix()
        self.assertFalse(compare_poses(centers,rotations,centers,changed)['passed'])
        with self.assertRaises(ValueError): similarity(np.zeros((4,3)),np.zeros((4,3)))


if __name__=='__main__': unittest.main()
