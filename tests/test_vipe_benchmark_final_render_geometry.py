"""Full-rig producer fixtures at the worker/initializer boundary; no model load."""
import importlib
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from vipe_benchmark.files import read_json, file_record
from vipe_benchmark.final_render_initializer import assemble


class FakeMatcher:
    record_kind = 'fixture'
    sample_thresh = .5

    def match(self, first, second):
        # Pixel markers are fixture camera IDs. Literal world point (0,0,8).
        c0, c1 = int(first[0,0,0]), int(second[0,0,0])
        uv0 = np.array([480.5-5*c0,270.5])
        uv1 = np.array([480.5-5*c1,270.5])
        warp = np.empty((2,2,4), np.float64)
        warp[...,:2] = uv0/[480,270]-1
        warp[...,2:] = uv1/[480,270]-1
        confidence = np.array([[1.,0.],[0.,0.]])
        return (warp,confidence),dict(wall_seconds=0.,cuda_seconds=0.)

    def crop(self, warp, confidence, images, labels, ids):
        return (warp,confidence,[dict(source_instance=1,target_instance=1)]),dict(wall_seconds=0.,cuda_seconds=0.)

    def triangulate(self, P0, P1, uv0, uv1):
        from basketball_temporal_geometry import triangulate
        xyz = triangulate(np.array([uv0,uv1]),np.array([P0,P1]))
        return (xyz,np.isfinite(xyz).all(1)),dict(wall_seconds=0.,cuda_seconds=0.)


def fake_tracker(first, second, uv, labels0, labels1):
    # 2.5 pixel translation at focal length200/z8: .1metres per .04seconds.
    return uv+np.array([2.5,0]),np.ones(len(uv),bool)


