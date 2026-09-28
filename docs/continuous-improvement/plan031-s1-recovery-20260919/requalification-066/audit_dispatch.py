"""Preserve the consumed attempt's observed outcome without changing the ledger."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record,read_json
from vipe_benchmark.ledger import Ledger
from vipe_benchmark import s1_recovery as s1

HERE=Path(__file__).resolve().parent
LOCAL=ROOT/'.local/vipe-alternatives/plan031-20260913T032700Z'
raw=(LOCAL/'ledger.jsonl').read_bytes();events=Ledger(LOCAL/'ledger.jsonl',load()).events()
assert len(events)==453
assert hashlib.sha256(raw[:334929]).hexdigest()=='1710e2388c6398a5093e75d71a42c75adf4c0ef5817d0ac6de3709f48c56a13a'
assert [e['event'] for e in events[449:]]==['s1_source_requalified','reserve','temporary_directory','finish']
reserve,temporary,finish=events[450:]
assert finish['status']=='failed' and finish['cleanup_confirmed'] and not finish['cleanup_uncertain']
assert finish['surviving_pids']==[] and finish['helper_ownership']==[]
assert finish['primary_failure']['phase']=='prelaunch' and finish['terminal_receipt'] is None
assert Path(temporary['path']).is_dir() and not list(Path(temporary['path']).iterdir())
authorization=reserve['evidence']['authorization']
s1.validate_binding(LOCAL,load(),authorization,consumed=True)
try:s1.validate_binding(LOCAL,load(),authorization)
except ValueError as exc:
    refusal=str(exc);assert 'consumed' in refusal
else:raise AssertionError('consumed attempt incorrectly reusable')
failure=LOCAL/'jobs/S1-calibration-recovery-001/helper-error-0309e72198384773bd674d6f7ac98dcf-1.json'
error=read_json(failure)
assert 'operation(read_record,clock.mapping()' in error['error']
assert "256*1024" in error['error'] and 'progress regular file capacity' in error['error']
request=reserve['evidence']['request'];assert file_record(request['path'])==request and request['bytes']==353132
totals=Ledger(LOCAL/'ledger.jsonl',load()).totals(events)
assert totals['gpu']['attempts']==31 and totals['gpu']['reserved_seconds']==0
assert not any(e['event']=='started' and e.get('job_id')==s1.JOB for e in events)
def preserve(path,data):
    with path.open('xb') as stream:stream.write(data)
    return file_record(path)
snapshot=preserve(HERE/'post-dispatch-ledger.jsonl',raw)
failure_snapshot=preserve(HERE/'post-dispatch-helper-error.json',failure.read_bytes())
result=dict(status='failed_before_worker_launch',attempt_consumed=True,redispatch_authorized=False,
    reconstruction_authorized=False,original_449_event_prefix_unchanged=True,
    ledger=snapshot,live_ledger=file_record(LOCAL/'ledger.jsonl'),events=len(events),
    reservation=reserve,finish=finish,totals=totals,validate_binding_consumed_passed=True,
    unconsumed_binding_refusal=refusal,temporary_directory_empty=True,
    failure=file_record(failure),failure_snapshot=failure_snapshot,
    root_cause=dict(request=request,request_limit_bytes=256*1024,actual_bytes=request['bytes'],
                   source='scripts/vipe_benchmark/s1_progress.py:453'),
    host_observations=dict(gpu_compute_query=dict(chunk_id='64dc38',exit_code=0,output=''),
        process_query=dict(chunk_id='c4142a',exit_code=0,matching_payloads=[],
                           note='Only the ps/rg inspection commands matched their own search text.')))
assert (LOCAL/'ledger.jsonl').read_bytes()==raw
with (HERE/'dispatch-outcome.json').open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps({k:result[k] for k in ('status','attempt_consumed','events','totals','validate_binding_consumed_passed','unconsumed_binding_refusal','temporary_directory_empty')},indent=2))
