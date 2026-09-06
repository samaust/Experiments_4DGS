from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atgs_runtime import EXTENSIONS, extension_inventory


class RuntimeTests(unittest.TestCase):
    def test_fingerprint_detects_binary_change_and_missing_component(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(ValueError, 'missing compiled'):
                extension_inventory(root)
            for component in EXTENSIONS:
                (root / component).mkdir()
                (root / component / 'fixture.so').write_bytes(component.encode())
            first = extension_inventory(root)
            self.assertEqual(len(first), len(EXTENSIONS))
            path = root / EXTENSIONS[0] / 'fixture.so'
            path.write_bytes(b'changed')
            self.assertNotEqual(first, extension_inventory(root))
