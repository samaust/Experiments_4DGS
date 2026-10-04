"""One separately approved offline D9 setup recovery; no automatic retry or GPU."""
import json
import os
from pathlib import Path
import runpy
import subprocess
import time

from .budgets import budget_snapshot, _inventory
from .config import ROOT
from .depth_environment import _validate_inventory, _requirements
from .files import file_record, read_json, safe_path, verify_record, write_json

JOB='plan069-D9-setup-recovery-001'
SCHEMA='plan069-video-setup-recovery-request/v1'
PROFILE='D9-D10-torch-2.14.1-pypi-frame-input'


def _require(condition,message):
    if not condition:
        raise ValueError(message)


def _bound(record):
    _require(verify_record(record)==record,'changed immutable recovery input')
    return read_json(record['path'])


def _old_snapshot(root):
    # Hardlink installation may change link counts/ctime, but never old bytes.
    return {path:(s.st_dev,s.st_ino,s.st_size,s.st_mtime_ns) for path,s in _inventory(root).items()}


def _environment(request,output,binding,deadline,check,runner):
    started=time.monotonic()
    recipe=_bound(request['recipe'])
    _require(request.get('constraints')==recipe.get('constraints') and
        request.get('requirements')==recipe.get('requirements') and len(request['constraints'])==48 and
        request.get('runtime_profile')==PROFILE and request.get('python_version')==recipe.get('python_version')=='3.11',
        'exact reviewed 48-pin frame-input recovery recipe required')
    pins=_requirements(request['constraints'])
    _require(len(pins)==48 and all(r.url is None and str(r.specifier).startswith('==') and
        '*' not in str(r.specifier) and r.name.lower() not in ('decord','xformers') for r in pins),
        'exact offline pins without Decord or xformers required')
    _require(not request.get('sources'),'recovery cannot introduce local source packages')
    _require(request.get('indexes')==['https://pypi.org/simple'],'exact cached PyPI recovery index required')
    seed=safe_path(request['python_seed_executable']).absolute()
    _require(file_record(seed)==request['python_seed'],'exact retained Python seed required')
    uv=verify_record(request['uv'])['path']
    _require(request['recipe'] in request.get('requirement_sources',[]),'recovery recipe must bind runtime source inventory')
    for record in [*request.get('requirement_sources',[]),*request.get('media_tools',{}).values()]:verify_record(record)
    root=Path(binding['run_root'])
    output.mkdir(exist_ok=False)
    write_json(output/'request.json',request)
    (output/'requirements.txt').write_text('\n'.join(request['requirements'])+'\n')
    (output/'constraints.txt').write_text('\n'.join(request['constraints'])+'\n')
    environment=dict(os.environ,UV_CACHE_DIR=str(root/'setup-cache'),UV_PYTHON_INSTALL_DIR=str(root/'managed-python'),
        UV_LINK_MODE='hardlink',UV_OFFLINE='1',UV_PYTHON_DOWNLOADS='never',UV_HTTP_RETRIES='0',
        UV_CONCURRENT_DOWNLOADS='1',UV_CONCURRENT_BUILDS='1',UV_CONCURRENT_INSTALLS='7',
        HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',PIP_NO_INDEX='1',PIP_RETRIES='0',PIP_NO_INPUT='1',
        PYTHONNOUSERSITE='1',PYTHONDONTWRITEBYTECODE='1',CUDA_VISIBLE_DEVICES='',OMP_NUM_THREADS='7',MAX_JOBS='7')
    for name in ('PYTHONPATH','PYTHONHOME','UV_INDEX','UV_INDEX_URL','UV_EXTRA_INDEX_URL','UV_DEFAULT_INDEX'):
        environment.pop(name,None)
    receipts: list[dict] = []
    def command(argv,label):
        check()
        log=output/'commands'/f'{len(receipts):02d}-{label}.log';log.parent.mkdir(exist_ok=True)
        started=time.monotonic();error=None
        try:
            if runner is not None:
                runner(argv,environment=environment,cwd=ROOT,timeout=deadline-time.monotonic(),log=log)
            else:
                with log.open('x') as stream:
                    subprocess.run(argv,env=environment,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,
                        check=True,timeout=max(.001,deadline-time.monotonic()))
            check()
        except BaseException as failure:
            error=type(failure).__name__+': '+str(failure);raise
        finally:
            if not log.exists():log.write_text('Command failed before log creation.\n')
            path=log.with_suffix('.json')
            write_json(path,dict(command=argv,cwd=str(ROOT),log=file_record(log),wall_seconds=time.monotonic()-started,
                error=error,offline=True,automatic_retries=0,package_transfer_proxy=False,
                uv_transfer_receipt=None,record_kind=binding['record_kind']))
            receipts.append(file_record(path))
        return log
    probe=command([str(seed),'-I','-B','-c','import json,sys; print(json.dumps({"python_version": "%d.%d" % sys.version_info[:2]}))'],'seed-python')
    _require(json.loads(probe.read_text())=={'python_version':'3.11'},'retained seed Python version differs')
    env=output/'environment';python=str(env/'bin/python');lock=output/'requirements.lock'
    command([uv,'venv','--offline','--python',str(seed),'--no-python-downloads',str(env)],'venv')
    command([uv,'pip','compile','--offline','--python',python,'--index-url','https://pypi.org/simple','--generate-hashes','--no-build-isolation',
        '-c',str(output/'constraints.txt'),'--output-file',str(lock),str(output/'requirements.txt')],'resolve')
    command([uv,'pip','install','--offline','--python',python,'--index-url','https://pypi.org/simple','--require-hashes','--no-build-isolation',
        '-c',str(output/'constraints.txt'),'-r',str(lock)],'locked-dependencies')
    command([uv,'pip','check','--offline','--python',python],'dependency-check')
    inventory=output/'inventory.json'
    command([python,'-I','-B',str(ROOT/'scripts/vipe_benchmark/runtime_inventory.py'),'--output',str(inventory)],'inventory')
    installed=read_json(inventory);_validate_inventory(installed,request,python)
    _require({row['name'].lower().replace('_','-') for row in installed['packages']}.isdisjoint({'decord','xformers'}),
        'Decord and xformers must be absent from fresh recovery environment')
    result=dict(schema='plan069-depth-environment-result/v1',status='complete',candidate='D9',
        record_kind=binding['record_kind'],python_executable=python,python=file_record(python),python_seed=request['python_seed'],
        dependency_lock=file_record(lock),inventory=file_record(inventory),command_receipts=receipts,
        requirement_sources=request.get('requirement_sources',[]),sources=[],source_packages=[],
        model_imports=False,gpu_operations=False,automatic_retries=0,offline=True,
        excluded_distributions=['decord','xformers'],runtime_recipe=request['recipe'],runtime_profile=PROFILE,
        elapsed_seconds=time.monotonic()-started)
    write_json(output/'result.json',result)
    return result


