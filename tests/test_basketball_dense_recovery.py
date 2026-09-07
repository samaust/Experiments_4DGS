import sys
import unittest
from pathlib import Path
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_dense_recovery import bilateral_sample


class DenseRecoveryTests(unittest.TestCase):
    def test_bilateral_grid_and_confidence(self):
        a=np.array([[1.,1.],[17.,1.],[33.,1.],[49.,1.]])
        b=np.array([[1.,1.],[2.,2.],[17.,1.],[33.,1.]])
        confidence=np.array([.99,.98,.94,.89])
        self.assertEqual(bilateral_sample(a,b,confidence,.95).tolist(),[0])
        self.assertEqual(bilateral_sample(a,b,confidence,.9).tolist(),[0,2])

    def test_empty_and_pair_cap(self):
        self.assertEqual(len(bilateral_sample(np.empty((0,2)),np.empty((0,2)),np.empty(0),.9)),0)
        points=np.array([[16.*i,0] for i in range(2000)])
        self.assertEqual(len(bilateral_sample(points,points,np.ones(2000),.9)),1500)


if __name__=='__main__':unittest.main()
