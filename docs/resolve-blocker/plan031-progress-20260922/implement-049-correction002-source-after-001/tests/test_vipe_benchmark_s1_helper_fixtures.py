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
        from vipe_benchmark.s1_helper_session import create_owned_process
        pid = create_owned_process('Owner.run '+role,os.posix_spawn,sys.executable,
            [sys.executable, '-B', '-m', 'test_vipe_benchmark_s1_helper_fixtures', role, self.session.token, '100', self.mode],
            env,deadline=self.session.ready_deadline,file_actions=actions,setsid=True)
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
                from vipe_benchmark.s1_helper_session import create_owned_process,register_owned,retire_owned
                child=create_owned_process('helper fixture descendant',os.posix_spawn,sys.executable,
                    [sys.executable,'-B','-c','import time; time.sleep(10)'],os.environ,file_actions=[(os.POSIX_SPAWN_CLOSE,int(fd))])
                try:register_owned(child,'helper fixture descendant')
                except BaseException as primary:
                    try:os.kill(child,signal.SIGKILL);os.waitpid(child,0);retire_owned(child)
                    except BaseException as cleanup:
                        primary.s1_owned_pid=child;primary.add_note('descendant retirement: '+repr(cleanup))
                    raise
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
        publication=dict(producer=None,sequence=None,versions=[],request_id=sequence,binding=None,previous=None,installed=False,head_installed=False,acknowledged=False)
        original_publish=p.Publisher._publish
        def publish(publisher):
            terminal[0]=False
            publication.update(producer=publisher.producer,sequence=publisher.sequence+1,
                versions=[row['version'] for row in publisher.rows.values()],request_id=publisher.request_id,binding=dict(publisher.binding),previous=publisher.previous,installed=False,head_installed=False,acknowledged=False)
            result=original_publish(publisher)
            publication['acknowledged']=True
            event('producer_acknowledged','boundary')
            return result
        def gate():
            if time.monotonic()>=clock.total_deadline:raise TimeoutError('child trace original cleanup cutoff')
        def event(phase,state):
            actual(phase,state)
            if lost[0]:return
            if publication['producer'] is None and not phase.startswith('raw_guard:'):return
            # Explicit required boundary vocabulary; primitive read/stat loops
            # are independently covered by the114 observations, not duplicated.
            if state not in ('boundary','terminal') and phase not in ('write','flush','fsync','close','read_record','raw_guard:produced_row','raw_guard:qualify_row'):return
            if phase=='generation_directory_fsync':publication['installed']=True
            if phase=='head_directory_fsync':publication['head_installed']=True
            count[0]+=1
            if count[0]>4096:
                dropped[0]+=1
                if dropped[0]!=1:return
            try:
                gate();now=time.monotonic()
                finished=state=='terminal' or phase=='producer_acknowledged'
                row=dict(index=count[0],phase=phase,state=state,observed=now,session=session,
                    reservation=clock.mapping()['reservation'],work_deadline=clock.work_deadline,total_deadline=clock.total_deadline,
                    request=fixture['request_record'],pid=os.getpid(),boot_id=clock.boot_id,overflow=dropped[0],valid=dropped[0]==0,
                    terminal=finished,late_suffix=fixture.get('late_suffix') if phase=='P01_late_suffix' else None,**publication)
                gate();text=json.dumps(row,separators=(',',':'))+'\n'
                gate();raw=text.encode()
                gate()
                with path.open('ab',buffering=0) as stream:
                    gate()
                    if stream.write(raw)!=len(raw):raise OSError('child boundary trace short write')
                    gate()
                terminal[0]=finished
            except BaseException:
                # No diagnostic I/O after C. A lost/partial tail cannot obtain
                # the mandatory terminal witness used by the parent.
                lost[0]=True
                raise
        from vipe_benchmark import s1_evidence as e
        def guard(name,operation):
            def observed(*args,**kwargs):
                if time.monotonic()<clock.work_deadline:event('raw_guard:'+name,'start')
                result=operation(*args,**kwargs)
                event('raw_guard:'+name,'completed');p.before(clock.work_deadline)
                return result
            return observed
        with patch.object(p.Publisher,'_publish',publish),patch.object(p,'trace_event',side_effect=event),patch.object(e,'produced_row',side_effect=guard('produced_row',e.produced_row)),patch.object(e,'qualify_row',side_effect=guard('qualify_row',e.qualify_row)):
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
            while time.monotonic()<clock.work_deadline:time.sleep(min(.001,max(0.,clock.work_deadline-time.monotonic())))
            from vipe_benchmark import s1_evidence as e,s1_recovery as recovery
            from unittest.mock import patch
            import contextlib
            reservation=dict(event='reserve',monotonic_start=clock.monotonic_start,seconds=clock.effective_seconds)
            attempts=[];entered=[]
            def forbidden(name):
                def tripwire(*args,**kwargs):entered.append(name);raise AssertionError('P01 forbidden post-W successor: '+name)
                return tripwire
            operations=[('raw',lambda:e.produced_row(fixture['rows'][0],fixture['request'],loader=loader,deadline=clock.work_deadline)),
                ('reconcile',lambda:e.reconcile_rows(output,fixture['request'],deadline=clock.work_deadline,publisher=publisher)),
                ('first',lambda:e.first_record(fixture['request'],output,'passed',clock=clock)),
                ('runtime',lambda:e.qualify_runtime({},fixture['request'],deadline=clock.work_deadline)),
                ('accept',lambda:recovery.accept_result(output,{},fixture['request'],{},output,reservation=reservation))]
            with contextlib.ExitStack() as guards:
                for module,attribute in ((e,'load_array'),(e,'input_loader'),(p,'candidate_inventory'),(p,'checked_require_clock'),(recovery,'_accept_result')):
                    guards.enter_context(patch.object(module,attribute,side_effect=forbidden(attribute)))
                # Trace persistence is outside each guarded production attempt.
                # The API decorators may sample the clock, never read file data.
                for name,operation in operations:
                    start=time.monotonic()
                    with patch.object(Path,'open',side_effect=forbidden('Path.open')),patch.object(p.os,'open',side_effect=forbidden('os.open')),patch.object(p.hashlib,'sha256',side_effect=forbidden('hash')),patch.object(json,'dumps',side_effect=forbidden('serialize')):
                        try:operation()
                        except TimeoutError as error:attempts.append(dict(operation=name,start=start,end=time.monotonic(),error_class=type(error).__name__,message=str(error)))
                        else:raise AssertionError('P01 late operation admitted: '+name)
            if entered:raise AssertionError('P01 nonempty post-W suffix: '+repr(entered))
            fixture['late_suffix']=dict(attempts=attempts,entered=entered,cutoff=clock.work_deadline,
                sequence=publisher.sequence,versions=[row['version'] for row in publisher.rows.values()],
                binding=publisher.binding,request=fixture['request_record'],session=publisher.context['session'])
            p.trace_event('P01_late_suffix','terminal')
            if time.monotonic()>=clock.total_deadline:raise TimeoutError('P01 cutoff witness missed original C')
            (Path(fixture['root'])/'P01-cutoff-ready').write_text('terminal cutoff witness retained')
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


