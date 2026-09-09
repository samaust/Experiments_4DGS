"""Audit retained Plan 024 evidence and budgets without running new experiments."""
import collections,hashlib,json,math
from pathlib import Path
root=Path.cwd();report=root/'docs/research/basketball-sync-pivot';local=root/'.local/sync-pivot'
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def finite(x):
 if isinstance(x,float):assert math.isfinite(x)
 elif isinstance(x,dict):
  for v in x.values():finite(v)
 elif isinstance(x,list):
  for v in x:finite(v)
inputs=read(report/'evaluation-inputs.json')
assert {(e['method'],e['seed']) for e in inputs['runs']}=={(m,s) for m in ['stg-full','freetimegs'] for s in range(3)}
assert len(inputs['runs'])==6 and sha(report/'evaluation-inputs.json')==sha(local/'evaluation-inputs.json')
records=[];keys=None
for e in inputs['runs']:
 assert sha(root/e['checkpoint']['path'])==e['checkpoint']['sha256']
 path=Path(e['render']);r=read(path);ev=read(path.parent.parent/'evaluation.json')
 assert r['checkpoint_sha256']==e['checkpoint']['sha256'] and r['iteration']==5000 and r['complete']
 assert r['manifest_sha256']==sha(local/'basketball-zero/manifest.json')
 assert len(r['frames'])==350 and ev['reload']==dict(fresh_process=True,compared=13,png_identical=True,float_identical=True,complete=True)
 metric=local/f"evaluation/metrics/worker/{e['method']}-seed{e['seed']}.json";m=read(metric);finite(m)
 assert m['complete'] and m['iteration']==5000 and len(m['frames'])==350 and m['render_sha256']==sha(path)
 current={(f['camera'],f['frame_id'],f['split']) for f in m['frames']}
 if keys is None:keys=current
 assert current==keys and len(current)==350
 assert collections.Counter(f['split'] for f in m['frames'])=={'heldout-camera':200,'temporal-interpolation':150}
 assert sum('temporal_difference_mae' in f for f in m['frames'])==316
 assert all(f['full'] and f['dynamic'] and f['motion_pixels'] for f in m['frames'])
 records.append(dict(method=e['method'],seed=e['seed'],render=str(path.relative_to(root)),render_sha256=sha(path),metrics=str(metric.relative_to(root)),metrics_sha256=sha(metric),complete_images=350,exact_reload_probes=13,temporal_pairs=316))
ledger=read(report/'gpu-budget.json');assert all(e['status'] in ['completed','failed','conservatively-accounted','failed-import','entrypoint-passed'] for e in ledger['attempts'])
charges=collections.defaultdict(float)
for e in ledger['attempts']:charges[e['allocation']]+=e['charged_seconds']
assert sum(charges.values())<=ledger['limit_seconds']
for allocation,amount in charges.items():assert amount<=ledger['allocation_limits_seconds'][allocation]
before=read(local/'central-training-before.json');after=read(root/'.local/runs/plan-004-training-budget.json')
assert len(before['attempts'])==22 and before['attempts']==after['attempts'][:22]
combined=sum(e['charged_seconds'] for e in after['attempts'])+charges['sync-nerf'];assert combined<86400
protocol=read(report/'evaluation-protocol-v3.json')
for p,h in protocol['files'].items():assert sha(root/p)==h,p
for p,h in read(report/'timing-decision.json')['evidence'].items():assert sha(report/p)==h,p
summary=read(local/'evaluation/metrics/worker/summary.json');finite(summary)
assert summary['inputs_sha256']==sha(local/'evaluation-inputs.json')
assert sha(report/'reconstruction-metrics.json')==sha(local/'evaluation/metrics/worker/summary.json')
for method in ['stg-full','freetimegs']:
 assert summary[method]['iteration']==5000 and len(summary[method]['metrics'])==16
assert len(summary['paired_methods_at_zero']['metrics'])==16
assert summary['timing_correction_benefit']['status']=='unavailable'
result=dict(schema='sync-pivot-final-validation/v1',status='passed',records=records,total_evaluation_images=2100,exact_reload_probes=78,temporal_pairs=1896,historical_training_records_preserved=22,combined_training_seconds=combined,campaign_gpu_seconds=sum(charges.values()),allocation_seconds=dict(charges),frozen_protocol_hashes_match=True,summary_sha256=sha(local/'evaluation/metrics/worker/summary.json'),validator_sha256=sha(Path(__file__)),scientific_limitations='No full-rig timing correction or real-data timing truth; no correction-benefit claim. Tests and reload success do not imply high-quality dynamic reconstruction.')
(report/'final-validation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
