"""Plan 014 recovery, coordinate, search, budget and gate contracts."""
import sys
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from unittest.mock import patch,Mock
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_scale import read,write
from basketball_shared_recovery_v8 import fixture,reconstruct,replay_compare
from basketball_shared_solver_v8 import Adapter
from basketball_shared_regressions_v8 import conditioning_regressions,scalar_regressions
from basketball_shared_workflow_v8 import deadline,main,terminate_group
from basketball_shared_report_v8 import package

class V8Tests(unittest.TestCase):
    def policy(self):return read('configs/basketball-rev2/timing-shared-v8.json')
    def test_deadlines(self):
        p=self.policy()
        for stage,m in dict(prepare=30,recover=30,diagnose=30,condition=70,basins=170,pilot=220,package=240).items():self.assertEqual(deadline(p,stage),p['investigation_started_unix']+60*m)
        self.assertEqual(p['v8']['max_iterations'],200);self.assertEqual(p['v8']['max_distinct_states'],200)
    def test_derivative_chain_rules_and_caps(self):self.assertTrue(conditioning_regressions()['passed'])
    def test_refinement_and_failed_neighbors(self):self.assertTrue(scalar_regressions()['passed'])
    def test_raw_and_transformed_reconstruction_differ(self):
        p=fixture(2,-25.,1.);r=reconstruct(p,p.x0,.1,True);t=reconstruct(p,p.x0,.1,False)
        self.assertFalse(np.allclose(r['multipliers_depth'],t['multipliers_depth']))
        np.testing.assert_allclose(r['G'],t['G'],atol=1e-12)
        self.assertTrue(np.all(np.asarray(r['slacks'])>0))
    def test_replay_divergence_rejected(self):
        saved=dict(status=1,nfev=1,initial_x=[0],x=[1],objective=1.,normalized_depths=[1.],optimality=1e-7,solver_trace=[dict(iteration=1,x=[1],objective=1.,optimality=1e-7,min_depth=1.)])
        replay_compare(saved,saved)
        for changed in [dict(status=0),dict(nfev=2),dict(x=[1.01]),dict(solver_trace=[])]:
            with self.assertRaises((ValueError,AssertionError)):replay_compare(saved,{**saved,**changed})
    def test_expired_stage_preserves_unknown_counts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=self.policy();p['investigation_started_unix']=0;write(root/'config.json',p)
            a=Namespace(stage='prepare',config=root/'config.json',output=root/'prepare',predecessor=None)
            with patch('basketball_shared_workflow_v8.subprocess.Popen') as launch:
                self.assertEqual(main(a),1);launch.assert_not_called()
            r=read(a.output/'result.json');self.assertIsNone(r['executed_counts'])
            out=root/'package';out.mkdir();package(out,r,a.output,p)
            decisions=read(out/'development-decisions.json');self.assertIsNone(decisions['conditioning']['passed'])
    def test_process_group_killed_even_after_leader_exits(self):
        import signal
        child=Mock(pid=1234)
        with patch('basketball_shared_workflow_v8.os.killpg') as kill:terminate_group(child)
        self.assertEqual([c.args for c in kill.call_args_list],[(1234,signal.SIGTERM),(1234,signal.SIGKILL)])
    def test_missing_predecessor_packaged(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);a=Namespace(stage='recover',config=Path('configs/basketball-rev2/timing-shared-v8.json'),output=root/'out',predecessor=root/'missing')
            self.assertEqual(main(a),1);self.assertEqual(read(a.output/'result.json')['terminal_kind'],'provenance_failure')
    def test_transform_gtol_protects_original_coordinate_norm(self):
        a=Adapter(fixture(2,0.,1.),True)
        g=np.full(len(a.P),a.gtol)
        self.assertLessEqual(np.linalg.norm(a.inverse.T@g,np.inf),1e-6*(1+1e-12))
        # A loose transformed threshold alone can falsely indicate convergence.
        P=np.diag([1e-3,1.]);physical=np.array([1e-4,0.]);self.assertLess(np.max(np.abs(P.T@physical)),1e-6);self.assertGreater(np.max(np.abs(physical)),1e-6)

    def test_scipy_rejected_iteration_retains_returned_owner(self):
        from scipy.optimize import OptimizeResult
        from scipy.optimize._trustregion_constr.minimize_trustregion_constr import update_state_sqp
        state=OptimizeResult(nit=1,cg_niter=0,x=np.array([1.]),v=[np.array([2.])])
        objective=Mock(nfev=4,ngev=3,nhev=2)
        updated=update_state_sqp(state,np.array([99.]),True,objective,[],0.,.1,1.,dict(niter=0,stop_cond=0))
        np.testing.assert_array_equal(updated.x,[1.]);np.testing.assert_array_equal(updated.v[0],[2.])
    def test_stale_barrier_cannot_pass_full_multiplier_comparison(self):
        from basketball_shared_recovery_v8 import compare
        from basketball_shared_diagnose_v5 import compressed_read
        row=compressed_read('docs/experiments/basketball-shared-timing-v6/pilot/weight1.0-group02.json.gz')['attempts']['-25.0'][0]
        p=fixture(2,-25.,1.);stale=reconstruct(p,row['x'],.1)
        with self.assertRaises(AssertionError):compare(p,row,stale)
    def test_conditional_stationarity_omits_offset_and_preserves_support(self):
        from basketball_shared_spline_v2 import SplineProblem
        from basketball_shared_synthetic_v2 import synthetic
        from basketball_shared_solver_v6 import ConstrainedProblem,sanitize,support
        groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
        p=SplineProblem([groups[0]],cameras,{1:0.,2:0.,3:25.},window,10,0.,(1,2,3))
        a=ConstrainedProblem(p);self.assertEqual(p.n_offsets,0)
        x,init=sanitize(p,p.x0.copy(),-25.,3);self.assertIsNotNone(x)
        self.assertEqual(init['source_lag'],-25.);self.assertEqual(init['destination_lag'],25.)
        r,J=a.evaluate(x);self.assertEqual(J.shape[1],54)
        joint=SplineProblem([groups[0]],cameras,{1:0.,2:0.,3:0.},window,10,0.,(1,2))
        b=ConstrainedProblem(joint);rr,JJ=b.evaluate(np.r_[25.,x]/b.scale)
        np.testing.assert_allclose(r,rr,atol=1e-12);np.testing.assert_allclose(J.toarray(),JJ.toarray()[:,1:],atol=1e-12)
        self.assertEqual(JJ.shape[1],55)
        self.assertGreater(abs(float((2*JJ.T@rr)[0])),1e-6)
    def test_cross_problem_seed_rejected(self):
        from basketball_shared_profiles_v8 import attempt
        with self.assertRaisesRegex(ValueError,'cross-problem'):
            attempt(None,None,None,None,10,1.,0.,'ascending','destination',(0.,dict(start='cold',problem_key='historical')),lambda:None)
    def test_package_no_worker_artifact_is_unknown(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);out=root/'package';out.mkdir();source=root/'condition';source.mkdir()
            write(source/'worker-ledger.json',dict(tasks=[dict(scheduled=24,executed=None)]))
            prior=dict(stage='condition',status='blocked',terminal_kind='budget_exhaustion',blockers=['terminated'],source_sha256={},elapsed_seconds=4200)
            package(out,prior,source,self.policy())
            counts=read(out/'search-ledgers.json');self.assertIsNone(counts['conditioning']['executed']);self.assertEqual(counts['conditioning']['known_completed_attempts'],0)

if __name__=='__main__':unittest.main()
