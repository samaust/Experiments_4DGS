"""CPU fixtures for setup ordering, provenance and transfer limits."""
from contextlib import contextmanager
import hashlib
import io
from pathlib import Path
import signal
import subprocess
import sys
import tarfile
import tempfile
from types import ModuleType, SimpleNamespace
import unittest
from unittest.mock import Mock, patch

from scripts.vipe_benchmark import backends, runtime, setup_recipes
from scripts.vipe_benchmark.budgets import budget_snapshot
from scripts.vipe_benchmark.files import file_record, read_json, verify_record, write_json


class Response(io.BytesIO):
    def __init__(self, value, *, declared=True):
        super().__init__(value)
        self.headers = {'Content-Length': str(len(value))} if declared else {}
        self.read_sizes = []

    def geturl(self):
        return 'https://fixture.invalid/blob'

    def read(self, size=-1):
        self.read_sizes.append(size)
        return super().read(size)


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.config = dict(new_download_gib_limit=1, new_artifact_disk_gib_limit=1)

    def test_download_stops_before_over_budget_read_and_retains_received_bytes(self):
        response = Response(b'abcdef')
        with patch.object(runtime.urllib.request, 'urlopen', return_value=response) as opened:
            with self.assertRaisesRegex(ValueError, 'before next read'):
                runtime.download('https://fixture.invalid/blob', self.root / 'data.bin', self.root / 'transfers',
                                 limit=3, artifact_limit=10**6)
        opened.assert_called_once()
        self.assertEqual(response.read_sizes, [3])
        self.assertEqual((self.root / 'data.bin.partial').read_bytes(), b'abc')
        self.assertEqual(budget_snapshot(self.root)['download_bytes'], 3)
        receipt = read_json(next((self.root / 'transfers').glob('transfer-*.json')))
        self.assertEqual(receipt['bytes_received'], 3)
        self.assertEqual(receipt['partial_identity']['size'], 3)
        self.assertIsNotNone(receipt['error'])
        with patch.object(runtime.urllib.request, 'urlopen') as retry:
            with self.assertRaisesRegex(ValueError, 'exists without reuse'):
                runtime.download('https://fixture.invalid/blob', self.root / 'data.bin', self.root / 'transfers',
                                 limit=3, artifact_limit=10**6)
            retry.assert_not_called()

    def test_download_known_length_finishes_at_exact_cap_without_eof_probe(self):
        response = Response(b'abcd')
        with patch.object(runtime.urllib.request, 'urlopen', return_value=response):
            record = runtime.download('https://fixture.invalid/blob', self.root / 'data.bin', self.root / 'transfers',
                                      limit=4, artifact_limit=10**6)
        self.assertEqual(response.read_sizes, [4])
        verify_record(record)
        self.assertEqual(budget_snapshot(self.root)['download_bytes'], 4)
        receipt = read_json(next((self.root / 'transfers').glob('transfer-*.json')))
        self.assertEqual(receipt['partial_identity']['inode'], receipt['output_identity']['inode'])
        self.assertIsNone(receipt['error'])

    def test_download_exhausted_allocation_never_opens_network(self):
        with patch.object(runtime.urllib.request, 'urlopen') as opened:
            with self.assertRaisesRegex(ValueError, 'before opening URL'):
                runtime.download('https://fixture.invalid/blob', self.root / 'data.bin', self.root / 'transfers',
                                 limit=0, artifact_limit=10**6)
            opened.assert_not_called()

    def test_unknown_length_does_not_probe_one_byte_past_allocation(self):
        response = Response(b'abcd', declared=False)
        with patch.object(runtime.urllib.request, 'urlopen', return_value=response):
            with self.assertRaisesRegex(ValueError, 'before next read'):
                runtime.download('https://fixture.invalid/blob', self.root / 'data.bin', self.root / 'transfers',
                                 limit=4, artifact_limit=10**6)
        self.assertEqual(response.read_sizes, [4])
        self.assertEqual(budget_snapshot(self.root)['download_bytes'], 4)

    def test_read_exception_retains_reservation_for_internally_consumed_unknown_bytes(self):
        response = Response(b'abcdef')
        def read(count):
            response.read_sizes.append(count)
            block = io.BytesIO.read(response, min(count, 2))
            if len(response.read_sizes) == 2:
                raise OSError('fixture transport consumed bytes before reporting an error')
            return block
        with patch.object(response, 'read', side_effect=read), \
             patch.object(runtime.urllib.request, 'urlopen', return_value=response):
            with self.assertRaisesRegex(OSError, 'consumed bytes'):
                runtime.download('https://fixture.invalid/blob', self.root / 'data.bin', self.root / 'transfers',
                                 limit=6, artifact_limit=10**6)
        self.assertEqual(response.read_sizes, [6, 4])
        self.assertEqual((self.root / 'data.bin.partial').read_bytes(), b'ab')
        receipt = read_json(next((self.root / 'transfers').glob('transfer-*.json')))
        self.assertEqual(receipt['bytes_received'], 2)
        self.assertEqual(receipt['received_or_reserved_upper_bound'], 6)
        self.assertEqual(budget_snapshot(self.root)['download_bytes'], 6)

    def test_sigkill_during_mocked_read_cannot_erase_reserved_download_bytes(self):
        code = '''
import os
from pathlib import Path
import signal
import sys
from scripts.vipe_benchmark import runtime
class Response:
    headers = {'Content-Length': '4'}
    def geturl(self):
        return 'https://fixture.invalid/blob'
    def __enter__(self):
        return self
    def __exit__(self, *args):
        return False
    def read(self, count):
        os.kill(os.getpid(), signal.SIGKILL)
runtime.urllib.request.urlopen = lambda *args, **kwargs: Response()
root = Path(sys.argv[1])
runtime.download('https://fixture.invalid/blob', root / 'data.bin', root / 'transfers',
                 limit=4, artifact_limit=10**6)
'''
        process = subprocess.run([sys.executable, '-c', code, str(self.root)], cwd=runtime.ROOT,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.assertEqual(process.returncode, -signal.SIGKILL, process.stderr)
        self.assertFalse(list((self.root / 'transfers').glob('transfer-*.json')))
        self.assertEqual((self.root / 'data.bin.partial').stat().st_size, 0)
        self.assertEqual(budget_snapshot(self.root)['download_bytes'], 4)

    def test_source_extraction_preserves_executable_modes_and_skips_forbidden_payload(self):
        revision = 'a' * 40
        archive = self.root / 'source.tar'
        with tarfile.open(archive, 'w') as stream:
            for name, value, mode in [('script.sh', b'executable fixture', 0o755),
                                      ('prompts/skip.txt', b'not extracted', 0o644)]:
                info = tarfile.TarInfo('source-' + revision + '/' + name)
                info.mode, info.size = mode, len(value)
                stream.addfile(info, io.BytesIO(value))
        opened = []
        extract = tarfile.TarFile.extractfile
        def observed(source, member):
            opened.append(member.name)
            return extract(source, member)
        with patch.object(tarfile.TarFile, 'extractfile', observed):
            record = runtime.extract_source(archive, self.root / 'source', revision)
        self.assertEqual(record['files'][0]['mode'], 0o755)
        self.assertEqual(len(opened), 1)
        self.assertFalse((self.root / 'source/prompts').exists())

    def test_tree_record_preserves_logical_hf_snapshot_paths(self):
        snapshot = self.root / 'snapshots' / ('a' * 40)
        snapshot.mkdir(parents=True)
        blob = self.root / 'blob'
        blob.write_bytes(b'fake checkpoint')
        (snapshot / 'model.safetensors').symlink_to(blob)
        record = runtime.tree_record(snapshot, 'a' * 40)
        self.assertEqual(record['files'][0]['path'], str(snapshot / 'model.safetensors'))
        verify_record(record['files'][0])

    def test_checkpoint_keeps_pinned_repository_tree_and_license_evidence(self):
        source = self.root / 'source'
        source.mkdir()
        (source / 'source.py').write_text('fixture')
        source_record = runtime.tree_record(source, backends.SOURCE_PINS['depth_pro_source'])
        payloads = {'depth_pro.pt': b'checkpoint', 'README.md': b'license model card', 'LICENSE': b'terms'}
        tree = [dict(path=name, type='file', size=len(value), **(
            dict(lfs={'oid': hashlib.sha256(value).hexdigest()}) if name.endswith('.pt') else
            dict(oid=hashlib.sha1(f'blob {len(value)}\0'.encode() + value).hexdigest())))
                for name, value in payloads.items()]
        def download(url, path, transfer_dir, *, limit):
            path.parent.mkdir(parents=True, exist_ok=True)
            if '/api/models/' in url:
                write_json(path, tree)
            else:
                path.write_bytes(payloads[url.rsplit('/', 1)[1]])
            return file_record(path)
        request = dict(components=['D4'], historical_assets={}, reuse_assets={'depth_pro_source': source_record},
                       transfer_dir=str(self.root / 'transfers'))
        with patch.object(runtime, 'download', side_effect=download):
            assets = runtime.acquire_assets(request, self.root / 'output', self.config)
        checkpoint = assets['depth_pro_checkpoint']
        write_json(self.root / 'serialized-assets.json', assets)
        self.assertEqual(checkpoint['revision'], runtime.REMOTE_ASSETS['depth_pro_checkpoint'][1])
        self.assertEqual(len(checkpoint['repository_files']), 3)
        self.assertEqual({Path(r['path']).name for r in checkpoint['license_files']}, {'README.md', 'LICENSE'})
        verify_record(checkpoint['source_tree'])

    def test_sam2_checkpoint_metadata_serializes_without_self_reference(self):
        _, existing = self.fixture_request('E2')
        payloads = {'sam2.1_hiera_large.pt': b'sam2 checkpoint', 'README.md': b'fixture model license'}
        tree = [dict(path=name, type='file', size=len(value), lfs={'oid': hashlib.sha256(value).hexdigest()})
                for name, value in payloads.items()]
        def download(url, path, transfer_dir, *, limit):
            path.parent.mkdir(parents=True, exist_ok=True)
            if '/api/models/' in url:
                write_json(path, tree)
            else:
                path.write_bytes(payloads[url.rsplit('/', 1)[1]])
            return file_record(path)
        request = dict(components=['S4'], historical_assets={key: existing[key] for key in
                       ('sam2_source', 'rtdetr_snapshot')}, reuse_assets={}, transfer_dir=str(self.root / 'transfers'))
        with patch.object(runtime, 'download', side_effect=download):
            assets = runtime.acquire_assets(request, self.root / 'output', self.config)
        path = self.root / 'serialized-sam2.json'
        write_json(path, assets)
        record = read_json(path)['sam2_checkpoint']
        self.assertEqual(record['revision'], runtime.REMOTE_ASSETS['sam2_checkpoint'][1])
        self.assertEqual(len(record['repository_files']), 2)
        self.assertEqual(Path(record['license_files'][0]['path']).name, 'README.md')
        verify_record(record['source_tree'])

    def test_grounding_historical_bytes_must_match_pinned_hf_identity(self):
        payload = b'published fixture checkpoint'
        checkpoint = self.root / 'groundingdino_swint_ogc.pth'
        checkpoint.write_bytes(payload)
        model_card = b'fixture asset license'
        tree = [dict(type='file', path=checkpoint.name, size=len(payload),
                     lfs={'oid': hashlib.sha256(payload).hexdigest()}),
                dict(type='file', path='README.md', size=len(model_card),
                     oid=hashlib.sha1(f'blob {len(model_card)}\0'.encode() + model_card).hexdigest())]
        def download(url, path, transfer_dir, *, limit):
            self.assertIn(runtime.GROUNDING_WEIGHT_PIN[1], url)
            path.parent.mkdir(parents=True, exist_ok=True)
            if '/api/models/' in url:
                write_json(path, tree)
            else:
                path.write_bytes(model_card)
            return file_record(path)
        request = dict(transfer_dir=str(self.root / 'transfers'))
        assets = {'grounding_checkpoint': file_record(checkpoint)}
        with patch.object(runtime, 'download', side_effect=download):
            runtime._grounding_weight_provenance(assets, request, self.root / 'verified', self.config)
        write_json(self.root / 'grounding-assets.json', assets)
        self.assertEqual(assets['grounding_checkpoint']['revision'], runtime.GROUNDING_WEIGHT_PIN[1])
        self.assertTrue(assets['grounding_checkpoint']['license_files'])
        checkpoint.write_bytes(b'different historical bytes')
        with patch.object(runtime, 'download', side_effect=download):
            with self.assertRaisesRegex(ValueError, 'do not match the prescribed S2'):
                runtime._grounding_weight_provenance({'grounding_checkpoint': file_record(checkpoint)}, request,
                                                    self.root / 'mismatch', self.config)

    def test_source_refresh_preserves_historical_vipe_record_without_traversal(self):
        historical = dict(path=str(self.root / 'never-inspect-vipe'), revision='a' * 40,
                          files=[dict(path='historical-exact-record', sha256='b' * 64)])
        assets = {'vipe_source': historical}
        baseline = self.root / 'assets-before-build.json'
        write_json(baseline, assets)
        with patch.object(runtime, 'tree_record', side_effect=AssertionError('historical traversal')):
            refreshed = runtime._refresh_sources(assets, file_record(baseline))
        self.assertEqual(refreshed['vipe_source'], historical)

    def fixture_request(self, environment):
        request = dict(environment=environment, job_id=environment + '-setup',
            components=sorted(c for c, e in runtime.ENVIRONMENTS.items() if e == environment),
            run_root=str(self.root), uv=str(self.root / 'uv'), uv_cache=str(self.root / 'setup-cache'),
            python_install_dir=str(self.root / 'managed-python'), transfer_dir=str(self.root / 'transfers'),
            toolkit_directory=str(self.root / 'toolkits/cuda-12.4.1'),
            forbidden_vipe_roots=[str(self.root / 'historical-vipe')], historical_assets={}, reuse_assets={},
            no_runtime_fallback=True, no_automatic_retry=True, **setup_recipes.recipe(environment))
        names = {name for component in request['components'] for name in backends.REQUIRED_ASSETS[component]}
        assets = {}
        for name in names:
            path = self.root / 'fixtures' / name
            if name.endswith(('_source', '_snapshot')):
                path.mkdir(parents=True)
                (path / 'LICENSE').write_text('fixture license')
                if name.endswith('_snapshot'):
                    (path / 'config.json').write_text('{}')
                    (path / 'model.safetensors').write_bytes(b'checkpoint')
                revision = backends.SOURCE_PINS.get(name, backends.SNAPSHOT_PINS.get(name, 'a' * 40))
                assets[name] = runtime.tree_record(path, revision)
            else:
                path.mkdir(parents=True)
                file = path / backends.CHECKPOINT_NAMES.get(name, name)
                file.write_bytes(b'fixture asset')
                assets[name] = file_record(file)
        return request, assets

    def fake_subprocess(self, request, assets, events, *, fail_label=None):
        def run(command, **kwargs):
            events.append((command, dict(kwargs['env'])))
            if command[0] == request['uv']:
                self.assertEqual(kwargs['env']['HTTPS_PROXY'], 'http://fixture-proxy')
                self.assertEqual(kwargs['env']['UV_HTTP_RETRIES'], '0')
            if fail_label and any(fail_label in part for part in command):
                raise subprocess.CalledProcessError(1, command)
            if command[1] == 'venv':
                (Path(command[-1]) / 'bin').mkdir(parents=True)
            elif 'compile' in command:
                Path(command[command.index('--output-file') + 1]).write_text('# fixture hash lock\n')
            elif '-e' in command:
                source = Path(command[-1])
                (source / 'generated-native.so').write_bytes(b'fixture compiled artifact')
            elif '--qualify-imports' in command:
                write_json(command[-1], dict(status='complete', forwards=0,
                           cuda_context_initialized=bool(request.get('_fixture_cuda_initialized'))))
            elif 'runtime_inventory.py' in command[1]:
                requirements = request['requirements'] + ([request['native_correlation']] if request['native_correlation'] else [])
                packages = [dict(name=name, version=version, license='fixture license', files=[])
                            for name, version in runtime._fixed_versions(requirements).items()]
                write_json(command[-1], dict(versions=runtime.TARGETS[request['environment']], packages=packages))
            return subprocess.CompletedProcess(command, 0)
        return run

    @contextmanager
    def mocked_setup(self, request, assets, events, *, fail_label=None):
        module = ModuleType('scripts.vipe_benchmark.transfer_proxy')
        checks, entries = [], []
        @contextmanager
        def proxy(*args, **kwargs):
            entries.append((args, kwargs))
            yield SimpleNamespace(environment={'HTTPS_PROXY': 'http://fixture-proxy'}, check=lambda: checks.append(True))
        module.uv_proxy = proxy
        build_env = dict(CUDA_HOME=request['toolkit_directory'], CPATH='fixture-headers',
                         SAM2_BUILD_CUDA='1', SAM2_BUILD_ALLOW_ERRORS='0', TORCH_CUDA_ARCH_LIST='8.9', MAX_JOBS='8')
        def correlation(req, output, config):
            path = output / 'correlation.tar.gz'
            path.write_bytes(b'fixture correlation source')
            return file_record(path)
        with patch.dict(sys.modules, {'scripts.vipe_benchmark.transfer_proxy': module}), \
             patch.object(runtime, 'acquire_assets', return_value=assets), \
             patch.object(runtime, '_correlation_asset', side_effect=correlation), \
             patch('scripts.vipe_benchmark.toolkit.acquire_toolkit', return_value={'path': request['toolkit_directory']}), \
             patch('scripts.vipe_benchmark.toolkit.build_environment', return_value={'env': build_env}) as toolkit_build, \
             patch.object(runtime.subprocess, 'run', side_effect=self.fake_subprocess(request, assets, events, fail_label=fail_label)):
            yield SimpleNamespace(entries=entries, checks=checks, toolkit_build=toolkit_build)

    def test_e1_setup_orders_torch_toolkit_correlation_and_imports_and_refreshes_sources(self):
        request, assets = self.fixture_request('E1')
        events = []
        output = self.root / 'E1'
        with self.mocked_setup(request, assets, events) as state:
            runtime.setup(request, output, self.config)
        commands = [command for command, _ in events]
        self.assertEqual(commands[0][1], 'venv')
        self.assertIn('torch==2.5.1+cu124', commands[1])
        state.toolkit_build.assert_called_once()
        self.assertEqual(len(state.entries), len([c for c in commands if c[0] == request['uv']]))
        self.assertEqual(len(state.checks), len(state.entries))
        native = next(i for i, c in enumerate(commands) if str(output / 'correlation.tar.gz') in c)
        resolved = next(i for i, c in enumerate(commands) if 'compile' in c)
        self.assertLess(resolved, native)
        self.assertEqual(events[native][1]['CUDA_HOME'], request['toolkit_directory'])
        self.assertEqual(events[native][1]['UV_OFFLINE'], '1')
        self.assertIn('--no-build-isolation', commands[native])
        self.assertTrue((Path(assets['samtrack_source']['path']) / 'aot').is_symlink())
        result = read_json(output / 'result.json')
        self.assertEqual(result['setup_attempts'], 1)
        current = read_json(result['assets']['path'])
        changes = current['grounding_source']['generated_file_changes']
        self.assertTrue(any(Path(item['path']).name == 'generated-native.so' and item['change'] == 'added' for item in changes))
        self.assertTrue(current['samtrack_source']['generated_links'])
        for key in ('inventory', 'imports', 'dependency_lock', 'build_inputs'):
            verify_record(result['runtime'][key])

    def test_e2_requires_sam2_extension_flags_and_exact_transformers(self):
        request, assets = self.fixture_request('E2')
        request['_fixture_cuda_initialized'] = True
        events = []
        with self.mocked_setup(request, assets, events):
            runtime.setup(request, self.root / 'E2', self.config)
        command, env = next((c, e) for c, e in events if '-e' in c and c[-1] == assets['sam2_source']['path'])
        self.assertEqual(env['SAM2_BUILD_CUDA'], '1')
        self.assertEqual(env['SAM2_BUILD_ALLOW_ERRORS'], '0')
        self.assertIn('--no-deps', command)
        self.assertIn('transformers==4.51.3', (self.root / 'E2/constraints.txt').read_text())
        self.assertTrue(read_json(self.root / 'E2/imports.json')['cuda_context_initialized'])

    def test_failed_build_has_no_success_and_never_restarts_existing_attempt(self):
        request, assets = self.fixture_request('E2')
        events = []
        with self.mocked_setup(request, assets, events, fail_label=assets['grounding_source']['path']):
            with self.assertRaises(subprocess.CalledProcessError):
                runtime.setup(request, self.root / 'E2', self.config)
            count = len(events)
            with self.assertRaises(FileExistsError):
                runtime.setup(request, self.root / 'E2', self.config)
        self.assertEqual(len(events), count)
        self.assertFalse((self.root / 'E2/result.json').exists())
        receipts = sorted((self.root / 'E2/commands').glob('*.json'))
        self.assertIn('CalledProcessError', read_json(receipts[-1])['error'])

    def test_inventory_rejects_prescribed_non_torch_pin_changes(self):
        request, _ = self.fixture_request('E2')
        packages = [dict(name=name, version=version) for name, version in runtime._fixed_versions(request['requirements']).items()]
        next(p for p in packages if p['name'] == 'transformers')['version'] = '4.52.0'
        with self.assertRaisesRegex(ValueError, 'transformers==4.51.3'):
            runtime._check_inventory(dict(versions=runtime.TARGETS['E2'], packages=packages), request)

    def test_recipe_mutation_cannot_start_build(self):
        request, _ = self.fixture_request('E2')
        request['requirements'] = [r.replace('4.51.3', '4.52.0') for r in request['requirements']]
        with patch.object(runtime.subprocess, 'run') as process:
            with self.assertRaisesRegex(ValueError, 'changes a prescribed'):
                runtime.setup(request, self.root / 'E2', self.config)
            process.assert_not_called()

    def test_import_qualification_checks_symbols_without_calling_native_builder(self):
        source = self.root / 'source'
        source.mkdir()
        file = source / 'native.py'
        file.write_text('fixture native definitions')
        builder = Mock(side_effect=AssertionError('builder must not run'))
        native = SimpleNamespace(__file__=str(file), build=builder)
        with patch.dict(setup_recipes.CORE_IMPORTS, E7=[('native', 'depth_pro_source', ['build'])]), \
             patch('importlib.import_module', return_value=native):
            rows = runtime._native_api_imports('E7', {'depth_pro_source': {'path': str(source)}})
        builder.assert_not_called()
        verify_record(rows[0]['file'])

    def test_import_qualification_rejects_python_stub_for_mandatory_extension(self):
        source = self.root / 'source'
        source.mkdir()
        file = source / '_C.py'
        file.write_text('fixture stub')
        with patch.dict(setup_recipes.CORE_IMPORTS, E2=[('sam2._C', 'sam2_source', [])]), \
             patch('importlib.import_module', return_value=SimpleNamespace(__file__=str(file))):
            with self.assertRaisesRegex(ValueError, 'mandatory compiled'):
                runtime._native_api_imports('E2', {'sam2_source': {'path': str(source)}})

    def test_import_qualification_rejects_aot_fallback(self):
        source = self.root / 'source'
        source.mkdir()
        file = source / 'attention.py'
        file.write_text('fixture definitions')
        with patch.dict(setup_recipes.CORE_IMPORTS,
                        E1=[('networks.layers.attention', 'aot_source', ['enable_corr'])]), \
             patch('importlib.import_module', return_value=SimpleNamespace(__file__=str(file), enable_corr=False)):
            with self.assertRaisesRegex(ValueError, 'implicit fallback'):
                runtime._native_api_imports('E1', {'aot_source': {'path': str(source)}})

    def test_qualifier_blocks_model_forward_and_truthfully_records_incidental_cuda_init(self):
        import numpy as np
        from scripts.vipe_benchmark import isolation
        class FakeModule:
            def _call_impl(self, *args):
                raise AssertionError('unguarded forward executed')
        fake_torch = SimpleNamespace(__version__='2.5.1+cu124', nn=SimpleNamespace(Module=FakeModule),
                                     cuda=SimpleNamespace(is_initialized=lambda: True))
        fake_vision = SimpleNamespace(__version__='0.20.1+cu124')
        assets = self.root / 'assets.json'
        write_json(assets, {})
        request = self.root / 'imports-request.json'
        write_json(request, dict(environment='E1', assets=file_record(assets), forbidden_vipe_roots=[]))
        actual = dict(python=f'{sys.version_info.major}.{sys.version_info.minor}', numpy=np.__version__,
                      torch=fake_torch.__version__, torchvision=fake_vision.__version__)
        def imports(*args):
            with self.assertRaisesRegex(RuntimeError, 'model forwards'):
                FakeModule()._call_impl()
            return []
        with patch.dict(sys.modules, torch=fake_torch, torchvision=fake_vision,
                        cv2=SimpleNamespace(__version__='fixture')), \
             patch.dict(runtime.TARGETS, E1=actual), \
             patch.object(isolation, 'deny_vipe', return_value={'fixture': True}), \
             patch.object(runtime, '_native_api_imports', side_effect=imports):
            runtime.qualify_imports(request, self.root / 'imports.json')
        result = read_json(self.root / 'imports.json')
        self.assertEqual(result['forwards'], 0)
        self.assertTrue(result['cuda_context_initialized'])


if __name__ == '__main__':
    unittest.main()
