"""Independent arithmetic/provenance check of the Plan 013 admission blocker."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='1'
import argparse
import hashlib
from pathlib import Path
import re
import time
import numpy as np
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes
from basketball_shared_diagnose_v5 import compressed_read
from basketball_shared_verify_v5 import objective_depth,verify_partition
from basketball_shared_solver_v6 import ConstrainedProblem
from basketball_shared_spline_v2 import SplineProblem
from basketball_shared_synthetic_v2 import synthetic


def verify(root,output):
    if output.exists():raise FileExistsError('fresh verification required')
    p=read('configs/basketball-rev2/timing-shared-v7.json')
    def check():
        if time.time()>=p['investigation_started_unix']+14400:raise TimeoutError('packaging deadline')
    for stage in ['prepare','diagnose','package']:
        r=read(root/stage/'result.json');verify_hashes(r['source_sha256']);verify_hashes(r['artifacts_sha256'])
    manifest=compressed_read(root/'prepare/diagnostic-manifest.json.gz');verify_hashes(manifest['source_sha256'])
    records=compressed_read(root/'diagnose/states.json.gz')['records']
    assert len(records)==len(manifest['references'])==441
    assert sum(not r['historical'] for r in records)==432
    groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    max_cost=max_depth=max_gradient=max_kkt=0.;returned=0;historical=0;cache={}
    for ref,r in zip(manifest['references'],records):
        check();s=manifest['states'][ref['state_key']]
        assert ref=={k:r[k] for k in ref}
        raw=bytes.fromhex(s['parameter_bytes_le_hex']);assert hashlib.sha256(raw).hexdigest()==s['parameter_sha256']
        np.testing.assert_array_equal(np.frombuffer(raw,dtype='<f8'),s['x'])
        source=ref['source'];assert sha256(source)==ref['source_sha256']
        if source not in cache:cache[source]=compressed_read(source)
        original=next(row for row in cache[source]['attempts'][ref['lag_key']] if row['start']==ref['start'])
        cost,depth=objective_depth(groups,cameras,original,s['x'],s['lag']);stat=r['stationarity']
        np.testing.assert_allclose(cost,r['objective'],rtol=1e-9,atol=1e-10)
        np.testing.assert_allclose(depth,stat['original_depths'],rtol=1e-12,atol=1e-12)
        max_cost=max(max_cost,abs(cost-r['objective']));max_depth=max(max_depth,float(np.max(np.abs(depth-stat['original_depths']))))
        problem=SplineProblem([groups[s['group_id']]],cameras,{1:0.,2:s['lag'],3:0.},window,10,s['weight'],(1,2),check)
        a=ConstrainedProblem(problem);q=np.asarray(s['x'])/a.scale;rr,J=a.evaluate(q);G=np.asarray(2*J.T@rr).ravel()
        np.testing.assert_allclose(G,stat['G'],rtol=1e-10,atol=1e-10);max_gradient=max(max_gradient,float(np.max(np.abs(G-stat['G']))))
        for label,jac in [('data',J.toarray()[:problem.n*2]),('objective_coefficients',J.toarray()[:,problem.n_offsets:])]:
            spectrum=r['spectra'][label];sv=np.linalg.svd(jac,compute_uv=False)
            np.testing.assert_allclose(sv,spectrum['singular_values'],rtol=1e-10,atol=1e-10)
            assert spectrum['exact_zero_columns']==np.flatnonzero(np.all(jac==0,axis=0)).tolist()
            assert spectrum['rank']==sum(sv>spectrum['rank_threshold'])
        if ref['historical']:
            historical+=1;assert original.get('multipliers_depth') is None and original.get('bound_multipliers') is None
            assert not stat['multiplier_KKT_available'] and stat['KKT_inf'] is None
            assert stat['saved_KKT_inf']==original['optimality']
            assert stat['barrier_form']=='v4 raw-depth inequality'
            # The archived raw result must also lack multipliers, not just the compressed export.
        elif ref['label']=='returned':
            returned+=1;z,Dz=a.raw_depth(q);vg=np.asarray(original['multipliers_transformed']);vd=np.asarray(original['multipliers_depth']);vb=np.asarray(original['bound_multipliers'])
            np.testing.assert_allclose(vd,vg/(1+(z-1e-8)**2)**1.5,rtol=1e-12,atol=1e-12)
            kkt=G+Dz.T@vd+vb
            np.testing.assert_allclose(kkt,stat['KKT'],rtol=1e-10,atol=1e-10)
            np.testing.assert_allclose(np.max(np.abs(kkt)),original['optimality'],rtol=1e-8,atol=1e-10)
            max_kkt=max(max_kkt,abs(np.max(np.abs(kkt))-original['optimality']))
        else:assert not stat['multiplier_KKT_available'] and 'KKT' not in stat
    assert returned==144 and historical==9
    raw_path=Path('.local/calibration/basketball-rev2/shared-v4/safeguard/exact-retest/regularized-round0.json')
    raw=read(raw_path)
    # This is the original state cache bound by the immutable v4 evidence.
    archived=[]
    def visit(value):
        if isinstance(value,dict):
            if 'x' in value and 'objective' in value and 'start' in value:archived.append(value)
            for child in value.values():visit(child)
        elif isinstance(value,list):
            for child in value:visit(child)
    visit(raw)
    matches=0
    for ref in manifest['historical']:
        original=next(r for r in cache[ref['source']]['attempts'][str(ref['lag'])] if r['start']==ref['start'])
        found=[r for r in archived if r.get('x')==original['x'] and r['objective']==original['objective']]
        assert found
        assert all(r.get('multipliers_depth') is None and r.get('bound_multipliers') is None and 'v' not in r for r in found)
        matches+=1
    decision=read(root/'diagnose/diagnostic-decision.json');assert not decision['passed'] and len(decision['blockers'])==9
    assert len(manifest['missing'])==9
    old_verification=read('docs/experiments/basketball-shared-timing-v6/verification-final.json')
    verify_hashes(old_verification['markers']);verify_hashes(old_verification['docs_sha256'])
    tests={};logs={}
    for name in ['v7','basketball','budget','selfcap']:
        f=root/f'{name}-tests.log';text=f.read_text();assert re.search(r'\nOK\s*$',text)
        tests[name]=int(re.search(r'Ran (\d+) tests?',text).group(1));logs[str(f)]=sha256(f)
    terminal=read(root/'package/result.json');assert terminal['scientific_solves']==0 and terminal['accepted_timing'] is None
    for field in ['profiles','intervals','candidate_offsets','final_protocol']:assert terminal[field] is None
    assert not terminal['selection_consumed_this_attempt'] and not terminal['final_validation_consumed']
    method=root.with_suffix('.md');links=0
    for link in re.findall(r'\]\(([^)]+)\)',method.read_text()):
        if '://' in link:continue
        target=(method.parent/link.split('#')[0]).resolve()
        assert target.exists() or target==output.resolve(),link
        links+=1
    check()
    write(output,dict(status='passed',terminal_kind='numerical_failure',verifier_sha256=sha256(__file__),
          historical_hashes_verified=True,current_stage_hashes_verified=True,references=441,v6_returned_kkt_checks=returned,
          historical_missing_multiplier_states=historical,original_v4_cache_matches=matches,original_v4_cache_sha256=sha256(raw_path),
          maximum_original_cost_error=max_cost,maximum_original_depth_error=max_depth,maximum_gradient_error=max_gradient,maximum_kkt_error=max_kkt,
          partition=verify_partition(p),markers=old_verification['markers'],tests=tests,test_logs_sha256=logs,documentation_links=links,
          method_sha256=sha256(method),elapsed_seconds=time.time()-p['investigation_started_unix'],within_four_hours=True,accepted_timing=None,
          derivative_and_search_adapters='not implemented or invoked after missing-evidence gate',escape_reuse='unassessed, not invoked'))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--root',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    a=parser.parse_args();verify(a.root,a.output)
