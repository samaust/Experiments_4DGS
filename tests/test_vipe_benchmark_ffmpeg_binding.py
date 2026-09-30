"""CPU request/result fixtures for managed FFmpeg import binding."""
import base64
import copy
import hashlib
import os
from pathlib import Path
import sys
import subprocess
import textwrap
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np
from scripts.vipe_benchmark import runtime
from scripts.vipe_benchmark.files import file_record, read_json, write_json


class FFmpegBindingTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.binary = self.root / 'lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
        self.binary.parent.mkdir(parents=True)
        self.binary.write_bytes(b'fixture managed executable')
        self.binary.chmod(0o755)
        digest = base64.urlsafe_b64encode(hashlib.sha256(self.binary.read_bytes()).digest()).decode().rstrip('=')
        relative = Path('imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2')
        self.distribution = SimpleNamespace(version='0.6.0', files=[relative],
            locate_file=lambda value: self.binary.parent.parent.parent / value,
            read_text=lambda name: f'{relative},sha256={digest},{self.binary.stat().st_size}\n')
        assets = self.root / 'assets.json'
        write_json(assets, {})
        self.request = self.root / 'request.json'
        write_json(self.request, dict(environment='E5', assets=file_record(assets), forbidden_vipe_roots=[]))
        self.torch = SimpleNamespace(__version__='2.5.1+cu124',
            nn=SimpleNamespace(Module=type('Module', (), {'_call_impl': lambda *args: None})),
            cuda=SimpleNamespace(is_initialized=lambda: False))
        self.modules = dict(torch=self.torch, torchvision=SimpleNamespace(__version__='0.20.1+cu124'),
                            cv2=SimpleNamespace(__version__='fixture'))
        self.target = dict(python=f'{sys.version_info.major}.{sys.version_info.minor}',
                          torch='2.5.1+cu124', torchvision='0.20.1+cu124', numpy=np.__version__)

    def qualify(self, imports):
        with patch.dict(sys.modules, self.modules), patch.dict(runtime.TARGETS, E5=self.target), \
             patch('importlib.metadata.distribution', return_value=self.distribution), \
             patch.object(sys, 'prefix', str(self.root)), \
             patch('scripts.vipe_benchmark.isolation.deny_vipe', return_value={'subprocesses': False}), \
             patch.object(runtime, '_native_api_imports', side_effect=imports):
            runtime.qualify_imports(self.request, self.root / 'imports.json')
        return read_json(self.root / 'imports.json')

    def test_qualification_binds_verified_wheel_binary_before_offline_imports(self):
        def imports(*args):
            self.assertEqual(os.environ['IMAGEIO_FFMPEG_EXE'], str(self.binary))
            self.assertEqual(os.environ['FFMPEG_BINARY'], 'ffmpeg-imageio')
            with self.assertRaisesRegex(RuntimeError, 'network access'):
                import socket
                socket.create_connection(('fixture.invalid', 80))
            with self.assertRaisesRegex(RuntimeError, 'model forwards'):
                self.torch.nn.Module()._call_impl()
            return []
        with patch.dict(os.environ, IMAGEIO_FFMPEG_EXE='/untrusted/ffmpeg', FFMPEG_BINARY='/untrusted/override'):
            result = self.qualify(imports)
        self.assertEqual(result['ffmpeg']['executable'], file_record(self.binary))
        self.assertEqual(result['ffmpeg']['distribution_version'], '0.6.0')
        self.assertEqual(result['forwards'], 0)
        self.assertFalse(result['cuda_context_initialized'])
        self.assertFalse(result['isolation']['subprocesses'])

    def test_changed_missing_or_unmanaged_binary_refuses_imports_and_result(self):
        for variant in ('changed', 'missing', 'unmanaged', 'non-executable', 'version'):
            with self.subTest(variant=variant):
                original = self.binary.read_bytes()
                original_locator = self.distribution.locate_file
                if variant == 'changed':
                    self.binary.write_bytes(b'changed bytes')
                elif variant == 'missing':
                    self.binary.unlink()
                elif variant == 'unmanaged':
                    self.distribution.locate_file = lambda value: Path('/usr/bin/ffmpeg')
                elif variant == 'non-executable':
                    self.binary.chmod(0o644)
                else:
                    self.distribution.version = 'unprescribed'
                imports = unittest.mock.Mock()
                with self.assertRaises((ValueError, FileNotFoundError)):
                    self.qualify(imports)
                imports.assert_not_called()
                self.assertFalse((self.root / 'imports.json').exists())
                self.binary.write_bytes(original)
                self.binary.chmod(0o755)
                self.distribution.locate_file = original_locator
                self.distribution.version = '0.6.0'

    def runtime_request(self, result):
        interpreter = str(self.root / 'bin/python')
        inventory = self.root / 'inventory.json'
        write_json(inventory, dict(executable=interpreter, packages=[dict(name='imageio-ffmpeg',
            version='0.6.0', files=[result['ffmpeg']['executable']])]))
        return dict(python=interpreter, versions=self.target,
            inventory=file_record(inventory), imports=file_record(self.root / 'imports.json'))

    def test_d2_runtime_rechecks_setup_binding_and_refuses_substitution(self):
        from scripts.vipe_benchmark.ffmpeg_binding import bind_runtime
        result = self.qualify(lambda *args: [])
        runtime_request = self.runtime_request(result)
        with patch('importlib.metadata.distribution', return_value=self.distribution), \
             patch.object(sys, 'prefix', str(self.root)), \
             patch.dict(os.environ, IMAGEIO_FFMPEG_EXE='/caller/override', FFMPEG_BINARY='/caller/override'):
            observed = bind_runtime(runtime_request)
            self.assertEqual(observed, result['ffmpeg'])
            self.assertEqual(os.environ['IMAGEIO_FFMPEG_EXE'], str(self.binary))
            self.assertEqual(os.environ['FFMPEG_BINARY'], 'ffmpeg-imageio')
            self.binary.write_bytes(b'changed after qualification')
            with self.assertRaises(ValueError):
                bind_runtime(runtime_request)
        missing = self.root / 'missing-binding.json'
        write_json(missing, dict(environment='E5'))
        with self.assertRaisesRegex(ValueError, 'lacks qualified'):
            bind_runtime(dict(imports=file_record(missing)))

    def test_d2_refuses_substituted_receipts_inventory_and_managed_root(self):
        from scripts.vipe_benchmark.ffmpeg_binding import bind_runtime
        result = self.qualify(lambda *args: [])
        original = self.runtime_request(result)
        for variant in ('missing-receipt', 'substituted-binary', 'foreign-root', 'missing-inventory',
                        'wrong-inventory-hash', 'not-offline', 'cuda-initialized'):
            with self.subTest(variant=variant):
                request = copy.deepcopy(original)
                imports = copy.deepcopy(result)
                inventory = read_json(original['inventory']['path'])
                if variant == 'missing-receipt':
                    del imports['ffmpeg']
                elif variant == 'substituted-binary':
                    replacement = self.root / 'replacement-executable'
                    replacement.write_bytes(b'substituted executable')
                    imports['ffmpeg']['executable'] = file_record(replacement)
                elif variant == 'foreign-root':
                    request['python'] = str(self.root / 'another-environment/bin/python')
                    inventory['executable'] = request['python']
                elif variant == 'missing-inventory':
                    inventory['packages'] = []
                elif variant == 'wrong-inventory-hash':
                    inventory['packages'][0]['files'][0]['sha256'] = '0' * 64
                elif variant == 'not-offline':
                    imports['offline'] = False
                else:
                    imports['cuda_context_initialized'] = True
                imports_path = self.root / (variant + '-imports.json')
                inventory_path = self.root / (variant + '-inventory.json')
                write_json(imports_path, imports)
                write_json(inventory_path, inventory)
                request.update(imports=file_record(imports_path), inventory=file_record(inventory_path))
                with patch('importlib.metadata.distribution', return_value=self.distribution), \
                     patch.object(sys, 'prefix', str(self.root)), \
                     patch.dict(os.environ, IMAGEIO_FFMPEG_EXE='/unchanged/invalid'):
                    with self.assertRaises(ValueError):
                        bind_runtime(request)
                    self.assertEqual(os.environ['IMAGEIO_FFMPEG_EXE'], '/unchanged/invalid')

    def test_d2_worker_import_boundary_propagates_verified_setup_binding(self):
        from scripts.vipe_benchmark import stages
        result = self.qualify(lambda *args: [])
        self.torch.cuda = SimpleNamespace(is_available=lambda: True, init=lambda: None,
            get_device_name=lambda: 'fixture RTX 4090', manual_seed_all=lambda value: None,
            reset_peak_memory_stats=lambda: None)
        self.torch.manual_seed = lambda value: None
        self.torch.version = SimpleNamespace(cuda='fixture')
        request = dict(component='D2', runtime=self.runtime_request(result), forbidden_vipe_roots=[])
        def guard(*args, **kwargs):
            self.assertEqual(os.environ['IMAGEIO_FFMPEG_EXE'], str(self.binary))
            self.assertEqual(os.environ['FFMPEG_BINARY'], 'ffmpeg-imageio')
            return {'subprocesses': False}
        with patch.dict(sys.modules, self.modules), \
             patch('importlib.metadata.distribution', return_value=self.distribution), \
             patch.object(sys, 'prefix', str(self.root)), \
             patch('scripts.vipe_benchmark.isolation.deny_vipe', side_effect=guard), \
             patch.dict(os.environ, IMAGEIO_FFMPEG_EXE='/caller/override'), \
             patch('socket.create_connection'), patch('socket.socket.connect'), patch('socket.socket.connect_ex'):
            observed = stages._model_runtime(request)
        self.assertFalse(observed['isolation']['subprocesses'])

    def test_real_audit_guard_remains_closed_after_qualifier_binding(self):
        # Audit hooks cannot be removed; keep this fixture in its own CPU child.
        child = textwrap.dedent(r"""
            import base64, hashlib, os, sys, subprocess
            from pathlib import Path
            from types import SimpleNamespace
            from unittest.mock import patch
            import numpy as np
            from scripts.vipe_benchmark import runtime
            from scripts.vipe_benchmark.files import read_json
            root, request = Path(sys.argv[1]), Path(sys.argv[2])
            binary = root / 'lib/python3.11/site-packages/imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
            relative = 'imageio_ffmpeg/binaries/ffmpeg-linux-x86_64-v7.0.2'
            digest = base64.urlsafe_b64encode(hashlib.sha256(binary.read_bytes()).digest()).decode().rstrip('=')
            distribution = SimpleNamespace(version='0.6.0', files=[relative],
                locate_file=lambda value: binary.parent.parent.parent / value,
                read_text=lambda name: f'{relative},sha256={digest},{binary.stat().st_size}\n')
            torch = SimpleNamespace(__version__='2.5.1+cu124',
                nn=SimpleNamespace(Module=type('Module', (), {'_call_impl': lambda *args: None})),
                cuda=SimpleNamespace(is_initialized=lambda: False))
            fake = dict(torch=torch, torchvision=SimpleNamespace(__version__='0.20.1+cu124'),
                        cv2=SimpleNamespace(__version__='fixture'))
            target = dict(python=f'{sys.version_info.major}.{sys.version_info.minor}',
                torch='2.5.1+cu124', torchvision='0.20.1+cu124', numpy=np.__version__)
            def imports(*args):
                assert os.environ['IMAGEIO_FFMPEG_EXE'] == str(binary)
                try:
                    subprocess.run([str(binary), '-version'], check=True)
                except PermissionError as error:
                    assert 'subprocesses are prohibited' in str(error)
                else:
                    raise AssertionError('subprocess isolation was relaxed')
                return []
            with patch.dict(sys.modules, fake), patch.dict(runtime.TARGETS, E5=target), \
                 patch('importlib.metadata.distribution', return_value=distribution), \
                 patch.object(sys, 'prefix', str(root)), \
                 patch.object(runtime, '_native_api_imports', side_effect=imports):
                runtime.qualify_imports(request, root / 'child-imports.json')
            evidence = read_json(root / 'child-imports.json')
            assert evidence['isolation']['subprocesses'] is False
            assert evidence['forwards'] == 0 and evidence['cuda_context_initialized'] is False
        """)
        completed = subprocess.run([sys.executable, '-B', '-c', child, str(self.root), str(self.request)],
                                   text=True, capture_output=True, timeout=30)
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == '__main__':
    unittest.main()
