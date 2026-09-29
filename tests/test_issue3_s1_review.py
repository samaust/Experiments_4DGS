"""Read-only check of the refreshed issue #3 S1 REVIEW proposal."""

import json
import tempfile
import unittest
from pathlib import Path

from vipe_benchmark import s1_recovery
from vipe_benchmark.config import ROOT
from vipe_benchmark.files import file_record


class S1ReviewProposalTests(unittest.TestCase):
    def test_review_refuses_dispatch_but_qualifies_exact_synthetic_do(self):
        from vipe_benchmark.config import load

        local = ROOT / '.local/vipe-alternatives/plan031-20260913T032700Z'
        proposal = ROOT / 'docs/research/vipe-alternatives/issue3-preparation/s1-calibration-recovery-authorization-004-review-001.json'
        before = (local / 'ledger.jsonl').read_bytes()
        draft = json.loads(proposal.read_text())
        self.assertEqual(draft['authorization_context']['stage'], 'REVIEW')
        self.assertIs(draft['additional_attempt_approved'], False)
        with self.assertRaisesRegex(ValueError, 'explicit S1 calibration'):
            s1_recovery.validate_binding(local, load(), file_record(proposal))

        with tempfile.TemporaryDirectory() as directory:
            candidate = Path(directory) / 'synthetic-do.json'
            approved = dict(draft, additional_attempt_approved=True,
                            authorization='Synthetic CPU validation only',
                            authorization_context=dict(draft['authorization_context'], stage='DO'))
            candidate.write_text(json.dumps(approved))
            document, request = s1_recovery.validate_binding(local, load(), file_record(candidate))
            self.assertEqual(document['job_id'], 'S1-calibration-recovery-004')
            self.assertEqual(request['job_id'], 'S1-calibration')
        self.assertEqual((local / 'ledger.jsonl').read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
