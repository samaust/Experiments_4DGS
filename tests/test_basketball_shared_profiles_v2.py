import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_spline_v2 import profile_group


class ActualIndependentProfileTests(unittest.TestCase):
    def test_actual_full_range_independent_group_profile(self):
        groups,cameras,truth,window=synthetic(motion='constant_velocity',delta=.25,groups=1)
        grid=np.unique(np.r_[np.arange(-25,26),np.arange(0,.501,.05)])
        for weight in [.1,0.]:
            result=profile_group(groups[0],cameras,dict(a=1,b=2),window,10,weight,grid)
            self.assertFalse(result['failures'])
            lag=grid[np.argmin(result['costs'])]
            self.assertLessEqual(abs(lag-truth[2]),.05)
            self.assertTrue(all(r['converged'] for r in result['optimizer_traces']))

    def test_parallel_group_curves_equal_serial(self):
        from concurrent.futures import ProcessPoolExecutor
        import multiprocessing
        from basketball_shared_spline_v2 import profile_job
        groups,cameras,_,window=synthetic(groups=2)
        payloads=[(g,cameras,dict(a=1,b=2),window,10,.1,[-25.,0.,.25,25.],None) for g in groups]
        serial=[profile_job(p) for p in payloads]
        with ProcessPoolExecutor(max_workers=2,mp_context=multiprocessing.get_context('spawn')) as pool:
            parallel=list(pool.map(profile_job,payloads))
        self.assertEqual(serial,parallel)

    def test_noisy_outlier_model_and_fixed_source_support(self):
        from basketball_shared_spline_v2 import fit_trajectories
        for noise in [.25,.5]:
            groups,cameras,truth,window=synthetic(noise=noise,delta=-.25,groups=3,outliers=True)
            fit=fit_trajectories(groups,cameras,{c:0. for c in cameras},window,10,.1)
            self.assertTrue(fit['converged'])
            self.assertLessEqual(abs(fit['offsets'][2]-truth[2]),.25)
        original=synthetic(delta=0,groups=1)[0][0]['observations']
        for delta in [-.75,-.25,-.1,0,.1,.25,.75]:
            shifted=synthetic(delta=delta,groups=1)[0][0]['observations']
            for a,b in zip(original,shifted):np.testing.assert_array_equal(a['frames'],b['frames'])


if __name__=='__main__':unittest.main()
