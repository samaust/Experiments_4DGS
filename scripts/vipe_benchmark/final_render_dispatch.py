"""CPU fixture dispatch candidate over the locked ledger and owned supervisor.

Actual admission is absent. No prospective GPU allocation or native runtime can
be consumed through this interface. Acceptance runs inside the charged worker.
"""
import copy
import os
from pathlib import Path
import runpy
import sys

from .config import load
from .extended_final_render_contract import parse_request,validate_scene_bindings
from .files import file_record,object_hash,read_json,safe_path,verify_record,write_json
from .final_render_contract import PHASES
from .final_render_pipeline import validate_worker_result
from .ledger import Ledger
from .supervisor import directory_bytes,group_processes,supervise


def _require(condition,message):
    if not condition:raise ValueError(message)


def _bound(record):
    _require(type(record) is dict and set(record)=={'path','sha256','bytes'} and
        verify_record(record)==record,'exact unchanged dispatch input required')
    return read_json(record['path'])


class _FixtureLedger(Ledger):
    def __init__(self,path,config,request):
        self.request=request
        super().__init__(path,config)

    def _jobs(self,events):
        return {f"fixture/{self.request['id']}/{a['arm']}/{a['phase']}":
            dict(id=f"fixture/{self.request['id']}/{a['arm']}/{a['phase']}",resource='cpu',
                seconds=a['seconds'],scope='private CPU final-render fixture')
            for a in self.request['allocations'] if a['phase'] in PHASES}


class FixtureDispatcher:
    """Own a fresh private fixture ledger; dispatch serial, immutable phase jobs."""
    def __init__(self,request,root):
        _require(request.get('record_kind')=='fixture','fixture-only dispatch; actual DO admission is absent')
        self.request=parse_request(request)
        validate_scene_bindings(self.request)
        self.root=safe_path(root).resolve()
        self.root.mkdir(parents=True,exist_ok=False)
        request_path=self.root/'request.json'
        write_json(request_path,self.request)
        self.request_record=file_record(request_path)
        config=copy.deepcopy(load())
        config['gpu_peak_device_gib_limit']=self.request['device_bytes_limit']/2**30
        config['new_artifact_disk_gib_limit']=self.request['artifact_bytes_limit']/2**30
        self.ledger=_FixtureLedger(self.root/'ledger.jsonl',config,self.request)

    def dispatch(self,arm,phase,worker,*,parent=None,arguments=(),seconds_limit=None,resource_samples=()):
        request=parse_request(_bound(self.request_record))
        _require(arm in request['compositions'] and phase in PHASES,'unknown worker arm/phase')
        _require(type(worker) is dict and verify_record(worker)==worker,'worker script changed')
        _require(safe_path(worker['path']).suffix=='.py','explicit Python fixture worker required')
        _require(type(arguments) in (tuple,list) and all(type(v) is str for v in arguments),'literal worker arguments required')
        _require(type(resource_samples) in (tuple,list),'finite fixture resource samples required')
        for row in resource_samples:
            _require(type(row) is dict and set(row)<= {'device_bytes','download_bytes','artifact_bytes','cpu_workers_used'} and
                all(type(v) is int and v>=0 for v in row.values()),'nonnegative integer fixture resources required')
        phases=tuple(PHASES);index=phases.index(phase)
        if index:
            previous=validate_worker_result(request,arm,phases[index-1],_bound(parent))
            _require(previous['status']=='complete','complete predecessor required')
        else:_require(parent is None,'geometry cannot consume a predecessor')
        output=self.root/f'{arm}-{phase}'
        sources=[file_record(Path(__file__).resolve().parent/name) for name in
            ('final_render_dispatch.py','final_render_pipeline.py','extended_final_render_contract.py',
             'final_render_contract.py','final_render_initializer.py','files.py','ledger.py','supervisor.py')]
        invocation=dict(schema='plan069-final-render-fixture-invocation/v1',record_kind='fixture',
            request=self.request_record,arm=arm,phase=phase,worker=worker,parent_result=parent,
            output=str(output),arguments=list(arguments),resource_samples=list(resource_samples),source_files=sources,
            execution_authorized=False,native_adapter_qualified=False)
        invocation_path=self.root/f'{arm}-{phase}-invocation.json'
        write_json(invocation_path,invocation)
        invocation_record=file_record(invocation_path)
        entry=Path(__file__).resolve().parents[1]/'final-render-fixture-worker.py'
        command=[sys.executable,str(entry),str(invocation_path)]
        job=f"fixture/{request['id']}/{arm}/{phase}"
        readings=iter(resource_samples);last={};peak_cpu=0
        def sample():
            nonlocal last,peak_cpu
            last=next(readings,last)
            starts=[e for e in self.ledger.events() if e['event']=='started' and e['job_id']==job]
            cpu=max(last.get('cpu_workers_used',0),len(group_processes(starts[-1]['pgid'])) if starts else 0)
            peak_cpu=max(peak_cpu,cpu)
            _require(cpu<=request['cpu_workers_limit'],'CPU worker ceiling exceeded')
            return dict(device_bytes=last.get('device_bytes',0),download_bytes=last.get('download_bytes',0),
                artifact_bytes=max(directory_bytes(self.root),last.get('artifact_bytes',0)),gpu_pids=[])
        def accept(directory):
            _require((directory/'result.json').stat().st_size<=2**20 and
                (directory/'dispatch-validation.json').stat().st_size<=8192,'bounded terminal control files required')
            record=file_record(directory/'result.json')
            proof=read_json(directory/'dispatch-validation.json')
            _require(proof==dict(schema='plan069-final-render-fixture-acceptance/v1',record_kind='fixture',
                status='passed',invocation=invocation_record,result=record,
                execution_authorized=False,native_adapter_qualified=False),'charged worker acceptance differs')
            return proof
        supervise(self.ledger,job,command,output,evidence=dict(record_kind='fixture',
            invocation=invocation_record,entry=file_record(entry),interpreter=file_record(sys.executable)),
            sample_resources=sample,validate_result=accept,seconds_limit=seconds_limit,poll_seconds=.02,
            cpu_workers_limit=request['cpu_workers_limit'])
        state=self.ledger.states()[job]
        _require(state['status']=='complete' and state['cleanup_confirmed'] is True and
            state['cleanup_uncertain'] is False,'fixture dispatch cleanup/terminal accounting failed')
        return dict(schema='plan069-final-render-fixture-dispatch/v1',record_kind='fixture',status='complete',
            job_id=job,request_sha256=object_hash(request),worker_result=state['result'],
            elapsed_seconds=state['elapsed_seconds'],cleanup_confirmed=True,peak=state['peak'],cpu_workers_used=peak_cpu,
            execution_authorized=False,native_adapter_qualified=False)


