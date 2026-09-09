"""Exercise the actual adapted native optimizer guard beyond update 30,000."""
import ast
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_study_train import extend_stg, adapted_stg_worker


class STGExtensionTests(unittest.TestCase):
    def test_complete_adapted_worker_compiles(self):
        path = Path(__file__).resolve().parents[1] / 'scripts/train-stg-manifest.py'
        source = adapted_stg_worker(path.read_text())
        compile(source, '<study-worker>', 'exec')
        self.assertIn('step_complete_monotonic-self.training_start', source)
        self.assertIn("os.replace(a.output/'checkpoint-next.pt', a.output/'checkpoint.pt')", source)
        self.assertIn("local['camindex']", source)

    def test_native_optimizer_receives_update_after_30000(self):
        import torch
        path = Path(__file__).resolve().parents[1] / '.local/SpacetimeGaussians/train.py'
        if not path.exists():
            self.skipTest('pinned STG checkout unavailable')
        source = extend_stg(path.read_text(), source_frames=[0, 1, 25, 26])
        tree = ast.parse(source)
        guards = [n for n in ast.walk(tree) if isinstance(n, ast.If)
                  and ast.unparse(n.test) == 'iteration <= hooks.target_update']
        self.assertEqual(len(guards), 1)
        parameter = torch.nn.Parameter(torch.tensor([1.]))
        optimizer = torch.optim.SGD([parameter], lr=.1)
        parameter.square().sum().backward()
        module = ast.Module(body=guards, type_ignores=[])
        namespace = dict(iteration=30001, hooks=SimpleNamespace(target_update=50000),
                         opt=SimpleNamespace(iterations=30000),
                         gaussians=SimpleNamespace(optimizer=optimizer))
        exec(compile(module, '<native-optimizer-guard>', 'exec'), namespace)
        self.assertAlmostEqual(parameter.item(), .8, places=6)
        self.assertIsNone(parameter.grad)
        self.assertIn('range(first_iter, hooks.target_update + 1)', source)
        self.assertIn('gaussians.update_learning_rate(iteration)', source)

    def test_modified_native_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            extend_stg('arbitrary replacement training source')

    def test_native_position_decay_retains_final_rate(self):
        import numpy as np
        path = Path(__file__).resolve().parents[1] / '.local/SpacetimeGaussians/thirdparty/gaussian_splatting/utils/general_utils.py'
        if not path.exists():
            self.skipTest('pinned STG checkout unavailable')
        functions = [n for n in ast.parse(path.read_text()).body
                     if isinstance(n, ast.FunctionDef) and n.name == 'get_expon_lr_func']
        self.assertEqual(len(functions), 1)
        namespace = {'np': np}
        exec(compile(ast.Module(body=functions, type_ignores=[]), str(path), 'exec'), namespace)
        schedule = namespace['get_expon_lr_func'](lr_init=.00016, lr_final=.0000016, max_steps=30000)
        self.assertEqual(schedule(30000), schedule(30001))
        self.assertEqual(schedule(30000), schedule(50000))


if __name__ == '__main__':
    unittest.main()
