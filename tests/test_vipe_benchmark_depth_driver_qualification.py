"""D6 driver qualification authority, resource scope and retained result seams."""
from pathlib import Path
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from vipe_benchmark.config import load
from vipe_benchmark.depth_driver_qualification import JOB, KIND, validate_request, validate_result
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.ledger import Ledger


def fixture(root, kind="fixture"):
    def save(name, value):
        path = root / name
        write_json(path, value)
        return file_record(path)
    worker = save('worker.py', dict(fixture='never executed'))
    archive = save('source.zip', dict(fixture='never imported'))
    setup = save('setup.json', dict(candidate='D6', status='complete', record_kind=kind,
        source_archive=archive, source_tree=[], python_executable=sys.executable))
    source = save('source-review.json', dict(schema='plan069-depth-source-review/v1',candidate='D6',status='passed',
        reviewer='independent fixture reviewer',local_sources=[worker],source_archive=archive,source_files=[]))
    proposal = dict(candidate='D6',job_id=JOB,qualification_kind=KIND,max_attempts=1,seconds=180,
        device_bytes=2*1024**3,artifact_bytes=64*1024**2,downloads=0,inference=False,benchmarks=False,strict_cpu_loads=2,setup=setup)
    review = save('review.json', dict(schema='plan069-D6-driver-qualification-review/v1',status='REVIEW',proposal=proposal))
    approval = save('DO.json',dict(schema='plan069-D6-driver-qualification-authorization/v1',status='DO',review=review,proposal_sha256=object_hash(proposal)))
    request_path=root/'request.json'
    output=root/'qualification'
    request=dict(schema='plan069-D6-driver-qualification-request/v1',record_kind=kind,candidate='D6',job_id=JOB,
        review=review,authorization=approval,source_review=source,setup=setup,worker=worker,
        executable=file_record(Path(sys.executable).resolve()),interpreter_invocation=sys.executable,
        setup_request=save('setup-request.json',{}),setup_dispatch=save('setup-dispatch.json',{}),
        cpu_validation=save('CPU.json',dict(schema='plan069-delta-cpu-test-capture/v1',record_kind=kind,passed=True,
            within_wall_limit=True,source_bytes_unchanged=True,sources_before=[worker],sources_after=[worker])),root=str(root),
        ledger_path=str(root/'ledger.jsonl'),output=str(output),command=[sys.executable,'-I','-B',worker['path'],
            'driver-child','--request',str(request_path),'--output',str(output)])
    write_json(request_path,request)
    return file_record(request_path),request,[worker]


def result_fixture(record, request, sources):
    output=Path(request['output']);output.mkdir(exist_ok=True)
    dependency=output/'installed-dependencies.json'
    write_json(dependency,dict(schema='plan069-depth-installed-dependencies/v1',candidate='D6',setup=request['setup']))
    return dict(schema='plan069-D6-driver-qualification-result/v1',candidate='D6',record_kind=request['record_kind'],status='passed',
        qualification_kind=KIND,request=record,setup=request['setup'],strict_cpu_loads=2,all_parameters_cpu=True,
        all_buffers_cpu=True,cuda_initialized=True,inference=False,forward_calls=0,benchmark_calls=0,
        kernel_launches=0,gpu_model_load='not_performed',tensor_peak_allocated_bytes=0,local_sources=sources,
        method=request['worker'],python_executable=request['interpreter_invocation'],python=file_record(request['interpreter_invocation']),
        dependency_manifest=file_record(dependency))


