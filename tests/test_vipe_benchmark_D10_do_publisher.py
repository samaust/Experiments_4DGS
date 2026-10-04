"""CPU-only publication seam: real frame gate, isolated receipts, fake acceptance."""
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import test_vipe_benchmark_video_frame_authorization as fixtures
from vipe_benchmark.files import file_record, object_hash, read_json

PRODUCER = Path(__file__).resolve().parents[1] / 'docs/research/vipe-alternatives/plan031-execution/video-post-recovery-controls-001/prepare_D10.py'
spec = importlib.util.spec_from_file_location('D10_do_publisher', PRODUCER)
assert spec is not None and spec.loader is not None
publisher = importlib.util.module_from_spec(spec)
spec.loader.exec_module(publisher)


class PublisherTests(unittest.TestCase):
    def setUp(self):
        self.f = fixtures.FrameAuthorityTests()
        self.f.setUp()
        self.addCleanup(self.f.doCleanups)
        _, self.prefix, self.rows = self.f.recovery_prerequisite_fixture(repair=True)
        self.root = self.f.root
        self.review = self.root / 'review.json'
        fixtures.write_json(self.review, self.f.review)
        self.approval = self.root / 'user-approval.json'
        self.approval_value = dict(schema='plan069-D10-frame-user-approval/v1',
            status='approved', candidate='D10', review=file_record(self.review),
            proposal_sha256=object_hash(self.f.proposal), max_attempts=1,
            optional_decoder_omission_approved=True,
            authorization_basis='CPU fixture only; never actual user authority')
        fixtures.write_json(self.approval, self.approval_value)
        self.output = self.root / 'DO.json'
        self.ledger_bytes = (self.root / 'ledger.jsonl').read_bytes()

    def publish(self, *, accept=True):
        with patch('vipe_benchmark.config.ROOT', self.root):
            if accept:
                # Only the accepted-recovery producer is faked. The public frame
                # gate still checks profile, assets, science, charge and ancestry.
                with patch('vipe_benchmark.depth_recovery_lineage.accepted_setup_lineage',
                           return_value=dict(finish=self.rows[0])):
                    return publisher.prepare(self.root, self.root, self.review,
                        self.f.qual_path, self.prefix['path'], self.approval, self.output)
            return publisher.prepare(self.root, self.root, self.review,
                self.f.qual_path, self.prefix['path'], self.approval, self.output)

    def test_publish_preserves_prior_caps_and_consumption(self):
        result = self.publish()
        self.assertEqual(read_json(self.output), result)
        prior = read_json(self.f.prior_path)
        for key in ('cap_amendment', 'cap_approval', 'video_amendment'):
            self.assertEqual(result[key], prior[key])
        self.assertIs(result['reset_previous_consumption'], False)
        self.assertEqual(result['candidate_approvals'][0]['max_attempts'], 1)
        self.assertEqual(result['user_approval'], file_record(self.approval))
        self.assertEqual((self.root / 'ledger.jsonl').read_bytes(), self.ledger_bytes)

    def test_no_approval_no_output(self):
        for key, value in (('status', 'REVIEW'), ('candidate', 'D9'),
                ('proposal_sha256', 'wrong'), ('max_attempts', 2), ('max_attempts', True),
                ('optional_decoder_omission_approved', False),
                ('authorization_basis', ''), ('authorization_basis', None),
                ('review', {}), ('schema', 'wrong')):
            with self.subTest(key=key, value=value):
                fixtures.write_json(self.approval, dict(self.approval_value, **{key: value}))
                with self.assertRaisesRegex(ValueError, 'user approval'):
                    self.publish()
                self.assertFalse(self.output.exists())
        self.approval.unlink()
        with self.assertRaises(FileNotFoundError):
            self.publish()
        self.assertFalse(self.output.exists())

    def test_schema_alone_does_not_establish_accepted_recovery(self):
        with self.assertRaisesRegex(ValueError, 'unique accepted recovery'):
            self.publish(accept=False)
        self.assertFalse(self.output.exists())

    def test_actual_D9_and_exact_recovery002_required(self):
        original = read_json(self.f.qual_path)
        for key, value in (('record_kind', 'fixture'), ('candidate', 'D10'), ('status', 'failed')):
            with self.subTest(key=key):
                fixtures.write_json(self.f.qual_path, dict(original, **{key: value}))
                with self.assertRaisesRegex(ValueError, 'actual passed D9'):
                    self.publish()
                self.assertFalse(self.output.exists())
        fixtures.write_json(self.f.qual_path, original)
        setup_path = Path(original['setup']['path'])
        setup = read_json(setup_path)
        for field, value in (('schema', 'plan069-video-setup-recovery-result/v1'),
                             ('job_id', 'plan069-D9-setup-recovery-001')):
            fixtures.write_json(setup_path, dict(setup, **{field: value}))
            fixtures.write_json(self.f.qual_path, dict(original, setup=file_record(setup_path)))
            with self.assertRaisesRegex(ValueError, 'recovery002'):
                self.publish()
            self.assertFalse(self.output.exists())

    def test_missing_finalization_charge_rejected(self):
        data = (json.dumps(self.rows[0]) + '\n').encode()
        Path(self.prefix['path']).write_bytes(data)
        (self.root / 'ledger.jsonl').write_bytes(data)
        with self.assertRaisesRegex(ValueError, 'finalization charge'):
            self.publish()
        self.assertFalse(self.output.exists())

    def test_stale_live_prefix_rejected(self):
        (self.root / 'ledger.jsonl').write_bytes(self.ledger_bytes + b'\n')
        with self.assertRaisesRegex(ValueError, 'exact current'):
            self.publish()
        self.assertFalse(self.output.exists())

    def test_public_gate_blocks_scientific_scope_change(self):
        review = read_json(self.review)
        review['proposals'][0]['allocation']['gpu_seconds'] += 1
        fixtures.write_json(self.review, review)
        approval = dict(self.approval_value, review=file_record(self.review),
                        proposal_sha256=object_hash(review['proposals'][0]))
        fixtures.write_json(self.approval, approval)
        with self.assertRaisesRegex(ValueError, 'science, caps'):
            self.publish()
        self.assertFalse(self.output.exists())

    def test_prior_D10_grant_rejected(self):
        row = dict(event='depth_setup_authorized', candidate='D10', sequence=0, previous_sha256=None)
        row['event_sha256'] = object_hash(row)
        Path(self.prefix['path']).write_text(json.dumps(row) + '\n')
        with self.assertRaisesRegex(ValueError, 'already started'):
            self.publish()
        self.assertFalse(self.output.exists())

    def test_fresh_output_and_symlink_required(self):
        self.publish()
        original = self.output.read_bytes()
        with self.assertRaisesRegex(ValueError, 'fresh immutable'):
            self.publish()
        self.assertEqual(self.output.read_bytes(), original)
        self.output.unlink()
        self.output.symlink_to(self.root / 'missing')
        with self.assertRaisesRegex(ValueError, 'fresh immutable'):
            self.publish()
        self.assertFalse((self.root / 'missing').exists())

    def test_mutation_during_gate_blocks_publication(self):
        from vipe_benchmark.depth_video_frame_authorization import validate_frame_amendment
        def changed(*args, **kwargs):
            validate_frame_amendment(*args, **kwargs)
            self.approval.write_text('{}')
        with patch('vipe_benchmark.depth_video_frame_authorization.validate_frame_amendment', side_effect=changed):
            with self.assertRaisesRegex(ValueError, 'changed during publication'):
                self.publish()
        self.assertFalse(self.output.exists())
