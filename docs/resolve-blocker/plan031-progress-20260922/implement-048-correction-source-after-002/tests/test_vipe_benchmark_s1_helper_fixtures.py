"""Importable CPU faults, reachable only through injected disposable sessions."""
import json
import os
from pathlib import Path
import signal
import struct
import sys
import time

from vipe_benchmark.s1_helper_session import Owner, Session, THREADS, identity


class FaultOwner(Owner):
    mode = 'normal'
    released = False

    def run(self):
        if self.mode == 'owner_block':
            time.sleep(.15)
        super().run()

    def spawn(self, role, actions, env):
        env = dict(env, PYTHONPATH=env['PYTHONPATH']+os.pathsep+str(Path(__file__).parent))
        pid = os.posix_spawn(sys.executable,
            [sys.executable, '-B', '-m', 'test_vipe_benchmark_s1_helper_fixtures', role, self.session.token, '100', self.mode],
            env, file_actions=actions, setsid=True)
        if role == 'work' and self.mode in ('held_spawn','late_spawn'):
            time.sleep(.16 if self.mode == 'held_spawn' else .45)
        return pid

    def observe_identity(self, pid):
        value = super().observe_identity(pid)
        if self.mode == 'identity_failure':
            raise ValueError('fixture identity capture after actual spawn')
        return value

    def observe(self):
        if self.mode == 'census_block' and getattr(self,'armed',False) and not self.released:
            self.block_entered = time.monotonic()
            while not self.released: time.sleep(.005)
        if self.mode == 'census_error' and getattr(self,'armed',False) and not self.released:
            raise OSError('fixture active census enumeration failure')
        if self.mode == 'enumeration_failure' and self.cancelled and not self.released:
            raise OSError('fixture enumeration failure')
        return super().observe()

    def signal_group(self, pid, sig):
        if self.mode == 'signal_failure' and not self.released:
            raise OSError('fixture signal failure')
        super().signal_group(pid, sig)

    def reap_child(self, pid):
        if self.mode == 'reap_failure' and not self.released:
            raise OSError('fixture reap failure')
        return super().reap_child(pid)


def session(mode='normal', instance=None, **kwargs):
    class Selected(FaultOwner):
        pass
    Selected.mode = mode
    instance = Session.__new__(Session) if instance is None else instance
    instance.__init__(owner_factory=Selected, **kwargs)
    return instance


def main(role, token, fd, mode):
    from vipe_benchmark.s1_cpu_helper import main as serve, session_operation
    boot = Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    def ready(channel):
        payload = dict(identity(os.getpid()), threads={key:os.environ.get(key) for key in THREADS})
        message = dict(version=1, session=token, boot_id=boot, role=role, request_id=0, kind='ready', payload=payload)
        if role == 'work':
            if mode in ('child_block','late_ready'):
                time.sleep(.2)
            if mode == 'partial_header':
                channel.send(b'\x00\x00'); time.sleep(10)
            if mode == 'stalled_body':
                channel.send(struct.pack('!I',100)+b'{'); time.sleep(10)
            if mode == 'eof_frame':
                channel.send(struct.pack('!I',100)+b'{'); os._exit(7)
            if mode == 'oversized':
                channel.send(struct.pack('!I',65537)); time.sleep(10)
            if mode == 'wrong_role':
                message['role'] = 'sample'
            if mode in ('early_encoder','early_partial'):
                raw=json.dumps(message).encode(); channel.send(struct.pack('!I',len(raw))+raw)
                # An out-of-band fixture barrier permits deterministic early bytes
                # while the production request remains unencoded or backpressured.
                import socket
                barrier=Path(os.environ['S1_EARLY_BARRIER'])
                while not barrier.exists(): time.sleep(.001)
                reply=dict(message,kind='response',request_id=1,payload=dict(operation='constant',ok=True,value=37,acquisition_start=None,acquisition_end=None))
                raw=json.dumps(reply).encode(); channel.send(struct.pack('!I',len(raw))+raw)
                barrier.with_suffix('.sent').write_text('sent')
                time.sleep(10)
            if mode in ('stalled_reader','wrong_role'):
                raw=json.dumps(message).encode(); channel.send(struct.pack('!I',len(raw))+raw); time.sleep(10)
            if mode == 'descendant':
                os.posix_spawn(sys.executable,[sys.executable,'-B','-c','import time; time.sleep(10)'],os.environ,
                    file_actions=[(os.POSIX_SPAWN_CLOSE,int(fd))])
            if mode == 'ignore_term':
                signal.signal(signal.SIGTERM, signal.SIG_IGN)
    def operation(operation, session_token, sequence):
        if mode.startswith('progress_'):
            return progress_operation(operation,session_token,sequence,mode)
        if mode == 'exit_transport' and role == 'work':
            os._exit(8)
        if role == 'sample' and mode in ('sample_late','phase_late','post_task'):
            time.sleep({'sample_late':1.05,'phase_late':.2,'post_task':.06}[mode])
        if mode == 'artifact' and role == 'work':
            return artifact_checks(operation, session_token, sequence)
        return session_operation(operation,session_token,sequence)
    serve(role,token,fd,operation_runner=operation,before_ready=ready)


