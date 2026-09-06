import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('atgs_offline',
    Path(__file__).resolve().parents[1] / 'scripts/verify-atgs-offline.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ATGSOfflineTests(unittest.TestCase):
    def test_inventory_rejects_changed_hash_size_or_missing_component(self):
        expected = {'auxiliary.pth': {'sha256': 'abc', 'bytes': 42}}
        module.verify_inventory(expected, expected.copy())
        for actual in ({}, {'auxiliary.pth': {'sha256': 'def', 'bytes': 42}},
                       {'auxiliary.pth': {'sha256': 'abc', 'bytes': 43}}):
            with self.assertRaisesRegex(ValueError, 'inventory'):
                module.verify_inventory(actual, expected)
