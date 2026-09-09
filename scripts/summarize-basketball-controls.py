"""Package retained Plan 024 control results without performing new GPU work."""
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
REPORT=ROOT/'docs/research/basketball-sync-pivot'
LOCAL=ROOT/'.local/sync-pivot'


def read(path):return json.loads(path.read_text())
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def relative(path):return str(path.relative_to(ROOT))


def main():
    ledger=read(REPORT/'gpu-budget.json')
    before=read(LOCAL/'central-training-before.json')
    after=read(ROOT/'.local/runs/plan-004-training-budget.json')
    # Use the original record structure; never modify either training ledger.
    key='attempts'
    if len(before[key])!=22:raise ValueError('unexpected historical snapshot')
    preserved=after[key][:len(before[key])]==before[key]
    if not preserved:raise ValueError('historical training records changed')
    rows=[]
    for method in ['stg-full','freetimegs']:
        for seed in range(3):
            path=LOCAL/f'runs/{method}-zero-seed{seed}'
            worker=path/'worker/worker-result.json';supervisor=path/'supervisor-result.json'
            row=dict(method=method,seed=seed,condition='zero',path=relative(path),status='not completed')
            entries=[e for e in ledger['attempts'] if e['role']==f'{method}-basketball-zero-seed{seed}']
            if entries:row['accounting']=entries[0]
            if worker.exists():
                row['worker']=read(worker);row['worker_sha256']=sha(worker)
                row['status']='retained worker result'
                row['checkpoints']=[dict(path=relative(p),bytes=p.stat().st_size,sha256=sha(p)) for p in sorted((path/'worker').glob('checkpoint-*.pt'))]
            if supervisor.exists():row['supervisor']=read(supervisor)
            evaluation=LOCAL/f'evaluation/{method}-seed{seed}/worker/evaluation.json'
            if evaluation.exists():
                row['evaluation']=read(evaluation);row['evaluation_sha256']=sha(evaluation)
                first=evaluation.parent/'first/render.json';r=read(first)
                row['render']={k:v for k,v in r.items() if k!='frames'}
            rows.append(row)
    charges={}
    for entry in ledger['attempts']:
        charges[entry['allocation']]=charges.get(entry['allocation'],0)+entry['charged_seconds']
    central_seconds=sum(e['charged_seconds'] for e in after[key])
    result=dict(central_training_seconds=central_seconds,combined_training_seconds=central_seconds+charges.get('sync-nerf',0),
                schema='basketball-zero-controls/v1',runs=rows,gpu_charged_seconds=charges,
                gpu_total_seconds=sum(charges.values()),historical_training_records_preserved=preserved,
                historical_record_count=len(before[key]),historical_snapshot_sha256=sha(LOCAL/'central-training-before.json'),
                central_training_ledger_sha256=sha(ROOT/'.local/runs/plan-004-training-budget.json'),
                limitation='Zero is an operational assumption. No corrected condition exists; no timing correction benefit can be estimated.')
    (REPORT/'reconstruction-results.json').write_text(json.dumps(result,indent=2)+'\n')
    metrics=LOCAL/'evaluation/metrics/worker'
    if (metrics/'summary.json').exists():
        (REPORT/'reconstruction-metrics.json').write_text((metrics/'summary.json').read_text())
        temporal=[]
        for p in sorted(metrics.glob('*-seed*.json')):
            r=read(p)
            for split in ['heldout-camera','temporal-interpolation']:
                values=[f['temporal_difference_mae'] for f in r['frames'] if f['split']==split and 'temporal_difference_mae' in f]
                temporal.append(dict(method=r['method'],seed=r['seed'],split=split,count=len(values),mean=sum(values)/len(values) if values else None))
        (REPORT/'temporal-observations.json').write_text(json.dumps(dict(schema='basketball-temporal-observations/v1',runs=temporal,
            definition='Mean absolute RGB error of adjacent predicted frame differences against ground-truth differences; uint8 RGB/255. Descriptive observations, no additional hypothesis test.'),indent=2)+'\n')


if __name__=='__main__':main()
