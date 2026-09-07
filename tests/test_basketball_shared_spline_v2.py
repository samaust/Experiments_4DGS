import copy
import inspect
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_spline_v2 import (SplineProblem,fit_trajectories,robust_residual_jacobian,project_jacobian,
    clip_groups,estimate_held_out,profile_group,independent_edge,curve_summary,independent_cycles,InsufficientSupport)
from basketball_shared_synthetic_v2 import synthetic


class SharedSplineTests(unittest.TestCase):
    def test_actual_sparse_analytic_jacobian(self):
        groups,cameras,_,window=synthetic(groups=1,length=25)
        p=SplineProblem(groups,cameras,{c:0. for c in cameras},window,10,.1,(1,))
        x=p.x0.copy(); _,J=p.evaluate(x)
        for index in [0,1,2,15,30,len(x)-1]:
            h=1e-6;plus=x.copy();minus=x.copy();plus[index]+=h;minus[index]-=h
            expected=(p.evaluate(plus)[0]-p.evaluate(minus)[0])/(2*h)
            np.testing.assert_allclose(J[:,index].toarray().ravel(),expected,atol=2e-7,rtol=2e-5)

    def test_soft_l1_before_normalization_and_quadratic_acceleration(self):
        errors=np.array([[0.,0.],[2.,-3.]])
        r,_=robust_residual_jacobian(errors,2)
        self.assertAlmostEqual(float(np.sum(r*r)),float(np.mean(2*(np.sqrt(1+np.sum(errors**2,axis=1))-1))))
        duplicate=np.tile(errors,(2,1)); rr,_=robust_residual_jacobian(duplicate,4)
        self.assertAlmostEqual(float(np.sum(r*r)),float(np.sum(rr*rr)))
        g,c,_,w=synthetic(groups=1,length=25)
        a=SplineProblem(g,c,{c:0 for c in c},w,10,1,(1,));b=SplineProblem(g,c,{c:0 for c in c},w,10,10,(1,))
        ra=a.evaluate(a.x0)[0][2*a.n:];rb=b.evaluate(b.x0)[0][2*b.n:]
        np.testing.assert_allclose(rb,np.sqrt(10)*ra,atol=1e-12)

    def test_known_fractional_offset_and_identifiable_constant_velocity(self):
        for motion in ['constant_velocity','acceleration','direction_changes']:
            for delta in [-.75,-.25,-.1,0,.1,.25,.75]:
                groups,cameras,truth,window=synthetic(motion=motion,delta=delta,groups=1)
                result=fit_trajectories(groups,cameras,{c:0. for c in cameras},window,10,.1)
                self.assertTrue(result['converged'],result['message'])
                self.assertLessEqual(abs(result['offsets'][2]-truth[2]),.05)

    def test_projection_pose_distortion_derivative(self):
        camera=json.loads(Path('docs/experiments/basketball-calibration-alternatives/calibration.json').read_text())['cameras'][7]
        xyz=(np.array([[.2,.3,3.]])-camera['t'])@np.array(camera['R'])
        _,J,_=project_jacobian(xyz,camera,np.zeros(3),1.)
        for i in range(3):
            d=np.zeros((1,3));d[0,i]=1e-6
            expected=(project_jacobian(xyz+d,camera,np.zeros(3),1.)[0]-project_jacobian(xyz-d,camera,np.zeros(3),1.)[0])/(2e-6)
            np.testing.assert_allclose(J[:,:,i],expected,atol=1e-6)

    def test_initialization_role_clipping_and_missing_support(self):
        groups,cameras,_,_=synthetic(groups=1)
        clipped=clip_groups(groups,[75,99],{1,2,3})
        self.assertTrue(all(min(o['frames'])==75 and max(o['frames'])==99 for o in clipped[0]['observations']))
        with self.assertRaises(ValueError):SplineProblem(groups,cameras,{c:0 for c in cameras},[75,99],10,1,(1,))
        with self.assertRaises(InsufficientSupport):SplineProblem(clip_groups(groups,[75,77]),cameras,{c:0 for c in cameras},[75,77],10,1,(1,))

    def test_held_out_observations_cannot_modify_training_fit(self):
        groups,cameras,_,window=synthetic(groups=1,held_out=True)
        training=clip_groups(groups,window,{1,2,3})
        fit=fit_trajectories(training,cameras,{c:0. for c in [1,2,3]},window,10,.1)
        before=json.dumps(fit,sort_keys=True)
        result=estimate_held_out(groups,cameras,fit,held_out=(0,))
        self.assertEqual(before,json.dumps(fit,sort_keys=True))
        self.assertEqual(result[0]['status'],'passed')
        self.assertLess(abs(result[0]['offset']-.1),.05)

    def test_independent_api_and_regularization_only_confidence(self):
        self.assertFalse({'production_offsets','production_fit','candidate'}&set(inspect.signature(independent_edge).parameters))
        grid=np.round(np.arange(-25,25.001,.05),8)
        regularized=np.tile((grid-.25)**2,(12,1));flat=np.ones_like(regularized)
        self.assertTrue(curve_summary(regularized,grid)['passed'])
        self.assertFalse(curve_summary(flat,grid)['passed'])
        groups,cameras,_,window=synthetic(groups=12)
        def mock_profile(group,cameras,edge,window,spacing,weight,grid,check):
            return dict(group_id=group['group_id'],costs=[(v-.25)**2 if weight else 1. for v in grid],failures=[])
        with patch('basketball_shared_spline_v2.profile_group',side_effect=mock_profile):
            result=independent_edge(groups,cameras,dict(a=1,b=2),window,10,10)
        self.assertFalse(result['passed']);self.assertTrue(result['profiles']['regularized']['passed'])
        self.assertFalse(result['profiles']['data_only']['passed'])

    def test_missing_evidence_and_inconsistent_independent_cycles(self):
        grid=np.arange(-25,26)
        self.assertFalse(curve_summary([],grid)['passed'])
        curves=np.tile(grid**2,(12,1)).astype(float);curves[0,0]=np.nan
        self.assertFalse(curve_summary(curves,grid)['passed'])
        edges=[dict(a=1,b=2,lag=.1),dict(a=2,b=3,lag=.1),dict(a=1,b=3,lag=.6)]
        self.assertFalse(independent_cycles(edges,[1,2,3])['passed'])


if __name__=='__main__':unittest.main()
