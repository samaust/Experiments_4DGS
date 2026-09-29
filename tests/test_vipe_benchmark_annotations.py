import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.access import annotation_identities
from vipe_benchmark.annotations import IMAGE_FLAGS, INSTANCE_FLAGS, template, validate
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, write_json
from vipe_benchmark.ledger import Ledger
import basketball_vipe_benchmark as controller


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

    def test_proxy_cannot_be_relabelled_as_human_truth(self):
        bundle = self.complete()
        for changes in ({'schema': 'vipe-benchmark-automated-annotations/v1'},
                        {'human_ground_truth': False}, {'evidence_kind': 'model-assisted-proxy'}):
            with self.subTest(changes=changes):
                substituted = copy.deepcopy(bundle)
                substituted.update(changes)
                with self.assertRaisesRegex(ValueError, 'independent human'):
                    validate(substituted, self.inputs, self.config)

    def test_rejected_import_does_not_allocate_or_replace_proxy_history(self):
        bundle = self.complete()
        bundle['human_ground_truth'] = False
        write_json(self.root / 'incoming.json', bundle)
        write_json(self.root / 'prepare/inputs.json', self.inputs)
        # Existing proxy publication and ledger remain untouched by preflight rejection.
        write_json(self.root / 'annotations/annotations.json', {'evidence_kind': 'model-assisted-proxy'})
        proxy = (self.root / 'annotations/annotations.json').read_bytes()
        write_json(self.root / 'docs/exposure-history.json', {})
        ledger = Ledger(self.root / 'ledger.jsonl', self.config)
        args = SimpleNamespace(command='annotations', bundle=self.root / 'incoming.json')
        with patch.object(controller, 'check_run', return_value=(self.root, self.root / 'docs', ledger)):
            with self.assertRaisesRegex(ValueError, 'independent human'):
                controller.cpu_stage(args, self.config)
        self.assertFalse((self.root / 'annotations-request.json').exists())
        self.assertFalse((self.root / 'annotations/result.json').exists())
        self.assertEqual((self.root / 'annotations/annotations.json').read_bytes(), proxy)
        self.assertEqual(ledger.events(), [])

    def test_import_worker_refuses_unreviewed_or_changed_evidence(self):
        bundle = self.complete()
        write_json(self.root / 'inputs.json', self.inputs)
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        config_path = scripts.parent / 'configs/vipe-alternatives/benchmark-v1.json'
        baseline = copy.deepcopy(bundle)
        cases = ['attestation', 'same-person', 'blindness', 'revision', 'duplicate',
                 'substitution', 'unresolved', 'layers', 'association']
        for name in cases:
            with self.subTest(name=name):
                changed = copy.deepcopy(baseline)
                if name == 'attestation':
                    changed['contributors']['primary'].pop('attestation')
                elif name == 'same-person':
                    changed['contributors']['independent_review']['id'] = 'primary'
                elif name == 'blindness':
                    changed['blinded_to_candidate_outputs'] = False
                elif name == 'revision':
                    changed['images'][0]['primary_revision']['sha256'] = '0' * 64
                elif name == 'duplicate':
                    changed['images'][-1] = copy.deepcopy(changed['images'][0])
                elif name == 'substitution':
                    changed['images'][0]['identity']['frame'] = 51
                elif name == 'unresolved':
                    write_json(self.root / 'unresolved.json', dict(review_sha256=changed['images'][0]['review_record']['sha256'],
                        final_layers_sha256=changed['images'][0]['final_layers']['sha256'], unresolved_disagreements=1))
                    changed['images'][0]['adjudication_record'] = file_record(self.root / 'unresolved.json')
                elif name == 'layers':
                    np.savez_compressed(self.root / 'bad-layers.npz', instances=np.zeros((1, 1), np.int32))
                    changed['images'][0]['final_layers'] = file_record(self.root / 'bad-layers.npz')
                    write_json(self.root / 'bad-adjudication.json', dict(review_sha256=changed['images'][0]['review_record']['sha256'],
                        final_layers_sha256=changed['images'][0]['final_layers']['sha256'], unresolved_disagreements=0))
                    changed['images'][0]['adjudication_record'] = file_record(self.root / 'bad-adjudication.json')
                elif name == 'association':
                    changed['pairs'][0]['associations'] = [dict(first_id=99, second_id=None)]
                incoming = self.root / (name + '-bundle.json')
                write_json(incoming, changed)
                request = self.root / (name + '-request.json')
                write_json(request, dict(configuration=file_record(config_path), inputs=file_record(self.root / 'inputs.json'),
                    annotations=file_record(incoming)))
                output = self.root / (name + '-output')
                result = subprocess.run([sys.executable, str(scripts / 'basketball_vipe_worker.py'),
                    '--operation', 'annotations', '--config', str(config_path), '--request', str(request),
                    '--output', str(output)], capture_output=True, text=True, timeout=30)
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertFalse(output.exists(), result.stderr)

    def test_worker_publishes_only_complete_hash_bound_human_fixture(self):
        bundle = self.complete()
        write_json(self.root / 'complete-bundle.json', bundle)
        write_json(self.root / 'inputs.json', self.inputs)
        scripts = Path(__file__).resolve().parents[1] / 'scripts'
        config_path = scripts.parent / 'configs/vipe-alternatives/benchmark-v1.json'
        write_json(self.root / 'request.json', dict(configuration=file_record(config_path),
            inputs=file_record(self.root / 'inputs.json'), annotations=file_record(self.root / 'complete-bundle.json')))
        output = self.root / 'imported'
        command = [sys.executable, str(scripts / 'basketball_vipe_worker.py'), '--operation', 'annotations',
            '--config', str(config_path), '--request', str(self.root / 'request.json'), '--output', str(output)]
        subprocess.run(command, check=True, capture_output=True, timeout=30)
        from vipe_benchmark.files import read_json, verify_record
        result = read_json(output / 'result.json')
        self.assertEqual(result['status'], 'complete')
        verify_record(result['annotations'])
        verify_record(result['validation'])
        self.assertEqual(result['source_bundle'], file_record(self.root / 'complete-bundle.json'))
        self.assertEqual(read_json(result['validation']['path'])['images'], 232)
        previous = (output / 'annotations.json').read_bytes()
        retry = subprocess.run(command, capture_output=True, timeout=30)
        self.assertNotEqual(retry.returncode, 0)
        self.assertEqual((output / 'annotations.json').read_bytes(), previous)

    def test_visible_semantics_changing_ignored_and_pair_identity_contract(self):
        bundle = self.complete()
        valid = np.ones((540, 960), bool)
        labels = np.zeros(valid.shape, np.int32)
        labels[0, 0], labels[0, 1] = 1, 2
        changing, ignored = np.zeros_like(valid), np.zeros_like(valid)
        changing[0, 2], ignored[0, 3] = True, True
        np.savez_compressed(self.root / 'visible-truth.npz', instances=labels,
                            changing=changing, valid=valid, ignored=ignored)
        truth = file_record(self.root / 'visible-truth.npz')
        write_json(self.root / 'visible-adjudication.json', dict(review_sha256=bundle['images'][0]['review_record']['sha256'],
            final_layers_sha256=truth['sha256'], unresolved_disagreements=0))
        flags = {key: False for key in INSTANCE_FLAGS}
        for row in bundle['images']:
            row.update(final_layers=truth, adjudication_record=file_record(self.root / 'visible-adjudication.json'),
                instances={'1': dict(flags, **{'class': 'person', 'role': 'player'}),
                           '2': dict(flags, **{'class': 'basketball'})})
        for row in bundle['pairs']:
            row['associations'] = [dict(first_id=1, second_id=1), dict(first_id=2, second_id=2)]
        self.assertEqual(validate(bundle, self.inputs, self.config)['pairs'], 112)
        bundle['images'][0]['instances']['1']['role'] = 'model-person'
        with self.assertRaisesRegex(ValueError, 'independently annotated'):
            validate(bundle, self.inputs, self.config)
        bundle['images'][0]['instances']['1']['role'] = 'player'
        bundle['pairs'][0]['associations'][1]['first_id'] = 1
        with self.assertRaisesRegex(ValueError, 'missing/duplicate'):
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
