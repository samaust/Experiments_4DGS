import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_solver_v4 import ConstrainedProblem,sanitize,support,solve,EvaluationLimit,POLICY
from basketball_shared_spline_v2 import SplineProblem
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_profiles_v4 import group_job,attempt,summaries,problem_key,decision,basin_grid


class V4Tests(unittest.TestCase):
    def fixture(self,weight=0.,lag=-7.,gid=0):
        groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
        return SplineProblem([groups[gid]],cameras,{1:0.,2:lag,3:0.},window,10,weight,(1,2))

    def test_analytic_scaled_objective_depth_and_constraint_hessian(self):
        for weight in [0.,1.]:
            p=self.fixture(weight);a=ConstrainedProblem(p);q=p.x0/a.scale
            rng=np.random.default_rng(4);d=rng.normal(size=len(q));h=1e-6
            r,J=a.evaluate(q)
            np.testing.assert_allclose(J@d,(a.evaluate(q+h*d)[0]-a.evaluate(q-h*d)[0])/(2*h),rtol=2e-4,atol=2e-5)
            z,D=a.depth(q);v=rng.normal(size=len(z))
            np.testing.assert_allclose(D@d,(a.depth(q+h*d)[0]-a.depth(q-h*d)[0])/(2*h),rtol=2e-5,atol=2e-6)
            np.testing.assert_allclose(a.depth(q,v)@d,(a.depth(q+h*d)[1].T@v-a.depth(q-h*d)[1].T@v)/(2*h),rtol=2e-5,atol=2e-5)
            original=p.evaluate(p.x0)[0];self.assertEqual(a.fun(q),float(original@original))
            self.assertEqual(len(q),len(p.x0));self.assertEqual(a.scale[0],25.);self.assertTrue(np.all(a.scale[1:]==1))

    def test_strict_distinct_evaluation_limit_including_derivatives(self):
        p=self.fixture();a=ConstrainedProblem(p);q=p.x0/a.scale
        with patch('basketball_shared_solver_v4.MAX_EVALUATIONS',2):
            a.jac(q);a.hess(q);a.fun(q);self.assertEqual(a.evaluations,1)
            a.hess(q+1e-9);self.assertEqual(a.evaluations,2)
            with self.assertRaises(EvaluationLimit):a.jac(q+2e-9)
            self.assertEqual(a.evaluations,2)

    def test_seed_replacement_activation_and_deterministic_blending(self):
        from basketball_scale import read
        raw=read('.local/calibration/basketball-rev2/shared-v3/safeguard/exact-retest/data_only-round2.json')
        for gid in [9,11]:
            state=next(s for s in raw['states'] if s['group_id']==gid)
            row=next(r for r in state['attempts']['-7.0'] if r['start']=='descending')
            p=self.fixture(gid=gid);seed=np.asarray(row['initial_x'])
            x,trace=sanitize(p,seed,-6.,2)
            self.assertIn(dict(group_id=gid,block=16),trace['replaced_blocks'])
            self.assertFalse(trace['original_valid']);self.assertIsNotNone(x)
            self.assertEqual(len(x),len(seed));self.assertGreater(min(ConstrainedProblem(p).depth(x/ConstrainedProblem(p).scale)[0]),2e-8)
            again,other=sanitize(p,seed,-6.,2);np.testing.assert_array_equal(x,again)
            self.assertEqual(trace['blend_fraction'],other['blend_fraction'])
        p=self.fixture();seed=p.x0.copy();seed[1:]=np.nan
        x,trace=sanitize(p,seed,-6.,2);np.testing.assert_array_equal(x,p.x0);self.assertEqual(trace['blend_fraction'],0.)

    def test_group2_camera_plane_crossing_and_infeasible_cold(self):
        from basketball_scale import read
        raw=read('.local/calibration/basketball-rev2/shared-v3/safeguard/exact-retest/data_only-round2.json')
        row=next(r for s in raw['states'] if s['group_id']==2 for r in s['attempts']['-19.0'] if r['start']=='ascending')
        p=self.fixture(lag=-19,gid=2);a=ConstrainedProblem(p)
        self.assertGreater(min(a.depth(np.asarray(row['initial_x'])/a.scale)[0]),0)
        self.assertLess(min(a.depth(np.asarray(row['x'])/a.scale)[0]),0)
        p.x0[1:]=np.tile([0.,0.,-10.],p.nc)
        x,trace=sanitize(p);self.assertIsNone(x);self.assertFalse(trace['cold_valid'])
        p.x0[:]=np.nan;x,trace=sanitize(p);self.assertIsNone(x)

    def test_no_fourth_attempt_deadline_and_cache_isolation(self):
        p=self.fixture();g=p.groups[0];payload=(g,p.cameras,dict(a=1,b=2),p.window,10,0.,'synthetic',[-1.,0.,1.],None,None)
        def fake(group,cameras,edge,window,spacing,weight,lag,label,key,seed,check):
            return dict(valid=True,objective=lag**2,start=label,problem_key=key,x=[lag])
        with patch('basketball_shared_profiles_v4.attempt',side_effect=fake):
            state=group_job(payload);state=group_job((*payload[:8],state,None))
            self.assertTrue(all(len(v)==3 for v in state['attempts'].values()))
            refined=group_job((*payload[:7],[-1.,-.5,0.,.5,1.],state,None))
            self.assertTrue(all(len(v)==3 for v in refined['attempts'].values()))
        with patch('basketball_shared_profiles_v4.solve') as solver:
            with self.assertRaises(TimeoutError):group_job((*payload[:-1],0.))
            solver.assert_not_called()
        from basketball_shared_profiles_v3 import problem_key as old_key
        self.assertNotEqual(problem_key(*payload[:7]),old_key(*payload[:7]))
        base=problem_key(*payload[:7])
        self.assertNotEqual(base,problem_key(*payload[:6],'selection'))
        self.assertNotEqual(base,problem_key(*payload[:5],1.,payload[6]))
        self.assertNotEqual(base,problem_key(payload[0],payload[1],dict(a=2,b=1),*payload[3:7]))

    def test_each_direction_fixed_membership_and_missing_noisy_evidence(self):
        grid=np.arange(-25,26,dtype=float);states=[]
        for i in range(13):
            asc={l:dict(valid=i!=0,objective=l*l) for l in grid}
            desc={l:dict(valid=i!=1,objective=l*l) for l in grid}
            states.append(dict(group_id=i,ascending=asc,descending=desc,attempts={l:[asc[l],desc[l]] for l in grid}))
        row=summaries(states,grid,12,.05,list(range(13)))
        self.assertFalse(row['passed']);self.assertIn('ascending fixed group support lost',row['blockers'])
        for state in states:
            for lag in grid:
                state['ascending'][lag].update(valid=True)
                state['descending'][lag].update(valid=True,objective=(lag-1)**2)
        disagreement=summaries(states,grid,12,.05,list(range(13)))
        self.assertFalse(disagreement['passed']);self.assertEqual(disagreement['sweep_disagreement_frames'],1.)
        row['support']=0
        self.assertFalse(decision('acceleration',100,.25,0.,dict(passed=False,profiles=dict(regularized=row,data_only=row)))['safeguard_passed'])

    def test_constraint_boundary_and_failed_termination_rejected(self):
        from types import SimpleNamespace
        p=self.fixture(lag=0.)
        def fake(fun,q,**kwargs):
            fun(q)
            return SimpleNamespace(x=q,success=True,status=1,message='test',v=[np.zeros(p.n),np.zeros(len(q))])
        with patch('basketball_shared_solver_v4.minimize',side_effect=fake):
            row=solve(p)
            self.assertFalse(row['valid'])  # Independently recomputed optimality rejects false success.
        row=solve(self.fixture(weight=1.,lag=0.))
        self.assertTrue(row['valid']);self.assertLessEqual(row['nfev'],200)
        self.assertGreater(row['minimum_normalized_depth'],1e-7)
        self.assertTrue(all(r['min_depth']>=1e-8 for r in row['solver_trace']))

    def test_heldout_pixels_do_not_change_training_initialization(self):
        import copy
        groups,cameras,_,window=synthetic(groups=1)
        extra=copy.deepcopy(groups[0]['observations'][2]);extra['camera_id']=0
        cameras[0]=copy.deepcopy(cameras[3]);groups[0]['observations'].append(extra)
        payload=(groups[0],cameras,dict(a=1,b=0),window,10,.1,'synthetic',[0.],None,None)
        first=group_job(payload)
        extra['xy']=extra['xy']+100
        second=group_job(payload)
        self.assertEqual(first['frozen_training']['x'],second['frozen_training']['x'])
        self.assertEqual(first['frozen_training']['initialization_transfer'],second['frozen_training']['initialization_transfer'])

    def test_fresh_stage_and_deadline(self):
        import tempfile
        from types import SimpleNamespace
        from basketball_shared_workflow_v4 import main,bounded
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(FileExistsError):main(SimpleNamespace(output=Path(folder)))
            from basketball_shared_workflow_v4 import prepare
            from basketball_scale import read
            original=read
            def changed(path):
                value=original(path)
                if str(path).endswith('optimizer-controls/case0000.json'):value['known_offset_frames']=123.
                return value
            with patch('basketball_shared_workflow_v4.read',side_effect=changed),patch('basketball_shared_workflow_v4.verify_hashes'):
                with self.assertRaisesRegex(ValueError,'recipe mismatch'):prepare(read('configs/basketball-rev2/timing-shared-v4.json'),Path(folder))
        with patch('basketball_shared_workflow_v4.time.time',return_value=5400.):
            with self.assertRaises(TimeoutError):bounded(dict(investigation_started_unix=0.),early=True)

    def test_acceleration_prevents_unsupported_replacement(self):
        p=self.fixture(weight=1.,lag=-6.)
        records=support(p,p.x0)
        self.assertEqual(records[0]['unsupported'],[])
        p.weight=0.
        self.assertIn(16,support(p,p.x0)[0]['unsupported'])

    def test_boundary_dependent_confidence_rejected(self):
        with patch('basketball_shared_solver_v4.QUALIFICATION_DEPTH',10.):
            row=solve(self.fixture(weight=1.,lag=0.))
        self.assertTrue(row['converged'])
        self.assertFalse(row['valid']);self.assertTrue(row['constraint_boundary_dependent'])

    def test_fractional_sign_group_bootstrap_competing_basins_and_cycles(self):
        from basketball_shared_spline_v2 import curve_summary,independent_cycles
        groups,cameras,_,window=synthetic('constant_velocity',0.,-.25,100,groups=1)
        state=group_job((groups[0],cameras,dict(a=1,b=2),window,10,0.,'synthetic',[-.3,-.25,-.2],None,None))
        self.assertEqual(min(state['cold'],key=lambda lag:state['cold'][lag]['objective']),-.25)
        grid=np.arange(-25,26,dtype=float)
        curve=np.minimum((grid+3)**2,(grid-4)**2)
        summary=curve_summary([curve]*12,grid)
        self.assertEqual(summary['bootstrap_unit'],'whole multiview group');self.assertFalse(summary['passed'])
        summary['sweeps']={}
        refined=basin_grid(summary,grid,.05)
        self.assertTrue(np.any(np.isclose(refined,-3.05)));self.assertTrue(np.any(np.isclose(refined,4.05)))
        self.assertFalse(independent_cycles([dict(a=1,b=2,lag=0.),dict(a=2,b=3,lag=0.),dict(a=1,b=3,lag=1.)],[1,2,3])['passed'])


if __name__=='__main__':unittest.main()
