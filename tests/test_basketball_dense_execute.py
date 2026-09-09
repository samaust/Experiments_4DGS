"""Fixed experimental order and resource gates for Plan 027."""
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import basketball_dense_execute as execute
from basketball_dense_training import ARMS


class ExecutionTests(unittest.TestCase):
    def test_all_first_endpoints_precede_absolute_continuations(self):
        trained, evaluated = [], []
        def train(arm, seed, target, output, resume=None, **kwargs):
            trained.append((arm,seed,target,resume))
        with patch('basketball_dense_resources.projection',return_value={'fits':True}), \
                patch.object(execute,'train',side_effect=train), \
                patch.object(execute,'invoke',side_effect=lambda module,args:evaluated.append((module.__name__,args))), \
                patch.object(execute,'state'):
            execute.production()
        self.assertEqual([r[2] for r in trained], [5000]*6+[50000]*6)
        expected=[(arm,seed) for seed in range(3) for arm in ARMS]
        self.assertEqual([r[:2] for r in trained[:6]],expected)
        self.assertEqual([r[:2] for r in trained[6:]],expected)
        self.assertTrue(all(r[3] is None for r in trained[:6]))
        for arm,seed,_,parent in trained[6:]:
            self.assertEqual(parent.parts[-3:],(f'{arm}-seed{seed}','005000','checkpoint-005000.pt'))
        self.assertEqual(sum(name=='basketball_dense_evaluate' for name,_ in evaluated),30)
        self.assertEqual(sum(name=='basketball_dense_metrics' for name,_ in evaluated),10)

    def test_insufficient_storage_prevents_any_training(self):
        with patch('basketball_dense_resources.projection',return_value={'fits':False}), patch.object(execute,'train') as train:
            with self.assertRaisesRegex(RuntimeError,'storage pause'):
                execute.production()
            train.assert_not_called()


if __name__ == '__main__':
    unittest.main()
