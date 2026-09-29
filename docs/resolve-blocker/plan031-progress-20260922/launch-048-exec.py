"""Plan048 sole exec driver; main must supply a fresh durable launch admission."""
import ast
import datetime
import hashlib
import json
import os
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
RUN=Path(__file__).resolve().parent


def stamp():
    return dict(utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),monotonic=time.monotonic())


def record(path):
    raw=path.read_bytes()
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
    if kind not in ('diagnostic','aggregate'):raise ValueError('launch kind')
    suffix=kind+'-'+str(index).zfill(3)
    timeout=120 if kind=='diagnostic' else 300
    counts={k:len(list(RUN.glob('driver-048-'+k+'-*-exec-start.json'))) for k in ('diagnostic','aggregate')}
    limits=dict(diagnostic=4,aggregate=2)
    indices=[int(p.stem.rsplit('-',1)[1]) for p in RUN.glob('launch-note-048-'+kind+'-*.json')]
    if index!=(max(indices,default=0)+1) or counts[kind]>=limits[kind]:raise ValueError('launch slot/index')
    admission_path=RUN/('launch-admission-048-'+suffix+'.json')
    admission=json.loads(admission_path.read_bytes())
    if admission['kind']!=kind or admission['index']!=index or admission['reason']!=reason or admission['counts_before']!=counts:
        raise ValueError('main launch admission correlation')
    if admission['cpu_bound']!='B+max(1,H)≤8':raise ValueError('CPU bound')
    if admission['approved'] is not True or admission['cleanup_resolved'] is not True:raise ValueError('launch prerequisite')
    independent=admission['independent_seconds_remaining']
    if type(independent) not in (int,float) or not 0<=independent<=800:raise ValueError('independent reservation')
    final=admission['final_aggregate']
    if type(final) is not bool or final and kind!='aggregate':raise ValueError('final aggregate type')
    if not final and counts['aggregate']>=1:raise ValueError('final aggregate reserved')
    correction=json.loads((RUN/'implementation-dispatch-048-budget-correction-001.json').read_bytes())
    start=correction['monotonic']
    already=7200-correction['remaining_at_actual_agent_dispatch_upper_bound_seconds']
    reserve=0 if final else 300
    def admit():
        charged=already+time.monotonic()-start
        if charged+timeout+reserve+independent>=6000:raise TimeoutError('Plan048 source/test cutoff reservation')
        if charged+timeout+reserve+independent+1200>7200:raise TimeoutError('Plan048 handoff reservation')
        if time.monotonic()>=admission['admission_expires_monotonic']:raise TimeoutError('main admission expired')
        return charged
    charged=admit()
    directory=RUN/(kind+'-048-'+str(index).zfill(3))
    if directory.exists():raise ValueError('output path occupied')
    dispatch=json.loads((RUN/'implementation-dispatch-048.json').read_bytes())
    status=dispatch['implementation_status_snapshot']
    if record(Path(status['path']))!=status:raise ValueError('immutable dispatch status changed')
    if record(Path(dispatch['resolver_plan']['path']))['sha256']!=dispatch['resolver_plan']['sha256']:raise ValueError('plan changed')
    contract=ast.parse((ROOT/'scripts/vipe_benchmark/s1_validation_contract.py').read_text())
    stdin=ast.literal_eval(next(n.value for n in contract.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='STDIN' for t in n.targets))).encode()
    function=next(n for n in contract.body if isinstance(n,ast.FunctionDef) and n.name=='source_paths')
    paths=[]
    for item in function.body[0].value.args[0].elts:
        if isinstance(item,ast.BinOp):paths.append(ROOT/ast.literal_eval(item.right))
        else:
            call=item.value
            paths.extend((ROOT/ast.literal_eval(call.func.value.right)).glob(ast.literal_eval(call.args[0])))
    sources=[record(path) for path in sorted(paths)]
    if [r['path'] for r in sources]!=admission['source_paths'] or sources!=admission['sources']:raise ValueError('main admitted source snapshot changed')
    for path in paths:
        if path.suffix=='.py':ast.parse(path.read_bytes())
    command=[str(ROOT/'.local/envs/stg-colmap/bin/python'),'-B','-m','vipe_benchmark.s1_validation_capture',str(directory),'--timeout',str(timeout)]
    if kind=='diagnostic':command.append('--diagnostic')
    settings={key:'1' for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS','OPENCV_FOR_THREADS_NUM','VIPE_CPU_VALIDATION')}
    settings['PYTHONPATH']=str(ROOT/'scripts');env=dict(os.environ,**settings)
    for key in ('S1_HELPER_DIAGNOSTIC','S1_RECEIPT_DIAGNOSTIC'):env.pop(key,None)
    boot=Path('/proc/sys/kernel/random/boot_id').read_text().strip()
    def process(pid):
        f=Path('/proc',str(pid),'stat').read_text().rsplit(')',1)[1].split()
        return dict(boot_id=boot,pid=pid,ppid=int(f[1]),pgid=int(f[2]),start_ticks=int(f[19]))
    root=process(os.getpid());ancestors=[];cursor=root['ppid'];seen=set()
    while cursor:
        if cursor in seen:raise ValueError('ancestry cycle')
        seen.add(cursor);row=process(cursor);ancestors.append(row);cursor=row['ppid']
    if not ancestors:raise ValueError('terminated ancestry required')
    bindings=[record(ROOT/'plans/plan_048.md'),record(RUN/'implementation-dispatch-048.json'),record(RUN/'implementation-dispatch-048-budget-correction-001.json'),record(RUN/'plan048-correction-001.md'),record(admission_path)]
    observed=stamp();after=dict(counts);after[kind]+=1
    prefix=RUN/('driver-048-'+suffix)
    outputs=[str(directory/name) for name in ('receipt.json','execution.json','process-stdout.log','process-stderr.log','stdout.log','stderr.log','stdin.py','runner.py','capture.py')]+[str(prefix)+ending for ending in ('-exec-start.json','-stdout.log','-stderr.log')]
    note=dict(schema='plan048-prospective-launch/v1',driver=record(Path(__file__)),bindings=bindings,sources=sources,status={k:status[k] for k in ('bytes','sha256')},kind=kind,attempt_index=index,counts_before=counts,counts_after=after,remaining_before={k:limits[k]-counts[k] for k in counts},remaining_after={k:limits[k]-after[k] for k in counts},reason=reason,command=command,cwd=str(ROOT),run_directory=str(directory),timeout_seconds=timeout,environment=settings,unset_environment=['S1_HELPER_DIAGNOSTIC','S1_RECEIPT_DIAGNOSTIC'],stdin_identity=dict(bytes=len(stdin),sha256=hashlib.sha256(stdin).hexdigest(),content=stdin.decode()),ownership_root=root,preexisting_ancestors=ancestors,ancestry_terminal=dict(pid=ancestors[-1]['pid'],ppid=0),retained_wrappers=[],output_paths=outputs,observed=observed,charged_elapsed=charged,independent_seconds_remaining=independent,final_aggregate=final,cpu_bound='B+max(1,H)≤8',existing_scenarios=42,direct_scripts=6,scenario_execution_seconds=2,scenario_cleanup_seconds=1,direct_execution_seconds=10,direct_cleanup_seconds=2)
    note_record=publish(RUN/('launch-note-048-'+suffix+'.json'),note)
    env['S1_OWNED_ROOT_NOTE']=note_record['path'];env['S1_OWNED_ROOT_SHA256']=note_record['sha256']
    with Path(str(prefix)+'-stdout.log').open('xb') as out,Path(str(prefix)+'-stderr.log').open('xb') as err:
        logs={}
        for number,stream in [(1,out),(2,err)]:
            stream.flush();os.fsync(stream.fileno());st=os.fstat(stream.fileno());logs[str(number)]=dict(device=st.st_dev,inode=st.st_ino)
        admit()
        publish(Path(str(prefix)+'-exec-start.json'),dict(schema='plan048-exec-launch/v1',note=note_record,before_launch=stamp(),logs=logs,command=command,replacement='driver execve unchanged capture'))
        os.dup2(out.fileno(),1);os.dup2(err.fileno(),2)
    admit()
    os.execve(command[0],command,env)


if __name__=='__main__':
    main()
