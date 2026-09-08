"""Independent terminal audit of the frozen v10 run; never invokes optimization."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='1'
import argparse
from pathlib import Path
import time
import numpy as np
from basketball_shared_storage_v10 import read,publish,sha,journal_prefix
from basketball_shared_verify_v10 import inspect_attempt,exact_hashes,verify_schedule
from basketball_shared_workflow_v10 import ROOT,CONFIG,load_records,preservation
from basketball_shared_benchmark_v9 import iteration_ids
from basketball_shared_solver_v6 import transform,MARGIN,support
from basketball_shared_diagnose_v9 import make_problem
from basketball_shared_solver_v3 import objective_agreement


def detailed_evidence(item):
    row=item['row'];directory=Path(item['artifact']['artifact']).parent
    events=journal_prefix(directory/'journal.jsonl')['events']
    if not row['executed']:return dict(passed=True,missing_seed=True)
    a=row['accounting'];states={s['identity']:s for s in a['states']}
    trace=row.get('solver_trace',[]);P=np.frombuffer(bytes.fromhex(a['transform_hex']),dtype='<f8').reshape(len(make_problem(item['reference']).x0),-1)
    previous=0
    for snapshot in trace:
        assert previous<=snapshot['iteration']<=200;previous=snapshot['iteration']
        state=states[snapshot['state']]
        assert np.asarray(snapshot['x'],dtype='<f8').tobytes().hex()==state['physical_hex']
        assert np.asarray(snapshot['q'],dtype='<f8').tobytes().hex()==state['canonical_hex']
    if row.get('x') is None:return dict(passed=True,initialization_rejection=True,trace_records=len(trace))
    z=np.asarray(row['normalized_depths']);_,gp,_,_=transform(z-MARGIN)
    if row.get('multipliers_depth') is not None:
        vd=np.asarray(row['multipliers_depth']);vg=np.asarray(row['multipliers_transformed'])
        np.testing.assert_allclose(vd,vg*gp,atol=1e-12,rtol=1e-10)
        np.testing.assert_allclose(row['complementarity_original'],vd*(z-MARGIN),atol=1e-12,rtol=1e-10)
        assert trace
        np.testing.assert_allclose(vg,trace[-1]['multipliers'][0],atol=1e-12,rtol=1e-10)
        np.testing.assert_allclose(row['bound_multipliers'],np.linalg.inv(P).T@trace[-1]['multipliers'][1],atol=1e-12,rtol=1e-10)
    p=make_problem(item['reference']);init=row['initialization_transfer']
    # Recompute support from the original physical parameters and declared source offset.
    def same_support(actual,expected):
        assert len(actual)==len(expected)
        for x,y in zip(actual,expected):
            assert x.keys()==y.keys()
            for k in x:
                if isinstance(x[k],(list,float,int)):
                    np.testing.assert_allclose(x[k],y[k],atol=1e-10,rtol=1e-8)
                else:assert x[k]==y[k]
    same_support(support(p,np.asarray(row['x'])),row['original_support'])
    same_support(support(p,np.asarray(init['cold_x'])),init['destination_support'])
    if row['seed']:
        endpoint=3 if 'offset' in item['reference'] else 2;old=p.offsets[endpoint];p.offsets[endpoint]=row['seed']['coordinate']
        try:same_support(support(p,np.asarray(init['original_x'])),init['source_support'])
        finally:p.offsets[endpoint]=old
    norms=[]
    for x in [trace[0]['x'] if trace else row['x'],row['x']]:
        offsets,co=p.unpack(np.asarray(x));norms.append(max(float(np.max(np.abs(p.spline((o['frames']-offsets[o['camera_id']])/25)@co[gi]))) for gi,g in enumerate(p.groups) for o in g['observations']))
    growth=norms[1]>max(1e6,100*norms[0])
    if 'offset' in item['reference']:
        entry=[e for e in events if e['event']=='diagnostic_entry'];done=[e for e in events if e['event']=='diagnostic_return']
        assert len(entry)==len(done)==1 and entry[0]['seq']<done[0]['seq']
        assert entry[0]['physical_hex']==np.asarray([item['reference']['offset'],*row['x']],dtype='<f8').tobytes().hex()
        assert row['joint_qualified'] is False and row['conditional_qualified']==row['valid']
    return dict(passed=True,trace_records=len(trace),full_multiplier_mapping_verified=True,support_recomputed=True,observable_norms=norms,observable_growth_issue=growth)


def policy_audit(folder,manifest):
    begin=time.monotonic();records=load_records(folder);verify_schedule(records,manifest)
    evidence=[];completion_seconds=[];solver_seconds=[]
    for item in records:
        proof=detailed_evidence(item);directory=Path(item['artifact']['artifact']).parent;events=journal_prefix(directory/'journal.jsonl')['events']
        boundary=max([e['unix'] for e in events if e['event'] in ['numerical_return','diagnostic_return']]+[events[0]['unix']])
        completion_seconds.append(events[-1]['unix']-boundary);solver_seconds.append(item['row'].get('wall_seconds',0.))
        evidence.append(dict(id=item['id'],artifact_sha256=item['artifact']['sha256'],**proof))
    counts=read(folder/'counts.json')
    observed=dict(scheduled=len(records),persisted_outcomes=len(records),executed=sum(r['row']['executed'] for r in records),solver_invocations=sum(r['row']['solver_invoked'] for r in records),qualified=sum(r['row']['valid'] for r in records),missing=sum(not r['row']['executed'] for r in records),numerical_entries=sum(len(r['row'].get('accounting',{}).get('observed_numerical_entries',[])) for r in records))
    for key,value in observed.items():assert counts[key]==value
    return records,dict(counts=observed,wall_seconds=counts['wall_seconds'],solver_wall_sum_including_journal_sync=sum(solver_seconds),post_numerical_completion_wall_sum=sum(completion_seconds),independent_reverification_wall_seconds=time.monotonic()-begin,evidence=evidence,observable_growth_issues=[r['id'] for r in evidence if r.get('observable_growth_issue')])


def screen_decisions(cohorts,manifest,controls):
    base={r['id']:r for r in cohorts['baseline']};frozen=read(ROOT/'baseline/denominators.json');denom={i:base[i]['verification']['KKT'] for i in iteration_ids(manifest)}
    assert denom==frozen['values'] and frozen['positive_verified']==all(v is not None and v>0 for v in denom.values())
    decisions={}
    for name in ['metric','initialization','stopping']:
        saved=read(ROOT/'adapt'/(name+'-decision.json'));rows={r['id']:r for r in cohorts[name]};keep=preservation(cohorts[name],controls);assert keep==saved['preservation']
        if name=='metric':
            targets=iteration_ids(manifest);recovered=[i for i in targets if rows[i]['row']['valid']];groups=sorted({rows[i]['reference']['group_id'] for i in recovered})
            ratios=[np.inf if rows[i]['verification']['KKT'] is None else rows[i]['verification']['KKT']/denom[i] for i in targets];median=float(np.median(ratios))
            passed=len(recovered)>=3 and groups==[2,9,11] and median<=.1 and keep['passed']
            assert saved['recovered']==recovered;np.testing.assert_allclose(median,saved['median_KKT_ratio'],atol=0,rtol=0)
            decisions[name]=dict(passed=passed,recovered=recovered,groups=groups,ratios=[v if np.isfinite(v) else None for v in ratios],median_KKT_ratio=median if np.isfinite(median) else None)
        elif name=='initialization':
            targets=sorted({t['id']+'/'+l['reference']['path'] for t in manifest['targets'] for l in t['labels'] if l['stratum']=='regularized_infeasible_cold'});assert len(targets)==3
            feasible=[];depths={}
            for ident in targets:
                item=rows[ident];init=item['row']['initialization_transfer'];p=make_problem(item['reference'])
                from basketball_shared_accounting_v10 import NumericalEntries
                raw=NumericalEntries(p);cold=np.asarray(init['cold_x']);z,_=raw.depth(cold);depths[ident]=float(min(z))
                if np.isfinite(cold).all() and np.all(np.abs(cold[:p.n_offsets])<=25) and min(z)>2e-8:feasible.append(ident)
                assert init['restoration']['minimum_target_depth']==1e-6
            passed=len(feasible)==3 and keep['passed'];assert saved['feasible']==feasible
            decisions[name]=dict(passed=passed,feasible=feasible,minimum_depths=depths,subsequently_qualified=[i for i in targets if rows[i]['row']['valid']])
        else:
            targets=sorted({t['id']+'/'+l['reference']['path'] for t in manifest['targets'] for l in t['labels'] if l['stratum']=='regularized_xtol'});assert len(targets)==3
            qualified=[i for i in targets if rows[i]['row']['valid']];passed=len(qualified)==3 and keep['passed'];assert saved['qualified']==qualified
            decisions[name]=dict(passed=passed,qualified=qualified,targets=targets)
        assert bool(passed)==saved['passed']
    final=read(ROOT/'adapt/final-policy.json');selected=[n for n in ['metric','initialization','stopping'] if decisions[n]['passed']]
    assert final['selected_arms']==selected and final['conditioned_conditional']==('metric' in selected) and final['repair']==('initialization' in selected) and final['disable_xtol']==('stopping' in selected)
    exact_hashes(final['standalone_decisions_sha256'])
    return decisions


def audit():
    p=read(CONFIG);assert time.time()<p['v10']['absolute_deadlines']['verify']
    admission=read(ROOT/'prepare/admission.json');exact_hashes(admission['committed_v9_sha256']);exact_hashes(read(ROOT/'prepare/execution-sources.json'))
    manifest=read(ROOT/'prepare/benchmark-manifest.json');controls=read(ROOT/'prepare/controls.json');assert len(controls)==47
    cohorts={};policies={}
    for name,folder in [('baseline',ROOT/'baseline/policy'),('metric',ROOT/'adapt/metric'),('initialization',ROOT/'adapt/initialization'),('stopping',ROOT/'adapt/stopping'),('final',ROOT/'benchmark/policy')]:
        if (folder/'counts.json').exists():cohorts[name],policies[name]=policy_audit(folder,manifest)
    assert sum(len(v) for v in cohorts.values())<=405 and len(cohorts)<=5
    decisions=screen_decisions(cohorts,manifest,controls)
    journals=list((ROOT/'persist').glob('**/journal.jsonl'));assert len(journals)==6
    preflight=[inspect_attempt(j.parent) for j in journals];assert sum(r['completed'] for r in preflight)==5 and sum(not r['completed'] for r in preflight)==1
    # Check each frozen wall deadline against disk events, not exported elapsed counters.
    timing={'admission':admission['frozen_unix'],'persist':read(ROOT/'persist/result.json')['finished_unix'],'baseline':read(ROOT/'baseline/result.json')['finished_unix']}
    assert timing['admission']<p['v10']['absolute_deadlines']['prepare']
    for stage in ['persist','baseline']:assert timing[stage]<p['v10']['absolute_deadlines'][stage]
    assert read(ROOT/'baseline/denominators.json')['frozen_unix']<min(journal_prefix(j)['events'][0]['unix'] for j in (ROOT/'adapt/metric').glob('**/journal.jsonl'))
    for name in ['metric','initialization','stopping']:
        timing[name]=max(journal_prefix(j)['events'][-1]['unix'] for j in (ROOT/'adapt'/name).glob('**/journal.jsonl'))
        assert timing[name]<p['v10']['absolute_deadlines'][name]
    final_policy=read(ROOT/'adapt/final-policy.json');assert final_policy['frozen_unix']<p['v10']['absolute_deadlines']['adapt']
    ready=False;final_decision=dict(status='unassessed')
    if 'final' in cohorts:
        final=cohorts['final'];byid={r['id']:r for r in final};keep=preservation(final,controls);disagreements=[]
        for t in manifest['targets']:
            costs=[byid[t['id']+'/'+path]['row'].get('objective') for path in ['cold','ascending','descending']]
            if any(c is None for c in costs) or not all(objective_agreement(costs[0],c) for c in costs[1:]):disagreements.append(t['id'])
        ready=all(r['row']['valid'] for r in final) and keep['passed'] and not disagreements and not policies['final']['observable_growth_issues']
        saved=read(ROOT/'benchmark/decision.json');assert saved['ready_for_full_screens']==ready and saved['path_disagreements']==disagreements
        assert final_policy['frozen_unix']<min(journal_prefix(j)['events'][0]['unix'] for j in (ROOT/'benchmark/policy').glob('**/journal.jsonl'))
        timing['benchmark']=read(ROOT/'benchmark/result.json')['finished_unix'];assert timing['benchmark']<p['v10']['absolute_deadlines']['benchmark']
        final_decision=dict(status='ready_for_full_screens' if ready else 'scientific_rejection',passed=ready,preservation=keep,path_disagreements=disagreements,failed=[r['id'] for r in final if not r['row']['valid']])
    terminal=read(ROOT/'package/terminal-decision.json');assert terminal['ready_for_full_screens']==ready
    verification=read(ROOT/'verify/result.json');assert verification['status']=='passed' and verification['ready_for_full_screens']==ready
    result=dict(status='passed',scientific_status=final_decision['status'],ready_for_full_screens=ready,policies=policies,standalone_decisions=decisions,final_decision=final_decision,preflight=preflight,
        scientific_scheduled=sum(len(v) for v in cohorts.values()),scientific_solver_invocations=sum(v['counts']['solver_invocations'] for v in policies.values()),scientific_qualifications=sum(v['counts']['qualified'] for v in policies.values()),scientific_numerical_entries=sum(v['counts']['numerical_entries'] for v in policies.values()),
        deadline_evidence_unix=timing,started_unix=p['investigation_started_unix'],finished_unix=time.time(),elapsed_seconds=time.time()-p['investigation_started_unix'],required_tests=verification['tests'],accepted_timing=None,production_candidate=None,final_validation_protocol=None,full_screens_launched=False,
        source_sha256={__file__:sha(__file__),str(CONFIG):sha(CONFIG)},terminal_sha256=sha(ROOT/'package/terminal-decision.json'),verification_sha256=sha(ROOT/'verify/result.json'))
    assert result['finished_unix']<p['v10']['absolute_deadlines']['verify']
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,default=ROOT/'independent-report.json');args=parser.parse_args()
    try:result=audit()
    except Exception as error:
        import traceback
        result=dict(status='blocked',scientific_status='verification_failure',ready_for_full_screens=False,error=type(error).__name__+': '+str(error),traceback=traceback.format_exc(),finished_unix=time.time())
    publish(args.output,result);print(result['status'],result.get('scientific_status'));raise SystemExit(result['status']!='passed')
