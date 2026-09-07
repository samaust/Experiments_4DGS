import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_timing import trajectory_cost, solve_curve, graph_offsets, essential, validate_protocol, undistort_points


class TimingTests(unittest.TestCase):
    def setUp(self):
        self.p=validate_protocol('configs/basketball-rev2/timing.json')

    def test_fractional_offset_sign_and_recovery(self):
        times=np.arange(50,150)
        def trajectory(t):return np.column_stack((.1*np.sin(t*.04),.003*t+.03*np.sin(t*.07)))
        a=dict(frames=times,normalized=trajectory(times))
        b=dict(frames=times,normalized=trajectory(times-2.35)-[.2,0])
        E=essential(dict(R=np.eye(3),t=[0,0,0]),dict(R=np.eye(3),t=[-1,0,0]))
        grid=np.round(np.arange(-25,25.001,.05),8)
        costs=np.array([trajectory_cost(a,b,d,E,800,15) for d in grid])
        result=solve_curve(np.tile(costs,(12,1)),grid,self.p)
        self.assertTrue(result['passed'])
        self.assertAlmostEqual(result['lag'],2.35,places=6)
        self.assertTrue(np.isnan(trajectory_cost(a,b,99,E,800,15)))

    def test_flat_boundary_and_insufficient_support(self):
        grid=np.arange(-25,26)
        for costs,reason in [(np.ones((12,51)),'ambiguous optimum'),
                             (np.tile(np.arange(51),(12,1)),'boundary optimum')]:
            r=solve_curve(costs,grid,self.p)
            self.assertFalse(r['passed']);self.assertIn(reason,r['blockers'])
        self.assertFalse(solve_curve(np.ones((11,51)),grid,self.p)['passed'])

    def test_uncertain_tracks_rejected(self):
        grid=np.arange(-25,25.001,.05)
        costs=np.array([abs(grid-x) for x in [-2]*6+[2]*6])
        r=solve_curve(costs,grid,self.p)
        self.assertIn('timing uncertainty',r['blockers'])

    def test_connected_cycles_and_reference_gauge(self):
        edges=[dict(a=1,b=2,lag=.2,passed=True),dict(a=2,b=3,lag=.3,passed=True),dict(a=1,b=3,lag=.5,passed=True)]
        r=graph_offsets(edges,cameras=(1,2,3))
        self.assertEqual(r['status'],'passed');self.assertAlmostEqual(r['offsets'][3],.5)
        edges[-1]['lag']=2.
        self.assertEqual(graph_offsets(edges,cameras=(1,2,3))['status'],'blocked')
        self.assertEqual(graph_offsets(edges[:2],cameras=(1,2,3))['status'],'blocked')
        self.assertEqual(graph_offsets(edges[:1],cameras=(1,2,3))['unreachable_cameras'],[3])

    def test_cycle_closure_cannot_be_diluted_by_least_squares(self):
        edges=[dict(a=1,b=2,lag=.2,passed=True),dict(a=2,b=3,lag=.3,passed=True),dict(a=1,b=3,lag=1.1,passed=True)]
        r=graph_offsets(edges,cameras=(1,2,3))
        self.assertLess(r['max_edge_fit_residual_frames'],.25)
        self.assertAlmostEqual(r['max_cycle_closure_frames'],.6)
        self.assertEqual(r['status'],'blocked')
        self.assertIsNone(r['offsets'])

    def test_full_image_distortion_inverse_matches_native(self):
        import json
        import pycolmap as cm
        xy=np.array([(x,y) for x in np.linspace(0,959,17) for y in np.linspace(0,539,9)])
        for c in json.loads(Path('docs/experiments/basketball-calibration-alternatives/calibration.json').read_text())['cameras']:
            native=cm.Camera(model=c['camera_model'],params=c['parameters_colmap'],width=960,height=540)
            uv=undistort_points(xy,c)
            back=native.img_from_cam(np.column_stack((uv,np.ones(len(uv)))))-.5
            self.assertLess(np.linalg.norm(back-xy,axis=1).max(),1e-6)


if __name__=='__main__':unittest.main()
