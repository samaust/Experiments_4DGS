from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from freetimegs_training import load_training

CHECKOUT = Path(__file__).resolve().parents[1] / '.local/FreeTimeGsVanilla'
try:
    import fused_ssim
    import gsplat
    AVAILABLE = True
except ImportError:
    AVAILABLE = False


@unittest.skipUnless(AVAILABLE and CHECKOUT.is_dir(), 'FreeTimeGS native dependencies unavailable')
class NativeTrainingSourceTests(unittest.TestCase):
    def test_preset_and_all_step_components(self):
        cfg, methods, evidence = load_training(CHECKOUT)
        self.assertEqual(cfg.max_steps, 70000)
        self.assertEqual(cfg.relocation_stop_iter, 63000)
        self.assertEqual(cfg.densification_start_step, 100)
        self.assertEqual(cfg.strategy.refine_start_iter, 100000)
        self.assertEqual(cfg.init_duration, -1.)  # Preserve native sentinel semantics.
        self.assertEqual(cfg.lambda_perc, .01)
        self.assertEqual(len(methods), 4)
        self.assertEqual(len(evidence['training_ast_sha256']), 64)

    def test_changed_source_fails_closed(self):
        with patch('pathlib.Path.read_bytes', return_value=b'changed'):
            with self.assertRaisesRegex(ValueError, 'audit required'):
                load_training(CHECKOUT)
