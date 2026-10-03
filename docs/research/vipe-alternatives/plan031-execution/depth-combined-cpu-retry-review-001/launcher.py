import argparse,hashlib,json,os,signal,subprocess,time
from pathlib import Path
def main():
 p=argparse.ArgumentParser();p.add_argument('--checkout',required=True);p.add_argument('--overlay',required=True);p.add_argument('--output',required=True);p.add_argument('--max-seconds',type=float,default=1800);p.add_argument('--review-request',required=True);a=p.parse_args()
 outer_start=time.monotonic();root=Path(a.checkout).resolve();out=Path(a.output).resolve();out.mkdir(exist_ok=False);fixture=out/'disposable-results';fixture.mkdir();mpl=out/'matplotlib';mpl.mkdir()
 python='/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python'
 env=dict(os.environ,PYTHONPATH=f'{a.overlay}:{root}/scripts:{root}/tests',VIPE_CPU_VALIDATION='1',S1_VALIDATION_RUN_DIRECTORY=str(fixture),CUDA_VISIBLE_DEVICES='',MPLCONFIGDIR=str(mpl),MPLBACKEND='Agg',PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1')
 def record(f):
  b=f.read_bytes();return dict(path=str(f),sha256=hashlib.sha256(b).hexdigest(),bytes=len(b))
 def sources():
  rows=[]
  names=subprocess.check_output(['git','ls-files','-z'],cwd=root).decode().split('\0')
  for name in sorted(names):
   f=root/name
   if name and 'prompts' not in Path(name).parts and f.is_file() and f.suffix in ['.py','.json','.txt','.in','.md','.yaml','.yml','.toml']:
    rows.append(record(f))
  return rows
 def process_rows():
  rows={}
  for f in Path('/proc').glob('[0-9]*/stat'):
   try:
    raw=f.read_text();tail=raw[raw.rfind(')')+2:].split();pid=int(f.parent.name)
    rows[pid]=dict(pid=pid,ppid=int(tail[1]),pgid=int(tail[2]),start_ticks=int(tail[19]),state=tail[0])
   except (OSError,ValueError,IndexError):pass
  return rows
 def census_owned(child,owned):
  rows=process_rows();branch={child.pid}|{pid for pid,row in owned.items() if pid in rows and rows[pid]['start_ticks']==row['start_ticks']}
  while True:
   add={pid for pid,row in rows.items() if row['ppid'] in branch};new=branch|add
   if new==branch:break
   branch=new
  for pid in branch:
   if pid in rows:owned[pid]=rows[pid]
  return rows

 request_path=Path(a.review_request).resolve();request=json.loads(request_path.read_text())
 def verify_record(row):
  actual=record(Path(row['path']))
  if actual!=row:raise ValueError('changed reviewed file: '+row['path'])
 verify_record(request['launcher'])
 if request['launcher']['path']!=str(Path(__file__).resolve()) or request['output']!=str(out) or request['max_seconds']!=a.max_seconds:
  raise ValueError('reviewed launcher/output/time mismatch')
 if request['interpreter']['path']!=python:raise ValueError('reviewed test interpreter mismatch')
 verify_record(request['interpreter'])
 for key in ['source_bindings','environment_bindings']:verify_record(request[key])
 for row in json.loads(Path(request['source_bindings']['path']).read_text()):verify_record(row)
 for package in json.loads(Path(request['environment_bindings']['path']).read_text()):
  for row in package['metadata']+package.get('files',[]):verify_record(row)
 receipt=dict(schema='plan069-integrated-cpu-test-capture/v1',record_kind='actual',scope='CPU test suite; no model admission receipt',review_request=record(request_path),checkout=str(root),head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip(),environment={k:env[k] for k in ['PYTHONPATH','VIPE_CPU_VALIDATION','S1_VALIDATION_RUN_DIRECTORY','CUDA_VISIBLE_DEVICES','MPLCONFIGDIR','MPLBACKEND','PYTHONDONTWRITEBYTECODE','PYTEST_DISABLE_PLUGIN_AUTOLOAD','OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']},max_seconds=a.max_seconds,launcher=record(Path(__file__).resolve()),sources_before=sources(),commands=[],passed=False)
 start=outer_start;deadline=start+a.max_seconds
 jobs=[('pytest',[python,'-B','-m','pytest','-q','-p','no:cacheprovider','tests/test_basketball_scene.py','tests/test_sync_pivot_budget.py','tests/test_sync_timing.py']),('unittest',[python,'-B','-m','unittest','discover','-s','tests','-v'])]
 try:
  for name,cmd in jobs:
   elapsed=time.monotonic();log=out/(name+'.log');row=dict(name=name,command=cmd,log=str(log),start_new_session=True,timed_out=False);receipt['commands'].append(row)
   with log.open('xb') as stream:
    child=subprocess.Popen(cmd,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
    print(json.dumps(dict(running=name,pid=child.pid,output=str(out))),flush=True)
    owned={}
    while child.poll() is None and time.monotonic()<deadline-15:
     census_owned(child,owned)
     time.sleep(.1)
    census_owned(child,owned)
    if child.poll() is None:
     row['timed_out']=True
     try:os.killpg(child.pid,signal.SIGTERM)
     except ProcessLookupError:pass
     until=min(deadline-10,time.monotonic()+3)
     while child.poll() is None and time.monotonic()<until:time.sleep(.05)
     if child.poll() is None:
      try:os.killpg(child.pid,signal.SIGKILL)
      except ProcessLookupError:pass
      child.wait(timeout=2)
    rows=census_owned(child,owned)
    survivors=[r for pid,r in rows.items() if pid in owned and r['start_ticks']==owned[pid]['start_ticks'] and r['state']!='Z']
    # Escaped groups are observed independently; never infer cleanup from killpg.
    row['observed_owned_processes']=list(owned.values())
    row['cleanup']=dict(method='observed /proc PID and start-ticks census',surviving_observed_owned_processes=survivors,confirmed_no_surviving_observed_processes=not survivors,limitation='100 ms polling cannot prove ownership of unobserved short-lived or detached descendants')
   row.update(returncode=child.returncode,elapsed_seconds=time.monotonic()-elapsed,log_sha256=hashlib.sha256(log.read_bytes()).hexdigest())
   print(json.dumps(row),flush=True)
   if child.returncode or row['timed_out']:break
  receipt['sources_after']=sources();receipt['source_bytes_unchanged']=receipt['sources_before']==receipt['sources_after'];receipt['passed']=len(receipt['commands'])==2 and all(r['returncode']==0 and not r['timed_out'] for r in receipt['commands']) and receipt['source_bytes_unchanged'] and all(r['cleanup']['confirmed_no_surviving_observed_processes'] for r in receipt['commands'])
 finally:
  receipt['elapsed_seconds']=time.monotonic()-start;receipt['within_wall_limit']=receipt['elapsed_seconds']<=a.max_seconds;receipt['passed']=receipt['passed'] and receipt['within_wall_limit'];(out/'receipt.json').write_text(json.dumps(receipt,indent=2)+'\n');print(json.dumps(dict(passed=receipt['passed'],elapsed_seconds=receipt['elapsed_seconds'],receipt=str(out/'receipt.json'))),flush=True)

if __name__=='__main__':
 main()
