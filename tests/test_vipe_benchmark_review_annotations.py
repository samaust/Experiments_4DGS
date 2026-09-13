import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record
from vipe_benchmark.review_annotations import (ELIGIBILITY, IMAGE_FLAGS, PRIMARY_ID, Reader,
    SCHEMA, atomic_exclusive_json, audit_image, audit_pairs, finalize)


class IntegrityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.annotations = self.root / 'annotations'
        (self.annotations / 'layers').mkdir(parents=True)
        (self.annotations / 'overlays').mkdir()
        self.valid = np.ones((540, 960), dtype=bool)
        self.valid[0, 0] = False
        self.labels = np.zeros((540, 960), dtype=np.int32)
        self.labels[0, 0] = -1
        self.labels[10:20, 20:30] = 1
        Image.new('RGB', (960, 540)).save(self.root / 'rgb.png')
        Image.new('RGB', (960, 540)).save(self.annotations / 'overlays/image-000.png')
        np.save(self.root / 'valid.npy', self.valid)
        self.parent = dict(identity=dict(branch='calibration', camera=0, frame=50, pair_start=None),
            rgb=file_record(self.root / 'rgb.png'), valid=file_record(self.root / 'valid.npy'),
            K=[[800., 0., 479.5], [0., 800., 269.5], [0., 0., 1.]],
            grid='distorted-opencv-integer', static_feature_locations=[dict(index=6, uv=[42., 25.])])
        self.row = copy.deepcopy(self.parent)
        self.row.update(status='model-proposal', negative_labels_verified=False,
            eligibility=copy.deepcopy(ELIGIBILITY), tags={key: 'unknown' for key in IMAGE_FLAGS},
            review_overlay=file_record(self.annotations / 'overlays/image-000.png'),
            instances={'1': dict(**{'class': 'person'}, native_label=1, native_index=0, score=.9,
                box=[20., 10., 30., 20.], role='uncertain', role_uncertain=True,
                visibility='unknown', occlusion='unknown', blur='unknown', tiny_ball='unknown',
                source='model-inferred', independent_semantic_validation=False,
                proxy_mask_area=100, proxy_tiny_ball=False)},
            static_feature_review=[dict(index=6, suitable='uncertain', source='unreviewed')], ball_crops=[])
        self.write_layers()

    def tearDown(self):
        self.temp.cleanup()

    def write_layers(self, **changes):
        arrays = dict(instances=self.labels, valid=self.valid, ignored=np.zeros_like(self.valid),
                      changing=np.zeros_like(self.valid))
        arrays.update(changes)
        path = self.annotations / 'layers/image-000.npz'
        np.savez_compressed(path, **arrays)
        self.row['final_layers'] = file_record(path)

    def check(self):
        return audit_image(self.row, self.parent,
            Reader(dict(images=[self.parent]), self.annotations / 'proposal.json'))

    def test_valid_proxy_preserves_unknowns_and_does_not_claim_visual_review(self):
        result = self.check()
        self.assertEqual(result['integrity'], 'passed')
        self.assertEqual(result['review_mode'], 'structural-only')
        self.assertEqual(result['uncertain_features'], 1)
        self.assertTrue(result['unknowns_retained'])
        self.assertEqual(result['visual_findings'], [])

    def test_corrupt_file_and_validly_rehashed_footprint_corruption_are_rejected(self):
        path = Path(self.row['final_layers']['path'])
        with path.open('ab') as stream:
            stream.write(b'changed after freeze')
        with self.assertRaisesRegex(ValueError, 'hash/size'):
            self.check()
        labels = self.labels.copy()
        labels[0, 0] = 0
        self.write_layers(instances=labels)
        with self.assertRaisesRegex(ValueError, 'footprint mismatch'):
            self.check()

    def test_semantic_and_feature_uncertainty_cannot_be_promoted(self):
        self.row['instances']['1']['role'] = 'player'
        with self.assertRaisesRegex(ValueError, 'uncertainty promoted'):
            self.check()
        self.row['instances']['1']['role'] = 'uncertain'
        self.row['static_feature_review'][0]['suitable'] = True
        with self.assertRaisesRegex(ValueError, 'feature uncertainty changed'):
            self.check()

    def test_grid_and_empty_changing_layer_cannot_silently_change(self):
        self.row['grid'] = 'undistorted-opencv-integer'
        with self.assertRaisesRegex(ValueError, 'provenance changed'):
            self.check()
        self.row['grid'] = self.parent['grid']
        changing = np.zeros_like(self.valid)
        changing[30, 50] = True
        self.write_layers(changing=changing)
        with self.assertRaisesRegex(ValueError, 'changing/ignored truth'):
            self.check()

    def test_correct_hash_cannot_authorize_an_unlisted_input(self):
        reader = Reader(dict(images=[self.parent]), self.annotations / 'proposal.json')
        with self.assertRaisesRegex(ValueError, 'outside exact annotation template'):
            reader.record(self.row['review_overlay'], 'input')


