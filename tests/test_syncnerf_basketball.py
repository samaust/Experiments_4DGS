import sys
from pathlib import Path
import unittest
from unittest.mock import patch
import numpy as np
import torch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from syncnerf_basketball import Rays, export_offsets


class RayAndTimingTests(unittest.TestCase):
    def test_normalized_shift_sign_and_gauge(self):
        seconds=np.array([0.,.013,-.02,.04,0.,.001,.02,-.08])
        native=-seconds*1.6/3.96+.07
        np.testing.assert_allclose(export_offsets(native),seconds,atol=1e-12)
        np.testing.assert_allclose(export_offsets(native+10),seconds,atol=1e-12)
        with self.assertRaises(ValueError):export_offsets([np.nan]*8)

    def test_sampled_world_ray_reprojects_to_source_pixel(self):
        rays=Rays.__new__(Rays);rays.torch=torch;rays.batch_size=2
        rays.origins=np.tile(np.array([[2.,3.,4.]],np.float32),(8,1))
        rotation=np.array([[0.,-1.,0.],[1.,0.,0.],[0.,0.,1.]],np.float32)
        rays.rotations=np.tile(rotation[None],(8,1,1))
        K=np.array([[800.,0.,480.],[0.,800.,270.],[0.,0.,1.]],np.float32)
        rays.intrinsics=np.tile(K[None],(8,1,1));rays.far=100.
        rays.images=np.broadcast_to(np.array([12,45,99],np.uint8),(8,100,540,960,3))
        x=np.array([0,959]);y=np.array([0,539])
        with patch.object(np.random,'randint',side_effect=[np.array([0,7]),np.array([0,99]),x,y]):
            batch=next(rays)
        d=batch['rays_d'].numpy();np.testing.assert_allclose(np.linalg.norm(d,axis=1),1,atol=1e-6)
        camera=d@rotation.T;pixel=camera@K.T;pixel=pixel[:,:2]/pixel[:,2:]
        np.testing.assert_allclose(pixel,np.stack((x+.5,y+.5),-1),atol=1e-4)
        np.testing.assert_allclose(batch['timestamps'],[-.8,.8],atol=1e-7)
        np.testing.assert_allclose(batch['imgs'],np.tile(np.array([12,45,99])/255,(2,1)),atol=1e-7)
