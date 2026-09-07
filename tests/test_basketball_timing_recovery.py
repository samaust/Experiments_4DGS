import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_timing_recovery import temporal_cost
from basketball_timing import essential, solve_curve
from basketball_scale import read


class TimingRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.p=read('configs/basketball-rev2/timing.json');self.p.update(read('configs/basketball-rev2/timing-recovery.json'))
        self.E=essential(dict(R=np.eye(3),t=[0,0,0]),dict(R=np.eye(3),t=[-1,0,0]))
        self.t=np.arange(50,150)

    def test_nonlinear_motion_recovers_fractional_lag_despite_constant_bias(self):
        def motion(t):return np.column_stack((.1*np.cos(t*.04),.1*np.sin(t*.12)+.002*t))
        a=dict(frames=self.t,normalized=motion(self.t))
        b=dict(frames=self.t,normalized=motion(self.t-2.35)+[-.2,.001])
        grid=np.round(np.arange(-25,25.001,.05),8)
        costs=np.array([temporal_cost(a,b,d,self.E,800,self.p) for d in grid])
        r=solve_curve(np.tile(costs,(12,1)),grid,self.p)
        self.assertTrue(r['passed']);self.assertAlmostEqual(r['lag'],2.35)

    def test_constant_velocity_is_unidentifiable_after_bias_removal(self):
        a=dict(frames=self.t,normalized=np.column_stack((self.t*.001,self.t*.003)))
        b=dict(frames=self.t,normalized=a['normalized']+[-.2,.001])
        grid=np.arange(-25,26)
        costs=np.array([temporal_cost(a,b,d,self.E,800,self.p) for d in grid])
        self.assertLess(np.ptp(costs),1e-10)
        r=solve_curve(np.tile(costs,(12,1)),grid,self.p)
        self.assertFalse(r['passed']);self.assertIn('ambiguous optimum',r['blockers'])

    def test_common_support_requires_full_search_and_no_extrapolation(self):
        a=dict(frames=self.t,normalized=np.column_stack((self.t*.001,self.t*.003)))
        b=dict(frames=self.t[:60],normalized=a['normalized'][:60])
        self.assertTrue(np.isnan(temporal_cost(a,b,0,self.E,800,self.p)))
        self.assertTrue(np.isnan(temporal_cost(a,a,100,self.E,800,self.p)))


if __name__=='__main__':unittest.main()