def run_video_setup_recovery(request,output,*,request_path=None,environment_runner=None):
    """Build a fresh offline environment while preserving the failed original job."""
    started=time.monotonic()
    _require(request.get('schema')==SCHEMA and request.get('candidate')=='D9' and request.get('job_id')==JOB,
        'explicit one-use D9 recovery request required')
    output=safe_path(output).absolute()
    kind=request.get('record_kind')
    if kind=='actual':
        _require(environment_runner is None and request_path is not None,'actual recovery cannot inject fixture commands')
        record=file_record(request_path);_require(_bound(record)==request,'exact reserved recovery request required')
        from .depth_setup_recovery import validate_recovery_request
        from .ledger import Ledger
        from .config import load
        root=safe_path(request['ledger_path']).resolve().parent
        config=dict(load(),new_download_gib_limit=110,new_artifact_disk_gib_limit=210)
        events=Ledger(root/'ledger.jsonl',config).events()
        binding=validate_recovery_request(record,events,root,require_reservation=True)
        binding=dict(binding,run_root=str(root),record_kind='actual')
        reservation=next(e for e in events if e.get('event')=='reserve' and e.get('job_id')==JOB)
        command=reservation.get('command',[])
        _require(os.environ.get('VIPE_RESERVATION_START')==str(reservation['monotonic_start']) and
            '--request' in command and '--output' in command and
            command[command.index('--request')+1]==record['path'] and
            command[command.index('--output')+1]==str(output),
            'exact externally supervised recovery command required')
        deadline=min(started+binding['allocation']['setup_seconds'],reservation['monotonic_start']+reservation['seconds'])-30
    else:
        _require(kind=='fixture' and environment_runner is not None,'explicit fixture recovery runner required')
        root=output.parent.parent
        binding=dict(original=request['original_setup'],runtime_environment=request['runtime_environment'],
            allocation=request['fixture_allocation'],run_root=str(root),record_kind='fixture')
        baseline=budget_snapshot(root)
        binding['byte_limits']=dict(download_bytes=baseline['download_bytes'],
            artifact_bytes=baseline['artifact_bytes']+binding['allocation']['artifact_bytes'])
        deadline=started+binding['allocation']['setup_seconds']
    _require(output==root/'jobs'/JOB and not output.exists() and not output.is_symlink(),
        'fresh immutable recovery output required')
    original=binding['original']
    archive=verify_record(original['source_archive']);checkpoint=verify_record(original['checkpoint'])
    oldroot=root/'jobs/plan069-D9-setup-001'
    _require(Path(archive['path']).parent==oldroot and Path(checkpoint['path']).parent==oldroot,
        'recovery can reuse only retained original owned assets')
    for record in original['source_files']:
        _require(verify_record(record)==record and safe_path(record['path']).is_relative_to(oldroot/'source'),
            'retained exact original source files required')
    preserved=_old_snapshot(oldroot);baseline=budget_snapshot(root)
    limits=binding['byte_limits']
    def check():
        current=budget_snapshot(root)
        _require(time.monotonic()<deadline,'recovery setup deadline exceeded')
        _require(current['download_bytes']==baseline['download_bytes'] and
            current['download_bytes']<=limits['download_bytes'] and current['artifact_bytes']<=limits['artifact_bytes'],
            'offline recovery byte allocation exceeded or acquired new downloads')
    check();output.mkdir(parents=True,exist_ok=False);write_json(output/'request.json',request)
    try:
        if kind=='actual':
            guard=runpy.run_path(str(ROOT/'scripts/offline-python.py'))['restrict_network']()
        else:guard=dict(policy='fixture runner; no actual command or network operation')
        runtime=_environment(binding['runtime_environment'],output/'runtime',binding,deadline,check,environment_runner)
        new_checkpoint=output/Path(checkpoint['path']).name
        os.link(checkpoint['path'],new_checkpoint)
        check()
        _require(_old_snapshot(oldroot)==preserved,'original failed setup tree changed during recovery')
        for record in [archive,checkpoint,*original['source_files']]:verify_record(record)
        result=dict(schema='plan069-video-setup-recovery-result/v1',record_kind=kind,status='complete',candidate='D9',job_id=JOB,
            original_setup=original,source_archive=archive,source_dir=str(oldroot/'source'),source_files=original['source_files'],
            checkpoint=file_record(new_checkpoint),runtime_environment=file_record(output/'runtime/result.json'),
            python_executable=runtime['python_executable'],python=runtime['python'],dependency_lock=runtime['dependency_lock'],
            inventory=runtime['inventory'],runtime_recipe=binding['runtime_environment']['recipe'],runtime_profile=PROFILE,
            excluded_distributions=['decord','xformers'],media_tools=binding['runtime_environment'].get('media_tools',{}),
            xformers=binding['runtime_environment'].get('xformers'),bytes_received=0,elapsed_seconds=time.monotonic()-started,
            offline_guard=guard,original_failure_preserved=True,model_imports=False,gpu_operations=False,automatic_retries=0)
        if kind=='actual':
            result.update(request=binding['request'],review=binding['review'],authorization=binding['authorization'],
                source_review=binding['source_review'],
                source_revision=binding['map_proposal']['candidate_config']['code']['revision'],
                weight_revision=binding['map_proposal']['candidate_config']['weights']['revision'])
        write_json(output/'result.json',result);check()
        return result
    except BaseException as error:
        write_json(output/'failure.json',dict(schema='plan069-video-setup-recovery-failure/v1',record_kind=kind,status='failed',
            job_id=JOB,error=type(error).__name__+': '+str(error),elapsed_seconds=time.monotonic()-started,
            original_setup=original,automatic_retries=0,gpu_operations=False))
        raise
