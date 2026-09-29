"""Hand-calculated Plan 031 neighbor scores and public result diagnostics."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import stages
from vipe_benchmark.files import file_record
from vipe_benchmark.neighbors import rank


class NeighborContractTests(unittest.TestCase):
    def test_n0_n1_hand_calculated_order_and_physical_id_ties(self):
        tracks = {10: {1, 2, 3, 4}, 8: {1, 2, 3, 5, 6, 7},
                  2: {1, 2, 3, 8, 9, 10}, 3: {1, 2}, 4: set()}
        # Counts: 3, 3, 2, 0. Jaccard: 3/7, 3/7, 2/4, 0.
        self.assertEqual(rank('N0', 10, tracks, training=list(tracks))['neighbors'], [2, 8, 3])
        self.assertEqual(rank('N1', 10, tracks, training=list(tracks))['neighbors'], [3, 2, 8])
        self.assertEqual(rank('N1', 10, tracks, training=list(tracks))['zero_support_cameras'], [4])

    def test_n2_full_tuple_recomputed_after_each_choice(self):
        tracks = {1: {1, 2, 3, 4}, 2: {1, 2}, 3: {2, 3},
                  4: {4}, 5: {1, 2, 3, 4}}
        supports = {
            2: dict(points={1, 2}, reference_cells={(0, 0), (1, 0)}, candidate_cells={(0, 0)}, median_sin=.5),
            3: dict(points={2, 3}, reference_cells={(0, 0), (1, 0)}, candidate_cells={(0, 0), (1, 0)}, median_sin=.4),
            4: dict(points={4}, reference_cells={(2, 0)}, candidate_cells={(0, 0)}, median_sin=.9),
            5: dict(points={1, 2, 3, 4}, reference_cells={(0, 0)}, candidate_cells={(0, 0)}, median_sin=.99),
        }
        with patch('vipe_benchmark.neighbors.eligible_support', side_effect=lambda ref, other, *args: supports[other]):
            result = rank('N2', 1, tracks, training=list(tracks))
        self.assertEqual(result['neighbors'], [3, 4, 5])
        scores = [{row['camera']: row['score'] for row in round_rows} for round_rows in result['rounds']]
        self.assertEqual(scores[0][3], [2, 2, 2, .4, .5, 2, -3])
        self.assertEqual(scores[1][4], [1, 1, 1, .9, .25, 1, -4])
        self.assertEqual(scores[2][5], [0, 1, 1, .99, 1., 4, -5])
        self.assertEqual(result['covered_point_ids'], [1, 2, 3, 4])

    def test_n2_equal_geometry_uses_jaccard_raw_count_then_id(self):
        tracks = {1: set(range(1, 7)), 2: {1, 2}, 3: {1, 2, 3, 7, 8, 9},
                  4: {1, 2, 3, 10, 11, 12}, 5: {1}}
        equal_geometry = dict(points={1}, reference_cells={(0, 0)},
                              candidate_cells={(0, 0)}, median_sin=.5)
        with patch('vipe_benchmark.neighbors.eligible_support', return_value=equal_geometry):
            result = rank('N2', 1, tracks, training=list(tracks))
        # Cameras 2/3/4 have J=1/3; count 3 beats count 2, then ID 3 beats 4.
        self.assertEqual(result['neighbors'], [3, 4, 2])
        self.assertEqual(result['rounds'][0][0]['score'], [1, 1, 1, .5, round(1/3, 12), 3, -3])

    def test_public_request_result_records_zero_and_geometric_failures(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            footprint = root / 'valid.npy'
            np.save(footprint, np.ones((540, 960), bool))
            K = [[100., 0., 480.], [0., 100., 270.], [0., 0., 1.]]
            cameras = {str(i): dict(K=K, R=np.eye(3).tolist(), t=[-x, 0., 0.], center=[x, 0., 0.])
                       for i, x in [(1, 0.), (2, 1.), (3, 0.), (4, 2.)]}
            scene = dict(cameras=cameras, tracks={'1': [1, 2], '2': [1, 2], '3': [1], '4': []},
                         points={'1': [0., 0., 10.], '2': [1., 0., 10.]},
                         footprints={str(i): file_record(footprint) for i in range(1, 5)})
            map_path = root / 'map.json'
            map_path.write_text(json.dumps(scene))
            inputs_path = root / 'inputs.json'
            inputs_path.write_text(json.dumps({'map': file_record(map_path)}))
            config = {'held_out_cameras': [c for c in range(34) if c not in range(1, 5)]}
            for method in ('N0', 'N2'):
                output = root / method
                stages.neighbors({'component': method, 'inputs': file_record(inputs_path)}, output, config)
                result = json.loads((output / 'result.json').read_text())
                reference = next(r for r in result['records'] if r['reference'] == 1)
                self.assertEqual(reference['status'], 'blocked')
                self.assertEqual(reference['neighbors'], [])
                self.assertIn('fewer than three', reference['reason'])
                self.assertEqual(reference['zero_support_cameras'], [4])
                self.assertEqual(reference['ineligible_geometry_cameras'], [3] if method == 'N2' else [])
                self.assertFalse(result['all_references_have_three_neighbors'])


if __name__ == '__main__':
    unittest.main()
