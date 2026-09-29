import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.access import annotation_identities
from vipe_benchmark.annotations import IMAGE_FLAGS, template, validate
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, write_json


class AnnotationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.config = load()
        # Synthetic fixtures have no scientific status and never enter a run ledger.
        valid = np.ones((540, 960), bool)
        np.save(self.root / 'valid.npy', valid)
        np.savez_compressed(self.root / 'truth.npz', instances=np.zeros(valid.shape, np.int32),
                           changing=np.zeros_like(valid), valid=valid, ignored=np.zeros_like(valid))
        (self.root / 'rgb.fixture').write_bytes(b'synthetic RGB identity fixture')
        write_json(self.root / 'attestation.json', dict(kind='synthetic fixture only'))
        rgb, footprint = file_record(self.root / 'rgb.fixture'), file_record(self.root / 'valid.npy')
        self.inputs = dict(rgb=[dict(identity=i.record(), rgb=rgb, valid=footprint,
            K=np.eye(3).tolist(), grid='fixture-grid', static_feature_locations=[])
            for i in annotation_identities(self.config)])
        self.bundle = template(self.inputs, self.config)

    def tearDown(self):
        self.tmp.cleanup()

    def complete(self):
        truth = file_record(self.root / 'truth.npz')
        self.bundle['contributors'] = {k: dict(id=k, kind='external_human', attestation=file_record(self.root / 'attestation.json'))
                                       for k in ('primary', 'independent_review')}
        write_json(self.root / 'review.json', dict(reviewer_id='independent_review',
            primary_revision_sha256=truth['sha256'], blind_to_outputs_methods_scores=True))
        review = file_record(self.root / 'review.json')
        write_json(self.root / 'adjudication.json', dict(review_sha256=review['sha256'],
            final_layers_sha256=truth['sha256'], unresolved_disagreements=0))
        for row in self.bundle['images']:
            row.update(status='reviewed-adjudicated', final_layers=truth, instances={}, tags={k: False for k in IMAGE_FLAGS},
                       primary_revision=truth, review_record=review,
                       adjudication_record=file_record(self.root / 'adjudication.json'), static_feature_review=[])
        for row in self.bundle['pairs']:
            row['associations'] = []
        return self.bundle

    def test_incomplete_template_cannot_admit_models(self):
        self.assertEqual(len(self.bundle['images']), 232)
        self.assertEqual(len(self.bundle['pairs']), 112)
        with self.assertRaisesRegex(ValueError, 'external contributor'):
            validate(self.bundle, self.inputs, self.config)

    def test_every_image_review_and_exact_rgb_are_required(self):
        bundle = self.complete()
        result = validate(bundle, self.inputs, self.config)
        self.assertEqual((result['images'], result['pairs']), (232, 112))
        bundle['images'][-1]['status'] = 'primary-only'
        with self.assertRaisesRegex(ValueError, 'incomplete'):
            validate(bundle, self.inputs, self.config)
        bundle['images'].pop()
        with self.assertRaisesRegex(ValueError, '232'):
            validate(bundle, self.inputs, self.config)

    def test_same_reviewer_and_budget_transfer_rejected(self):
        bundle = self.complete()
        bundle['contributors']['independent_review']['id'] = 'primary'
        with self.assertRaisesRegex(ValueError, 'must differ'):
            validate(bundle, self.inputs, self.config)
        bundle['contributors']['independent_review']['id'] = 'independent_review'
        bundle['person_hours']['adjudication'] = 9.
        with self.assertRaisesRegex(ValueError, 'separate allocations'):
            validate(bundle, self.inputs, self.config)

    def test_grid_tampering_and_unblinded_review_rejected(self):
        bundle = self.complete()
        bundle['images'][0]['grid'] = 'wrong-grid'
        with self.assertRaisesRegex(ValueError, 'provenance'):
            validate(bundle, self.inputs, self.config)
        bundle['blinded_to_candidate_outputs'] = False
        with self.assertRaisesRegex(ValueError, 'blinded'):
            validate(bundle, self.inputs, self.config)


class IsolationTests(unittest.TestCase):
    def test_neutral_modules_load_with_vipe_imports_and_source_denied(self):
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        code = '''
import sys
from pathlib import Path
sys.path.insert(0, sys.argv[1])
from vipe_benchmark.isolation import deny_vipe
deny_vipe([sys.argv[2]])
from vipe_benchmark import contracts, scale, geometry, metrics, motion, neighbors
for name in ('vipe', 'vipe_ext'):
    try:
        __import__(name)
    except ImportError:
        pass
    else:
        raise AssertionError('ViPE import allowed')
try:
    Path(sys.argv[2], 'source.py').read_text()
except PermissionError:
    pass
else:
    raise AssertionError('ViPE source access allowed')
try:
    Path(sys.argv[3], 'source.py').read_text()
except PermissionError:
    pass
else:
    raise AssertionError('symlink source access allowed')
'''
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'source').mkdir()
            (root / 'source/source.py').write_text('synthetic forbidden source')
            (root / 'alias').symlink_to(root / 'source')
            subprocess.run([sys.executable, '-c', code, str(scripts), str(root / 'source'), str(root / 'alias')], check=True, timeout=20)


if __name__ == '__main__':
    unittest.main()
