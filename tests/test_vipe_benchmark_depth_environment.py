"""Metered depth setup shares one bounded environment provisioning interface."""
from pathlib import Path
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.depth_environment import provision_depth_environment
from vipe_benchmark.files import file_record, read_json, write_json


class DepthEnvironmentTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        seed = self.root / 'seed/bin/python'
        seed.parent.mkdir(parents=True)
        seed.write_bytes(b'fixture Python3.11')
        uv = self.root / 'uv'
        uv.write_bytes(b'fixture uv')
        source = self.root / 'source-requirements.txt'
        source.write_text('torch>=2\nnumpy\n')
        self.request = dict(schema='plan069-depth-environment-request/v1',
            candidate='D7', record_kind='fixture', python_version='3.11',
            python_seed_executable=str(seed.absolute()), python_seed=file_record(seed),
            uv=file_record(uv), requirements=['torch>=2', 'numpy', 'setuptools', 'wheel'],
            constraints=['torch==2.5.1+cu124', 'torchvision==0.20.1+cu124', 'numpy==1.26.4'],
            requirement_sources=[file_record(source)], indexes=['https://pypi.org/simple',
                'https://download.pytorch.org/whl/cu124'], sources=[])
        self.config = dict(new_download_gib_limit=110, new_artifact_disk_gib_limit=210)
        self.output = self.root / 'jobs/plan069-D7-setup-001/runtime'
        self.calls = []

    def tearDown(self):
        self.temporary.cleanup()

    def run_fixture(self, command, *, environment, cwd, timeout, log):
        self.assertGreater(timeout, 0)
        self.assertEqual(environment['UV_HTTP_RETRIES'], '0')
        self.assertEqual(environment['PYTHONNOUSERSITE'], '1')
        self.assertNotIn('PYTHONPATH', environment)
        self.assertNotIn('PYTHONHOME', environment)
        self.calls.append(command)
        log.write_text('fixture command completed\n')
        if '-c' in command:
            log.write_text('{"python_version":"3.11"}\n')
        if 'venv' in command:
            python = Path(command[-1]) / 'bin/python'
            python.parent.mkdir(parents=True)
            python.write_bytes(b'isolated fixture Python')
        if 'compile' in command:
            Path(command[command.index('--output-file') + 1]).write_text('numpy==1.26.4 --hash=sha256:fixture\n')
        if '--output' in command:
            python = str(self.output / 'environment/bin/python')
            write_json(command[command.index('--output') + 1], dict(executable=python,
                versions=dict(python='3.11', torch='2.5.1+cu124',
                    torchvision='0.20.1+cu124', numpy='1.26.4'),
                inventory_only=True, model_imports=False, gpu_operations=False,
                packages=[dict(name=name, version=version, files=[]) for name, version in
                    [('torch','2.5.1+cu124'), ('torchvision','0.20.1+cu124'),
                     ('numpy','1.26.4'), ('setuptools','80.9.0'), ('wheel','0.45.1')]]))

    def provision(self, request=None, runner=None):
        return provision_depth_environment(request or self.request, self.output, self.config,
            run_root=self.root, deadline=time.monotonic() + 60,
            download_limit=10**7, artifact_limit=10**7, runner=runner or self.run_fixture)

    def test_isolated_environment_has_hash_lock_exact_interpreter_and_command_receipts(self):
        result = self.provision()
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(result['python_executable'], str(self.output / 'environment/bin/python'))
        venv = next(command for command in self.calls if 'venv' in command)
        self.assertIn('--no-python-downloads', venv)
        self.assertEqual(venv[venv.index('--python') + 1], self.request['python_seed_executable'])
        install = next(command for command in self.calls if 'install' in command)
        self.assertIn('--require-hashes', install)
        self.assertTrue(result['dependency_lock']['sha256'])
        self.assertEqual(len(result['command_receipts']), len(self.calls))
        self.assertTrue(all(read_json(row['path'])['automatic_retries'] == 0
                            for row in result['command_receipts']))
        with self.assertRaisesRegex(ValueError, 'immutable'):
            self.provision()

    def test_unmetered_git_requirement_and_actual_fixture_injection_are_rejected_before_commands(self):
        for request in [dict(self.request, requirements=['utils3d @ git+https://example.org/source']),
                        dict(self.request, record_kind='actual')]:
            with self.assertRaises(ValueError):
                self.provision(request)
            self.assertEqual(self.calls, [])
            self.assertFalse(self.output.exists())

    def test_command_failure_is_receipted_without_retry(self):
        def failing(command, **kwargs):
            self.run_fixture(command, **kwargs)
            if 'compile' in command:
                raise RuntimeError('fixture resolver failure')
        with self.assertRaisesRegex(RuntimeError, 'resolver failure'):
            self.provision(runner=failing)
        failures = [read_json(path) for path in (self.output / 'commands').glob('*.json')
                    if read_json(path)['error'] is not None]
        self.assertEqual(len(failures), 1)
        self.assertEqual(failures[0]['automatic_retries'], 0)
        self.assertEqual(sum('compile' in command for command in self.calls), 1)
        self.assertEqual(read_json(self.output / 'failure.json')['status'], 'failed')

    def test_changed_requirement_source_is_rejected_before_environment_creation(self):
        Path(self.request['requirement_sources'][0]['path']).write_text('changed requirements')
        with self.assertRaisesRegex(ValueError, 'changed file'):
            self.provision()
        self.assertEqual(self.calls, [])
        self.assertFalse(self.output.exists())

    def test_local_archive_is_installed_offline_and_preserved_as_provenance(self):
        archive = self.root / 'utils3d.tar.gz'
        archive.write_bytes(b'fixture pinned archive')
        source = dict(name='utils3d', revision='a' * 40,
                      record=file_record(archive), install_local_offline=True)
        self.request['sources'] = [source]
        def fixture(command, **kwargs):
            self.run_fixture(command, **kwargs)
            if '--output' in command:
                path = Path(command[command.index('--output') + 1])
                inventory = read_json(path)
                inventory['packages'].append(dict(name='utils3d', version='0.1.0', files=[]))
                path.unlink()
                write_json(path, inventory)
        result = self.provision(runner=fixture)
        installs = [command for command in self.calls if str(archive) in command]
        self.assertEqual(len(installs), 1)
        self.assertIn('--offline', installs[0])
        self.assertIn('--no-deps', installs[0])
        self.assertEqual(result['source_packages'], [source])
        receipt = next(read_json(row['path']) for row in result['command_receipts']
                       if str(archive) in read_json(row['path'])['command'])
        self.assertTrue(receipt['offline'])

    def test_actual_environment_requires_active_parent_reservation_before_native_commands(self):
        parent = self.root / 'requests/plan069-D7-setup-001.json'
        write_json(parent, dict(candidate='D7', job_id='plan069-D7-setup-001',
                               record_kind='actual'))
        request = dict(self.request, record_kind='actual',
                       ledger_path=str(self.root / 'ledger.jsonl'), setup_request=file_record(parent))
        with self.assertRaisesRegex(ValueError, 'active exact depth setup reservation'):
            provision_depth_environment(request, self.output, self.config,
                run_root=self.root, deadline=time.monotonic() + 60,
                download_limit=10**7, artifact_limit=10**7)
        self.assertFalse(self.output.exists())

    def test_moge_install_uses_official_scoped_cache_and_disables_cuda_build(self):
        import os
        import io
        import tarfile
        from vipe_benchmark.moge_source_build import REVISION, derive_flex_archive
        payload = (Path(__file__).parent / 'fixtures/plan069-flex-gemm/setup.py.txt').read_bytes()
        original = self.root / 'flex-original.tar.gz'
        with tarfile.open(original, 'w:gz') as archive:
            info = tarfile.TarInfo('FlexGEMM-' + REVISION + '/setup.py')
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload))
        derived = derive_flex_archive(file_record(original), self.root / 'flex-derived.tar.gz')
        request = dict(self.request, candidate='D5', sources=[derived],
            flex_cache_path=str(self.output / 'flex-cache/autotune_cache.json'))
        homes = {name: os.environ.get(name) for name in ('HOME', 'CODEX_HOME')}
        def fixture(command, **kwargs):
            environment = kwargs['environment']
            self.assertEqual(environment['FLEX_GEMM_AUTOTUNE_CACHE_PATH'], request['flex_cache_path'])
            self.assertEqual(environment['FLEX_GEMM_BUILD_CUDA'], '0')
            self.assertEqual(environment['BUILD_CUDA'], '0')
            for name, value in homes.items():
                self.assertEqual(environment.get(name), value)
            self.run_fixture(command, **kwargs)
            if '--output' in command:
                path = Path(command[command.index('--output') + 1])
                inventory = read_json(path)
                inventory['packages'].append(dict(name='flex_gemm', version='1.0.0', files=[]))
                path.unlink()
                write_json(path, inventory)
        result = self.provision(request=request, runner=fixture)
        self.assertEqual(result['source_packages'], [derived])
        self.assertEqual(result['flex_cache_path'], request['flex_cache_path'])
