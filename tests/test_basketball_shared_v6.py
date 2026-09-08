"""Non-optimizing Plan 012 regressions; historical solves live in inherited tests."""
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_curvature_v6 import (snapshots, deterministic_svd, directions, gate,
    DiagnosticProblem, analyze, parameter_hash, probe, stationarity)
from basketball_shared_diagnose_v5 import fixture
from basketball_shared_workflow_v6 import bounded, stage
from argparse import Namespace


class V6Tests(unittest.TestCase):
    def test_missing_snapshots_and_multipliers_block(self):
        for row in [{}, {'solver_trace': [], 'x':[0]}, {'solver_trace':[{'x':[0]}], 'x':[0]}]:
            with self.assertRaises(ValueError):snapshots(row)
        row=dict(x=[1.,2.], solver_trace=[dict(x=[0.,2.]), dict(x=[1.,2.])],
                 multipliers_transformed=[0], multipliers_depth=[0], bound_multipliers=[0,0])
        s=snapshots(row)
        self.assertEqual([r['index'] for r in s], [0,1,None])
        self.assertEqual(s[1]['sha256'],s[2]['sha256'])

    def test_deterministic_repeated_and_null_subspaces(self):
        J=np.diag([3.,3.,1.,0.,0.]);s,b,t,spaces=deterministic_svd(J)
        s2,b2,t2,_=deterministic_svd(J)
        np.testing.assert_array_equal(b,b2);np.testing.assert_allclose(b@b.T,np.eye(5),atol=1e-14)
        self.assertEqual(sum(s>t),3);self.assertEqual(len(spaces),3)
        rng=np.random.default_rng(42);U=np.linalg.qr(rng.normal(size=(5,5)))[0]
        _,bb,_,_=deterministic_svd(U@J)
        np.testing.assert_allclose(bb,b,atol=1e-14)

    def test_sign_equivalent_directions_deduplicate(self):
        J=np.eye(7);G=np.arange(1.,8.)
        chosen,_=directions(J,G,[G,-G],1)
        row=next(r for r in chosen if 'gradient' in r['labels'])
        self.assertEqual(row['labels'],['gradient','saved_step_0','saved_step_1'])

    def test_failed_gate_never_authorizes_missing_group_or_null_probe(self):
        rows=[]
        for group in [2,9]:
            rows.append(dict(label='returned',saved_valid=False,group_id=group,reference=str(group),
                 analysis=dict(probes=[dict(labels=['gradient'],exactly_data_null=False,
                                           selected=dict(missing_curvature_screen=True))])))
        self.assertFalse(gate(rows,True,True)['passed'])
        self.assertEqual(gate(rows,True,True)['missing_groups'],[11])
        rows.append(dict(rows[-1],group_id=11));self.assertTrue(gate(rows,True,True)['passed'])
        self.assertFalse(gate(rows,False,True)['passed']);self.assertFalse(gate(rows,True,False)['passed'])
        rows[-1]['analysis']['probes'][0]['exactly_data_null']=True
        self.assertFalse(gate(rows,True,True)['passed'])

    def test_barrier_is_not_callback_KKT(self):
        p=fixture(2,-7.,0.,lambda:None);a=DiagnosticProblem(p);q=p.x0/a.scale
        _,_,g=a.evaluate(q);r=dict(solver_trace=[dict(barrier_parameter=.1)])
        s=stationarity(a,q,g,r,'first',0)
        self.assertFalse(s['multiplier_KKT_available']);self.assertGreater(s['B_depth_inf'],0)
        self.assertNotIn('KKT',s);self.assertTrue(s['barrier_available'])
        q[0]=1.;s=stationarity(a,q,g,r,'first',0);self.assertIsNone(s['B_bounds'])

    def test_fixed_probe_ladder_recovers_gradient_action(self):
        p=fixture(2,-7.,0.,lambda:None);a=DiagnosticProblem(p);q=p.x0/a.scale
        r,J,G=a.evaluate(q);v=G/np.linalg.norm(G)
        result=probe(a,q,v,2*J.T@J,G,[],J,np.zeros((0,len(q))))
        self.assertEqual([r['nominal_step'] for r in result['levels']],[1e-3,1e-4,1e-5,1e-6])
        self.assertIsNotNone(result['selected']);self.assertGreater(a.calls,1)
        self.assertEqual(a.a.evaluations,0)

    def test_deadlines_and_negative_predecessor(self):
        with patch('basketball_shared_workflow_v6.time.time',return_value=1800):
            with self.assertRaises(TimeoutError):bounded(dict(investigation_started_unix=0),early=True)
        with patch('basketball_shared_workflow_v6.time.time',return_value=13200):
            with self.assertRaises(TimeoutError):bounded(dict(investigation_started_unix=0))
            bounded(dict(investigation_started_unix=0),package=True)
        with patch('basketball_shared_workflow_v6.time.time',return_value=14400):
            with self.assertRaises(TimeoutError):bounded(dict(investigation_started_unix=0),package=True)
        from basketball_scale import write
        from basketball_audit import sha256
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);config=root/'config.json';prior=root/'prior';prior.mkdir()
            write(config,dict(investigation_started_unix=1e20))
            write(prior/'result.json',dict(stage='diagnose',config_sha256=sha256(config),
                 source_sha256={},artifacts_sha256={},status='blocked'))
            with patch('basketball_shared_solver_v5.minimize') as solver:
                with self.assertRaisesRegex(ValueError,'blocked predecessor'):
                    stage(Namespace(config=config,predecessor=prior,output=root/'pilot',stage='pilot'))
                solver.assert_not_called()
            self.assertFalse((root/'pilot').exists())

if __name__=='__main__':unittest.main()
