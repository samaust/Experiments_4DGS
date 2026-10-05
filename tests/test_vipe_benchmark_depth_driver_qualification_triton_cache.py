"""Public separately approved005 boundary; fixtures execute no guard, compiler or runtime."""
from pathlib import Path
import json,tempfile,unittest
from unittest.mock import patch
import test_vipe_benchmark_depth_driver_qualification_local_listen as prior
from test_vipe_benchmark_triton_helper_cache import fixture as cache_fixture
from vipe_benchmark.files import file_record,read_json,write_json,object_hash
from vipe_benchmark.depth_driver_qualification_triton_cache import JOB,LISTEN_EXCEPTION,validate_request


def fixture(root):
 ledger,oldrecord,old,sources,live=prior.fixture(root)
 with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
  ledger.authorize_depth_driver_qualification_local_listen(oldrecord);ledger.reserve(prior.JOB,old['command'],dict(request=oldrecord));finish=ledger.finish(prior.JOB,'failed',2,cleanup_confirmed=True)
 def save(name,value):
  path=root/name;write_json(path,value);return file_record(path)
 fourth_finish=save('failed004.json',finish)
 trace=Path(old['output']).with_suffix('.syscalls.log');trace.write_text('listen(local) = 0; PermissionError child process escape fixture')
 (root/'cachefixture').mkdir();_,_,_,cache=cache_fixture((root/'cachefixture').resolve(),python=old['interpreter_invocation'])
 worker=save('producer008.py',{'fixture':True});guard=save('guard008.py',{'fixture':True});startup=save('startup008.py',{'fixture':True});sources=[worker,guard,startup]
 source=read_json(old['source_review']['path']);source['local_sources']=sources
 lineage=dict(job_id=JOB,worker=worker,network_guard=guard,guard_startup=startup,fourth_predecessor_finish=fourth_finish,fourth_predecessor_trace=file_record(trace),triton_cache=cache)
 request=dict(old,schema='plan069-D6-driver-qualification-request/v5',output=str(root/'qualification005'),**lineage)
 proposal=dict(read_json(old['review']['path'])['proposal'],**lineage)
 request['review']=save('review005.json',dict(schema='plan069-D6-driver-qualification-review/v5',status='REVIEW',proposal=proposal))
 request['authorization']=save('DO005.json',dict(schema='plan069-D6-driver-qualification-authorization/v5',status='DO',review=request['review'],proposal_sha256=object_hash(proposal)))
 request['source_review']=save('source005.json',source)
 request['cpu_validation']=save('cpu005.json',dict(schema='plan069-delta-cpu-test-capture/v1',record_kind='fixture',passed=True,within_wall_limit=True,source_bytes_unchanged=True,sources_before=sources,sources_after=sources))
 path=root/'request005.json';command=list(old['command']);command[10]=str(Path(request['output']).with_suffix('.syscalls.log'));command[14]=worker['path'];command[17]=str(path);command[19]=request['output'];request['command']=command;write_json(path,request)
 return ledger,file_record(path),request,sources,live


def rewrite(record,request):
 Path(record['path']).write_text(json.dumps(request));return file_record(record['path'])