def direct_script_launch(command, *, cwd, env):
    """Actual six-script creation/registration entry; caller owns normal wait."""
    import subprocess
    from vipe_benchmark.s1_helper_session import create_owned_process,register_owned,retire_owned
    process=create_owned_process('direct script',subprocess.Popen,command,cwd=cwd,env=env,
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True,start_new_session=True)
    try:register_owned(process.pid,'direct script')
    except BaseException as primary:
        try:
            if process.poll() is None:os.killpg(process.pid,signal.SIGKILL)
            process.wait();retire_owned(process.pid)
        except BaseException as cleanup:
            primary.s1_owned_process=process
            primary.add_note('direct registration cleanup: '+repr(cleanup))
        raise
    return process


def l18_sentinel_launch():
    """Actual L18 foreign sentinel entry with registration-failure ownership."""
    from vipe_benchmark.s1_helper_session import create_owned_process,register_owned,retire_owned
    pid=create_owned_process('L18 sentinel',os.posix_spawn,sys.executable,
        [sys.executable,'-B','-c','import time; time.sleep(10)'],os.environ,setsid=True)
    try:register_owned(pid,'L18 sentinel')
    except BaseException as primary:
        try:os.killpg(pid,signal.SIGKILL);os.waitpid(pid,0);retire_owned(pid)
        except BaseException as cleanup:
            primary.s1_owned_pid=pid
            primary.add_note('sentinel registration cleanup: '+repr(cleanup))
        raise
    return pid


def named_creation_controls(test,kind,root):
    """Invoke actual named enclosing paths; only process/identity syscalls fake."""
    import contextlib,copy,subprocess
    import signal as signal_module
    from types import SimpleNamespace
    from unittest.mock import patch
    from vipe_benchmark import s1_helper_session as h,supervisor as sup,s1_progress as p
    observations=[];original_identity=h.identity
    for fault in ('creation','registration','census','cleanup','registration_cleanup','success'):
        events=[];pid=2147482800;created=[];waited=[];failed=[False];cleanup_failed=[False];handles={}
        original_records=copy.deepcopy(h.INVOCATION.records)
        primary=OSError('plan049 '+kind+' '+fault);cleanup_error=OSError('plan049 '+kind+' cleanup after registration')
        class Handle:
            def __init__(self,pid):self.pid=pid;self.returncode=None;handles[pid]=self
            def poll(self):return self.returncode
            def kill(self):events.append(dict(operation='handle_kill',pid=self.pid))
            def wait(self,*args,**kwargs):
                if fault in ('cleanup','registration_cleanup') and not cleanup_failed[0]:cleanup_failed[0]=True;raise (cleanup_error if fault=='registration_cleanup' else primary)
                self.returncode=0;waited.append(self.pid);return 0
        def spawn(*args,**kwargs):
            if fault=='creation':raise primary
            number=pid+len(created);created.append(number);events.append(dict(operation='creation_return',pid=number))
            return number
        def popen(*args,**kwargs):return Handle(spawn(*args,**kwargs))
        def identity(number):
            if number in created:
                if fault in ('registration','registration_cleanup') and not failed[0]:failed[0]=True;raise primary
                return dict(pid=number,pgid=number,start_ticks=100+number-pid)
            return original_identity(number)
        def waitpid(number,flags):
            if fault in ('cleanup','registration_cleanup') and not cleanup_failed[0]:cleanup_failed[0]=True;raise (cleanup_error if fault=='registration_cleanup' else primary)
            waited.append(number);return number,0
        def signal(number,sig):events.append(dict(operation='signal',pid=number,signal=int(sig)))
        try:
            with contextlib.ExitStack() as stack:
                stack.enter_context(patch.object(h,'identity',side_effect=identity))
                stack.enter_context(patch.object(os,'posix_spawn',side_effect=spawn))
                stack.enter_context(patch.object(subprocess,'Popen',side_effect=popen))
                stack.enter_context(patch.object(os,'killpg',side_effect=signal))
                stack.enter_context(patch.object(os,'waitpid',side_effect=waitpid))
                stack.enter_context(patch.object(os,'waitid',return_value=SimpleNamespace(si_status=0,si_code=os.CLD_EXITED)))
                if kind=='registry_owner_dispatch':
                    class Channel:
                        def fileno(self):return 97
                        def close(self):events.append(dict(operation='channel_close'))
                    session=SimpleNamespace(token='0'*32,channels={role:(Channel(),Channel()) for role in ('work','sample')},
                        events=h.Trace(128),ready_deadline=time.monotonic()+1,term_grace=.2,progress_cache=p.RetainedProgress())
                    owner=h.Owner(session)
                    def observe():
                        owner.cancelled=True
                        if fault=='census' and not failed[0]:failed[0]=True;raise primary
                        return {number:dict(pid=number,pgid=number,ppid=os.getpid(),start_ticks=100+number-pid,state='Z') for number in created}
                    stack.enter_context(patch.object(owner,'observe',side_effect=observe))
                    owner.run()
                    test.assertTrue(owner.done)
                    test.assertTrue(all(r['state'] in ('pending','reaped') for r in owner.records.values()))
                    events.append(dict(operation='Owner.run_return',records=copy.deepcopy(owner.records),errors=list(owner.errors)))
                elif kind in ('registry_direct_dispatch','registry_sentinel_dispatch'):
                    process=None
                    try:
                        if fault=='census':
                            # The actual launch path must stop in its fresh audit.
                            stack.enter_context(patch.object(h,'census',side_effect=primary))
                        if kind=='registry_direct_dispatch':process=direct_script_launch(['pure'],cwd=root,env=os.environ)
                        else:process=l18_sentinel_launch()
                    except OSError as error:
                        events.append(dict(operation='primary_return',same_primary=error is primary,message=str(error),secondary=list(getattr(error,'__notes__',()))))
                        if fault=='registration_cleanup':
                            test.assertIs(error,primary)
                            process=getattr(error,'s1_owned_process',getattr(error,'s1_owned_pid',None))
                            test.assertIsNotNone(process)
                            test.assertTrue(any(row['pid'] in created and row['state']=='unresolved' for row in h.INVOCATION.records.values()))
                            test.assertTrue(any('cleanup after registration' in note for note in error.__notes__))
                    finally:
                        if process is not None:
                            try:
                                if type(process) is int:os.killpg(process,signal_module.SIGKILL);os.waitpid(process,0);h.retire_owned(process)
                                else:process.kill();process.wait();h.retire_owned(process.pid)
                            except OSError as error:
                                events.append(dict(operation='cleanup_error',same_primary=error is primary,unresolved=copy.deepcopy(list(h.INVOCATION.records.values()))))
                                if type(process) is int:os.waitpid(process,0);h.retire_owned(process)
                                else:process.wait();h.retire_owned(process.pid)
                else:
                    # Actual supervisor reaches its real worker creation branch;
                    # native helper traffic uses the existing synchronous seam.
                    fixture=progress_fixture(Path(root)/('supervisor-'+fault))
                    reservation=progress_reservation(fixture,4)
                    output=Path(root)/('worker-'+fault);finished={}
                    class Session:
                        def admission_guard(self):pass
                        def install_progress(self,*args):pass
                        def retire_worker(self):pass
                        def close(self,deadline):return True
                        def ownership(self):return []
                    life=sup.HelperLifecycle(retain=True);life.helpers=[Session()]
                    class Ledger:
                        path=Path(root)/'disposable.jsonl';config=__import__('vipe_benchmark.config',fromlist=['load']).load();jobs={'S1-calibration-recovery-001':dict(resource='gpu')}
                        def reserve(self,*args,**kwargs):return reservation
                        def note(self,*args,**kwargs):pass
                        def finish(self,*args,**kwargs):finished.update(kwargs)
                    def monitor(*args,**kwargs):
                        if kwargs['phase']=='initial_sample':return dict(device_bytes=0,artifact_bytes=0,download_bytes=0,gpu_pids=[])
                        if kwargs['phase']=='prelaunch':return fixture['request_record']
                        raise RuntimeError('plan049 pure worker monitor stop')
                    def stop(process,deadline):
                        if process is None:return []
                        try:process.kill();process.wait();h.retire_owned(process.pid)
                        except OSError as error:
                            events.append(dict(operation='cleanup_error',same_primary=error is primary))
                            if fault=='registration_cleanup':raise
                            process.wait();h.retire_owned(process.pid)
                        return []
                    stack.enter_context(patch.object(sup,'HelperLifecycle',return_value=life))
                    stack.enter_context(patch.object(sup,'monitored_call',side_effect=monitor))
                    stack.enter_context(patch.object(sup,'stop_group',side_effect=stop))
                    if fault=='census':stack.enter_context(patch.object(h,'census',side_effect=primary))
                    try:sup.supervise(Ledger(),'S1-calibration-recovery-001',['pure'],output,evidence={},sample_resources={})
                    except sup.SupervisionFailure as error:
                        events.append(dict(operation='supervise_return',message=str(error),kind=error.kind,finish=finished))
                        if fault=='registration_cleanup':
                            test.assertIs(error.primary_exception,primary)
                            test.assertTrue(any(row['phase']=='cleanup' and row['message']==str(cleanup_error) for row in error.secondary_failures))
                            test.assertTrue(any(row['pid'] in created and row['state']=='unresolved' for row in h.INVOCATION.records.values()))
                            for handle in handles.values():handle.wait();h.retire_owned(handle.pid)
            test.assertEqual(set(created),set(waited))
            if fault in ('creation','census') and kind!='registry_owner_dispatch':test.assertEqual(created,[])
            test.assertFalse(any(r.get('pid') in created and r.get('state')!='retired' for r in h.INVOCATION.records.values()))
            observations.append(dict(entrypoint=kind,fault=fault,returned_pids=created,waited_pids=waited,events=events,real_processes_created=0))
        finally:h.INVOCATION.records=original_records
    return observations


