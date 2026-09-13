"""Fixture archives and wheel metadata only: no network, native import or probe."""
import hashlib
import io
import os
from pathlib import Path
import stat
import tarfile
import tempfile
import unittest
from unittest.mock import patch

from scripts.vipe_benchmark import toolkit
from scripts.vipe_benchmark.files import file_record, verify_record


class ToolkitTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.config = dict(new_download_gib_limit=1, new_artifact_disk_gib_limit=1)

    def fixture_archives(self, extra=None, omitted=()):
        components, blobs = [], {}
        for index, source in enumerate(toolkit.COMPONENTS):
            component = dict(source)
            archive_root = Path(source['relative_path']).name.removesuffix('.tar.xz')
            contents = {f'{archive_root}/LICENSE.txt': (f'license {index}'.encode(), 0o644)}
            for name in toolkit.REQUIRED_TOOLKIT_FILES:
                if name in omitted or name.startswith('lib64/'):
                    continue
                owner = (0 if name.startswith(('bin/', 'nvvm/', 'include/crt/')) else
                         2 if name.startswith(('include/nv/', 'include/cub/',
                                              'include/thrust/', 'include/cuda/std/')) else 1)
                if owner == index:
                    mode = 0o755 if name.startswith(('bin/', 'nvvm/bin/')) else 0o644
                    contents[f'{archive_root}/{name}'] = (name.encode(), mode)
            if index == 1:
                contents[f'{archive_root}/lib/libcudart.so.12.4.127'] = (b'fake runtime library', 0o644)
                contents[f'{archive_root}/lib/libcudart.so'] = ('libcudart.so.12.4.127', 'link')
            if index == 0:
                contents[f'{archive_root}/prompts/do-not-extract.txt'] = (b'fixture skipped entry', 0o644)
                for name, value in (extra or {}).items():
                    contents[name.format(root=archive_root)] = value
            stream = io.BytesIO()
            with tarfile.open(fileobj=stream, mode='w:xz') as archive:
                for name, (content, mode) in contents.items():
                    item = tarfile.TarInfo(name)
                    if mode in ('link', 'hardlink'):
                        item.type = tarfile.SYMTYPE if mode == 'link' else tarfile.LNKTYPE
                        item.linkname = content
                        item.mode = 0o777
                        archive.addfile(item)
                    else:
                        item.mode, item.size = mode, len(content)
                        archive.addfile(item, io.BytesIO(content))
            blob = stream.getvalue()
            component.update(sha256=hashlib.sha256(blob).hexdigest(), bytes=len(blob))
            components.append(component)
            blobs[toolkit.BASE_URL + component['relative_path']] = blob
        return tuple(components), blobs

    def download(self, blobs):
        def fake(url, path, transfer_dir, *, limit):
            self.assertEqual(limit, 2**30)
            self.assertEqual(Path(transfer_dir), self.base / 'transfers')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(blobs[url])
            return file_record(path)
        return fake

    def acquire(self, components, blobs, *, name='toolkit'):
        with patch.object(toolkit, 'COMPONENTS', components), \
             patch('scripts.vipe_benchmark.runtime.download', side_effect=self.download(blobs)):
            return toolkit.acquire_toolkit(self.base / name, self.base / 'transfers', self.config)

    def python_environment(self, torch_version='2.5.1+cu124'):
        env = self.base / 'environment'
        site = env / 'lib/python3.11/site-packages'
        site.mkdir(parents=True)
        packages = {'nvidia-cublas-cu12': '12.4.5.8', 'nvidia-cusparse-cu12': '12.3.1.170',
                    'nvidia-cusolver-cu12': '11.6.1.9'}
        torch = site / f'torch-{torch_version}.dist-info/METADATA'
        torch.parent.mkdir()
        torch.write_text(f'Name: torch\nVersion: {torch_version}\n' + ''.join(
            f'Requires-Dist: {name} (=={version}); platform_system == "Linux"\n'
            for name, version in packages.items()))
        for name, version in packages.items():
            metadata = site / f'{name.replace("-", "_")}-{version}.dist-info/METADATA'
            metadata.parent.mkdir()
            metadata.write_text(f'Name: {name}\nVersion: {version}\n')
            subdir, required = toolkit.WHEEL_HEADERS[name]
            include = site / 'nvidia' / subdir / 'include'
            include.mkdir(parents=True)
            for header in (*required, 'companion.h'):
                (include / header).write_text(f'fixture {name}/{header}\n')
        return env, site

    def test_verified_acquisition_preserves_layout_licenses_modes_and_internal_links(self):
        components, blobs = self.fixture_archives()
        opened = []
        original = tarfile.TarFile.extractfile
        def observed(source, member):
            opened.append(member.name)
            return original(source, member)
        with patch.object(tarfile.TarFile, 'extractfile', observed):
            record = self.acquire(components, blobs)
        root = Path(record['path'])
        self.assertFalse(record['reused'])
        self.assertEqual(record['archive_bytes'], sum(len(v) for v in blobs.values()))
        self.assertEqual(stat.S_IMODE((root / 'bin/nvcc').stat().st_mode), 0o755)
        self.assertTrue((root / 'lib64').is_symlink())
        self.assertEqual((root / 'lib64/libcudart.so').read_bytes(), b'fake runtime library')
        self.assertEqual(len(record['links']), 2)
        for index, component in enumerate(components):
            self.assertEqual((root / 'licenses' / component['name'] / 'LICENSE.txt').read_text(),
                             f'license {index}')
        self.assertFalse(any('prompts' in Path(name).parts for name in opened))
        self.assertFalse((root / 'prompts').exists())
        verify_record(record['receipt'])

    def test_reuse_verifies_without_transfers_or_new_attempts(self):
        components, blobs = self.fixture_archives()
        original = self.acquire(components, blobs)
        with patch.object(toolkit, 'COMPONENTS', components), \
             patch('scripts.vipe_benchmark.runtime.download', side_effect=AssertionError('network')):
            reused = toolkit.acquire_toolkit(original['path'], self.base / 'transfers', self.config)
        self.assertTrue(reused['reused'])
        self.assertEqual(reused['receipt'], original['receipt'])
        self.assertEqual(reused['files'], original['files'])
        self.assertEqual(reused['archives'], original['archives'])

    def test_changed_toolkit_refuses_reuse_without_reacquisition(self):
        components, blobs = self.fixture_archives()
        record = self.acquire(components, blobs)
        (Path(record['path']) / 'include/cuda.h').write_text('changed')
        with patch.object(toolkit, 'COMPONENTS', components), \
             patch('scripts.vipe_benchmark.runtime.download') as download:
            with self.assertRaisesRegex(ValueError, 'changed'):
                toolkit.acquire_toolkit(record['path'], self.base / 'transfers', self.config)
            download.assert_not_called()

    def test_hash_failure_retains_partial_state_and_never_retries_it_implicitly(self):
        components, blobs = self.fixture_archives()
        wrong = (dict(components[0], sha256='0' * 64), *components[1:])
        with self.assertRaisesRegex(ValueError, 'expected'):
            self.acquire(wrong, blobs)
        self.assertFalse((self.base / 'toolkit' / toolkit.RECEIPT).exists())
        with patch.object(toolkit, 'COMPONENTS', components), \
             patch('scripts.vipe_benchmark.runtime.download') as download:
            with self.assertRaisesRegex(ValueError, 'no automatic reacquisition'):
                toolkit.acquire_toolkit(self.base / 'toolkit', self.base / 'transfers', self.config)
            download.assert_not_called()

    def test_unsafe_members_are_rejected(self):
        cases = (
            {'{root}/../../outside': (b'escape', 0o644)},
            {'/absolute': (b'escape', 0o644)},
            {'{root}/include/bad': ('../../outside', 'link')},
            {'{root}/include/bad': ('/tmp/outside', 'link')},
            {'{root}/include/bad': ('../prompts/hidden', 'link')},
            {'{root}/include/bad': ('{root}/include/cuda.h', 'hardlink')},
            {'{root}/bin/unsafe': (b'setuid', 0o4755)},
        )
        for index, extra in enumerate(cases):
            with self.subTest(extra=extra):
                components, blobs = self.fixture_archives(extra)
                with self.assertRaises(ValueError):
                    self.acquire(components, blobs, name=f'unsafe-{index}')
                self.assertFalse((self.base / f'unsafe-{index}' / toolkit.RECEIPT).exists())
        self.assertFalse((self.base / 'outside').exists())

    def test_archive_size_identity_is_checked_before_extracting(self):
        components, blobs = self.fixture_archives()
        wrong = (dict(components[0], bytes=components[0]['bytes'] + 1), *components[1:])
        with self.assertRaisesRegex(ValueError, 'published bytes'):
            self.acquire(wrong, blobs)
        self.assertFalse((self.base / 'toolkit/bin').exists())

    def test_build_environment_records_exact_metadata_and_all_companion_headers(self):
        components, blobs = self.fixture_archives()
        record = self.acquire(components, blobs)
        env, site = self.python_environment()
        with patch.object(toolkit, 'COMPONENTS', components), patch.dict(os.environ, CPATH='/cuda13/include'):
            result = toolkit.build_environment(record, env / 'bin/python')
        delta = result['env']
        self.assertEqual(delta['CUDA_HOME'], record['path'])
        self.assertTrue(delta['PATH'].startswith(str(Path(record['path']) / 'bin') + os.pathsep))
        self.assertEqual(delta['CPATH'].split(os.pathsep), [str(Path(record['path']) / 'include')] +
                         [str(site / 'nvidia' / name / 'include') for name in ('cublas', 'cusparse', 'cusolver')])
        self.assertEqual(delta['TORCH_CUDA_ARCH_LIST'], '8.9')
        self.assertEqual(delta['SAM2_BUILD_ALLOW_ERRORS'], '0')
        self.assertEqual(delta['SAM2_BUILD_CUDA'], '1')
        self.assertLessEqual(int(delta['MAX_JOBS']), 8)
        self.assertEqual(len(result['packages']), 4)
        self.assertEqual(len([r for r in result['headers'] if r['path'].endswith('companion.h')]), 3)
        for item in result['headers']:
            verify_record(item)

    def test_wrong_torch_target_fails(self):
        components, blobs = self.fixture_archives()
        record = self.acquire(components, blobs)
        env, _ = self.python_environment('2.5.1+cu130')
        with patch.object(toolkit, 'COMPONENTS', components), self.assertRaisesRegex(ValueError, 'exact torch'):
            toolkit.build_environment(record, env)

    def test_wrong_wheel_dependency_version_fails(self):
        components, blobs = self.fixture_archives()
        record = self.acquire(components, blobs)
        env, site = self.python_environment()
        metadata = next(site.glob('nvidia_cusolver_cu12-*.dist-info/METADATA'))
        metadata.write_text('Name: nvidia-cusolver-cu12\nVersion: 99.0\n')
        with patch.object(toolkit, 'COMPONENTS', components), self.assertRaisesRegex(ValueError, 'cu124 torch'):
            toolkit.build_environment(record, env)

    def test_missing_required_wheel_header_fails(self):
        components, blobs = self.fixture_archives()
        record = self.acquire(components, blobs)
        env, site = self.python_environment()
        (site / 'nvidia/cublas/include/cublasLt.h').unlink()
        with patch.object(toolkit, 'COMPONENTS', components), self.assertRaisesRegex(ValueError, 'closure missing'):
            toolkit.build_environment(record, env)

    def test_missing_required_toolkit_file_fails_before_build(self):
        components, blobs = self.fixture_archives(omitted=('include/nv/target',))
        record = self.acquire(components, blobs)
        env, _ = self.python_environment()
        with patch.object(toolkit, 'COMPONENTS', components), self.assertRaisesRegex(ValueError, 'include/nv/target'):
            toolkit.build_environment(record, env)

    def test_changed_executable_mode_fails_receipt_verification(self):
        components, blobs = self.fixture_archives()
        record = self.acquire(components, blobs)
        env, _ = self.python_environment()
        (Path(record['path']) / 'bin/nvcc').chmod(0o644)
        with patch.object(toolkit, 'COMPONENTS', components), self.assertRaisesRegex(ValueError, 'modes'):
            toolkit.build_environment(record, env)


if __name__ == '__main__':
    unittest.main()
