import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_initial_pairs import rank_common,eligible


class InitialPairTests(unittest.TestCase):
    def record(self,pair,n=150,angle=20,coverage=8,homography=.5):
        return dict(cameras=pair,inliers=n,triangulation_degrees=angle,coverage_cells=[coverage,coverage],homography_fraction=homography)

    def test_common_eligibility_and_deterministic_cap(self):
        early=[self.record([1,2],200),self.record([2,3],300),self.record([3,6],150)]
        late=[self.record([1,2],180),self.record([2,3],120),self.record([3,6],150)]
        self.assertEqual(rank_common(early,late),[[1,2],[3,6]])
        self.assertEqual(rank_common(early,[]),[])

    def test_reject_weak_planar_and_poor_coverage(self):
        for change in [dict(n=99),dict(angle=15.9),dict(coverage=5),dict(homography=.8)]:
            self.assertFalse(eligible(self.record([1,2],**change)))


if __name__=='__main__':unittest.main()
