"""Approved depth setup consumes one ledger identity and blocks overlap."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.config import ROOT, load
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from unittest.mock import patch


REVIEW = ROOT / 'docs/specs/plan031-execution/depth-execution-review-001.json'
DO = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'


class DepthSetupAuthorizationTests(unittest.TestCase):
    def test_exact_approval_allocates_once_and_reservation_blocks_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / 'ledger.jsonl', load())
            review, approved = file_record(REVIEW), file_record(DO)
            ledger.authorize_depth_setup('D7', review, approved)
            self.assertEqual(ledger.jobs['plan069-D7-setup-001']['seconds'], 1800)
            with self.assertRaisesRegex(ValueError, 'already authorized'):
                ledger.authorize_depth_setup('D7', review, approved)
            ledger.reserve('plan069-D7-setup-001', ['bounded-setup'], approved)
            with self.assertRaisesRegex(ValueError, 'unreconciled active attempt'):
                ledger.reserve('S1-calibration', ['forbidden-overlap'], approved)
            ledger.finish('plan069-D7-setup-001', 'failed', 1)
            with self.assertRaisesRegex(ValueError, 'already consumed'):
                ledger.reserve('plan069-D7-setup-001', ['forbidden-retry'], approved)

    def test_changed_grant_cannot_allocate_setup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = Ledger(root / 'ledger.jsonl', load())
            altered = read_json(DO)
            altered['candidate_approvals'][3]['proposal_sha256'] = '0' * 64
            write_json(root / 'altered.json', altered)
            with self.assertRaisesRegex(ValueError, 'exact approved depth setup'):
                ledger.authorize_depth_setup('D7', file_record(REVIEW),
                                             file_record(root / 'altered.json'))
            self.assertEqual(ledger.events(), [])

    def test_amended_caps_must_match_approved_record_and_live_headroom(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = dict(load(), new_download_gib_limit=110,
                          new_artifact_disk_gib_limit=210)
            ledger = Ledger(root / 'ledger.jsonl', config)
            review, approved = file_record(REVIEW), file_record(DO)
            altered = read_json(DO)
            altered['cap_approval']['amendment_sha256'] = '0' * 64
            write_json(root / 'invalid-cap.json', altered)
            with self.assertRaisesRegex(ValueError, 'exact approved depth cap amendment'):
                ledger.authorize_depth_setup('D7', review,
                                             file_record(root / 'invalid-cap.json'))
            with patch('vipe_benchmark.execution.resources', return_value=dict(
                    download_bytes=110 * 2**30, artifact_bytes=0)):
                with self.assertRaisesRegex(ValueError, 'download_bytes setup allocation'):
                    ledger.authorize_depth_setup('D7', review, approved)
            self.assertEqual(ledger.events(), [])


if __name__ == '__main__':
    unittest.main()
