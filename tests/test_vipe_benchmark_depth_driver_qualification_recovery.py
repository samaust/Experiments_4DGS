"""Separate D6 qualification002 authority/reservation seam; no runtime loads."""
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch

import test_vipe_benchmark_depth_driver_diagnostic as diagnostic_tests
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, object_hash, read_json, write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.depth_driver_qualification_recovery import JOB, KIND, validate_request


def fixture(root):
    ledger,diag_record,diag,sources,live=diagnostic_tests.DiagnosticTests().prepare(root)
    with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), patch('vipe_benchmark.execution.resources',return_value=live):
        ledger.authorize_depth_driver_diagnostic(diag_record)
        ledger.reserve('plan069-D6-driver-diagnostic-001',diag['command'],dict(request=diag_record))
        output=Path(diag['output']);output.mkdir()
        trace=output.with_suffix('.syscalls.log');trace.write_text('socket(0x1,0x80005,0) = -1 EPERM\n')
        result=dict(schema='plan069-D6-driver-diagnostic-result/v1',request=diag_record,record_kind='fixture',status='captured',model_loaded=False,inference=False,benchmarks=False,tensor_peak_allocated_bytes=0,network_guard=diag['guard'],cuda_init_outcome='error',trace_path=str(trace))
        write_json(output/'result.json',result)
        diag_result=file_record(output/'result.json')
        finish=ledger.finish('plan069-D6-driver-diagnostic-001','complete',1,cleanup_confirmed=True,result=diag_result,peak=dict(device_bytes=0))
        write_json(output/'finish.json',finish)
    old=read_json(root/'request.json')
    def save(name,value):
        path=root/name;write_json(path,value);return file_record(path)
    guard=save('guard005.py',dict(fixture='not executed'))
    worker=save('producer005.py',dict(fixture='not executed'))
    sources=[guard,worker]
    source=read_json(old['source_review']['path']);source['local_sources']=sources
    source_record=save('source002.json',source)
    cpu=save('cpu002.json',dict(schema='plan069-delta-cpu-test-capture/v1',record_kind='fixture',passed=True,within_wall_limit=True,source_bytes_unchanged=True,sources_before=sources,sources_after=sources))
    proposal=dict(candidate='D6',job_id=JOB,qualification_kind=KIND,max_attempts=1,seconds=180,cleanup_seconds=30,device_bytes=2*1024**3,artifact_bytes=64*1024**2,downloads=0,inference=False,benchmarks=False,strict_cpu_loads=2,gpu_model_load=False,setup=old['setup'],network_guard=guard,strace=diag['strace'],predecessor_finish=diag['predecessor_finish'],diagnostic_finish=file_record(output/'finish.json'),diagnostic_result=diag_result,diagnostic_trace=file_record(trace),creation_exception=dict(syscall='socket',domain=1,type=524293,protocol=0))
    review=save('review002.json',dict(schema='plan069-D6-driver-qualification-review/v2',status='REVIEW',proposal=proposal))
    approval=save('DO002.json',dict(schema='plan069-D6-driver-qualification-authorization/v2',status='DO',review=review,proposal_sha256=object_hash(proposal)))
    request=dict(old,schema='plan069-D6-driver-qualification-request/v2',job_id=JOB,review=review,authorization=approval,source_review=source_record,cpu_validation=cpu,worker=worker,output=str(root/'qualification002'))
    for key in ('network_guard','strace','predecessor_finish','diagnostic_finish','diagnostic_result','diagnostic_trace','creation_exception'):request[key]=proposal[key]
    path=root/'request002.json';request['command']=[diag['strace']['path'],'-f','-qq','-s','128','-e',
        'trace=socket,socketpair,connect,bind,listen,accept,accept4,sendto,sendmsg,recvfrom,recvmsg,ioctl',
        '-e','raw=sendto,sendmsg,recvfrom,recvmsg,ioctl','-o',str(Path(request['output']).with_suffix('.syscalls.log')),
        old['interpreter_invocation'],'-I','-B',worker['path'],'driver-child','--request',str(path),'--output',request['output']]
    write_json(path,request)
    return ledger,file_record(path),request,sources,live


