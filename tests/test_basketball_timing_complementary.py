import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_timing_complementary import combine
from basketball_continuation_audit import CALIBRATION_SHA


class ComplementaryTests(unittest.TestCase):
    def source(self,edges):
        return dict(calibration_sha256=CALIBRATION_SHA,selection_consumed=False,
                    final_validation_consumed=False,edges=edges)

    def test_priority_is_fixed_and_failed_edges_are_not_rescued(self):
        a=self.source([dict(a=0,b=1,lag=.2,passed=True),dict(a=1,b=2,lag=0.,passed=False)])
        b=self.source([dict(a=0,b=1,lag=0.,passed=True),dict(a=1,b=2,lag=-.3,passed=True)])
        rows=combine(a,b)
        self.assertEqual(rows[0]['lag'],.2)
        self.assertEqual(rows[0]['source'],'sift-temporal-bias')
        self.assertEqual(rows[1]['lag'],-.3)
        self.assertEqual(rows[1]['source'],'sift-absolute')

    def test_reserved_or_wrong_calibration_source_is_rejected(self):
        for k,v in [('selection_consumed',True),('final_validation_consumed',True),('calibration_sha256','changed')]:
            bad=self.source([]);bad[k]=v
            with self.assertRaises(ValueError):combine(bad,self.source([]))


if __name__=='__main__':unittest.main()
