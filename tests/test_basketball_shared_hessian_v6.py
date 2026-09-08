import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_solver_v6 import ConstrainedProblem,exact_objective_hessian,projection_second,EvaluationLimit
from basketball_shared_diagnose_v5 import fixture
from basketball_shared_spline_v2 import project_jacobian

class ExactHessianTests(unittest.TestCase):
    def test_distorted_rotated_projection_second(self):
        p=fixture(2,-7.,1.,lambda:None);camera=dict(p.cameras[3]);theta=.2
        camera['R']=np.array([[np.cos(theta),0,np.sin(theta)],[0,1,0],[-np.sin(theta),0,np.cos(theta)]])
        camera['parameters_colmap']=list(camera['parameters_colmap']);camera['parameters_colmap'][3]=.07
        xyz=np.array([[.2,.3,4.],[.3,-.2,5.]])
        pred,J,H=projection_second(xyz,camera,p.center,p.diameter)
        original,P,_=project_jacobian(xyz,camera,p.center,p.diameter)
        np.testing.assert_allclose(pred,original);np.testing.assert_allclose(J,P)
        for j in range(3):
            d=np.zeros_like(xyz);d[:,j]=1
            for h in [1e-4,1e-5,1e-6]:
                fd=(project_jacobian(xyz+h*d,camera,p.center,p.diameter)[1]-project_jacobian(xyz-h*d,camera,p.center,p.diameter)[1])/(2*h)
                np.testing.assert_allclose(fd,H[:,:,:,j],rtol=1e-6,atol=1e-7)

    def test_full_hessian_all_blocks_weights_and_knot_near(self):
        for weight in [0.,1.]:
            p=fixture(2,-7.,weight,lambda:None)
            for c in p.cameras.values():
                c['parameters_colmap']=list(c['parameters_colmap']);c['parameters_colmap'][3]=.02
            a=ConstrainedProblem(p);q=p.x0/a.scale;q[0]=.04+1e-9
            H=a.hess(q).toarray();r,J=a.evaluate(q)
            np.testing.assert_allclose(H,H.T,atol=1e-10)
            self.assertGreater(np.max(np.abs(H-2*(J.T@J).toarray())),1e-4)
            estimates=[]
            for h in [1e-4,1e-5,1e-6]:
                fd=np.empty_like(H)
                for j in range(len(q)):
                    v=np.eye(len(q))[j]
                    # Direct immutable gradient, not the solver's counted cache.
                    def gradient(q):
                        rr,JJ=p.evaluate(q*a.scale);return np.asarray(2*(JJ@a.D).T@rr).ravel()
                    fd[:,j]=(gradient(q+h*v)-gradient(q-h*v))/(2*h)
                estimates.append(fd)
                if h<=1e-5:np.testing.assert_allclose(fd,H,rtol=3e-5,atol=2e-5)
            self.assertLess(np.max(np.abs(estimates[-1]-H)),np.max(np.abs(estimates[0]-H)))
            np.testing.assert_allclose(estimates[-1],estimates[-2],rtol=3e-5,atol=2e-5)
            np.testing.assert_array_equal(r,p.evaluate(q*a.scale)[0])

    def test_acceleration_exact_linear_and_no_penalty_at_zero(self):
        p=fixture(2,-7.,0.,lambda:None);a=ConstrainedProblem(p);q=p.x0/a.scale
        H0=exact_objective_hessian(p,q*a.scale).toarray();p.weight=1.
        H1=exact_objective_hessian(p,q*a.scale).toarray();expected=np.zeros_like(H0)
        expected[1:,1:]=np.kron(2/p.nacc*p.accel.T@p.accel,np.eye(3))
        np.testing.assert_allclose(H1-H0,expected,rtol=1e-11,atol=1e-11)
        z=np.zeros(len(q));z[3::3]=1
        np.testing.assert_allclose(expected@z,0,atol=1e-12)

    def test_hessian_first_cap_cache_and_deadline(self):
        p=fixture(2,-7.,0.,lambda:None);a=ConstrainedProblem(p);q=p.x0/a.scale
        with patch('basketball_shared_solver_v6.MAX_EVALUATIONS',2):
            a.hess(q);a.jac(q);a.fun(q);a.hess(q)
            self.assertEqual(a.evaluations,1);self.assertEqual(a.hessian_assemblies,1)
            a.hess(q+1e-8);self.assertEqual(a.evaluations,2)
            with self.assertRaises(EvaluationLimit):a.hess(q+2e-8)
        def expired():raise TimeoutError('deadline')
        p.check=expired
        with self.assertRaises(TimeoutError):a.hess(q)

if __name__=='__main__':unittest.main()
