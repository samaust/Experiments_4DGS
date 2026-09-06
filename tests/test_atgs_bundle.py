import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atgs_bundle import save_bundle, inspect_bundle, load_bundle_supplements
from atgs_checkpoint import MODEL_FILES
from test_atgs_loop_state import make


class BundleTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name) / 'checkpoint'
        self.provenance = dict(manifest_sha256='a' * 64, source_revision='b' * 40,
                               config_sha256='c' * 64, helper_ast_sha256='d' * 64)
        self.model, self.sampler, a, b = make()
        key = next(self.sampler)
        (a + b).sum().backward()
        self.loop = dict(iteration=1, micro_steps=1, encoder_visits={key[1]: 1},
                         update_count=0, last_update_iteration=0, ema_loss=.5)
        self.model.time_embedding = torch.nn.Linear(1, 1)
        self.model.spatial_lr_scale = 1.
        self.model.voxel_size = .01
        self.model.percent_dense = .01
        self.model.save_ply = lambda path: Path(path).write_bytes(b'fixture-ply')
        self.model.save_mlp_checkpoints = self.save_native
        self.model.save_optimizer = self.save_optimizers

    def save_native(self, directory):
        for name in MODEL_FILES[1:]:
            torch.save({'fixture': torch.ones(1)}, Path(directory) / name)

    def save_optimizers(self, directory):
        for name in ('optimizer', 'dy_optimizer'):
            torch.save(getattr(self.model, name).state_dict(), Path(directory) / (name + '.pth'))

    def save(self):
        return save_bundle(self.directory, self.model, self.sampler, self.loop,
                           self.provenance, include_cuda=False)

    def test_committed_round_trip_and_no_overwrite(self):
        record = self.save()
        auxiliary, supplement, loaded = load_bundle_supplements(
            self.directory, expected_provenance=self.provenance)
        self.assertEqual(loaded, record)
        self.assertEqual(supplement['loop'], self.loop)
        self.assertEqual(auxiliary['schema'], 'atgs-auxiliary/v1')
        self.assertEqual(len(record['files']), 11)
        self.assertFalse((self.directory / 'bundle.json.pending').exists())
        with self.assertRaises(FileExistsError):
            self.save()
        self.assertEqual(inspect_bundle(self.directory, expected_provenance=self.provenance), record)

    def test_interrupted_write_has_no_completion_marker(self):
        with patch.object(self.model, 'save_optimizer', side_effect=RuntimeError('synthetic interrupted write')):
            with self.assertRaisesRegex(RuntimeError, 'synthetic interrupted'):
                self.save()
        self.assertTrue(self.directory.is_dir())
        with self.assertRaisesRegex(ValueError, 'completion marker'):
            inspect_bundle(self.directory, expected_provenance=self.provenance)

    def test_wrong_provenance_and_corrupt_component_rejected(self):
        self.save()
        wrong = dict(self.provenance, config_sha256='e' * 64)
        with self.assertRaisesRegex(ValueError, 'provenance mismatch'):
            inspect_bundle(self.directory, expected_provenance=wrong)
        with (self.directory / 'loop.pth').open('ab') as stream:
            stream.write(b'corruption')
        with patch('atgs_bundle.torch.load') as loader:
            with self.assertRaisesRegex(ValueError, 'inventory mismatch'):
                load_bundle_supplements(self.directory, expected_provenance=self.provenance)
            loader.assert_not_called()

    def test_marker_counter_and_symlink_rejected(self):
        record = self.save()
        record['iteration'] = 99
        (self.directory / 'bundle.json').write_text(json.dumps(record))
        with self.assertRaisesRegex(ValueError, 'counters mismatch'):
            load_bundle_supplements(self.directory, expected_provenance=self.provenance)
        linked = self.directory.parent / 'linked'
        linked.symlink_to(self.directory, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, 'linked'):
            inspect_bundle(linked, expected_provenance=self.provenance)