def backend_gate_controls(test,fixture,root):
    """Real S1 factory, assets and tracker handoff with existing CPU native seams."""
    import contextlib
    from types import SimpleNamespace
    from unittest.mock import patch
    from vipe_benchmark import backends as b,s1_progress as p
    from test_vipe_benchmark_backends import S1NativeBridgeTests
    bridge=S1NativeBridgeTests();bridge.setUp();test.addCleanup(bridge.doCleanups)
    bridge.arguments['model_path']=fixture['request']['assets']['aot_checkpoint']['path']
    native_module,_,native_calls=bridge.make_module()
    assets=fixture['request']['assets'];seen=[];created=[]
    class Model:
        def to(self,**kwargs):return self
        def eval(self):return self
        def load_state_dict(self,state,*,strict):return SimpleNamespace(missing_keys=[],unexpected_keys=[])
    def build_model(config):return Model()
    def checkpoint(path,**kwargs):return {'model':{}}
    def sam_model(**kwargs):return Model()
    def transform(*args,**kwargs):return (args,kwargs)
    torch=SimpleNamespace(float32='float32',cuda=SimpleNamespace(is_available=lambda:True,manual_seed_all=lambda seed:None),
        manual_seed=lambda seed:None,load=checkpoint,hub=SimpleNamespace(download_url_to_file=None,load_state_dict_from_url=None))
    modules={
        'torch':torch,
        'groundingdino.models':SimpleNamespace(build_model=build_model),
        'groundingdino.util.slconfig':SimpleNamespace(SLConfig=SimpleNamespace(fromfile=lambda path:SimpleNamespace())),
        'groundingdino.util.utils':SimpleNamespace(clean_state_dict=lambda value:value),
        'groundingdino.datasets.transforms':SimpleNamespace(Compose=transform,RandomResize=transform,ToTensor=transform,Normalize=transform),
        'groundingdino.util.inference':SimpleNamespace(predict=lambda *args,**kwargs:None),
        'segment_anything':SimpleNamespace(SamPredictor=lambda model:SimpleNamespace(model=model),sam_model_registry={'vit_b':sam_model}),
        'aot_tracker':native_module,'aot':SimpleNamespace(__path__=[assets['aot_source']['path']]),
        'networks.layers.attention':SimpleNamespace(enable_corr=True)}
    for name,module in modules.items():
        if name.startswith('groundingdino'):source='grounding_source'
        elif name=='segment_anything':source='sam_source'
        elif name=='aot_tracker':source='samtrack_source'
        elif name=='networks.layers.attention':source='aot_source'
        else:continue
        module.__file__=assets[source]['files'][0]['path']
    actual_import=b.importlib.import_module
    def imported(name,*args,**kwargs):return modules[name] if name in modules else actual_import(name,*args,**kwargs)
    def gate(function,*args,**kwargs):
        item=dict(operation=getattr(function,'__qualname__',str(function)),state='entry');seen.append(item)
        result=p.backend_operation(function,*args,**kwargs);item['state']='returned'
        if isinstance(result,b.S1TrackerBridge):created.append(result)
        return result
    with patch.object(b.importlib,'import_module',side_effect=imported),patch.dict(os.environ,HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',TMPDIR=str(bridge.root)):
        backend=p.operation(b.build_backend,'S1',assets,s1_gate=gate,deadline=time.monotonic()+3600)
        legacy_module,_,legacy_calls=bridge.make_module();legacy_module.__file__=native_module.__file__;modules['aot_tracker']=legacy_module
        legacy=b.build_backend('S1',assets)
    try:
        test.assertIsInstance(backend,b.LegacyStandaloneBackend)
        test.assertEqual(backend.detector.text_threshold,.5);test.assertTrue(backend.detector.s1_assignment)
        test.assertEqual(len(native_calls),1);test.assertEqual(len(created),1)
        test.assertEqual(backend.tracker.metadata['engine_argument_bridge']['removed'],{'max_len_long_term':9999})
        test.assertTrue(all(item['state']=='returned' for item in seen))
        test.assertEqual(backend.provenance,legacy.provenance)
        test.assertEqual({key:value for key,value in backend.tracker.metadata.items() if key!='config_working_directory'},{key:value for key,value in legacy.tracker.metadata.items() if key!='config_working_directory'})
        test.assertEqual(len(legacy_calls),1)
    finally:
        for tracker in created:tracker._config_directory.cleanup()
        legacy.tracker._config_directory.cleanup()
    # Same factory seam rejects a callback crossing W before its successor.
    for offset in (-.001,0.,.001):
        now=[1.];entered=[]
        def operation():entered.append('opaque constructor');now[0]=2.+offset;return 'native return'
        with patch.object(p.time,'monotonic',side_effect=lambda:now[0]):
            if offset<0:test.assertEqual(p.operation(b._s1_call,p.backend_operation,operation,deadline=2.),'native return')
            else:
                with test.assertRaises(TimeoutError):p.operation(b._s1_call,p.backend_operation,operation,deadline=2.)
        test.assertEqual(entered,['opaque constructor'])
    constructor_controls=[]
    for fault in ('exception','late_return'):
        module,_,calls=bridge.make_module(fail=fault=='exception');native_call=module.get_aot;now=[1.]
        def get_aot(arguments):
            value=native_call(arguments)
            if fault=='late_return':now[0]=3.1
            return value
        module.get_aot=get_aot
        def constructor_gate(function,*args,**kwargs):return p.backend_operation(function,*args,cleanup_deadline=3.,**kwargs)
        constructor_gate.cleanup_deadline=3.
        cwd=Path.cwd()
        with patch.object(p.time,'monotonic',side_effect=lambda:now[0]),patch.dict(os.environ,TMPDIR=str(bridge.root)):
            with test.assertRaises(TimeoutError if fault=='late_return' else RuntimeError) as caught:
                p.operation(b._s1_tracker,module,bridge.runtime,bridge.arguments,s1_gate=constructor_gate,deadline=2.)
        test.assertEqual(Path.cwd(),cwd);test.assertEqual(len(calls),1)
        test.assertFalse(p.TEMPORARY_OWNERS);test.assertFalse(p.PROCESS_STATE_OWNERS)
        test.assertTrue(caught.exception.s1_temporary_retirement[-1]['resolved'])
        constructor_controls.append(dict(fault=fault,error_class=type(caught.exception).__name__,message=str(caught.exception),
            retirement=list(caught.exception.s1_temporary_retirement),cwd_restored=True))
    return dict(entrypoint='build_backend/AssetBundle/_build_native/_grounding/_s1_tracker',operations=seen,native_calls=[{key:value for key,value in call.items() if key!='aot_model'} for call in native_calls],
        constructor_controls=constructor_controls,absent_hook_equivalence=True,opaque_policy='native call indivisible; immediate original-W pre/post gates',models_imported=False,devices_used=False)


def retire_fixture_processes(processes,primary=None,*,stop=None):
    """Retire every returned handle, retaining uncertainty on the first error."""
    from vipe_benchmark.s1_helper_session import retire_owned
    errors=[];unresolved=[]
    for process in processes:
        try:
            if stop is None:
                if process.poll() is None:process.kill()
                process.wait()
            elif stop(process):raise RuntimeError('fixture process cleanup unconfirmed')
            retire_owned(process.pid)
        except BaseException as error:
            errors.append(error);unresolved.append(process)
    if errors:
        failure=primary if primary is not None else errors[0]
        failure.s1_owned_processes=tuple(unresolved)
        failure.s1_cleanup_errors=tuple(errors)
        for error in errors:failure.add_note('owned fixture retirement: '+repr(error))
        if primary is None:raise failure
    return not errors


def fixture_process_launch(event,command,**kwargs):
    """Shared real helper/race/detached entry; no process escapes registration."""
    import subprocess
    from vipe_benchmark.s1_helper_session import create_owned_process,register_owned
    process=create_owned_process(event,subprocess.Popen,command,**kwargs)
    try:register_owned(process.pid,event)
    except BaseException as primary:
        primary.s1_owned_process=process
        retire_fixture_processes([process],primary)
        raise
    return process


def nested_worker_code(seconds,*,parent_wait=False):
    # This is executed by the existing worker; there is no new launcher process.
    scripts=str(Path(__file__).resolve().parents[1]/'scripts')
    tests=str(Path(__file__).resolve().parent)
    return ('import sys,time; sys.path[:0]='+repr([scripts,tests])+'; '
        'from test_vipe_benchmark_s1_helper_fixtures import fixture_process_launch; '
        "p=fixture_process_launch('nested fixture descendant',[sys.executable,'-B','-c','import time; time.sleep("+str(seconds)+")']); "+
        ('time.sleep('+str(seconds)+')' if parent_wait else ''))


def enclosing_creation_controls(test,root):
    """Actual helper/race/detached callers, with creation/identity syscalls fake."""
    import copy,contextlib,subprocess
    from types import SimpleNamespace
    from unittest.mock import patch
    import test_vipe_benchmark_supervisor as cases
    from vipe_benchmark import s1_helper_session as h,supervisor as sup
    evidence=[]
    for entry in ('helper_worker','helper_runner','race','detached'):
        for fault in ('creation','registration','census','cleanup','registration_cleanup','success'):
            old=copy.deepcopy(h.INVOCATION.records);events=[];handles=[];cleanup_calls=[]
            primary=OSError(entry+' '+fault);secondary=OSError(entry+' cleanup')
            fail_cleanup=[fault in ('cleanup','registration_cleanup')]
            class Handle:
                def __init__(self):self.pid=2147482200+len(handles);self.returncode=None;handles.append(self)
                def poll(self):return self.returncode
                def kill(self):events.append(('kill',self.pid))
                def wait(self,**kwargs):
                    cleanup_calls.append(self.pid)
                    if fail_cleanup[0]:fail_cleanup[0]=False;raise secondary
                    self.returncode=handles.index(self)%2 if entry=='race' else 0;return self.returncode
                def communicate(self):self.returncode=0;return ('37; reaped','')
            def authority(event):
                events.append(('fresh_authority',event))
                if fault=='census':raise primary
                # This pure syscall fixture supplies a fresh full census each
                # time; the separate common-gate controls audit actual /proc.
                h.owned_charge(1+sum(handle.returncode is None for handle in handles),0)
                return dict(total_workers=2,registry_identity=id(h.INVOCATION))
            def create(*args,**kwargs):
                test.assertEqual(events[-1][0],'fresh_authority')
                if fault=='creation':raise primary
                result=Handle();events.append(('returned',result.pid));return result
            def identify(pid):
                events.append(('registration_identity',pid))
                if fault in ('registration','registration_cleanup'):raise primary
                return dict(pid=pid,pgid=pid,start_ticks=pid)
            fixture=None;caught=None
            try:
                with contextlib.ExitStack() as stack:
                    stack.enter_context(patch.object(h,'predispatch_owned',side_effect=authority))
                    stack.enter_context(patch.object(h,'identity',side_effect=identify))
                    stack.enter_context(patch.object(subprocess,'Popen',side_effect=create))
                    def stop(process,deadline):
                        process.kill();process.wait();return []
                    stack.enter_context(patch.object(sup,'stop_group',side_effect=stop))
                    try:
                        if entry=='helper_worker':
                            fixture=cases.HelperIntegrationTests();fixture.sup=sup;fixture.time=time
                            handle=fixture.worker('pure CPU syscall seam')
                            retire_fixture_processes([handle],stop=lambda value:stop(value,None))
                        elif entry=='helper_runner':
                            fixture=cases.HelperIntegrationTests()
                            fixture.test_importable_guarded_file_control()
                        elif entry=='race':
                            fixture=cases.SupervisorTests();fixture.root=Path(root)
                            fixture.test_concurrent_reservation_has_one_winner()
                        else:
                            handle=fixture_process_launch('existing detached descendant',['pure'])
                            # Same enclosing post-registration exception handler
                            # used by the L35 worker, without executing its string.
                            retire_fixture_processes([handle])
                    except BaseException as error:caught=error
                    if fault in ('creation','census'):
                        test.assertIs(caught,primary);test.assertEqual(handles,[])
                    elif fault in ('registration','registration_cleanup'):
                        test.assertIs(caught,primary);test.assertIs(primary.s1_owned_process,handles[0])
                        if fault=='registration_cleanup':
                            test.assertEqual(primary.s1_owned_processes,(handles[0],))
                            test.assertEqual(primary.s1_cleanup_errors,(secondary,))
                            test.assertTrue(any(row['pid']==handles[0].pid and row['state']=='unresolved' for row in h.INVOCATION.records.values()))
                    elif fault=='cleanup':
                        test.assertIs(caught,secondary)
                        if entry=='race':test.assertTrue(all(handle.pid in cleanup_calls for handle in handles))
                    else:test.assertIsNone(caught)
                    # Retrospective fixture retirement follows the asserted
                    # uncertain state, after fault injection has been removed.
                    fail_cleanup[0]=False
                    retire_fixture_processes(handles)
                    test.assertTrue(all(handle.returncode is not None for handle in handles))
                    test.assertFalse(any(row['pid'] in [h.pid for h in handles] and row['state']!='retired' for row in h.INVOCATION.records.values()))
                    if fixture is not None:fixture._cleanups.clear()
                evidence.append(dict(entrypoint=entry,fault=fault,events=events,cleanup_calls=cleanup_calls,primary=None if caught is None else str(caught),returned=[h.pid for h in handles],real_processes=0))
            finally:h.INVOCATION.records=old
    # One permanently failing wait must not prevent the next owned retirement.
    calls=[];primary=ValueError('race pending primary');cleanup=OSError('first wait')
    class Owned:
        def __init__(self,pid):self.pid=pid
        def poll(self):return 0
        def wait(self):
            calls.append(self.pid)
            if self.pid==1:raise cleanup
    retire_fixture_processes([Owned(1),Owned(2)],primary)
    test.assertEqual(calls,[1,2]);test.assertIs(primary.s1_cleanup_errors[0],cleanup)
    return evidence


def scenario_secondary_controls(test,root):
    """Inject failures in the actual collected scenario cleanup wrapper."""
    from types import SimpleNamespace
    from unittest.mock import patch
    from vipe_benchmark.s1_helper_session import Trace
    import test_vipe_benchmark_supervisor as cases
    evidence=[]
    for pending in (False,True):
        for fault in ('destination','serialize','open','write'):
            primary=RuntimeError('scenario pending primary');failure=OSError('scenario secondary '+fault)
            instance=cases.HelperSessionTests();instance.time=SimpleNamespace(monotonic=lambda:1.)
            def setup(mode,instance,**bounds):
                instance.t0=1.;instance.ready_deadline=2.;instance.setup_deadline=2.;instance.cleanup_deadline=3.
                instance.owner=SimpleNamespace(released=False,records={},errors=Trace(32),signals=Trace(32))
                instance.ticks=Trace(32);instance.events=Trace(32);instance.requests={};instance.wires={}
                instance.census_requests=SimpleNamespace(value=0);instance.max_gap=0;instance.max_turn=0;instance.last_sample=None
                instance.tick=lambda *args:None;instance.close=lambda *args:True;instance.await_ready=lambda:None;instance.ownership=lambda:[]
            # Force a secondary record without violating original timing bounds.
            class BrokenTrace(Trace):
                def facts(self):raise ValueError('scenario initial assembly fault')
            def faulty_setup(mode,instance,**bounds):setup(mode,instance,**bounds);instance.events=BrokenTrace(32)
            original_open=Path.open;original_dump=json.dump;calls=[]
            class Sink:
                def __enter__(self):return self
                def __exit__(self,*args):pass
                def write(self,value):calls.append('write');raise failure
            def opened(path,*args,**kwargs):
                if path.name.endswith('-secondary.json'):
                    calls.append('open')
                    if fault=='open':raise failure
                    if fault=='write':return Sink()
                return original_open(path,*args,**kwargs)
            def dump(value,stream,*args,**kwargs):
                if isinstance(value,dict) and 'primary_class' in value:
                    calls.append('serialize')
                    if fault=='serialize':raise failure
                return original_dump(value,stream,*args,**kwargs)
            directory=Path(root)/(str(pending)+'-'+fault);directory.mkdir()
            caught=None
            with patch(__name__+'.session',side_effect=faulty_setup),patch.dict(os.environ,S1_VALIDATION_RUN_DIRECTORY=str(directory)),patch.object(Path,'open',opened),patch.object(json,'dump',side_effect=dump):
                if fault=='destination':os.environ.pop('S1_VALIDATION_RUN_DIRECTORY')
                try:
                    with instance.scenario('pure-secondary'):
                        if pending:raise primary
                except BaseException as error:caught=error
            if pending:test.assertIs(caught,primary)
            else:test.assertIsInstance(caught,AssertionError)
            secondary=instance.scenario_secondary
            test.assertTrue(any(row['operation']==('scenario_destination' if fault=='destination' else 'scenario_secondary_write') for row in secondary))
            if fault!='destination':test.assertEqual(sum(value=='open' for value in calls),1)
            test.assertTrue(secondary)
            evidence.append(dict(primary_present=pending,fault=fault,calls=calls,secondary=secondary,primary_preserved=caught is primary))
    return evidence


def backend_retirement_controls(test,root):
    """Correction003–005 exact-root/CWD exceptions, using real owned CPU FDs."""
    import contextlib,hashlib,tempfile,shutil
    from unittest.mock import patch
    from vipe_benchmark import s1_progress as p
    evidence=[];root=Path(root);original_cwd=Path.cwd()
    for mode in ('before','late','late_cleanup_failure','symlink_containment'):
        now=[1.];C=3.;operations=[];objects=[];original_ctor=tempfile.TemporaryDirectory
        outside=root/('outside-'+mode);outside.write_bytes(b'outside must remain exact')
        def constructor(*args,**kwargs):
            directory=original_ctor(*args,**kwargs);objects.append(directory)
            nested=Path(directory.name)/'nested';nested.mkdir();(nested/'owned').write_bytes(b'owned')
            (Path(directory.name)/'outside-link').symlink_to(outside)
            now[0]=1.5 if mode=='before' else 3.1
            return directory
        original_open=os.open;original_unlink=os.unlink;original_rmdir=os.rmdir;original_stat=os.stat
        def opened(path,flags,*args,**kwargs):
            if now[0]>=C:
                test.assertTrue(flags&os.O_DIRECTORY);test.assertTrue(flags&os.O_NOFOLLOW)
                test.assertIn('dir_fd',kwargs);test.assertNotIn('..',Path(path).parts)
                operations.append(dict(operation='openat_directory',path=str(path),dir_fd=kwargs['dir_fd']))
            return original_open(path,flags,*args,**kwargs)
        def stat_at(path,*args,**kwargs):
            if now[0]>=C:
                test.assertIs(kwargs.get('follow_symlinks'),False);test.assertIn('dir_fd',kwargs)
                operations.append(dict(operation='statat',path=str(path),dir_fd=kwargs['dir_fd']))
            return original_stat(path,*args,**kwargs)
        def unlink(path,*args,**kwargs):
            if now[0]>=C:
                test.assertIn('dir_fd',kwargs);test.assertNotIn('..',Path(path).parts)
                operations.append(dict(operation='unlinkat',path=str(path),dir_fd=kwargs['dir_fd']))
                if mode=='late_cleanup_failure':raise OSError('exact owned unlink failure')
            return original_unlink(path,*args,**kwargs)
        def rmdir(path,*args,**kwargs):
            if now[0]>=C:
                test.assertIn('dir_fd',kwargs);test.assertNotIn('..',Path(path).parts)
                operations.append(dict(operation='rmdirat',path=str(path),dir_fd=kwargs['dir_fd']))
            return original_rmdir(path,*args,**kwargs)
        def forbid_after(function,name):
            def checked(*args,**kwargs):
                if now[0]>=C:raise AssertionError('unrelated post-C '+name)
                return function(*args,**kwargs)
            return checked
        caught=None;owned=None
        with contextlib.ExitStack() as stack:
            stack.enter_context(patch.object(p.time,'monotonic',side_effect=lambda:now[0]))
            stack.enter_context(patch.object(os,'open',side_effect=opened));stack.enter_context(patch.object(os,'stat',side_effect=stat_at))
            stack.enter_context(patch.object(os,'unlink',side_effect=unlink));stack.enter_context(patch.object(os,'rmdir',side_effect=rmdir))
            for module,name in ((Path,'open'),(Path,'read_bytes'),(Path,'resolve'),(json,'dumps'),(hashlib,'sha256')):
                stack.enter_context(patch.object(module,name,forbid_after(getattr(module,name),name)))
            try:
                owned=p.operation(p.owned_temporary_directory,constructor,(),dict(prefix='owned-retire-',dir=str(root)),C,deadline=2.)
                owned.cleanup()
            except TimeoutError as error:caught=error
        if mode=='before':
            test.assertIsNone(caught);test.assertFalse(owned.unresolved);test.assertEqual(owned.events[-1]['operation'],'temporary_cleanup')
        else:
            test.assertIsInstance(caught,TimeoutError);test.assertEqual(str(caught),'progress original work deadline')
            if mode=='late_cleanup_failure':
                test.assertEqual(len(caught.s1_temporary_owners),1);owned=caught.s1_temporary_owners[0]
                test.assertTrue(owned.unresolved);test.assertIn(owned,p.TEMPORARY_OWNERS)
                test.assertEqual(owned.events[-1]['error_class'],'OSError')
            else:test.assertFalse(any(owner.name==objects[0].name for owner in p.TEMPORARY_OWNERS))
            test.assertTrue(operations)
        test.assertEqual(outside.read_bytes(),b'outside must remain exact')
        if mode!='late_cleanup_failure':test.assertFalse(Path(objects[0].name).exists())
        record=dict(mode=mode,operations=operations,primary=None if caught is None else dict(error_class=type(caught).__name__,message=str(caught)),
            retirement=list(caught.s1_temporary_retirement) if caught is not None else list(owned.events),outside_unchanged=True)
        evidence.append(record)
        # Explicit retrospective fixture cleanup, outside the production clock
        # and tripwires; never a second production retirement attempt.
        if mode=='late_cleanup_failure':
            shutil.rmtree(owned.name)
            for fd in (owned.root_fd,owned.parent_fd):
                if fd is not None:os.close(fd)
            owned.unresolved=False;p.TEMPORARY_OWNERS.remove(owned)
    for late in (False,True):
        for fault in ('none','restore','close'):
            now=[1.];owner=p.OwnedWorkingDirectory();fd=owner.fd
            primary=RuntimeError('original opaque constructor failure');calls=[]
            os.chdir(root)
            real_fchdir=os.fchdir;real_close=os.close
            def restore(value):
                calls.append(('fchdir',value));test.assertEqual(value,fd)
                if fault=='restore':raise OSError('retained cwd restore failure')
                return real_fchdir(value)
            def close(value):
                calls.append(('close',value));test.assertEqual(value,fd)
                if fault=='close':raise OSError('retained cwd close failure')
                return real_close(value)
            now[0]=3.1 if late else 1.5
            with patch.object(p.time,'monotonic',side_effect=lambda:now[0]),patch.object(os,'fchdir',side_effect=restore),patch.object(os,'close',side_effect=close),patch.object(Path,'resolve',side_effect=AssertionError('cwd path lookup')),patch.object(Path,'open',side_effect=AssertionError('cwd content I/O')):
                try:raise primary
                except RuntimeError as pending:
                    owner.restore(3.);test.assertIs(pending,primary)
            test.assertEqual(calls,[('fchdir',fd),('close',fd)])
            if fault!='restore':test.assertEqual(Path.cwd(),original_cwd)
            os.chdir(original_cwd)
            test.assertEqual(owner.unresolved,fault!='none')
            if fault!='none':test.assertIn(owner,primary.s1_cwd_owners)
            if fault=='close':real_close(fd)
            else:
                with test.assertRaises(OSError):os.fstat(fd)
            evidence.append(dict(mode='cwd',late=late,fault=fault,calls=calls,events=list(owner.events),same_primary=True))
            if owner in p.PROCESS_STATE_OWNERS:p.PROCESS_STATE_OWNERS.remove(owner)
    test.assertEqual(Path.cwd(),original_cwd)
    return evidence


def backend_interior_controls(test,root):
    """Each owned read/parse/hash/close is an individually observable gate."""
    from unittest.mock import patch
    from vipe_benchmark import s1_progress as p,files,backends
    root=Path(root);path=root/'backend-interior.json';files.write_json(path,{'value':[1,2,3]})
    record=files.file_record(path);evidence=[]
    routes=[('file_record',files.file_record,(path,),('resolve','sha256','read','update','close','hexdigest','stat')),
        ('read_json',files.read_json,(path,),('resolve','read','close','loads')),
        ('object_hash',files.object_hash,({'value':[1,2,3]},),('dumps','encode','sha256','update','hexdigest'))]
    for route,function,args,targets in routes:
        expected=function(*args)
        test.assertEqual(p.backend_operation(function,*args),expected)
        for target in targets:
            original=p.operation;events=[];failure=OSError(route+' '+target)
            def step(function,*args,**kwargs):
                name='sha256' if function is p.hashlib.sha256 else getattr(function,'__name__','')
                events.append(name)
                if name==target:raise failure
                return original(function,*args,**kwargs)
            with patch.object(p,'operation',side_effect=step):
                with test.assertRaises(OSError) as caught:p.backend_operation(function,*args)
            test.assertIs(caught.exception,failure);test.assertIn(target,events)
            test.assertEqual(events[-1],target)
            evidence.append(dict(route=route,target=target,operations=events,same_primary=True))
    for route,function,args in (('file_record',files.file_record,(path,)),('read_json',files.read_json,(path,))):
        failure=OSError(route+' open');opened=[]
        def failed_open(*args,**kwargs):opened.append((args,kwargs));raise failure
        with patch.object(Path,'open',side_effect=failed_open):
            with test.assertRaises(OSError) as caught:p.backend_operation(function,*args)
        test.assertIs(caught.exception,failure);test.assertEqual(len(opened),1)
        evidence.append(dict(route=route,target='open',attempts=1,same_primary=True))
    calls=[]
    def unchanged(*args,**kwargs):calls.append((args,kwargs));return record
    test.assertIs(backends._s1_call(None,unchanged,1,expected=2),record)
    test.assertEqual(calls,[((1,),{'expected':2})])
    with test.assertRaisesRegex(ValueError,'restricted to S1'):backends.AssetBundle('S2',{},s1_gate=lambda *args:None)
    return evidence


def named_deadline_witness(test,name,state,stack,now,deadline,injected,stage,phase):
    """Explicit production-call target and distinct successor for each case."""
    import functools,zipfile,cv2,numpy as np
    from types import SimpleNamespace
    from unittest.mock import patch
    from vipe_benchmark import s1_progress as p,s1_evidence as e,s1_recovery as recovery
    witness=SimpleNamespace(target=[],successor=[],spec={},calls=[])
    def bind(module,attribute,role,predicate=lambda *args,**kwargs:True):
        original=getattr(module,attribute)
        @functools.wraps(original)
        def observed(*args,**kwargs):
            selected=injected() and predicate(*args,**kwargs)
            if not selected:return original(*args,**kwargs)
            record=dict(role=role,operation=attribute,entered=now(),stage=stage(),completed=False)
            getattr(witness,role).append(record);witness.calls.append(record)
            if now()>=deadline():raise AssertionError('named '+role+' entered at deadline: '+name+'/'+attribute)
            try:value=original(*args,**kwargs)
            except BaseException as error:record.update(error_class=type(error).__name__,message=str(error),exited=now());raise
            record.update(completed=True,exited=now());return value
        observed.__name__=attribute
        stack.enter_context(patch.object(module,attribute,observed))
        witness.spec[role]=dict(module=getattr(module,'__name__',type(module).__name__),operation=attribute)
    # Publication targets are the actual filesystem/socket/retention calls,
    # never a replacement for publication_boundary or its original W gate.
    suffix=name.split('_',1)[1] if name.startswith(('checkpoint_','head_')) else None
    publication={
        'generation_install':(p.os,'link','generation_install',p.os,'unlink','generation_install'),
        'generation_dir_fsync':(p,'fsync_dir','generation_directory_fsync',p,'record','generation_directory_fsync'),
        'generation_reopen_hash':(p,'read_record','generation_reopen_hash',p,'encode','generation_reopen_hash'),
        'head_install':(p.os,'replace','head_install',p,'fsync_dir','head_directory_fsync'),
        'head_dir_fsync':(p,'fsync_dir','head_directory_fsync',p,'record','head_directory_fsync'),
        'final_head_read':(p,'read_record','final_head_read',p,'read_record','final_generation_read'),
        'final_generation_read':(p,'read_record','final_generation_read',p,'encode','final_generation_read')}
    if name in publication:
        module,attribute,target_stage,smodule,sattribute,successor_stage=publication[name]
        bind(module,attribute,'target',lambda *a,**k:stage()==target_stage)
        bind(smodule,sattribute,'successor',lambda *a,**k:stage()==successor_stage)
    elif suffix in ('write','flush','fsync','close','readback'):
        selected_phase=name.split('_',1)[0]
        # Stream primitives are bound by the actual operation observer below;
        # readback calls have a stable production function to instrument here.
        spec={'write':('write','write','flush','flush'),'flush':('flush','flush','fsync','file_fsync'),
            'fsync':('fsync','file_fsync','close','close'),'close':('close','close','read_bytes','close_readback'),
            'readback':('read_bytes','close_readback','record','close_readback')}[suffix]
        witness.spec=dict(target=dict(operation=spec[0],stage=spec[1],phase=selected_phase),successor=dict(operation=spec[2],stage=spec[3],phase=selected_phase))
        def primitive(function,args,kwargs,invoke):
            operation=getattr(function,'__name__','')
            selected=None
            for role in ('target','successor'):
                expected=witness.spec[role]
                if injected() and operation==expected['operation'] and stage()==expected['stage'] and phase()==expected['phase']:
                    selected=role;break
            if selected is None:return invoke()
            record=dict(role=selected,operation=operation,stage=stage(),entered=now(),completed=False)
            getattr(witness,selected).append(record);witness.calls.append(record)
            if now()>=deadline():raise AssertionError('named stream operation entered late: '+name)
            try:value=invoke()
            except BaseException as error:record.update(exited=now(),error_class=type(error).__name__,message=str(error));raise
            record.update(exited=now(),completed=True);return value
        witness.primitive=primitive
    elif name in ('notice_send','ack_send'):
        producer=name=='notice_send';owner=state.publisher if producer else state.consumer
        original=owner.channel
        class Channel:
            def __getattr__(self,key):return getattr(original,key)
            def sendto(self,*args,**kwargs):
                if not injected():return original.sendto(*args,**kwargs)
                record=dict(role='target',operation='sendto',entered=now(),stage=stage(),completed=False);witness.target.append(record)
                if now()>=deadline():raise AssertionError('named socket successor entered late')
                result=original.sendto(*args,**kwargs);record.update(completed=True,exited=now());return result
        owner.channel=Channel();stack.callback(setattr,owner,'channel',original)
        witness.spec['target']=dict(operation='publisher.sendto' if producer else 'owner.sendto')
        bind(p,'receive','successor',lambda *args,**kwargs:True)
    elif name=='owner_retention':
        bind(state.cache,'acknowledge','target');bind(state.cache,'retain','successor',lambda *a,**k:True)
    elif name=='ack_receipt':
        bind(p,'ack_correlation','target');bind(p,'encode','successor',lambda *a,**k:True)
    elif name=='array_npy':
        bind(np,'save','target');bind(p.DeadlineSink,'write','successor',lambda *a,**k:True)
    elif name=='array_png':
        bind(cv2,'imencode','target');bind(p,'write_exclusive','successor',lambda *a,**k:True)
    elif name=='array_hash':
        bind(p,'checked_file_record','target');bind(p,'read_bytes','successor',lambda *a,**k:True)
    elif name=='npz_member':
        bind(zipfile.ZipFile,'open','target',lambda archive,member,*a,**k:member=='b.npy')
        bind(np.lib.format,'write_array','successor',lambda *a,**k:True)
    elif name=='npz_finalize':
        bind(zipfile.ZipFile,'close','target',lambda archive,*a,**k:archive.fp is not None)
        bind(p.DeadlineSink,'write','successor',lambda *a,**k:True)
    elif name=='cleanup_next_array':
        bind(np,'asanyarray','target');bind(zipfile.ZipFile,'open','successor',lambda archive,member,*a,**k:member=='b.npy')
    elif name=='produced_json':
        bind(p,'encode','target',lambda value,*a,**k:isinstance(value,dict) and 'identity' in value and 'instances' in value)
        bind(p,'write_exclusive','successor',lambda path,*a,**k:Path(path).name=='produced.json')
    elif name=='produced_read':
        bind(p,'read_record','target',lambda row,*a,**k:Path(row['path']).name=='produced.json')
        bind(e,'produced_row','successor')
    elif name=='produced_guard':
        bind(e,'produced_row','target');bind(p.Publisher,'seal','successor',lambda *a,**k:True)
    elif name=='qualified_guard':
        bind(e,'qualify_row','target');bind(p,'write_exclusive','successor',lambda path,*a,**k:Path(path).name=='qualified.json')
    elif name in ('first_guard','reuse_after_read'):
        bind(e,'verify_first','target');bind(e,'qualify_runtime','successor',lambda *a,**k:True)
    elif name=='runtime_guard':
        bind(e,'qualify_runtime','target');bind(recovery,'strict_record','successor',lambda *a,**k:True)
    elif name=='accept_after_read':
        bind(e,'validate_result','target');bind(e,'verify_first','successor',lambda *a,**k:True)
    elif name=='complete_after_read':
        bind(e,'evidence_counts','target');bind(e,'qualify_runtime','successor',lambda *a,**k:True)
    elif name in ('next_input','worker_popen'):
        witness.spec=dict(target=dict(operation='load_rgb(frame62)' if name=='next_input' else 'Popen'),successor=dict(operation='frame62 valid/native/raw' if name=='next_input' else 'post_creation_registration'))
    else:raise AssertionError('missing named deadline witness '+name)
    return witness
