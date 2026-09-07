import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_timing_fine_fit import refinement_grid,replace_edges,subset_check
from basketball_scale import read


class FineTimingTests(unittest.TestCase):
    def test_grid_preserves_full_search_and_finer_offset(self):
        grid=refinement_grid(0,.01)
        self.assertEqual(grid[0],-25);self.assertEqual(grid[-1],25)
        self.assertIn(.13,grid)
        self.assertTrue(set(range(-25,26))<=set(grid))

    def test_failed_replacement_cannot_fall_back(self):
        old=[dict(a=1,b=2,passed=True,lag=0),dict(a=2,b=3,passed=True,lag=0)]
        new=[dict(a=1,b=2,passed=False,lag=.2)]
        result=replace_edges(old,new,{(1,2)})
        self.assertEqual(len(result),2);self.assertFalse(result[0]['passed'])
        with self.assertRaises(ValueError):replace_edges(old,new+new,{(1,2)})

    def parameters(self):
        p=read(Path(__file__).resolve().parents[1]/'configs/basketball-rev2/timing.json')
        return dict(p,subset_seed=0,subset_minimum_tracks=6)

    def test_groups_recover_fractional_offset(self):
        grid=refinement_grid(0,.01);costs=np.tile((grid-.13)**2,(24,1))
        r=subset_check(costs,grid,self.parameters())
        self.assertTrue(r['passed']);self.assertEqual(r['groups'][0]['lag'],.13)
        self.assertFalse(set(r['groups'][0]['indices'])&set(r['groups'][1]['indices']))

    def test_inconsistent_groups_rejected(self):
        grid=refinement_grid(0,.01);order=np.random.default_rng(0).permutation(24)
        costs=np.tile((grid-.13)**2,(24,1));costs[order[1::2]]=(grid+.3)**2
        r=subset_check(costs,grid,self.parameters())
        self.assertFalse(r['passed']);self.assertGreater(r['lag_difference_frames'],.25)


if __name__=='__main__':unittest.main()
