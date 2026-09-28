"""Append the validated Plan066 source amendment once; never reserve a GPU job."""
import hashlib
import json
import sys
from pathlib import Path

ROOT=Path.cwd();sys.path.insert(0,str(ROOT/'scripts'))
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record
from vipe_benchmark.ledger import Ledger
from vipe_benchmark import s1_recovery as s1

HERE=Path(__file__).resolve().parent
LOCAL=ROOT/'.local/vipe-alternatives/plan031-20260913T032700Z'
destination=HERE/'registration-result.json'
assert not destination.exists(), 'registration result already exists; inspect without retrying'
raw=(LOCAL/'ledger.jsonl').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='1710e2388c6398a5093e75d71a42c75adf4c0ef5817d0ac6de3709f48c56a13a'
events=[json.loads(line) for line in raw.splitlines()]
assert len(events)==449 and events[-1]['event']=='component_recovery_authorized'
config=load();ledger=Ledger(LOCAL/'ledger.jsonl',config);totals=ledger.totals(events)
amendment=file_record(HERE/'source-requalification.json')
event=s1.register_source_requalification(LOCAL,config,amendment)
after=(LOCAL/'ledger.jsonl').read_bytes();current=ledger.events()
assert after.startswith(raw) and len(current)==450 and current[-1]==event
assert ledger.totals(current)==totals
authorization=json.loads((HERE/'source-requalification.json').read_text())['authorization']
s1.validate_binding(LOCAL,config,authorization)
result=dict(event=event,amendment=amendment,original_449_event_prefix_unchanged=True,
            events=len(current),ledger=file_record(LOCAL/'ledger.jsonl'),totals=totals,
            validate_binding_passed=True,gpu_attempt_reserved=False)
with destination.open('x') as stream:json.dump(result,stream,indent=2);stream.write('\n')
print(json.dumps(result,indent=2))
