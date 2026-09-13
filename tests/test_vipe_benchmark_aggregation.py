from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import aggregation
from vipe_benchmark.access import Identity
from vipe_benchmark.files import file_record, read_json, write_json
from vipe_benchmark.metrics import paired_bootstrap, pixel_scores


def metadata(semantic='person', role='uncertain', **flags):
    return {'class': semantic, 'native_class': semantic, 'score': .9, 'role': role,
            'role_uncertain': role == 'uncertain', **flags}


def fixture():
    labels = np.zeros((12, 12), np.int32)
    labels[2:5, 2:5], labels[7:9, 8:10] = 1, 2
    valid = np.ones_like(labels, bool)
    layers = dict(instances=labels.copy(), valid=valid, ignored=np.zeros_like(valid), changing=np.zeros_like(valid))
    annotation = dict(identity=Identity('calibration', 1, 175).record(),
        instances={'1': metadata(role='player', occlusion=False, blur=False),
                   '2': metadata('basketball', tiny_ball=True)}, tags={}, static_feature_locations=[], static_feature_review=[],
        eligibility=dict(person_union=True, basketball=True, boundary='proxy-only', changing=False, static=False, roles=False, temporal=False))
    prediction = labels.copy()
    semantics = {'1': metadata(), '2': metadata('basketball')}
    return prediction, semantics, annotation, layers


class AnnotationAggregationTests(unittest.TestCase):
    def test_proxy_unknown_static_roles_and_temporal_never_become_truth(self):
        p, s, a, layers = fixture()
        rows, _ = aggregation.score_image(p, s, np.zeros_like(p, bool), a, layers, proxy=True)
        by_metric = {(r['kind'], r['metric']): r for r in rows}
        self.assertEqual(by_metric['pixel', 'person']['counts']['tp'], 9)
        self.assertEqual(by_metric['pixel', 'basketball']['counts']['tp'], 4)
        for key in [('pixel', 'usable_static'), ('pixel', 'changing'), ('pixel', 'player'),
                    ('fraction', 'foreground_leakage'), ('fraction', 'retained_static_features')]:
            self.assertEqual(by_metric[key]['status'], 'unverified')
            self.assertIsNone(by_metric[key]['counts'])
        temporal = aggregation.score_pair(dict(labels=p, semantics=s), dict(labels=p, semantics=s), a, a,
            [dict(first_id=1, second_id=1, eligible=False), dict(first_id=2, second_id=2, eligible=False)], layers, layers, proxy=True)
        self.assertTrue(all(r['status'] == 'unverified' for r in temporal))
        self.assertEqual(by_metric['boundary', 'semantic_foreground']['evidence_kind'], 'model-assisted-proxy')

    def test_visible_tiny_ball_miss_and_negative_proxy_false_positives_count(self):
        p, s, a, layers = fixture()
        p[p == 2] = 0
        del s['2']
        rows, _ = aggregation.score_image(p, s, np.zeros_like(p, bool), a, layers, proxy=True)
        tiny = next(r['counts'] for r in rows if r['kind'] == 'tiny_ball')
        self.assertEqual((tiny['visible'], tiny['detected']), (1, 0))
        layers['instances'][layers['instances'] == 2] = 0
        del a['instances']['2']
        p[0, 0] = 2
        s['2'] = metadata('basketball')
        rows, _ = aggregation.score_image(p, s, np.zeros_like(p, bool), a, layers, proxy=True)
        ball = next(r for r in rows if r['kind'] == 'pixel' and r['metric'] == 'basketball')
        self.assertEqual(ball['counts']['negative_images'], 1)
        self.assertEqual(ball['counts']['negative_false_positive_pixels'], 1)
        self.assertEqual(ball['evidence_kind'], 'model-assisted-proxy')

    def test_roles_ignore_other_people_keep_background_and_precision_bounds(self):
        p, s, a, layers = fixture()
        layers['instances'][10, 10] = 3
        a['instances']['3'] = metadata(role='other-person')
        p[0, 0] = 3  # Unmatched person prediction has unknown role.
        s['3'] = metadata()
        rows, _ = aggregation.score_image(p, s, np.zeros_like(p, bool), a, layers)
        by_metric = {(r['kind'], r['metric']): r for r in rows}
        counts = by_metric['pixel', 'player']['counts']
        self.assertEqual((counts['tp'], counts['fp'], counts['fn']), (9, 1, 0))
        counts = by_metric['role_instance', 'player']['counts']
        self.assertEqual((counts['matches'], counts['unmatched_predictions']), (1, 1))
        scores = aggregation.balanced_statistics({'S1': {(1, 175): counts}}, 'role_instance', resamples=20)
        self.assertEqual(scores['scores']['precision_lower']['estimates']['S1'], .5)

    def test_reviewed_static_feature_retention_does_not_use_uncertain_as_static(self):
        p, s, a, layers = fixture()
        a['static_feature_locations'] = [dict(index=0, uv=[0, 0]), dict(index=1, uv=[2, 2]), dict(index=2, uv=[1, 1])]
        a['static_feature_review'] = [dict(index=0, suitable=True), dict(index=1, suitable=True), dict(index=2, suitable='uncertain')]
        rows, _ = aggregation.score_image(p, s, np.zeros_like(p, bool), a, layers, proxy=True, sift=np.array([[0, 0], [2, 2], [1, 1]]))
        counts = next(r['counts'] for r in rows if r['metric'] == 'retained_static_features')
        self.assertEqual(counts, dict(numerator=1, denominator=2))


