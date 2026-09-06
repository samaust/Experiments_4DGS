import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atgs_checkpoint import MODEL_FILES, OPTIMIZER_FILES, inspect_native_checkpoint
from atgs_checkpoint import capture_auxiliary_state, restore_auxiliary_state
from atgs_checkpoint import assert_state_equal
from atgs_checkpoint import tensor_difference
from atgs_checkpoint import capture_gradients, compare_gradients
from types import SimpleNamespace
import torch


class ATGSCheckpointTests(unittest.TestCase):
    def test_gradient_snapshots_are_independent_and_presence_is_checked(self):
        parameter = torch.nn.Parameter(torch.tensor([2.]))
        model = SimpleNamespace(optimizer=torch.optim.Adam([parameter]),
                                dy_optimizer=torch.optim.Adam([torch.nn.Parameter(torch.ones(1))]))
        parameter.square().sum().backward()
        first = capture_gradients(model)
        parameter.grad.add_(1)
        second = capture_gradients(model)
        differences = compare_gradients(first, second)
        self.assertEqual(differences['optimizer/0:unnamed/0'], 1.)
        self.assertIsNone(differences['dy_optimizer/0:unnamed/0'])
        parameter.grad = None
        with self.assertRaisesRegex(ValueError, 'presence'):
            compare_gradients(first, capture_gradients(model))
        with self.assertRaisesRegex(ValueError, 'labels'):
            compare_gradients(first, {})

    def test_tensor_difference_reports_errors_and_rejects_invalid_inputs(self):
        a = torch.tensor([1., 2.])
        self.assertEqual(tensor_difference(a, a.clone()), 0.)
        self.assertEqual(tensor_difference(a, a + .5), .5)
        self.assertEqual(tensor_difference(torch.empty(0), torch.empty(0)), 0.)
        with self.assertRaisesRegex(ValueError, 'nonfinite'):
            tensor_difference(a, torch.tensor([float('nan'), 2.]))
        with self.assertRaisesRegex(ValueError, 'structure'):
            tensor_difference(a, torch.ones(3))

    def test_optimizer_comparison_detects_step_moment_and_structure_changes(self):
        import copy
        expected = {'state': {0: {'step': torch.tensor(3.), 'exp_avg': torch.ones(2)}},
                    'param_groups': [{'params': [0], 'lr': .001}]}
        assert_state_equal(expected, copy.deepcopy(expected))
        for key in ('step', 'exp_avg'):
            changed = copy.deepcopy(expected)
            changed['state'][0][key].add_(1)
            with self.assertRaises(AssertionError):
                assert_state_equal(expected, changed)
        with self.assertRaises(AssertionError):
            assert_state_equal(expected, {})

    def model(self):
        model = SimpleNamespace(optimizer=None, time_embedding=torch.nn.Embedding(3, 2),
                                spatial_lr_scale=2., voxel_size=.01, percent_dense=.1)
        for name in ('_anchor', '_offset', '_opacity', '_scaling', '_rotation', '_anchor_feat'):
            setattr(model, name, torch.nn.Parameter(torch.ones(2, 3), requires_grad=name != '_opacity'))
        model.point_times_list = torch.ones(2, 4, dtype=torch.bool)
        return model

    def test_auxiliary_roundtrip_preserves_values_flags_and_lifetimes(self):
        original, restored = self.model(), self.model()
        state = capture_auxiliary_state(original)
        with torch.no_grad():
            original._anchor.add_(3)
        restore_auxiliary_state(restored, state, device='cpu')
        self.assertTrue(torch.equal(restored._anchor, torch.ones(2, 3)))
        self.assertFalse(restored._opacity.requires_grad)
        self.assertTrue(restored._anchor.requires_grad)
        self.assertEqual(restored.point_times_list.dtype, torch.bool)
        self.assertTrue(torch.equal(restored.time_embedding.weight, original.time_embedding.weight))

    def test_auxiliary_requires_complete_state_and_unbound_optimizer(self):
        model = self.model()
        state = capture_auxiliary_state(model)
        del state['tensors']['_offset']
        with self.assertRaisesRegex(ValueError, 'missing required'):
            restore_auxiliary_state(model, state, device='cpu')
        state = capture_auxiliary_state(model)
        model.optimizer = object()
        with self.assertRaisesRegex(ValueError, 'before optimizer'):
            restore_auxiliary_state(model, state, device='cpu')

    def populate(self, directory):
        for name in MODEL_FILES:
            (directory / name).write_bytes(b'fixture, not a real model')

    def test_model_inventory_and_optimizer_requirement(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.populate(root)
            inventory = inspect_native_checkpoint(root)
            self.assertEqual(set(inventory), set(MODEL_FILES))
            self.assertTrue(all(len(item['sha256']) == 64 for item in inventory.values()))
            with self.assertRaisesRegex(ValueError, 'optimizer.pth'):
                inspect_native_checkpoint(root, require_optimizers=True)
            for name in OPTIMIZER_FILES:
                (root / name).write_bytes(b'optimizer fixture')
            self.assertEqual(len(inspect_native_checkpoint(root, require_optimizers=True)), 9)

    def test_missing_empty_and_linked_components_rejected(self):
        for mode in ('missing', 'empty', 'linked'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                self.populate(root)
                path = root / 'voxel_grid.pth'
                path.unlink()
                if mode == 'empty':
                    path.touch()
                elif mode == 'linked':
                    path.symlink_to(root / 'FDHash.pth')
                with self.assertRaisesRegex(ValueError, 'voxel_grid.pth'):
                    inspect_native_checkpoint(root)
