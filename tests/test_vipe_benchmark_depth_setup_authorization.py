"""Approved depth setup consumes one ledger identity and blocks overlap."""

from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.config import ROOT, load
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.depth_admission import local_source_records
from unittest.mock import patch


REVIEW = ROOT / 'docs/specs/plan031-execution/depth-execution-review-001.json'
DO = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'
REVIEW = Path(read_json(DO)['review']['path'])


def source_review(root, candidate):
    proposal = next(row for row in read_json(REVIEW)['proposals']
                    if row['candidate'] == candidate)
    path = root / (candidate + '-review.json')
    write_json(path, dict(schema='plan069-depth-source-review/v1',
        status='passed', candidate=candidate, reviewer='independent fixture reviewer',
        source_revision=proposal['candidate_config']['code']['revision'],
        profile_inventory=proposal['profile_inventory'],
        local_sources=local_source_records(candidate)))
    return file_record(path)


class DepthSetupAuthorizationTests(unittest.TestCase):
    def test_depth_gpu_slot_requires_fresh_head_and_is_one_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ledger = Ledger(root / 'ledger.jsonl', load())
            review, approved = file_record(REVIEW), file_record(DO)
            source = source_review(root, 'D7')
            proposal = next(row for row in read_json(REVIEW)['proposals']
                            if row['candidate'] == 'D7')
            from vipe_benchmark.files import object_hash
            def admit(head, path):
                write_json(path, dict(schema='plan069-depth-admission-result/v1',
                    status='passed', candidate='D7', proposal_sha256=object_hash(proposal),
                    review=review, authorization=approved, source_review=source,
                    commercial={}, assets=[], runtime={},
                    live=dict(ledger_head_sha256=head)))
                return file_record(path)
            stale = admit('f' * 64, root / 'stale.json')
            current = admit('0' * 64, root / 'current.json')
            reading = dict(gpu_pids=[], download_bytes=0, artifact_bytes=0,
                           device_bytes=0)
            with patch('vipe_benchmark.depth_admission.review', return_value=[]), \
                 patch('vipe_benchmark.execution.resources', return_value=reading):
                with self.assertRaisesRegex(ValueError, 'ledger head is stale'):
                    ledger.authorize_depth_attempt('D7', review, approved, source, stale)
                self.assertEqual(ledger.events(), [])
                ledger.authorize_depth_attempt('D7', review, approved, source, current)
                self.assertEqual(ledger.jobs['plan069-D7-maps-001']['seconds'], 3600)
                with self.assertRaisesRegex(ValueError, 'already authorized'):
                    ledger.authorize_depth_attempt('D7', review, approved, source, current)
                ledger.reserve('plan069-D7-maps-001', ['fixture'], dict(
                    request=current, worker=current, admission=current,
                    review=review, authorization=approved, source_review=source))
                ledger.finish('plan069-D7-maps-001', 'failed', 1)
                with self.assertRaisesRegex(ValueError, 'already consumed'):
                    ledger.reserve('plan069-D7-maps-001', ['no-retry'], current)

    def test_exact_approval_allocates_once_and_reservation_blocks_overlap(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger = Ledger(Path(directory) / 'ledger.jsonl', load())
            review, approved = file_record(REVIEW), file_record(DO)
            d7_review = source_review(Path(directory), 'D7')
            ledger.authorize_depth_setup('D7', review, approved, d7_review)
            self.assertEqual(ledger.jobs['plan069-D7-setup-001']['seconds'], 1800)
            with self.assertRaisesRegex(ValueError, 'unstarted depth setup'):
                ledger.authorize_depth_setup('D5', review, approved,
                    source_review(Path(directory), 'D5'))
            with self.assertRaisesRegex(ValueError, 'already authorized'):
                ledger.authorize_depth_setup('D7', review, approved, d7_review)
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
                    file_record(root / 'altered.json'), source_review(root, 'D7'))
            self.assertEqual(ledger.events(), [])

    def test_amended_caps_must_match_approved_record_and_live_headroom(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = dict(load(), new_download_gib_limit=110,
                          new_artifact_disk_gib_limit=210)
            ledger = Ledger(root / 'ledger.jsonl', config)
            review, approved = file_record(REVIEW), file_record(DO)
            d7_review = source_review(root, 'D7')
            altered = read_json(DO)
            altered['cap_approval']['amendment_sha256'] = '0' * 64
            write_json(root / 'invalid-cap.json', altered)
            with self.assertRaisesRegex(ValueError, 'exact approved depth cap amendment'):
                ledger.authorize_depth_setup('D7', review,
                    file_record(root / 'invalid-cap.json'), d7_review)
            with patch('vipe_benchmark.execution.resources', return_value=dict(
                    download_bytes=110 * 2**30, artifact_bytes=0)):
                with self.assertRaisesRegex(ValueError, 'download_bytes setup allocation'):
                    ledger.authorize_depth_setup('D7', review, approved,
                        d7_review)
            self.assertEqual(ledger.events(), [])


if __name__ == '__main__':
    unittest.main()
