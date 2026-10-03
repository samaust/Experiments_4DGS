"""CPU archive and cache boundary tests; fetched setup code is never executed."""
from pathlib import Path
import io
import json
import tarfile
import tempfile
import unittest
from unittest.mock import patch
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.moge_source_build import REVISION, derive_flex_archive, verify_derivation, cache_path

class SourceBuildTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.setup = (Path(__file__).parent / 'fixtures/plan069-flex-gemm/setup.py.txt').read_bytes()

    def archive(self, setup=None):
        path = self.root / 'original.tar.gz'
        with tarfile.open(path, 'w:gz') as archive:
            for name, payload in [('setup.py', self.setup if setup is None else setup),
                                   ('flex_gemm/kernels/untouched.py', b'numerical source remains unchanged')]:
                info = tarfile.TarInfo('FlexGEMM-' + REVISION + '/' + name)
                info.size = len(payload)
                archive.addfile(info, io.BytesIO(payload))
        return file_record(path)

    def test_derivation_changes_only_setup_paths_and_is_deterministic(self):
        original = self.archive()
        first = derive_flex_archive(original, self.root / 'one/derived.tar.gz')
        second = derive_flex_archive(original, self.root / 'two/derived.tar.gz')
        self.assertEqual(first['record']['sha256'], second['record']['sha256'])
        self.assertEqual(first['original_record'], original)
        self.assertEqual(verify_derivation(first)['changed_files'], ['setup.py'])
        self.assertEqual(file_record(original['path']), original)
        with tarfile.open(first['record']['path']) as archive:
            setup = archive.extractfile('FlexGEMM-' + REVISION + '/setup.py').read()
        self.assertNotIn(b'~/.flex_gemm', setup)
        self.assertIn(b'FLEX_GEMM_AUTOTUNE_CACHE_PATH', setup)

    def test_changed_original_setup_and_changed_pristine_archive_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'unreviewed FlexGEMM setup'):
            derive_flex_archive(self.archive(self.setup + b'\n# unexpected edit'), self.root / 'derived.tar.gz')
        original = self.archive()
        derived = derive_flex_archive(original, self.root / 'accepted.tar.gz')
        Path(original['path']).write_bytes(b'changed pristine bytes')
        with self.assertRaises(ValueError):
            verify_derivation(derived)

    def test_changed_manifest_and_unscoped_inherited_cache_are_rejected(self):
        derived = derive_flex_archive(self.archive(), self.root / 'accepted.tar.gz')
        manifest = read_json(derived['derivation']['path'])
        manifest['patches'].append(dict(before='numerical', after='changed'))
        Path(derived['derivation']['path']).write_text(json.dumps(manifest))
        derived['derivation'] = file_record(derived['derivation']['path'])
        with self.assertRaisesRegex(ValueError, 'derivation lineage'):
            verify_derivation(derived)
        with patch.dict('os.environ', {'FLEX_GEMM_AUTOTUNE_CACHE_PATH': '/outside/cache.json'}):
            with self.assertRaisesRegex(ValueError, 'escapes'):
                cache_path(self.root / 'runtime')
        with patch.dict('os.environ', {}, clear=True):
            self.assertEqual(cache_path(self.root / 'runtime'), self.root / 'runtime/flex-cache/autotune_cache.json')