class QualificationTritonCacheTests(unittest.TestCase):
 def test_fresh005_preserves_consumed004_and_maps(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d))
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    ledger.authorize_depth_driver_qualification_triton_cache(record);reserve=ledger.reserve(JOB,request['command'],dict(request=record))
   self.assertEqual(reserve['seconds'],180);self.assertEqual(ledger.states()[prior.JOB]['status'],'failed');self.assertNotIn('plan069-D6-maps-001',ledger.states())
 def test_stale_or_non_final_grant_cannot_reserve(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d))
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    ledger.authorize_depth_driver_qualification_triton_cache(record)
    with patch('vipe_benchmark.ledger.time.time',return_value=ledger.events()[-1]['recorded_unix']+31):
     with self.assertRaisesRegex(ValueError,'fresh exact .*qualification-005'):ledger.reserve(JOB,request['command'],dict(request=record))
    ledger.note('fixture_interleaved_event')
    with self.assertRaisesRegex(ValueError,'fresh exact .*qualification-005'):ledger.reserve(JOB,request['command'],dict(request=record))
   self.assertNotIn(JOB,ledger.states())
 def test_note_cannot_mint_authority(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,*_=fixture(Path(d));before=ledger.events()
   with self.assertRaisesRegex(ValueError,'checked'):ledger.note('depth_driver_qualification_triton_cache_authorized',job_id=JOB)
   self.assertEqual(before,ledger.events())
 def test_changed_triton_cache_blocks_authorization(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d));before=ledger.events()
   binding=read_json(request['triton_cache']['path']);helper=Path(binding['cache_directory'])/binding['manifest']['files'][0]['relative_path'];helper.write_bytes(b'recompiled')
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    with self.assertRaisesRegex(ValueError,'contents changed'):ledger.authorize_depth_driver_qualification_triton_cache(record)
   self.assertEqual(before,ledger.events())
 def test_cache_built_by_other_interpreter_is_rejected(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);ledger,record,request,sources,live=fixture(root)
   other=root/'foreign-python';other.mkdir();_,_,_,foreign=cache_fixture(other.resolve(),python='/other/python')
   review=read_json(request['review']['path']);review['proposal']['triton_cache']=foreign;Path(request['review']['path']).write_text(json.dumps(review));request['review']=file_record(request['review']['path'])
   approval=read_json(request['authorization']['path']);approval.update(review=request['review'],proposal_sha256=object_hash(review['proposal']))
   Path(request['authorization']['path']).write_text(json.dumps(approval));request['authorization']=file_record(request['authorization']['path'])
   with self.assertRaisesRegex(ValueError,'qualification interpreter'):validate_request(rewrite(record,dict(request,triton_cache=foreign)))
 def test_request_cache_must_equal_reviewed_proposal(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d))
   other=Path(d)/'other';other.mkdir();_,_,_,foreign=cache_fixture(other.resolve())
   with self.assertRaisesRegex(ValueError,'lineage/guard'):validate_request(rewrite(record,dict(request,triton_cache=foreign)))
 def test_failed004_must_be_exact_checked_terminal(self):
  from vipe_benchmark.depth_driver_qualification_triton_cache import check_predecessor
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d));finish=read_json(request['fourth_predecessor_finish']['path']);finish['cleanup_confirmed']=False;Path(request['fourth_predecessor_finish']['path']).write_text(json.dumps(finish));request['fourth_predecessor_finish']=file_record(request['fourth_predecessor_finish']['path'])
   with self.assertRaises(ValueError):check_predecessor(ledger.events(),request)
 def test_wrong_fourth_trace_cannot_authorize(self):
  from vipe_benchmark.depth_driver_qualification_triton_cache import check_predecessor
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d))
   foreign=Path(d)/'foreign.trace';foreign.write_text('not the retained004 trace')
   with self.assertRaisesRegex(ValueError,'retained qualification004 trace'):check_predecessor(ledger.events(),dict(request,fourth_predecessor_trace=file_record(foreign)))
 def test_consumed005_cannot_retry_or_borrow004_approval(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d))
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    ledger.authorize_depth_driver_qualification_triton_cache(record);ledger.reserve(JOB,request['command'],dict(request=record));ledger.finish(JOB,'failed',1,cleanup_confirmed=True)
    before=ledger.events()
    with self.assertRaisesRegex(ValueError,'consumed'):ledger.authorize_depth_driver_qualification_triton_cache(record)
    with self.assertRaisesRegex(ValueError,'consumed'):ledger.reserve(JOB,request['command'],dict(request=record))
   self.assertEqual(before,ledger.events())
   request['authorization']=read_json(Path(d)/'request004.json')['authorization']
   with self.assertRaisesRegex(ValueError,'approved.*allocation'):validate_request(rewrite(record,request))
 def test_current_source_and_exact_command_required(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d))
   with self.assertRaisesRegex(ValueError,'sources changed'):validate_request(record,current_sources=[])
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    ledger.authorize_depth_driver_qualification_triton_cache(record);before=ledger.events()
    with self.assertRaisesRegex(ValueError,'command/evidence'):ledger.reserve(JOB,['unreviewed'],dict(request=record))
   self.assertEqual(before,ledger.events())
 def test_new_helpers_are_enforced_in_D6_closure(self):
  from vipe_benchmark.depth_admission import local_source_records
  with patch('vipe_benchmark.depth_admission.file_record',side_effect=lambda path:dict(path=str(path))):paths={r['path'] for r in local_source_records('D6')}
  for suffix in ['depth_driver_qualification_triton_cache.py','triton_helper_cache.py','basketball_vipe_depth_driver_qualification_triton_cache.py','basketball_vipe_triton_helper_cache.py','moge-driver-method-008/producer.py','moge-driver-method-008/network_guard.py','moge-driver-method-008/startup.py']:
   self.assertTrue(any(p.endswith(suffix) for p in paths),suffix)
 def test_result_requires_bound_unchanged_cache_and_listen_proof(self):
  from test_vipe_benchmark_depth_driver_qualification import result_fixture
  from vipe_benchmark.depth_driver_qualification_triton_cache import validate_result
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture(Path(d));result=result_fixture(record,request,sources)
   proof=dict(socket_descriptors=0,descriptor_count=3,single_thread=True,numeric_imports=False,unix_bind_allowed=True,unix_listen_allowed=True)
   result.update(schema='plan069-D6-driver-qualification-result/v5',network_guard=request['network_guard'],guard_startup=request['guard_startup'],guard_startup_proof=proof,creation_exception=request['creation_exception'],bind_exception=request['bind_exception'],listen_exception=LISTEN_EXCEPTION,triton_cache=request['triton_cache'],triton_cache_unchanged=True,trace_path=str(Path(request['output']).with_suffix('.syscalls.log')))
   trace=Path(result['trace_path']);trace.write_text('fixture trace')
   worker=Path(request['output'])/'worker-result.json';write_json(worker,result);result.update(trace=file_record(trace),worker_result=file_record(worker));validate_result(result,record,cleanup_confirmed=True)
   for key,value in [('triton_cache_unchanged',False),('triton_cache',request['network_guard'])]:
    with self.subTest(key=key):
     with self.assertRaisesRegex(ValueError,'exact D6 driver qualification result'):validate_result(dict(result,**{key:value}),record,cleanup_confirmed=True)
   with self.assertRaisesRegex(ValueError,'descriptor proof'):validate_result(dict(result,guard_startup_proof=dict(proof,unix_listen_allowed=False)),record,cleanup_confirmed=True)


