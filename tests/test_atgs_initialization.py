import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from atgs_initialization import validate_initialization


class InitializationTests(unittest.TestCase):
    def test_checks_manifest_split_and_input_hashes(self):
        scene = SimpleNamespace(sha256='manifest', training_keys=lambda frame: [('0000', frame)],
                                frames={('0000', 4150): dict(sha256='image')})
        result = dict(status='triangulated', manifest_sha256='manifest',
                      inputs=[dict(camera_id='0000', frame_id=4150, sha256='image')])
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)
            (path / 'initialization.ply').write_bytes(b'fixture')
            (path / 'result.json').write_text(json.dumps(result))
            self.assertEqual(len(validate_initialization(path, scene)['ply_sha256']), 64)
            for field, value, error in [('sha256', 'wrong', 'digest'), ('camera_id', '0015', 'split')]:
                changed = json.loads(json.dumps(result))
                changed['inputs'][0][field] = value
                (path / 'result.json').write_text(json.dumps(changed))
                with self.assertRaisesRegex(ValueError, error):
                    validate_initialization(path, scene)
            result['manifest_sha256'] = 'wrong'
            (path / 'result.json').write_text(json.dumps(result))
            with self.assertRaisesRegex(ValueError, 'manifest'):
                validate_initialization(path, scene)