class PairTests(unittest.TestCase):
    def test_duplicate_pair_and_uncovered_visible_identity_are_rejected(self):
        pairs = [dict(camera=1, pair_start=i * 2,
                      associations=[dict(first_id=1, second_id=1, proxy_iou=.8,
                                         status='model-inferred', eligible=False)]) for i in range(112)]
        parents = copy.deepcopy(pairs)
        images = {f'reconstruction/camera1/frame{i}': dict(instances={'1': {'class': 'person'}})
                  for i in range(224)}
        audit_pairs(pairs, parents, images)
        pairs[1] = copy.deepcopy(pairs[0])
        with self.assertRaisesRegex(ValueError, '112 exact unique pairs'):
            audit_pairs(pairs, parents, images)
        pairs = copy.deepcopy(parents)
        pairs[1]['associations'] = []
        with self.assertRaisesRegex(ValueError, 'pair identity coverage'):
            audit_pairs(pairs, parents, images)


class PublicationTests(unittest.TestCase):
    def test_atomic_exclusive_publication_never_replaces_existing_evidence(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'decision.json'
            atomic_exclusive_json(path, {'complete': True})
            with self.assertRaises(FileExistsError):
                atomic_exclusive_json(path, {'replacement': True})
            self.assertEqual(json.loads(path.read_text()), {'complete': True})
            self.assertEqual(list(path.parent.iterdir()), [path])

    def test_visual_claim_requires_actual_attestation_and_bound_inspected_file(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            fixture = root / 'fixture.json'
            fixture.write_text('{}')
            record = file_record(fixture)
            images = [dict(identity=dict(branch='reconstruction', camera=1, frame=i, pair_start=None),
                           review_mode='structural-only', visual_findings=[]) for i in range(232)]
            audit = dict(schema=SCHEMA, status='integrity-passed', images=images, pairs=112,
                         uncertain_features=768, template=record, proposal=record, audit_source=record,
                         inspected_file_hashes=[record])
            observations = dict(reviewer_id='fixture-reviewer', candidate_outputs_seen=False,
                proposal_sha256=record['sha256'], actual_visual_inspection=False, viewed_files=[record],
                images=[dict(images[0], review_mode='integrity-and-native-sheet-visual',
                             visual_findings=['fixture observed'], viewed_file_sha256s=['unseen-hash'])])
            audit_path, notes_path, output = root / 'audit.json', root / 'notes.json', root / 'decision.json'
            audit_path.write_text(json.dumps(audit))
            notes_path.write_text(json.dumps(observations))
            with self.assertRaisesRegex(ValueError, 'visual attestation'):
                finalize(audit_path, notes_path, output, 'fixture-reviewer')
            observations['actual_visual_inspection'] = True
            notes_path.write_text(json.dumps(observations))
            with self.assertRaisesRegex(ValueError, 'inspected file hashes'):
                finalize(audit_path, notes_path, output, 'fixture-reviewer')
            self.assertFalse(output.exists())
            with self.assertRaisesRegex(ValueError, 'independent reviewer'):
                finalize(audit_path, notes_path, output, PRIMARY_ID)


if __name__ == '__main__':
    unittest.main()
