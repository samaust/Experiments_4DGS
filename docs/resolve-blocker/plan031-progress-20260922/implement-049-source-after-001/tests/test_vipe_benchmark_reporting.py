from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import reporting
from vipe_benchmark.config import load, training_cameras
from vipe_benchmark.files import file_record, read_json, write_json


def score(candidate='S1', baseline='S0', difference=.2, interval=(.1, .3)):
    return dict(estimates={baseline: .5, candidate: .5+difference},
        interval_95={baseline: [.4, .6], candidate: [.4+difference, .6+difference]},
        per_camera={baseline: {'1': .4, '6': .6, '33': None},
                    candidate: {'1': .4+difference, '6': .6+difference, '33': None}},
        per_camera_extrema={baseline: [.4, .6], candidate: [.4+difference, .6+difference]},
        undefined_cameras={baseline: [33], candidate: [33]},
        differences={candidate+'-'+baseline: dict(estimate=difference, interval_95=list(interval), defined_resamples=10000)})


def comparison(field='dice', **kwargs):
    return dict(status='complete', scores={field: score(**kwargs)}, ineligible={},
                evidence_kinds=['model-assisted-proxy'])


class PairedInterpretationTests(unittest.TestCase):
    def test_saved_direction_intervals_and_unknowns_cannot_become_global_winners(self):
        comparisons = {
            'calibration/fit/all/pixel/person': comparison(),
            'calibration/selection/all/pixel/basketball': comparison(difference=-.2, interval=(-.3, -.1)),
            'reconstruction/reconstruction/all/boundary/person': comparison(field='f1', interval=(-.1, .3)),
            'calibration/selection/tiny_ball/tiny_ball/basketball': comparison(field='center_error_pixels', difference=-.1, interval=(-.2, -.01)),
            'calibration/selection/all/fraction/predicted_static_area': comparison(field='fraction'),
            'calibration/selection/all/pixel/player': dict(comparison(), ineligible={'S1': {'reason': 'unknown role'}}),
            'calibration/selection/shadows': dict(status='unverified', scores={})}
        rows = reporting.paired_rows(comparisons, {'S1': 'S0'}, {'path': 'fixture'}, scope='masks')
        result = {(r['metric'], r['field']): r for r in rows}
        self.assertEqual(result['person', 'dice']['conclusion'], 'improvement')
        self.assertEqual(result['basketball', 'dice']['conclusion'], 'regression')
        self.assertEqual(result['person', 'f1']['conclusion'], 'inconclusive')
        self.assertEqual(result['basketball', 'center_error_pixels']['conclusion'], 'improvement')
        self.assertEqual(result['predicted_static_area', 'fraction']['conclusion'], 'increase')
        self.assertEqual(result['player', 'dice']['conclusion'], 'unverified')
        self.assertIsNone(result['player', 'dice']['estimate'])
        self.assertEqual(result['person', 'dice']['undefined_cameras']['S1'], [33])

    def test_zero_endpoint_is_inconclusive_and_reverse_difference_flips_both_bounds(self):
        original = comparison(candidate='G-S0', baseline='G-S1', difference=-.2, interval=(-.3, -.1), field='fraction')
        rows = reporting.paired_rows({'reconstruction/reconstruction/all/fraction/accepted_person': original},
                                     {'G-S1': 'G-S0'}, {'path': 'fixture'}, scope='isolated-geometry')
        self.assertEqual(rows[0]['interval_95'], [.1, .3])
        self.assertEqual(rows[0]['conclusion'], 'increase')
        original = comparison(interval=(0., .3))
        rows = reporting.paired_rows({'calibration/fit/all/pixel/person': original}, {'S1': 'S0'}, {}, scope='masks')
        self.assertEqual(rows[0]['conclusion'], 'inconclusive')


