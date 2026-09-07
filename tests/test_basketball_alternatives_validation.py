import json
import sys
import tempfile
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import basketball_alternatives_evaluate as evaluation
from basketball_audit import sha256


class ReservedValidationTests(unittest.TestCase):
    def test_static_track_filter_uses_measured_pixels_and_deduplicates_points(self):
        descriptors=np.array([[0.,0.],[100.,100.],[200.,200.]],np.float32)
        anchor=(descriptors,[11,22,33],np.array([[20.,20.],[40.,40.],[60.,60.]]))
        query=np.array([[0.,0.],[.1,.1],[100.,100.],[200.,200.]],np.float32)
        pixels=np.array([[21.,20.],[22.,20.],[100.,100.],[60.,62.]])
        matches=evaluation.temporal_correspondences(query,pixels,anchor)
        self.assertEqual(matches,[(0,11),(3,33)])
        # No camera or 3D parameters are accepted by the filter.
        self.assertEqual(len({pid for _,pid in matches}),len(matches))

    def test_final_evaluation_rejects_changed_map_and_second_consumption(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);cal=root/'calibration.json';cal.write_text('{}')
            frozen=root/'frozen-winner.json'
            record=dict(status='frozen',selection_passed=True,calibration_sha256=sha256(cal),
                        frozen_artifact_sha256={'map':'original'},
                        evaluation_adapter_sha256=sha256(evaluation.__file__))
            frozen.write_text(json.dumps(record))
            prepared=dict(frozen_winner_sha256=sha256(frozen))
            evaluation.validate_frozen(frozen,cal,prepared,{'map':'original'})
            with self.assertRaisesRegex(ValueError,'changed frozen map'):
                evaluation.validate_frozen(frozen,cal,prepared,{'map':'changed'})
            self.assertFalse((root/'validation-consumed.json').exists())
            evaluation.consume_validation(frozen,root/'result')
            with self.assertRaises(FileExistsError):
                evaluation.consume_validation(frozen,root/'second-result')


if __name__=='__main__':unittest.main()
