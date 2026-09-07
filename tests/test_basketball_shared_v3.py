import sys
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_solver_v3 import solve,POLICY,structural_inactivity,rank_record,objective_agreement
from basketball_shared_profiles_v3 import (group_job,problem_key,nearest_valid,attempt,summaries,basin_grid,decision)
from basketball_shared_spline_v2 import SplineProblem,curve_summary,independent_cycles
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_workflow_v3 import bounded


class V3Tests(unittest.TestCase):
    def fixture(self,weight=0.,lag=0.):
        groups,cameras,truth,window=synthetic('direction_changes',0.,-.1,100,groups=1)
        return groups,cameras,window,SplineProblem(groups,cameras,{1:0.,2:lag,3:0.},window,10,weight,(1,2))

    def test_scaling_analytic_derivative_and_full_coefficients(self):
        groups,cameras,window,p=self.fixture()
        x=p.x0.copy();r,J=p.evaluate(x)
        rng=np.random.default_rng(3);v=rng.normal(size=len(x));h=1e-6
        numerical=(p.evaluate(x+h*v)[0]-p.evaluate(x-h*v)[0])/(2*h)
        np.testing.assert_allclose(J@v,numerical,rtol=2e-5,atol=2e-5)
        result=solve(p)
        self.assertEqual(len(result['x']),len(x));self.assertEqual(POLICY['x_scale'],'jac')
        self.assertTrue(POLICY['tr_options']['regularize']);self.assertLessEqual(result['nfev'],200)
        residual,_=p.evaluate(np.asarray(result['x']))
        self.assertAlmostEqual(result['objective'],float(residual@residual))

    def test_inactive_columns_can_become_observable(self):
        _,_,_,p=self.fixture()
        initial={r['column'] for r in rank_record(p,p.x0)['zero_columns']}
        structural={r['column'] for r in structural_inactivity(p)}
        x=p.x0.copy();x[p.index[3]]=25.
        later={r['column'] for r in rank_record(p,x)['zero_columns']}
        self.assertTrue(initial-later);self.assertTrue((initial-later).isdisjoint(structural))
        self.assertTrue(structural<=initial)

    def test_problem_cache_isolation_and_production_exclusion(self):
        import inspect
        groups,cameras,window,_=self.fixture();g=groups[0];edge=dict(a=1,b=2)
        base=(g,cameras,edge,window,10,0.,'fit')
        key=problem_key(*base)
        variants=[(g,cameras,edge,window,10,1.,'fit'),(g,cameras,edge,[50,99],10,0.,'fit'),
                  (g,cameras,dict(a=2,b=1),window,10,0.,'fit'),(g,cameras,edge,window,5,0.,'fit'),
                  (g,cameras,edge,window,10,0.,'select'),({**g,'group_id':999},cameras,edge,window,10,0.,'fit')]
        self.assertTrue(all(problem_key(*v)!=key for v in variants))
        from basketball_shared_profiles_v3 import independent_edge
        self.assertNotIn('offsets',inspect.signature(independent_edge).parameters)
        with self.assertRaisesRegex(ValueError,'cross-problem'):
            attempt(g,cameras,edge,window,10,0.,0.,'ascending',key,(0.,dict(problem_key='other',start='cold')),lambda:None)
        with self.assertRaisesRegex(ValueError,'cache isolation'):
            group_job((*base[:6],base[6],[0.],dict(problem_key='other'),None))

    def test_cold_warm_provenance_and_three_attempt_limit(self):
        groups,cameras,window,_=self.fixture();g=groups[0];edge=dict(a=1,b=2)
        payload=(g,cameras,edge,window,10,0.,'synthetic',[-1.,0.,1.],None,None)
        def fake(group,cameras,edge,window,spacing,weight,lag,label,key,seed,check):
            return dict(valid=True,objective=lag**2,x=[lag],start=label,problem_key=key,
                        seed_lag=None if seed is None else seed[0],seed_start=None if seed is None else seed[1]['start'])
        with patch('basketball_shared_profiles_v3.attempt',side_effect=fake):
            s=group_job(payload)
            self.assertEqual(s['ascending'][-1.]['seed_start'],'cold')
            self.assertEqual(s['ascending'][0.]['seed_lag'],-1.)
            self.assertEqual(s['descending'][0.]['seed_lag'],1.)
            refined=group_job((*payload[:7],[-1.,-.5,0.,.5,1.],s,None))
            self.assertEqual(refined['ascending'][-.5]['seed_lag'],-1.)
            self.assertEqual(refined['descending'][-.5]['seed_lag'],0.)
            self.assertTrue(all(len(v)==3 for v in refined['attempts'].values()))
        choices={-1.:dict(valid=True),1.:dict(valid=True)}
        self.assertEqual(nearest_valid(choices,0.)[0],-1.)
        row=attempt(g,cameras,edge,window,10,0.,0.,'ascending','key',None,lambda:None)
        self.assertFalse(row['valid']);self.assertIn('missing valid seed',row['error'])

    def test_sweep_disagreement_and_regularization_only_confidence(self):
        grid=np.arange(-25,26,dtype=float);states=[]
        for i in range(12):
            asc={l:dict(valid=True,objective=l*l) for l in grid}
            desc={l:dict(valid=True,objective=(l-1)**2) for l in grid}
            states.append(dict(group_id=i,ascending=asc,descending=desc,attempts={l:[asc[l],desc[l]] for l in grid}))
        r=summaries(states,grid,12,.25)
        self.assertFalse(r['passed']);self.assertEqual(r['sweep_disagreement_frames'],1.)
        independent=dict(passed=False,profiles={'regularized':r,'data_only':{**r,'passed':False}})
        self.assertFalse(decision('direction_changes',100,0.,-.1,independent)['safeguard_passed'])
        # Missing negative evidence is not a successful ambiguity safeguard.
        missing={**r,'support':0}
        negative=dict(passed=False,profiles=dict(regularized=missing,data_only=missing))
        self.assertFalse(decision('stationary',100,0.,0.,negative)['safeguard_passed'])

    def test_competing_basins_and_group_bootstrap(self):
        grid=np.arange(-25,26,dtype=float);c=np.minimum((grid+3)**2,(grid-4)**2)
        summary=curve_summary([c]*12,grid)
        self.assertEqual(summary['bootstrap_unit'],'whole multiview group')
        self.assertFalse(summary['passed'])
        summary['sweeps']={}
        fine=basin_grid(summary,grid,.05)
        self.assertTrue(np.any(np.isclose(fine,-3.05)));self.assertTrue(np.any(np.isclose(fine,4.05)))

    def test_fractional_sign_and_heldout_isolation(self):
        groups,cameras,truth,window=synthetic('constant_velocity',0.,-.25,100,groups=1)
        s=group_job((groups[0],cameras,dict(a=1,b=2),window,10,0.,'synthetic',[-.3,-.25,-.2],None,None))
        self.assertEqual(min(s['cold'],key=lambda l:s['cold'][l]['objective']),-.25)
        # Camera3 becomes held-out0; its pixels cannot affect training nuisance state.
        import copy
        groups,cameras,_,window=synthetic(groups=1)
        extra=copy.deepcopy(groups[0]['observations'][2]);extra['camera_id']=0
        cameras[0]=copy.deepcopy(cameras[3]);groups[0]['observations'].append(extra)
        payload=(groups[0],cameras,dict(a=1,b=0),window,10,.1,'synthetic',[0.],None,None)
        first=group_job(payload)
        extra['xy']=extra['xy']+100
        second=group_job(payload)
        self.assertEqual(first['frozen_training']['x'],second['frozen_training']['x'])

    def test_cycles_deadline_and_objective_agreement(self):
        self.assertFalse(independent_cycles([dict(a=1,b=2,lag=0.),dict(a=2,b=3,lag=0.),dict(a=1,b=3,lag=1.)],[1,2,3])['passed'])
        with patch('basketball_shared_workflow_v3.time.time',return_value=5400.):
            with self.assertRaises(TimeoutError):bounded(dict(investigation_started_unix=0.),early=True)
        self.assertTrue(objective_agreement(1.,1.00001));self.assertFalse(objective_agreement(1.,1.1))


if __name__=='__main__':unittest.main()