def artifact_checks(operation, token, sequence):
    """Exercise real adapters and strict references with a tiny owned fixture."""
    from unittest.mock import patch
    from vipe_benchmark import s1_cpu_helper as helper
    from vipe_benchmark.files import read_json, write_json, file_record
    args = operation['args']
    local = Path(args['value']['local'])
    reservation = dict(sequence=7,event_sha256='a'*64)
    summary = dict(counts=dict(complete=510), produced_identities=list(range(510)),
        qualified_identities=list(range(510)), verification_errors=['raw retained error'],runtime={})
    common = dict(local=str(local), reservation=reservation, config={}, outcome={}, deadline=time.monotonic()+1)
    with patch.object(helper,'run',return_value=summary):
        reference = helper.session_operation(dict(operation='reconcile',args=common),token,sequence)
    publish = dict(operation='publish',args=dict(common,docs=str(local),outcome=dict(evidence_summary_record=reference)))
    rejected=[]
    with patch.object(helper,'run',side_effect=lambda op:op['args']['outcome']):
        valid=helper.session_operation(publish,token,sequence+1)
        for label in ('session','reservation','missing','tamper'):
            changed=json.loads(json.dumps(publish))
            ref=changed['args']['outcome']['evidence_summary_record']
            if label == 'session': ref['session']='foreign'
            elif label == 'reservation': ref['reservation']['sequence']=8
            elif label == 'missing': ref['record']['path']=str(local/'missing.json')
            else: ref['record']['sha256']='0'*64
            try:
                helper.session_operation(changed,token,sequence+1)
            except (ValueError,OSError):
                rejected.append(label)
            else:
                raise AssertionError('invalid summary reference accepted: '+label)
    assert valid['evidence_summary'] == summary
    assert valid['evidence_summary_record'] == reference
    return dict(rejected=rejected, counts=summary['counts'], identities=len(valid['evidence_summary']['produced_identities']),reference=reference)




def progress_fixture(root,*,states=False):
    """Small shared real numerical artifacts, mixed admitted fit/selection rows."""
    import copy
    from test_vipe_benchmark_s1_recovery import synthetic_inputs, synthetic_row
    from vipe_benchmark.config import load
    from vipe_benchmark.files import write_json,file_record
    root=Path(root);root.mkdir(parents=True,exist_ok=True)
    def put(name,value):
        path=root/name;write_json(path,value);return file_record(path)
    request=dict(job_id='S1-calibration-recovery-001',inputs=synthetic_inputs(root/'inputs',put,load()))
    observed=None
    if states:
        from test_vipe_benchmark_s1_recovery import synthetic_assets
        assets,runtime,observed=synthetic_assets(root,put)
        request.update(assets=assets,runtime=runtime,forbidden_vipe_roots=['/fixture/vipe'])
    request['recovery_authorization']=put('authorization.json',{'disposable':True,'semantic_amendment':{'disposable':True}})
    request_record=put('request.json',request)
    row,_=synthetic_row(root/'numeric',request)
    second=copy.deepcopy(row);second['identity']['frame']=150
    return dict(root=str(root),request=request,request_record=request_record,rows=[row,second],observed_runtime=observed)


