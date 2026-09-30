"""CPU provenance fixtures contain files, without importing model implementations."""
import json
import os
from types import SimpleNamespace
from unittest.mock import patch
import stat
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record, write_json
from vipe_benchmark.s1_evidence import qualify_runtime
from test_vipe_benchmark_s1_recovery import synthetic_assets


class S1RuntimeProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        def put(name, value):
            path = self.root / name
            write_json(path, value)
            return file_record(path)
        assets, runtime, self.observed = synthetic_assets(self.root, put)
        for tree in assets.values():
            for record in tree.get('files', []):
                record['mode'] = stat.S_IMODE(Path(record['path']).stat().st_mode)
        self.assets = assets
        self.request = dict(runtime=runtime, assets=assets, forbidden_vipe_roots=['/fixture/vipe'])
        self.target = assets['sam_source']['files'][-1]

    def test_mode_bearing_admitted_source_is_accepted(self):
        qualify_runtime(self.observed, self.request)

    def test_changed_source_bytes_are_rejected(self):
        Path(self.target['path']).write_bytes(b'changed CPU fixture')
        with self.assertRaisesRegex(ValueError, 'progress source bytes changed'):
            qualify_runtime(self.observed, self.request)

    def test_substituted_source_path_is_rejected(self):
        replacement = self.root / 'sam_source/substituted.py'
        replacement.write_bytes(Path(self.target['path']).read_bytes())
        self.target['path'] = str(replacement)
        with self.assertRaisesRegex(ValueError, 'import differs from admitted source tree'):
            qualify_runtime(self.observed, self.request)

    def test_changed_source_mode_is_rejected_independently(self):
        Path(self.target['path']).chmod(self.target['mode'] ^ stat.S_IXUSR)
        with self.assertRaisesRegex(ValueError, 'admitted source mode changed'):
            qualify_runtime(self.observed, self.request)


    def test_invalid_source_mode_record_is_rejected(self):
        self.target['mode'] = None
        with self.assertRaisesRegex(ValueError, 'admitted source mode changed'):
            qualify_runtime(self.observed, self.request)

    def test_required_attention_alias_remains_mandatory(self):
        manifest = json.loads(Path(self.observed['loaded_files']['path']).read_text())
        for entry in manifest['files']:
            entry['modules'] = [name for name in entry['modules'] if name != 'aot.networks.layers.attention']
        path = self.root / 'loaded-without-alias.json'
        write_json(path, manifest)
        self.observed['loaded_files'] = file_record(path)
        with self.assertRaisesRegex(ValueError, 'loaded native/import identity differs from E1'):
            qualify_runtime(self.observed, self.request)

    def test_backend_loads_both_pinned_attention_aliases_without_real_imports(self):
        from vipe_benchmark import backends
        calls = []
        noop = lambda *args, **kwargs: None
        torch = SimpleNamespace(float32='float32',
            cuda=SimpleNamespace(is_available=lambda: True, manual_seed_all=noop),
            hub=SimpleNamespace(download_url_to_file=noop, load_state_dict_from_url=noop),
            manual_seed=noop)
        model = SimpleNamespace()
        model.to = lambda **kwargs: model
        model.eval = lambda: model
        sam = SimpleNamespace(sam_model_registry={'vit_b': lambda **kwargs: model}, SamPredictor=lambda model: object())
        aot_root = Path(self.assets['aot_source']['path'])
        attention_file = next(item['path'] for item in self.assets['aot_source']['files']
                              if item['path'].endswith('/networks.layers.attention.py'))
        attention = SimpleNamespace(enable_corr=True, __file__=attention_file)
        def module(bundle, name, source):
            calls.append((name, source))
            if name == 'segment_anything': return sam
            if name == 'aot_tracker': return SimpleNamespace()
            if name in ('networks.layers.attention', 'aot.networks.layers.attention'): return attention
            raise AssertionError('unexpected model import')
        def imported(name):
            if name == 'torch': return torch
            if name == 'aot': return SimpleNamespace(__path__=[str(aot_root)])
            raise AssertionError('unexpected native import')
        with patch.object(backends.AssetBundle, 'module', autospec=True, side_effect=module), patch.object(backends.importlib, 'import_module', side_effect=imported), patch.object(backends, '_grounding', return_value=object()), patch.object(backends, '_s1_tracker', return_value=object()), patch.dict(os.environ, HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1'), patch.object(sys, 'path', list(sys.path)):
            backend = backends.build_backend('S1', self.assets)
        self.assertEqual([call for call in calls if call[0].endswith('layers.attention')],
                         [('networks.layers.attention', 'aot_source'), ('aot.networks.layers.attention', 'aot_source')])
        self.assertEqual(backend.runtime.device, 'cuda')


if __name__ == '__main__':
    unittest.main()