JOB6='plan069-D6-driver-qualification-006'


def fixture006(root):
 ledger,record5,request5,sources,live=fixture(root)
 with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
  ledger.authorize_depth_driver_qualification_triton_cache(record5);ledger.reserve(JOB,request5['command'],dict(request=record5));finish=ledger.finish(JOB,'failed',1,cleanup_confirmed=True)
 def save(name,value):
  path=root/name;write_json(path,value);return file_record(path)
 fifth=save('failed005.json',finish)
 trace=Path(request5['output']).with_suffix('.syscalls.log');trace.write_text('KeyError triton_cache fixture')
 worker=save('producer009.py',{'fixture':True});guard=save('guard009.py',{'fixture':True});startup=save('startup009.py',{'fixture':True});sources=[worker,guard,startup]
 source=read_json(request5['source_review']['path']);source['local_sources']=sources
 lineage=dict(job_id=JOB6,worker=worker,network_guard=guard,guard_startup=startup,fifth_predecessor_finish=fifth,fifth_predecessor_trace=file_record(trace))
 request=dict(request5,output=str(root/'qualification006'),**lineage)
 proposal=dict(read_json(request5['review']['path'])['proposal'],**lineage)
 request['review']=save('review006.json',dict(schema='plan069-D6-driver-qualification-review/v5',status='REVIEW',proposal=proposal))
 request['authorization']=save('DO006.json',dict(schema='plan069-D6-driver-qualification-authorization/v5',status='DO',review=request['review'],proposal_sha256=object_hash(proposal)))
 request['source_review']=save('source006.json',source)
 request['cpu_validation']=save('cpu006.json',dict(schema='plan069-delta-cpu-test-capture/v1',record_kind='fixture',passed=True,within_wall_limit=True,source_bytes_unchanged=True,sources_before=sources,sources_after=sources))
 path=root/'request006.json';command=list(request5['command']);command[10]=str(Path(request['output']).with_suffix('.syscalls.log'));command[14]=worker['path'];command[17]=str(path);command[19]=request['output'];request['command']=command;write_json(path,request)
 return ledger,file_record(path),request,sources,live


