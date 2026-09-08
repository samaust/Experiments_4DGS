"""Fresh isolated baseline, standalone arms and one conditional final benchmark."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='1'
import json
import subprocess
import sys
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import numpy as np
from basketball_scale import read,write
from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes
from basketball_shared_diagnose_v5 import compressed_read
from basketball_shared_serialization_v9 import compressed_write
from basketball_shared_diagnose_v9 import make_problem
from basketball_shared_solver_v9 import solve
from basketball_shared_solver_v4 import ConstrainedProblem
from basketball_shared_solver_v3 import objective_agreement
from basketball_shared_verify_v9 import verify_row

PATHS=['cold','ascending','descending']


def event(file,data):
    with file.open('a') as f:
        f.write(json.dumps(data,sort_keys=True)+'\n');f.flush()


def event_accounting(path):
    """Interrupted/truncated streams never manufacture exact executed totals."""
    if not path.exists():return dict(allocated=0,entered=None,completed=0,interrupted=None,exact=False,reason='no worker event artifact')
    records=[];truncated=False
    for line in path.read_text().splitlines():
        try:records.append(json.loads(line))
        except json.JSONDecodeError:truncated=True
    allocated=[r['id'] for r in records if r.get('event')=='allocated'];entered=[r['id'] for r in records if r.get('event')=='entered'];finished=[r['id'] for r in records if r.get('event')=='completed']
    uncertain=truncated or set(entered)-set(finished)
    return dict(allocated=len(allocated),entered=None if uncertain else len(entered),entered_lower_bound=len(entered),completed=len(finished),
        interrupted=None if truncated else len(set(entered)-set(finished)),exact=not bool(uncertain),truncated=truncated)


def nearest(cold,offset,side=None):
    eligible=[(x,item) for x,item in cold.items() if item['row']['valid'] and (side is None or (x<offset if side=='lower' else x>offset))]
    return min(eligible,key=lambda v:(abs(v[0]-offset),v[0])) if eligible else None


def jobs(manifest):
    groups={}
    for t in manifest['targets']:
        k=(t['group_id'],t['weight'],t['lag']);groups.setdefault(k,dict(targets=[],dependencies=[]))['targets'].append(t)
    for i,t in enumerate(manifest['dependencies']):
        k=(t['group_id'],t['weight'],t['lag']);groups.setdefault(k,dict(targets=[],dependencies=[]))['dependencies'].append(dict(t,id=f'conditional-source-{i:02d}'))
    result=[]
    for i,(key,data) in enumerate(sorted(groups.items())):result.append(dict(id=f'conditional-job-{i:02d}',kind='conditional',**data))
    joint={}
    for i,t in enumerate(manifest['joint_targets']):joint.setdefault((t['group_id'],t['weight']),dict(targets=[],dependencies=[]))['targets'].append(dict(t,id=f'joint-{i:02d}'))
    for i,t in enumerate(manifest['joint_dependencies']):joint.setdefault((t['group_id'],t['weight']),dict(targets=[],dependencies=[]))['dependencies'].append(dict(t,id=f'joint-source-{i:02d}'))
    for i,(key,data) in enumerate(sorted(joint.items())):result.append(dict(id=f'joint-job-{i:02d}',kind='joint',**data))
    return result


def worker(config,policy_file,task_file,output,absolute_deadline):
    p=read(config);policy=read(policy_file);task=read(task_file);records=[];events=output.with_suffix('.events.jsonl')
    def check():
        if time.time()>=absolute_deadline:raise TimeoutError('frozen local policy deadline')
    def fit(ref,path,seed=None):
        check();ident=ref['id']+'/'+path
        event(events,dict(event='allocated',id=ident,policy=policy['name']))
        reference={k:ref[k] for k in ['group_id','weight','lag','offset'] if k in ref}
        if path!='cold' and seed is None:
            row=dict(valid=False,converged=False,executed=False,objective=None,error='missing required fresh qualifying source',policy=policy['name'],seed=None)
            item=dict(id=ident,reference=reference,row=row,verification=verify_row(reference,row));records.append(item)
            event(events,dict(event='completed',id=ident,executed=False,qualified=False));return item
        provenance=dict(policy_sha256=sha256(policy_file),manifest_sha256=policy['manifest_sha256'],task=task['id'],path=path,seed=None if seed is None else dict(id=seed[1]['id'],coordinate=seed[0],policy=seed[1]['row']['policy'],state=seed[1]['row']['returned_state']))
        if seed is not None and seed[1]['row']['policy']!=policy['name']:raise ArithmeticError('cross-policy seed')
        problem=make_problem(reference,check);event(events,dict(event='entered',id=ident,policy=policy['name']))
        row=solve(problem,None if seed is None else seed[1]['row']['x'],None if seed is None else seed[0],3 if task['kind']=='conditional' else 2,
            conditioned=policy['conditioned_conditional'] if task['kind']=='conditional' else True,repair=policy['repair'],disable_xtol=policy['disable_xtol'],namespace='v9-'+policy['name']+'/'+task['id']+'/'+ident,provenance=provenance)
        row.update(executed=True,policy=policy['name'],seed=provenance['seed'],seed_initial_x=None if seed is None else seed[1]['row']['x'])
        if 'offset' in reference and row.get('x') is not None:
            joint=make_problem({k:v for k,v in reference.items() if k!='offset'},check);a=ConstrainedProblem(joint);x=np.r_[reference['offset'],row['x']];r,J=a.evaluate(x/a.scale);z,D=a.depth(x/a.scale)
            row['omitted_camera_offset_objective_derivative_per_frame']=float((2*J.T@r)[0]/25)
            vd=row.get('multipliers_depth');row['omitted_camera_offset_lagrangian_derivative_per_frame']=None if vd is None else float((2*J.T@r+D.T@vd)[0]/25)
            row['omitted_derivative_role']='read-only same-physical-state joint diagnostic, outside coefficient solver; never qualifies joint state'
        verification=verify_row(reference,row)
        item=dict(id=ident,reference=reference,row=row,verification=verification);records.append(item)
        event(events,dict(event='completed',id=ident,executed=True,qualified=row['valid'],states=row['nfev'],iterations=row['iterations']))
        return item
    cold={}
    if task['kind']=='conditional':
        for ref in sorted(task['dependencies']+task['targets'],key=lambda t:(t['offset'],t['id'])):cold[ref['offset']]=fit(ref,'cold')
        for path,reverse,side in [('ascending',False,'lower'),('descending',True,'upper')]:
            previous=None;directional={}
            for ref in sorted(task['targets'],key=lambda t:t['offset'],reverse=reverse):
                offset=ref['offset']
                if float(offset).is_integer():seed=previous if previous is not None else nearest(cold,offset)
                else:
                    # Local analogue of refinement: declared source cold plus established same-direction target states.
                    candidates={**cold,**directional};seed=nearest(candidates,offset,side)
                item=fit(ref,path,seed);directional[offset]=item
                if item['row']['valid']:previous=(offset,item)
    else:
        for ref in sorted(task['dependencies'],key=lambda t:t['lag']):cold[ref['lag']]=fit(ref,'cold')
        for ref in task['targets']:
            path=ref['path'];seed=None if path=='cold' else nearest(cold,ref['seed_lag'])
            # A required joint source cannot be silently replaced by a different coordinate.
            if seed is not None and seed[0]!=ref['seed_lag']:seed=None
            fit(ref,path,seed)
    compressed_write(output,dict(policy=policy,task=task,records=records,event_accounting=event_accounting(events),completed=True))


def run_policy(p,output,policy,manifest,stage):
    from basketball_shared_workflow_v9 import deadline,check,terminate_group
    check(p,stage);output.mkdir();policy=dict(policy,manifest_sha256=sha256(policy['manifest']))
    write(output/'policy.json',policy);tasks=jobs(manifest);taskrows=[]
    for task in tasks:
        file=output/(task['id']+'.json');write(file,task)
        taskrows.append(dict(task=task,task_file=str(file),artifact=str(output/(task['id']+'-attempts.json.gz'))))
    write(output/'scheduled.json',dict(attempts=manifest['scheduled_per_policy'],tasks=taskrows,policy_sha256=sha256(output/'policy.json')))
    def launch(t):
        check(p,stage)
        args=[sys.executable,__file__,'worker','configs/basketball-rev2/timing-shared-v9.json',str(output/'policy.json'),t['task_file'],t['artifact'],str(deadline(p,stage))]
        child=subprocess.Popen(args) # Inherits stage process group so its external watchdog owns descendants.
        code=child.wait();return dict(task=t['task']['id'],exit_code=code,artifact=t['artifact'])
    with ThreadPoolExecutor(max_workers=6) as pool:outcomes=list(pool.map(launch,taskrows))
    write(output/'worker-outcomes.json',dict(records=outcomes))
    if any(r['exit_code']!=0 for r in outcomes):raise ArithmeticError('policy worker failed; no retry; inspect retained events')
    records=[]
    for t in taskrows:records.extend(compressed_read(t['artifact'])['records'])
    assert len(records)==manifest['scheduled_per_policy']<=104
    byid={r['id']:r for r in records};assert len(byid)==len(records)
    # Independent provenance check: every seed was freshly returned by this policy.
    for item in records:
        seed=item['row'].get('seed')
        if seed:
            source=byid[seed['id']];assert source['row']['valid'] and source['row']['policy']==policy['name']
            np.testing.assert_array_equal(item['row']['seed_initial_x'],source['row']['x'])
            assert item['reference']['group_id']==source['reference']['group_id'] and item['reference']['weight']==source['reference']['weight']
            if 'offset' in item['reference']:assert item['reference']['lag']==source['reference']['lag']
    count=dict(scheduled=len(records),executed=sum(r['row'].get('executed',True) for r in records),missing=sum(not r['row'].get('executed',True) for r in records),qualified=sum(r['row']['valid'] for r in records))
    write(output/'counts.json',count)
    return records,count


def diagnostic_controls(root):
    decision=read(root/'diagnostic-decision.json');controls={}
    for a in decision['artifacts']:
        for r in compressed_read(a['path'])['records']:
            ref=r['reference'];ident=ref['target_id']+'/'+ref['path']
            if r['archived_qualified']:
                controls[ident]=dict(objective=r['states'][-1]['objective'],reference=ref)
    return controls


def preservation(records,controls):
    byid={r['id']:r for r in records};bad=[]
    for ident,old in controls.items():
        row=byid[ident]['row'];cost=row.get('objective')
        if not row['valid'] or cost is None or not (cost<=old['objective'] or objective_agreement(cost,old['objective'])):bad.append(ident)
    return dict(passed=not bad,required=len(controls),failed=bad)


def iteration_ids(manifest):
    return sorted({t['id']+'/'+label['reference']['path'] for t in manifest['targets'] for label in t['labels'] if label['stratum'] in ['cold_iteration','directional_iteration','support_changing_iteration']})


def arm_decision(policy,records,manifest,controls,baseline,denominators):
    byid={r['id']:r for r in records};keep=preservation(records,controls);decision=dict(policy=policy['name'],preservation=keep,status='rejected',passed=False)
    if policy['name']=='metric':
        targets=iteration_ids(manifest);recovered=[i for i in targets if byid[i]['row']['valid']];groups=sorted({byid[i]['reference']['group_id'] for i in recovered})
        ratios=[np.inf if byid[i]['verification']['KKT'] is None else byid[i]['verification']['KKT']/denominators[i] for i in targets]
        median=float(np.median(ratios));passed=keep['passed'] and len(recovered)>=len(targets)/2 and groups==[2,9,11] and median<=.1
        decision.update(targets=targets,recovered=recovered,recovery_groups=groups,median_KKT_ratio=median if np.isfinite(median) else None,median_infinite=not np.isfinite(median),passed=passed)
    elif policy['name']=='initialization':
        targets=sorted({t['id']+'/'+l['reference']['path'] for t in manifest['targets'] for l in t['labels'] if l['stratum']=='regularized_infeasible_cold'})
        feasible=[i for i in targets if byid[i]['row'].get('initialization_transfer',{}).get('cold_valid')]
        decision.update(targets=targets,feasible=feasible,subsequently_qualified=[i for i in targets if byid[i]['row']['valid']],passed=len(feasible)==len(targets) and keep['passed'])
    elif policy['name']=='stopping':
        targets=sorted({t['id']+'/'+l['reference']['path'] for t in manifest['targets'] for l in t['labels'] if l['stratum']=='regularized_xtol'})
        decision.update(targets=targets,qualified=[i for i in targets if byid[i]['row']['valid']],passed=all(byid[i]['row']['valid'] for i in targets) and keep['passed'])
    # All arms additionally retain explicit support/observable checks at first and returned states.
    issues=[]
    for item in records:
        row=item['row'];trace=row.get('solver_trace',[])
        if row.get('x') is None or not trace:continue
        p=make_problem(item['reference']);norms=[]
        for x in [trace[0]['x'],row['x']]:
            offsets,co=p.unpack(np.asarray(x));norms.append(max(float(np.max(np.abs(p.spline((o['frames']-offsets[o['camera_id']])/25)@co[gi]))) for gi,g in enumerate(p.groups) for o in g['observations']))
        if norms[1]>max(1e6,100*norms[0]):issues.append(item['id'])
    decision['observable_growth_issues']=issues;decision['passed']=decision['passed'] and not issues
    decision['status']='passed' if decision['passed'] else 'rejected'
    return decision


def adapt(p,output,predecessor):
    from basketball_shared_workflow_v9 import check
    frozen=read(predecessor/'candidate-freeze.json');verify_hashes(frozen['implementation_sha256']);manifest=read(frozen['manifest']);controls=diagnostic_controls(predecessor)
    baseline_policy=dict(frozen['policies'][0],manifest=frozen['manifest'])
    baseline,counts=run_policy(p,output/'baseline',baseline_policy,manifest,'adapt');byid={r['id']:r for r in baseline}
    denom={i:byid[i]['verification']['KKT'] for i in iteration_ids(manifest)}
    ready=all(v is not None and np.isfinite(v) and v>0 for v in denom.values())
    write(output/'baseline-denominators.json',dict(frozen_unix=time.time(),positive_verified=ready,values=denom,baseline_counts=counts))
    decisions=[]
    for arm in frozen['policies'][1:]:
        check(p,'adapt')
        if arm['name']=='metric' and not ready:
            decisions.append(dict(policy='metric',status='unassessed',passed=False,reason='missing positive independently verified fresh baseline KKT denominator'));continue
        records,count=run_policy(p,output/arm['name'],dict(arm,manifest=frozen['manifest']),manifest,'adapt')
        decision=arm_decision(arm,records,manifest,controls,baseline,denom);decision['counts']=count;decisions.append(decision)
        write(output/(arm['name']+'-decision.json'),decision)
    selected=[d['policy'] for d in decisions if d['passed']]
    final=dict(name='final',conditioned_conditional='metric' in selected,repair='initialization' in selected,disable_xtol='stopping' in selected,manifest=frozen['manifest'],selected_arms=selected,
               frozen_unix=time.time(),standalone_decisions=decisions)
    write(output/'final-policy-freeze.json',final)
    write(output/'adapt-decision.json',dict(status='passed' if selected else 'rejected',baseline=counts,decisions=decisions,selected_arms=selected,final_benchmark='authorized' if selected else 'unassessed',no_retuning=True))
    return dict(status='passed' if selected else 'blocked',terminal_kind=None if selected else 'scientific_rejection',blockers=[] if selected else ['no standalone adaptation passed its frozen screen'])


def benchmark(p,output,predecessor):
    policy=read(predecessor/'final-policy-freeze.json');assert policy['selected_arms']
    manifest=read(policy['manifest']);records,counts=run_policy(p,output/'final',policy,manifest,'benchmark');byid={r['id']:r for r in records}
    frozen=read(predecessor/'frozen.json');diagnose_root=next(Path(f).parent for f in frozen['source_sha256'] if f.endswith('/diagnose/result.json'))
    controls=diagnostic_controls(diagnose_root);keep=preservation(records,controls);disagreements=[]
    for t in manifest['targets']:
        rows=[byid[t['id']+'/'+path]['row'] for path in PATHS];costs=[r.get('objective') for r in rows]
        if any(v is None for v in costs) or not all(objective_agreement(costs[0],v) for v in costs[1:]):disagreements.append(t['id'])
    passed=counts['qualified']==counts['scheduled'] and not counts['missing'] and keep['passed'] and not disagreements
    decision=dict(passed=passed,status='ready_for_full_screens' if passed else 'scientific_rejection',counts=counts,preservation=keep,path_disagreements=disagreements,
        failed_attempts=[i for i,r in byid.items() if not r['row']['valid']],all_physical_and_entry_checks=True,selected_policy_sha256=sha256(output/'final/policy.json'),
        full_screens_launched=False,accepted_timing=None,production_candidate=None,final_validation_protocol=None)
    write(output/'benchmark-decision.json',decision)
    if passed:
        wall=sum(r['row'].get('wall_seconds',0) for r in records);estimate=2*wall/max(1,counts['executed'])*(144+12126+144)/6
        write(output/'continuation-manifest.json',dict(candidate_sha256=decision['selected_policy_sha256'],estimated_compute_seconds_with_factor_two=estimate,
            uncertainty='18-point focused benchmark cannot bound full refinement workload',separately_frozen_absolute_clock_required=True,full_screens_authorized=False,
            required_gates=['144 conditioning attempts preserve all 94; recover >=25/50; median KKT ratio <=0.1','independent scalar grid 7344 initial paths plus unchanged inclusive refinements; every path and nine basin references pass','fresh combined pilot only after both independent passes'],
            packaging_and_refinement_allowances='must be frozen before any launch; no launch in this phase'))
    return dict(status='passed' if passed else 'blocked',terminal_kind=None if passed else 'scientific_rejection',blockers=[] if passed else ['focused all-attempts benchmark gate failed'])

if __name__=='__main__':
    assert sys.argv[1]=='worker'
    worker(Path(sys.argv[2]),Path(sys.argv[3]),Path(sys.argv[4]),Path(sys.argv[5]),float(sys.argv[6]))
