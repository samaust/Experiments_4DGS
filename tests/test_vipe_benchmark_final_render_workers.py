"""CPU fake runtime at the agreed final-render worker request/result seam."""
import importlib
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import os

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'scripts'))
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.final_render_contract import initializer_arrays_hash


class FakeFreeTimeRuntime:
    record_kind = 'fixture'

    def __init__(self):
        self.iteration = 0
        self.value = 0
        self.closed = False
        self.is_fresh = True

    def prepare_training(self, request, arm, data, receipt, provenance):
        self.is_fresh = False
        self.provenance = provenance

    def training_step(self, iteration):
        if iteration != self.iteration:
            raise ValueError('nonsequential native update')
        self.iteration += 1
        self.value += 2
        return {'loss': 1.}

    def save_checkpoint(self, path, iteration):
        write_json(path, dict(iteration=iteration, provenance=self.provenance,
            parameters=self.value, optimizer_steps=self.iteration))

    def checkpoint_metadata(self, path):
        state = read_json(path)
        return dict(iteration=state['iteration'], provenance=state['provenance'])

    def resource_usage(self):
        return dict(peak_device_bytes=0, cpu_workers_used=1)

    def reload_checkpoint(self, checkpoint, request, arm, data, receipt, provenance, restored_path):
        self.is_fresh = False
        state = read_json(checkpoint['path'])
        self.iteration = state['iteration']; self.value = state['parameters']
        self.provenance = provenance
        write_json(restored_path,state)
        return dict(iteration=self.iteration,provenance=state['provenance'],
            restored_state_equal=True)

    def render_frame(self, camera, frame):
        return np.full((540,960,3),[camera/30,frame/49,.5],np.float32)

    def close(self):
        self.closed = True


