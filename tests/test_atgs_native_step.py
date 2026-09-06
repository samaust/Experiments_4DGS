from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atgs_native_step import NativeTrainingStep, load_loss_helpers


class NativeStepTests(unittest.TestCase):
    def make(self):
        image = torch.nn.Parameter(torch.full((3, 4, 4), .5))
        model = SimpleNamespace(update_learning_rate=Mock(), training_statis=Mock(),
                                adjust_anchor=Mock(), optimizer=None, dy_optimizer=None,
                                dynamic_module=SimpleNamespace(routing_encoder_id=lambda t: 0))
        camera = SimpleNamespace(time=.1, original_image=torch.full_like(image, .25))
        package = dict(render=image, scaling=torch.full((2, 3), 2.), neural_points=None,
                       viewspace_points=None, neural_opacity=None, visibility_filter=None, selection_mask=None)
        sanitize = Mock()
        step = NativeTrainingStep(scene=None,
            opt=SimpleNamespace(start_stat=1, update_until=4, update_from=2, update_interval=2,
                                success_threshold=.8, densify_grad_threshold=.001, min_opacity=.01,
                                lambda_dssim=.2), pipe=None, cfg=SimpleNamespace(hash=True, primitive_type='3dgs'),
            background=torch.zeros(3), render=Mock(return_value=package), prefilter=Mock(return_value=True),
            losses={'l1_loss': lambda a, b: (a - b).abs().mean(), 'ssim': lambda a, b: (a.mean(),)},
            updates={'sanitize_accumulated_gradients': sanitize})
        return step, model, camera, image, sanitize

    def test_loss_statistics_and_densification_order(self):
        step, model, camera, image, sanitize = self.make()
        encoder, loss = step.camera_step(model, camera, 2)
        self.assertEqual(encoder, 0)
        self.assertAlmostEqual(loss, .8 * .25 + .2 * .5 + .01 * 8)
        self.assertIsNotNone(image.grad)
        sanitize.assert_called_once()
        model.training_statis.assert_called_once()
        self.assertTrue(step.force_update_due(2))
        with self.assertRaisesRegex(ValueError, 'completed optimizer update'):
            step.after_microstep(model, 2, False)
        step.after_microstep(model, 2, True)
        model.adjust_anchor.assert_called_once()

    def test_cleanup_and_target_validation(self):
        step, model, camera, image, _ = self.make()
        model.opacity_accum = torch.ones(1)
        self.assertFalse(step.statistics_active(4))
        step.after_microstep(model, 4, False)
        self.assertFalse(hasattr(model, 'opacity_accum'))
        camera.original_image = torch.zeros(1)
        with self.assertRaisesRegex(ValueError, 'target'):
            step.camera_step(model, camera, 1)
        self.assertIsNone(image.grad)

    @unittest.skipUnless(Path('.local/ATGS/utils/loss_utils.py').exists(), 'ATGS checkout unavailable')
    def test_native_loss_helpers_without_metric_import(self):
        helpers, digest = load_loss_helpers('.local/ATGS')
        image = torch.rand(3, 16, 16, requires_grad=True)
        self.assertEqual(helpers['l1_loss'](image, image).item(), 0.)
        self.assertAlmostEqual(helpers['ssim'](image, image)[0].item(), 1.)
        helpers['ssim'](image, torch.zeros_like(image))[0].backward()
        self.assertTrue(torch.isfinite(image.grad).all())
        self.assertEqual(len(digest), 64)
