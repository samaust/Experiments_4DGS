"""Verify actual terminal process absence and, for aggregates, full receipts."""
import json
import sys
from pathlib import Path

ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
from vipe_benchmark.files import file_record,read_json
from vipe_benchmark.s1_helper_session import _job_read,_job_state
from vipe_benchmark.s1_validation_contract import validate_inner,validate_execution

kind,index=sys.argv[1],int(sys.argv[2])
failed='--failed' in sys.argv[3:]
base=ROOT/'docs/resolve-blocker/plan031-progress-20260922'
sidecar=base/f'.job-ledger-{kind}-049-{index:03d}.jsonl'
raw=sidecar.read_bytes();rows=_job_read(raw);state=_job_state(rows)
pids=sorted({r['data']['identity']['pid'] for r in rows if r['event'] in ('root-bound','descendant-bound')})
present=[pid for pid in pids if Path(f'/proc/{pid}').exists()]
result=dict(ledger=file_record(sidecar),pids=pids,present=present,
    payload_roots_retired=all(r['state']=='retired' for r in state['roots'].values()),
    descendants_retired=all(r['state']=='retired' for r in state['descendants'].values()),
    B=state['B'],H_at_capture=state['H'])
if kind=='aggregate' and not failed:
    directory=base/f'{kind}-049-{index:03d}'
    inner=validate_inner(read_json(directory/'receipt.json'))
    execution=validate_execution(read_json(directory/'execution.json'),file_record(directory/'receipt.json'),inner)
    result.update(validate_inner_passed=True,validate_execution_passed=True,
                  receipt=file_record(directory/'receipt.json'),execution=file_record(directory/'execution.json'),
                  elapsed_seconds=execution['elapsed_seconds'],tests=inner['tests_run'])
assert not present and sidecar.read_bytes()==raw
if failed:result['qualification']=False
else:
    assert result['payload_roots_retired'] and result['descendants_retired']
    assert state['B']==0 and state['H']==1
with (Path(__file__).parent/f'owned-{kind}-{index:03d}-cleanup.json').open('x') as stream:
    json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(result,indent=2))
