import copy
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.auto_annotations import PRIMARY_ID, SCHEMA, check_policy, finish_review, merge_teacher, validate
from vipe_benchmark.annotations import template
from vipe_benchmark.access import annotation_identities
from vipe_benchmark.config import ROOT, load
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.ledger import Ledger


class PolicyHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.policy = read_json(ROOT / 'docs/research/vipe-alternatives/plan031-20260913T032700Z/annotation-amendment-001.json')
        self.archive = self.root / 'annotation-policy-parents'
        self.archive.mkdir()
        for field in ('original_plan', 'original_protocol', 'historical_authorization'):
            path = self.root / field
            path.write_text('original ' + field)
            self.policy[field] = file_record(path)
            (self.archive / self.policy[field]['sha256']).write_bytes(path.read_bytes())

    def check(self):
        write_json(self.root / 'policy.json', self.policy)
        return check_policy(file_record(self.root / 'policy.json'))

    def test_exact_historical_parents_survive_amendments_without_rewriting_policy(self):
        for field in ('original_plan', 'historical_authorization'):
            (self.root / field).write_text('amended current document')
        self.assertEqual(self.check(), self.policy)
        self.assertFalse(self.policy['human_ground_truth'])

    def test_missing_original_requires_exact_archive(self):
        (self.root / 'original_plan').unlink()
        self.assertEqual(self.check(), self.policy)

    def test_changed_parent_without_archive_is_rejected(self):
        (self.root / 'original_plan').write_text('changed')
        (self.archive / self.policy['original_plan']['sha256']).unlink()
        with self.assertRaisesRegex(ValueError, 'changed file'):
            self.check()

    def test_tampered_archive_is_rejected(self):
        (self.root / 'historical_authorization').write_text('changed')
        (self.archive / self.policy['historical_authorization']['sha256']).write_text('fabricated')
        with self.assertRaisesRegex(ValueError, 'changed file'):
            self.check()

    def test_protocol_remains_live_even_with_exact_archive(self):
        (self.root / 'original_protocol').write_text('changed')
        with self.assertRaisesRegex(ValueError, 'changed file'):
            self.check()

    def test_archive_cannot_hide_forbidden_original_path(self):
        self.policy['original_plan']['path'] = str(self.root / 'prompts' / 'never-read')
        with self.assertRaisesRegex(ValueError, 'prompts access is prohibited'):
            self.check()


class MergeTests(unittest.TestCase):
    def test_overlaps_preserve_probability_score_order_and_ignore_other_coco_classes(self):
        valid = np.ones((2, 3), bool)
        valid[0, 0] = False
        masks = np.full((4, 1, 2, 3), .8, np.float32)
        masks[1, 0, 1, 1] = .9
        labels, meta = merge_teacher(dict(masks=masks, labels=[1, 37, 2, 1],
            scores=[.9, .8, .99, .4], boxes=np.zeros((4, 4))), valid)
        self.assertEqual(labels.tolist(), [[-1, 1, 1], [1, 2, 1]])
        self.assertEqual(set(meta), {'1', '2'})
        self.assertEqual(meta['2']['class'], 'basketball')
        self.assertEqual(meta['1']['role'], 'uncertain')
        self.assertFalse(meta['1']['independent_semantic_validation'])

    def test_empty_detections_do_not_invent_instances(self):
        labels, meta = merge_teacher(dict(masks=np.empty((0, 1, 2, 3)), labels=[],
            scores=[], boxes=np.empty((0, 4))), np.ones((2, 3), bool))
        self.assertEqual(meta, {})
        self.assertFalse(labels.any())


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.config = load()
        valid = np.ones((540, 960), bool)
        np.save(self.root / 'valid.npy', valid)
        np.savez_compressed(self.root / 'layers.npz', instances=np.zeros(valid.shape, np.int32),
                            valid=valid, changing=np.zeros_like(valid), ignored=np.zeros_like(valid))
        (self.root / 'rgb.fixture').write_bytes(b'not a model output; synthetic RGB fixture')
        image, footprint, layers = [file_record(self.root / name) for name in ('rgb.fixture', 'valid.npy', 'layers.npz')]
        self.inputs = dict(rgb=[dict(identity=i.record(), rgb=image, valid=footprint,
            K=np.eye(3).tolist(), grid='fixture', static_feature_locations=[])
            for i in annotation_identities(self.config)])
        proposal = template(self.inputs, self.config)
        policy = file_record(ROOT / 'docs/research/vipe-alternatives/plan031-20260913T032700Z/annotation-amendment-001.json')
        proposal.update(schema=SCHEMA, evidence_kind='model-assisted-proxy', human_ground_truth=False,
            status='proposal', policy=policy, checkpoint=image, unknowns=['roles', 'motion'],
            contributors={'primary': dict(id=PRIMARY_ID, kind='model-cpu')})
        for row in proposal['images']:
            row.update(final_layers=layers, instances={}, status='model-proposal',
                       eligibility={'changing': False}, negative_labels_verified=False,
                       static_feature_review=[])
        for row in proposal['pairs']:
            row['associations'] = []
        write_json(self.root / 'proposal.json', proposal)
        proposal_record = file_record(self.root / 'proposal.json')
        decision = dict(status='accepted-proxy-with-unknowns', reviewer_id='independent-fixture-reviewer',
            proposal_sha256=proposal_record['sha256'], candidate_outputs_seen=False,
            review_scope='automated-integrity-plus-documented-visual-inspection',
            images=[dict(identity=r['identity'], layers_sha256=layers['sha256'], integrity='passed',
                         unknowns_retained=True) for r in proposal['images']])
        write_json(self.root / 'review/decision.json', decision)

    def tearDown(self):
        self.temp.cleanup()

    def test_complete_proxy_review_is_distinct_from_human_truth(self):
        finish_review(self.root, self.inputs, self.config)
        bundle = read_json(self.root / 'annotations.json')
        result = validate(bundle, self.inputs, self.config)
        self.assertEqual((result['images'], result['pairs']), (232, 112))
        self.assertFalse(result['human_ground_truth'])
        bundle['human_ground_truth'] = True
        with self.assertRaisesRegex(ValueError, 'human-truth'):
            validate(bundle, self.inputs, self.config)

    def test_missing_review_or_uncertainty_upgrade_rejected(self):
        finish_review(self.root, self.inputs, self.config)
        bundle = read_json(self.root / 'annotations.json')
        bundle['images'][0]['negative_labels_verified'] = True
        with self.assertRaisesRegex(ValueError, 'uncertainty'):
            validate(bundle, self.inputs, self.config)
        bundle['images'].pop()
        with self.assertRaisesRegex(ValueError, '232'):
            validate(bundle, self.inputs, self.config)

    def test_acquisition_time_is_charged_without_resetting_or_extra_attempt(self):
        ledger = Ledger(self.root / 'ledger.jsonl', self.config)
        evidence = file_record(self.root / 'proposal.json')
        ledger.charge_cpu_preparation(2.5, evidence)
        self.assertEqual(ledger.totals()['cpu']['elapsed_seconds'], 2.5)
        self.assertEqual(ledger.totals()['cpu']['attempts'], 0)
        with self.assertRaisesRegex(ValueError, 'already charged'):
            ledger.charge_cpu_preparation(2.5, evidence)
        reservation = ledger.reserve('annotations', ['fixture'], {}, seconds_limit=12.)
        self.assertEqual(reservation['seconds'], 12.)


if __name__ == '__main__':
    unittest.main()
