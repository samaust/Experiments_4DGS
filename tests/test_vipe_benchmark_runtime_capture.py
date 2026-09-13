from pathlib import Path
import sys
import tempfile
import types
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import read_json
from vipe_benchmark.runtime_capture import loaded_runtime


class LoadedRuntimeTests(unittest.TestCase):
    def test_loaded_libraries_and_module_aliases_are_bound_once(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source, library = root / 'model.py', root / 'native.so'
            source.write_text('x = 1\n')
            library.write_bytes(b'fixture-native-library')
            maps = root / 'maps'
            maps.write_text(f'0-1 r-xp 0000 08:00 1 {library}\n1-2 r--p 0000 08:00 1 {library}\n')
            module = types.SimpleNamespace(__file__=str(source))
            record = loaded_runtime(root / 'result.json', modules={'alias': module, 'model': module}, maps_path=maps)
            result = read_json(record['path'])
            self.assertEqual(len(result['files']), 2)
            modules = next(f for f in result['files'] if f['modules'])
            self.assertEqual(modules['modules'], ['alias', 'model'])
            self.assertFalse(result['new_inference'])

    def test_unhashable_loaded_library_cannot_qualify(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            maps = root / 'maps'
            maps.write_text('0-1 r-xp 0000 08:00 1 /tmp/native.so (deleted)\n')
            with self.assertRaisesRegex(ValueError, 'deleted'):
                loaded_runtime(root / 'result.json', modules={}, maps_path=maps)
            self.assertFalse((root / 'result.json').exists())


if __name__ == '__main__':
    unittest.main()
