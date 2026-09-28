"""Compare preserved historical and current job-ledger readers, without writes."""
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
from vipe_benchmark import s1_helper_session as current
from vipe_benchmark.files import file_record
HERE=Path(__file__).resolve().parent
old_path=HERE/'old-sources/scripts/vipe_benchmark/s1_helper_session.py'
spec=importlib.util.spec_from_file_location('vipe_benchmark.legacy_helper066',old_path)
old=importlib.util.module_from_spec(spec);sys.modules[spec.name]=old;spec.loader.exec_module(old)
results=[]
for index in range(1,6):
    path=ROOT/f'docs/resolve-blocker/plan031-progress-20260922/.job-ledger-aggregate-049-{index:03d}.jsonl'
    raw=path.read_bytes()
    start=time.monotonic();before=old._job_read(raw);historical_seconds=time.monotonic()-start
    current._job_read(raw)
    start=time.monotonic();after=current._job_read(raw);current_seconds=time.monotonic()-start
    assert before==after
    assert old._job_state(before)==current._job_state(after)
    assert path.read_bytes()==raw
    results.append(dict(ledger=file_record(path),rows=len(after),all_rows_and_state_equal=True,
        historical_seconds=historical_seconds,current_seconds=current_seconds))
path=ROOT/'docs/resolve-blocker/plan031-progress-20260922/.job-ledger-aggregate-049-007.jsonl'
raw=path.read_bytes();rows=current._job_read(raw);prefix=b'';start=time.monotonic()
for index,line in enumerate(raw.splitlines(keepends=True)):
    prefix+=line
    assert current._job_state_raw(prefix)==current._job_state(rows[:index+1]),index
incremental=dict(ledger=file_record(path),successive_prefixes=len(rows),all_states_equal=True,
                 comparison_seconds=time.monotonic()-start)
current._job_state_raw(raw)
for name,operation in [('full_replay',lambda:current._job_state(current._job_read(raw))),
                       ('exact_prefix',lambda:current._job_state_raw(raw))]:
    start=time.monotonic()
    for _ in range(20):operation()
    incremental[name+'_seconds']=(time.monotonic()-start)/20
assert path.read_bytes()==raw
result=dict(old_source=file_record(old_path),current_source=file_record(ROOT/'scripts/vipe_benchmark/s1_helper_session.py'),comparisons=results,incremental=incremental)
with (HERE/'job-line-audit.json').open('x') as stream:
    json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(result,indent=2))
