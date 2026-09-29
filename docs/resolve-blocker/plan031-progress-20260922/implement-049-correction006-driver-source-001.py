"""Plan049 sole exec driver: explicit no-timeout mode, no operational ceilings."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
RUN=Path(__file__).resolve().parent

def stamp():return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),monotonic=time.monotonic())
def record(path):
    raw=Path(path).read_bytes()
    return dict(path=str(path),bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest())
def publish(path,value):
    raw=(json.dumps(value,indent=2,allow_nan=False)+'\n').encode()
    with path.open('xb',buffering=0) as stream:
        if stream.write(raw)!=len(raw):raise OSError('short launch evidence write')
        stream.flush();os.fsync(stream.fileno())
    if path.read_bytes()!=raw:raise ValueError('launch evidence readback')
    return record(path)
def main():
    kind,index,reason=sys.argv[1],int(sys.argv[2]),sys.argv[3]
    if kind not in ('diagnostic','aggregate') or index<1 or not reason.strip():raise ValueError('launch kind/index/reason')
    suffix=kind+'-'+str(index).zfill(3)
    indices=[int(p.stem.rsplit('-',1)[1]) for p in RUN.glob('launch-note-049-'+kind+'-*.json')]
    if index<=max(indices,default=0):raise ValueError('launch index not increasing')
    counts={k:len(list(RUN.glob('driver-049-'+k+'-*-exec-start.json'))) for k in ('diagnostic','aggregate')}
    admission_path=RUN/('launch-admission-049-'+suffix+'.json')
    # Main binds the actual existing exec root, never a predicted PID.
    # The sole driver may wait on its existing stdin for Main's explicit ADMIT.
    admission=None
    directory=RUN/(kind+'-049-'+str(index).zfill(3))
    if directory.exists():raise ValueError('output path occupied')
    dispatch_path=RUN/'implementation-dispatch-049.json';dispatch=json.loads(dispatch_path.read_bytes())
    plan=record(ROOT/'plans/plan_049.md');status=dispatch['implementation_status_snapshot'];authorization=dispatch['authorization_note']
    if dispatch['schema']!='plan049-implementation-dispatch/v1' or dispatch['plan']!={k:plan[k] for k in ('path','sha256')}:raise ValueError('fixed Plan049 dispatch')
    if status['path']!=str(RUN/'implementation-status-049.md') or record(Path(status['path']))!=status:raise ValueError('fixed immutable status')
    if authorization['path']!=str(RUN/'authorization-049.md') or record(Path(authorization['path']))!=authorization:raise ValueError('fixed authorization')
    if any(dispatch['authorization'][key] is not None for key in ('invocation_timeout','attempt_ceiling','correction_ceiling','operational_duration_ceiling_seconds')):raise ValueError('no-timeout authority required')
    contract=ast.parse((ROOT/'scripts/vipe_benchmark/s1_validation_contract.py').read_text())
    stdin=ast.literal_eval(next(n.value for n in contract.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STDIN' for t in n.targets))).encode()
    function=next(n for n in contract.body if isinstance(n,ast.FunctionDef) and n.name=='source_paths')
    paths=[]
    for item in function.body[0].value.args[0].elts:
        if isinstance(item,ast.BinOp):paths.append(ROOT/ast.literal_eval(item.right))
        else:
            call=item.value;paths.extend((ROOT/ast.literal_eval(call.func.value.right)).glob(ast.literal_eval(call.args[0])))
    sources=[record(path) for path in sorted(paths)]
    if len(sources)!=78:raise ValueError('source membership count')
    for path in paths:
        if path.suffix=='.py':ast.parse(path.read_bytes())
    command=[str(ROOT/'.local/envs/stg-colmap/bin/python'),'-B','-m','vipe_benchmark.s1_validation_capture',str(directory),'--no-timeout']
    if kind=='diagnostic':command.append('--diagnostic')
    settings={key:'1' for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OPENCV_FOR_THREADS_NUM','VIPE_CPU_VALIDATION')}
    settings['PYTHONPATH']=str(ROOT/'scripts');env=dict(os.environ,**settings)
    for key in ('S1_HELPER_DIAGNOSTIC','S1_RECEIPT_DIAGNOSTIC'):env.pop(key,None)
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    def process(pid):
        def row():
            fields=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
            return dict(boot_id=boot,pid=pid,ppid=int(fields[1]),pgid=int(fields[2]),start_ticks=int(fields[19]))
        def tasks():
            result=[]
            for path in sorted(Path('/proc',str(pid),'task').iterdir(),key=lambda value:int(value.name)):
                fields=(path/'stat').read_text().rsplit(')',1)[1].split()
                result.append(dict(boot_id=boot,pid=pid,process_start_ticks=first['start_ticks'],tid=int(path.name),start_ticks=int(fields[19])))
            return result
        first=row();threads=tasks();again=tasks();last=row()
        if first!=last or threads!=again or not threads:raise ValueError('unstable driver identity')
        return dict(first,threads=threads,threads_before=[dict(task) for task in threads],threads_after=again,process_before=first,process_after=last)
    root=process(os.getpid());ancestors=[];cursor=root['ppid'];seen=set()
    while cursor:
        if cursor in seen:raise ValueError('ancestry cycle')
        seen.add(cursor);row=process(cursor);ancestors.append(row);cursor=row['ppid']
    if not ancestors:raise ValueError('terminated ancestry required')
    prefix=RUN/('driver-049-'+suffix)
    outputs=[str(directory/name) for name in ('receipt.json','execution.json','process-stdout.log','process-stderr.log','stdout.log','stderr.log','stdin.py','runner.py','capture.py')]+[str(prefix)+ending for ending in ('-exec-start.json','-stdout.log','-stderr.log')]
    identity_request_path=RUN/('launch-identity-049-'+suffix+'.json')
    identity_binding=dict(ownership_root=root,preexisting_ancestors=ancestors,ancestry_terminal=dict(pid=ancestors[-1]['pid'],ppid=0),retained_wrappers=[],output_paths=outputs)
    identity_request=publish(identity_request_path,dict(schema='plan049-prospective-identity/v1',kind=kind,index=index,driver=record(Path(__file__)),**identity_binding))
    if not admission_path.exists():
        print(json.dumps(dict(awaiting_main_admission=str(admission_path),identity_request=identity_request)),flush=True)
        if sys.stdin.readline()!='ADMIT\n':raise ValueError('explicit Main admission handoff required')
    admission=json.loads(admission_path.read_bytes())
    if any(admission.get(k)!=v for k,v in dict(kind=kind,index=index,reason=reason,counts_before=counts,execution_mode='no-timeout',timeout_seconds=None,cpu_bound='B+max(1,H)≤8').items()):raise ValueError('main admission correlation')
    if admission.get('approved') is not True or admission.get('cleanup_resolved') is not True:raise ValueError('main cleanup/approval prerequisite')
    if 'timeout_seconds' not in admission:raise ValueError('explicit null timeout required')
    capacity=admission.get('resource_capacity',{})
    B=capacity.get('B');H=capacity.get('H')
    if type(B) is not int or type(H) is not int or min(B,H)<0 or B+max(1,H)>8 or capacity.get('charge')!=B+max(1,H):raise ValueError('main resource capacity proof')
    if type(capacity.get('artifact_bytes')) is not int or not 0<=capacity['artifact_bytes']<=150*1024**3:raise ValueError('artifact cap proof')
    if [r['path'] for r in sources]!=admission['source_paths'] or sources!=admission['sources']:raise ValueError('main source snapshot changed')
    addenda=[record(RUN/name) for name in ('plan049-correction-001.md','plan049-correction-002.md','plan049-correction-003.md','plan049-correction-004.md','plan049-correction-005.md','plan049-correction-006.md')]
    expected=dict(plan=plan,dispatch=record(dispatch_path),status=status,authorization=authorization,driver=record(Path(__file__)),command=command,environment=settings,stdin=dict(bytes=len(stdin),sha256=hashlib.sha256(stdin).hexdigest()),run_directory=str(directory),identity_request=identity_request,addenda=addenda,**identity_binding)
    if json.dumps(admission.get('bindings'),sort_keys=True,allow_nan=False)!=json.dumps(expected,sort_keys=True,allow_nan=False):raise ValueError('main immutable typed command/authority/identity binding')
    if process(os.getpid())!=root or [process(row['pid']) for row in ancestors]!=ancestors:raise ValueError('Main prospective identity changed')
    if capacity['B']!=len(root['threads']) or capacity['H']!=0:raise ValueError('Main live driver capacity mismatch')
    bindings=[plan,record(dispatch_path),status,authorization,record(admission_path),identity_request]+addenda
    note=dict(schema='plan049-prospective-launch/v1',execution_mode='no-timeout',timeout_seconds=None,driver=record(Path(__file__)),admission=record(admission_path),bindings=bindings,sources=sources,status={k:status[k] for k in ('bytes','sha256')},kind=kind,attempt_index=index,counts_before=counts,counts_after=dict(counts,**{kind:counts[kind]+1}),reason=reason,command=command,cwd=str(ROOT),run_directory=str(directory),environment=settings,unset_environment=['S1_HELPER_DIAGNOSTIC','S1_RECEIPT_DIAGNOSTIC'],stdin_identity=dict(bytes=len(stdin),sha256=hashlib.sha256(stdin).hexdigest(),content=stdin.decode()),ownership_root=root,preexisting_ancestors=ancestors,ancestry_terminal=dict(pid=ancestors[-1]['pid'],ppid=0),retained_wrappers=[],output_paths=outputs,observed=stamp(),cpu_bound='B+max(1,H)≤8',existing_scenarios=42,direct_scripts=6,scenario_execution_seconds=2,scenario_cleanup_seconds=1)
    note_record=publish(RUN/('launch-note-049-'+suffix+'.json'),note)
    env['S1_OWNED_ROOT_NOTE']=note_record['path'];env['S1_OWNED_ROOT_SHA256']=note_record['sha256']
    with Path(str(prefix)+'-stdout.log').open('xb') as out,Path(str(prefix)+'-stderr.log').open('xb') as err:
        logs={}
        for number,stream in [(1,out),(2,err)]:
            stream.flush();os.fsync(stream.fileno());info=os.fstat(stream.fileno());logs[str(number)]=dict(device=info.st_dev,inode=info.st_ino)
        # Fresh bytes, not age, determine admission immediately before exec.
        for item in bindings+sources+[note['driver'],note_record]:
            if record(Path(item['path']))!=item:raise ValueError('authority/source changed before exec')
        if process(os.getpid())!=root:raise ValueError('driver identity changed')
        publish(Path(str(prefix)+'-exec-start.json'),dict(schema='plan049-exec-launch/v1',execution_mode='no-timeout',timeout_seconds=None,note=note_record,before_launch=stamp(),logs=logs,command=command,replacement='driver execve unchanged child capture'))
        os.dup2(out.fileno(),1);os.dup2(err.fileno(),2)
    os.execve(command[0],command,env)
if __name__=='__main__':main()