def progress_reservation(fixture,seconds=1.4):
    return dict(event='reserve',job_id='S1-calibration-recovery-001',sequence=7,event_sha256='a'*64,
        boot_id=Path('/proc/sys/kernel/random/boot_id').read_text().strip(),monotonic_start=time.monotonic(),seconds=seconds,
        evidence=dict(request=fixture['request_record'],authorization=fixture['request']['recovery_authorization']))


def child_progress_trace(fixture,clock,session,sequence):
    """Bounded child evidence; missing terminal event is incomplete, never valid."""
    import contextlib
    from unittest.mock import patch
    from vipe_benchmark import s1_progress as p
    @contextlib.contextmanager
    def tracing():
        path=Path(fixture['root'])/('child-progress-'+str(os.getpid())+'.jsonl')
        actual=p.trace_event;count=[0];dropped=[0];lost=[False];terminal=[False]
        publication=dict(producer=None,sequence=None,versions=[],request_id=sequence)
        original_publish=p.Publisher._publish
        def publish(publisher):
            publication.update(producer=publisher.producer,sequence=publisher.sequence+1,
                versions=[row['version'] for row in publisher.rows.values()],request_id=publisher.request_id)
            return original_publish(publisher)
        def gate():
            if time.monotonic()>=clock.total_deadline:raise TimeoutError('child trace original cleanup cutoff')
        def event(phase,state):
            actual(phase,state)
            if lost[0]:return
            count[0]+=1
            if count[0]>4096:
                dropped[0]+=1
                if dropped[0]!=1:return
            try:
                gate();now=time.monotonic()
                finished=state=='terminal'
                row=dict(index=count[0],phase=phase,state=state,observed=now,session=session,
                    reservation=clock.mapping()['reservation'],work_deadline=clock.work_deadline,total_deadline=clock.total_deadline,
                    request=fixture['request_record'],pid=os.getpid(),overflow=dropped[0],valid=dropped[0]==0,
                    terminal=finished,**publication)
                gate();text=json.dumps(row,separators=(',',':'))+'\n'
                gate();raw=text.encode()
                gate()
                with path.open('ab',buffering=0) as stream:
                    gate()
                    if stream.write(raw)!=len(raw):raise OSError('child boundary trace short write')
                    gate()
                if finished:terminal[0]=True
            except BaseException:
                # No diagnostic I/O after C. A lost/partial tail cannot obtain
                # the mandatory terminal witness used by the parent.
                lost[0]=True
                raise
        with patch.object(p.Publisher,'_publish',publish),patch.object(p,'trace_event',side_effect=event):
            try:yield path
            finally:
                if not lost[0] and not terminal[0]:
                    pending=__import__('sys').exception()
                    try:event('child_trace_exit','terminal')
                    except BaseException as error:
                        if pending is None:raise
                        pending.add_note('child trace unavailable: '+str(error))
    return tracing()


def progress_operation(operation,token,sequence,mode):
    from vipe_benchmark.s1_clock import ReservationClock
    from vipe_benchmark.files import read_json
    from vipe_benchmark import s1_progress as p
    args=operation.get('args',{});data=args.get('value',args)
    fixture=data.get('progress_fixture')
    if fixture is None and 'local' in args:
        path=Path(args['local'])/'progress-fixture.json'
        if path.exists():fixture=read_json(path)
    if fixture is None:return _progress_operation(operation,token,sequence,mode)
    if 'reservation' in args:clock=ReservationClock.from_reservation(args['reservation'])
    else:
        reference=data.get('progress_context',args.get('progress_context'))
        if reference is None:return _progress_operation(operation,token,sequence,mode)
        clock=ReservationClock.from_mapping(p.read_record(reference,p.SMALL_BYTES)['clock'])
    with child_progress_trace(fixture,clock,token,sequence):return _progress_operation(operation,token,sequence,mode)


