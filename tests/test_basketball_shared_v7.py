"""Plan 013 admission failures must never masquerade as solver decisions."""
import sys
import signal
import subprocess
import tempfile
import time
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import Mock,patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_scale import read,write
from basketball_shared_workflow_v7 import deadline,main,predecessor,terminate_group
from basketball_shared_report_v7 import package
from basketball_shared_diagnose_v7 import historical_stationarity
from basketball_shared_curvature_v6 import DiagnosticProblem,snapshots
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_spline_v2 import SplineProblem


class AdmissionV7Tests(unittest.TestCase):
    def policy(self):
        return read('configs/basketball-rev2/timing-shared-v7.json')

    def test_absolute_deadlines_and_unchanged_policy(self):
        p=self.policy();start=p['investigation_started_unix']
        expected=dict(prepare=30,diagnose=30,condition=60,basins=105,pilot=120,safeguard=165,multinuisance=195,controls=195,benchmark=220,fit=220,assess=220,select=220,package=240)
        for stage,minutes in expected.items():self.assertEqual(deadline(p,stage),start+60*minutes)
        old=read('configs/basketball-rev2/timing-shared-v6.json')
        for key in ['source_sha256','fit_frames','roles','configurations','held_out_cameras','independent_solver']:
            self.assertEqual(p[key],old[key])
        self.assertEqual(len(p['pilot_groups'])*len(p['pilot_lags'])*2*3,144)
        self.assertEqual(48*51*3,p['v7']['basins']['scheduled_initial'])

    def test_timeout_before_worker_has_no_success_artifacts(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=self.policy();p['investigation_started_unix']=0;write(root/'config.json',p)
            a=Namespace(stage='prepare',config=root/'config.json',predecessor=None,output=root/'prepare')
            with patch('basketball_shared_workflow_v7.subprocess.Popen') as launch:
                self.assertEqual(main(a),1);launch.assert_not_called()
            r=read(a.output/'result.json')
            self.assertEqual(r['terminal_kind'],'budget_exhaustion')
            self.assertFalse(read(a.output/'frozen.json')['worker_initialized'])
            self.assertIsNone(r['accepted_timing']);self.assertIsNone(r['final_protocol'])
            out=root/'package';out.mkdir();package(out,r,a.output,p)
            decision=read(out/'development-decisions.json')
            self.assertIsNone(decision['conditioning']['passed'])
            self.assertEqual(decision['scalar_basins']['conditional_initial']['missing'],7344)

    def test_watchdog_kills_descendants_after_leader_exits(self):
        child=Mock(pid=12345)
        with patch('basketball_shared_workflow_v7.os.killpg') as kill:
            terminate_group(child)
        self.assertEqual([c.args for c in kill.call_args_list],[(12345,signal.SIGTERM),(12345,signal.SIGKILL)])

    def test_watchdog_with_no_worker_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);p=self.policy();p['investigation_started_unix']=time.time();write(root/'config.json',p)
            a=Namespace(stage='prepare',config=root/'config.json',predecessor=None,output=root/'prepare')
            child=Mock(pid=4321);child.wait.side_effect=[subprocess.TimeoutExpired('worker',1),0,0]
            with patch('basketball_shared_workflow_v7.subprocess.Popen',return_value=child),patch('basketball_shared_workflow_v7.os.killpg') as kill:
                self.assertEqual(main(a),1)
            self.assertEqual(kill.call_count,2)
            self.assertEqual(read(a.output/'result.json')['terminal_kind'],'budget_exhaustion')

    def test_predecessor_hash_tampering_is_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);write(root/'config.json',self.policy());prior=root/'prior';prior.mkdir()
            write(prior/'result.json',dict(schema='basketball-shared-timing-stage/v7',config_sha256='wrong'))
            with self.assertRaisesRegex(ValueError,'config mismatch'):
                predecessor(Namespace(stage='diagnose',predecessor=prior,config=root/'config.json'))

    def test_returned_multiplier_omission_is_not_intermediate_exception(self):
        row=dict(x=[0.,1.],solver_trace=[dict(x=[0.,1.])])
        with self.assertRaisesRegex(ValueError,'returned multipliers'):snapshots(row)

    def test_v4_raw_barrier_does_not_invent_returned_kkt(self):
        groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
        p=SplineProblem([groups[2]],cameras,{1:0.,2:-25.,3:0.},window,10,1.,(1,2))
        a=DiagnosticProblem(p);q=p.x0/a.scale;r,J,g=a.evaluate(q)
        row=dict(solver_trace=[dict(barrier_parameter=.1)],optimality=3e-7)
        stat=historical_stationarity(a,q,g,row)
        self.assertFalse(stat['multiplier_KKT_available']);self.assertIsNone(stat['KKT_inf'])
        self.assertEqual(stat['saved_KKT_inf'],3e-7);self.assertIsNone(stat['C_depth'])
        # Independently differentiate the raw-depth log barrier in a physical direction.
        v=np.random.default_rng(13).normal(size=len(q));v/=np.linalg.norm(v);h=1e-6
        def barrier(t):
            z=a.a.raw_depth(q+t*v)[0]
            return -.1*np.log(z-1e-8).sum()
        fd=(barrier(h)-barrier(-h))/(2*h)
        self.assertAlmostEqual(fd,np.asarray(stat['B_depth'])@v,places=6)

if __name__=='__main__':unittest.main()
