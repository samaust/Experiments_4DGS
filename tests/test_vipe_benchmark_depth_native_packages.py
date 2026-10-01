"""Pinned D8 and D11 dependency probes fail closed without importing a GPU."""

from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.depth_native_packages import (
    D8_REQUIRED, D8_UTILS3D_REVISION, D11_PINNED, blockers)


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
        packages['diffusers']['version'] = '0.39.0'
        packages['h5py']['version'] = '3.9.0'
        self.assertIn('diffusers differs from pinned version 0.38.0',
                      blockers('D11', packages))
        self.assertIn('h5py requires version >=3.10', blockers('D11', packages))


if __name__ == '__main__':
    unittest.main()
