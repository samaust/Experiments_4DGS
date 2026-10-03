"""MoGe recipes bind source requirements and offline pinned dependency archives."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record
from vipe_benchmark.moge_environment import environment_request, validate_environment_request


class EnvironmentRecipeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / 'source'
        self.source.mkdir()
        (self.source / 'pyproject.toml').write_text('''
[build-system]
requires = ["setuptools>=77.0.3"]
[project]
name = "moge"
dependencies = [
  "torch>=2.4", "torchvision>=0.19", "numpy>=2",
  "utils3d_moge @ git+https://github.com/EasternJournalist/utils3d-moge.git@62f09d58509485564e24d5d9f6aac9ee9ebc0c37",
  "pipeline @ git+https://github.com/EasternJournalist/pipeline.git@1c511390d90226c00c101f34b84df26a0f8789b4",
  "flex-gemm @ git+https://github.com/JeffreyXiang/FlexGEMM.git@b2fadb29d41846c7981ade6801ffc689fae119cf"
]
''')
        self.dependencies = {}
        for name, dependencies in (('utils3d_moge', ['moderngl', 'numpy', 'scipy']),
                                   ('pipeline', []),
                                   ('flex-gemm', ['torch>=2.4.0', 'triton>=3.2.0', 'filelock'])):
            directory = self.root / name
            directory.mkdir()
            (directory / 'pyproject.toml').write_text(
                '[build-system]\nrequires=["setuptools>=64", "wheel"]\n'
                '[project]\nname="' + name + '"\ndependencies=' + repr(dependencies) + '\n')
            if name == 'flex-gemm':
                (directory / 'setup.py').write_bytes((Path(__file__).parent / 'fixtures/plan069-flex-gemm/setup.py.txt').read_bytes())
            self.dependencies[name] = directory
        self.seed = self.root / 'seed-python'
        self.seed.write_bytes(b'fixture interpreter')
        self.uv = self.root / 'uv'
        self.uv.write_bytes(b'fixture uv executable')

    def test_d5_and_d6_freeze_compatible_torch_and_metered_git_sources(self):
        for candidate in ('D5', 'D6'):
            recipe = environment_request(candidate, self.source,
                python_seed_executable=self.seed, uv=self.uv, record_kind='fixture',
                dependency_sources=self.dependencies, runtime_directory=self.root / 'runtime')
            validate_environment_request(recipe, self.source, candidate, 'fixture')
            self.assertIn('torch==2.6.0+cu124', recipe['constraints'])
            self.assertIn('triton==3.2.0', recipe['constraints'])
            self.assertEqual(len(recipe['sources']), 3)
            self.assertFalse(any('git+' in dependency for dependency in recipe['requirements']))
            self.assertEqual(len(recipe['requirement_sources']), 4)
            self.assertIn('moderngl', recipe['requirements'])
            self.assertIn('filelock', recipe['requirements'])

    def test_changed_requirements_or_unpinned_source_is_rejected(self):
        recipe = environment_request('D6', self.source,
            python_seed_executable=self.seed, uv=self.uv, record_kind='fixture',
                dependency_sources=self.dependencies, runtime_directory=self.root / 'runtime')
        recipe['sources'][2]['revision'] = 'main'
        with self.assertRaisesRegex(ValueError, 'pinned offline source'):
            validate_environment_request(recipe, self.source, 'D6', 'fixture')
        recipe = environment_request('D6', self.source,
            python_seed_executable=self.seed, uv=self.uv, record_kind='fixture',
                dependency_sources=self.dependencies, runtime_directory=self.root / 'runtime')
        recipe['requirements'].append('unreviewed-dependency')
        with self.assertRaisesRegex(ValueError, 'source requirements'):
            validate_environment_request(recipe, self.source, 'D6', 'fixture')

    def test_setup_meters_pinned_sources_and_binds_environment_receipt(self):
        from io import BytesIO
        from types import ModuleType
        import tarfile
        from unittest.mock import patch
        import test_vipe_benchmark_moge_setup as fixtures
        from vipe_benchmark.files import read_json, write_json
        from vipe_benchmark.moge_setup import run_moge_setup
        setup = fixtures.MoGeSetupTests()
        setup.setUp()
        self.addCleanup(setup.tearDown)
        from vipe_benchmark.files import object_hash
        for candidate, saved in setup.requests.items():
            reviewed = read_json(saved['review']['path'])
            reviewed['proposals'][0]['allocation']['download_bytes'] = 100000
            review_path = setup.root / (candidate + '-environment-review.json')
            write_json(review_path, reviewed)
            authorized = read_json(saved['authorization']['path'])
            authorized['review'] = file_record(review_path)
            authorized['candidate_approvals'][0]['proposal_sha256'] = object_hash(reviewed['proposals'][0])
            auth_path = setup.root / (candidate + '-environment-approval.json')
            write_json(auth_path, authorized)
            saved.update(review=file_record(review_path), authorization=file_record(auth_path))

        recipe = environment_request('D6', self.source,
            python_seed_executable=self.seed, uv=self.uv, record_kind='fixture',
                dependency_sources=self.dependencies, runtime_directory=self.root / 'runtime')
        request = dict(setup.requests['D6'], runtime_environment=recipe)
        downloaded = []
        revision = '74fbce054ebed49800de42d0ad0e83495065719a'
        buffer = BytesIO()
        with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
            for name in ('moge/model/v2.py', 'moge/model/v3.py', 'pyproject.toml', 'LICENSE'):
                payload = ((self.source / name).read_bytes() if name == 'pyproject.toml'
                           else b'pinned fixture')
                info = tarfile.TarInfo(f'MoGe-{revision}/{name}')
                info.size = len(payload)
                archive.addfile(info, BytesIO(payload))
        def acquire(url, path, **options):
            if 'microsoft/MoGe' in url:
                payload = buffer.getvalue()
            elif path.name == 'model.pt':
                payload = setup.weight
            else:
                name = path.name.removesuffix('.tar.gz')
                package = next(row for row in recipe['sources'] if row['name'] == name)
                packed = BytesIO()
                with tarfile.open(fileobj=packed, mode='w:gz') as archive:
                    for filename in ('pyproject.toml', 'setup.py'):
                        original = self.dependencies[name] / filename
                        if not original.exists():
                            continue
                        data = original.read_bytes()
                        info = tarfile.TarInfo(name + '-' + package['revision'] + '/' + filename)
                        info.size = len(data)
                        archive.addfile(info, BytesIO(data))
                payload = packed.getvalue()
            path.write_bytes(payload)
            downloaded.append((url, options))
            transfers = options['run_root'] / 'transfers'
            transfers.mkdir(exist_ok=True)
            transfer_id = path.relative_to(options['run_root']).as_posix().replace('/', '-')
            write_json(transfers / (transfer_id + '.json'),
                dict(transfer_id=transfer_id,
                     output=str(path), bytes_received=len(payload)))
            return file_record(path)
        calls = []
        module = ModuleType('vipe_benchmark.depth_environment')
        def provision(recipe, output, config, **options):
            calls.append((recipe, options))
            output.mkdir()
            result = dict(status='complete', candidate=recipe['candidate'],
                          python_executable=str(output / 'env/bin/python'))
            write_json(output / 'result.json', result)
            return result
        module.provision_depth_environment = provision
        output = setup.root / request['job_id']
        with patch.dict(sys.modules, {'vipe_benchmark.depth_environment': module}):
            result = run_moge_setup(request, output, acquire=acquire)
        self.assertEqual(len(downloaded), 5)
        self.assertEqual(len(calls), 1)
        installed = calls[0][0]['sources']
        self.assertEqual([row['revision'] for row in installed],
                         [row['revision'] for row in recipe['sources']])
        self.assertTrue(all('url' not in row and row['install_local_offline'] for row in installed))
        self.assertEqual(calls[0][1]['deadline'], downloaded[0][1]['deadline'])
        self.assertEqual(calls[0][1]['download_limit'], downloaded[0][1]['download_limit'])
        self.assertEqual(result['dependency_sources'], installed)
        runtime = read_json(result['runtime_environment']['path'])
        self.assertEqual(result['python_executable'], runtime['python_executable'])

        # Keep existing artifacts below the cap; the final tree receipt crosses it.
        from vipe_benchmark.budgets import directory_bytes
        from vipe_benchmark.files import object_hash
        cap = directory_bytes(output) - (output / 'result.json').stat().st_size // 2
        cap_review = read_json(setup.requests['D5']['review']['path'])
        proposal = cap_review['proposals'][0]
        proposal['allocation']['artifact_bytes'] = cap
        review_path = setup.root / 'cap-review.json'
        write_json(review_path, cap_review)
        approved = read_json(setup.requests['D5']['authorization']['path'])
        approved['review'] = file_record(review_path)
        approved['candidate_approvals'][0]['proposal_sha256'] = object_hash(proposal)
        approval_path = setup.root / 'cap-approval.json'
        write_json(approval_path, approved)
        cap_recipe = environment_request('D5', self.source,
            python_seed_executable=self.seed, uv=self.uv, record_kind='fixture',
                dependency_sources=self.dependencies, runtime_directory=self.root / 'runtime')
        cap_request = dict(setup.requests['D5'], review=file_record(review_path),
            authorization=file_record(approval_path), runtime_environment=cap_recipe)
        cap_output = setup.root / cap_request['job_id']
        before_receipt = []
        def bounded_provision(recipe, output, config, **options):
            result = provision(recipe, output, config, **options)
            before_receipt.append(directory_bytes(output.parent))
            return result
        module.provision_depth_environment = bounded_provision
        with patch.dict(sys.modules, {'vipe_benchmark.depth_environment': module}):
            with self.assertRaisesRegex(ValueError, 'candidate artifact allocation'):
                run_moge_setup(cap_request, cap_output, acquire=acquire)
        self.assertLess(before_receipt[0], cap)
        self.assertGreater(directory_bytes(cap_output), cap)
        self.assertTrue((cap_output / 'failure.json').is_file())

    def test_inherited_cuda_build_flags_are_rejected_before_recipe(self):
        from unittest.mock import patch
        for name in ('FLEX_GEMM_BUILD_CUDA', 'BUILD_CUDA'):
            with self.subTest(name=name), patch.dict('os.environ', {name: '1'}):
                with self.assertRaisesRegex(ValueError, 'inherited FlexGEMM'):
                    environment_request('D5', self.source, python_seed_executable=self.seed,
                        uv=self.uv, record_kind='fixture', dependency_sources=self.dependencies, runtime_directory=self.root / 'runtime')

    def test_changed_vcs_pyproject_is_rejected_at_validation(self):
        recipe = environment_request('D6', self.source,
            python_seed_executable=self.seed, uv=self.uv, record_kind='fixture',
            dependency_sources=self.dependencies, runtime_directory=self.root / 'runtime')
        project = self.dependencies['utils3d_moge'] / 'pyproject.toml'
        project.write_text(project.read_text().replace('moderngl', 'unexpected'))
        with self.assertRaises(ValueError):
            validate_environment_request(recipe, self.source, 'D6', 'fixture')

    def test_inherited_official_cache_escape_is_rejected_before_recipe(self):
        from unittest.mock import patch
        with patch.dict('os.environ', {'FLEX_GEMM_AUTOTUNE_CACHE_PATH': '/outside/cache.json'}):
            with self.assertRaisesRegex(ValueError, 'escapes'):
                environment_request('D5', self.source, python_seed_executable=self.seed,
                    uv=self.uv, record_kind='fixture', dependency_sources=self.dependencies,
                    runtime_directory=self.root / 'runtime')
