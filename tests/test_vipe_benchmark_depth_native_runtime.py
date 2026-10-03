"""Native runtime recipes remain metered and bind dependency source provenance."""

from io import BytesIO
from pathlib import Path
import sys
import tarfile
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.depth_native_runtime import prepare, D8_REQUIREMENTS
from vipe_benchmark.depth_native_packages import D8_UTILS3D_REVISION
from vipe_benchmark.files import file_record


class NativeRuntimePreparationTests(unittest.TestCase):
    def test_d8_installs_only_the_metered_pinned_local_utils_archive(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            native_requirements = root / 'source/models/student_pointmap/requirements.txt'
            native_requirements.parent.mkdir(parents=True)
            native_requirements.write_text('torch<2.5.0\n')
            request = dict(candidate='D8', record_kind='fixture',
                           environment=dict(candidate='D8', record_kind='fixture',
                                            requirements=list(D8_REQUIREMENTS)))
            transfers, calls = [], []

            def acquire(url, target, **bounds):
                self.assertEqual(url, 'https://codeload.github.com/EasternJournalist/utils3d/tar.gz/' + D8_UTILS3D_REVISION)
                self.assertEqual(bounds['download_limit'], 123456789)
                self.assertEqual(bounds['artifact_limit'], 987654321)
                payload = b'# pinned dependency source fixture\n'
                with tarfile.open(target, 'w:gz') as archive:
                    entry = tarfile.TarInfo('utils3d-' + D8_UTILS3D_REVISION + '/utils3d/__init__.py')
                    entry.size = len(payload)
                    archive.addfile(entry, BytesIO(payload))
                record = file_record(target)
                transfers.append(record)
                return record

            def provision(environment, output, config, **bounds):
                calls.append(environment)
                self.assertEqual(bounds['download_limit'], 123456789)
                self.assertEqual(bounds['artifact_limit'], 987654321)
                self.assertIn('torch==2.4.1+cu124', environment['requirements'])
                self.assertTrue(environment['sources'][0]['install_local_offline'])
                self.assertEqual(environment['sources'][0]['record'], transfers[0])
                self.assertEqual(environment['requirement_sources'], [file_record(native_requirements)])
                return dict(status='complete', python_executable=sys.executable)

            helper = ModuleType('vipe_benchmark.depth_environment')
            helper.provision_depth_environment = provision
            with patch.dict(sys.modules, {'vipe_benchmark.depth_environment': helper}), \
                    patch('vipe_benchmark.depth_native_packages.qualify', return_value={'status': 'passed'}):
                runtime = prepare(request, root, {}, run_root=root, deadline=10**20,
                                  acquire=acquire, download_limit=123456789,
                                  artifact_limit=987654321)
            self.assertEqual(len(calls), 1)
            self.assertEqual(runtime['source_packages'][0]['revision'], D8_UTILS3D_REVISION)
            self.assertEqual(runtime['native_qualification'], {'status': 'passed'})


if __name__ == '__main__':
    unittest.main()
