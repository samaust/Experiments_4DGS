"""Read-only generation and accounting linkage checks, separate from pixels."""
import hashlib
import json
from pathlib import Path
import time

started = time.monotonic()
RUN = Path('/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z')
def load(record):
    p = Path(record['path'])
    data = p.read_bytes()
    assert len(data) == record['bytes'] and hashlib.sha256(data).hexdigest() == record['sha256']
    return json.loads(data)
ledger = [json.loads(line) for line in (RUN / 'ledger.jsonl').read_text().splitlines()]
checks = []
for candidate in ('D0','D1','D2','D3','D4','D5','D7','D11'):
    folder = RUN / 'jobs' / f'plan069-{candidate}-anchor-previews-002'
    result = json.loads((folder/'result.json').read_text())
    slot = result['slot']
    origins = [slot['provenance']['source_result']]
    if candidate in ('D0','D1','D2','D3','D4'):
        origins += [slot['evidence']['historical_fit'],slot['evidence']['historical_check']]
    rows = {}
    for origin in origins:
        generation = load(origin)
        assert generation['status'] == 'complete'
        for row in generation['rows']:
            identity = row.get('identity', row)
            key = (identity['camera'],identity['frame'])
            if key[1] in (100,175):
                prediction = row.get('prediction',row.get('depth'))
                if key in rows:
                    assert rows[key] == prediction
                rows[key] = prediction
    assert len(rows) == 60
    for anchor in result['anchors']:
        assert anchor['prediction'] == rows[anchor['camera'],anchor['frame']]
    accounting_path = folder/'cpu-accounting.json'
    accounting_bytes = accounting_path.read_bytes()
    accounting = json.loads(accounting_bytes)
    assert accounting['status'] == 'complete' and accounting['candidate'] == candidate
    assert load(accounting['result']) == result
    sha = hashlib.sha256(accounting_bytes).hexdigest()
    matching = [event for event in ledger if event.get('evidence',{}).get('sha256') == sha]
    # CPU preparation events carry immutable evidence under a named binding.
    if not matching:
        matching = [event for event in ledger if sha in json.dumps(event)]
    assert len(matching) == 1, (candidate,len(matching))
    checks.append(dict(candidate=candidate, anchors_bound=60, accounting_sha256=sha, accounting_events=1))
report = dict(schema='plan069-independent-preview-bindings/v1',status='pass',checks=checks,elapsed_seconds=time.monotonic()-started,ledger_modified=False,gpu_used=False)
Path(__file__).with_name('bindings.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report))