class QualificationRecoveryTests(unittest.TestCase):
    def test_new_approved_slot_preserves_failed001_and_does_not_consume_maps(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=fixture(Path(directory))
            with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), patch('vipe_benchmark.execution.resources',return_value=live):
                ledger.authorize_depth_driver_qualification_recovery(record)
                reserved=ledger.reserve(JOB,request['command'],dict(request=record))
            self.assertEqual(reserved['seconds'],180)
            self.assertEqual(ledger.states()['plan069-D6-driver-qualification-001']['status'],'failed')
            self.assertNotIn('plan069-D6-maps-001',ledger.states())

    def test_consumed002_and_unchecked_notes_cannot_mint_another_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=fixture(Path(directory))
            with self.assertRaisesRegex(ValueError,'checked'):
                ledger.note('depth_driver_qualification_recovery_authorized',job_id=JOB)
            with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), patch('vipe_benchmark.execution.resources',return_value=live):
                ledger.authorize_depth_driver_qualification_recovery(record)
                ledger.reserve(JOB,request['command'],dict(request=record))
                ledger.finish(JOB,'failed',1,cleanup_confirmed=True)
                before=ledger.events()
                with self.assertRaisesRegex(ValueError,'consumed'):
                    ledger.authorize_depth_driver_qualification_recovery(record)
                with self.assertRaisesRegex(ValueError,'consumed'):
                    ledger.reserve(JOB,request['command'],dict(request=record))
            self.assertEqual(ledger.events(),before)

    def test_new_review_without_fresh_DO_or_original_DO_fails_before_append(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=fixture(Path(directory))
            before=ledger.events()
            approved=read_json(request['authorization']['path']);approved['status']='REVIEW'
            Path(request['authorization']['path']).write_text(json.dumps(approved))
            request['authorization']=file_record(request['authorization']['path'])
            Path(record['path']).write_text(json.dumps(request))
            with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources):
                with self.assertRaisesRegex(ValueError,'approved.*allocation'):
                    ledger.authorize_depth_driver_qualification_recovery(file_record(record['path']))
            self.assertEqual(ledger.events(),before)
            request['authorization']=read_json(Path(directory)/'request.json')['authorization']
            Path(record['path']).write_text(json.dumps(request))
            with self.assertRaisesRegex(ValueError,'approved.*allocation'):
                validate_request(file_record(record['path']))

    def test_changed_diagnostic_finish_or_trace_rejects_without_authority(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=fixture(Path(directory))
            before=ledger.events()
            finish=read_json(request['diagnostic_finish']['path']);finish['cleanup_confirmed']=False
            Path(request['diagnostic_finish']['path']).write_text(json.dumps(finish))
            proposal=read_json(request['review']['path'])['proposal']
            request['diagnostic_finish']=file_record(request['diagnostic_finish']['path']);proposal['diagnostic_finish']=request['diagnostic_finish']
            self.rebind(record,request,proposal)
            with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources):
                with self.assertRaisesRegex(ValueError,'completed clean diagnostic'):
                    ledger.authorize_depth_driver_qualification_recovery(file_record(record['path']))
            self.assertEqual(ledger.events(),before)
            Path(request['diagnostic_trace']['path']).write_text('changed retained trace')
            with self.assertRaises(ValueError):validate_request(file_record(record['path']))

    @staticmethod
    def rebind(record,request,proposal):
        review=read_json(request['review']['path']);review['proposal']=proposal
        Path(request['review']['path']).write_text(json.dumps(review));request['review']=file_record(request['review']['path'])
        approved=read_json(request['authorization']['path']);approved.update(review=request['review'],proposal_sha256=object_hash(proposal))
        Path(request['authorization']['path']).write_text(json.dumps(approved));request['authorization']=file_record(request['authorization']['path'])
        Path(record['path']).write_text(json.dumps(request))

    def test_changed_creation_exception_or_bounds_rejects(self):
        for key,value in [('creation_exception',dict(syscall='socket',domain=2,type=524293,protocol=0)),('cleanup_seconds',15),('strict_cpu_loads',1),('gpu_model_load',True),('seconds',181),('max_attempts',2)]:
            with self.subTest(key=key),tempfile.TemporaryDirectory() as directory:
                ledger,record,request,sources,live=fixture(Path(directory))
                proposal=read_json(request['review']['path'])['proposal'];proposal[key]=value
                if key=='creation_exception':request[key]=value
                self.rebind(record,request,proposal)
                with self.assertRaisesRegex(ValueError,'bounded D6 contract'):
                    validate_request(file_record(record['path']))

    def test_exact_command_and_fresh_grant_required_before_consumption(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=fixture(Path(directory))
            with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), patch('vipe_benchmark.execution.resources',return_value=live):
                ledger.authorize_depth_driver_qualification_recovery(record)
                before=ledger.events()
                with self.assertRaisesRegex(ValueError,'command/evidence'):
                    ledger.reserve(JOB,['unreviewed'],dict(request=record))
                self.assertEqual(ledger.events(),before)
                ledger.note('ordinary_note')
                with self.assertRaisesRegex(ValueError,'fresh exact'):
                    ledger.reserve(JOB,request['command'],dict(request=record))
            self.assertNotIn(JOB,ledger.states())

    def test_new_guard_worker_dispatch_and_authority_are_mandatory_D6_sources(self):
        from vipe_benchmark.depth_admission import local_source_records
        with patch('vipe_benchmark.depth_admission.file_record',side_effect=lambda path:dict(path=str(path))):
            paths={row['path'] for row in local_source_records('D6')}
        for suffix in ('scripts/vipe_benchmark/depth_driver_qualification_recovery.py',
                'scripts/basketball_vipe_depth_driver_qualification_recovery.py',
                'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-005/producer.py',
                'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-005/network_guard.py'):
            self.assertTrue(any(path.endswith(suffix) for path in paths),suffix)

    def test_retained002_result_is_separate_from_inference_and_original001(self):
        from test_vipe_benchmark_depth_driver_qualification import result_fixture
        from vipe_benchmark.depth_driver_qualification_recovery import validate_result, qualification_exception
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=fixture(Path(directory))
            result=result_fixture(record,request,sources)
            result.update(schema='plan069-D6-driver-qualification-result/v2',network_guard=request['network_guard'],creation_exception=request['creation_exception'],trace_path=str(Path(request['output']).with_suffix('.syscalls.log')))
            trace=Path(result['trace_path']);trace.write_text('completed strace fixture')
            worker_result=Path(request['output'])/'worker-result.json';write_json(worker_result,result)
            result.update(trace=file_record(trace),worker_result=file_record(worker_result))
            validate_result(result,record,cleanup_confirmed=True)
            result_path=Path(request['output'])/'result.json';write_json(result_path,result)
            with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), patch('vipe_benchmark.execution.resources',return_value=live):
                ledger.authorize_depth_driver_qualification_recovery(record)
                ledger.reserve(JOB,request['command'],dict(request=record))
                finish=ledger.finish(JOB,'complete',2,cleanup_confirmed=True,result=file_record(result_path),peak=dict(device_bytes=0))
            finish_path=Path(request['output'])/'finish.json';write_json(finish_path,finish)
            proof=dict(request=record,result=file_record(result_path),finish=file_record(finish_path),ledger_path=str(ledger.path))
            runtime=dict(record_kind='fixture',qualification_kind=KIND,setup=request['setup'],local_sources=sources,driver_qualification=proof)
            self.assertEqual(qualification_exception(runtime),proof)
            for key,value in [('network_guard',{}),('creation_exception',{}),('forward_calls',1),('strict_cpu_loads',1)]:
                with self.subTest(key=key),self.assertRaises(ValueError):
                    validate_result(dict(result,**{key:value}),record,cleanup_confirmed=True)
            with self.assertRaises(ValueError):validate_result(result,record,cleanup_confirmed=False)

    def test_uncertain_or_surviving_predecessor_cleanup_cannot_authorize002(self):
        original_finish=Ledger.finish
        for target in ('plan069-D6-driver-qualification-001','plan069-D6-driver-diagnostic-001'):
            for field,value in [('cleanup_uncertain',True),('surviving_pids',[123])]:
                with self.subTest(target=target,field=field),tempfile.TemporaryDirectory() as directory:
                    def finish(instance,job,*args,**kwargs):
                        if job==target:kwargs[field]=value
                        return original_finish(instance,job,*args,**kwargs)
                    with patch.object(Ledger,'finish',new=finish):
                        ledger,record,request,sources,live=fixture(Path(directory))
                    before=ledger.events()
                    with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources), patch('vipe_benchmark.execution.resources',return_value=live):
                        with self.assertRaisesRegex(ValueError,'clean'):
                            ledger.authorize_depth_driver_qualification_recovery(record)
                    self.assertEqual(ledger.events(),before)

    def test_traced_command_rejects_changed_filter_tool_or_escaped_trace(self):
        with tempfile.TemporaryDirectory() as directory:
            ledger,record,request,sources,live=fixture(Path(directory))
            good=list(request['command'])
            for index,value in [(0,'other-strace'),(7,'trace=none'),(11,str(Path(directory)/'unowned.log'))]:
                with self.subTest(index=index):
                    request['command']=list(good);request['command'][index]=value
                    Path(record['path']).write_text(json.dumps(request))
                    with self.assertRaisesRegex(ValueError,'traced qualification command'):
                        validate_request(file_record(record['path']))


if __name__=='__main__':unittest.main()
