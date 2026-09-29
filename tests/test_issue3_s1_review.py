"""Read-only check of the refreshed issue #3 S1 REVIEW proposal."""

import json
import unittest

from vipe_benchmark import s1_recovery
from vipe_benchmark.config import ROOT
from vipe_benchmark.files import file_record


class S1ReviewProposalTests(unittest.TestCase):
    def test_historical_review_refuses_dispatch(self):
        from vipe_benchmark.config import load

        local = ROOT / '.local/vipe-alternatives/plan031-20260913T032700Z'
        proposal = ROOT / 'docs/research/vipe-alternatives/issue3-preparation/s1-calibration-recovery-authorization-004-review-001.json'
        before = (local / 'ledger.jsonl').read_bytes()
        draft = json.loads(proposal.read_text())
        self.assertEqual(draft['authorization_context']['stage'], 'REVIEW')
        self.assertIs(draft['additional_attempt_approved'], False)
        with self.assertRaisesRegex(ValueError, 'explicit S1 calibration'):
            s1_recovery.validate_binding(local, load(), file_record(proposal))

        self.assertEqual((local / 'ledger.jsonl').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
