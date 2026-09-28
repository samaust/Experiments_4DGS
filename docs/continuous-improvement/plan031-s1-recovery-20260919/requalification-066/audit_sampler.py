"""Read-only host differential and unchanged-deadline sampler qualification."""
import hashlib
import importlib.util
import json
import sys
import time
from pathlib import Path

ROOT = Path.cwd()
sys.path.insert(0, str(ROOT / 'scripts'))
from vipe_benchmark import budgets
from vipe_benchmark.config import load
from vipe_benchmark.execution import resources, s1_sampling_operation
from vipe_benchmark.files import file_record
from vipe_benchmark.supervisor import monitored_call

HERE = Path(__file__).resolve().parent
LOCAL = ROOT / '.local/vipe-alternatives/plan031-20260913T032700Z'
old_path = HERE / 'old-sources/scripts/vipe_benchmark/budgets.py'
spec = importlib.util.spec_from_file_location('vipe_benchmark.legacy_budget066', old_path)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
before = (LOCAL / 'ledger.jsonl').read_bytes()
comparisons = []
for _ in range(3):
    start = time.monotonic()
    historical = old._snapshot(LOCAL)
    old_seconds = time.monotonic() - start
    start = time.monotonic()
    current = budgets._snapshot(LOCAL)
    new_seconds = time.monotonic() - start
    assert historical == current, (historical, current)
    comparisons.append(dict(exact_all_fields_equal=True, old_seconds=old_seconds,
                            new_seconds=new_seconds))
direct = []
for _ in range(5):
    start = time.monotonic()
    reading = resources(LOCAL, gpu=True)
    direct.append(dict(seconds=time.monotonic()-start, reading=reading))
supervised = []
sample = s1_sampling_operation(LOCAL)
for _ in range(5):
    start = time.monotonic()
    reading = monitored_call(sample, start+2., sample, load(),
        dict(device_bytes=0, artifact_bytes=0, download_bytes=0), phase='initial_sample')
    supervised.append(dict(seconds_including_setup_cleanup=time.monotonic()-start,
                           reading=reading, unchanged_one_second_request_deadline_passed=True))
assert (LOCAL / 'ledger.jsonl').read_bytes() == before
result = dict(old_source=file_record(old_path), current_source=file_record(ROOT/'scripts/vipe_benchmark/budgets.py'),
    comparisons=comparisons, direct=direct, supervised=supervised,
    ledger=dict(bytes=len(before), events=len(before.splitlines()), sha256=hashlib.sha256(before).hexdigest(), unchanged=True),
    snapshot={k: ({str(p):v for p,v in value.items()} if isinstance(value,dict) else value)
              for k,value in current.items()})
with (HERE/'sampler-audit.json').open('x') as stream:
    json.dump(result, stream, indent=2); stream.write('\n')
print(json.dumps(result, indent=2))
