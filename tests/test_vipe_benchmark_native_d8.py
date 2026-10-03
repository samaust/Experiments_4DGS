"""D8's actual loader rejects non-pinned bytes and incomplete state dictionaries."""

from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import native_d8
from vipe_benchmark.depth_native_packages import D8_CU130_PROFILE
from vipe_benchmark.files import file_record
from vipe_benchmark.depth_source_integrity import source_manifest


class Model:
    training = True

    def __init__(self, **config):
        self.config = config
        self.strict = None

    def load_state_dict(self, state, *, strict):
        self.strict = strict
        if not strict or state != {'weight': 1}:
            raise ValueError('incomplete native weights')

    def to(self, device):
        self.device = device
        return self

    def eval(self):
        self.training = False
        return self


class Torch:
    def __init__(self, state):
        self.state = state

    def load(self, path, *, map_location, weights_only):
        if map_location != 'cpu' or weights_only is not True:
            raise ValueError('unsafe checkpoint load')
        return dict(model_config={'encoder': 'vitl'}, model=self.state)


class NativeD8Tests(unittest.TestCase):
    def test_existing_pointmap_grid_contract_with_real_cpu_tensors(self):
        import numpy as np
        from tests.test_vipe_benchmark_moge2 import FakeMoGe2
        from vipe_benchmark.moge_metric import MetricAnythingPointMapAdapter, POINTMAP_PIN
        rgb = np.zeros((540, 960, 3), np.uint8)
        K = np.array([[800, 0, 480], [0, 800, 270], [0, 0, 1]], np.float64)
        valid = np.ones((540, 960), bool)
        model = FakeMoGe2()
        result = MetricAnythingPointMapAdapter(model, POINTMAP_PIN).predict(rgb, K, valid)
        self.assertEqual(result.values.shape, valid.shape)
        self.assertEqual(result.metadata['component'], 'D8')
        self.assertFalse(result.valid[0, 0])
        self.assertTrue(np.isnan(result.values[0, 0]))
        self.assertEqual(model.calls[0][0].shape, (3, 540, 960))
        with self.assertRaisesRegex(ValueError, 'predicted camera'):
            MetricAnythingPointMapAdapter(FakeMoGe2(predicted_camera=True), POINTMAP_PIN).predict(rgb, K, valid)
        with self.assertRaisesRegex(ValueError, 'camera-z differs'):
            MetricAnythingPointMapAdapter(FakeMoGe2(radial=True), POINTMAP_PIN).predict(rgb, K, valid)

    def test_strict_pinned_local_loader(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / 'source/models/student_pointmap/moge/model/v2.py'
            source.parent.mkdir(parents=True)
            source.write_text('# pinned source\n')
            requirements = root / 'source/models/student_pointmap/requirements.txt'
            requirements.write_text('torch<2.5.0\n')
            archive = root / 'source.tar.gz'
            archive.write_bytes(b'fixture archive')
            helper = source.parent / 'modules.py'
            helper.write_text('# pinned helper\n')
            weight = root / 'student_pointmap.pt'
            weight.write_bytes(b'fixture')
            record = file_record(weight)
            setup = dict(schema='plan069-depth-setup-result/v1', status='complete',
                candidate='D8', source_revision=native_d8.SOURCE_REVISION,
                source_dir=str(root / 'source'),
                native_source=file_record(source), source_archive=file_record(archive),
                runtime=dict(status='complete', python_executable=sys.executable,
                             native_qualification={'status': 'passed'},
                             compatibility_profile=dict(D8_CU130_PROFILE),
                             requirement_sources=[file_record(requirements)]),
                source_manifest=source_manifest(root / 'source'),
                assets=[dict(repository='metricanything', path='student_pointmap.pt',
                             record=record)])
            setup['runtime']['python_executable'] = str(root / 'wrong-python')
            with self.assertRaisesRegex(ValueError, 'exact prepared interpreter'):
                native_d8.load(setup, torch_module=Torch({'weight': 1}), model_class=Model)
            setup['runtime']['python_executable'] = sys.executable
            profile = setup['runtime'].pop('compatibility_profile')
            with self.assertRaisesRegex(ValueError, 'compatibility profile required'):
                native_d8.load(setup, torch_module=Torch({'weight': 1}), model_class=Model)
            setup['runtime']['compatibility_profile'] = profile
            original_requirement = setup['runtime']['requirement_sources']
            setup['runtime']['requirement_sources'] = []
            with self.assertRaisesRegex(ValueError, 'original requirements changed'):
                native_d8.load(setup, torch_module=Torch({'weight': 1}), model_class=Model)
            setup['runtime']['requirement_sources'] = original_requirement
            with patch('vipe_benchmark.depth_native_packages.qualify', return_value={'status': 'passed', 'packages_sha256': 'changed'}):
                with self.assertRaisesRegex(ValueError, 'qualification changed since setup'):
                    native_d8.load(setup, torch_module=Torch({'weight': 1}), model_class=Model)
            with patch('vipe_benchmark.depth_native_packages.qualify', side_effect=ValueError('dependency qualification failed')):
                with self.assertRaisesRegex(ValueError, 'dependency qualification failed'):
                    native_d8.load(setup, torch_module=Torch({'weight': 1}), model_class=Model)
            with patch.object(native_d8, 'WEIGHT_SHA256', record['sha256']), \
                    patch('vipe_benchmark.depth_native_packages.qualify', return_value={'status': 'passed'}):
                adapter = native_d8.load(setup, torch_module=Torch({'weight': 1}),
                                         model_class=Model)
                self.assertEqual(adapter.runtime.strict, True)
                self.assertEqual(adapter.runtime.device, 'cuda')
                self.assertFalse(adapter.runtime.training)
                with self.assertRaisesRegex(ValueError, 'incomplete native weights'):
                    native_d8.load(setup, torch_module=Torch({}), model_class=Model)
                helper.write_text('# edited executed module\n')
                with self.assertRaisesRegex(ValueError, 'source tree changed'):
                    native_d8.load(setup, torch_module=Torch({'weight': 1}), model_class=Model)
                helper.write_text('# pinned helper\n')
                weight.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'weights changed'):
                    native_d8.load(setup, torch_module=Torch({'weight': 1}),
                                   model_class=Model)


if __name__ == '__main__':
    unittest.main()
