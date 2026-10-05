"""CPU fakes validate qualification005 dispatcher supervision and clean finish."""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock,patch
from vipe_benchmark.config import ROOT
from vipe_benchmark.depth_admission import local_source_records
from vipe_benchmark.files import file_record,write_json

JOB='plan069-D6-driver-qualification-005'


class RecoveryQualificationDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.path=self.root/'request.json';write_json(self.path,{'fixture':'never executed'})
        self.record=file_record(self.path);self.output=self.root/'jobs'/JOB
        self.sources=[{'fixture_source':True}]
        self.request=dict(record_kind='actual',ledger_path=str(self.root/'ledger.jsonl'),output=str(self.output),command=['fixture worker'],triton_cache={'fixture_cache':True},job_id=JOB)
        self.cache_validator=Mock()
        self.proposal=dict(seconds=180,cleanup_seconds=30,device_bytes=2*1024**3,artifact_bytes=64*1024**2)
        self.validator=Mock(return_value=(self.request,self.proposal));self.result_validator=Mock()
        self.authority=SimpleNamespace(JOB=JOB,ATTEMPTS={JOB:{}},validate_request=self.validator,validate_result=self.result_validator,reservation_evidence=lambda record,request:dict(request=record))
        self.states={};self.ledger=Mock();self.ledger.states.side_effect=lambda:self.states
        self.extra_log_bytes=0;self.worker_failure=False;self.finish_changes={};self.sampler=Mock(return_value=dict(device_bytes=0,gpu_pids=[],download_bytes=0,artifact_bytes=0))
        spec=importlib.util.spec_from_file_location('driver_recovery_dispatch',ROOT/'scripts/basketball_vipe_depth_driver_qualification_triton_cache.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)

    def supervisor(self,ledger,job,command,output,**kwargs):
        self.assertEqual(kwargs['cleanup_reserve_seconds'],30)
        self.assertEqual(kwargs['seconds_limit'],180)
        self.assertEqual(kwargs['cpu_workers_limit'],7)
        self.assertEqual(kwargs['evidence'],dict(request=self.record))
        if self.extra_log_bytes:
            output.parent.mkdir(parents=True,exist_ok=True);output.with_suffix('.log').write_bytes(b'x'*self.extra_log_bytes)
        kwargs['sample_resources']()
        output.mkdir(parents=True);output.with_suffix('.syscalls.log').write_text('fixture traced syscall')
        write_json(output/'worker-result.json',{'fixture_only':True,'trace_path':str(output.with_suffix('.syscalls.log'))})
        if self.worker_failure:
            self.states[JOB]=dict(event='finish',status='failed',cleanup_confirmed=True,cleanup_uncertain=False,surviving_pids=[])
            raise RuntimeError('fixture worker failed')
        kwargs['validate_result'](output)
        finish=dict(event='finish',status='complete',result=file_record(output/'result.json'),cleanup_confirmed=True,
            cleanup_uncertain=False,surviving_pids=[],deadline_exceeded=False)
        finish.update(self.finish_changes);self.states[JOB]=finish
        return finish

    def dispatch(self):
        with patch.dict(sys.modules,{'vipe_benchmark.depth_driver_qualification_triton_cache':self.authority}), \
                patch.dict(os.environ,{},clear=True),patch.object(self.module,'Ledger',return_value=self.ledger), \
                patch.object(self.module,'resources',self.sampler),patch.object(self.module,'supervise',side_effect=self.supervisor), \
                patch('vipe_benchmark.depth_admission.local_source_records',return_value=self.sources), \
                patch('vipe_benchmark.triton_helper_cache.validate_binding',self.cache_validator):
            return self.module.dispatch(self.path)

    def test_exact_supervision_uses_cleanup_reserve_and_revalidates_clean_finish(self):
        self.assertEqual(self.dispatch()['status'],'complete')
        self.validator.assert_called_once_with(self.record,current_sources=self.sources)
        self.ledger.authorize_depth_driver_qualification_triton_cache.assert_called_once_with(self.record)
        self.assertTrue((self.output/'finish.json').exists())
        self.assertEqual(self.result_validator.call_count,2)
        from vipe_benchmark.files import read_json
        result=read_json(self.output/'result.json')
        self.assertEqual(result['trace'],file_record(self.output.with_suffix('.syscalls.log')))
        self.assertEqual(result['worker_result'],file_record(self.output/'worker-result.json'))

    def test_post_run_cache_change_blocks_result_publication(self):
        self.cache_validator.side_effect=ValueError('Triton helper cache contents changed')
        with self.assertRaisesRegex(ValueError,'cache contents changed'):self.dispatch()
        self.cache_validator.assert_called_once_with(self.request['triton_cache'])
        self.assertFalse((self.output/'result.json').exists())

    def test_failed_clean_worker_retains_trace_without_passing_envelope(self):
        self.worker_failure=True
        with self.assertRaisesRegex(RuntimeError,'worker failed'):self.dispatch()
        from vipe_benchmark.files import read_json
        self.assertFalse((self.output/'result.json').exists())
        self.assertEqual(read_json(self.output.with_suffix('.trace-record.json')),file_record(self.output.with_suffix('.syscalls.log')))

    def test_fixture_or_active_attempt_is_rejected_before_authorization(self):
        self.request['record_kind']='fixture'
        with self.assertRaisesRegex(ValueError,'fixture'):self.dispatch()
        self.request['record_kind']='actual';self.states['other']={'event':'reserve'}
        with self.assertRaisesRegex(ValueError,'active'):self.dispatch()
        self.ledger.authorize_depth_driver_qualification_triton_cache.assert_not_called()

    def test_existing_output_or_sibling_log_cannot_consume_new_grant(self):
        self.output.parent.mkdir(parents=True);self.output.with_suffix('.log').write_text('retained original log')
        with self.assertRaisesRegex(ValueError,'fresh'):self.dispatch()
        self.ledger.authorize_depth_driver_qualification_triton_cache.assert_not_called()

    def test_oversized_sibling_log_stops_before_worker_output(self):
        self.proposal['artifact_bytes']=128*1024;self.extra_log_bytes=129*1024
        with self.assertRaisesRegex(ValueError,'artifact cap'):self.dispatch()
        self.assertFalse(self.output.exists())

    def test_unclean_finish_cannot_publish_accepted_finish(self):
        self.finish_changes['cleanup_confirmed']=False
        with self.assertRaisesRegex(ValueError,'clean'):self.dispatch()
        self.assertFalse((self.output/'finish.json').exists())

    def test_foreign_active_finish_or_deadline_is_rejected(self):
        self.finish_changes['deadline_exceeded']=True
        with self.assertRaisesRegex(ValueError,'clean'):self.dispatch()
        self.assertFalse((self.output/'finish.json').exists())

    def test_no_injection_or_masked_gpu_before_authorization(self):
        with patch.dict(sys.modules,{'vipe_benchmark.depth_driver_qualification_triton_cache':self.authority}), \
                patch('vipe_benchmark.depth_admission.local_source_records',return_value=self.sources), \
                patch.dict(os.environ,{'PYTHONPATH':'injected'},clear=True):
            with self.assertRaisesRegex(ValueError,'injection'):self.module.dispatch(self.path)
        with patch.dict(sys.modules,{'vipe_benchmark.depth_driver_qualification_triton_cache':self.authority}), \
                patch('vipe_benchmark.depth_admission.local_source_records',return_value=self.sources), \
                patch.dict(os.environ,{'TRITON_CACHE_MANAGER':'evil:Cache'},clear=True):
            with self.assertRaisesRegex(ValueError,'injection: TRITON_CACHE_MANAGER'):self.module.dispatch(self.path)
        self.ledger.authorize_depth_driver_qualification_triton_cache.assert_not_called()


class Method008ProducerTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('method006',ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-008/producer.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.guard=file_record(ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-008/network_guard.py')

    def request(self,root):
        from vipe_benchmark.files import object_hash
        startup=file_record(Path(self.module.__file__).with_name('startup.py'))
        worker=file_record(self.module.__file__)
        request=dict(record_kind='actual',worker=worker,network_guard=self.guard,guard_startup=startup,
            schema='plan069-D6-driver-qualification-request/v5',candidate='D6',job_id=JOB)
        proposal={key:request[key] for key in ('worker','network_guard','guard_startup')}
        write_json(root/'review.json',dict(schema='plan069-D6-driver-qualification-review/v5',status='REVIEW',proposal=proposal))
        request['review']=file_record(root/'review.json')
        write_json(root/'DO.json',dict(schema='plan069-D6-driver-qualification-authorization/v5',status='DO',review=request['review'],proposal_sha256=object_hash(proposal)))
        request['authorization']=file_record(root/'DO.json')
        write_json(root/'request.json',request)
        return root/'request.json',request

    def test_startup_is_bound_before_helpers_without_installing_actual_filter(self):
        proof=dict(socket_descriptors=0,descriptor_count=3,single_thread=True,numeric_imports=False,unix_bind_allowed=True,unix_listen_allowed=True)
        installed=Mock(return_value=proof)
        def fake_exec(code,namespace):namespace['install_before_helpers']=installed
        with tempfile.TemporaryDirectory() as directory:
            path,request=self.request(Path(directory))
            with patch.object(self.module,'exec',side_effect=fake_exec,create=True),patch.object(self.module,'helpers',side_effect=RuntimeError('first helper')) as helpers:
                with self.assertRaisesRegex(RuntimeError,'first helper'):
                    self.module.driver_child(SimpleNamespace(request=str(path),root='unused'))
            installed.assert_called_once_with(self.guard);helpers.assert_called_once_with('unused')

    def test_changed_or_foreign_startup_and_worker_are_rejected_before_execution(self):
        for field in ('guard_startup','worker','network_guard'):
            with self.subTest(field=field),tempfile.TemporaryDirectory() as directory:
                path,request=self.request(Path(directory));request[field]=dict(request[field],sha256='a'*64)
                path.write_text(__import__('json').dumps(request))
                with patch.object(self.module,'exec',create=True) as executed:
                    with self.assertRaises(ValueError):self.module.install_early_guard(path)
                    executed.assert_not_called()

    def test_unapproved_or_fixture_request_never_installs_startup(self):
        from vipe_benchmark.files import file_record
        import json
        for changed in ('fixture','DO'):
            with self.subTest(changed=changed),tempfile.TemporaryDirectory() as directory:
                path,request=self.request(Path(directory))
                if changed=='fixture':request['record_kind']='fixture'
                else:
                    approval=__import__('json').loads(Path(request['authorization']['path']).read_text());approval['status']='REVIEW'
                    Path(request['authorization']['path']).write_text(json.dumps(approval));request['authorization']=file_record(request['authorization']['path'])
                path.write_text(json.dumps(request))
                with patch.object(self.module,'exec',create=True) as executed:
                    with self.assertRaises(ValueError):self.module.install_early_guard(path)
                    executed.assert_not_called()

    def test_failed_startup_prevents_any_helper_import(self):
        with tempfile.TemporaryDirectory() as directory:
            path,_=self.request(Path(directory))
            def fake_exec(code,namespace):
                namespace['install_before_helpers']=Mock(side_effect=ValueError('inherited socket proof rejected'))
            with patch.object(self.module,'exec',side_effect=fake_exec,create=True),patch.object(self.module,'helpers') as helpers:
                with self.assertRaisesRegex(ValueError,'inherited socket'):
                    self.module.driver_child(SimpleNamespace(request=str(path),root='unused'))
                helpers.assert_not_called()

    def test_prohibited_inference_controls_are_preserved(self):
        torch=SimpleNamespace(nn=SimpleNamespace(Module=SimpleNamespace(_call_impl=lambda:None)))
        triton=SimpleNamespace(testing=SimpleNamespace(do_bench=lambda:None,do_bench_cudagraph=lambda:None),runtime=SimpleNamespace(
            Autotuner=SimpleNamespace(_bench=lambda:None),
            jit=SimpleNamespace(JITFunction=SimpleNamespace(run=lambda:None))))
        with self.module.no_inference_guards(torch,triton) as calls:
            with self.assertRaises(PermissionError):torch.nn.Module._call_impl()
            self.assertEqual(calls['forward_calls'],1)


class QualificationOwnedArtifactTests(unittest.TestCase):
    def test_sibling_log_and_temporary_cache_share_attempt_cap(self):
        spec=importlib.util.spec_from_file_location('owned_artifacts',ROOT/'scripts/basketball_vipe_depth_driver_qualification_triton_cache.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'job';output.mkdir();(output/'result.json').write_bytes(b'x'*100)
            temporary=output.with_name(output.name+'-temporary');temporary.mkdir();(temporary/'cache').write_bytes(b'y'*200)
            output.with_suffix('.log').write_bytes(b'z'*300)
            self.assertGreaterEqual(module.owned_artifact_bytes(output),600)
            self.assertGreater(module.owned_artifact_bytes(output),module.owned_artifact_bytes(output/'absent'))


class RealTritonCacheEnvelopeContractTests(unittest.TestCase):
    def test_public_envelope_matches_real005_request_and_result_contract(self):
        from test_vipe_benchmark_depth_driver_qualification_triton_cache import fixture
        from test_vipe_benchmark_depth_driver_qualification import result_fixture
        from vipe_benchmark.depth_driver_qualification_triton_cache import validate_request,validate_result
        from vipe_benchmark.files import read_json
        spec=importlib.util.spec_from_file_location('real005envelope',ROOT/'scripts/basketball_vipe_depth_driver_qualification_triton_cache.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=fixture(Path(directory))
            _,proposal=validate_request(record,current_sources=sources)
            raw=result_fixture(record,request,sources)
            out=Path(request['output']);trace=out.with_suffix('.syscalls.log');trace.write_text('completed fixture syscall trace')
            raw.update(schema='plan069-D6-driver-qualification-result/v5',network_guard=request['network_guard'],
                creation_exception=request['creation_exception'],bind_exception=request['bind_exception'],listen_exception=request['listen_exception'],
                triton_cache=request['triton_cache'],triton_cache_unchanged=True,
                guard_startup=request['guard_startup'],guard_startup_proof=dict(socket_descriptors=0,descriptor_count=3,
                    single_thread=True,numeric_imports=False,unix_bind_allowed=True,unix_listen_allowed=True),trace_path=str(trace))
            write_json(out/'worker-result.json',raw)
            result=module.publish_result_envelope(out,record,proposal,validate_result)
            self.assertEqual(read_json(out/'result.json'),result)
            self.assertEqual(result['trace'],file_record(trace))
            self.assertEqual(result['worker_result'],file_record(out/'worker-result.json'))
            validate_result(result,record,cleanup_confirmed=True)


class Method008TritonCacheOrderTests(unittest.TestCase):
    def test_bound_triton_cache_is_selected_before_torch_or_triton_import(self):
        import inspect
        spec=importlib.util.spec_from_file_location('method008order',ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-008/producer.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        source=inspect.getsource(module.driver_child)
        bound=source.index('select_triton_cache(os.environ, out, triton_cache)')
        self.assertLess(source.index("validate_binding(request['triton_cache']"),bound)
        self.assertLess(bound,source.index('import torch'))
        self.assertLess(bound,source.index('import triton'))
        self.assertIn("'Triton helper cache changed during qualification'",source)

    def test_supervisor_triton_paths_are_the_only_accepted_triton_environment(self):
        spec=importlib.util.spec_from_file_location('method008select',ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-008/producer.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        output=Path('/run/jobs/plan069-D6-driver-qualification-005');temporary='/run/jobs/plan069-D6-driver-qualification-005-temporary/'
        supervised=dict(TRITON_HOME=temporary+'triton-home',TRITON_CACHE_DIR=temporary+'triton-cache',TRITON_DUMP_DIR=temporary+'triton-dump',TRITON_OVERRIDE_DIR=temporary+'triton-override')
        environment=dict(supervised,PATH='/usr/bin');module.select_triton_cache(environment,output,dict(cache_directory='/bound'))
        self.assertEqual(environment,dict(supervised,PATH='/usr/bin',TRITON_CACHE_DIR='/bound'))
        for changed in (dict(supervised,TRITON_CACHE_MANAGER='evil:Cache'),dict(supervised,TRITON_HOME='/elsewhere'),
                        {k:v for k,v in supervised.items() if k!='TRITON_DUMP_DIR'},{}):
            with self.subTest(changed=sorted(changed)):
                with self.assertRaisesRegex(ValueError,'supervised per-attempt'):module.select_triton_cache(dict(changed),output,dict(cache_directory='/bound'))

    def test_supervisor_still_injects_exactly_the_accepted_triton_names(self):
        spec=importlib.util.spec_from_file_location('method008names',ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-008/producer.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        source=(ROOT/'scripts/vipe_benchmark/supervisor.py').read_text()
        for name,folder in module.SUPERVISED_TRITON:
            self.assertIn("('%s', '%s')"%(name,folder),source)


class Method009RequestShadowingTests(unittest.TestCase):
    def test_triton_cache_is_read_only_from_the_verified_qualification_request(self):
        import inspect
        spec=importlib.util.spec_from_file_location('method009shadow',ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-009/producer.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        source=inspect.getsource(module.driver_child)
        shadow=source.index('request = read(args.setup_request)')
        self.assertLess(source.index("qualification = early['request']"),shadow)
        after=source[shadow:]
        for key in ('triton_cache','listen_exception','bind_exception','fourth_predecessor','fifth_predecessor','worker'):
            self.assertNotIn("request['%s']"%key,after,key)
        self.assertEqual(after.count("qualification['triton_cache']"),2)
        self.assertLess(after.index('bind_triton_cache(qualification, out)'),after.index('import torch'))

    def test_bind_triton_cache_runs_on_a_real_qualification_request_shape(self):
        from test_vipe_benchmark_triton_helper_cache import fixture as cache_fixture
        from test_vipe_benchmark_depth_driver_qualification_triton_cache import fixture006
        spec=importlib.util.spec_from_file_location('method009bind',ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-009/producer.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory).resolve()
            ledger,record,qualification,sources,live=fixture006(root)
            from vipe_benchmark.files import read_json
            setup_request=read_json(qualification['setup_request']['path']) if Path(qualification['setup_request']['path']).exists() else {}
            self.assertNotIn('triton_cache',setup_request)
            binding=read_json(qualification['triton_cache']['path'])
            triton=Path(binding['driver_source']['path']).parents[2]
            output=Path(qualification['output']);temporary=output.with_name(output.name+'-temporary')
            environment={name:str(temporary/folder) for name,folder in module.SUPERVISED_TRITON}
            with patch.object(module.importlib.util,'find_spec',return_value=SimpleNamespace(origin=str(triton/'__init__.py'))):
                directory_found,cache=module.bind_triton_cache(qualification,output,environment)
                self.assertEqual(directory_found,triton);self.assertEqual(environment['TRITON_CACHE_DIR'],binding['cache_directory'])
                with self.assertRaises(KeyError):module.bind_triton_cache(setup_request or {'runtime_environment':{}},output,dict(environment))

    def test_method009_serves_only_qualification006(self):
        source=(ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-009/producer.py').read_text()
        self.assertIn("request.get('job_id') == 'plan069-D6-driver-qualification-006'",source)
        self.assertIn("require(JOB == 'plan069-D6-driver-qualification-006'",source)
        guard=lambda n:(ROOT/f'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-00{n}/network_guard.py').read_bytes()
        self.assertEqual(guard(9),guard(7))
