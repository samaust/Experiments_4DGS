import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_timing_reserved import role_cost,check_role_frames,validate_candidate
from basketball_continuation_audit import CALIBRATION_SHA


class ReservedTimingTests(unittest.TestCase):
    def test_role_boundary_and_interpolation_support(self):
        check_role_frames(list(range(150,200)),150,199)
        with self.assertRaises(ValueError):check_role_frames([199,200],150,199)
        a=dict(frames=np.arange(150,200),normalized=np.zeros((50,2)))
        E=np.array([[0,0,0],[0,0,-1],[0,1,0]])
        self.assertTrue(np.isfinite(role_cost(a,a,0,[-1,1],E,1,150,199,15)))
        self.assertTrue(np.isnan(role_cost(a,a,0,[-25,25],E,1,150,199,15)))

    def test_independent_edge_admission_preserves_full_rig(self):
        edges=[dict(a=i,b=(i+1)%34,lag=0.,passed=True) for i in range(34)]
        edges.append(dict(a=0,b=2,lag=10.,passed=False))
        source=dict(status='blocked',edges=edges,calibration_sha256=CALIBRATION_SHA,selection_consumed=False,final_validation_consumed=False)
        accepted,graph=validate_candidate(source)
        self.assertEqual(len(accepted),34);self.assertEqual(graph['status'],'passed')
        source['selection_consumed']=True
        with self.assertRaises(ValueError):validate_candidate(source)

    def test_cycle_failure_cannot_be_admitted(self):
        edges=[dict(a=i,b=(i+1)%34,lag=.3 if i==1 else 0.,passed=True) for i in range(34)]
        source=dict(edges=edges,calibration_sha256=CALIBRATION_SHA,selection_consumed=False,final_validation_consumed=False)
        with self.assertRaises(ValueError):validate_candidate(source)


if __name__=='__main__':unittest.main()
