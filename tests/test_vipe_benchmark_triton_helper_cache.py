"""Prebuilt Triton helper cache binding; fixtures compile and import nothing."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from vipe_benchmark.files import file_record, write_json
from vipe_benchmark.triton_helper_cache import SCHEMA, build, cache_directory_name, cache_key, manifest, validate_binding


def fixture(root, python='/fixture/python'):
    triton = root / 'triton'
    (triton / 'backends/nvidia').mkdir(parents=True)
    (triton / 'backends/nvidia/driver.c').write_text('int helper(void) { return 0; }\n')
    (triton / '__init__.py').write_text("__version__ = '3.2.0'\n")
    key = cache_key((triton / 'backends/nvidia/driver.c').read_bytes())
    cache = root / 'cache'
    entry = cache / cache_directory_name(key)
    entry.mkdir(parents=True)
    (entry / 'cuda_utils.so').write_bytes(b'\x7fELF fixture')
    receipt = root / 'build-receipt.json'
    write_json(receipt, dict(schema='plan069-triton-helper-build/v1', elapsed_seconds=1.0, python=python, gpu_operations=False))
    binding = dict(schema=SCHEMA, status='built', helper='cuda_utils', cache_directory=str(cache),
                   triton_version='3.2.0', driver_source=file_record(triton / 'backends/nvidia/driver.c'),
                   key=key, manifest=manifest(cache), build_receipt=file_record(receipt))
    path = root / 'binding.json'
    write_json(path, binding)
    return triton, cache, entry, file_record(path)


class TritonHelperCacheTests(unittest.TestCase):
    def test_exact_bound_cache_validates(self):
        with tempfile.TemporaryDirectory() as directory:
            triton, _, _, record = fixture(Path(directory).resolve())
            self.assertEqual(validate_binding(record, triton_directory=triton)['helper'], 'cuda_utils')

    def test_changed_helper_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            triton, _, entry, record = fixture(Path(directory).resolve())
            (entry / 'cuda_utils.so').write_bytes(b'replaced')
            with self.assertRaisesRegex(ValueError, 'contents changed'):
                validate_binding(record, triton_directory=triton)

    def test_new_compile_output_or_directory_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            triton, cache, _, record = fixture(Path(directory).resolve())
            (cache / 'NEWKEY').mkdir()
            with self.assertRaisesRegex(ValueError, 'contents changed'):
                validate_binding(record, triton_directory=triton)
            (cache / 'NEWKEY').rmdir()
            validate_binding(record, triton_directory=triton)
            (cache / 'launcher.so').write_bytes(b'new')
            with self.assertRaisesRegex(ValueError, 'contents changed'):
                validate_binding(record, triton_directory=triton)

    def test_link_in_cache_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            triton, cache, _, record = fixture(Path(directory).resolve())
            os.symlink(triton, cache / 'escape')
            with self.assertRaisesRegex(ValueError, 'link'):
                validate_binding(record, triton_directory=triton)

    def test_installed_driver_source_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            triton, _, _, record = fixture(root)
            other = root / 'other'
            (other / 'backends/nvidia').mkdir(parents=True)
            (other / 'backends/nvidia/driver.c').write_text('changed\n')
            with self.assertRaisesRegex(ValueError, 'driver source differs'):
                validate_binding(record, triton_directory=other)

    def test_installed_triton_version_must_match(self):
        with tempfile.TemporaryDirectory() as directory:
            triton, _, _, record = fixture(Path(directory).resolve())
            (triton / '__init__.py').write_text("__version__ = '3.3.0'\n")
            with self.assertRaisesRegex(ValueError, 'version differs'):
                validate_binding(record, triton_directory=triton)

    def test_helper_must_sit_at_triton_key_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            triton, cache, entry, _ = fixture(root)
            moved = cache / 'not-the-key'
            entry.rename(moved)
            binding = __import__('json').loads((root / 'binding.json').read_text())
            binding['manifest'] = manifest(cache)
            write_json(root / 'moved-binding.json', binding)
            with self.assertRaisesRegex(ValueError, 'key directory'):
                validate_binding(file_record(root / 'moved-binding.json'), triton_directory=triton)

    def test_triton_directory_name_matches_triton_base64_encoding(self):
        self.assertEqual(cache_directory_name('ab' * 32), 'q6urq6urq6urq6urq6urq6urq6urq6urq6urq6urq6s')

    def test_binding_record_is_hash_bound(self):
        with tempfile.TemporaryDirectory() as directory:
            triton, _, _, record = fixture(Path(directory).resolve())
            Path(record['path']).write_text('{}')
            with self.assertRaises(ValueError):
                validate_binding(record, triton_directory=triton)

    def test_build_requires_hidden_gpu_fresh_paths_and_no_triton_environment(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': '0'}):
                with self.assertRaisesRegex(ValueError, 'hide GPUs'):
                    build(root / 'cache', root / 'out')
            with patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': '', 'TRITON_HOME': str(root)}):
                with self.assertRaisesRegex(ValueError, 'inherited Triton'):
                    build(root / 'cache', root / 'out')
            (root / 'cache').mkdir()
            with patch.dict(os.environ, {'CUDA_VISIBLE_DEVICES': ''}):
                with self.assertRaisesRegex(ValueError, 'fresh'):
                    build(root / 'cache', root / 'out')
            self.assertFalse((root / 'out').exists())


if __name__ == '__main__':
    unittest.main()
