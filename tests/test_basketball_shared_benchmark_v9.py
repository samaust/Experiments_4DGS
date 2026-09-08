"""Frozen local schedules, feasibility, failure reporting and process watchdog checks."""
from pathlib import Path
import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_accounting_v9 import CanonicalAdapter,reconcile,Ledger
from basketball_shared_initialization_v9 import repair_cold,sanitize,sampled_support
from basketball_shared_diagnose_v9 import make_problem
from basketball_shared_benchmark_v9 import event_accounting,jobs,nearest,iteration_ids
from basketball_shared_solver_v9 import solve

class BenchmarkTests(unittest.TestCase):
    def test_frozen_schedule_limits(self):
        m=json.loads(Path('docs/experiments/basketball-shared-timing-v9/prepare-resumed/benchmark-manifest.json').read_text())
        self.assertEqual(m['scheduled_per_policy'],81);self.assertLessEqual(len(m['targets']),24);self.assertLessEqual(len(m['dependencies']),24)
        count=sum((3 if t['kind']=='conditional' else 1)*len(t['targets'])+len(t['dependencies']) for t in jobs(m))
        self.assertEqual(count,81);self.assertEqual(len(iteration_ids(m)),6)

    def test_feasible_analytical_initialization(self):
        for g in [2,9,11]:
            p=make_problem(dict(group_id=g,weight=1.,lag=-19.,offset=-21.));a=CanonicalAdapter(p,'init-unit')
            initial=a.state_x(p.x0,'cold');self.assertLessEqual(min(a.raw(initial)[0]),2e-8)
            fixed,record=repair_cold(a,p.x0);self.assertIsNotNone(fixed);self.assertTrue(record['feasible'])
            self.assertGreater(min(a.raw(a.state_x(fixed,'verify'))[0]),2e-8)
            self.assertEqual(a.ledger.iterations,0);reconcile(a.export())

    def test_support_activation_and_ledger_scope(self):
        p=make_problem(dict(group_id=2,weight=0.,lag=-6.,offset=-25.));a=CanonicalAdapter(p)
        source=sampled_support(a,p.x0,'source_support',-5.,3);destination=sampled_support(a,p.x0,'destination_support')
        self.assertNotEqual(source[0]['data_norms'],destination[0]['data_norms'])
        self.assertTrue(any(s['scope']!='destination' for s in a.export()['states']));reconcile(a.export())

    def test_missing_dependency_not_replaced_by_invalid_seed(self):
        cold={-25.:dict(row=dict(valid=False))}
        self.assertIsNone(nearest(cold,-24.))
        cold[-20.]=dict(row=dict(valid=True));self.assertIsNone(nearest(cold,-24.,'lower'))
        self.assertEqual(nearest(cold,-24.)[0],-20.)

    def test_truncated_and_absent_events_keep_unknown(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/'events';self.assertIsNone(event_accounting(p)['entered'])
            p.write_text('{"event":"allocated","id":"a"}\n{"event":"entered","id":"a"}\n{"event":')
            row=event_accounting(p);self.assertIsNone(row['entered']);self.assertEqual(row['entered_lower_bound'],1);self.assertFalse(row['exact'])
            p.write_text('{"event":"allocated","id":"a"}\n{"event":"completed","id":"a","executed":false}\n')
            self.assertEqual(event_accounting(p)['entered'],0)

    def test_initialization_and_solver_share_identity(self):
        p=make_problem(dict(group_id=2,weight=1.,lag=0.,offset=0.))
        def stopped(fun,y0,**kwargs):
            from types import SimpleNamespace
            jac=kwargs['jac'](y0);kwargs['hess'](y0)
            z=kwargs['constraints'][0].fun(y0)
            state=SimpleNamespace(nit=1,fun=fun(y0),optimality=1.,barrier_parameter=.1,tr_radius=1.,v=[np.zeros(len(z)),np.zeros(len(y0))])
            kwargs['callback'](y0,state)
            return SimpleNamespace(x=y0,v=state.v,nit=1,success=True,status=2,message='xtol test')
        with patch('basketball_shared_solver_v9.minimize',stopped):row=solve(p)
        self.assertFalse(row['valid']);self.assertTrue(row['converged']);self.assertEqual(row['iterations'],1)
        reconcile(row['accounting'])
        states={s['identity'] for s in row['accounting']['states']};self.assertIn(row['returned_state'],states)

    def test_entire_process_group_watchdog(self):
        from basketball_shared_workflow_v9 import terminate_group
        with tempfile.TemporaryDirectory() as t:
            f=Path(t)/'pid'
            script='import subprocess,time,pathlib; p=subprocess.Popen(["sleep","30"]); pathlib.Path('+repr(str(f))+').write_text(str(p.pid)); time.sleep(30)'
            child=subprocess.Popen([sys.executable,'-c',script],start_new_session=True)
            for _ in range(100):
                if f.exists():break
                time.sleep(.01)
            self.assertTrue(f.exists());pid=int(f.read_text());terminate_group(child)
            for _ in range(100):
                stat=Path(f'/proc/{pid}/stat')
                if not stat.exists() or stat.read_text().split()[2]=='Z':break
                time.sleep(.01)
            else:self.fail('descendant remained running')

if __name__=='__main__':unittest.main()
