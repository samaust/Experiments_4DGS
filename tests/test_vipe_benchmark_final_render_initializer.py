"""CPU-only QF geometry-to-initializer worker boundary fixtures."""
import copy
import importlib
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.files import file_record, object_hash
from vipe_benchmark.final_render_contract import KEYFRAMES, TRAINING_CAMERAS
from vipe_benchmark.final_render_initializer import assemble


class InitializerTests(unittest.TestCase):
    def setUp(self):
        fixture = importlib.import_module('test_vipe_benchmark_final_render_contract')
        self.base = fixture.ContractTests()
        self.base.setUp()
        self.addCleanup(self.base.tearDown)
        self.root = self.base.root
        self.request = copy.deepcopy(self.base.request)
        self.transform = np.array([[0., -2., 0., 1.], [2., 0., 0., 2.],
                                   [0., 0., 2., 3.], [0., 0., 0., 1.]])
        self.request['initializer_contract']['normalization'] = dict(transform=self.transform.tolist())
        ids = [str(c) for c in range(34)]
        timing = dict(schema='camera-timing/v1', units='seconds',
            convention='corrected_timestamp_seconds = source_timestamp_seconds - offset_seconds',
            camera_ids=ids, reference_camera='1', offset_seconds={c: 0. for c in ids},
            uncertainty_seconds={c: 0. for c in ids}, source_support_seconds={c: [0., 2.] for c in ids},
            coverage=dict(camera_ids=ids), source_window_seconds=[0., 2.],
            normalization=dict(origin_seconds=0., duration_seconds=2.),
            kind='operational-assumption', provenance=dict(fixture=True))
        from sync_timing import common_training_keys
        frames = [(c, f, f/25) for c in ids for f in range(50)]
        keys, excluded = common_training_keys(frames, [timing], ['0','10','20','30'])
        self.manifest = dict(schema='basketball-processed/v1', status='prepared', source_fps=25,
            timing=timing, comparison_timings=[timing], time=timing['normalization'],
            heldout_camera_ids=['0','10','20','30'], temporal_holdout_seconds=[.8,1.],
            training_keys=[list(k) for k in keys], training_exclusions=excluded,
            cameras=[dict(id=c, split='train' if int(c) in TRAINING_CAMERAS else 'test',
                K=[[2.,0.,1.5],[0.,2.,1.5],[0.,0.,1.]], width=960,height=540,
                world_to_camera_R=np.eye(3).tolist(),world_to_camera_T=[0.,0.,0.],center=[0.,0.,0.],
                frames=[dict(frame_id=f, normalized_time=f/50, sha256=f'{c}-{f}') for f in range(50)]) for c in ids])
        self.request['bindings']['scene_manifest'] = self.base.record('manifest', self.manifest)
        basis=self.root/'voxel-basis.npz';np.savez(basis,normalized_positions=np.array([[0.,0.,0.],[0.,0.,1.]],np.float32))
        self.request['initializer_contract']['voxel_basis']=file_record(basis)
        inputs = self._read(self.request['bindings']['inputs'])
        inputs['reference_geometry'] = dict(scale=1.7,normalization=dict(scene_scale=10.,transform=self.transform.tolist()),freeze=self.base.record('historical-freeze',{}))
        inputs['map']=self.base.record('accepted-map',{})
        self.manifest['freeze_sha256']=inputs['reference_geometry']['freeze']['sha256']
        self.request['bindings']['scene_manifest']=self.base.record('manifest-frozen',self.manifest)
        for row in inputs['rgb']:row['K']=[[2.,0.,1.],[0.,2.,1.],[0.,0.,1.]]
        for name in ('S2','M0','M1','M2'):
            native=self._read(self.request['bindings'][name])
            for row in native['rows']:row['K']=[[2.,0.,1.],[0.,2.,1.],[0.,0.,1.]]
            self.request['bindings'][name]=self.base.record(name+'-calibrated',native)
        self.request['bindings']['inputs'] = self.base.record('inputs2', inputs)
        prior=self.root/'static-prior.npz';np.savez(prior,positions=((np.array([[0.,0.,0.],[0.,0.,1.]])-self.transform[:3,3])@np.linalg.inv(self.transform[:3,:3]).T).astype(np.float32))
        origin=self.base.record('static-origin',dict(schema='basketball-static-initialization/v1',status='prepared',source_frame=25,points=2,inputs=[],
            manifest_sha256=self.request['bindings']['scene_manifest']['sha256'],archive_sha256=file_record(prior)['sha256'],
            freeze_sha256=inputs['reference_geometry']['freeze']['sha256']))
        self.request['initializer_contract']['voxel_basis_source']=dict(archive=file_record(prior),receipt=origin)
        for name in ('N0','N1','N2'):
            native=self._read(self.request['bindings'][name]);native['inputs']=self.request['bindings']['inputs']
            self.request['bindings'][name]=self.base.record(name+'-inputs',native)
        scale = self._read(self.request['bindings']['D4_fit'])['scale']
        scene = dict(schema='vipe-benchmark-diagnostic-scene/v1', status='complete', depth_component='D4',
            scale=1.7, scale_evidence=dict(fit=scale,check=scale), normalization=self.transform.tolist(),
            historical_reference=inputs['reference_geometry'],map=inputs['map'],
            units=dict(normalized_time_seconds=2.,frame_seconds=.04,
                velocity='metres/second -> normalization linear map * 2 seconds'),
            cameras={str(c):dict(K=[[2.,0.,1.],[0.,2.,1.],[0.,0.,1.]],R=np.eye(3).tolist(),t=[0.,0.,0.],center=[0.,0.,0.]) for c in TRAINING_CAMERAS})
        self.scene_record = self.base.record('scene2', scene)
        self.width = self.base.record('width', dict(schema='plan067-final-render-voxel-width/v1',
            rule='half median positive nearest-neighbor distance', width=.5, scene=self.scene_record,
            basis=self.request['initializer_contract']['voxel_basis'],source=self.request['initializer_contract']['voxel_basis_source'],
            request_sha256=object_hash(self.request), record_kind='fixture'))
        neighbors = self._read(self.request['bindings']['N0'])['records']
        segmentation = self._read(self.request['bindings']['S2'])['rows']
        motion = self._read(self.request['bindings']['M0'])['rows']
        index = lambda rows: {(r['identity']['camera'],r['identity']['frame'],r['identity']['pair_start']):r for r in rows}
        si, mi = index(segmentation), index(motion)
        rows = []
        for frame in KEYFRAMES:
            for neighbor in neighbors:
                camera = neighbor['reference']; cameras = [camera, *neighbor['neighbors']]
                source_rows = {name:[object_hash(idx[c,f,frame]) for c in cameras for f in (frame,frame+1)]
                    for name,idx in [('S2',si),('M0',mi)]}
                for other in cameras[1:]:
                    physical=np.array([[1.,2.,3.],[3.,2.,1.]],np.float32)
                    archive=self.root/f'edge-{frame}-{camera}-{other}.npz'
                    np.savez(archive,world_positions=physical,
                        positions=(physical@self.transform[:3,:3].T+self.transform[:3,3]).astype(np.float32),
                        colors=np.full((2,3),.5,np.float32), velocities=np.array([[0.,0.,0.],[1.,0.,0.]],np.float32),
                        world_velocities=np.array([[0.,0.,0.],[0.,-.25,0.]],np.float32),
                        times=np.full((2,1),frame/50,np.float32),durations=np.full((2,1),.2,np.float32),
                        region=np.array([0,1],np.int32),velocity_valid=np.array([False,True]),camera_ids=np.array(cameras))
                    rows.append(dict(pair_start=frame,reference=camera,other=other,artifact=file_record(archive),source_rows=source_rows))
        self.geometry = dict(schema='plan067-final-render-geometry/v1',status='complete',record_kind='fixture',
            arm='QF-B',request_sha256=object_hash(self.request),composition=self.request['compositions']['QF-B'],
            scene=self.scene_record,rows=rows,prerequisites={k:self.request['bindings'][k] for k in ['S2','D4_fit','D4_check','M0','N0']})

    @staticmethod
    def _read(record):
        import json
        return json.loads(Path(record['path']).read_text())

    def run_adapter(self, geometry=None, width=None):
        return assemble(self.request,'QF-B',self.base.record('geometry-'+str(len(list(self.root.glob('geometry-*')))),geometry or self.geometry),width or self.width)

    def test_rotated_scene_full_coverage_fuses_static_and_preserves_foreground(self):
        arrays,receipt=self.run_adapter()
        self.assertEqual(len(arrays['positions']),819)
        self.assertEqual(receipt['physical_static_points'],1)
        self.assertEqual(receipt['foreground_observations'],810)
        self.assertEqual(receipt['coverage_edges'],810)
        self.assertFalse(receipt['execution_authorized'])
        self.assertFalse(receipt['native_adapter_qualified'])
        from vipe_benchmark.final_render_contract import validate_initializer
        checked=validate_initializer(self.request,'QF-B',receipt['initializer_receipt'],arrays)
        self.assertEqual(checked['point_count'],819)
        self.assertFalse(checked['native_adapter_qualified'])
        np.testing.assert_allclose(arrays['positions'][0],[-3.,4.,9.])
        self.assertTrue(np.all(arrays['velocities'][:9]==0))
        np.testing.assert_allclose(arrays['velocities'][9],[1.,0.,0.])

    def test_missing_duplicate_and_heldout_context_rejected(self):
        for mutate in (lambda g:g['rows'].pop(),lambda g:g['rows'].append(g['rows'][0]),
                       lambda g:g['rows'][0].update(reference=0)):
            g=copy.deepcopy(self.geometry);mutate(g)
            with self.assertRaises(ValueError):self.run_adapter(g)

    def test_changed_source_identity_and_neighbor_order_rejected(self):
        for mutate in (lambda g:g['rows'][0]['source_rows']['S2'].__setitem__(0,'wrong'),
                       lambda g:g['rows'][0].update(other=33)):
            g=copy.deepcopy(self.geometry);mutate(g)
            with self.assertRaises(ValueError):self.run_adapter(g)

    def test_changed_physical_normalization_and_unmeasured_velocity_rejected(self):
        for name in ('positions','velocities','world_velocities','camera_ids','times'):
            record=self.geometry['rows'][0]['artifact'];path=Path(record['path'])
            with np.load(path,allow_pickle=False) as archive:arrays={k:archive[k].copy() for k in archive.files}
            arrays[name].flat[0]+=1
            changed=self.root/f'changed-{name}.npz';np.savez(changed,**arrays)
            g=copy.deepcopy(self.geometry);g['rows'][0]['artifact']=file_record(changed)
            with self.assertRaises(ValueError):self.run_adapter(g)

    def test_manifest_union_exclusions_and_nonzero_offsets_rejected(self):
        for mutate in (lambda m:m['training_keys'].pop(),
                       lambda m:m['timing']['offset_seconds'].update({'1':.1})):
            m=copy.deepcopy(self.manifest);mutate(m)
            request=copy.deepcopy(self.request);request['bindings']['scene_manifest']=self.base.record('bad-manifest-'+str(len(list(self.root.glob('bad-manifest-*')))),m)
            g=copy.deepcopy(self.geometry);g['request_sha256']=object_hash(request)
            width=self._read(self.width);width['request_sha256']=object_hash(request)
            with self.assertRaises(ValueError):assemble(request,'QF-B',self.base.record('geo-badmanifest-'+str(len(list(self.root.glob('geo-badmanifest-*')))),g),self.base.record('width-badmanifest-'+str(len(list(self.root.glob('width-badmanifest-*')))),width))

    def test_actual_assembly_rejects_consistent_substituted_manifest(self):
        from sync_timing import common_training_keys
        from vipe_benchmark import final_render_contract as contract
        # Real scope/source/preset pins exercise actual parsing. Geometry remains
        # a mutation fixture; this test establishes no native qualification.
        request=copy.deepcopy(self.request);request['record_kind']='actual'
        for name,(relative,_,_) in contract.FROZEN_SCOPE.items():
            request['bindings'][name]=file_record(contract.ROOT/relative)
        repository=Path('/home/auss/git_repos/samaust/Experiments_4DGS')
        request['bindings']['source']=file_record(contract.__file__)
        request['bindings']['preset']=file_record(repository/'.local/FreeTimeGsVanilla/src/simple_trainer_freetime_4d_pure_relocation.py')
        request['bindings']['scene_freeze']=self.scene_record
        manifest=copy.deepcopy(self.manifest)
        comparison=copy.deepcopy(manifest['timing'])
        comparison['offset_seconds']['2']=-.04
        manifest['comparison_timings'].append(comparison)
        frames=[(str(c),f,f/25) for c in range(34) for f in range(50)]
        retained,excluded=common_training_keys(frames,manifest['comparison_timings'],manifest['heldout_camera_ids'])
        manifest['training_keys']=[list(k) for k in retained];manifest['training_exclusions']=excluded
        request['bindings']['scene_manifest']=self.base.record('substituted-union',manifest)
        geometry=copy.deepcopy(self.geometry)
        geometry.update(record_kind='actual',request_sha256=object_hash(request))
        width=self._read(self.width);width.update(record_kind='actual',request_sha256=object_hash(request))
        with self.assertRaisesRegex(ValueError,'accepted processed manifest path/hash/size'):
            assemble(request,'QF-B',self.base.record('substituted-union-geometry',geometry),
                     self.base.record('substituted-union-width',width))

    def test_consistent_but_unapproved_normalization_substitution_rejected(self):
        request=copy.deepcopy(self.request)
        changed=self.transform.copy();changed[:3,:3]*=2
        request['initializer_contract']['normalization']['transform']=changed.tolist()
        scene=self._read(self.scene_record);scene['normalization']=changed.tolist()
        g=copy.deepcopy(self.geometry);g['scene']=self.base.record('changed-scene',scene);g['request_sha256']=object_hash(request)
        width=self._read(self.width);width['scene']=g['scene'];width['request_sha256']=object_hash(request)
        with self.assertRaisesRegex(ValueError,'historical normalized coordinates'):
            assemble(request,'QF-B',self.base.record('changed-scene-geometry',g),self.base.record('changed-scene-width',width))

    def test_voxel_basis_origin_and_normalized_points_rejected(self):
        for broken in ('origin','basis'):
            request=copy.deepcopy(self.request);width=self._read(self.width)
            if broken=='origin':
                origin=self._read(width['source']['receipt']);origin['source_frame']=22
                source=dict(width['source'],receipt=self.base.record('heldout-origin',origin))
                request['initializer_contract']['voxel_basis_source']=source;width['source']=source
            else:
                path=self.root/'wrong-basis.npz';np.savez(path,normalized_positions=np.array([[0.,0.,0.],[0.,0.,2.]],np.float32))
                request['initializer_contract']['voxel_basis']=file_record(path);width['basis']=file_record(path)
            width['request_sha256']=object_hash(request)
            g=copy.deepcopy(self.geometry);g['request_sha256']=object_hash(request)
            with self.assertRaisesRegex(ValueError,'static prior|normalized voxel basis'):
                assemble(request,'QF-B',self.base.record('basis-geometry-'+broken,g),self.base.record('basis-width-'+broken,width))

    def test_geometry_provenance_fixture_kind_and_width_substitution_rejected(self):
        for key,value in [('record_kind','actual'),('request_sha256','wrong'),('composition',{})]:
            g=copy.deepcopy(self.geometry);g[key]=value
            with self.assertRaises(ValueError):self.run_adapter(g)
        width=self._read(self.width);width['scene']=self.request['bindings']['scene_manifest']
        with self.assertRaises(ValueError):self.run_adapter(width=self.base.record('wrong-width',width))


if __name__=='__main__':unittest.main()
