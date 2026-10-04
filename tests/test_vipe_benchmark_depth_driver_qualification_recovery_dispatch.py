"""CPU fakes validate qualification002 dispatcher supervision and clean finish."""
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

JOB='plan069-D6-driver-qualification-002'


class RecoveryQualificationDispatchTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.path=self.root/'request.json';write_json(self.path,{'fixture':'never executed'})
        self.record=file_record(self.path);self.output=self.root/'jobs'/JOB
        self.sources=[{'fixture_source':True}]
        self.request=dict(record_kind='actual',ledger_path=str(self.root/'ledger.jsonl'),output=str(self.output),command=['fixture worker'])
        self.proposal=dict(seconds=180,cleanup_seconds=30,device_bytes=2*1024**3,artifact_bytes=64*1024**2)
        self.validator=Mock(return_value=(self.request,self.proposal));self.result_validator=Mock()
        self.authority=SimpleNamespace(JOB=JOB,validate_request=self.validator,validate_result=self.result_validator)
        self.states={};self.ledger=Mock();self.ledger.states.side_effect=lambda:self.states
        self.extra_log_bytes=0;self.worker_failure=False;self.finish_changes={};self.sampler=Mock(return_value=dict(device_bytes=0,gpu_pids=[],download_bytes=0,artifact_bytes=0))
        spec=importlib.util.spec_from_file_location('driver_recovery_dispatch',ROOT/'scripts/basketball_vipe_depth_driver_qualification_recovery.py')
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
        with patch.dict(sys.modules,{'vipe_benchmark.depth_driver_qualification_recovery':self.authority}), \
                patch.dict(os.environ,{},clear=True),patch.object(self.module,'Ledger',return_value=self.ledger), \
                patch.object(self.module,'resources',self.sampler),patch.object(self.module,'supervise',side_effect=self.supervisor), \
                patch('vipe_benchmark.depth_admission.local_source_records',return_value=self.sources):
            return self.module.dispatch(self.path)

    def test_exact_supervision_uses_cleanup_reserve_and_revalidates_clean_finish(self):
        self.assertEqual(self.dispatch()['status'],'complete')
        self.validator.assert_called_once_with(self.record,current_sources=self.sources)
        self.ledger.authorize_depth_driver_qualification_recovery.assert_called_once_with(self.record)
        self.assertTrue((self.output/'finish.json').exists())
        self.assertEqual(self.result_validator.call_count,2)
        from vipe_benchmark.files import read_json
        result=read_json(self.output/'result.json')
        self.assertEqual(result['trace'],file_record(self.output.with_suffix('.syscalls.log')))
        self.assertEqual(result['worker_result'],file_record(self.output/'worker-result.json'))

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
        self.ledger.authorize_depth_driver_qualification_recovery.assert_not_called()

    def test_existing_output_or_sibling_log_cannot_consume_new_grant(self):
        self.output.parent.mkdir(parents=True);self.output.with_suffix('.log').write_text('retained original log')
        with self.assertRaisesRegex(ValueError,'fresh'):self.dispatch()
        self.ledger.authorize_depth_driver_qualification_recovery.assert_not_called()

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
        with patch.dict(sys.modules,{'vipe_benchmark.depth_driver_qualification_recovery':self.authority}), \
                patch('vipe_benchmark.depth_admission.local_source_records',return_value=self.sources), \
                patch.dict(os.environ,{'PYTHONPATH':'injected'},clear=True):
            with self.assertRaisesRegex(ValueError,'injection'):self.module.dispatch(self.path)


class Method005ProducerTests(unittest.TestCase):
    def setUp(self):
        spec=importlib.util.spec_from_file_location('method005',ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-005/producer.py')
        self.module=importlib.util.module_from_spec(spec);spec.loader.exec_module(self.module)
        self.guard=file_record(ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-005/network_guard.py')

    def test_guard_is_bound_before_execution_without_installing_actual_filter(self):
        from vipe_benchmark.files import verify_record
        installed=Mock()
        def fake_exec(code,namespace):namespace['deny_native_network']=installed
        with patch.object(self.module,'exec',side_effect=fake_exec,create=True):
            self.assertEqual(self.module.install_reviewed_network_guard({'network_guard':self.guard},file_record,verify_record),self.guard)
        installed.assert_called_once_with()

    def test_changed_or_foreign_guard_is_rejected_before_execution(self):
        from vipe_benchmark.files import verify_record
        for guard in (dict(self.guard,sha256='a'*64),dict(self.guard,path='/foreign/network_guard.py')):
            with patch.object(self.module,'exec',create=True) as executed:
                with self.assertRaisesRegex(ValueError,'reviewed'):
                    self.module.install_reviewed_network_guard({'network_guard':guard},file_record,verify_record)
                executed.assert_not_called()

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
        spec=importlib.util.spec_from_file_location('owned_artifacts',ROOT/'scripts/basketball_vipe_depth_driver_qualification_recovery.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'job';output.mkdir();(output/'result.json').write_bytes(b'x'*100)
            temporary=output.with_name(output.name+'-temporary');temporary.mkdir();(temporary/'cache').write_bytes(b'y'*200)
            output.with_suffix('.log').write_bytes(b'z'*300)
            self.assertGreaterEqual(module.owned_artifact_bytes(output),600)
            self.assertGreater(module.owned_artifact_bytes(output),module.owned_artifact_bytes(output/'absent'))


class RealRecoveryEnvelopeContractTests(unittest.TestCase):
    def test_dispatcher_envelope_matches_real_authority_result_contract(self):
        from test_vipe_benchmark_depth_driver_qualification_recovery import fixture
        from test_vipe_benchmark_depth_driver_qualification import result_fixture
        from vipe_benchmark.depth_driver_qualification_recovery import validate_request,validate_result
        from vipe_benchmark.files import read_json
        spec=importlib.util.spec_from_file_location('real_envelope_contract',ROOT/'scripts/basketball_vipe_depth_driver_qualification_recovery.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=fixture(Path(directory))
            _,proposal=validate_request(record,current_sources=sources)
            raw=result_fixture(record,request,sources)
            out=Path(request['output']);trace=out.with_suffix('.syscalls.log');trace.write_text('completed fixture syscall trace')
            raw.update(schema='plan069-D6-driver-qualification-result/v2',network_guard=request['network_guard'],
                creation_exception=request['creation_exception'],trace_path=str(trace))
            write_json(out/'worker-result.json',raw)
            result=module.publish_result_envelope(out,record,proposal,validate_result)
            self.assertEqual(read_json(out/'result.json'),result)
            self.assertEqual(result['trace'],file_record(trace))
            self.assertEqual(result['worker_result'],file_record(out/'worker-result.json'))
            validate_result(result,record,cleanup_confirmed=True)