def _progress_operation(operation,token,sequence,mode):
    from vipe_benchmark import s1_progress as progress
    from vipe_benchmark.s1_clock import ReservationClock
    from vipe_benchmark.files import read_json,write_json,file_record
    from vipe_benchmark.config import load
    from vipe_benchmark.s1_evidence import input_loader,reconcile_rows
    args=operation.get('args',{});name=operation['operation']
    if name=='prelaunch':
        request=read_json(args['reservation']['evidence']['request']['path'])
        clock=ReservationClock.from_reservation(args['reservation'])
        return progress.prepare_context(Path(args['local']),clock,request,args['reservation']['evidence']['authorization'],token,identity(os.getpid()),load())
    data=args.get('value',args)
    if name=='constant' and 'progress_fixture' not in data:
        marker=data.get('progress_fail_marker') or os.environ.get('S1_PROGRESS_SAMPLE_FAIL')
        if marker and Path(marker).exists():raise ValueError('fixture final sample failed')
        from vipe_benchmark.s1_cpu_helper import session_operation
        clean=dict(data);clean.pop('progress_fail_marker',None)
        return session_operation(dict(operation='constant',args=dict(value=clean)),token,sequence)
    if name in ('reconcile','accept') or 'progress_fixture' in data:
        fixture=data.get('progress_fixture')
        if fixture is None:fixture=read_json(Path(args['local'])/'progress-fixture.json')
        reference=data.get('progress_context',args.get('progress_context'))
        output=Path(data.get('output',args.get('output',Path(args.get('local',fixture['root']))/'jobs'/'S1-calibration-recovery-001')))
        output.mkdir(parents=True,exist_ok=True)
        for i,row in enumerate(fixture['rows']):
            path=output/(str(i)+'-produced-row.json')
            if not path.exists():write_json(path,row)
        clock=ReservationClock.from_mapping(progress.read_record(reference,progress.SMALL_BYTES)['clock'])
        publisher=progress.Publisher(reference,'reconcile',sequence,clock=clock,request=fixture['request'])
        original=publisher.seal
        def seal(*a,**k):
            value=original(*a,**k)
            if publisher.sequence==1:
                if mode=='progress_death':progress.trace_event('P03_child_exit','terminal');os._exit(9)
            if publisher.sequence==2 and mode=='progress_block':progress.trace_event('P02_block_entered','terminal');time.sleep(10)
            return value
        publisher.seal=seal
        real_replace=progress.os.replace
        def replace(*a,**k):
            if mode=='progress_torn' and a[0]=='head.tmp' and publisher.sequence==1:
                progress.trace_event('P05_pre_head_replace','terminal');os._exit(10)
            return real_replace(*a,**k)
        from unittest.mock import patch
        try:
            if mode=='progress_final':
                from vipe_benchmark.s1_evidence import first_record,qualify_runtime,qualify_row
                clock=ReservationClock.from_mapping(publisher.context['clock'])
                runtime=fixture['observed_runtime'];qualify_runtime(runtime,fixture['request']);clock.observe()
                write_json(output/'partial-runtime.json',runtime)
                publisher.runtime['partial-runtime.json']=file_record(output/'partial-runtime.json')
                publisher.first_result=first_record(fixture['request'],output,'passed',clock=clock,
                    rows=fixture['rows'][:1],runtime=runtime,checks=qualify_row(fixture['rows'][0],fixture['request'],first=True),raw=[fixture['rows'][0]['diagnostics']])
            with patch.object(progress.os,'replace',side_effect=replace):
                summary=reconcile_rows(output,fixture['request'],deadline=publisher.deadline,publisher=publisher)
            marker=str(Path(args['local'])/'sample-fail') if 'local' in args else os.environ.get('S1_PROGRESS_SAMPLE_FAIL')
            if mode=='progress_final':
                clock.observe();publisher.publish()
                if marker:Path(marker).write_text('guarded rows first runtime before failed sample')
            return [None,None] if name=='accept' else summary
        finally:publisher.close()
    raise ValueError('unexpected progress fixture operation')


