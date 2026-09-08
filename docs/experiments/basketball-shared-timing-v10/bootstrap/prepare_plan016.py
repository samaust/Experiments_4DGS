import sys,json,time,hashlib,subprocess
from pathlib import Path
sys.path.insert(0,'scripts')
from basketball_shared_provenance_v9 import verify_hashes
from basketball_shared_benchmark_v9 import diagnostic_controls
from basketball_audit import sha256
R=Path('docs/experiments/basketball-shared-timing-v9');O=Path('docs/experiments/basketball-shared-timing-v10');O.mkdir()
def write(p,d):p.write_text(json.dumps(d,indent=2,allow_nan=False)+'\n')
start=1788843120.0 # 04:52 UTC, before implementation inspection
p=json.loads(Path('configs/basketball-rev2/timing-shared-v9.json').read_text());p['schema']='basketball-shared-trajectories/v10';p['investigation_started_unix']=start;p['clock_note']='Plan 016 clock anchored before implementation inspection at 2026-09-08 04:52 UTC; no restart.'
p.pop('v9');p['v10']=dict(deadlines_minutes=dict(prepare=10,persist=20,baseline=35,metric=45,initialization=52,stopping=60,adapt=60,benchmark=75,package=90,verify=90),max_workers=6,cpu_workers=8,numerical_threads=1,max_iterations=200,max_distinct_states=200,max_policies=5,max_attempts_per_policy=81,max_scientific_attempts=405,max_preflight_attempts=6,accepted_timing=None,production_candidate=None,final_validation_protocol=None,full_screens_authorized=False)
p['v10']['absolute_deadlines']={k:start+60*v for k,v in p['v10']['deadlines_minutes'].items()}
write(Path('configs/basketball-rev2/timing-shared-v10.json'),p)
O=O/'prepare';O.mkdir();hashes={};substitutions=[]
cor=json.loads((R/'corrections/serialization.json').read_text())
for r in cor['source_replacements']:
 assert sha256(r['path'])==r['corrected_sha256'] and sha256(r['archive'])==r['original_sha256'];substitutions.append(r)
for f in sorted(R.rglob('*')):
 if f.is_file():
  data=f.read_bytes();committed=subprocess.check_output(['git','show','HEAD:'+str(f)]);assert data==committed,str(f);hashes[str(f)]=sha256(f)
for f in R.glob('*/result.json'):
 d=json.loads(f.read_text())
 for field in ['source_sha256','artifacts_sha256']:
  hs=d.get(field,{})
  if f.parent.name=='prepare':
   for n,h in hs.items():
    archive=R/'restart'/Path(n).name
    if field=='source_sha256' and archive.exists():assert sha256(archive)==h;substitutions.append(dict(path=n,archive=str(archive),original_sha256=h,corrected_sha256=sha256(n)))
    else:verify_hashes({n:h})
  else:verify_hashes(hs)
ad=json.loads((R/'prepare-resumed/admission.json').read_text())
for field in ['source_sha256','installed_solver_sha256','markers']:verify_hashes(ad[field])
frozen=json.loads((R/'diagnose/candidate-freeze.json').read_text());verify_hashes(frozen['implementation_sha256'])
manifest=json.loads(Path(frozen['manifest']).read_text());assert [len(manifest[k]) for k in ['targets','dependencies','joint_targets','joint_dependencies']]==[18,20,4,3];assert manifest['scheduled_per_policy']==81
controls=diagnostic_controls(R/'diagnose');assert len(controls)==47
write(O/'benchmark-manifest.json',manifest);write(O/'controls.json',controls)
frozen.update(manifest=str(O/'benchmark-manifest.json'),manifest_sha256=sha256(O/'benchmark-manifest.json'),maximum_attempts=405,maximum_preflight_attempts=6,frozen_unix=time.time())
write(O/'policies.json',frozen)
write(O/'preflight-allocations.json',dict(cases=['conditional-03/cold','conditional-02/cold','conditional-00/cold','conditional-04/cold','conditional-03/cold','conditional-00/cold'],last_two='persist success then interrupt fresh actual worker after journaled numerical entry',max_attempts=6,benchmark_seeds=False))
write(O/'admission.json',dict(passed=True,frozen_unix=time.time(),committed_v9_sha256=hashes,historical_substitutions=substitutions,inherited=ad,actual_inherited_source_sha256={f:sha256(f) for f in frozen['implementation_sha256']},v9_reported_qualifications=50,v9_verified_baseline_records=0,v9_baseline_usable=False,config_sha256=sha256('configs/basketball-rev2/timing-shared-v10.json')))
assert time.time()<p['v10']['absolute_deadlines']['prepare']
print('admitted',len(hashes),'v9 files; frozen 81 attempts and 47 controls',flush=True)