class WorkerTests(unittest.TestCase):
    def setUp(self):
        self.pipeline = importlib.import_module('test_vipe_benchmark_final_render_pipeline').PipelineTests()
        self.pipeline.setUp(); self.addCleanup(self.pipeline.doCleanups)
        self.request = self.pipeline.request
        self.root = self.pipeline.fixture.base.root
        self.record = self.pipeline.record
        arrays = dict(positions=np.array([[0,0,1],[1,0,1],[0,1,1],[1,1,1]],np.float32),
            colors=np.full((4,3),.5,np.float32), velocities=np.zeros((4,3),np.float32),
            times=np.zeros((4,1),np.float32), durations=np.full((4,1),.2,np.float32),
            region=np.zeros(4,np.int32), velocity_valid=np.zeros(4,bool))
        archive = self.root/'initializer.npz'; np.savez(archive, **arrays)
        names = ('S2','D_fit','D_check','depth_decision','M0','N0')
        receipt = dict(self.request['initializer_contract'], arm='QF-B',
            composition=self.request['compositions']['QF-B'], arrays_sha256=initializer_arrays_hash(arrays),
            scene_manifest=self.request['bindings']['scene_manifest'],
            prerequisites={name:self.request['bindings'][name] for name in names})
        self.initializer = self.record('prepared-initializer',dict(
            schema='plan069-final-render-prepared-initializer/v1',record_kind='fixture',arm='QF-B',
            request_sha256=object_hash(self.request),archive=file_record(archive),initializer_receipt=receipt,
            execution_authorized=False,native_adapter_qualified=False))
        parent = read_json(self.pipeline.records['initializer']['path'])
        parent['artifacts'] = [self.initializer,file_record(archive)]
        parent['artifact_bytes'] = sum(r['bytes'] for r in parent['artifacts'])
        self.parent = self.record('published-initializer-result',parent)

    def test_training_returns_bound_exact_5000_endpoint_through_worker_result_seam(self):
        from vipe_benchmark.final_render_workers import train
        from vipe_benchmark.final_render_pipeline import validate_worker_result
        runtime = FakeFreeTimeRuntime()
        result = train(self.request,'QF-B',self.parent,self.initializer,self.root/'training',runtime)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['completed_iterations'],5000)
        state = read_json(result['checkpoint']['path'])
        self.assertEqual(state['parameters'],10000)
        self.assertEqual(state['optimizer_steps'],5000)
        self.assertEqual(state['provenance']['initializer'],self.initializer)
        self.assertTrue(runtime.closed)
        self.assertEqual(validate_worker_result(self.request,'QF-B','train',result),result)

    def test_deadline_reserve_stops_updates_and_preserves_partial_evidence(self):
        from vipe_benchmark.final_render_workers import train
        runtime = FakeFreeTimeRuntime()
        ticks = iter([0.,0.,3451.])
        output = self.root/'deadline-training'
        with self.assertRaisesRegex(RuntimeError,'deadline'):
            train(self.request,'QF-B',self.parent,self.initializer,output,runtime,
                clock=lambda:next(ticks,3451.))
        self.assertEqual(runtime.iteration,0)
        self.assertTrue(runtime.closed)
        failure = read_json(output/'failure.json')
        self.assertEqual(failure['status'],'failed')
        self.assertEqual(failure['completed_iterations'],0)
        self.assertFalse((output/'result.json').exists())

    def test_excessive_runtime_memory_stops_before_any_native_update(self):
        from vipe_benchmark.final_render_workers import train
        runtime = FakeFreeTimeRuntime()
        runtime.resource_usage = lambda:dict(peak_device_bytes=23*2**30,cpu_workers_used=1)
        output = self.root/'excessive-memory'
        with self.assertRaisesRegex(ValueError,'peak_device_bytes'):
            train(self.request,'QF-B',self.parent,self.initializer,output,runtime)
        self.assertEqual(runtime.iteration,0)
        self.assertTrue(runtime.closed)
        self.assertTrue((output/'failure.json').exists())

    def test_fresh_reload_renders_exact_200_matched_frames_with_frozen_png_conversion(self):
        from PIL import Image
        from vipe_benchmark.final_render_workers import train, render
        from vipe_benchmark.final_render_pipeline import validate_worker_result
        training = train(self.request,'QF-B',self.parent,self.initializer,
            self.root/'training',FakeFreeTimeRuntime())
        parent = file_record(self.root/'training/result.json')
        runtime = FakeFreeTimeRuntime()
        result = render(self.request,'QF-B',parent,self.initializer,self.root/'render',runtime)
        self.assertEqual(result['status'],'complete')
        self.assertEqual(result['checkpoint'],training['checkpoint'])
        self.assertEqual(len(result['rendered_frames']),200)
        self.assertTrue(runtime.closed)
        first = Image.open(result['rendered_frames'][0]['rgb']['path'])
        last = Image.open(result['rendered_frames'][-1]['rgb']['path'])
        self.assertEqual(first.size,(960,540))
        self.assertEqual(first.getpixel((0,0)),(0,0,128))
        self.assertEqual(last.getpixel((0,0)),(255,255,128))
        first.close();last.close()
        self.assertGreaterEqual(result['artifact_bytes'],sum(p.stat().st_size for p in (self.root/'render').iterdir()))
        self.assertEqual(validate_worker_result(self.request,'QF-B','render',result),result)

    def test_cleanup_failure_preserves_checkpoint_without_passing_receipt(self):
        from vipe_benchmark.final_render_workers import train
        runtime = FakeFreeTimeRuntime()
        def failed_cleanup():
            raise RuntimeError('cleanup did not complete')
        runtime.close = failed_cleanup
        output = self.root/'failed-cleanup'
        with self.assertRaisesRegex(RuntimeError,'cleanup'):
            train(self.request,'QF-B',self.parent,self.initializer,output,runtime)
        self.assertTrue((output/'checkpoint-005000.pt').exists())
        self.assertFalse((output/'result.json').exists())
        failure = read_json(output/'failure.json')
        self.assertFalse(failure['cleanup_confirmed'])

    def test_native_camera_keeps_pixel_centers_and_full_rotated_normalization(self):
        from vipe_benchmark.final_render_native import prepare_camera
        camera = prepare_camera(self.request,0,45)
        np.testing.assert_allclose(camera['camtoworld'],[[0,-1,0,1],[1,0,0,2],[0,0,1,3],[0,0,0,1]])
        np.testing.assert_allclose(camera['K'],[[2,0,1.5],[0,2,1.5],[0,0,1]])
        self.assertEqual(camera['time'],.9)
        self.assertEqual(camera['resolution'],[960,540])

    def test_native_runtime_cannot_accept_a_fixture_as_actual_input(self):
        from vipe_benchmark.final_render_native import NativeFreeTimeRuntime
        with self.assertRaisesRegex(ValueError,'actual'):
            NativeFreeTimeRuntime(self.request,'QF-B',self.root/'checkout')

    def test_runtime_cannot_mutate_the_expected_checkpoint_provenance(self):
        from vipe_benchmark.final_render_workers import train
        runtime = FakeFreeTimeRuntime()
        original_step = runtime.training_step
        def mutate_provenance(iteration):
            metrics = original_step(iteration)
            runtime.provenance['arm'] = 'QF-N2'
            return metrics
        runtime.training_step = mutate_provenance
        output = self.root/'mutated-provenance'
        with self.assertRaisesRegex(ValueError,'provenance'):
            train(self.request,'QF-B',self.parent,self.initializer,output,runtime)
        self.assertTrue(runtime.closed)
        self.assertFalse((output/'result.json').exists())

    def test_partial_runtime_failure_is_preserved_and_cleanup_runs(self):
        from vipe_benchmark.final_render_workers import train
        runtime = FakeFreeTimeRuntime()
        output = self.root/'partial-failure'
        original = runtime.training_step
        def fail_second_update(iteration):
            if iteration == 1:
                write_json(output/'partial.json',{'completed_update':1})
                raise RuntimeError('synthetic model exception')
            return original(iteration)
        runtime.training_step = fail_second_update
        with self.assertRaisesRegex(RuntimeError,'synthetic model exception'):
            train(self.request,'QF-B',self.parent,self.initializer,output,runtime)
        self.assertTrue(runtime.closed)
        failure = read_json(output/'failure.json')
        self.assertEqual(failure['completed_iterations'],1)
        self.assertTrue(failure['cleanup_confirmed'])
        self.assertEqual(failure['artifacts'],[file_record(output/'partial.json')])

    def test_actual_or_reused_runtime_and_unpublished_initializer_stop_before_output(self):
        from vipe_benchmark.final_render_workers import train
        cases = [(dict(self.request,record_kind='actual'),FakeFreeTimeRuntime(),self.initializer),
            (self.request,FakeFreeTimeRuntime(),self.record('copied-initializer',read_json(self.initializer['path'])))]
        used = FakeFreeTimeRuntime();used.is_fresh=False
        cases.append((self.request,used,self.initializer))
        native = FakeFreeTimeRuntime();native.record_kind='actual'
        cases.append((self.request,native,self.initializer))
        for i,(request,runtime,initializer) in enumerate(cases):
            output = self.root/f'rejected-{i}'
            with self.subTest(i=i),self.assertRaises(ValueError):
                train(request,'QF-B',self.parent,initializer,output,runtime)
            self.assertFalse(output.exists())
            self.assertEqual(runtime.iteration,0)

    def test_changed_archive_and_failed_predecessor_stop_before_initialization(self):
        from vipe_benchmark.final_render_workers import train
        parent = read_json(self.parent['path']);parent.update(status='failed',reason='initializer rejected')
        failed = self.record('failed-initializer',parent)
        with self.assertRaisesRegex(ValueError,'complete predecessor'):
            train(self.request,'QF-B',failed,self.initializer,self.root/'blocked',FakeFreeTimeRuntime())
        bundle = read_json(self.initializer['path']);Path(bundle['archive']['path']).write_bytes(b'changed')
        with self.assertRaises(ValueError):
            train(self.request,'QF-B',self.parent,self.initializer,self.root/'changed',FakeFreeTimeRuntime())

    def test_wrong_restored_state_stops_before_any_png(self):
        from vipe_benchmark.final_render_workers import train, render
        train(self.request,'QF-B',self.parent,self.initializer,self.root/'training',FakeFreeTimeRuntime())
        parent = file_record(self.root/'training/result.json')
        runtime = FakeFreeTimeRuntime();original = runtime.reload_checkpoint
        def incorrect_reload(*args):
            result = original(*args);result['restored_state_equal']=False
            return result
        runtime.reload_checkpoint = incorrect_reload
        output = self.root/'failed-render'
        with self.assertRaisesRegex(ValueError,'restoration differs'):
            render(self.request,'QF-B',parent,self.initializer,output,runtime)
        self.assertTrue(runtime.closed)
        self.assertEqual(list(output.glob('*.png')),[])
        self.assertTrue((output/'restored-checkpoint.pt').exists())
        self.assertFalse((output/'result.json').exists())

    def test_nan_loss_and_backwards_clock_cannot_complete(self):
        from vipe_benchmark.final_render_workers import train
        for kind in ('loss','clock'):
            runtime = FakeFreeTimeRuntime();kwargs={}
            if kind == 'loss':
                runtime.training_step=lambda _:dict(loss=float('nan'))
            else:
                ticks=iter([2.,1.]);kwargs['clock']=lambda:next(ticks,1.)
            output=self.root/('bad-'+kind)
            with self.subTest(kind=kind),self.assertRaises(ValueError):
                train(self.request,'QF-B',self.parent,self.initializer,output,runtime,**kwargs)
            self.assertTrue(runtime.closed)
            self.assertFalse((output/'result.json').exists())

    def test_checkpoint_endpoint_must_be_integer(self):
        from vipe_benchmark.final_render_workers import train
        runtime=FakeFreeTimeRuntime();original=runtime.checkpoint_metadata
        def float_endpoint(path):
            metadata=original(path);metadata['iteration']=5000.
            return metadata
        runtime.checkpoint_metadata=float_endpoint
        with self.assertRaisesRegex(ValueError,'endpoint'):
            train(self.request,'QF-B',self.parent,self.initializer,self.root/'float-endpoint',runtime)

    def test_missing_restored_snapshot_cannot_be_replaced_by_a_passing_claim(self):
        from vipe_benchmark.final_render_workers import train,render
        train(self.request,'QF-B',self.parent,self.initializer,self.root/'training',FakeFreeTimeRuntime())
        runtime=FakeFreeTimeRuntime();original=runtime.reload_checkpoint
        def omitted_snapshot(checkpoint,request,arm,data,receipt,provenance,path):
            result=original(checkpoint,request,arm,data,receipt,provenance,path)
            path.unlink()
            return result
        runtime.reload_checkpoint=omitted_snapshot
        output=self.root/'missing-restore'
        with self.assertRaises(FileNotFoundError):
            render(self.request,'QF-B',file_record(self.root/'training/result.json'),self.initializer,output,runtime)
        self.assertEqual(list(output.glob('*.png')),[])
        self.assertTrue(runtime.closed)

    def test_interrupt_closes_runtime_and_preserves_failed_disposition(self):
        from vipe_benchmark.final_render_workers import train
        runtime=FakeFreeTimeRuntime()
        def interrupted_step(_):
            raise KeyboardInterrupt('synthetic interruption')
        runtime.training_step=interrupted_step
        output=self.root/'interrupted'
        with self.assertRaises(KeyboardInterrupt):
            train(self.request,'QF-B',self.parent,self.initializer,output,runtime)
        self.assertTrue(runtime.closed)
        self.assertTrue(read_json(output/'failure.json')['cleanup_confirmed'])

    def test_terminal_publication_error_keeps_checkpoint_and_failure_evidence(self):
        from vipe_benchmark.final_render_workers import train
        runtime=FakeFreeTimeRuntime();output=self.root/'publication-failure'
        link=os.link
        def fail_result_link(source,destination,*args,**kwargs):
            if Path(destination).name == 'result.json':
                raise ValueError('synthetic terminal publication failure')
            return link(source,destination,*args,**kwargs)
        with patch('os.link',side_effect=fail_result_link):
            with self.assertRaisesRegex(ValueError,'terminal publication') as raised:
                train(self.request,'QF-B',self.parent,self.initializer,output,runtime)
        self.assertTrue(runtime.closed)
        self.assertTrue((output/'checkpoint-005000.pt').exists())
        self.assertTrue(read_json(output/'failure.json')['cleanup_confirmed'])
        self.assertEqual(raised.exception.worker_failure['completed_iterations'],5000)

    def test_published_result_past_deadline_cannot_advance_rendering(self):
        from vipe_benchmark.final_render_workers import train,render
        from vipe_benchmark.final_render_pipeline import validate_worker_result
        runtime=FakeFreeTimeRuntime();now=[0.];output=self.root/'late-publication'
        link=os.link
        def late_result_link(source,destination,*args,**kwargs):
            result=link(source,destination,*args,**kwargs)
            if Path(destination).name == 'result.json':
                now[0]=3601.
            return result
        with patch('os.link',side_effect=late_result_link):
            with self.assertRaisesRegex(RuntimeError,'deadline'):
                train(self.request,'QF-B',self.parent,self.initializer,output,runtime,clock=lambda:now[0])
        self.assertTrue((output/'result.json').exists())
        self.assertFalse((output/'completion.json').exists())
        self.assertEqual(read_json(output/'failure.json')['elapsed_seconds'],3601.)
        with self.assertRaisesRegex(ValueError,'publication failed'):
            validate_worker_result(self.request,'QF-B','train',read_json(output/'result.json'))
        render_output=self.root/'rejected-render'
        with self.assertRaisesRegex(ValueError,'publication failed'):
            render(self.request,'QF-B',file_record(output/'result.json'),self.initializer,
                render_output,FakeFreeTimeRuntime())
        self.assertFalse(render_output.exists())

    def test_deadline_during_terminal_validation_rejects_completion(self):
        from vipe_benchmark.final_render_workers import train
        runtime=FakeFreeTimeRuntime();now=[0.];output=self.root/'terminal-deadline'
        open_file=Path.open
        def advance_clock(path,*args,**kwargs):
            if str(path) == self.parent['path'] and runtime.closed:
                now[0]=3601.
            return open_file(path,*args,**kwargs)
        with patch.object(Path,'open',advance_clock):
            with self.assertRaisesRegex(RuntimeError,'deadline'):
                train(self.request,'QF-B',self.parent,self.initializer,output,runtime,clock=lambda:now[0])
        self.assertFalse((output/'result.json').exists())
        self.assertTrue(read_json(output/'failure.json')['cleanup_confirmed'])


if __name__ == '__main__':
    unittest.main()
