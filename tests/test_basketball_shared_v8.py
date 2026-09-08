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

if __name__=='__main__':unittest.main()