class FinalStaticAssemblyTests(unittest.TestCase):
    def fixture(self, root):
        identities = [Identity('calibration', 2, 100), Identity('reconstruction', 1, 20, 20),
                      Identity('reconstruction', 1, 21, 20)]
        valid = np.ones((540, 960), bool)
        valid[0] = False
        np.save(root/'valid.npy', valid, allow_pickle=False)
        footprint = file_record(root/'valid.npy')
        sources, predictions, common_rows = [], {}, []
        for n, identity in enumerate(identities):
            image = root/f'image-{n}.bin'
            image.write_bytes(bytes([n]))  # The assembler consumes frozen RGB identity, not RGB pixels.
            source = dict(identity=Identity(identity.branch, identity.camera, identity.frame).record(),
                          rgb=file_record(image), valid=footprint, K=np.eye(3).tolist(), grid=identity.branch)
            sources.append(source)
            labels = np.zeros(valid.shape, np.int32)
            labels[~valid] = -1
            labels[10, 10+n] = 1
            np.save(root/f'instances-{n}.npy', labels, allow_pickle=False)
            row = dict(identity=identity.record(), source_rgb_sha256=source['rgb']['sha256'],
                       K=source['K'], grid=source['grid'], valid=footprint)
            common_rows.append(row)
            predictions[identity.key()] = dict(row, instances=file_record(root/f'instances-{n}.npy'),
                                               semantics={'1': metadata()})
        inputs = dict(rgb=sources)
        write_json(root/'inputs.json', inputs)
        request = dict(inputs=file_record(root/'inputs.json'), segmentation={}, motion={})
        segmentation = {f'S{i}': dict(predictions) for i in range(5)}
        for method, indexed in segmentation.items():
            request['segmentation'][method] = {}
            for branch in ('calibration', 'reconstruction'):
                path = root/f'{method}-{branch}.json'
                write_json(path, dict(status='complete', component=method,
                    rows=[r for r in indexed.values() if r['identity']['branch'] == branch]))
                request['segmentation'][method][branch] = file_record(path)
        motion = {}
        for m in range(3):
            method = f'M{m}'
            motion[method] = {}
            for n, (identity, common) in enumerate(zip(identities, common_rows)):
                change = np.zeros(valid.shape, bool)
                coordinate = 20 + n*10 + m*70
                change[coordinate, coordinate] = True
                path = root/f'{method}-{n}.npy'
                np.save(path, change, allow_pickle=False)
                motion[method][identity.key()] = dict(common, changing=file_record(path))
            path = root/f'{method}.json'
            write_json(path, dict(status='complete', component=method, rows=list(motion[method].values())))
            request['motion'][method] = file_record(path)
        return identities, request, inputs, segmentation, motion

    def assemble(self, root, identities, request, inputs, segmentation, motion):
        from vipe_benchmark.config import load
        with mock.patch.object(aggregation, 'output_identities',
                side_effect=lambda config, branch: [i for i in identities if i.branch == branch]):
            return aggregation.assemble_final_static(request, root/'output', load(), inputs, segmentation, motion)

    def test_all_outputs_have_exact_sources_pair_union_and_single_S0_M0_assembly(self):
        import cv2
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identities, request, inputs, segmentation, motion = self.fixture(root)
            result = self.assemble(root, identities, request, inputs, segmentation, motion)
            self.assertEqual((result['expected_rows'], result['generated_rows'], result['unavailable_rows']), (21, 21, 0))
            self.assertEqual(result['availability'], 'complete')
            self.assertEqual(result['aliases'], {'M0': 'S0'})
            self.assertTrue(result['annotation_independent'])
            self.assertFalse(result['human_ground_truth'])
            self.assertEqual(len(list((root/'output/final-static').glob('**/*.png'))), 21)
            self.assertFalse((root/'output/final-static/M0').exists())
            rows = {(r['method'], Identity(**r['identity']).key()): r for r in result['rows']}
            first = rows['S0', identities[1].key()]
            mask = cv2.imread(first['final_static']['path'], cv2.IMREAD_UNCHANGED)
            self.assertEqual([int(mask[y, x]) for y, x in [(0, 0), (10, 11), (30, 30), (40, 40), (100, 100)]],
                             [0, 0, 0, 0, 255])
            varied = rows['M1', identities[1].key()]
            mask = cv2.imread(varied['final_static']['path'], cv2.IMREAD_UNCHANGED)
            self.assertEqual([int(mask[y, x]) for y, x in [(30, 30), (100, 100), (110, 110)]], [255, 0, 0])
            self.assertEqual(first['segmentation']['result'], request['segmentation']['S0']['reconstruction'])
            self.assertEqual(first['motion']['result'], request['motion']['M0'])
            self.assertEqual([r['identity']['frame'] for r in first['motion']['rows']], [20, 21])
            self.assertEqual(first['motion']['rows'][1]['changing'], motion['M0'][identities[2].key()]['changing'])
            self.assertEqual(read_json(root/'output/final-static-masks.json')['generated_rows'], 21)

    def test_missing_pair_member_never_becomes_static_background(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            identities, request, inputs, segmentation, motion = self.fixture(root)
            del motion['M0'][identities[2].key()]
            result = self.assemble(root, identities, request, inputs, segmentation, motion)
            self.assertEqual((result['generated_rows'], result['unavailable_rows']), (11, 10))
            self.assertEqual(result['availability'], 'partial')
            unavailable = [r for r in result['rows'] if r['method'] == 'S0' and r['identity']['branch'] == 'reconstruction']
            self.assertEqual(len(unavailable), 2)
            self.assertTrue(all(r['status'] == 'unverified' and 'final_static' not in r for r in unavailable))

    def test_motion_source_and_grid_cannot_be_changed_by_pair_union(self):
        for field, value in [('source_rgb_sha256', 'different-image'), ('grid', 'different-grid')]:
            with self.subTest(field=field), tempfile.TemporaryDirectory() as temporary:
                root = Path(temporary)
                identities, request, inputs, segmentation, motion = self.fixture(root)
                motion['M0'][identities[2].key()][field] = value
                with self.assertRaisesRegex(ValueError, 'source RGB/valid footprint|wrong branch/grid/intrinsics'):
                    self.assemble(root, identities, request, inputs, segmentation, motion)


class StatisticalTests(unittest.TestCase):
    def test_boundary_complete_miss_is_zero_and_empty_empty_is_undefined(self):
        raw = dict(predicted_boundary=0, truth_boundary=20, matched_prediction=0, matched_truth=0)
        result = aggregation.balanced_statistics({'S1': {(1, 175): raw}}, 'boundary', resamples=20)
        self.assertEqual(result['scores']['f1']['estimates']['S1'], 0.)
        raw['truth_boundary'] = 0
        result = aggregation.balanced_statistics({'S1': {(1, 175): raw}}, 'boundary', resamples=20)
        self.assertIsNone(result['scores']['f1']['estimates']['S1'])

    def test_vectorized_bootstrap_matches_independent_existing_algorithm(self):
        a = {(1, 20): dict(tp=90, fp=0, fn=0, negative_images=0, negative_false_positive_pixels=0),
             (1, 45): dict(tp=3, fp=1, fn=2, negative_images=0, negative_false_positive_pixels=0),
             (6, 20): dict(tp=1, fp=0, fn=9, negative_images=0, negative_false_positive_pixels=0)}
        b = {k: dict(v) for k, v in a.items()}
        b[6, 20].update(tp=5, fn=5)
        reference = paired_bootstrap({'A': a, 'B': b}, lambda c: pixel_scores(c)['recall'], resamples=10000)
        measured = aggregation.balanced_statistics({'A': a, 'B': b}, 'pixel')['scores']['recall']
        self.assertEqual(measured['estimates'], reference['estimates'])
        self.assertEqual(measured['differences'], reference['differences'])
        self.assertAlmostEqual(measured['estimates']['A'], ((93/95)+.1)/2)

    def test_crossing_contexts_remain_one_temporal_group_and_missing_method_explicit(self):
        rows = []
        for method in ('S0', 'S1'):
            for start, frame in [(20, 20), (20, 21), (21, 21), (21, 22), (25, 25), (25, 26)]:
                rows.append(dict(method=method, identity=Identity('reconstruction', 1, frame, start).record(),
                    kind='fraction', metric='test', counts=dict(numerator=1, denominator=2), status='complete',
                    strata=['all'], evidence_kind='model-assisted-proxy'))
        # The full manifest connects 22 to 25 through 23/24 as required.
        for method in ('S0', 'S1'):
            for start in (22, 23, 24):
                rows.append(dict(rows[0], method=method, identity=Identity('reconstruction', 1, start+1, start).record()))
        report = aggregation.aggregate_rows(rows, ['S0', 'S1', 'S2'], resamples=20)
        key = 'reconstruction/reconstruction/all/fraction/test'
        groups = report[key]['raw_by_group']['S0']
        self.assertEqual([r['temporal_group'] for r in groups], [20])
        self.assertIn('S2', report[key]['ineligible'])
        self.assertEqual(report['reconstruction/reconstruction/occlusion']['status'], 'unverified')

    def test_unavailable_truth_terms_cannot_rank_as_zeros(self):
        identity = Identity('calibration', 1, 175).record()
        base = dict(identity=identity, kind='fraction', metric='foreground_leakage', strata=['all'], evidence_kind='model-assisted-proxy')
        rows = [dict(base, method='S1', counts=None, status='unverified', reason='unknown changing/static layer')]
        report = aggregation.aggregate_rows(rows, ['S1'], resamples=20)
        self.assertEqual(report['calibration/selection/all/fraction/foreground_leakage']['scores'], {})

    def test_missing_or_duplicate_paired_groups_rejected(self):
        with self.assertRaises(ValueError):
            aggregation.balanced_statistics({'A': {(1, 20): dict(numerator=1, denominator=1)},
                'B': {(2, 20): dict(numerator=1, denominator=1)}}, 'fraction', resamples=20)
        row = dict(method='S1', identity=Identity('calibration', 1, 175).record(), kind='fraction', metric='test',
                   counts=dict(numerator=1, denominator=1), status='complete', strata=['all'], evidence_kind='reviewed-annotation')
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            aggregation.aggregate_rows([row, row], ['S1'], resamples=20)


class SelectionCheckpointTests(unittest.TestCase):
    def test_authorized_proxy_defaults_freeze_and_missing_depth_never_substitutes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            policy = dict(selection=dict(segmentation='original tuple where all required proxy terms are defined on common frozen domain; otherwise explicit S2 unverified baseline default',
                motion='M0 predeclared baseline default if independent changing/static evidence is unavailable, never labeled a measured winner'))
            write_json(root/'policy.json', policy)
            write_json(root/'masks.json', dict(status='complete', comparisons={}, evidence_kind='model-assisted-proxy', amendment=file_record(root/'policy.json')))
            request = dict(mask_metrics=file_record(root/'masks.json'))
            result = aggregation.finalist_stage(request, root, {})
            self.assertEqual((result['finalists']['S']['selected'], result['finalists']['S']['status']), ('S2', 'unverified'))
            self.assertEqual((result['finalists']['M']['selected'], result['finalists']['M']['status']), ('M0', 'unverified'))
            self.assertIsNone(result['finalists']['N']['selected'])
            self.assertEqual(result['combined']['C1']['components'][1], 'D1')
            self.assertEqual(result['combined']['C2']['components'][1], 'D2')
            self.assertTrue(all(r['status'] == 'blocked' for r in result['combined'].values()))
            with self.assertRaises(FileExistsError):
                aggregation.finalist_stage(request, root, {})

    def test_hash_bound_scale_check_cannot_use_other_fit(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            from vipe_benchmark.config import ROOT
            from vipe_benchmark.files import digest
            common = dict(status='passed', scale_protocol_sha256=digest(ROOT/'configs/basketball-rev2/scale.json'),
                          provenance=dict(component='D1', component_sha256='candidate'))
            write_json(root/'fit.json', dict(common, role='fit'))
            fit = file_record(root/'fit.json')
            write_json(root/'check.json', dict(common, role='selection', frozen_fit=dict(fit, sha256='stale')))
            result = aggregation.scale_status(dict(fit=fit, check=file_record(root/'check.json')), 'D1')
            self.assertFalse(result['eligible'])
            self.assertEqual(result['fit'], 'passed')
            self.assertEqual(result['check'], 'unverified')
            result = aggregation.scale_status(dict(fit=fit), 'D2')
            self.assertEqual(result['fit'], 'unverified')

    def test_depth_repeat_reports_frozen_sparse_ratios_without_refitting(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid = np.ones((12, 12), bool)
            np.savez(root/'a.npz', depth=np.full(valid.shape, 4., np.float32), valid=valid)
            other_valid = valid.copy()
            other_valid[3, 3] = False
            depth = np.full(valid.shape, 6., np.float32)
            depth[~other_valid] = np.nan
            np.savez(root/'b.npz', depth=depth, valid=other_valid)
            np.savez(root/'geometry.npz', valid=valid, uv=np.array([[0, 0], [2, 2], [3.5, 3.5]]), camera_z=np.full(3, 2.))
            identity = Identity('depth', 1, 100).record()
            source = dict(identity=identity, K=np.eye(3).tolist(), grid='scale', rgb=dict(sha256='image'), samples=file_record(root/'geometry.npz'))
            common = dict(identity=identity, K=source['K'], grid='scale', source_rgb_sha256='image')
            result = aggregation.compare_depth(dict(common, depth=file_record(root/'a.npz')), dict(common, depth=file_record(root/'b.npz')), source)
            self.assertEqual(result['mean_abs_depth'], 2.)
            self.assertEqual(result['validity_disagreement'], 1)
            self.assertEqual((result['sparse_primary_valid'], result['sparse_compared_valid'], result['sparse_common_valid']), (3, 2, 2))
            self.assertAlmostEqual(result['camera_scale_ratio_difference'], 1.)
            self.assertAlmostEqual(result['camera_scale_ratio_relative_difference'], .5)
            self.assertEqual(result['full_rig_scale_evaluations'], 0)

    def test_segmentation_control_quantifies_arrays_and_marks_unmatched_queries(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            p, s, annotation, _ = fixture()
            np.save(root/'a.npy', p, allow_pickle=False)
            changed = p.copy()
            changed[2, 2] = 0
            np.save(root/'b.npy', changed, allow_pickle=False)
            np.savez(root/'da.npz', detector_rgb=np.ones((3, 4, 4), np.float32), detector_raw_token_logits=np.ones((9, 3)),
                     detector_selected_boxes_xyxy=np.zeros((1, 4)))
            np.savez(root/'db.npz', detector_rgb=np.ones((3, 4, 4), np.float32)*2, detector_raw_token_logits=np.ones((8, 3)),
                     detector_selected_boxes_xyxy=np.ones((1, 4)))
            common = dict(identity=annotation['identity'], source_rgb_sha256='image', K=np.eye(3).tolist(), grid='calibration', semantics=s)
            a = dict(common, instances=file_record(root/'a.npy'), diagnostics=file_record(root/'da.npz'))
            b = dict(common, instances=file_record(root/'b.npy'), diagnostics=file_record(root/'db.npz'))
            result = aggregation.segmentation_control({'key': a}, {'key': b})['rows'][0]
            self.assertEqual(result['semantic_union_disagreements']['person'], 1)
            self.assertEqual(result['intermediate_arrays']['detector_rgb']['mean_abs_difference'], 1.)
            self.assertEqual(result['intermediate_arrays']['detector_raw_token_logits']['status'], 'unverified')
            self.assertEqual(result['intermediate_arrays']['detector_selected_boxes_xyxy']['status'], 'recorded')

    def test_mask_checkpoint_accounts_for_entire_annotation_domain_when_outputs_missing(self):
        from vipe_benchmark.access import annotation_identities
        from vipe_benchmark.config import load
        config = load()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            p, s, annotation, layers = fixture()
            np.savez(root/'layers.npz', **layers)
            np.save(root/'valid.npy', layers['valid'], allow_pickle=False)
            records = []
            images = []
            valid = file_record(root/'valid.npy')
            for identity in annotation_identities(config):
                row = dict(identity=identity.record(), rgb=dict(path='unused-image', sha256='image', bytes=0),
                           K=np.eye(3).tolist(), grid=identity.branch, valid=valid)
                records.append(row)
                images.append(dict(annotation, **row, final_layers=file_record(root/'layers.npz')))
            write_json(root/'map.json', dict(observations=[]))
            write_json(root/'inputs.json', dict(rgb=records, map=file_record(root/'map.json')))
            pairs = [dict(camera=c, pair_start=t, associations=[]) for c in config['diagnostic_cameras'] for t in config['pair_starts']]
            write_json(root/'policy.json', dict(schema='vipe-benchmark-automated-annotation-policy/v1', human_ground_truth=False))
            write_json(root/'annotations.json', dict(schema=aggregation.PROXY_SCHEMA, status='reviewed-proxy', human_ground_truth=False,
                evidence_kind='model-assisted-proxy', images=images, pairs=pairs, policy=file_record(root/'policy.json')))
            request = dict(stage='masks', inputs=file_record(root/'inputs.json'), annotations=file_record(root/'annotations.json'),
                           amendment=file_record(root/'policy.json'))
            result = aggregation.run(request, root/'output', config)
            self.assertEqual(result['status'], 'complete')
            from vipe_benchmark.files import read_json
            metrics = read_json(root/'output/mask-metrics.json')
            self.assertEqual(metrics['scored_unique_annotation_images'], 0)
            self.assertEqual(metrics['semantic_class_presence'], dict(person=True, basketball=True))
            comparison = metrics['comparisons']['calibration/selection/all/pixel/person']
            self.assertEqual(comparison['scores'], {})
            self.assertEqual(len(comparison['ineligible']['S1']['reasons']), 1)
            self.assertEqual(metrics['expected_unique_annotation_images'], 232)
            static = read_json(result['final_static_masks']['path'])
            self.assertEqual((static['expected_rows'], static['generated_rows'], static['unavailable_rows']), (9450, 0, 9450))
            self.assertEqual(static['availability'], 'partial')


if __name__ == '__main__':
    unittest.main()