def progress_worker(fixture_path,output):
    from vipe_benchmark.s1_progress import Publisher,publish_segment_row
    from vipe_benchmark.s1_clock import ReservationClock
    from vipe_benchmark.s1_evidence import input_loader
    fixture=json.loads(Path(fixture_path).read_text());output=Path(output);output.mkdir(parents=True)
    clock=ReservationClock.from_mapping(json.loads(os.environ['VIPE_S1_RESERVATION_CLOCK']))
    publisher=Publisher(json.loads(os.environ['VIPE_S1_PROGRESS_CONTEXT']),'worker',1,clock=clock,request=fixture['request'])
    loader=input_loader(fixture['request'])
    try:
        with child_progress_trace(fixture,clock,publisher.context['session'],1):
            for i,row in enumerate(fixture['rows']):
                publish_segment_row(row,fixture['request'],loader,clock,publisher,output/(str(i)+'-produced-row.json'),output/(str(i)+'-qualified-row.json'),first=i==0)
            from vipe_benchmark import s1_progress as p
            p.trace_event('P01_worker_wait','terminal')
            time.sleep(10)
    finally:publisher.close()


def inline_progress(root,clock,request,config):
    """Real metadata/socket protocol driven serially in existing pure worker tests."""
    import contextlib,uuid
    from unittest.mock import patch
    from vipe_benchmark import s1_progress as p
    @contextlib.contextmanager
    def owned():
        ref=p.prepare_context(root,clock,request,request['recovery_authorization'],uuid.uuid4().hex,identity(os.getpid()),config,owner_pid=os.getpid())
        cache=p.RetainedProgress();binding=p.process_binding(identity(os.getpid()))
        consumer=p.Consumer(ref,cache,lambda:False,lambda producer:(binding,1))
        actual=p.Publisher.after_notice
        def pulse(publisher):consumer.tick()
        try:
            with patch.dict(os.environ,{'VIPE_S1_PROGRESS_CONTEXT':json.dumps(ref)}),patch.object(p.Publisher,'after_notice',pulse):yield ref,cache
        finally:consumer.close()
    return owned()


if __name__ == '__main__':
    main(*sys.argv[1:])


def plan047_state(fixture, root, *, qualified=True):
    """Real serial producer/consumer with one shared numerical row and no child."""
    import contextlib,uuid
    from types import SimpleNamespace
    from unittest.mock import patch
    from vipe_benchmark import s1_progress as p,s1_evidence as evidence
    from vipe_benchmark.s1_clock import ReservationClock
    from vipe_benchmark.files import write_json,file_record
    from vipe_benchmark.config import load
    root=Path(root)
    @contextlib.contextmanager
    def state():
        root.mkdir(parents=True);(root/'jobs').mkdir()
        clock=ReservationClock.from_reservation(progress_reservation(fixture,3600))
        reference=p.prepare_context(root,clock,fixture['request'],fixture['request']['recovery_authorization'],uuid.uuid4().hex,identity(os.getpid()),load(),owner_pid=os.getpid())
        cache=p.RetainedProgress();cancelled=[False];binding=p.process_binding(identity(os.getpid()))
        consumer=p.Consumer(reference,cache,lambda:cancelled[0],lambda producer:(binding,1))
        publisher=None
        try:
            with patch.object(p.Publisher,'after_notice',side_effect=lambda:consumer.tick()):
                publisher=p.Publisher(reference,'worker',1,clock=clock,request=fixture['request'])
                row=fixture['rows'][0];path=root/'row.json';write_json(path,row)
                evidence.produced_row(row,fixture['request'],deadline=clock.work_deadline)
                publisher.seal(row,file_record(path))
                if qualified:
                    evidence.qualify_row(row,fixture['request'],first=True,deadline=clock.work_deadline)
                    publisher.seal(row,file_record(path),qualified=True)
                yield SimpleNamespace(root=root,p=p,clock=clock,reference=reference,cache=cache,consumer=consumer,
                    publisher=publisher,fixture=fixture,cancelled=cancelled,row=row,row_record=file_record(path))
        finally:
            try:
                if publisher is not None:publisher.close()
            finally:consumer.close()
    return state()


