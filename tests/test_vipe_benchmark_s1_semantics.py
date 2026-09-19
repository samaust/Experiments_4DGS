"""CPU-only S1 semantic amendment fixtures; no model imports or inference."""
import sys
import copy
import unittest
from pathlib import Path
from types import SimpleNamespace
from contextlib import nullcontext
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.backends import (BackendError, GroundingDetector, LegacyStandaloneBackend, detection_rows,
                                     s1_class_assignments)
from vipe_benchmark.contracts import instances


class Tokenizer:
    def __call__(self, caption):
        assert caption == 'person.basketball.'
        return {'input_ids': [101, 10, 1012, 11, 12, 1012, 102]}

    def decode(self, ids):
        return {(10,): 'person', (11, 12): 'basketball'}[tuple(ids)]


class Tensor:
    def __init__(self, data):
        self.data = np.asarray(data)
        self.dtype = self.data.dtype
    def cpu(self):
        return self
    def sigmoid(self):
        return Tensor(1 / (1 + np.exp(-self.data)))
    def numpy(self):
        return self.data
    def detach(self):
        return self


class S1SemanticsTests(unittest.TestCase):
    def assign(self, rows, phrases):
        return s1_class_assignments(np.asarray(rows), Tokenizer()('person.basketball.'),
                                    Tokenizer(), phrases, .5)

    def test_empty_combined_disagreement_tie_and_subword_sum(self):
        rows = [[0, .4, 0, .3, .2, 0, 0], [0, .8, 0, .1, .1, 0, 0],
                [0, .25, 0, .125, .125, 0, 0], [0, .2, 0, .4, .4, 0, 0]]
        result = self.assign(rows, ['', 'person basketball', 'person', 'person'])
        self.assertEqual([r['derived_class'] for r in result],
                         ['basketball', 'person', 'person', 'basketball'])
        self.assertEqual(result[0]['phrase_token_sums'], [.4, .5])
        self.assertIn('winner_below_native_text_threshold', result[0]['ambiguity_reasons'])
        self.assertIn('exact_phrase_sum_tie', result[2]['ambiguity_reasons'])
        self.assertIn('native_derived_disagreement', result[3]['ambiguity_reasons'])
        native = detection_rows([[1, 2, 3, 4]], [.4], [''], result[:1])[0]
        self.assertEqual((native['native_class'], native['score'], native['box']), ('', .4, [1, 2, 3, 4]))
        self.assertEqual(self.assign(np.empty((0, 7)), []), [])
        self.assertFalse(self.assign([[0, .8, 0, .1, .1, 0, 0]], ['person'])[0]['ambiguous'])

    def test_invalid_evidence_and_unamended_contract(self):
        for values in ([[0, float('nan'), 0, 0, 0, 0, 0]], [[2]*7], [[0]*3]):
            with self.assertRaises(BackendError):
                self.assign(values, [''])
        with self.assertRaises(BackendError):
            detection_rows([[0, 0, 1, 1]], [.4], [''])
        with self.assertRaises(BackendError):
            s1_class_assignments(np.zeros((1, 7)), {'input_ids': [101, 10, 102]}, Tokenizer(), [''], .5)

    def test_contract_rejects_missing_or_tampered_assignment(self):
        assignment = self.assign([[0, .4, 0, .3, .2, 0, 0]], [''])[0]
        item = detection_rows([[0, 0, 1, 1]], [.4], [''], [assignment])[0]
        labels, valid = np.ones((1, 1), np.int32), np.ones((1, 1), bool)
        instances(labels, {'1': item}, valid, (1, 1))
        missing = dict(item)
        del missing['class_assignment']
        with self.assertRaises(ValueError):
            instances(labels, {'1': missing}, valid, (1, 1))
        for field, value in [('policy', 'unknown'), ('winner_index', 0),
                             ('phrase_token_sums', [9, 9]), ('ambiguity_reasons', []),
                             ('derived_class', 'person'), ('phrase_token_scores', [[float('nan')], [.5]])]:
            bad = copy.deepcopy(item)
            bad['class_assignment'][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                instances(labels, {'1': bad}, valid, (1, 1))

    def detector(self, mismatch=False):
        # Query 0 is below box threshold; query 1 has no token above text threshold.
        logits = np.array([[[-3]*7, [-3, -.5, -3, -1, -1, -3, -3]]], np.float32)
        boxes = np.array([[[.1, .1, .1, .1], [.5, .5, .2, .4]]], np.float32)
        model = SimpleNamespace(tokenizer=Tokenizer(), forward=lambda *_: {
            'pred_logits': Tensor(logits), 'pred_boxes': Tensor(boxes)})
        def predict(model, image, caption, box_threshold, text_threshold, device):
            self.assertEqual((caption, box_threshold, text_threshold), ('person.basketball.', .35, .5))
            out = model.forward(image)
            scores = out['pred_logits'].cpu().sigmoid().numpy()[0]
            selected = scores.max(axis=1) > box_threshold
            return boxes[0][selected] + (1 if mismatch else 0), scores[selected].max(axis=1), ['']
        runtime = SimpleNamespace(device='fake:cpu', inference=nullcontext)
        return GroundingDetector(model, lambda *_: (np.zeros((3, 8, 8)), None),
                                 predict, runtime, .5, s1_assignment=True)

    def test_native_query_alignment_and_full_evidence(self):
        detector = self.detector()
        row = detector(np.zeros((10, 20, 3), np.uint8))[0]
        self.assertEqual(row['class'], 'basketball')
        self.assertEqual(row['native_class'], '')
        np.testing.assert_allclose(row['box'], [8, 3, 12, 7])
        np.testing.assert_array_equal(detector.diagnostics['detector_selected_query_indices'], [1])
        self.assertEqual(detector.diagnostics['detector_token_scores'].shape, (2, 7))
        with self.assertRaisesRegex(BackendError, 'alignment'):
            self.detector(True)(np.zeros((10, 20, 3), np.uint8))

    def test_assignment_survives_sam_and_pair_propagation(self):
        rgb = np.zeros((10, 20, 3), np.uint8)
        valid = np.ones((10, 20), bool)
        mask = np.zeros((1, 10, 20), bool)
        mask[0, 4, 9] = True
        sam = SimpleNamespace(set_image=lambda *_: None,
            predict=lambda **_: (mask, np.array([.9]), np.zeros((1, 2, 2))))
        tracker = SimpleNamespace(restart=lambda: None, add_reference_frame=lambda *_: None,
            track=lambda *_: mask.astype(np.int32), update_memory=lambda *_: None)
        detector = self.detector()
        backend = LegacyStandaloneBackend(detector, sam, tracker,
                                          SimpleNamespace(inference=nullcontext))
        first, second = backend.segment([rgb, rgb], [valid, valid], frame_ids=[20, 21])
        self.assertEqual(first.semantics, second.semantics)
        self.assertEqual(second.semantics['1']['native_class'], '')
        self.assertEqual(second.semantics['1']['class_assignment']['derived_class'], 'basketball')
        self.assertEqual(first.metadata['detections'][0]['score'], second.semantics['1']['score'])
        self.assertIn('detector_token_scores', first.diagnostics)


if __name__ == '__main__':
    unittest.main()