class FrozenReportTests(unittest.TestCase):
    def fixture(self, root):
        def save(name, document):
            path = root/(name+'.json')
            write_json(path, document)
            return file_record(path)
        config = load()
        raw = save('raw-counts', dict(rows=[]))
        static = save('final-static', dict(status='complete', expected_rows=9450, generated_rows=12, unavailable_rows=9438))
        seg_control = save('segmentation-control', dict(status='complete', rows=[dict(status='complete',
            instance_id_pixel_disagreements=4, semantic_union_disagreements=dict(person=2, basketball=1),
            intermediate_arrays=dict(detector_rgb=dict(status='complete', max_abs_difference=1.25),
                detector_raw_token_logits=dict(status='unverified'), detector_selected_boxes_xyxy=dict(status='recorded')))]))
        mask_comparisons = {domain+'/all/pixel/person': comparison() for domain in reporting.DOMAINS}
        mask_comparisons.update({
            'calibration/selection/all/pixel/basketball': comparison(difference=-.2, interval=(-.3, -.1)),
            'calibration/selection/all/boundary/semantic_foreground': comparison(field='f1', interval=(-.1, .3)),
            'calibration/selection/all/pixel/usable_static': dict(status='unverified', scores={}, ineligible={'S1': dict(reason='unknown independent static truth')}),
            'calibration/selection/shadows': dict(status='unverified', scores={})})
        masks = save('masks', dict(status='complete', comparisons=mask_comparisons, human_ground_truth=False,
            evidence_kind='model-assisted-proxy', generated_primary_mask_rows=1350, scored_unique_annotation_images=1,
            raw_counts=raw, segmentation_control=seg_control, final_static_masks=static))
        classes = {region: dict(attempted=10, accepted=8, velocity_valid=6) for region in ('static', 'person', 'ball')}
        summary = dict(expected_contexts=64, complete_contexts=64, full_image_matches=192, crop_matches=0,
            reciprocal_directed_edges=4, reciprocal_pairs=2, foreground_reference_cells=7.5,
            synchronized_cuda_seconds=4.5, neighbor_failures=[], classes=classes)
        edges = []
        for i in range(2):
            edges.append(dict(classes={region: dict(supporting_camera_histogram={'0': 0, '3': 2, '4': 2},
                parallax_degrees=dict(min=1.+i, median=3.+i, p95=9.+i)) for region in classes},
                raw_normalized_overlap=dict(shared=100+i*100, jaccard=.1+i*.2),
                sampling=dict(shortage=2), stages=dict(numerical=dict(rejected=0), parallax=dict(rejected=1))))
        contexts = [dict(status='complete', classes={region: dict(marginal_coverage=[dict(new_cells=k) for k in (10, 2, 0)]) for region in classes})]
        raw_geometry = save('G-S0', dict(status='complete', job_id='G-S0', summary=summary, rows=edges, contexts=contexts,
            wall_seconds=12., input_bytes_unique=1024, output_bytes_before_result=4096,
            resources=dict(peak_allocated_bytes=2**30, peak_reserved_bytes=2*2**30, peak_observed_device_bytes=123)))
        geometry = save('geometry', dict(slots={'G-S0': dict(status='complete', summary=summary, result=raw_geometry),
            'G-S1': dict(status='unverified', reason='runtime unavailable')}, comparisons={
                'reconstruction/reconstruction/all/fraction/accepted_person': comparison(
                    candidate='G-S0', baseline='G-S1', field='fraction', difference=-.1, interval=(-.2, .1))}))
        scale_fit = save('D0-fit', dict(status='passed', role='fit', scale=2., diagnostic_window_scale=2.,
            bootstrap_95_interval=[1.9, 2.1], blockers=[], cameras=[dict(camera_id=c, points=50) for c in training_cameras(config)]))
        scale_check = save('D0-check', dict(status='blocked', role='selection', scale=2., diagnostic_window_scale=2.4,
            bootstrap_95_interval=[2.3, 2.5], blockers=['frozen scale disagreement'],
            cameras=[dict(camera_id=c, points=45) for c in training_cameras(config)]))
        selected = {'C0': ['S0', 'D0', 'M0', 'N0'], 'C1': ['S2', 'D1', 'M0', 'N1'],
                    'C2': ['S4', 'D2', 'M0', 'N1'], 'C3': ['S1', 'D1', 'M0', 'N0']}
        combinations = {slot: dict(components=components, status='blocked', reasons=['specific prerequisite unavailable'])
                        for slot, components in selected.items()}
        finalists = save('finalists', dict(status='frozen', mask_metrics=masks,
            finalists=dict(S=dict(selected='S2', status='unverified', reason='authorized proxy baseline default'),
                M=dict(selected='M0', status='unverified', reason='unknown static truth'), N=dict(selected='N1', status='complete')),
            combined=combinations, depth_gates=dict(D0=dict(fit='passed', check='blocked', fit_record=scale_fit,
                                                          check_record=scale_check, reasons=[]))))
        depth_control = save('depth-control', dict(fit=dict(status='complete', rows=[
            dict(status='complete', mean_abs_depth=.5, camera_scale_ratio_difference=.1,
                 camera_scale_ratio_relative_difference=.05, sparse_validity_disagreement=2),
            dict(status='complete', mean_abs_depth=.8, camera_scale_ratio_difference=-.2,
                 camera_scale_ratio_relative_difference=-.1, sparse_validity_disagreement=4),
            dict(status='unverified', reason='camera missing')]), check=dict(status='unverified')))
        aggregate = save('aggregate', dict(status='complete', mask_metrics=masks, finalists=finalists,
            combined=combinations, isolated_geometry_metrics=geometry, depth_control=depth_control, repeats={
                'R-S': dict(status='complete', repeat=[dict(identity=dict(camera=1, frame=20), differing_pixels=5)]),
                'R-D': dict(status='complete', repeat=dict(mean_abs_depth=.03, validity_disagreement=2,
                    camera_scale_ratio_difference=.01, camera_scale_ratio_relative_difference=.005)),
                'R-G': dict(status='complete', repeat=dict(edges=[dict(other=2, original_accepted=8, repeated_accepted=7,
                    accepted_count_difference=-1, acceptance_disagreements=1, same_sampled_reference_coordinates=True)]))}))
        guarded = save('guarded', dict(status='complete', runtime=dict(isolation=dict(import_guard=True, subprocesses=False))))
        unguarded = save('unguarded', dict(status='complete', runtime=dict(isolation=dict(import_guard=False, subprocesses=False))))
        license_evidence = save('license', dict(status='unverified', reasons=['missing weight closure']))
        return dict(inputs=save('inputs', {}), annotations=save('annotations', dict(
            schema='vipe-benchmark-automated-annotations/v1', status='reviewed-proxy', human_ground_truth=False,
            evidence_kind='model-assisted-proxy', images=[{}], pairs=[{}])), aggregate=aggregate,
            accounting=save('accounting', dict(jobs={'G-S0': dict(status='complete', elapsed_seconds=15., result=raw_geometry,
                peak=dict(device_bytes=3*2**30))}, consumption=dict(gpu=dict(attempts=1, elapsed_seconds=15., reserved_seconds=0.)))),
            components=save('components', dict(S1=dict(status='qualified', qualification_results=[guarded],
                commercial_permission='verified', non_agpl='unverified',
                license_evidence=dict(assessment=license_evidence, status='unverified', reasons=['missing weight closure'])),
                S2=dict(status='qualified', qualification_results=[unguarded]))),
            validation=save('validation', dict(status='passed')))

    def test_disposable_report_preserves_saved_results_missing_slots_and_distinct_claims(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request = self.fixture(root)
            with mock.patch('vipe_benchmark.aggregation.balanced_statistics', side_effect=AssertionError('report must not resample')), \
                    mock.patch('vipe_benchmark.aggregation.run', side_effect=AssertionError('report must not aggregate')):
                result = reporting.run(request, root/'output', load())
            text = Path(result['report']['path']).read_text()
            for expected in ('Incomplete matrix', 'C1 primary', 'S2 + D1 + M0 + N1', 'C2 commercial-use/non-AGPL preference',
                             'C3 fallback', '0.2 [0.1, 0.3]; improvement', '-0.2 [-0.3, -0.1]; regression',
                             '0.2 [-0.1, 0.3]; inconclusive', 'calibration/fit', 'calibration/selection',
                             'reconstruction/reconstruction', 'undefined 1', '12 / 9450 generated',
                             '4/2', '1/2/3', '1024/4096', 'frozen scale disagreement', '0.5–0.8',
                             'detector_raw_token_logits', 'accepted 8 → 7', 'pointwise acceptance disagreements 1',
                             'Human boundary accuracy', 'Physical accuracy: **unverified**'):
                self.assertIn(expected, text)
            self.assertFalse(result['comparison_fully_executed'])
            self.assertIn('S0-calibration', result['unavailable_or_failed_slots'])
            self.assertFalse(result['human_ground_truth'])
            self.assertEqual(result['dependency_removal']['S1']['status'], 'qualified')
            self.assertEqual(result['dependency_removal']['S2']['status'], 'unverified')
            copied = read_json(result['paired_comparisons']['path'])
            self.assertTrue(copied['no_rescoring'])
            self.assertTrue(any(r['conclusion'] == 'regression' for r in copied['rows']))
            self.assertIn('calibration/selection/all/pixel/usable_static', copied['unavailable_mask_groups'])
            detail = read_json(result['geometry_details']['path'])['slots']['G-S0']
            self.assertEqual(detail['person']['edge_parallax_ranges'], dict(min=[1., 2.], median=[3., 4.], p95=[9., 10.]))
            self.assertEqual(detail['person']['supporting_camera_histogram']['3'], 4)
            self.assertEqual(detail['person']['supporting_camera_histogram']['0'], 0)
            self.assertEqual(detail['person']['marginal_new_reference_cells_by_rank'], [10, 2, 0])
            self.assertEqual(detail['overlap']['shared'], [100, 200])
            self.assertEqual(detail['sampling_shortage'], 4)
            self.assertEqual(detail['rejections']['numerical'], 0)
            with self.assertRaises(FileExistsError):
                reporting.run(request, root/'output', load())

    def test_changed_nested_evidence_and_false_human_truth_are_rejected(self):
        for change in ('nested', 'human'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                request = self.fixture(root)
                if change == 'nested':
                    (root/'masks.json').write_text('{"status":"complete"}')
                    expected = 'changed file'
                else:
                    annotation = read_json(request['annotations']['path'])
                    annotation['human_ground_truth'] = True
                    write_json(root/'changed-annotations.json', annotation)
                    request['annotations'] = file_record(root/'changed-annotations.json')
                    expected = 'human ground truth'
                with self.assertRaisesRegex(ValueError, expected):
                    reporting.run(request, root/'output', load())
                self.assertFalse((root/'output/result.json').exists())


if __name__ == '__main__':
    unittest.main()
