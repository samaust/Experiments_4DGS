"""Supervise the separately approved D6 qualification003; preserve attempts001/002."""
import argparse
import os
from pathlib import Path

from vipe_benchmark.config import load
from vipe_benchmark.execution import resources
from vipe_benchmark.files import file_record,read_json,write_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark.supervisor import supervise


TERMINAL_HEADROOM=64*1024


def owned_artifact_bytes(output):
    """Count result, supervisor cache and log within the attempt allowance."""
    from vipe_benchmark.budgets import directory_bytes
    total=0
    for directory in (output,output.with_name(output.name+'-temporary')):
        if directory.is_symlink():raise ValueError('qualification artifact directory is a symlink')
        if directory.exists():total+=directory_bytes(directory)
    for log in (output.with_suffix('.log'),output.with_suffix('.syscalls.log'),output.with_suffix('.trace-record.json')):
        if log.is_symlink():raise ValueError('qualification supervisor artifact is a symlink')
        if log.exists():
            info=log.stat();total+=max(info.st_size,info.st_blocks*512)
    return total


def publish_result_envelope(out,record,proposal,validate_result):
    """Bind exited-tracer bytes to the immutable worker result, before finish."""
    trace=out.with_suffix('.syscalls.log')
    worker_record=file_record(out/'worker-result.json')
    result=read_json(worker_record['path'])
    if result.get('trace_path')!=str(trace) or trace.is_symlink() or not trace.is_file():
        raise ValueError('exact qualification syscall trace required')
    result=dict(result,worker_result=worker_record,trace=file_record(trace))
    validate_result(result,record,cleanup_confirmed=True)
    if owned_artifact_bytes(out)>proposal['artifact_bytes']-TERMINAL_HEADROOM:
        raise ValueError('qualification envelope headroom exhausted')
    write_json(out/'result.json',result)
    return result


def dispatch(request_path):
    from vipe_benchmark.depth_driver_qualification_local_bind import JOB,validate_request,validate_result,reservation_evidence
    from vipe_benchmark.depth_admission import local_source_records
    record=file_record(request_path)
    request,proposal=validate_request(record,current_sources=local_source_records('D6'))
    if os.environ.get('CUDA_VISIBLE_DEVICES') not in (None,'0'):
        raise ValueError('qualification requires the approved unmasked single GPU')
    for variable in ('LD_PRELOAD','LD_AUDIT','PYTHONPATH','PYTHONHOME'):
        if variable in os.environ:
            raise ValueError('unreviewed loader/path injection: '+variable)
    if request['record_kind']!='actual':
        raise ValueError('fixture cannot dispatch actual GPU qualification')
    root=Path(request['ledger_path']).resolve().parent;output=Path(request['output']).absolute()
    trace=output.with_suffix('.syscalls.log');trace_receipt=output.with_suffix('.trace-record.json')
    if (trace.exists() or trace.is_symlink() or trace_receipt.exists() or trace_receipt.is_symlink() or
            output!=root/'jobs'/JOB or output!=output.resolve() or output.exists() or
            output.is_symlink() or output.with_suffix('.log').exists() or output.with_suffix('.log').is_symlink() or
            output.with_name(output.name+'-temporary').exists() or output.with_name(output.name+'-temporary').is_symlink()):
        raise ValueError('fresh owned output and supervisor log required')
    if proposal['seconds']!=180 or proposal['cleanup_seconds']!=30:
        raise ValueError('exact 180-second qualification with 30-second cleanup reserve required')
    ledger=Ledger(request['ledger_path'],dict(load(),new_download_gib_limit=110,new_artifact_disk_gib_limit=210))
    if any(row.get('event')=='reserve' for row in ledger.states().values()):
        raise ValueError('active attempt prevents qualification recovery dispatch')
    def sample():
        reading=resources(root,gpu=True)
        if reading['device_bytes']>proposal['device_bytes']:
            raise ValueError('driver qualification device cap exceeded')
        if owned_artifact_bytes(output)>proposal['artifact_bytes']-TERMINAL_HEADROOM:
            raise ValueError('driver qualification artifact cap exceeded')
        return reading
    def accept(out):
        # Called only after tracer exit and supervisor child-survival checks.
        publish_result_envelope(out,record,proposal,validate_result)
        return dict(status='passed',scope='GPU driver import; two strict CPU loads; no inference')
    ledger.authorize_depth_driver_qualification_local_bind(record)
    try:
        supervise(ledger,JOB,request['command'],output,evidence=reservation_evidence(record,request),sample_resources=sample,
            validate_result=accept,poll_seconds=.5,cpu_workers_limit=7,seconds_limit=180,cleanup_reserve_seconds=30)
    except BaseException:
        finish=ledger.states().get(JOB,{})
        if (finish.get('event')=='finish' and finish.get('cleanup_confirmed') is True and
                finish.get('cleanup_uncertain') is False and finish.get('surviving_pids')==[] and
                trace.is_file() and not trace.is_symlink()):
            # Retention only: a failed finish can never promote this trace.
            if owned_artifact_bytes(output)<=proposal['artifact_bytes']-TERMINAL_HEADROOM:
                write_json(trace_receipt,file_record(trace))
        raise
    states=ledger.states();finish=states.get(JOB,{})
    if (finish.get('event')!='finish' or finish.get('status')!='complete' or
            finish.get('result')!=file_record(output/'result.json') or finish.get('cleanup_confirmed') is not True or
            finish.get('cleanup_uncertain') is not False or finish.get('surviving_pids')!=[] or
            finish.get('deadline_exceeded') is not False or any(row.get('event')=='reserve' for row in states.values())):
        raise ValueError('accepted exact clean qualification finish with no active attempt required')
    validate_result(read_json(output/'result.json'),record,cleanup_confirmed=finish['cleanup_confirmed'])
    if owned_artifact_bytes(output)>proposal['artifact_bytes']-TERMINAL_HEADROOM:
        raise ValueError('driver qualification terminal evidence headroom exhausted')
    write_json(output/'finish.json',finish)
    if owned_artifact_bytes(output)>proposal['artifact_bytes']:
        raise ValueError('driver qualification terminal evidence exceeded artifact cap')
    return finish


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request',required=True)
    dispatch(parser.parse_args().request)
