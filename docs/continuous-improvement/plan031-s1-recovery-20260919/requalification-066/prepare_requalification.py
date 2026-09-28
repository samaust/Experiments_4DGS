"""Prepare and validate immutable source evidence; never append the live ledger."""
import copy
import json
import subprocess
import sys
import time
from pathlib import Path

ROOT=Path.cwd()
sys.path.insert(0,str(ROOT/'scripts'))
from vipe_benchmark.config import load
from vipe_benchmark.files import file_record, read_json
from vipe_benchmark.s1_validation_contract import source_paths, validate_wrapper
from vipe_benchmark import s1_recovery as s1

HERE=Path(__file__).resolve().parent
LOCAL=ROOT/'.local/vipe-alternatives/plan031-20260913T032700Z'
AUTH=ROOT/'docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-calibration-recovery-authorization-001.json'
authorization=file_record(AUTH)
document=read_json(AUTH)
old=read_json(document['repair_validation']['path'])
new=copy.deepcopy(old)
new['sources']=[file_record(p) for p in source_paths()]
diff=subprocess.run(['git','diff','--check'],capture_output=True,text=True,check=True)
new['diff_check']=dict(command='git diff --check',exit_code=diff.returncode,stdout=diff.stdout,stderr=diff.stderr)
pair=HERE/'aggregate-timed-006'
new['tests']=[dict(receipt=file_record(pair/'receipt.json'),execution=file_record(pair/'execution.json'))]
validate_wrapper(new,document['semantic_amendment'],document['configuration'])
def publish(path,value):
    with path.open('x') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    return file_record(path)
validation=publish(HERE/'validation.json',new)
raw=(LOCAL/'ledger.jsonl').read_bytes()
events=[json.loads(line) for line in raw.splitlines()]
registration=events[-1]
assert len(events)==449 and registration['event']=='component_recovery_authorized'
changes=[]
for before,after in zip(old['sources'],new['sources']):
    assert before['path']==after['path']
    if before==after:continue
    snapshot=file_record(HERE/'old-sources'/Path(before['path']).relative_to(ROOT))
    assert all(snapshot[k]==before[k] for k in ('bytes','sha256'))
    changes.append(dict(before=before,after=after,old_snapshot=snapshot))
note=dict(schema='plan066-s1-source-requalification/v1',authorization=authorization,
    registration=s1.event_ref(registration),ledger_head=s1.event_ref(registration),
    previous_validation=document['repair_validation'],validation=validation,
    scope='resource-sampler-and-codex-launch; no new allocation; unchanged deadlines',
    approval=file_record(HERE/'approval.md'),plan=file_record(ROOT/'plans/plan_066.md'),
    review=file_record(HERE/'review.md'),changes=changes)
amendment=publish(HERE/'source-requalification.json',note)
candidate=dict(event='s1_source_requalified',job_id=s1.JOB,authorization=authorization,
    amendment=amendment,sequence=len(events),previous_sha256=registration['event_sha256'],recorded_unix=time.time())
candidate['event_sha256']=s1.object_hash(candidate)
s1.validate_binding(LOCAL,load(),authorization,events=events+[candidate])
assert (LOCAL/'ledger.jsonl').read_bytes()==raw
print(json.dumps(dict(validation=validation,amendment=amendment,changed_sources=len(changes),
    prospective_binding_passed=True,ledger_unchanged=True),indent=2))