class GeometryWorkerTests(unittest.TestCase):
    def setUp(self):
        self.fixture = importlib.import_module('test_vipe_benchmark_extended_final_render_initializer').ExtendedInitializerTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.request,self.root = self.fixture.request,self.fixture.root
        self.record = self.fixture.record
        bindings = self.request['bindings']
        manifest = read_json(bindings['scene_manifest']['path'])
        scene = read_json(bindings['scene_freeze']['path'])
        K = [[200,0,480],[0,200,270],[0,0,1]]
        for camera in manifest['cameras']:
            c = int(camera['id'])
            camera.update(K=[[200,0,480.5],[0,200,270.5],[0,0,1]],center=[c*.2,0,0],world_to_camera_T=[-c*.2,0,0])
            if str(c) in scene['cameras']:
                scene['cameras'][str(c)].update(K=K,center=[c*.2,0,0],t=[-c*.2,0,0])
        bindings['scene_manifest'] = self.record('geometry-manifest',manifest)
        bindings['scene_freeze'] = self.record('geometry-scene',scene)
        inputs = read_json(bindings['inputs']['path'])
        for row in inputs['rgb']:
            row['K'] = K
        bindings['inputs'] = self.record('geometry-inputs',inputs)
        for name in ('S2','M0','M1','M2'):
            native = read_json(bindings[name]['path'])
            for row in native['rows']:
                row['K'] = K
                if name == 'S2':
                    row['semantics'] = {'1':dict(class_='person',native_class='person',score=1.)}
                    row['semantics']['1']['class'] = row['semantics']['1'].pop('class_')
            bindings[name] = self.record('geometry-'+name,native)
        for name in ('N0','N1','N2'):
            native = read_json(bindings[name]['path']);native['inputs'] = bindings['inputs']
            bindings[name] = self.record('geometry-'+name,native)
        review = self.fixture.fixture.review
        context = review.record(dict(inputs=bindings['inputs']))
        for candidate,slot in review.slots.items():
            generation = read_json(slot['evidence']['generation']['path'])
            fit = read_json(generation['scales']['fit']['path'])
            fit['provenance']['inputs'] = bindings['inputs']
            fit_record = review.record(fit)
            check = dict(fit,role='selection',frozen_fit=fit_record)
            check_record = review.record(check)
            generation.update(context=context,inputs=bindings['inputs'],scales=dict(fit=fit_record,check=check_record))
            slot['evidence'].update(generation=review.record(generation),scale=check_record)
            if candidate == 'D2':
                slot['evidence'].update(historical_fit=review.record({'scale':fit_record}),historical_check=review.record({'scale':check_record}))
            if candidate == 'D5':
                bindings['D_fit'],bindings['D_check'] = fit_record,check_record
        package = read_json(review.package['path'])
        package['bindings'].update(inputs=bindings['inputs'],context=context,depth_aggregate_request=review.record(dict(candidates=review.slots)))
        review.package = review.record(package);review.form['package'] = review.package
        from vipe_benchmark import depth_review
        imported = depth_review.import_review(review.package,review.record(review.form),self.root/'geometry-review.json',actual=False)
        depth_review.freeze_decision(imported,self.root/'geometry-decision.json',actual=False)
        bindings['depth_decision'] = file_record(self.root/'geometry-decision.json')
        scene['scale_evidence'] = dict(fit=bindings['D_fit'],check=bindings['D_check'])
        bindings['scene_freeze'] = self.record('geometry-scene-rebound',scene)
        origin = read_json(self.request['initializer_contract']['voxel_basis_source']['receipt']['path'])
        origin['manifest_sha256'] = bindings['scene_manifest']['sha256']
        self.request['initializer_contract']['voxel_basis_source']['receipt'] = self.record('geometry-prior-origin',origin)
        self.fixture.fixture.rebind_proposal()
        from vipe_benchmark.files import object_hash
        width = read_json(self.fixture.width['path'])
        width.update(request_sha256=object_hash(self.request),scene=bindings['scene_freeze'],source=self.request['initializer_contract']['voxel_basis_source'])
        self.width = self.record('geometry-width',width)
        self.images = {c:np.full((540,960,3),c,np.uint8) for c in scene['cameras']}
        self.valid = np.ones((540,960),bool)
        self.labels = np.ones((540,960),np.int32)
        self.changing = np.zeros((540,960),bool)

    def load(self, source, segmentation, motion):
        return dict(rgb=self.images[str(source['identity']['camera'])],valid=self.valid,
            labels=self.labels,changing=self.changing)

    def test_full_rig_records_retain_physical_velocity_and_can_assemble(self):
        from vipe_benchmark.final_render_geometry import run
        result = run(self.request,'QF-B',self.root/'geometry-worker',FakeMatcher(),self.load,tracker=fake_tracker)
        self.assertEqual(result['coverage_edges'],810)
        self.assertFalse(result['execution_authorized'])
        self.assertFalse(result['native_adapter_qualified'])
        geometry = read_json(result['geometry']['path'])
        self.assertEqual(geometry['recipe']['samples_per_edge'],5000)
        self.assertEqual(geometry['recipe']['seed'],0)
        self.assertFalse(geometry['recipe']['native_model_verified'])
        self.assertEqual(geometry['rows'][0]['sampling'],dict(requested=5000,obtained=1,shortage=4999))
        with np.load(geometry['rows'][0]['artifact']['path'],allow_pickle=False) as data:
            np.testing.assert_allclose(data['world_positions'][0],[0,0,8],atol=1e-5)
            np.testing.assert_allclose(data['world_velocities'][0],[2.5,0,0],atol=5e-4)
            np.testing.assert_allclose(data['velocities'][0],[0,10,0],atol=2e-3)
        arrays,receipt = assemble(self.request,'QF-B',result['geometry'],self.width)
        self.assertEqual(receipt['foreground_observations'],810)
        self.assertEqual(len(arrays['positions']),810)
        self.assertEqual(geometry['rows'][0]['source_rows'].keys(),{'S2','M0'})

    def test_unrecognized_crop_source_cannot_enter_geometry(self):
        from vipe_benchmark.final_render_geometry import run
        class WrongCrop(FakeMatcher):
            def crop(self,warp,confidence,images,labels,ids):
                return (warp,confidence,[dict(source_instance=2,target_instance=1)]),dict(wall_seconds=0.,cuda_seconds=0.)
        with self.assertRaisesRegex(ValueError,'crop semantic'):
            run(self.request,'QF-B',self.root/'bad-crop',WrongCrop(),self.load,tracker=fake_tracker)

    def test_deadline_failure_preserves_first_edge_and_bound_failure_receipt(self):
        from vipe_benchmark.final_render_geometry import run,GeometryFailure
        ticks = iter([0.,0.,0.,5401.])
        output = self.root/'timed-geometry'
        with self.assertRaisesRegex(GeometryFailure,'wall limit') as caught:
            run(self.request,'QF-B',output,FakeMatcher(),self.load,tracker=fake_tracker,clock=lambda:next(ticks))
        receipt = read_json(caught.exception.result['path'])
        self.assertEqual(receipt['status'],'failed')
        self.assertEqual(len(receipt['artifacts']),1)
        self.assertTrue(Path(receipt['artifacts'][0]['path']).exists())
        self.assertFalse((output/'geometry.json').exists())
        self.assertFalse(receipt['execution_authorized'])

    def test_unsupported_temporal_motion_stays_zero_without_cross_camera_identity(self):
        from vipe_benchmark.final_render_geometry import run
        def insufficient(first,second,uv,labels0,labels1):
            return uv+[2.5,0],np.full(len(uv),int(first[0,0,0]) <= 2,bool)
        result = run(self.request,'QF-B',self.root/'unsupported',FakeMatcher(),self.load,tracker=insufficient)
        geometry = read_json(result['geometry']['path'])
        for row in geometry['rows']:
            with np.load(row['artifact']['path'],allow_pickle=False) as arrays:
                self.assertFalse(arrays['velocity_valid'].any())
                self.assertFalse(arrays['world_velocities'].any())
                self.assertFalse(arrays['velocities'].any())

    def test_source_substitution_and_heldout_neighbors_fail_before_publication(self):
        import copy
        from vipe_benchmark.final_render_geometry import run
        original = copy.deepcopy(self.request)
        motion = read_json(self.request['bindings']['M0']['path'])
        motion['rows'][0]['source_rgb_sha256'] = 'substituted'
        self.request['bindings']['M0'] = self.record('substituted-motion',motion)
        self.fixture.fixture.rebind_proposal()
        with self.assertRaisesRegex(ValueError,'source identity'):
            run(self.request,'QF-B',self.root/'substituted',FakeMatcher(),self.load)
        self.assertFalse((self.root/'substituted').exists())
        self.request.clear();self.request.update(original)
        neighbors = read_json(self.request['bindings']['N0']['path'])
        neighbors['records'][0]['neighbors'][0] = 0
        self.request['bindings']['N0'] = self.record('heldout-neighbor',neighbors)
        self.fixture.fixture.rebind_proposal()
        with self.assertRaisesRegex(ValueError,'training neighbors'):
            run(self.request,'QF-B',self.root/'heldout',FakeMatcher(),self.load)
        self.assertFalse((self.root/'heldout').exists())

    def test_actual_requests_and_nonfixture_backends_never_reach_model_boundary(self):
        from vipe_benchmark.final_render_geometry import run
        self.request['record_kind'] = 'actual'
        with self.assertRaisesRegex(ValueError,'supervised native'):
            run(self.request,'QF-B',self.root/'actual',FakeMatcher(),self.load)
        self.request['record_kind'] = 'fixture'
        backend = FakeMatcher();backend.record_kind = 'actual'
        with self.assertRaisesRegex(ValueError,'fixture backend'):
            run(self.request,'QF-B',self.root/'actual-backend',backend,self.load)
        self.assertFalse((self.root/'actual').exists())
        self.assertFalse((self.root/'actual-backend').exists())

    def test_existing_output_directory_is_preserved(self):
        from vipe_benchmark.final_render_geometry import run
        output = self.root/'existing';output.mkdir();marker = output/'marker';marker.write_bytes(b'preserve me')
        with self.assertRaises(FileExistsError):
            run(self.request,'QF-B',output,FakeMatcher(),self.load)
        self.assertEqual(list(output.iterdir()),[marker])
        self.assertEqual(marker.read_bytes(),b'preserve me')

    def test_storage_rejection_does_not_publish_an_over_budget_archive(self):
        from vipe_benchmark.final_render_geometry import run,GeometryFailure
        self.request['artifact_bytes_limit'] = 1
        self.fixture.fixture.rebind_proposal()
        output = self.root/'storage'
        with self.assertRaisesRegex(GeometryFailure,'artifact limit') as caught:
            run(self.request,'QF-B',output,FakeMatcher(),self.load,tracker=fake_tracker)
        receipt = caught.exception.receipt
        self.assertIsNone(caught.exception.result)
        self.assertEqual(receipt['artifacts'],[])
        self.assertEqual(list(output.glob('*.npz')),[])

    def test_all_five_fixture_arms_keep_selected_depth_and_exact_parent_rows(self):
        from vipe_benchmark.final_render_geometry import run
        for arm in self.request['compositions']:
            if arm == 'QF-B':
                continue
            with self.subTest(arm=arm):
                result = run(self.request,arm,self.root/arm,FakeMatcher(),self.load,tracker=fake_tracker)
                geometry = read_json(result['geometry']['path'])
                self.assertEqual(result['composition'],self.request['compositions'][arm])
                self.assertEqual(result['composition']['depth'],'D5')
                self.assertEqual(len(geometry['rows']),810)
                self.assertEqual(set(geometry['rows'][0]['source_rows']),{'S2',self.request['compositions'][arm]['motion']})
                arrays,receipt = assemble(self.request,arm,result['geometry'],self.width)
                self.assertEqual(receipt['foreground_observations'],810)

    def test_nonfinite_clock_and_cuda_claim_fail_without_execution_authority(self):
        from vipe_benchmark.final_render_geometry import run,GeometryFailure
        ticks = iter([0.,float('nan')])
        with self.assertRaisesRegex(GeometryFailure,'finite monotonic') as caught:
            run(self.request,'QF-B',self.root/'clock',FakeMatcher(),self.load,clock=lambda:next(ticks))
        self.assertEqual(caught.exception.receipt['artifacts'],[])
        self.assertFalse(caught.exception.receipt['execution_authorized'])
        class CudaClaim(FakeMatcher):
            def match(self,first,second):
                value,measurement = super().match(first,second)
                measurement['cuda_seconds'] = 1.
                return value,measurement
        with self.assertRaisesRegex(GeometryFailure,'cannot claim CUDA'):
            run(self.request,'QF-B',self.root/'cuda-claim',CudaClaim(),self.load)

    def test_static_points_keep_zero_velocity_and_pair_motion_clearance(self):
        from vipe_benchmark.final_render_geometry import run
        mask = read_json(self.request['bindings']['S2']['path'])
        for row in mask['rows']:
            row['semantics'] = {}
        self.request['bindings']['S2'] = self.record('static-semantics',mask)
        self.fixture.fixture.rebind_proposal()
        from vipe_benchmark.files import object_hash
        width = read_json(self.width['path']);width['request_sha256'] = object_hash(self.request)
        width_record = self.record('static-width',width)
        self.labels = np.zeros((540,960),np.int32)
        class StaticMatcher(FakeMatcher):
            def crop(self,warp,confidence,images,labels,ids):
                return (warp,confidence,[]),dict(wall_seconds=0.,cuda_seconds=0.)
        result = run(self.request,'QF-B',self.root/'static',StaticMatcher(),self.load,tracker=fake_tracker)
        geometry = read_json(result['geometry']['path'])
        with np.load(geometry['rows'][0]['artifact']['path'],allow_pickle=False) as arrays:
            self.assertEqual(arrays['region'].tolist(),[0])
            self.assertFalse(arrays['world_velocities'].any())
            self.assertFalse(arrays['velocity_valid'].any())
        self.changing = np.ones((540,960),bool)
        result = run(self.request,'QF-B',self.root/'moving-static',StaticMatcher(),self.load,tracker=fake_tracker)
        geometry = read_json(result['geometry']['path'])
        self.assertEqual(sum(row['gates']['accepted'] for row in geometry['rows']),0)
        with self.assertRaisesRegex(ValueError,'empty full-rig'):
            assemble(self.request,'QF-B',result['geometry'],width_record)

    def test_cpu_geometry_works_when_torch_import_is_prohibited(self):
        import subprocess
        code = """
import importlib.abc
import sys
import unittest
class BlockTorch(importlib.abc.MetaPathFinder):
    def find_spec(self,fullname,path=None,target=None):
        if fullname == 'torch' or fullname.startswith('torch.'):
            raise RuntimeError('Torch import prohibited by CPU geometry qualification')
sys.meta_path.insert(0,BlockTorch())
suite = unittest.defaultTestLoader.loadTestsFromName('test_vipe_benchmark_final_render_geometry.GeometryWorkerTests.test_full_rig_records_retain_physical_velocity_and_can_assemble')
result = unittest.TextTestRunner().run(suite)
sys.exit(not result.wasSuccessful())
"""
        completed = subprocess.run([sys.executable,'-B','-c',code],capture_output=True,text=True,timeout=120)
        self.assertEqual(completed.returncode,0,completed.stdout+completed.stderr)

    def test_backend_host_permission_denial_keeps_its_error_class(self):
        from vipe_benchmark.final_render_geometry import run
        class Denied(FakeMatcher):
            def match(self,first,second):
                raise PermissionError('host access denied')
        with self.assertRaisesRegex(PermissionError,'host access denied'):
            run(self.request,'QF-B',self.root/'denied',Denied(),self.load)


if __name__=='__main__':
    unittest.main()
