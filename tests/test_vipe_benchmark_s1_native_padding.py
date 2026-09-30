"""Worker evidence checks for the pinned GroundingDINO caption padding."""
import copy
import unittest

import numpy as np

import test_vipe_benchmark_s1_recovery as recovery_fixture
from vipe_benchmark import s1_recovery
from vipe_benchmark.s1_evidence import numeric_file, qualify_row


class NativePaddingTests(unittest.TestCase):
    def setUp(self):
        self.fixture = recovery_fixture.S1RecoveryTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.request = dict(self.fixture.original, job_id=s1_recovery.JOB)
        self.row, self.arrays = recovery_fixture.synthetic_row(self.fixture.root/'numeric', self.request)

    def padded(self):
        # Six literal caption tokens followed by 250 native masked slots.
        arrays = {k: v.copy() for k, v in self.arrays.items()}
        arrays['detector_raw_token_logits'] = np.concatenate(
            (arrays['detector_raw_token_logits'], np.full((len(arrays['detector_raw_token_logits']), 250), -np.inf, np.float32)), axis=1)
        arrays['detector_token_scores'] = np.concatenate(
            (arrays['detector_token_scores'], np.zeros((len(arrays['detector_token_scores']), 250), np.float32)), axis=1)
        return arrays

    def qualify(self, arrays, name):
        row = copy.deepcopy(self.row)
        row['diagnostics'] = numeric_file(self.fixture.root/(name+'.npz'), arrays)
        return qualify_row(row, self.request, first=True)

    def test_native_masked_caption_padding_preserves_raw_evidence(self):
        arrays = self.padded()
        self.assertTrue(self.qualify(arrays, 'native'))
        self.assertTrue(np.isneginf(arrays['detector_raw_token_logits'][:, 6:]).all())
        self.assertTrue((arrays['detector_token_scores'][:, 6:] == 0).all())

    def test_only_exact_inactive_mask_sentinels_are_accepted(self):
        for name, field, position, value in [
                ('active_negative_inf', 'detector_raw_token_logits', (0, 1), -np.inf),
                ('active_nan', 'detector_raw_token_logits', (0, 1), np.nan),
                ('active_positive_inf', 'detector_raw_token_logits', (0, 1), np.inf),
                ('padding_nan', 'detector_raw_token_logits', (0, 6), np.nan),
                ('padding_positive_inf', 'detector_raw_token_logits', (0, 6), np.inf),
                ('padding_finite', 'detector_raw_token_logits', (0, 6), -100),
                ('padding_nonzero', 'detector_token_scores', (0, 6), 1e-12),
                ('padding_negative', 'detector_token_scores', (0, 6), -1e-12),
                ('padding_nan_score', 'detector_token_scores', (0, 6), np.nan),
                ('active_sigmoid_mismatch', 'detector_token_scores', (0, 1), .99),
                ('box_nan', 'detector_raw_boxes_cxcywh', (0, 0), np.nan)]:
            with self.subTest(name=name):
                arrays = self.padded()
                arrays[field][position] = value
                with self.assertRaisesRegex(ValueError, 'invalid raw S1'):
                    self.qualify(arrays, name)

    def test_frozen_caption_and_padding_width_are_required(self):
        arrays = self.padded()
        arrays['detector_token_ids'][1] = 3455
        with self.assertRaisesRegex(ValueError, 'frozen caption'):
            self.qualify(arrays, 'foreign_caption')
        for width in (5, 7, 255, 257):
            with self.subTest(width=width):
                arrays = self.padded()
                for field in ('detector_raw_token_logits', 'detector_token_scores'):
                    if width == 257:
                        arrays[field] = np.concatenate((arrays[field], arrays[field][:, -1:]), axis=1)
                    else:
                        arrays[field] = arrays[field][:, :width]
                with self.assertRaisesRegex(ValueError, 'invalid raw S1'):
                    self.qualify(arrays, 'width'+str(width))

    def test_native_padding_keeps_query_selection_checks(self):
        arrays = self.padded()
        arrays['detector_selected_query_indices'] = np.array([], np.int64)
        with self.assertRaisesRegex(ValueError, 'native query selection'):
            self.qualify(arrays, 'foreign_query')

    def test_native_padding_with_no_selected_detections_remains_valid(self):
        self.row, self.arrays = recovery_fixture.synthetic_row(
            self.fixture.root/'zero', self.request, zero=True)
        self.assertTrue(self.qualify(self.padded(), 'zero-native'))

    def test_compact_active_caption_fixture_remains_valid(self):
        self.assertTrue(self.qualify(self.arrays, 'compact'))


if __name__ == '__main__':
    unittest.main()