class QualificationTritonCacheRetryTests(unittest.TestCase):
 def test_fresh006_after_consumed005_preserves_all_attempts(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture006(Path(d))
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    ledger.authorize_depth_driver_qualification_triton_cache(record);reserve=ledger.reserve(JOB6,request['command'],dict(request=record))
   self.assertEqual(reserve['seconds'],180);self.assertEqual(ledger.states()[JOB]['status'],'failed');self.assertEqual(ledger.states()[prior.JOB]['status'],'failed')
 def test_006_requires_consumed_failed005(self):
  from vipe_benchmark.depth_driver_qualification_triton_cache import check_predecessor
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture006(Path(d))
   finish=read_json(request['fifth_predecessor_finish']['path']);finish['status']='complete'
   Path(request['fifth_predecessor_finish']['path']).write_text(json.dumps(finish));changed=dict(request,fifth_predecessor_finish=file_record(request['fifth_predecessor_finish']['path']))
   with self.assertRaisesRegex(ValueError,'previous Triton-cache'):check_predecessor(ledger.events(),changed)
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture006(Path(d))
   foreign=Path(d)/'foreign.trace';foreign.write_text('not retained005')
   with self.assertRaisesRegex(ValueError,'previous Triton-cache qualification trace'):check_predecessor(ledger.events(),dict(request,fifth_predecessor_trace=file_record(foreign)))
 def test_006_cannot_authorize_before_005_is_consumed(self):
  with tempfile.TemporaryDirectory() as d:
   root=Path(d);ledger,record5,request5,sources,live=fixture(root)
   from vipe_benchmark.depth_driver_qualification_triton_cache import check_predecessor
   with self.assertRaisesRegex(ValueError,r'clean previous Triton-cache qualification \(failed\)'):check_predecessor(ledger.events(),dict(request5,job_id=JOB6,fifth_predecessor_finish=request5['fourth_predecessor_finish'],fifth_predecessor_trace=request5['fourth_predecessor_trace']))
 def test_consumed006_cannot_retry_and_005_grant_cannot_be_reused(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture006(Path(d))
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    ledger.authorize_depth_driver_qualification_triton_cache(record);ledger.reserve(JOB6,request['command'],dict(request=record));ledger.finish(JOB6,'failed',1,cleanup_confirmed=True)
    before=ledger.events()
    with self.assertRaisesRegex(ValueError,'consumed'):ledger.authorize_depth_driver_qualification_triton_cache(record)
    with self.assertRaisesRegex(ValueError,'consumed'):ledger.reserve(JOB6,request['command'],dict(request=record))
   self.assertEqual(before,ledger.events())
 def test_006_requires_method009_paths_for_actual_requests(self):
  from vipe_benchmark.depth_driver_qualification_triton_cache import ATTEMPTS
  self.assertEqual(ATTEMPTS[JOB6]['method'],'moge-driver-method-009');self.assertEqual(ATTEMPTS[JOB6]['previous'],JOB)
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture006(Path(d))
   cpu=read_json(request['cpu_validation']['path']);cpu.update(record_kind='actual',commands=[dict(returncode=0,timed_out=False,cleanup=dict(confirmed_no_surviving_observed_processes=True,surviving_observed_owned_processes=[]))])
   Path(request['cpu_validation']['path']).write_text(json.dumps(cpu))
   actual=dict(request,record_kind='actual',cpu_validation=file_record(request['cpu_validation']['path']))
   with self.assertRaisesRegex(ValueError,'versioned attempt producer'):validate_request(rewrite(record,actual))
 def test_006_grant_cannot_reserve_another_attempt(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture006(Path(d))
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    ledger.authorize_depth_driver_qualification_triton_cache(record);before=ledger.events()
    with self.assertRaises(ValueError):ledger.reserve(JOB,request['command'],dict(request=record))
   self.assertEqual(before,ledger.events())
 def test_method009_sources_are_in_D6_closure(self):
  from vipe_benchmark.depth_admission import local_source_records
  with patch('vipe_benchmark.depth_admission.file_record',side_effect=lambda path:dict(path=str(path))):paths={r['path'] for r in local_source_records('D6')}
  for suffix in ['moge-driver-method-009/producer.py','moge-driver-method-009/network_guard.py','moge-driver-method-009/startup.py']:
   self.assertTrue(any(p.endswith(suffix) for p in paths),suffix)


JOB7='plan069-D6-driver-qualification-007'


def fixture007(root, previous_status='complete'):
 ledger,record6,request6,sources,live=fixture006(root)
 with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
  ledger.authorize_depth_driver_qualification_triton_cache(record6);ledger.reserve(JOB6,request6['command'],dict(request=record6));finish=ledger.finish(JOB6,previous_status,1,cleanup_confirmed=True)
 def save(name,value):
  path=root/name;write_json(path,value);return file_record(path)
 sixth=save('finished006.json',finish)
 trace=Path(request6['output']).with_suffix('.syscalls.log');trace.write_text('qualification006 fixture trace')
 worker=save('producer010.py',{'fixture':True});guard=save('guard010.py',{'fixture':True});startup=save('startup010.py',{'fixture':True});sources=[worker,guard,startup]
 source=read_json(request6['source_review']['path']);source['local_sources']=sources
 lineage=dict(job_id=JOB7,worker=worker,network_guard=guard,guard_startup=startup,sixth_predecessor_finish=sixth,sixth_predecessor_trace=file_record(trace))
 request=dict(request6,output=str(root/'qualification007'),**lineage)
 proposal=dict(read_json(request6['review']['path'])['proposal'],**lineage)
 request['review']=save('review007.json',dict(schema='plan069-D6-driver-qualification-review/v5',status='REVIEW',proposal=proposal))
 request['authorization']=save('DO007.json',dict(schema='plan069-D6-driver-qualification-authorization/v5',status='DO',review=request['review'],proposal_sha256=object_hash(proposal)))
 request['source_review']=save('source007.json',source)
 request['cpu_validation']=save('cpu007.json',dict(schema='plan069-delta-cpu-test-capture/v1',record_kind='fixture',passed=True,within_wall_limit=True,source_bytes_unchanged=True,sources_before=sources,sources_after=sources))
 path=root/'request007.json';command=list(request6['command']);command[10]=str(Path(request['output']).with_suffix('.syscalls.log'));command[14]=worker['path'];command[17]=str(path);command[19]=request['output'];request['command']=command;write_json(path,request)
 return ledger,file_record(path),request,sources,live


class QualificationTritonCacheRebindTests(unittest.TestCase):
 def test_fresh007_after_passed006_preserves_all_attempts(self):
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture007(Path(d))
   with patch('vipe_benchmark.depth_admission.local_source_records',return_value=sources),patch('vipe_benchmark.execution.resources',return_value=live):
    ledger.authorize_depth_driver_qualification_triton_cache(record);reserve=ledger.reserve(JOB7,request['command'],dict(request=record))
   self.assertEqual(reserve['seconds'],180);self.assertEqual(ledger.states()[JOB6]['status'],'complete');self.assertEqual(ledger.states()[JOB]['status'],'failed')
 def test_007_requires_the_passed006_not_a_failed_one(self):
  from vipe_benchmark.depth_driver_qualification_triton_cache import check_predecessor
  with tempfile.TemporaryDirectory() as d:
   ledger,record,request,sources,live=fixture007(Path(d),previous_status='failed')
   with self.assertRaisesRegex(ValueError,r'previous Triton-cache qualification \(complete\)'):check_predecessor(ledger.events(),request)
 def test_method010_serves_only_qualification007(self):
  from vipe_benchmark.config import ROOT
  from vipe_benchmark.depth_driver_qualification_triton_cache import ATTEMPTS
  self.assertEqual(ATTEMPTS[JOB7]['method'],'moge-driver-method-010');self.assertEqual(ATTEMPTS[JOB7]['previous'],JOB6)
  source=(ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-010/producer.py').read_text()
  self.assertIn("require(JOB == 'plan069-D6-driver-qualification-007'",source)
  guard=lambda n:(ROOT/f'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-0{n}/network_guard.py').read_bytes()
  self.assertEqual(guard(10),guard('07'))
 def test_method010_sources_are_in_D6_closure(self):
  from vipe_benchmark.depth_admission import local_source_records
  with patch('vipe_benchmark.depth_admission.file_record',side_effect=lambda path:dict(path=str(path))):paths={r['path'] for r in local_source_records('D6')}
  for suffix in ['moge-driver-method-010/producer.py','moge-driver-method-010/network_guard.py','moge-driver-method-010/startup.py']:
   self.assertTrue(any(p.endswith(suffix) for p in paths),suffix)

 def test_008_rebinds_after_passed007_with_method011(self):
  from vipe_benchmark.config import ROOT
  from vipe_benchmark.depth_driver_qualification_triton_cache import ATTEMPTS
  row=ATTEMPTS['plan069-D6-driver-qualification-008']
  self.assertEqual((row['method'],row['previous'],row['previous_status']),('moge-driver-method-011',JOB7,'complete'))
  self.assertEqual(row['lineage'][:-2],ATTEMPTS[JOB7]['lineage'])
  source=(ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-011/producer.py').read_text()
  self.assertIn("require(JOB == 'plan069-D6-driver-qualification-008'",source)
  guard=lambda n:(ROOT/f'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-0{n}/network_guard.py').read_bytes()
  self.assertEqual(guard(11),guard('07'))



class QualificationReplacementSetupTests(unittest.TestCase):
 def test_009_is_the_only_attempt_that_switches_setup(self):
  from vipe_benchmark.depth_driver_qualification_triton_cache import ATTEMPTS
  row=ATTEMPTS['plan069-D6-driver-qualification-009']
  self.assertEqual((row['method'],row['previous'],row['previous_status'],row['replaced_setup_job']),
                   ('moge-driver-method-012','plan069-D6-driver-qualification-008','complete','plan069-D6-setup-recovery-002'))
  self.assertEqual([job for job,attempt in ATTEMPTS.items() if attempt.get('replaced_setup_job')],['plan069-D6-driver-qualification-009'])
 def test_replacement_setup_must_be_the_accepted_replacement_of_the_retained_setup(self):
  from vipe_benchmark.depth_driver_qualification_triton_cache import _require_replacement_setup
  with tempfile.TemporaryDirectory() as d:
   root=Path(d).resolve();(root/'jobs/plan069-D6-setup-recovery-002').mkdir(parents=True)
   setup=dict(path=str(root/'jobs/plan069-D6-setup-recovery-002/result.json'));original=dict(path='original')
   lineage=dict(original=dict(setup=original),request=dict(path='rr'),review=dict(path='rv'))
   request=dict(ledger_path=str(root/'ledger.jsonl'),setup=setup,setup_request=lineage['request'],setup_dispatch=lineage['review'])
   with patch('vipe_benchmark.depth_moge_runtime_replacement.accepted_setup_lineage',return_value=lineage):
    _require_replacement_setup(request,dict(setup=original),'plan069-D6-setup-recovery-002',[])
    for changed,retained in ((dict(request,setup_dispatch=dict(path='other')),dict(setup=original)),(request,dict(setup=dict(path='foreign'))),
                             (dict(request,setup=dict(path=str(root/'jobs/plan069-D6-setup-001/result.json'))),dict(setup=original))):
     with self.subTest(changed=changed),self.assertRaisesRegex(ValueError,'runtime replacement'):
      _require_replacement_setup(changed,retained,'plan069-D6-setup-recovery-002',[])
 def test_method012_binds_recovered_setup_and_libcuda_path(self):
  import importlib.util
  from vipe_benchmark.config import ROOT
  path=ROOT/'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-012/producer.py'
  source=path.read_text()
  self.assertIn("require(JOB == 'plan069-D6-driver-qualification-009'",source)
  self.assertIn("'plan069-depth-setup-recovery-result/v1'",source)
  self.assertNotIn("dispatched.get('schema') == 'plan069-depth-setup-dispatch/v1'",source)
  spec=importlib.util.spec_from_file_location('method012',path);module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
  output=Path('/run/jobs/plan069-D6-driver-qualification-009');temporary='/run/jobs/plan069-D6-driver-qualification-009-temporary/'
  env={name:temporary+folder for name,folder in module.SUPERVISED_TRITON}
  module.select_triton_cache(env,output,dict(cache_directory='/bound',libcuda_path='/usr/lib/x86_64-linux-gnu'))
  self.assertEqual((env['TRITON_CACHE_DIR'],env['TRITON_LIBCUDA_PATH']),('/bound','/usr/lib/x86_64-linux-gnu'))
  with self.assertRaisesRegex(ValueError,'bound libcuda directory required'):
   module.select_triton_cache({name:temporary+folder for name,folder in module.SUPERVISED_TRITON},output,dict(cache_directory='/bound'))
  guard=lambda n:(ROOT/f'docs/research/vipe-alternatives/plan031-execution/moge-driver-method-0{n}/network_guard.py').read_bytes()
  self.assertEqual(guard(12),guard('07'))
 def test_attempt_runtime_pins_the_helper_cache_schema(self):
  import inspect
  from vipe_benchmark import depth_driver_qualification_triton_cache as module
  self.assertIn("(SCHEMA_V2 if attempt.get('replaced_setup_job') else SCHEMA)",inspect.getsource(module.validate_request))
