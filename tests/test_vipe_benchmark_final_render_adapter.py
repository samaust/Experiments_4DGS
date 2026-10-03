"""CPU checks at the QF initializer-to-native-model input boundary."""
import copy
import importlib
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.final_render_contract import initializer_arrays_hash
from vipe_benchmark.final_render_adapter import prepare_model_input, validate_model_input


class NativeInputTests(unittest.TestCase):
    def setUp(self):
        self.base = importlib.import_module('test_vipe_benchmark_final_render_contract').ContractTests()
        self.base.setUp()
        self.addCleanup(self.base.tearDown)
        self.request = copy.deepcopy(self.base.request)
        self.arrays = dict(positions=np.array([[1., 2., 3.], [4., 5., 6.]], np.float32),
            colors=np.full((2, 3), .5, np.float32), velocities=np.array([[0., 0., 0.], [1., 2., 3.]], np.float32),
            times=np.array([[0.], [.1]], np.float32), durations=np.full((2, 1), .2, np.float32),
            region=np.array([0, 1], np.int32), velocity_valid=np.array([False, True]))
        self.receipt = dict(self.request['initializer_contract'], arm='QF-B',
            composition=self.request['compositions']['QF-B'], arrays_sha256=initializer_arrays_hash(self.arrays),
            scene_manifest=self.request['bindings']['scene_manifest'],
            prerequisites={name:self.request['bindings'][name] for name in ('S2','D4_fit','D4_check','M0','N0')})

    def test_native_fields_preserve_units_and_sidecars_without_execution_authority(self):
        data, receipt = prepare_model_input(self.request, 'QF-B', self.receipt, self.arrays)
        self.assertEqual(set(data), {'positions','colors','velocities','times','durations'})
        np.testing.assert_array_equal(data['velocities'], [[0.,0.,0.],[1.,2.,3.]])
        np.testing.assert_array_equal(data['times'], np.array([[0.],[.1]],np.float32))
        self.assertEqual(receipt['native_array_bytes'], 88)
        self.assertEqual(receipt['sidecar_array_bytes'], 10)
        self.assertEqual(receipt['point_count'], 2)
        self.assertFalse(receipt['execution_authorized'])
        self.assertFalse(receipt['native_adapter_qualified'])
        self.assertEqual(receipt['initializer_receipt'], self.receipt)
        self.arrays['positions'][0,0] = 99
        self.assertEqual(data['positions'][0,0], 1.)

    def test_changed_arrays_and_wrong_arm_are_rejected_before_conversion(self):
        changed = {name:value.copy() for name,value in self.arrays.items()}
        changed['positions'][0,0] = 7
        with self.assertRaisesRegex(ValueError, 'arrays differ'):
            prepare_model_input(self.request, 'QF-B', self.receipt, changed)
        with self.assertRaisesRegex(ValueError, 'isolation'):
            prepare_model_input(self.request, 'QF-M1', self.receipt, self.arrays)

    def test_extra_fields_invalid_units_and_unknown_contract_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'exact native'):
            prepare_model_input(self.request, 'QF-B', self.receipt, dict(self.arrays, authorization=True))
        receipt = copy.deepcopy(self.receipt)
        receipt['velocity_units'] = 'metres/second'
        with self.assertRaisesRegex(ValueError, 'units'):
            prepare_model_input(self.request, 'QF-B', receipt, self.arrays)
        request = copy.deepcopy(self.request)
        request['schema'] = 'unknown/v1'
        with self.assertRaisesRegex(ValueError, 'request schema'):
            prepare_model_input(request, 'QF-B', self.receipt, self.arrays)

    def test_converter_does_not_modify_caller_arrays_or_provenance(self):
        request = copy.deepcopy(self.request)
        receipt = copy.deepcopy(self.receipt)
        data, result = prepare_model_input(self.request, 'QF-B', self.receipt, self.arrays)
        data['velocities'][1,0] = 99
        result['initializer_receipt']['composition']['depth'] = 'changed'
        self.assertEqual(self.arrays['velocities'][1,0], 1.)
        self.assertEqual(self.request, request)
        self.assertEqual(self.receipt, receipt)
        self.assertTrue(all(array.flags.c_contiguous for array in data.values()))

    def test_nonfinite_and_mutated_prepared_payload_fail_integrity_check(self):
        data, receipt = prepare_model_input(self.request, 'QF-B', self.receipt, self.arrays)
        self.assertEqual(validate_model_input(data, receipt), receipt['native_arrays_sha256'])
        data['positions'][0,0] = 7.
        with self.assertRaisesRegex(ValueError, 'arrays changed'):
            validate_model_input(data, receipt)
        data['positions'][0,0] = np.nan
        with self.assertRaises(ValueError):
            validate_model_input(data, receipt)
        self.arrays['velocities'][1,0] = np.inf
        with self.assertRaises(ValueError):
            prepare_model_input(self.request, 'QF-B', self.receipt, self.arrays)

    def test_normalization_substitution_is_rejected(self):
        receipt = copy.deepcopy(self.receipt)
        receipt['normalization']['radius'] = 2.
        with self.assertRaisesRegex(ValueError, 'transform'):
            prepare_model_input(self.request, 'QF-B', receipt, self.arrays)

    def test_extended_depth_uses_new_choice_validator_and_retains_rotation(self):
        fixture = importlib.import_module('test_vipe_benchmark_extended_final_render_contract').AdmissionTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        request = fixture.request
        names = ('S2','D_fit','D_check','depth_decision','M0','N0')
        receipt = dict(request['initializer_contract'], arm='QF-B',
            composition=request['compositions']['QF-B'], arrays_sha256=initializer_arrays_hash(self.arrays),
            scene_manifest=request['bindings']['scene_manifest'],
            prerequisites={name:request['bindings'][name] for name in names})
        data, result = prepare_model_input(request, 'QF-B', receipt, self.arrays)
        self.assertEqual(result['composition']['depth'], 'D5')
        self.assertEqual(result['initializer_receipt']['normalization'],
            {'transform':[[0,-2,0,1],[2,0,0,2],[0,0,2,3],[0,0,0,1]]})
        self.assertEqual(result['initializer_receipt']['prerequisites']['depth_decision'],
            request['bindings']['depth_decision'])
        self.assertFalse(result['execution_authorized'])
        self.assertEqual(validate_model_input(data, result), result['native_arrays_sha256'])
        altered = copy.deepcopy(receipt)
        altered['prerequisites']['D4_fit'] = altered['prerequisites'].pop('D_fit')
        with self.assertRaisesRegex(ValueError, 'lineage'):
            prepare_model_input(request, 'QF-B', altered, self.arrays)


if __name__ == '__main__':
    unittest.main()
