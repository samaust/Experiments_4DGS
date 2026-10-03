"""CPU fixture tests at the selected-depth geometry/initializer worker seam."""
import copy
import importlib
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from vipe_benchmark.files import file_record,object_hash,read_json
from vipe_benchmark.final_render_contract import KEYFRAMES
from vipe_benchmark.final_render_initializer import assemble


class ExtendedInitializerTests(unittest.TestCase):
    def setUp(self):
        self.fixture=importlib.import_module('test_vipe_benchmark_extended_final_render_contract').AdmissionTests()
        self.fixture.setUp()
        self.addCleanup(self.fixture.doCleanups)
        self.request=self.fixture.request
        self.root=self.fixture.base.root
        self.record=self.fixture.record
        self.matrix=np.asarray(self.request['initializer_contract']['normalization']['transform'])
        basis=self.root/'basis.npz'
        np.savez(basis,normalized_positions=np.array([[0,0,0],[0,0,1]],np.float32))
        prior=self.root/'prior.npz'
        np.savez(prior,positions=((np.array([[0,0,0],[0,0,1]])-self.matrix[:3,3])@np.linalg.inv(self.matrix[:3,:3]).T).astype(np.float32))
        inputs=read_json(self.request['bindings']['inputs']['path'])
        origin=self.record('static-origin',dict(schema='basketball-static-initialization/v1',status='prepared',
            source_frame=25,points=2,inputs=[],manifest_sha256=self.request['bindings']['scene_manifest']['sha256'],
            freeze_sha256=inputs['reference_geometry']['freeze']['sha256'],archive_sha256=file_record(prior)['sha256']))
        self.request['initializer_contract'].update(voxel_basis=file_record(basis),
            voxel_basis_source=dict(archive=file_record(prior),receipt=origin))
        self.fixture.rebind_proposal()
        self.width=self.record('width',dict(schema='plan069-final-render-voxel-width/v1',record_kind='fixture',
            rule='half median positive nearest-neighbor distance',width=.5,
            request_sha256=object_hash(self.request),scene=self.request['bindings']['scene_freeze'],
            basis=file_record(basis),source=self.request['initializer_contract']['voxel_basis_source']))

    def geometry(self,arm='QF-B'):
        composition=self.request['compositions'][arm]
        bindings=self.request['bindings']
        neighbors=read_json(bindings[composition['neighbors']]['path'])['records']
        indexed={name:{(r['identity']['camera'],r['identity']['frame'],r['identity']['pair_start']):r
            for r in read_json(bindings[name]['path'])['rows']}
            for name in ('S2',composition['motion'])}
        rows=[]
        for frame in KEYFRAMES:
            for neighbor in neighbors:
                camera=neighbor['reference'];cameras=[camera,*neighbor['neighbors']]
                source_rows={name:[object_hash(indexed[name][c,f,frame]) for c in cameras for f in (frame,frame+1)]
                    for name in indexed}
                physical=np.array([[1,2,3],[3,2,1]],np.float32)
                artifact=self.root/f'edge-{arm}-{frame}-{camera}.npz'
                np.savez(artifact,world_positions=physical,
                    positions=(physical@self.matrix[:3,:3].T+self.matrix[:3,3]).astype(np.float32),
                    colors=np.full((2,3),.5,np.float32),world_velocities=np.array([[0,0,0],[0,-.25,0]],np.float32),
                    velocities=np.array([[0,0,0],[1,0,0]],np.float32),times=np.full((2,1),frame/50,np.float32),
                    durations=np.full((2,1),.2,np.float32),region=np.array([0,1],np.int32),
                    velocity_valid=np.array([False,True]),camera_ids=np.array(cameras))
                rows.extend(dict(pair_start=frame,reference=camera,other=other,artifact=file_record(artifact),
                    source_rows=source_rows) for other in cameras[1:])
        names=('S2','D_fit','D_check','depth_decision',composition['motion'],composition['neighbors'])
        return dict(schema='plan069-final-render-geometry/v1',status='complete',record_kind='fixture',arm=arm,
            request_sha256=object_hash(self.request),composition=composition,scene=bindings['scene_freeze'],rows=rows,
            prerequisites={name:bindings[name] for name in names})

    def test_selected_depth_full_rig_assembly_preserves_rotated_physical_units(self):
        arrays,receipt=assemble(self.request,'QF-B',self.record('geometry',self.geometry()),self.width)
        self.assertEqual(receipt['schema'],'plan069-final-render-assembly-result/v1')
        self.assertEqual(receipt['composition']['depth'],'D5')
        self.assertEqual(receipt['coverage_edges'],810)
        self.assertEqual(len(arrays['positions']),819)
        np.testing.assert_allclose(arrays['positions'][0],[-3,4,9])
        np.testing.assert_array_equal(arrays['velocities'][9],[1,0,0])
        self.assertEqual(receipt['initializer_receipt']['prerequisites']['depth_decision'],
            self.request['bindings']['depth_decision'])
        self.assertFalse(receipt['execution_authorized'])
        self.assertFalse(receipt['native_adapter_qualified'])

    def test_assembled_arrays_reach_native_boundary_with_provenance_ids_bound(self):
        from vipe_benchmark.final_render_adapter import prepare_model_input,validate_model_input
        arrays,receipt=assemble(self.request,'QF-B',self.record('geometry',self.geometry()),self.width)
        data,native=prepare_model_input(self.request,'QF-B',receipt['initializer_receipt'],arrays)
        self.assertEqual(set(data),{'positions','colors','velocities','times','durations'})
        self.assertEqual(native['arrays_sha256'],receipt['arrays_sha256'])
        self.assertEqual(native['sidecar_fields'],['region','velocity_valid','physical_static_id','foreground_observation_id'])
        self.assertEqual(native['sidecar_array_bytes'],17199)
        self.assertEqual(validate_model_input(data,native),native['native_arrays_sha256'])
        self.assertEqual(arrays['physical_static_id'][:9].tolist(),[0]*9)
        self.assertEqual(arrays['foreground_observation_id'][:9].tolist(),[-1]*9)

    def test_all_five_arms_keep_one_depth_and_their_own_motion_neighbor_lineage(self):
        from vipe_benchmark.final_render_adapter import prepare_model_input
        expected={'QF-B':('M0','N0'),'QF-M1':('M1','N0'),'QF-M2':('M2','N0'),
            'QF-N1':('M0','N1'),'QF-N2':('M0','N2')}
        for arm,(motion,neighbors) in expected.items():
            with self.subTest(arm=arm):
                arrays,receipt=assemble(self.request,arm,self.record('geometry-'+arm,self.geometry(arm)),self.width)
                _,native=prepare_model_input(self.request,arm,receipt['initializer_receipt'],arrays)
                self.assertEqual(native['composition'],dict(segmentation='S2',depth='D5',motion=motion,neighbors=neighbors))
                self.assertEqual(set(native['initializer_receipt']['prerequisites']),
                    {'S2','D_fit','D_check','depth_decision',motion,neighbors})

    def test_historical_schema_incomplete_coverage_and_substituted_scene_are_rejected(self):
        geometry=self.geometry()
        cases=[]
        old=copy.deepcopy(geometry);old['schema']='plan067-final-render-geometry/v1';cases.append(old)
        missing=copy.deepcopy(geometry);missing['rows'].pop();cases.append(missing)
        duplicate=copy.deepcopy(geometry);duplicate['rows'].append(duplicate['rows'][0]);cases.append(duplicate)
        wrong=copy.deepcopy(geometry);wrong['rows'][0]['reference']=0;cases.append(wrong)
        stale=copy.deepcopy(geometry);stale['prerequisites']['D4_fit']=stale['prerequisites'].pop('D_fit');cases.append(stale)
        scene=copy.deepcopy(geometry);scene['scene']=self.record('copied-scene',read_json(scene['scene']['path']));cases.append(scene)
        for index,value in enumerate(cases):
            with self.subTest(case=index),self.assertRaises(ValueError):
                assemble(self.request,'QF-B',self.record('invalid-geometry-'+str(index),value),self.width)
        width=read_json(self.width['path']);width['schema']='plan067-final-render-voxel-width/v1'
        with self.assertRaises(ValueError):
            assemble(self.request,'QF-B',self.record('geometry-valid',geometry),self.record('historical-width',width))

    def test_partial_or_rehashed_inconsistent_assembly_ids_are_rejected(self):
        from vipe_benchmark.final_render_adapter import prepare_model_input
        from vipe_benchmark.final_render_contract import initializer_arrays_hash
        arrays,result=assemble(self.request,'QF-B',self.record('geometry',self.geometry()),self.width)
        partial=dict(arrays);partial.pop('physical_static_id')
        with self.assertRaisesRegex(ValueError,'exact native'):
            prepare_model_input(self.request,'QF-B',result['initializer_receipt'],partial)
        for name in ('physical_static_id','foreground_observation_id'):
            changed={key:value.copy() for key,value in arrays.items()};changed[name][0]=-2
            receipt=dict(result['initializer_receipt'],arrays_sha256=initializer_arrays_hash(changed))
            with self.subTest(field=name),self.assertRaisesRegex(ValueError,'provenance IDs'):
                prepare_model_input(self.request,'QF-B',receipt,changed)


if __name__=='__main__':
    unittest.main()