class DriverQualificationTests(unittest.TestCase):
    def test_integrated_cpu_capture_accepts_exact_pass_and_rejects_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);record,request,sources=fixture(root,'actual')
            packet=root/'full-review.json'
            head='a'*40
            write_json(packet,dict(schema='plan069-final-full-cpu-review/v1',status='REVIEW',
                base_head=head,checkout=str(root),max_seconds=1200,overlay=str(root/'overlay'),output=str(root/'full')))
            cpu=read_json(request['cpu_validation']['path'])
            cpu.update(schema='plan069-integrated-cpu-test-capture/v1',head=head,head_after=head,
                head_unchanged=True,environment_bytes_unchanged=True,review_request=file_record(packet),
                checkout=str(root),max_seconds=1200,elapsed_seconds=100,
                environment=dict(CUDA_VISIBLE_DEVICES='',VIPE_CPU_VALIDATION='1',
                    PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',
                    OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',
                    NUMEXPR_NUM_THREADS='1',MPLBACKEND='Agg',
                    PYTHONPATH=f'{root}/overlay:{root}/scripts:{root}/tests',
                    S1_VALIDATION_RUN_DIRECTORY=str(root/'full'/'disposable-results'),
                    MPLCONFIGDIR=str(root/'full'/'matplotlib')),
                commands=[dict(name=name,returncode=0,timed_out=False,cleanup=dict(
                    confirmed_no_surviving_observed_processes=True,
                    surviving_observed_owned_processes=[])) for name in ('pytest','unittest')])
            def check(value):
                Path(request['cpu_validation']['path']).write_text(json.dumps(value))
                request['cpu_validation']=file_record(request['cpu_validation']['path'])
                Path(record['path']).write_text(json.dumps(request))
                return validate_request(file_record(record['path']),current_sources=sources)
            self.assertEqual(check(cpu)[0]['record_kind'],'actual')
            for key,value in (('passed',False),('head_after','b'*40),('head','b'*40),
                              ('head_unchanged',False),('environment_bytes_unchanged',False)):
                with self.subTest(key=key),self.assertRaises(ValueError):check(dict(cpu,**{key:value}))
            with self.assertRaises(ValueError):
                check(dict(cpu,environment=dict(cpu['environment'],CUDA_VISIBLE_DEVICES='0')))
            with self.assertRaises(ValueError):
                check(dict(cpu,environment=dict(cpu['environment'],PYTHONPATH='/unreviewed')))
            commands=[dict(row) for row in cpu['commands']];commands[0]['returncode']=1
            with self.assertRaises(ValueError):check(dict(cpu,commands=commands))

    def test_review_without_explicit_do_cannot_allocate_gpu(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);record,request,sources=fixture(root)
            bad=read_json(request['authorization']['path']);bad['status']='REVIEW'
            Path(request['authorization']['path']).unlink();write_json(request['authorization']['path'],bad)
            request['authorization']=file_record(request['authorization']['path'])
            Path(record['path']).unlink();write_json(record['path'],request);record=file_record(record['path'])
            ledger=Ledger(root/'ledger.jsonl',load())
            with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources):
                with self.assertRaisesRegex(ValueError,'approved.*allocation'):
                    ledger.authorize_depth_driver_qualification(record)
            self.assertEqual(ledger.events(),[])

    def test_qualification_slot_is_one_use_and_does_not_consume_map_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);record,request,sources=fixture(root);ledger=Ledger(root/'ledger.jsonl',load())
            with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), \
                 patch('vipe_benchmark.execution.resources',return_value=dict(gpu_pids=[],device_bytes=0,artifact_bytes=0,download_bytes=0)):
                ledger.authorize_depth_driver_qualification(record)
                reserved=ledger.reserve(JOB,request['command'],dict(request=record))
                self.assertEqual(reserved['resource'],'gpu');self.assertEqual(reserved['seconds'],180)
                ledger.finish(JOB,'failed',1,cleanup_confirmed=True)
                with self.assertRaisesRegex(ValueError,'already.*consumed'):
                    ledger.authorize_depth_driver_qualification(record)
                with self.assertRaisesRegex(ValueError,'already consumed'):
                    ledger.reserve(JOB,request['command'],dict(request=record))
            self.assertNotIn('plan069-D6-maps-001',ledger.states())
            self.assertFalse(any(event['event']=='depth_attempt_authorized' for event in ledger.events()))

    def test_gpu_owner_or_scope_change_rejects_before_reservation(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);record,request,sources=fixture(root);ledger=Ledger(root/'ledger.jsonl',load())
            with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), \
                 patch('vipe_benchmark.execution.resources',return_value=dict(gpu_pids=[123],device_bytes=0,artifact_bytes=0,download_bytes=0)):
                with self.assertRaisesRegex(ValueError,'GPU owner active'):
                    ledger.authorize_depth_driver_qualification(record)
            self.assertEqual(ledger.events(),[])
            request['command']=['changed-worker']
            Path(record['path']).unlink();write_json(record['path'],request)
            with self.assertRaisesRegex(ValueError,'command binding'):validate_request(file_record(record['path']))

    def test_finished_scope_keeps_historical_helpers_and_rejects_changed_evidence(self):
        from vipe_benchmark.depth_driver_qualification import qualification_exception
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);record,request,sources=fixture(root);ledger=Ledger(root/'ledger.jsonl',load())
            result=result_fixture(record,request,sources)
            result_path=root/'result.json';write_json(result_path,result);result_record=file_record(result_path)
            with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), \
                 patch('vipe_benchmark.execution.resources',return_value=dict(gpu_pids=[],device_bytes=0,artifact_bytes=0,download_bytes=0)):
                ledger.authorize_depth_driver_qualification(record)
                ledger.reserve(JOB,request['command'],dict(request=record))
                finish=ledger.finish(JOB,'complete',2,cleanup_confirmed=True,result=result_record,peak=dict(device_bytes=0))
            finish_path=root/'finish.json';write_json(finish_path,finish)
            runtime=dict(record_kind=request['record_kind'],candidate='D6',qualification_kind=KIND,setup=request['setup'],local_sources=sources,
                driver_qualification=dict(request=record,result=result_record,finish=file_record(finish_path),ledger_path=str(ledger.path)))
            self.assertEqual(qualification_exception(runtime),runtime['driver_qualification'])
            # A later helper edit does not rewrite a completed qualification's retained metadata.
            Path(request['worker']['path']).write_text('later helper bytes')
            qualification_exception(runtime)
            # The receipt itself is immutable and must remain exact.
            result_path.write_text('{}')
            with self.assertRaises(ValueError):qualification_exception(runtime)

    def test_unchecked_note_cannot_mint_qualification_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger=Ledger(Path(directory)/'ledger.jsonl',load())
            with self.assertRaisesRegex(ValueError,'checked ledger transition'):
                ledger.note('depth_driver_qualification_authorized',job_id=JOB)
            self.assertEqual(ledger.events(),[])

    def test_two_cpu_loads_with_real_driver_metadata_are_distinct_from_inference(self):
        with tempfile.TemporaryDirectory() as directory:
            record,request,sources=fixture(Path(directory))
            result=result_fixture(record,request,sources)
            validate_result(result,record,cleanup_confirmed=True)
            for key,value in [('cuda_initialized',False),('strict_cpu_loads',1),('inference',True),
                    ('forward_calls',1),('benchmark_calls',1),('kernel_launches',1),('tensor_peak_allocated_bytes',4),('local_sources',[]),('method',{}),('python_executable','changed')]:
                changed=dict(result,**{key:value})
                with self.subTest(key=key),self.assertRaises(ValueError):
                    validate_result(changed,record,cleanup_confirmed=True)
            with self.assertRaisesRegex(ValueError,'scope'):
                validate_result(result,record,cleanup_confirmed=False)


