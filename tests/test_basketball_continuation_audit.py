import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from basketball_continuation_audit import verify_hashes, verify_membership, CALIBRATION, PROFILE
from basketball_audit import sha256


class ContinuationAuditTests(unittest.TestCase):
    def test_changed_artifact_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)/'evidence.json'
            path.write_text('{}')
            expected = {str(path): sha256(path)}
            verify_hashes(expected)
            path.write_text('{"changed": true}')
            with self.assertRaisesRegex(ValueError, 'changed provenance'):
                verify_hashes(expected)

    def test_full_rig_and_held_out_identity(self):
        profile = json.loads(PROFILE.read_text())
        calibration = json.loads(CALIBRATION.read_text())
        verify_membership(profile, calibration)
        for mutation in ('split', 'duplicate', 'count'):
            changed = copy.deepcopy(profile)
            if mutation == 'split':
                changed['cameras'][0]['role'] = 'training'
            elif mutation == 'duplicate':
                changed['cameras'][1]['id'] = '0'
            else:
                changed['variant']['expected_images'] = 1150
            with self.assertRaises(ValueError):
                verify_membership(changed, calibration)


if __name__ == '__main__':
    unittest.main()
