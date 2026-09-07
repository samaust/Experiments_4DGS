import json
import sys
import tempfile
from pathlib import Path
import unittest
import numpy as np
from scipy.spatial.transform import Rotation

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_alternatives_compare import load_export, frozen_errors
from basketball_geometry import invert_pose, resize_opencv
from basketball_alternatives_learned import project_rotations
from basketball_alternatives_refine import deduplicate


class AlternativeGeometryTests(unittest.TestCase):
    def test_repeated_observations_do_not_cross_bin_boundary(self):
        observations=[dict(xy=[1.9,4.],frame=50),dict(xy=[2.1,4.],frame=75),dict(xy=[8.,4.],frame=99)]
        selected=deduplicate(observations)
        self.assertEqual([p['frame'] for p in selected],[50,99])

    def test_rotation_drift_projection_preserves_center_and_rejects_scale(self):
        R=np.eye(3)[None]*1.0002
        C=np.array([[1.,2,3]])
        t=-np.einsum('nij,nj->ni',R,C)
        repaired,translation,drift=project_rotations(R,t)
        self.assertGreater(drift,0)
        self.assertTrue(np.allclose(-np.einsum('nji,nj->ni',repaired,translation),C))
        self.assertAlmostEqual(np.linalg.det(repaired[0]),1.)
        with self.assertRaises(ValueError):
            project_rotations(R*2,t)

    def test_held_out_uses_training_transform_without_refit(self):
        Q=Rotation.from_euler('xyz',[10,20,30],degrees=True).as_matrix()
        C=np.array([[2.,3,4],[4.,5,6]])
        R=np.repeat(np.eye(3)[None],2,axis=0)
        transform=(3.,Q,np.array([8.,9,10]))
        aligned=3*C@Q.T+transform[2]
        angles,errors=frozen_errors((aligned,R@Q.T),(C,R),transform,20.)
        self.assertLess(max(angles),1e-10)
        self.assertLess(max(errors),1e-10)
        changed=C.copy();changed[0,0]+=1
        _,errors=frozen_errors((aligned,R@Q.T),(changed,R),transform,20.)
        self.assertAlmostEqual(errors[0],.15)
        self.assertAlmostEqual(errors[1],0.)

    def test_resize_crop_inverse_and_reloaded_reprojection(self):
        K=np.array([[900.,0,479.5],[0,880.,269.5],[0,0,1.]])
        resized=resize_opencv(K,(960,540),(512,288))
        crop=resized.copy();crop[:2,2]-=[8,12]
        uncropped=crop.copy();uncropped[:2,2]+=[8,12]
        self.assertTrue(np.allclose(resize_opencv(uncropped,(512,288),(960,540)),K))
        R=Rotation.from_euler('y',15,degrees=True).as_matrix();t=np.array([1.,2,3])
        Rc,C=invert_pose(R,t)
        self.assertTrue(np.allclose(invert_pose(Rc,C)[1],t))
        value=dict(image_size=[960,540],pose_convention='world-to-camera',
                   pixel_convention='opencv-integer-centers',cameras=[
                       dict(camera_id=19,R=R.tolist(),t=t.tolist(),K=K.tolist(),center=C.tolist())])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'calibration.json';path.write_text(json.dumps(value))
            centers,rotations=load_export(path,expected=(19,))
            points=np.array([[0.,0,5],[1.,2,8],[-2.,1,7]])
            project=lambda rot,trans,k: (points@rot.T+trans)@k.T
            p1=project(R,t,K);p2=project(rotations[0],-rotations[0]@centers[0],np.array(json.loads(path.read_text())['cameras'][0]['K']))
            self.assertTrue(np.allclose(p1[:,:2]/p1[:,2:],p2[:,:2]/p2[:,2:]))
            value['cameras'][0]['K'][0][0]=-1
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'camera 19'):
                load_export(path,expected=(19,))


if __name__=='__main__':
    unittest.main()
