import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_reconstruction_metrics import block_interval,summarize

class BlockSummaryTests(unittest.TestCase):
    def test_constant_paired_effect_remains_constant(self):
        x=np.arange(30).reshape(3,10)
        d=block_interval((x+2)-x)
        self.assertEqual((d['mean'],d['lower'],d['upper']),(2.,2.,2.))

    def test_missing_seeds_do_not_receive_three_seed_interval(self):
        r=summarize([dict(method='stg-full',seed=0,iteration=1000,complete=True,frames=[])])
        self.assertIn('incomplete',r['stg-full']['status'])
        self.assertEqual(r['timing_correction_benefit']['status'],'unavailable')

    def test_mismatched_checkpoint_cohort_is_rejected(self):
        runs=[dict(method='stg-full',seed=s,iteration=1000+s,complete=True,frames=[]) for s in range(3)]
        self.assertIn('mismatched',summarize(runs)['stg-full']['status'])

    def test_matched_cohort_effect_and_cross_method_checkpoint_guard(self):
        runs=[]
        for method,shift in [('stg-full',0),('freetimegs',2)]:
            for seed in range(3):
                frames=[dict(split='heldout-camera',frame_id=f,
                    full=dict(psnr=20+shift+seed+f,ssim=.8,lpips_alex=.2),
                    dynamic=None,motion_pixels=dict(psnr=10+shift,mae=.1)) for f in range(50)]
                runs.append(dict(method=method,seed=seed,iteration=1000,complete=True,frames=frames))
        result=summarize(runs)
        effect=result['paired_methods_at_zero']['metrics']['heldout-camera/full/psnr']
        self.assertEqual((effect['mean'],effect['lower'],effect['upper']),(2.,2.,2.))
        for run in runs[3:]:run['iteration']=2000
        self.assertFalse(summarize(runs)['paired_methods_at_zero']['metrics'])
