"""Plan 015 saved evidence admission, deterministic selection and counter correction."""
from pathlib import Path
from collections import Counter
import hashlib
import time
import numpy as np
from basketball_scale import read, write
from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes
from basketball_shared_diagnose_v5 import compressed_read, compressed_write

ROOT = Path('docs/experiments/basketball-shared-timing-v8')
PATHS = ['cold', 'ascending', 'descending']

def key(g,w,l,o):
    return (int(g),float(w),float(l),float(o))

def row_ref(file, data, path, offset, row):
    return dict(source=str(file), source_sha256=sha256(file), group_id=data['group_id'],
                weight=data['weight'], lag=data['lag'], offset=float(offset), path=path,
                qualified=row['valid'], executed=row['executed'], seed_offset=row.get('seed_offset'),
                seed_start=row.get('seed_start'), status=row.get('status'), message=row.get('message',row.get('error')))

def prepare(p, output):
    from basketball_shared_workflow_v9 import check
    hashes={}
    # Follow hash-bound stage sources, including inherited manifests, without reading roles' images.
    for version in range(2,9):
        epath=Path(f'docs/experiments/basketball-shared-timing-v{version}/evidence.json')
        e=read(epath); hashes[str(epath)]=sha256(epath)
        for name in ['source_sha256','artifacts_sha256']:
            verify_hashes(e.get(name,{})); hashes.update(e.get(name,{}))
    for f in sorted(ROOT.glob('*/result.json')):
        r=read(f)
        for name in ['source_sha256','artifacts_sha256']:
            verify_hashes(r.get(name,{})); hashes.update(r.get(name,{}))
    installed=read('docs/experiments/basketball-shared-timing-v6/prepare/cross-version-manifest.json')['installed_solver_sha256']
    verify_hashes(installed); hashes.update(installed)
    markers=read('docs/experiments/basketball-shared-timing-v6/verification-final.json')['markers']
    verify_hashes(markers); hashes.update(markers)
    from basketball_shared_recovery_v8 import implementation
    impl=implementation(); verify_hashes(read(ROOT/'prepare/implementation.json')['source_sha256'])
    write(output/'admission.json',dict(source_sha256=hashes,installed_solver_sha256=impl,markers=markers))
    counts=Counter();affected=[];joint=[];ratios=[]
    for f in sorted((ROOT/'condition').glob('weight*-group*.json.gz')):
        d=compressed_read(f)
        old=compressed_read(f'docs/experiments/basketball-shared-timing-v6/pilot/{f.name}')
        for lag, rows in d['attempts'].items():
            for r,b in zip(rows,old['attempts'][str(float(lag))]):
                from basketball_shared_solver_v3 import objective_agreement
                counts['conditioning_executed']+=1;counts['conditioning_qualified']+=r['valid']
                counts['conditioning_preserved']+=bool(b['valid'] and r['valid'] and (r['objective']<=b['objective'] or objective_agreement(r['objective'],b['objective'])))
                counts['conditioning_recovered']+=bool(not b['valid'] and r['valid'])
                if not b['valid']:ratios.append(np.inf if r.get('optimality') is None else r['optimality']/b['optimality'])
                ref=dict(source=str(f),source_sha256=sha256(f),group_id=d['group_id'],weight=d['weight'],lag=float(lag),path=r['start'],seed_lag=r['seed_lag'],seed_start=r['seed_start'])
                if r.get('message')=='200 distinct objective evaluations exhausted':
                    affected.append(dict(**ref,exception_owner='v6 ConstrainedProblem.evaluate',exported_states=r['nfev'],exported_ledger_length=len(r['state_ledger']),inner_counter_at_exception=200,inner_exact_state_identities=None,all_entry_distinct_states=None,reason_unknown='v8 omitted inner cache keys, request events and initialization states',state_identity_source='physical state_ledger; conditioned_y only at callbacks',request_types_available=sorted({s['first'] for s in r['state_ledger']})))
                if d['group_id']==11 and d['weight']==1 and float(lag)==-19 and r['start']=='descending':joint.append(ref)
    counts['conditioning_median_KKT_ratio']=float(np.median(ratios))
    assert {k:counts[k] for k in ['conditioning_executed','conditioning_qualified','conditioning_preserved','conditioning_recovered']}==dict(conditioning_executed=144,conditioning_qualified=116,conditioning_preserved=93,conditioning_recovered=23)
    np.testing.assert_allclose(counts['conditioning_median_KKT_ratio'],.2500454027892694,atol=1e-15,rtol=1e-13)
    assert len(affected)==22 and min(r['exported_states'] for r in affected)==171 and max(r['exported_states'] for r in affected)==193
    for gid in [2,9,11]:joint.append(min((r for r in affected if r['group_id']==gid),key=lambda r:(r['weight'],r['lag'],PATHS.index(r['path']))))
    selected={}; strata={}; all_refs={}; absence=[]
    candidates=[]
    for f in sorted((ROOT/'basins').glob('weight*-group*-lag*.json.gz')):
        check(p,'prepare');d=compressed_read(f);counts['profiles']+=1
        assert d['complete'];counts['disagreements']+=len(d['disagreements'])
        counts['initial_scheduled']+=153; counts['refinement_scheduled']+=3*(len(d['fine_added'])+len(d['final_added']))
        for path in PATHS:
            for offset,r in d['curves'][path].items():
                ref=row_ref(f,d,path,offset,r);k=key(d['group_id'],d['weight'],d['lag'],offset)
                all_refs.setdefault(k,[]).append(ref)
                prefix='regularized' if d['weight'] else 'data_only'
                counts[prefix+'_executed']+=r['executed'];counts[prefix+'_qualified']+=r['valid']
                counts[prefix+'_missing']+=not r['executed']
                tags=[]
                if r['valid']:tags.append(prefix+'_control')
                elif not r['executed']:tags.append('missing_directional')
                elif r.get('error')=='no feasible deterministic initialization':tags.append(prefix+'_infeasible_cold');counts[prefix+'_infeasible']+=1
                elif r.get('status')==2:tags.append(prefix+'_xtol');counts[prefix+'_xtol']+=1
                elif r.get('solver_trace') and r['solver_trace'][-1]['iteration']==200:
                    counts[prefix+'_iteration']+=1
                    if not d['weight']:
                        tags.append('cold_iteration' if path=='cold' else 'directional_iteration')
                        init=r.get('initialization_transfer',{})
                        if path!='cold' and init.get('replaced_blocks'):tags.append('support_changing_iteration')
                candidates.append((k,PATHS.index(path),ref,tags))
    candidates.sort(key=lambda v:(*v[0],v[1]))
    wanted=['cold_iteration','directional_iteration','support_changing_iteration','missing_directional','regularized_infeasible_cold','regularized_control','data_only_control']
    for tag in wanted:
        for gid in [2,9,11]:
            eligible=[c for c in candidates if c[0][0]==gid and tag in c[3]]
            if not eligible:absence.append(dict(group_id=gid,stratum=tag));continue
            k,_,r,_=eligible[0];selected.setdefault(k,[]).append(dict(stratum=tag,reference=r));strata.setdefault(tag,[]).append(r)
    xtol=[c for c in candidates if 'regularized_xtol' in c[3]];assert len(xtol)==3
    for k,_,r,_ in xtol:selected.setdefault(k,[]).append(dict(stratum='regularized_xtol',reference=r))
    expected=dict(profiles=48,initial_scheduled=7344,refinement_scheduled=4782,regularized_executed=8454,regularized_qualified=8439,data_only_executed=2142,data_only_qualified=46,data_only_missing=1530,data_only_iteration=2093,data_only_infeasible=3,regularized_iteration=9,regularized_infeasible=3,regularized_xtol=3,disagreements=835)
    assert all(counts[k]==v for k,v in expected.items()),counts
    coverage=read(ROOT/'coverage-verification.json')
    targets=[];deps={}
    for i,(k,labels) in enumerate(sorted(selected.items())):
        refs=sorted(all_refs[k],key=lambda r:PATHS.index(r['path']))
        # Original coarse-grid neighboring coordinates are declared before fresh fits.
        # Archived successful parameters are NEVER imported as seeds.
        sources={}
        for path in PATHS[1:]:
            r=next(r for r in refs if r['path']==path)
            off=r['seed_offset']
            if off is None:off=max(-25.,np.ceil(k[3])-1) if path=='ascending' else min(25.,np.floor(k[3])+1)
            sk=key(*k[:3],off);sources[path]=list(sk)
            if sk not in selected:deps[sk]=dict(group_id=sk[0],weight=sk[1],lag=sk[2],offset=sk[3])
        targets.append(dict(id=f'conditional-{i:02d}',group_id=k[0],weight=k[1],lag=k[2],offset=k[3],labels=labels,references=refs,sources=sources))
    jd={}
    for r in joint:
        if r['seed_lag'] is not None:
            jk=(r['group_id'],r['weight'],r['seed_lag']);jd[jk]=dict(group_id=jk[0],weight=jk[1],lag=jk[2])
    manifest=dict(targets=targets,dependencies=list(deps.values()),joint_targets=joint,joint_dependencies=list(jd.values()),absent_strata=absence,
        target_count=len(targets),dependency_count=len(deps),scheduled_per_policy=3*len(targets)+len(deps)+len(joint)+len(jd),
        selection_order='group, weight, outer lag, nuisance offset, cold/ascending/descending',selection_source_sha256=sha256(__file__),frozen_unix=time.time(),
        source_policy='fresh source cold per declared coordinate; nearest valid within declared source schedule, previous valid within target sweep; missing stays missing',
        diagnostic_directions='four weakest full-J singular vectors, objective gradient, last nonzero saved displacement; no new escape rays',
        historical_states_diagnostic_only=True,accounting_reproductions=[])
    assert len(targets)<=24 and len(deps)<=24 and len(joint)<=4 and len(jd)<=4 and manifest['scheduled_per_policy']<=104, (len(targets),len(deps))
    write(output/'counts.json',dict(counts));write(output/'affected-attempts.json',dict(records=affected))
    write(output/'benchmark-manifest.json',manifest)
    write(output/'coverage-reuse.json',dict(source=str(ROOT/'coverage-verification.json'),sha256=sha256(ROOT/'coverage-verification.json'),record=coverage))
    write(output/'audit-findings.json',dict(mechanism='objective uses q_roundtrip=((P@y)*scale)/scale; Hessian uses q_direct=P@y. Byte-keyed inner cache distinguishes roundoff neighbors omitted from physical exported ledger. Constraint-only and initialization evaluations additionally bypass its state budget.',
        contract_deviations=['v8 coefficient block is V diag(t), not symmetric V diag(t) V.T','v8 origin is zero, not destination-cold q'],
        verifier_blind_spot='checked exported nfev <=200 and trace length <=200 without observing inner numerical-entry keys or sanitation/constraint-only evaluations',
        historical_exact_all_entry_counts=None,cap_breach_proven=False,conditioning_would_pass_after_repair=None,
        preserved_claims=['returned physical objective/depth/KKT evidence remains hash-bound','scalar coverage and historical recovery unaffected by conditioning counter discrepancy'],
        correction_scope='new v9 accounting and explicit coordinate-contract correction; immutable v8 remains rejected'))
    check(p,'prepare')
    return dict(status='passed',terminal_kind=None,blockers=[],executed_counts=dict(scientific_attempts=0),targets=len(targets),dependencies=len(deps))
