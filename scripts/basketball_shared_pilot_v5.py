"""Single fixed 48-problem pilot. No pilot state may seed qualification."""
import multiprocessing
import resource
import time
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path
import numpy as np
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_continuation_audit import verify_hashes
from basketball_shared_profiles_v5 import group_job
from basketball_shared_solver_v3 import objective_agreement
from basketball_shared_solver_v4 import ConstrainedProblem as RawProblem
from basketball_shared_solver_v5 import ConstrainedProblem
from basketball_shared_diagnose_v4 import state_record
from basketball_shared_diagnose_v5 import ROOT,GROUPS,LAGS,compressed_read,compressed_write,fixture,check_deadline
from basketball_shared_synthetic_v2 import synthetic


def pilot_job(payload):
    start=time.monotonic();state=group_job(payload)
    group,cameras,edge,window,spacing,weight,role,grid,_,deadline=payload
    def check():
        if time.time()>=deadline:raise TimeoutError('30-minute pilot evidence deadline')
    for lag,attempts in state['attempts'].items():
        for row in attempts:
            if 'x' not in row:continue
            p=fixture(group['group_id'],lag,weight,check);raw=RawProblem(p);new=ConstrainedProblem(p)
            x=np.asarray(row['x']);q=x/new.scale
            row['v4_v5_same_state_objective_equal']=objective_agreement(raw.fun(q),new.fun(q))
            trace=row['solver_trace'];indices=sorted(set([0,len(trace)//2,len(trace)-1])) if trace else []
            row['observable_states']=[dict(iteration=trace[i]['iteration'],**state_record(p,np.asarray(trace[i]['x']),False)) for i in indices]
            row['initial_observable_state']=state_record(p,np.asarray(row['initial_x']),False)
            row['evidence_seconds']=time.monotonic()-start-row['wall_seconds']
            row['maximum_rss_kib']=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # Each attempt is serialized once, with direction references reconstructed by consumers.
    return dict(group_id=state['group_id'],weight=weight,problem_key=state['problem_key'],attempts=state['attempts'],
        wall_seconds=time.monotonic()-start,maximum_rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)


def pilot(p,output,predecessor):
    manifest=read(predecessor/'pilot-manifest.json');verify_hashes(manifest['source_sha256'])
    assert read(predecessor/'escape-decision.json')['resolved']
    assert manifest['groups']==GROUPS and manifest['lags']==LAGS and manifest['scheduled_attempts']==144
    groups,cameras,truth,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    deadline=p['investigation_started_unix']+1800
    jobs=[(groups[gid],cameras,dict(a=1,b=2),window,10,weight,'pilot',LAGS,None,deadline)
          for weight in [1.,0.] for gid in GROUPS]
    write(output/'pilot-freeze.json',dict(manifest_path=str(predecessor/'pilot-manifest.json'),
        manifest_sha256=sha256(predecessor/'pilot-manifest.json'),fresh_qualification_required=True))
    states=[];artifacts=[]
    with ProcessPoolExecutor(max_workers=6,mp_context=multiprocessing.get_context('spawn')) as pool:
        for state in pool.map(pilot_job,jobs):
            check_deadline(p);states.append(state)
            artifacts.append(compressed_write(output/f'weight{state["weight"]}-group{state["group_id"]:02d}.json.gz',state))
    failures=[];comparisons=[];transfers=[];growth=[]
    for state in states:
        label='regularized' if state['weight'] else 'data_only'
        old=compressed_read(ROOT/f'{label}-group{state["group_id"]:02d}.json.gz')
        for lag,rows in state['attempts'].items():
            assert [r['start'] for r in rows]==['cold','ascending','descending']
            for r in rows:
                if not r['valid'] or not r.get('v4_v5_same_state_objective_equal',False):
                    failures.append(dict(group_id=state['group_id'],weight=state['weight'],lag=lag,start=r['start'],
                        message=r.get('message',r.get('error')),nfev=r.get('nfev'),optimality=r.get('optimality')))
                if r.get('observable_states'):
                    first=r['initial_observable_state'];last=r['observable_states'][-1]
                    initial=max(abs(v) for o in first['observations'] for xyz in o['normalized_xyz'] for v in xyz)
                    returned=max(abs(v) for o in last['observations'] for xyz in o['normalized_xyz'] for v in xyz)
                    # Growth beyond the audited uniform/individual block rays is never silently qualified.
                    if returned>max(1e6,100*initial):growth.append(dict(group_id=state['group_id'],lag=lag,start=r['start'],max_xyz=returned))
            values=[r['objective'] for r in rows if r.get('objective') is not None]
            agreement=len(values)==3 and all(objective_agreement(values[0],v) for v in values)
            refs=[r['objective'] for r in old['attempts'].get(str(float(lag)),[]) if r['valid']]
            best=min(values) if values else None;ref=min(refs) if refs else None
            no_worse=ref is None or (best is not None and (best<=ref or objective_agreement(best,ref)))
            comparisons.append(dict(group_id=state['group_id'],weight=state['weight'],lag=lag,three_start_agreement=agreement,
                v5_best=best,v4_qualified_reference=ref,v4_baseline_available=lag!=-.1,no_worse=no_worse,
                improvement=ref is not None and best is not None and best<ref and not objective_agreement(best,ref)))
        destination=-19. if state['group_id']==2 else -7.;source=-20. if state['group_id']==2 else -6.
        direction='ascending' if state['group_id']==2 else 'descending'
        row=next(r for r in state['attempts'][destination] if r['start']==direction)
        transfers.append(dict(group_id=state['group_id'],weight=state['weight'],source=source,destination=destination,
            direction=direction,verified=row['valid'] and row['seed_lag']==source))
    blockers=[]
    if failures:blockers.append(f'{len(failures)}/144 scheduled attempts did not qualify')
    if any(not c['three_start_agreement'] or not c['no_worse'] for c in comparisons):blockers.append('pilot objective agreement/reference gate failed')
    if not all(t['verified'] for t in transfers):blockers.append('required directional transfer missing')
    if growth:blockers.append('unexplained observable growth in pilot traces')
    check_deadline(p);verify_hashes(manifest['source_sha256'])
    write(output/'pilot-decision.json',dict(passed=not blockers,attempts=144,problems=48,failures=failures,
        comparisons=comparisons,required_transfers=transfers,unexplained_growth=growth,artifacts=artifacts,
        elapsed_seconds=time.time()-p['investigation_started_unix'],timing_qualification=False))
    return dict(status='blocked' if blockers else 'passed',terminal_kind='numerical_failure' if blockers else None,
        blockers=blockers,pilot_attempted=144,pilot_qualified=144-len(failures),full_exact_retest=None)
