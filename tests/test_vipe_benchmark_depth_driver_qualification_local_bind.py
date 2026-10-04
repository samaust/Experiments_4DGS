"""Public separately approved003 boundary; fixtures execute no guard or runtime."""
from pathlib import Path
import tempfile,unittest
from unittest.mock import patch
import test_vipe_benchmark_depth_driver_qualification_recovery as prior
from vipe_benchmark.files import file_record,read_json,write_json,object_hash
from vipe_benchmark.depth_driver_qualification_local_bind import JOB,KIND,BIND_EXCEPTION,validate_request


def fixture(root):
 ledger,oldrecord,old,sources,live=prior.fixture(root)
 with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
  ledger.authorize_depth_driver_qualification_recovery(oldrecord);ledger.reserve(prior.JOB,old['command'],dict(request=oldrecord));finish=ledger.finish(prior.JOB,'failed',2,cleanup_confirmed=True)
 def save(name,value):
  path=root/name;write_json(path,value);return file_record(path)
 second_finish=save('failed002.json',finish)
 trace=Path(old['output']).with_suffix('.syscalls.log');trace.write_text('bind(local) EPERM fixture')
 worker=save('producer006.py',{'fixture':True});guard=save('guard006.py',{'fixture':True});startup=save('startup006.py',{'fixture':True});sources=[worker,guard,startup]
 source=read_json(old['source_review']['path']);source['local_sources']=sources
 request=dict(old,schema='plan069-D6-driver-qualification-request/v3',job_id=JOB,worker=worker,network_guard=guard,guard_startup=startup,second_predecessor_finish=second_finish,second_predecessor_trace=file_record(trace),bind_exception=BIND_EXCEPTION,output=str(root/'qualification003'))
 proposal=dict(read_json(old['review']['path'])['proposal'],job_id=JOB,worker=worker,network_guard=guard,guard_startup=startup,second_predecessor_finish=second_finish,second_predecessor_trace=file_record(trace),bind_exception=BIND_EXCEPTION)
 request['review']=save('review003.json',dict(schema='plan069-D6-driver-qualification-review/v3',status='REVIEW',proposal=proposal))
 request['authorization']=save('DO003.json',dict(schema='plan069-D6-driver-qualification-authorization/v3',status='DO',review=request['review'],proposal_sha256=object_hash(proposal)))
 request['source_review']=save('source003.json',source)
 request['cpu_validation']=save('cpu003.json',dict(schema='plan069-delta-cpu-test-capture/v1',record_kind='fixture',passed=True,within_wall_limit=True,source_bytes_unchanged=True,sources_before=sources,sources_after=sources))
 path=root/'request003.json';command=list(old['command']);command[10]=str(Path(request['output']).with_suffix('.syscalls.log'));command[14]=worker['path'];command[17]=str(path);command[19]=request['output'];request['command']=command;write_json(path,request)
 return ledger,file_record(path),request,sources,live

class QualificationLocalBindTests(unittest.TestCase):
 def test_fresh003_preserves_consumed001002_and_maps(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d))
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    ledger.authorize_depth_driver_qualification_local_bind(record);reserve=ledger.reserve(JOB,request['command'],dict(request=record))
   self.assertEqual(reserve['seconds'],180);self.assertEqual(ledger.states()[prior.JOB]['status'],'failed');self.assertNotIn('plan069-D6-maps-001',ledger.states())
 def test_note_cannot_mint_authority(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,*_=fixture(Path(d));before=ledger.events()
   with self.assertRaisesRegex(ValueError,'checked'):ledger.note('depth_driver_qualification_local_bind_authorized',job_id=JOB)
   self.assertEqual(before,ledger.events())
 def test_fresh_physical_startup_binding_required(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d));Path(request['guard_startup']['path']).write_text('changed')
   with self.assertRaises(ValueError):validate_request(record)
 def test_failed002_must_be_exact_checked_terminal(self):
  from vipe_benchmark.depth_driver_qualification_local_bind import check_predecessor
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d));finish=read_json(request['second_predecessor_finish']['path']);finish['cleanup_confirmed']=False;Path(request['second_predecessor_finish']['path']).write_text(__import__('json').dumps(finish));request['second_predecessor_finish']=file_record(request['second_predecessor_finish']['path'])
   with self.assertRaises(ValueError):check_predecessor(ledger.events(),request)
 def test_consumed003_cannot_retry_or_borrow002_approval(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d))
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    ledger.authorize_depth_driver_qualification_local_bind(record);ledger.reserve(JOB,request['command'],dict(request=record));ledger.finish(JOB,'failed',1,cleanup_confirmed=True)
    before=ledger.events()
    with self.assertRaisesRegex(ValueError,'consumed'):ledger.authorize_depth_driver_qualification_local_bind(record)
    with self.assertRaisesRegex(ValueError,'consumed'):ledger.reserve(JOB,request['command'],dict(request=record))
   self.assertEqual(before,ledger.events())
   request['authorization']=read_json(Path(d)/'request002.json')['authorization'];Path(record['path']).write_text(__import__('json').dumps(request))
   with self.assertRaisesRegex(ValueError,'approved.*allocation'):validate_request(file_record(record['path']))
 def test_current_source_and_exact_command_required(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d));before=ledger.events()
   with self.assertRaisesRegex(ValueError,'sources changed'):validate_request(record,current_sources=[])
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    ledger.authorize_depth_driver_qualification_local_bind(record);before=ledger.events()
    with self.assertRaisesRegex(ValueError,'command/evidence'):ledger.reserve(JOB,['unreviewed'],dict(request=record))
   self.assertEqual(before,ledger.events())
 def test_new_helpers_are_enforced_in_D6_closure(self):
  from vipe_benchmark.depth_admission import local_source_records
  with patch('vipe_benchmark.depth_admission.file_record',side_effect=lambda path:dict(path=str(path))):paths={r['path'] for r in local_source_records('D6')}
  for suffix in ['depth_driver_qualification_local_bind.py','basketball_vipe_depth_driver_qualification_local_bind.py','moge-driver-method-006/producer.py','moge-driver-method-006/network_guard.py','moge-driver-method-006/startup.py']:
   self.assertTrue(any(p.endswith(suffix) for p in paths),suffix)
 def test_result_requires_exact_zero_socket_pre_helper_proof(self):
  from test_vipe_benchmark_depth_driver_qualification import result_fixture
  from vipe_benchmark.depth_driver_qualification_local_bind import validate_result
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d));result=result_fixture(record,request,sources)
   proof=dict(socket_descriptors=0,descriptor_count=3,single_thread=True,numeric_imports=False,unix_bind_allowed=True)
   result.update(schema='plan069-D6-driver-qualification-result/v3',network_guard=request['network_guard'],guard_startup=request['guard_startup'],guard_startup_proof=proof,creation_exception=request['creation_exception'],bind_exception=request['bind_exception'],trace_path=str(Path(request['output']).with_suffix('.syscalls.log')))
   trace=Path(result['trace_path']);trace.write_text('fixture trace')
   worker=Path(request['output'])/'worker-result.json';write_json(worker,result);result.update(trace=file_record(trace),worker_result=file_record(worker));validate_result(result,record,cleanup_confirmed=True)
   for key,value in [('socket_descriptors',1),('descriptor_count',True),('single_thread',False),('numeric_imports',True),('unix_bind_allowed',False)]:
    with self.subTest(key=key):
     changed=dict(result,guard_startup_proof=dict(proof,**{key:value}))
     with self.assertRaisesRegex(ValueError,'descriptor proof'):validate_result(changed,record,cleanup_confirmed=True)
