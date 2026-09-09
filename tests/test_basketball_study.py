"""Plan 026 split and provenance failure cases."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from basketball_study import CAMERAS, digest, training_key, verify_files, write_new
import basketball_study


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

    def test_supervisor_records_failure_and_releases_lock(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(basketball_study, 'ARTIFACTS', Path(tmp)):
            result = basketball_study.supervise([sys.executable, '-c', 'raise SystemExit(7)'], 'validation', Path(tmp)/'failed')
            self.assertEqual(result['exit_code'], 7)
            self.assertGreater(result['charged_seconds'], 0)
            with basketball_study.ledger_lock():
                with self.assertRaises(BlockingIOError):
                    with basketball_study.ledger_lock():
                        pass
            rows = [json.loads(line) for line in (Path(tmp)/'ledger.jsonl').read_text().splitlines()]
            self.assertEqual([r['event'] for r in rows], ['start', 'finish'])


if __name__ == '__main__':
    unittest.main()
