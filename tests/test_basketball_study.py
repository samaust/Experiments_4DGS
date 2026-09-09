"""Plan 026 split and provenance failure cases."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_study import CAMERAS, digest, training_key, verify_files, write_new


class StudyTests(unittest.TestCase):
    def test_all_initialization_access_including_neighbors(self):
        allowed = []
        for camera in range(34):
            for frame in range(-1, 51):
                if camera in CAMERAS and 0 <= frame < 50 and not 20 <= frame <= 24:
                    allowed.append(training_key(camera, frame))
                else:
                    with self.assertRaises(ValueError):
                        training_key(camera, frame)
        self.assertEqual(len(allowed), 1350)
        for frame in (19, 24, 49):
            with self.assertRaises(ValueError):
                training_key(1, frame+1) if frame != 24 else training_key(1, frame)

    def test_provenance_rejects_mutated_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'source.json'
            write_new(path, {'a': 1})
            files = {str(path): digest(path)}
            verify_files(files)
            with self.assertRaises(FileExistsError):
                write_new(path, {'a': 2})
            path.write_text(json.dumps({'a': 2}))
            with self.assertRaisesRegex(ValueError, 'changed historical input'):
                verify_files(files)


if __name__ == '__main__':
    unittest.main()
