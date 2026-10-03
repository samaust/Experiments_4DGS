"""CPU authorization seam: exact amended grants, unchanged historical lineage."""
import tempfile
from pathlib import Path
import unittest
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.depth_authorization import execution_authorization
from vipe_benchmark.config import ROOT

class DepthAuthorizationTests(unittest.TestCase):
    def test_approved_budget_amendment_routes_only_three_candidates(self):
        for candidate in ('D5', 'D6', 'D8'):
            review, auth, proposal, grant = execution_authorization(candidate)
            self.assertTrue(review['path'].endswith('depth-execution-review-002.json'))
            self.assertTrue(auth['path'].endswith('depth-approval-002.json'))
            self.assertEqual(proposal['allocation']['artifact_bytes'], 9663676416)
            self.assertEqual(grant['proposal_sha256'], object_hash(proposal))
            self.assertEqual(proposal['max_attempts'], 1)
        for candidate in ('D2', 'D7', 'D9', 'D10', 'D11'):
            review, auth, _, _ = execution_authorization(candidate)
            self.assertTrue(review['path'].endswith('depth-execution-review-001.json'))
            self.assertTrue(auth['path'].endswith('depth-approval-001.json'))

    def test_amended_grant_cannot_change_time_or_attempt_scope(self):
        import copy
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'docs/research/vipe-alternatives/plan031-execution'
            folder.mkdir(parents=True)
            baseline_path = ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'
            write_json(folder / baseline_path.name, read_json(baseline_path))
            approved = read_json(ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-002.json')
            reviewed = copy.deepcopy(read_json(approved['review']['path']))
            proposal = next(p for p in reviewed['proposals'] if p['candidate'] == 'D5')
            proposal['allocation']['setup_seconds'] = 3600
            for grant in approved['candidate_approvals']:
                if grant['candidate'] == 'D5':
                    grant['proposal_sha256'] = object_hash(proposal)
            review_path = root / 'review.json'
            write_json(review_path, reviewed)
            approved['review'] = file_record(review_path)
            write_json(folder / 'depth-approval-002.json', approved)
            with self.assertRaisesRegex(ValueError, 'budget-only'):
                execution_authorization('D5', root=root)

    def test_missing_amendment_does_not_fall_back_to_consumed_original_approval(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            folder = root / 'docs/research/vipe-alternatives/plan031-execution'
            folder.mkdir(parents=True)
            write_json(folder / 'depth-approval-001.json', read_json(ROOT / 'docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json'))
            with self.assertRaises(FileNotFoundError):
                execution_authorization('D8', root=root)

    def test_selection_module_is_bound_for_both_affected_setup_and_inference(self):
        from vipe_benchmark.depth_admission import local_source_records
        for candidate in ('D5', 'D6', 'D8', 'D11'):
            names = [Path(record['path']).name for record in local_source_records(candidate)]
            self.assertIn('depth_authorization.py', names)
