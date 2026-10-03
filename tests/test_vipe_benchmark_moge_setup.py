"""CPU fixtures for the two approved MoGe setup identities and byte limits."""

from io import BytesIO
import hashlib
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.moge_setup import run_moge_setup, source_tree_records


def archive_bytes(revision='abc', unsafe=False):
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        for name in ('moge/model/v2.py', 'moge/model/v3.py',
                     'pyproject.toml', 'LICENSE'):
            path = ('../escape.py' if unsafe else name)
            payload = b'pinned fixture native source\n'
            member = tarfile.TarInfo(f'MoGe-{revision}/{path}')
            member.size = len(payload)
            archive.addfile(member, BytesIO(payload))
            if unsafe:
                break
    return buffer.getvalue()


class MoGeSetupTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.weight = b'pinned MoGe fixture checkpoint'
        inventory = self.root / 'inventory.json'
        write_json(inventory, dict(candidates={candidate: dict(files=[dict(
            repository=repository, path='model.pt', bytes=len(self.weight),
            lfs_sha256=hashlib.sha256(self.weight).hexdigest())]) for
            candidate, repository in (('D5', 'moge2'), ('D6', 'moge3'))}))
        self.requests = {}
        for candidate, version in (('D5', 2), ('D6', 3)):
            proposal = dict(candidate=candidate, required_assets=file_record(inventory),
                allocation=dict(setup_seconds=1800, download_bytes=1000),
                candidate_config=dict(
                    code=dict(url='https://github.com/microsoft/MoGe',
                              revision='74fbce054ebed49800de42d0ad0e83495065719a'),
                    weights=dict(url=f'https://huggingface.co/Ruicheng/moge-{version}-vitl',
                                 revision='fixture-revision')))
            review = self.root / f'{candidate}-review.json'
            write_json(review, dict(schema='plan069-depth-execution-review/v1',
                                    proposals=[proposal]))
            approval = self.root / f'{candidate}-approval.json'
            write_json(approval, dict(review=file_record(review),
                candidate_approvals=[dict(candidate=candidate, status='approved',
                                          proposal_sha256=object_hash(proposal))]))
            self.requests[candidate] = dict(schema='plan069-depth-setup-request/v1',
                record_kind='fixture', candidate=candidate,
                job_id=f'plan069-{candidate}-setup-001',
                review=file_record(review), authorization=file_record(approval))

    def tearDown(self):
        self.temp.cleanup()

    def acquire(self, url, path, *, max_bytes, deadline, run_root,
                download_limit, artifact_limit):
        payload = archive_bytes('74fbce054ebed49800de42d0ad0e83495065719a') if (
            'codeload.github.com' in url) else self.weight
        self.assertLessEqual(len(payload), max_bytes)
        path.write_bytes(payload)
        transfer_dir = run_root / 'transfers'
        transfer_dir.mkdir(exist_ok=True)
        write_json(transfer_dir / ('transfer-' + path.parent.name + '-' + path.name + '.json'),
                   dict(transfer_id=path.parent.name + '-' + path.name,
                        output=str(path), bytes_received=len(payload)))
        return file_record(path)

    def test_each_pinned_candidate_preserves_exact_bytes_and_one_use_output(self):
        for candidate, request in self.requests.items():
            with self.subTest(candidate=candidate):
                output = self.root / request['job_id']
                result = run_moge_setup(request, output, acquire=self.acquire)
                self.assertEqual(result['candidate'], candidate)
                self.assertEqual(result['checkpoint'], file_record(output / 'model.pt'))
                self.assertTrue((output / 'source/moge/model/v3.py').is_file())
                with self.assertRaisesRegex(ValueError, 'immutable MoGe setup output'):
                    run_moge_setup(request, output, acquire=self.acquire)

    def test_bad_checkpoint_preserves_failure_and_transfer_bytes(self):
        request = self.requests['D5']
        def bad_acquire(url, path, **kwargs):
            result = self.acquire(url, path, **kwargs)
            if path.name == 'model.pt':
                path.write_bytes(b'bad')
                result = file_record(path)
            return result
        output = self.root / request['job_id']
        with self.assertRaisesRegex(ValueError, 'checkpoint bytes differ'):
            run_moge_setup(request, output, acquire=bad_acquire)
        self.assertTrue((output / 'failure.json').is_file())
        self.assertFalse((output / 'result.json').exists())
        self.assertGreater(read_json(output / 'failure.json')['bytes_received'], 0)

    def test_archive_traversal_is_rejected(self):
        request = self.requests['D6']
        def unsafe_acquire(url, path, **kwargs):
            if 'codeload.github.com' not in url:
                return self.acquire(url, path, **kwargs)
            payload = archive_bytes('74fbce054ebed49800de42d0ad0e83495065719a',
                                    unsafe=True)
            path.write_bytes(payload)
            transfer_dir = kwargs['run_root'] / 'transfers'
            transfer_dir.mkdir(exist_ok=True)
            write_json(transfer_dir / 'unsafe.json', dict(
                transfer_id='unsafe', output=str(path), bytes_received=len(payload)))
            return file_record(path)
        with self.assertRaisesRegex(ValueError, 'unsafe MoGe source archive'):
            run_moge_setup(request, self.root / request['job_id'], acquire=unsafe_acquire)

    def runtime_fixture(self, parent, candidate):
        from vipe_benchmark.moge_source_build import REVISION, derive_flex_archive, cache_path
        runtime = parent / 'runtime'
        runtime.mkdir()
        original = parent / 'flex-original.tar.gz'
        payload = (Path(__file__).parent / 'fixtures/plan069-flex-gemm/setup.py.txt').read_bytes()
        with tarfile.open(original, 'w:gz') as archive:
            info = tarfile.TarInfo('FlexGEMM-' + REVISION + '/setup.py')
            info.size = len(payload)
            archive.addfile(info, BytesIO(payload))
        derived = derive_flex_archive(file_record(original), parent / 'flex-derived.tar.gz')
        cache = cache_path(runtime)
        cache.parent.mkdir()
        result = runtime / 'result.json'
        write_json(result, dict(status='complete', candidate=candidate,
            source_packages=[derived], flex_cache_path=str(cache)))
        return file_record(result)

    def test_native_loader_requires_complete_checkpoint_and_refiner(self):
        import torch
        from vipe_benchmark.moge_native import load_adapter
        source = self.root / 'native/source'
        model_dir = source / 'moge/model'
        model_dir.mkdir(parents=True)
        (source / 'LICENSE').write_text('MIT fixture')
        (source / 'moge/__init__.py').write_text('')
        (model_dir / '__init__.py').write_text('')
        (model_dir / 'v3.py').write_text(
            'import torch\n'
            'class MoGeModel(torch.nn.Module):\n'
            '    def __init__(self, refiner=True):\n'
            '        super().__init__()\n'
            '        self.linear = torch.nn.Linear(1, 1)\n'
            '        if refiner: self.refiner = torch.nn.Linear(1, 1)\n')
        checkpoint = self.root / 'native/model.pt'
        checkpoint.parent.mkdir(exist_ok=True)
        torch.save(dict(model_config=dict(refiner=True), model={}), checkpoint)
        archive = self.root / 'native/source.tar.gz'
        archive.write_bytes(b'fixture archive')
        result_path = self.root / 'native/result.json'
        write_json(result_path, dict(schema='plan069-depth-setup-result/v1',
            status='complete', candidate='D6',
            source_revision='74fbce054ebed49800de42d0ad0e83495065719a',
            source_dir=str(source), source_archive=file_record(archive),
            source_tree=source_tree_records(source), checkpoint=file_record(checkpoint),
            runtime_environment=self.runtime_fixture(checkpoint.parent, 'D6')))
        with self.assertRaisesRegex(RuntimeError, 'Missing key'):
            load_adapter('D6', file_record(result_path), device='cpu')
        (model_dir / 'v3.py').write_text('changed native code')
        with self.assertRaisesRegex(ValueError, 'extracted source differs'):
            load_adapter('D6', file_record(result_path), device='cpu')

    def test_repeated_native_loads_preserve_verified_source_with_bytecode_enabled(self):
        from vipe_benchmark.moge_native import load_adapter
        native = ModuleType('fixture_moge_model')
        model = MagicMock()
        model.training = False
        model.to.return_value = model
        model.eval.return_value = model
        native.MoGeModel = MagicMock(return_value=model)
        original_path = sys.path.copy()
        original_modules = {name: module for name, module in sys.modules.items()
                            if name == 'moge' or name.startswith('moge.')}
        self.addCleanup(lambda: sys.path.__setitem__(slice(None), original_path))
        def restore_modules():
            for name in list(sys.modules):
                if name == 'moge' or name.startswith('moge.'):
                    del sys.modules[name]
            sys.modules.update(original_modules)
        self.addCleanup(restore_modules)
        for candidate, version in (('D5', 'v2'), ('D6', 'v3')):
            with self.subTest(candidate=candidate):
                restore_modules()
                for name in original_modules:
                    sys.modules.pop(name, None)
                source = self.root / candidate / 'source'
                model_dir = source / 'moge/model'
                model_dir.mkdir(parents=True)
                (source / 'LICENSE').write_text('MIT fixture')
                (source / 'moge/__init__.py').write_text('')
                (model_dir / '__init__.py').write_text('')
                (model_dir / (version + '.py')).write_text(
                    'from fixture_moge_model import MoGeModel\n')
                checkpoint = source.parent / 'model.pt'
                checkpoint.write_bytes(b'fixture checkpoint')
                archive = source.parent / 'source.tar.gz'
                archive.write_bytes(b'fixture archive')
                result_path = source.parent / 'result.json'
                records = source_tree_records(source)
                write_json(result_path, dict(schema='plan069-depth-setup-result/v1',
                    status='complete', candidate=candidate,
                    source_revision='74fbce054ebed49800de42d0ad0e83495065719a',
                    source_dir=str(source), source_archive=file_record(archive),
                    source_tree=records, checkpoint=file_record(checkpoint),
                    runtime_environment=self.runtime_fixture(checkpoint.parent, candidate)))
                with patch.object(sys, 'dont_write_bytecode', False), patch.dict(
                        sys.modules, {'fixture_moge_model': native}), patch(
                        'torch.load', return_value=dict(model_config={}, model={})):
                    for _ in range(2):
                        adapter = load_adapter(candidate, file_record(result_path), device='cpu')
                        self.assertIsNotNone(adapter)
                        self.assertFalse(sys.dont_write_bytecode)
                    self.assertEqual(source_tree_records(source), records)


if __name__ == '__main__':
    unittest.main()
