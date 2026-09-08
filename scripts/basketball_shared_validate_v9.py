"""Independent terminal audit, including unavailable baseline provenance and saved-state arithmetic."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='1'
from pathlib import Path
import argparse
import json
import time
import numpy as np
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_shared_diagnose_v5 import compressed_read
from basketball_shared_diagnose_v9 import make_problem
from basketball_shared_verify_v9 import verify_package,direct_gradient
from basketball_shared_verify_v5 import objective_depth
from basketball_shared_solver_v4 import ConstrainedProblem
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_provenance_v9 import verify_hashes


def validate(root,output):
    if output.exists():raise FileExistsError('fresh verification output required')
    policy=read('configs/basketball-rev2/timing-shared-v9.json')
    def check():
        if time.time()>=policy['investigation_started_unix']+5400:raise TimeoutError('Plan 015 final verification deadline')
    package_output=output.with_name(output.stem+'-package.json')
    verify_package(root,package_output);base=read(package_output)
    correction=read(root/'corrections/serialization.json')
    for r in correction['source_replacements']:
        assert sha256(r['path'])==r['corrected_sha256'] and sha256(r['archive'])==r['original_sha256']
    assert correction['scientific_retries']==0
    manifest=read(root/'prepare-resumed/benchmark-manifest.json');assert manifest['scheduled_per_policy']==81
    # Independently count durable invocation/completion events and distinguish reported qualification.
    scheduled=read(root/'adapt/baseline/scheduled.json');allocated={};entered={};completed={};files=[]
    for f in sorted((root/'adapt/baseline').glob('*.events.jsonl')):
        for line in f.read_text().splitlines():
            e=json.loads(line);dest={'allocated':allocated,'entered':entered,'completed':completed}[e['event']]
            assert e['id'] not in dest;dest[e['id']]=e
        files.append(dict(path=str(f),sha256=sha256(f)))
    assert len(allocated)==len(completed)==scheduled['attempts']==81
    assert len(entered)==sum(r['executed'] for r in completed.values())==75
    assert set(entered)=={i for i,r in completed.items() if r['executed']}
    reported=sum(r['qualified'] for r in completed.values());assert reported==50
    assert len(base['unavailable_attempt_artifacts'])==18 and base['attempt_records']==0
    states=0;returns=0;maxF=maxG=maxD=maxK=0.;groups,cameras,_,_=synthetic('direction_changes',0.,-.1,100,groups=12)
    decision=read(root/'diagnose/diagnostic-decision.json')
    for ref in decision['artifacts']:
        check();assert sha256(ref['path'])==ref['sha256']
        for record in compressed_read(ref['path'])['records']:
            r=record['reference'];p=make_problem(r,check);a=ConstrainedProblem(p)
            meta=dict(knots=p.spline.t.tolist(),group_ids=[r['group_id']],weight=r['weight'],diameter=p.diameter,center=p.center.tolist())
            for s in record['states']:
                check();x=np.asarray(s['x']);full=np.r_[r['offset'],x] if 'offset' in r else x
                F,D=objective_depth(groups,cameras,meta,full,r['lag']);G=direct_gradient(p,x)
                np.testing.assert_allclose(F,s['objective'],atol=1e-10,rtol=1e-9)
                np.testing.assert_allclose(D,s['depths'],atol=1e-12,rtol=1e-12)
                np.testing.assert_allclose(G,s['G'],atol=1e-10,rtol=1e-8)
                maxF=max(maxF,abs(F-s['objective']));maxD=max(maxD,float(np.max(np.abs(D-s['depths']))));maxG=max(maxG,float(np.max(np.abs(G-s['G']))))
                if s['KKT'] is not None:
                    assert s['label']=='returned';KKT=G+np.asarray(s['C_depth'])+np.asarray(s['C_bounds'])
                    np.testing.assert_allclose(KKT,s['KKT'],atol=1e-10,rtol=1e-8);maxK=max(maxK,float(np.max(np.abs(KKT-s['KKT']))));returns+=1
                else:assert not s['multiplier_KKT_available']
                states+=1
    audit=compressed_read(root/'account/counter-correction.json.gz');witnesses=0
    for r in audit['records']:
        assert r['exact_old_complete_entry_count'] is None and 171<=r['exported_states']<=193
        assert r['callback_roundtrip_witnesses']
        for w in r['callback_roundtrip_witnesses']:
            q=np.frombuffer(bytes.fromhex(w['direct_hex']),dtype='<f8');qr=np.frombuffer(bytes.fromhex(w['roundtrip_hex']),dtype='<f8');scale=np.r_[25.,np.ones(len(q)-1)]
            np.testing.assert_array_equal(qr,(q*scale)/scale)
            assert q.tobytes()!=qr.tobytes() and (q*scale).tobytes()==(qr*scale).tobytes();witnesses+=1
    assert len(audit['records'])==22 and witnesses==474
    final=dict(base)
    final.update(verification_status='passed_for_retained_evidence_with_documented_computational_blocker',
        baseline=dict(scheduled=81,executed=75,missing=6,reported_qualified=reported,independently_verified_qualified=None,full_attempt_records_retained=0,source_events=files),
        saved_diagnostics=dict(states=states,returned_KKT=returns,maximum_objective_error=maxF,maximum_gradient_error=maxG,maximum_depth_error=maxD,maximum_KKT_error=maxK),
        v8_counter_correction=dict(affected_attempts=22,callback_roundtrip_witnesses=witnesses,old_complete_state_totals=None),
        no_scientific_retries=True,standalone_arms_executed=0,final_benchmark_executed=0,ready_for_full_screens=False,
        final_verifier_sha256=sha256(__file__),elapsed_seconds=time.time()-policy['investigation_started_unix'])
    check();write(output,final)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--root',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();validate(a.root,a.output)
