"""Verified native output arrays at the geometry observation-loader seam."""
from pathlib import Path
import sys
import tempfile
import unittest

import numpy as np
from PIL import Image

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from vipe_benchmark.files import file_record


class LoaderTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.valid=np.ones((540,960),bool);self.valid[0,0]=False
        self.labels=np.zeros((540,960),np.int32);self.labels[0,0]=-1;self.labels[2,3]=1
        self.changing=np.zeros((540,960),bool);self.changing[4,5]=True
        rgb=np.full((540,960,3),[11,22,33],np.uint8)
        Image.fromarray(rgb).save(self.root/'rgb.png')
        self.source=dict(identity=dict(branch='reconstruction',camera=1,frame=0,pair_start=None),
            rgb=file_record(self.root/'rgb.png'),valid=self.array('valid',self.valid),
            K=[[200,0,480],[0,200,270],[0,0,1]],grid='undistorted-opencv-integer')
        common=dict(identity=dict(self.source['identity'],pair_start=0),
            source_rgb_sha256=self.source['rgb']['sha256'],K=self.source['K'],grid=self.source['grid'],valid=self.source['valid'])
        static=np.full((540,960),255,np.uint8);static[0,0]=static[2,3]=0
        Image.fromarray(static).save(self.root/'static.png')
        self.segmentation=dict(common,instances=self.array('labels',self.labels),
            semantics={'1':dict(**{'class':'person'},native_class='person',score=.9)},
            semantic_static=file_record(self.root/'static.png'))
        self.motion=dict(common,changing=self.array('changing',self.changing))

    def array(self,name,value):
        path=self.root/(name+'.npy');np.save(path,value,allow_pickle=False);return file_record(path)

    def test_accepted_rgb_instances_and_motion_are_loaded_without_transforming(self):
        from vipe_benchmark.final_render_loaders import load_observation
        observation=load_observation(self.source,self.segmentation,self.motion)
        self.assertEqual(set(observation),{'rgb','valid','labels','changing'})
        self.assertEqual(observation['rgb'][2,3].tolist(),[11,22,33])
        self.assertEqual(observation['labels'][2,3],1)
        self.assertEqual(observation['labels'][0,0],-1)
        self.assertTrue(observation['changing'][4,5])
        self.assertFalse(observation['valid'][0,0])
        self.assertEqual(observation['labels'].dtype,np.int32)
        self.assertEqual(observation['changing'].dtype,np.bool_)

    def test_substituted_native_files_or_row_calibration_are_rejected(self):
        from vipe_benchmark.final_render_loaders import load_observation
        for field,value in [('source_rgb_sha256','wrong'),('K',[[1,0,0],[0,1,0],[0,0,1]]),
                            ('grid','distorted-opencv-integer'),('valid',self.array('other-valid',self.valid))]:
            changed=dict(self.motion);changed[field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'identity/calibration'):
                load_observation(self.source,self.segmentation,changed)
        Path(self.segmentation['instances']['path']).write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'changed native input'):
            load_observation(self.source,self.segmentation,self.motion)

    def test_static_polarity_and_unsafe_instance_casts_are_rejected(self):
        from vipe_benchmark.final_render_loaders import load_observation
        swapped=np.zeros((540,960),np.uint8)
        Image.fromarray(swapped).save(self.root/'swapped.png')
        segmentation=dict(self.segmentation,semantic_static=file_record(self.root/'swapped.png'))
        with self.assertRaisesRegex(ValueError,'semantic static'):
            load_observation(self.source,segmentation,self.motion)
        segmentation=dict(self.segmentation,instances=self.array('cast-labels',self.labels.astype(np.uint8)))
        with self.assertRaisesRegex(ValueError,'int32'):
            load_observation(self.source,segmentation,self.motion)

    def test_invalid_mask_dtype_and_grayscale_rgb_are_not_silently_converted(self):
        from vipe_benchmark.final_render_loaders import load_observation
        motion=dict(self.motion,changing=self.array('uint8-motion',self.changing.astype(np.uint8)))
        with self.assertRaisesRegex(ValueError,'boolean masks'):
            load_observation(self.source,self.segmentation,motion)
        Image.fromarray(np.zeros((540,960),np.uint8)).save(self.root/'gray.png')
        source=dict(self.source,rgb=file_record(self.root/'gray.png'))
        segmentation=dict(self.segmentation,source_rgb_sha256=source['rgb']['sha256'])
        motion=dict(self.motion,source_rgb_sha256=source['rgb']['sha256'])
        with self.assertRaisesRegex(ValueError,'mode/grid'):
            load_observation(source,segmentation,motion)

    def test_metric_depth_preserves_camera_z_metres_without_second_scale(self):
        from vipe_benchmark.final_render_loaders import load_metric_depth
        values=np.full((540,960),8.,np.float32);values[0,0]=np.nan
        path=self.root/'depth.npz';np.savez(path,depth=values,valid=self.valid)
        source=dict(self.source,identity=dict(branch='depth',camera=1,frame=175,pair_start=None),
                    grid='scale-opencv-integer')
        native=dict(camera=1,frame=175,K=source['K'],grid=source['grid'],domain='camera_z_metres',
                    inference_rgb=source['rgb'],prediction=file_record(path))
        loaded=load_metric_depth(source,native)
        self.assertEqual(loaded['depth'][2,3],8.)
        self.assertTrue(np.isnan(loaded['depth'][0,0]))
        self.assertFalse(loaded['valid'][0,0])

    def test_metric_depth_rejects_relative_domains_and_invalid_support(self):
        from vipe_benchmark.final_render_loaders import load_metric_depth
        values=np.full((540,960),8.,np.float32);values[0,0]=np.nan
        path=self.root/'bad-depth.npz';np.savez(path,depth=values,valid=self.valid)
        source=dict(self.source,identity=dict(branch='depth',camera=1,frame=175,pair_start=None),grid='scale-opencv-integer')
        native=dict(camera=1,frame=175,K=source['K'],grid=source['grid'],domain='relative_depth',
            inference_rgb=source['rgb'],prediction=file_record(path))
        with self.assertRaisesRegex(ValueError,'domain differs'):
            load_metric_depth(source,native)
        native['domain']='camera_z_metres'
        values[2,3]=0.;np.savez(path,depth=values,valid=self.valid);native['prediction']=file_record(path)
        with self.assertRaisesRegex(ValueError,'finite positive'):
            load_metric_depth(source,native)

    def test_compressed_depth_cannot_allocate_an_unbounded_native_array(self):
        import zipfile
        from vipe_benchmark.final_render_loaders import load_metric_depth
        path=self.root/'bomb.npz'
        with zipfile.ZipFile(path,'w',compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('depth.npy',b'0'*(65*2**20))
        source=dict(self.source,identity=dict(branch='depth',camera=1,frame=175,pair_start=None),grid='scale-opencv-integer')
        native=dict(camera=1,frame=175,K=source['K'],grid=source['grid'],domain='camera_z_metres',
            inference_rgb=source['rgb'],prediction=file_record(path))
        with self.assertRaisesRegex(ValueError,'expanded native archive limit'):
            load_metric_depth(source,native)

    def test_npy_header_cannot_claim_a_larger_grid_before_decode(self):
        from vipe_benchmark.final_render_loaders import load_observation
        path=self.root/'claimed-large.npy'
        with path.open('wb') as stream:
            np.lib.format.write_array_header_1_0(stream,dict(descr='|b1',fortran_order=False,shape=(10**9,)))
        motion=dict(self.motion,changing=file_record(path))
        with self.assertRaisesRegex(ValueError,'native array header grid/dtype'):
            load_observation(self.source,self.segmentation,motion)

    def selected_request(self):
        import importlib
        from vipe_benchmark import depth_review
        from vipe_benchmark.files import read_json
        review=importlib.import_module('test_vipe_benchmark_depth_review').DepthReviewTests()
        review.setUp();self.addCleanup(review.doCleanups)
        source=dict(self.source,identity=dict(branch='depth',camera=1,frame=175,pair_start=None),
                    grid='scale-opencv-integer')
        inputs=review.record(dict(depth=[source]))
        context=review.record(dict(inputs=inputs))
        values=np.full((540,960),8.,np.float32);values[0,0]=np.nan
        path=self.root/'selected-depth.npz';np.savez(path,depth=values,valid=self.valid)
        row=dict(camera=1,frame=175,domain='camera_z_metres',grid=source['grid'],K=source['K'],
                    inference_rgb=source['rgb'],prediction=file_record(path))
        for name,slot in review.slots.items():
            generation=read_json(slot['evidence']['generation']['path'])
            fit=read_json(generation['scales']['fit']['path']);fit['provenance']['inputs']=inputs
            fit=review.record(fit)
            check=review.record(dict(read_json(generation['scales']['check']['path']),
                                   frozen_fit=fit,provenance=dict(inputs=inputs)))
            generation.update(context=context,inputs=inputs,scales=dict(fit=fit,check=check),rows=[row])
            slot['evidence'].update(generation=review.record(generation),scale=check)
            if name=='D2':slot['evidence'].update(historical_fit=review.record(dict(scale=fit)),
                                                historical_check=review.record(dict(scale=check)))
            if name=='D5':selected_fit,selected_check=fit,check
        package=read_json(review.package['path'])
        package['bindings'].update(inputs=inputs,context=context,
            depth_aggregate_request=review.record(dict(candidates=review.slots)))
        review.package=review.record(package);review.form['package']=review.package
        imported=depth_review.import_review(review.package,review.record(review.form),self.root/'review.json',actual=False)
        depth_review.freeze_decision(imported,self.root/'decision.json',actual=False)
        return dict(record_kind='fixture',depth_candidate='D5',bindings=dict(inputs=inputs,
            D_fit=selected_fit,D_check=selected_check,depth_decision=file_record(self.root/'decision.json')))

    def test_selected_depth_uses_exact_human_frozen_generation_and_never_falls_back(self):
        from vipe_benchmark.final_render_loaders import load_selected_depth
        request=self.selected_request()
        loaded=load_selected_depth(request,1,175)
        self.assertEqual(loaded['depth'][2,3],8.)
        with self.assertRaisesRegex(ValueError,'missing exact selected-depth anchor'):
            load_selected_depth(request,1,0)
        request['depth_candidate']='D7'
        with self.assertRaisesRegex(ValueError,'selected-depth decision'):
            load_selected_depth(request,1,175)


class WorkerDefaultTests(unittest.TestCase):
    def test_default_worker_loader_rejects_unaccepted_arrays_before_matching(self):
        import importlib
        from vipe_benchmark.final_render_geometry import run,GeometryFailure
        fixture=importlib.import_module('test_vipe_benchmark_final_render_geometry').GeometryWorkerTests()
        fixture.setUp();self.addCleanup(fixture.doCleanups)
        class Matcher:
            record_kind='fixture';sample_thresh=.5
            def match(self,*args):
                raise AssertionError('bad observations must never reach matcher')
        with self.assertRaisesRegex(GeometryFailure,'accepted reconstruction grid') as caught:
            run(fixture.request,'QF-B',fixture.root/'default-loader',Matcher())
        self.assertEqual(caught.exception.receipt['artifacts'],[])
        self.assertFalse(caught.exception.receipt['execution_authorized'])


if __name__=='__main__':unittest.main()