def run_fixture_invocation(path):
    """Entry into the owned CPU child; validate results before its supervised exit."""
    invocation_record=file_record(path);invocation=read_json(path)
    _require(invocation.get('schema')=='plan069-final-render-fixture-invocation/v1' and
        invocation.get('record_kind')=='fixture' and invocation.get('execution_authorized') is False and
        invocation.get('native_adapter_qualified') is False,'fixture invocation required')
    request=parse_request(_bound(invocation['request']))
    _require(request['record_kind']=='fixture','actual request cannot enter fixture process')
    validate_scene_bindings(request)
    _require(all(verify_record(r)==r for r in invocation['source_files']) and
        file_record(__file__) in invocation['source_files'],'dispatch control sources changed before launch')
    worker=invocation['worker'];_require(verify_record(worker)==worker,'worker script changed before launch')
    os.environ.update(CUDA_VISIBLE_DEVICES='',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
        OMP_NUM_THREADS=str(request['cpu_workers_limit']),OPENBLAS_NUM_THREADS=str(request['cpu_workers_limit']),
        MKL_NUM_THREADS=str(request['cpu_workers_limit']),NUMEXPR_NUM_THREADS=str(request['cpu_workers_limit']))
    output=safe_path(invocation['output']).resolve()
    _require(output.parent==safe_path(path).resolve().parent and not output.exists(),'fresh owned output required')
    sys.argv=[worker['path'],str(output),invocation['request']['path'],*invocation['arguments']]
    try:
        runpy.run_path(worker['path'],run_name='__main__')
    except SystemExit as error:
        if error.code not in (None,0):raise
    parse_request(_bound(invocation['request']))
    _require(verify_record(worker)==worker and file_record(path)==invocation_record,'dispatch sources changed during worker')
    _require(all(verify_record(r)==r for r in invocation['source_files']),'dispatch control sources changed during worker')
    result=validate_worker_result(request,invocation['arm'],invocation['phase'],read_json(output/'result.json'))
    _require(result['status']=='complete' and result['parent_result']==invocation['parent_result'],
        'worker did not produce exact complete predecessor lineage')
    _require(all(safe_path(r['path']).resolve().is_relative_to(output) for r in result['artifacts']),
        'worker artifacts must be published in its owned output')
    write_json(output/'dispatch-validation.json',dict(schema='plan069-final-render-fixture-acceptance/v1',
        record_kind='fixture',status='passed',invocation=invocation_record,result=file_record(output/'result.json'),
        execution_authorized=False,native_adapter_qualified=False))