def plan047_full_fixture(test):
    """One original full numerical result with an actual disposable admission."""
    from types import SimpleNamespace
    from test_vipe_benchmark_s1_recovery import S1RecoveryTests,synthetic_row
    from vipe_benchmark import s1_recovery as recovery,s1_evidence as evidence
    from vipe_benchmark.access import output_identities
    from vipe_benchmark.files import write_json,file_record,read_json
    fixture=S1RecoveryTests();fixture.setUp();test.addCleanup(fixture.doCleanups)
    _,request,binding=fixture.register();command=fixture.command(binding)
    reservation=fixture.ledger.reserve(recovery.JOB,command,binding)
    clock=recovery.captured_clock(fixture.root,fixture.config,reservation,command)
    output=fixture.root/'jobs'/recovery.JOB;output.mkdir();write_json(output/'config.json',request)
    row,_=synthetic_row(fixture.root/'plan047-numeric',request)
    rows=[dict(row,identity=i.record()) for i in output_identities(fixture.config,'calibration')]
    first=evidence.first_record(request,output,'passed',clock=clock,rows=rows[:1],runtime=fixture.observed,checks=evidence.qualify_row(row,request,first=True),raw=[row['diagnostics']])
    result=dict(status='complete',job_id=recovery.JOB,component='S1',branch='calibration',rows=rows,runtime=fixture.observed,native_wall_seconds=sum(r['native_group_wall_seconds'] for r in rows),peak_allocated_bytes=1024,peak_reserved_bytes=2048,configuration=file_record(output/'config.json'),first_result=first,reservation_clock=clock.mapping())
    write_json(output/'result.json',result)
    return SimpleNamespace(fixture=fixture,request=request,binding=binding,command=command,reservation=reservation,clock=clock,output=output,result=result)



def invalidated_fallback(test,fixture,root,kind):
    """Real acknowledged reconcile fallback, then its actual failure transition."""
    from types import SimpleNamespace
    from vipe_benchmark import s1_progress as p,s1_evidence as e,supervisor as sup
    from vipe_benchmark.files import write_json,file_record
    with plan047_state(fixture,root) as state:
        output=state.root/'fallback';output.mkdir()
        row=fixture['rows'][1];path=output/'one-produced-row.json';write_json(path,row)
        if kind.startswith('result_'):write_json(output/'result.json',dict(rows=[row]))
        publisher=p.Publisher(state.reference,'reconcile',1,clock=state.clock,trusted=state.cache.reference())
        try:
            result=e.reconcile_rows(output,fixture['request'],deadline=state.clock.work_deadline,publisher=publisher)
            test.assertEqual(result['counts']['produced_lower_bound'],2)
            reference=state.cache.reference();pointer=state.cache.snapshot
            test.assertEqual(reference['counts']['qualified'],2)
            test.assertIn('reconcile',reference['checkpoints'])
            history={str(q):file_record(q) for q in Path(state.reference['path']).parent.rglob('*.json')}
            if kind.startswith('member_add') or kind=='fallback_invalidated':write_json(output/'two-produced-row.json',row)
            elif kind.startswith('member_remove'):path.unlink()
            elif kind.startswith('member_rename'):path.rename(output/'renamed-produced-row.json')
            elif kind.startswith('result_'):(output/'result.json').write_bytes(b'{}')
            elif kind.startswith('row_'):path.write_bytes(path.read_bytes()+b' ')
            else:raise AssertionError(kind)
            with test.assertRaises(p.ProgressIntegrityError) as caught:publisher.publish()
            lifecycle=SimpleNamespace(progress=state.cache,poisoned=False)
            frozen=sup.record_progress_failure(lifecycle,caught.exception,'reconciliation')
            test.assertTrue(lifecycle.poisoned);test.assertTrue(publisher.stopped)
            test.assertTrue(frozen['frozen']);test.assertEqual(frozen['integrity_status'],'failed')
            test.assertIs(state.cache.snapshot,pointer)
            test.assertEqual(frozen['counts'],reference['counts'])
            test.assertEqual({str(q):file_record(q) for q in Path(state.reference['path']).parent.rglob('*.json')},history)
            with test.assertRaisesRegex(ValueError,'unverified'):p.recover(frozen)
            return dict(acknowledged=reference,invalidated=frozen,history=history,stop_required=lifecycle.poisoned,error_class=type(caught.exception).__name__)
        finally:publisher.close()
