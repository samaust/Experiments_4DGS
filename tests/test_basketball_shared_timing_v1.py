import copy
import sys
import tempfile
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_shared_timing_v1 import (common_injections, pair_costs, synthetic_pairs,
    project, mutual_pairs, merge_duplicates, build_groups, predecessor, validate_config)
from basketball_timing import essential, solve_curve, undistort_points, graph_offsets
from basketball_scale import read,write
from basketball_audit import sha256

BASE={**read('configs/basketball-rev2/timing.json'), **read('configs/basketball-rev2/timing-recovery.json')}
CONFIG=read('configs/basketball-rev2/timing-shared-v1.json')


class SharedTimingTests(unittest.TestCase):
    def test_vectorized_scores_match_historical_estimators(self):
        from basketball_timing_reserved import role_cost
        pairs,cams=synthetic_pairs('direction_changes',.25,.1)
        a,b=pairs[0];grid=np.array([-2.,-.1,0.,.25,2.]);E=essential(*cams)
        for absolute in [True,False]:
            actual,_=pair_costs(a,b,grid,E,800,15,absolute)
            expected=[role_cost(a,b,lag,grid,E,800,50,149,15,absolute) for lag in grid]
            np.testing.assert_allclose(actual,expected,atol=1e-12)

    def test_saved_trajectory_injection_recovers_positive_delta(self):
        pairs,cams=synthetic_pairs('acceleration',0)
        grid=np.round(np.arange(-2,2.001,.05),8)
        from basketball_shared_timing_v1 import evaluate_injections
        rows=evaluate_injections(pairs,CONFIG['injections'],grid,essential(*cams),800,BASE,50,99,False)
        for row in rows:
            self.assertIsNotNone(row['relative_recovery_error_frames'])
            self.assertLessEqual(abs(row['relative_recovery_error_frames']),.05)

    def test_positive_fractional_sign_and_noisy_recovery(self):
        grid=np.round(np.arange(-2,2.001,.05),8)
        for noise in [0,.25,.5]:
            for delta in CONFIG['injections']:
                pairs,cams=synthetic_pairs('acceleration',noise,delta)
                curves=[pair_costs(a,b,grid,essential(*cams),800,15,False)[0] for a,b in pairs]
                result=solve_curve(curves,grid,BASE)
                self.assertLessEqual(abs(result['lag']-delta),.1)
                self.assertNotIn('ambiguous optimum',result['blockers'])

    def test_constant_velocity_nuisance_removes_information(self):
        pairs,cams=synthetic_pairs('constant_velocity',0,.75)
        grid=np.arange(-25,26,dtype=float)
        curves=[pair_costs(a,b,grid,essential(*cams),800,15,False)[0] for a,b in pairs]
        self.assertLess(np.ptp(curves),1e-10)
        result=solve_curve(curves,grid,BASE)
        self.assertFalse(result['passed'])
        self.assertIn('ambiguous optimum',result['blockers'])

    def test_injection_identical_support_and_no_boundary_crossing(self):
        pairs,_=synthetic_pairs('acceleration',0)
        a,b=pairs[0];deltas=CONFIG['injections']
        a,bs=common_injections(a,b,deltas,75,99)
        for shifted,delta in zip(bs,deltas):
            np.testing.assert_array_equal(shifted['frames'],np.arange(76,99))
            np.testing.assert_allclose(shifted['xy'][:,1],np.interp(shifted['frames']-delta,b['frames'],b['xy'][:,1]))
        self.assertGreaterEqual(a['frames'].min(),75)
        self.assertLessEqual(a['frames'].max(),99)
        for bb in bs:
            curve,n=pair_costs(a,bb,[-25,25],np.eye(3),800,15,True)
            self.assertEqual(n,0);self.assertTrue(np.isnan(curve).all())

    def test_outlier_tracks_are_not_observation_bootstrap_units(self):
        pairs,cams=synthetic_pairs('direction_changes',.25,.25)
        grid=np.round(np.arange(-2,2.001,.05),8)
        curves=np.array([pair_costs(a,b,grid,essential(*cams),800,15,False)[0] for a,b in pairs])
        curves[:4]=np.abs(grid[None,:]+1.5)*10
        result=solve_curve(curves,grid,BASE)
        self.assertLessEqual(abs(result['lag']-.25),.1)
        self.assertEqual(result['support'],24)

    def test_pose_distortion_roundtrip(self):
        camera=read('docs/experiments/basketball-calibration-alternatives/calibration.json')['cameras'][7]
        cam=np.array([[.2,.3,3],[-.2,.7,4],[1,-.5,5]])
        xyz=(cam-np.array(camera['t']))@np.array(camera['R'])
        xy=project(xyz,camera)
        np.testing.assert_allclose(undistort_points(xy,camera),cam[:,:2]/cam[:,2,None],atol=1e-10)

    def test_mutual_ratio_both_directions(self):
        rows=lambda ds:[dict(descriptor=np.array([d])) for d in ds]
        self.assertEqual(mutual_pairs(rows([0.,.11]),rows([.05,3.])),[])
        self.assertEqual(mutual_pairs(rows([0.,1.]),rows([.01,1.01])),[(0,0),(1,1)])

    def test_duplicates_merged_before_whole_group_split(self):
        pairs,cams=synthetic_pairs('acceleration',0,n=24)
        items=[copy.deepcopy(a) for a,b in pairs]
        duplicate=copy.deepcopy(items[0]);duplicate['xy']+=.1
        merged=merge_duplicates(items+[duplicate],cams[0],CONFIG)
        self.assertEqual(len(merged),24)
        self.assertEqual(merged[0]['source_track_ids'],[0,24])
        tracks={c:copy.deepcopy(merged) for c in [1,2,3,0]}
        edges=[dict(a=a,b=b) for a,b in [(1,2),(2,3),(0,1)]]
        groups,rejected,_,support=build_groups(tracks,edges,CONFIG)
        self.assertEqual(len(groups),24);self.assertFalse(rejected)
        self.assertTrue(all(s['passed'] for s in support))
        members=[(m['camera_id'],m['track_id']) for g in groups for m in g['members']]
        self.assertEqual(len(members),len(set(members)))
        self.assertEqual(groups,build_groups(tracks,list(reversed(edges)),CONFIG)[0])

    def test_held_out_cannot_supply_training_support(self):
        pairs,_=synthetic_pairs('acceleration',0,n=24)
        tracks={c:[copy.deepcopy(a) for a,b in pairs] for c in [0,1,2]}
        groups,rejected,_,support=build_groups(tracks,[dict(a=0,b=1),dict(a=1,b=2)],CONFIG)
        self.assertFalse(groups)
        self.assertEqual({r['reason'] for r in rejected},{'fewer than three training cameras'})
        self.assertFalse(any(s['passed'] for s in support))

    def test_conflicting_components_rejected_whole(self):
        # Force a cycle connecting two trajectories in the same camera, without
        # depending on the geometry or the desired timing result.
        from unittest.mock import patch
        tracks={c:[{},{}] for c in [1,2,3]}
        edges=[dict(a=1,b=2),dict(a=2,b=3),dict(a=1,b=3)]
        with patch('basketball_shared_timing_v1.mutual_pairs',side_effect=[[(0,0)],[(0,0)],[(1,0)]]):
            groups,rejected,_,_=build_groups(tracks,edges,CONFIG)
        self.assertFalse(groups)
        bad=[r for r in rejected if r['reason']=='conflicting camera trajectories']
        self.assertEqual(len(bad),1);self.assertEqual(len(bad[0]['members']),4)

    def test_independent_cycle_inconsistency_is_not_global_offsets(self):
        edges=[dict(a=1,b=2,lag=.1,passed=True),dict(a=2,b=3,lag=.1,passed=True),dict(a=1,b=3,lag=.6,passed=True)]
        self.assertEqual(graph_offsets(edges,cameras=[1,2,3])['status'],'blocked')

    def test_frozen_hash_and_role_tamper_rejected(self):
        p=copy.deepcopy(CONFIG);p['roles']['fit']=[50,199]
        with self.assertRaises(ValueError):validate_config(p)
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);data=root/'data.json';write(data,dict(x=1))
            write(root/'result.json',dict(config_sha256='frozen',stage='audit',source_sha256={},artifacts_sha256={str(data):sha256(data)}))
            predecessor(root,'frozen',{'audit'})
            data.write_text('{"x":2}')
            with self.assertRaises(ValueError):predecessor(root,'frozen',{'audit'})


if __name__=='__main__':unittest.main()
