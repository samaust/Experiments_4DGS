"""Immutable admission and signed stationarity supplement for Plan 014."""
from pathlib import Path
import shutil
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes
from basketball_shared_diagnose_v5 import compressed_read
from basketball_shared_recovery_v8 import implementation,check

def prepare(p,output):
    check(p);verify_hashes(read('docs/experiments/basketball-shared-timing-v6/prepare/cross-version-manifest.json')['installed_solver_sha256']);root=Path('docs/experiments/basketball-shared-timing-v7');e=read(p['v7_evidence'])
    verify_hashes(e['source_sha256']);verify_hashes(e['artifacts_sha256'])
    hashes={p['v7_evidence']:sha256(p['v7_evidence']),**e['source_sha256'],**e['artifacts_sha256']}
    for stage in ['prepare','diagnose','package']:
        r=read(root/stage/'result.json')
        verify_hashes(r['source_sha256']);verify_hashes(r['artifacts_sha256']);hashes.update(r['source_sha256']);hashes.update(r['artifacts_sha256'])
    manifest=compressed_read(root/'prepare/diagnostic-manifest.json.gz');verify_hashes(manifest['source_sha256']);hashes.update(manifest['source_sha256'])
    old=read('configs/basketball-rev2/timing-shared-v6.json')
    for k in ['source_sha256','fit_frames','roles','configurations','held_out_cameras','independent_solver','independent_initialization','pilot_groups','pilot_lags']:
        if p[k]!=old[k]:raise ValueError('inherited policy changed '+k)
    from basketball_shared_verify_v6 import verify_pilot
    from basketball_shared_synthetic_v2 import synthetic
    groups,cameras,_,_=synthetic('direction_changes',0.,-.1,100,groups=12)
    baseline=verify_pilot(Path('docs/experiments/basketball-shared-timing-v6'),groups,cameras)
    saved=read(root/'prepare/baseline.json');detail=saved['attempts_detail']
    assert len(detail)==144 and sum(r['valid'] for r in detail)==94
    assert sum(r['valid'] for r in detail if r['weight'])==72 and sum(r['valid'] for r in detail if not r['weight'])==22
    assert len([r for r in detail if not r['valid'] and r['iterations']==200])==50
    assert baseline['three_start_disagreements']==5 and baseline['qualified_reference_failures']==9
    assert baseline['required_transfers']==[True]*3+[False]*3
    assert len(manifest['references'])==441 and sum(r['historical'] for r in manifest['references'])==9
    write(output/'baseline.json',dict(**baseline,regularized_qualified=72,data_only_qualified=22,iteration_limit_failures=50))
    shutil.copyfile(root/'prepare/diagnostic-manifest.json.gz',output/'diagnostic-manifest.json.gz')
    write(output/'cross-version-manifest.json',dict(source_sha256=hashes))
    write(output/'implementation.json',dict(source_sha256=implementation()))
    write(output/'experiments-freeze.json',dict(policy=p['v8'],groups=p['pilot_groups'],lags=p['pilot_lags'],conditioning_attempts=144,scalar_initial_attempts=7344,historical_states_diagnostic_only=True))
    check(p)
    return dict(status='passed',terminal_kind=None,blockers=[],references=432,historical=9)

def diagnose(p,output,predecessor):
    from basketball_shared_verify_v8 import verify_recovery,verify_escape
    from basketball_shared_diagnose_v5 import compressed_write
    import numpy as np
    verify_recovery(p,predecessor,output/'recovery-verification.json')
    verify_escape(p,output/'escape-reuse.json')
    records=compressed_read('docs/experiments/basketball-shared-timing-v7/diagnose/states.json.gz')['records']
    supplement=compressed_read(predecessor/'supplement.json.gz')['records'];pairs=[]
    for old in supplement:
        ref=next(r for r in records if r['historical'] and r['state_key']==old['state_key'])
        ref['stationarity'].update(old['reconstruction'],multiplier_KKT_available=True,evidence=old['evidence'])
        new=min((r for r in records if not r['historical'] and r['label']=='returned' and (r['group_id'],r['weight'],r['lag'])==(ref['group_id'],ref['weight'],ref['lag'])),key=lambda r:r['objective'])
        pairs.append(dict(group_id=ref['group_id'],lag=ref['lag'],historical_cost=ref['objective'],v6_cost=new['objective'],historical_KKT=ref['stationarity']['KKT_inf'],v6_KKT=new['stationarity']['KKT_inf'],signed_historical_stationarity=ref['stationarity']))
    compressed_write(output/'states.json.gz',dict(records=records))
    write(output/'diagnostic-decision.json',dict(passed=True,attempt_references=432,historical_references=9,pairs=pairs,historical_states_diagnostic_only=True))
    return dict(status='passed',terminal_kind=None,blockers=[])
