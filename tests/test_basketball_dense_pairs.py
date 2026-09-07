import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_protocol import TRAINING
from basketball_geometry import connected_components
from basketball_dense_matches import select_pairs


class DensePairTests(unittest.TestCase):
    def test_bounded_connected_overlap_selection(self):
        edges=[{'cameras':[a,b],'inliers':100+(i+j)%10} for i,a in enumerate(TRAINING) for j,b in enumerate(TRAINING) if i<j]
        pairs=select_pairs(edges)
        self.assertLessEqual(len(pairs),64)
        self.assertEqual(connected_components(TRAINING,pairs),[list(TRAINING)])
        self.assertFalse({0,5,10,20,30}&{c for pair in pairs for c in pair})

    def test_reject_disconnected_or_excluded_overlap(self):
        for edges in [[],[{'cameras':[1,5],'inliers':100}]]:
            with self.assertRaises(ValueError): select_pairs(edges)
        with self.assertRaises(ValueError): select_pairs([],maximum=10)


if __name__=='__main__':unittest.main()