class DriverDispatchTests(unittest.TestCase):
    def test_dispatch_persists_ledger_finish_instead_of_supervise_worker_return(self):
        import basketball_vipe_depth_driver_qualification as driver
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);record,request,sources=fixture(root,kind='actual')
            def supervised(ledger,job,command,output,**kwargs):
                ledger.reserve(job,command,kwargs['evidence'])
                result=result_fixture(record,request,sources)
                write_json(output/'result.json',result)
                ledger.finish(job,'complete',1,cleanup_confirmed=True,result=file_record(output/'result.json'),peak=dict(device_bytes=0))
                return result
            with patch.dict(driver.os.environ,{},clear=True), \
                 patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), \
                 patch('vipe_benchmark.execution.resources',return_value=dict(gpu_pids=[],device_bytes=0,artifact_bytes=0,download_bytes=0)), \
                 patch.object(driver,'supervise',side_effect=supervised):
                finished=driver.dispatch(record['path'])
            preserved=read_json(Path(request['output'])/'finish.json')
            self.assertEqual(preserved['event'],'finish')
            self.assertEqual(preserved,finished)
            self.assertEqual(preserved['result'],file_record(Path(request['output'])/'result.json'))


class DirectBenchmarkScopeTests(unittest.TestCase):
    def test_direct_benchmarks_and_kernel_launch_are_rejected_and_restored(self):
        import importlib.util
        from types import SimpleNamespace
        path=Path(__file__).resolve().parents[1]/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-004/producer.py'
        spec=importlib.util.spec_from_file_location('driver_producer',path)
        producer=importlib.util.module_from_spec(spec);spec.loader.exec_module(producer)
        def unchanged(*args,**kwargs):return 'original'
        model=type('Model',(),{'_call_impl':unchanged})
        autotuner=type('Autotuner',(),{'_bench':unchanged})
        kernel=type('Kernel',(),{'run':unchanged})
        torch=SimpleNamespace(nn=SimpleNamespace(Module=model))
        triton=SimpleNamespace(runtime=SimpleNamespace(Autotuner=autotuner,jit=SimpleNamespace(JITFunction=kernel)),
            testing=SimpleNamespace(do_bench=unchanged,do_bench_cudagraph=unchanged))
        with producer.no_inference_guards(torch,triton) as calls:
            for callback in (triton.testing.do_bench,triton.testing.do_bench_cudagraph):
                with self.assertRaisesRegex(PermissionError,'benchmark_calls'):callback(lambda:None)
            with self.assertRaisesRegex(PermissionError,'kernel_launches'):kernel().run()
            with self.assertRaisesRegex(PermissionError,'forward_calls'):model()._call_impl()
            self.assertEqual(calls,dict(forward_calls=1,benchmark_calls=2,kernel_launches=1))
        self.assertEqual(triton.testing.do_bench(lambda:None),'original')
        self.assertEqual(kernel().run(),'original')


if __name__=='__main__':unittest.main()
