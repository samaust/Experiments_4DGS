import hashlib, json, os, pathlib, re, signal, subprocess, time

root = pathlib.Path('/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/native-workers')
capture = root/'docs/research/vipe-alternatives/plan069-native-workers-001/full-suite-001'
capture.mkdir(parents=True, exist_ok=False)
output = pathlib.Path('/tmp/plan069-native-workers-fullsuite-001')
output.mkdir(exist_ok=False)
settings = dict(PYTHONPATH=str(root/'.local/plan069-cpu-validation/site-packages')+':scripts:tests',
    VIPE_CPU_VALIDATION='1',S1_VALIDATION_RUN_DIRECTORY=str(output),CUDA_VISIBLE_DEVICES='',
    MPLCONFIGDIR='/tmp/plan069-native-workers-mpl',OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',
    MKL_NUM_THREADS='1',NUMEXPR_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
env = dict(os.environ);env.update(settings)
interpreter = '/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python'
source_commit = subprocess.check_output(['git','rev-parse','HEAD'],cwd=root,text=True).strip()
paths = ['scripts/vipe_benchmark/final_render_geometry.py','scripts/vipe_benchmark/final_render_native.py',
    'scripts/vipe_benchmark/final_render_workers.py','scripts/vipe_benchmark/final_render_pipeline.py','tests/test_vipe_benchmark_final_render_geometry.py',
    'tests/test_vipe_benchmark_final_render_workers.py']
sources = {p:hashlib.sha256((root/p).read_bytes()).hexdigest() for p in paths}
commands = [('unittest',[interpreter,'-B','-m','unittest','discover','-s','tests']),
    ('pytest',[interpreter,'-B','-m','pytest','-q','tests/test_basketball_scene.py',
        'tests/test_sync_pivot_budget.py','tests/test_sync_timing.py'])]
for name,command in commands:
    started=time.monotonic();timed_out=False
    with (capture/(name+'.log')).open('x') as stream:
        proc=subprocess.Popen(command,cwd=root,env=env,stdout=stream,stderr=subprocess.STDOUT,start_new_session=True)
        try:
            code=proc.wait(timeout=1800)
        except subprocess.TimeoutExpired:
            timed_out=True;os.killpg(proc.pid,signal.SIGTERM)
            try:
                code=proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                os.killpg(proc.pid,signal.SIGKILL);code=proc.wait()
    log=(capture/(name+'.log')).read_text()
    result=dict(command=command,environment=settings,source_commit=source_commit,sources=sources,
        sources_unchanged=all(hashlib.sha256((root/p).read_bytes()).hexdigest()==digest for p,digest in sources.items()),
        returncode=code,timed_out=timed_out,elapsed_seconds=time.monotonic()-started,limit_seconds=1800,
        summary=log[-1800:])
    summaries=re.findall(r'^Ran (\d+) tests? in ([\d.]+)s$',log,re.M)
    if summaries:
        result['tests_run']=int(summaries[-1][0])
    skips=re.search(r'^OK \(skipped=(\d+)\)$',log,re.M)
    if skips:
        result['skipped']=int(skips[1])
    pytest_count=re.search(r'(\d+) passed in ',log)
    if name=='pytest' and pytest_count:
        result['tests_passed']=int(pytest_count[1])
    with (capture/(name+'-receipt.json')).open('x') as stream:
        json.dump(result,stream,indent=2);stream.write('\n')
    print(json.dumps(result),flush=True)
