from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark import diagnostics
from vipe_benchmark.access import Identity
from vipe_benchmark.config import load, training_cameras
from vipe_benchmark.files import file_record, read_json, write_json


def camera(offset):
    return dict(K=[[800., 0, 479.5], [0, 800., 269.5], [0, 0, 1]], R=np.eye(3).tolist(),
                t=[-float(offset), 0., 0.], center=[float(offset), 0., 0.])


def observed(xyz, cameras):
    result = []
    for c in cameras.values():
        # Independent pinhole projection, including precisely one +0.5 shift.
        q = xyz + c['t']
        result.append(np.column_stack((800*q[:, 0]/q[:, 2]+480, 800*q[:, 1]/q[:, 2]+270)))
    return np.asarray(result)


class GeometryDiagnosticTests(unittest.TestCase):
    def test_frozen_matrix_and_repeat_membership(self):
        config = load()
        self.assertEqual(len(diagnostics.COARSE_ARMS), 9)
        contexts = diagnostics.contexts(config)
        self.assertEqual((len(contexts), len(set(contexts)), contexts[0], contexts[-1]), (64, 64, (0, 1), (45, 33)))
        self.assertEqual(diagnostics.contexts(config, repeat=True), [(20, 1)])
        self.assertEqual(diagnostics.COARSE_ARMS['G-N2'], ['S0', 'D0', 'M0', 'N2'])

    def test_independent_points_expose_all_rejection_stages(self):
        cameras = {i: camera(x) for i, x in [(1, 0), (2, 1), (3, -1), (4, 2)]}
        xyz = np.array([[-2., -.8, 10], [-1., -.8, 10], [0., -.8, 10], [1., -.8, 10],
                        [2., -.8, 10], [1., -2, -10], [-1., 1., 10], [1., 1., 5000], [2., 1., 10]])
        uv = observed(xyz, cameras)
        labels, changing = {}, {}
        for k, c in enumerate(cameras):
            label = np.zeros((540, 960), np.int32)
            for i, instance in [(1, 1), (2, 2), (3, 1)]:
                if i == 3 and k >= 2:
                    continue
                x, y = np.floor(uv[k, i]).astype(int)
                label[y-1:y+2, x-1:x+2] = instance
            labels[c] = dict(labels=label, semantics={'1': {'class': 'person'}, '2': {'class': 'basketball'}})
            changing[c] = np.zeros(label.shape, bool)
        x, y = np.floor(uv[1, 4]).astype(int)
        changing[2][y, x] = True
        uv[1, 8, 1] += 3.
        numerical = np.ones(len(xyz), bool)
        numerical[6] = False
        arrays, record = diagnostics.evaluate_edge(xyz, numerical, uv, [1, 2, 3, 4], 1, cameras, labels, changing)
        np.testing.assert_array_equal(arrays['accepted'], [True, True, True, False, False, False, False, False, False])
        self.assertEqual([record['stages'][stage]['rejected'] for stage in record['stages']], [1, 1, 1, 1, 0, 1, 1])
        self.assertEqual(record['classes']['person']['attempted'], 2)
        self.assertEqual(record['classes']['person']['accepted'], 1)
        self.assertEqual(record['classes']['ball']['accepted'], 1)
        self.assertEqual(record['classes']['foreground']['supporting_camera_histogram']['4'], 2)

    def test_invalid_reference_is_never_static_and_empty_shortage_is_valid(self):
        cameras = {i: camera(i-1) for i in range(1, 5)}
        xyz = np.array([[0., 0., 10.]])
        uv = observed(xyz, cameras)
        labels = {c: dict(labels=np.zeros((540, 960), np.int32), semantics={}) for c in cameras}
        labels[1]['labels'][270, 480] = -1
        changes = {c: np.zeros((540, 960), bool) for c in cameras}
        arrays, record = diagnostics.evaluate_edge(xyz, [True], uv, list(cameras), 1, cameras, labels, changes)
        self.assertEqual(record['invalid_reference_samples'], 1)
        self.assertEqual(record['classes']['static']['attempted'], 0)
        self.assertFalse(arrays['accepted'][0])
        arrays, record = diagnostics.evaluate_edge(np.empty((0, 3)), np.empty(0, bool), np.empty((4, 0, 2)),
                                                  list(cameras), 1, cameras, labels, changes)
        self.assertEqual(record['accepted'], 0)

    def test_grid_uses_opencv_centers_and_marginal_coverage(self):
        uv = np.array([[240.25, 135.25], [240.5, 135.5], [960.5, 0.5]])
        report = diagnostics.coverage(uv, np.array([1, 1, 1]))
        self.assertEqual(report['person']['cells'], [[0, 0], [1, 1]])
        empty = diagnostics.coverage(np.empty((0, 2)), np.empty(0, int))
        first = dict(other=2, reference_coverage=report, classes={k: dict(attempted=3, accepted=2) for k in diagnostics.REGIONS}, matching=dict(wall_seconds=1))
        second = dict(first, other=3)
        third = dict(first, other=4, reference_coverage=empty)
        result = diagnostics._union_context([first, second, third], 20, 1, [2, 3, 4])
        self.assertEqual([x['new_cells'] for x in result['classes']['person']['marginal_coverage']], [2, 0, 0])

    def test_scene_freeze_preserves_projection_normalization_and_rejects_stale_gate(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name in ('reference', 'normalization'):
                write_json(root/f'{name}.json', {})
            inputs = dict(map={}, reference_geometry=dict(scale=2., freeze=file_record(root/'reference.json'),
                normalization_source=file_record(root/'normalization.json'), normalization=dict(transform=np.diag([.3, .3, .3, 1.]).tolist())))
            map_data = dict(points={'1': [0, 1, 10], '2': [1, 0, 10]}, cameras={'1': camera(1)})
            config_hash = diagnostics.digest(diagnostics.ROOT/'configs/basketball-rev2/scale.json')
            fitting = dict(status='passed', role='fit', scale=6., scale_protocol_sha256=config_hash,
                           provenance=dict(component='D1', component_sha256='frozen-component'))
            write_json(root/'fit.json', fitting)
            fit = file_record(root/'fit.json')
            write_json(root/'check.json', dict(fitting, role='selection', frozen_fit=fit))
            freeze = diagnostics.scene_freeze(inputs, map_data, fit=fit, check=file_record(root/'check.json'), depth_id='D1')
            np.testing.assert_allclose(freeze['points'], [[0, 6, 60], [6, 0, 60]])
            np.testing.assert_allclose(freeze['normalization'], np.diag([.1, .1, .1, 1.]))
            self.assertLess(freeze['projection_max_abs_error_pixels'], 1e-6)
            with self.assertRaisesRegex(ValueError, 'another depth'):
                diagnostics.scene_freeze(inputs, map_data, fit=fit, check=file_record(root/'check.json'), depth_id='D2')
            with self.assertRaisesRegex(ValueError, 'both current'):
                diagnostics.scene_freeze(inputs, map_data, fit=fit, depth_id='D1')

    def test_native_solver_contract_forces_cuda_float32_without_execution(self):
        import torch
        backend = diagnostics.NativeBackend.__new__(diagnostics.NativeBackend)
        backend.torch = torch
        backend.measured = lambda function: (function(), {})
        with mock.patch('triangulation.triangulate_points', return_value=(torch.zeros((1, 3)), torch.ones(1, dtype=torch.bool))) as solve:
            backend.triangulate(np.eye(3, 4), np.eye(3, 4), [[0, 0]], [[1, 0]])
        self.assertEqual(solve.call_args.kwargs, dict(device='cuda', dtype=torch.float32))

    def test_unavailable_or_uninitializable_cuda_stops_before_loading_geometry(self):
        import torch
        for available, initialization_error in [(False, None), (True, RuntimeError('fixture driver unavailable'))]:
            with self.subTest(available=available), \
                    mock.patch.object(torch.cuda, 'is_available', return_value=available), \
                    mock.patch.object(torch.cuda, 'init', side_effect=initialization_error) as initialize, \
                    mock.patch('edgs_source.load_roma') as load_model:
                with self.assertRaisesRegex(PermissionError, 'CUDA (device access|driver/device initialization)') as failure:
                    diagnostics.NativeBackend('unused-checkout', 'unused-weights')
                self.assertEqual(initialize.call_count, int(available))
                self.assertEqual(load_model.call_count, 0)
                if initialization_error is not None:
                    self.assertIs(failure.exception.__cause__, initialization_error)


class FakeBackend:
    def __init__(self, **unused):
        self.loading = dict(wall_seconds=0., cuda_seconds=0.)
        self.model = type('Model', (), {'sample_thresh': .5})()

    def match(self, first, second):
        reference, other = int(first[0, 0, 0]), int(second[0, 0, 0])
        uv = np.array([[[240., 135.], [720., 135.]], [[240., 405.], [720., 405.]]])
        target = uv + [-80*(other-reference), 0]
        warp = np.concatenate((uv/[480, 270]-1, target/[480, 270]-1), axis=2)
        return (warp, np.ones((2, 2))), dict(wall_seconds=.1, cuda_seconds=0.)

    def triangulate(self, P0, P1, uv0, uv1):
        # Independent float64 inhomogeneous fixture solver; never a production fallback.
        results = []
        for a, b in zip(uv0, uv1):
            A = np.asarray([a[0]*P0[2]-P0[0], a[1]*P0[2]-P0[1], b[0]*P1[2]-P1[0], b[1]*P1[2]-P1[1]])
            results.append(np.linalg.lstsq(A[:, :3], -A[:, 3], rcond=None)[0])
        return (np.asarray(results).reshape(-1, 3), np.ones(len(results), bool)), dict(wall_seconds=0., cuda_seconds=0.)

    def resources(self):
        return dict(test_fixture=True)


class DiagnosticWorkflowTests(unittest.TestCase):
    def test_repeat_cpu_fixture_writes_three_edges_pair_names_and_shortages(self):
        import cv2
        config = load()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            def json_file(name, value):
                path = root/(name+'.json')
                write_json(path, value)
                return file_record(path)
            def array_file(name, array):
                path = root/(name+'.npy')
                np.save(path, array, allow_pickle=False)
                return file_record(path)
            valid = array_file('valid', np.ones((540, 960), bool))
            mask = array_file('instances', np.zeros((540, 960), np.int32))
            change = array_file('changing', np.zeros((540, 960), bool))
            rgb, masks, motion = [], [], []
            for c in (1, 2, 3, 4):
                for frame in (20, 21):
                    image = root/f'c{c}f{frame}.png'
                    self.assertTrue(cv2.imwrite(str(image), np.full((540, 960, 3), c, np.uint8)))
                    source = dict(identity=Identity('reconstruction', c, frame).record(), rgb=file_record(image),
                                  K=camera(c-1)['K'], grid='undistorted-opencv-integer', valid=valid)
                    rgb.append(source)
                    common = dict(identity=Identity('reconstruction', c, frame, 20).record(), source_rgb_sha256=source['rgb']['sha256'],
                                  K=source['K'], grid=source['grid'])
                    masks.append(dict(common, instances=mask, semantics={}, valid=valid))
                    motion.append(dict(common, changing=change))
            reference = json_file('reference', {})
            normal = json_file('normal', {})
            map_record = json_file('map', dict(points={'1': [0, 0, 10]}, cameras={str(c): camera(c-1) for c in training_cameras(config)}))
            inputs = json_file('inputs', dict(rgb=rgb, map=map_record, reference_geometry=dict(scale=1, freeze=reference,
                    normalization_source=normal, normalization=dict(transform=np.eye(4).tolist()))))
            request = dict(job_id='R-G', inputs=inputs, segmentation=json_file('segmentation', dict(status='complete', component='S0', rows=masks)),
                motion=json_file('motion', dict(status='complete', component='M0', rows=motion)),
                neighbors=json_file('neighbors', dict(status='complete', component='N0', records=[dict(reference=1, status='complete', neighbors=[2, 3, 4])])),
                roma=dict(checkout='unused', weights='unused'))
            primary_config = json_file('primary-config', dict(request=dict(request, job_id='G-S0')))
            generator = np.random.Generator(np.random.PCG64(0))
            generator.random(73)  # The primary job had already sampled earlier contexts.
            primary_state = generator.bit_generator.state
            primary_rows = []
            grid = np.array([[240., 135.], [720., 135.], [240., 405.], [720., 405.]])
            for other in (2, 3, 4):
                chosen = generator.choice(np.arange(4), 4, replace=False, p=np.full(4, .25))
                path = root/f'primary-{other}.npz'
                np.savez(path, candidate_uv=np.asarray([grid[chosen]+[-80*(c-1), 0] for c in (1, 2, 3, 4)]),
                         accepted=np.ones(4, bool), numerical_valid=np.ones(4, bool))
                primary_rows.append(dict(pair_start=20, reference=1, other=other, artifact=file_record(path),
                    classes={k: dict(accepted=4 if k == 'static' else 0) for k in diagnostics.REGIONS}))
            request['repeat_source'] = json_file('primary-result', dict(status='complete', job_id='G-S0', configuration=primary_config,
                rows=primary_rows, contexts=[dict(pair_start=20, reference=1, status='complete', sampling_rng_state=primary_state)]))
            with mock.patch.object(diagnostics, 'NativeBackend', FakeBackend):
                report = diagnostics.run(request, root/'output', config)
            self.assertEqual(report['status'], 'complete')
            self.assertEqual(report['summary']['full_image_matches'], 3)
            self.assertEqual(report['summary']['classes']['static']['accepted'], 12)
            self.assertEqual([r['sampling']['shortage'] for r in report['rows']], [4996]*3)
            self.assertEqual(report['contexts'][0]['pair_start'], 20)
            self.assertEqual(report['contexts'][0]['sampling_rng_state'], primary_state)
            self.assertEqual([r['acceptance_disagreements'] for r in report['repeat']['edges']], [0, 0, 0])
            self.assertEqual(read_json(root/'output/result.json')['status'], 'complete')
            self.assertEqual(len(list((root/'output').glob('pair20-ref1-other*.npz'))), 3)


if __name__ == '__main__':
    unittest.main()
