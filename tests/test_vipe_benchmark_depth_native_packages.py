"""Pinned D8 and D11 dependency probes fail closed without importing a GPU."""

from pathlib import Path
import sys
import unittest
import tempfile
import json
import subprocess
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.depth_native_packages import (
    D8_REQUIRED, D8_UTILS3D_REVISION, D11_PINNED, blockers, qualify)


class NativePackageTests(unittest.TestCase):
    def test_d8_rejects_shared_torch_and_unpinned_utils(self):
        packages = {name: dict(version='1.0', direct_url=None) for name in D8_REQUIRED}
        packages['torch']['version'] = '2.5.1+cu124'
        self.assertIn('D8 requires torch<2.5.0', blockers('D8', packages))
        self.assertIn('D8 requires pinned utils3d Git revision', blockers('D8', packages))
        packages['torch']['version'] = '2.4.1+cu121'
        packages['utils3d']['direct_url'] = dict(vcs_info=dict(commit_id=D8_UTILS3D_REVISION))
        self.assertEqual(blockers('D8', packages), [])

    def test_d11_requires_exact_native_versions(self):
        packages = {name: dict(version=version or '3.10.0')
                    for name, version in D11_PINNED.items()}
        self.assertEqual(blockers('D11', packages), [])
        packages['pyarrow']['version'] = '18.0.0'
        self.assertEqual(blockers('D11', packages), [])
        packages['diffusers']['version'] = '0.39.0'
        packages['h5py']['version'] = '3.9.0'
        self.assertIn('diffusers differs from pinned version 0.38.0',
                      blockers('D11', packages))
        self.assertIn('h5py requires version >=3.10', blockers('D11', packages))


    def test_selected_interpreter_is_probed_before_qualification(self):
        packages = {name: dict(version=version or '3.10.0')
                    for name, version in D11_PINNED.items()}
        with tempfile.TemporaryDirectory() as temp:
            interpreter = Path(temp) / 'python'
            interpreter.write_bytes(b'fixture interpreter')
            result = subprocess.CompletedProcess([], 0, json.dumps(packages), '')
            with patch('vipe_benchmark.depth_native_packages.subprocess.run', return_value=result) as probe:
                qualified = qualify('D11', interpreter)
                self.assertEqual(probe.call_args.args[0][:3], [str(interpreter), '-I', '-B'])
                self.assertEqual(qualified['interpreter_path'], str(interpreter))
                self.assertEqual(qualified['packages']['torch']['version'], '2.10.0')
                packages['torch']['version'] = '2.5.1'
                probe.return_value = subprocess.CompletedProcess([], 0, json.dumps(packages), '')
                with self.assertRaisesRegex(ValueError, 'torch differs from pinned version'):
                    qualify('D11', interpreter)


if __name__ == '__main__':
    unittest.main()
