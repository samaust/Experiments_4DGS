import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('stg_train_source', ROOT/'scripts/stg_train_source.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class UpstreamHookTests(unittest.TestCase):
    def test_unknown_source_is_rejected(self):
        with self.assertRaisesRegex(ValueError, 'hash differs'):
            module.adapt_train('print("unexpected upstream")')

    def test_pinned_local_source_preserves_core_training(self):
        path = ROOT/'.local/SpacetimeGaussians/train.py'
        if not path.exists():
            self.skipTest('requires pinned upstream checkout')
        source = path.read_text()
        adapted = module.adapt_train(source)
        compile(adapted, 'adapted_train.py', 'exec')
        for fragment in ('loss.backward()', 'gaussians.cache_gradient()',
                         'gaussians.set_batch_gradient(opt.batch)', 'flag = controlgaussians(',
                         'totalNnewpoints = gaussians.addgaussians('):
            self.assertEqual(adapted.count(fragment), source.count(fragment))
        self.assertIn('cam.source_frame == 4120+i', adapted)
        self.assertIn('hooks.before_loop(gaussians, opt, locals())', adapted)
        self.assertIn('hooks.after_iteration(gaussians, opt, iteration, locals())', adapted)
