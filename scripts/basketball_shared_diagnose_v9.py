"""Frozen saved-state diagnosis; no optimization or reuse of fitted states as starts."""
from pathlib import Path
from collections import defaultdict
import json
import time
import numpy as np
from basketball_audit import sha256
from basketball_scale import read,write
from basketball_shared_diagnose_v5 import compressed_read,compressed_write
from basketball_shared_accounting_v9 import CanonicalAdapter,reconcile,bytes_of
from basketball_shared_curvature_v6 import deterministic_svd,canonical
from basketball_shared_initialization_v9 import sampled_support
from basketball_shared_solver_v6 import transform,MARGIN
from basketball_shared_spline_v2 import SplineProblem
from basketball_shared_synthetic_v2 import synthetic


def make_problem(ref,check=lambda:None):
    groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    conditional='offset' in ref
    return SplineProblem([groups[ref['group_id']]],cameras,{1:0.,2:ref['lag'],3:ref.get('offset',0.)},window,10,ref['weight'],(1,2,3) if conditional else (1,2),check)


def saved_references(manifest):
    refs=[]
    for t in manifest['targets']:
        for r in t['references']:refs.append(dict(**r,target_id=t['id'],kind='conditional_target'))
    for i,r in enumerate(manifest['dependencies']):
        f=Path('docs/experiments/basketball-shared-timing-v8/basins')/f'weight{r["weight"]}-group{r["group_id"]:02d}-lag{r["lag"]:g}.json.gz'
        refs.append(dict(**r,path='cold',source=str(f),source_sha256=sha256(f),target_id=f'conditional-source-{i:02d}',kind='conditional_dependency'))
    for i,r in enumerate(manifest['joint_targets']):refs.append(dict(**r,target_id=f'joint-{i:02d}',kind='joint_target'))
    for i,r in enumerate(manifest['joint_dependencies']):
        f=Path('docs/experiments/basketball-shared-timing-v8/condition')/f'weight{r["weight"]}-group{r["group_id"]:02d}.json.gz'
        refs.append(dict(**r,path='cold',source=str(f),source_sha256=sha256(f),target_id=f'joint-source-{i:02d}',kind='joint_dependency'))
    return refs


def get_row(data,ref):
    if 'offset' in ref:
        curve=data['curves'][ref['path']]
        return next(r for x,r in curve.items() if float(x)==ref['offset'])
    return next(r for r in data['attempts'][str(float(ref['lag']))] if r['start']==ref['path'])


def analyze(ref,row,check):
    p=make_problem(ref,check);a=CanonicalAdapter(p,'v9-saved-diagnostic',dict(source=ref['source_sha256'],target=ref['target_id'],path=ref['path']))
    trace=row.get('solver_trace',[]);snapshots=[]
    if trace:
        snapshots=[('first',trace[0]),('middle',trace[len(trace)//2])]
    if row.get('x') is not None:snapshots.append(('returned',row))
    if not snapshots:
        snapshots=[('destination_cold',dict(x=p.x0.tolist()))]
    records=[]
    for label,state in snapshots:
        check();s=a.state_x(state['x'],'saved_'+label);r,J=a.residual(s);J=J.toarray();z,D=a.raw(s)
        G=2*J.T@r;singular,V,tol,sub=deterministic_svd(J);sd,Vd,td,subd=deterministic_svd(J[:2*p.n])
        g,gp,_,flags=transform(z-MARGIN);mu=None
        if trace:mu=trace[-1 if label=='returned' else 0 if label=='first' else len(trace)//2]['barrier_parameter']
        Cd=Cb=KKT=comp=None
        if label=='returned' and row.get('multipliers_depth') is not None:
            Cd=np.asarray(D.T@row['multipliers_depth']).ravel();Cb=np.asarray(row['bound_multipliers']);KKT=G+Cd+Cb
            comp=(np.asarray(row['multipliers_depth'])*(z-MARGIN)).tolist()
            np.testing.assert_allclose(np.linalg.norm(KKT,np.inf),row['optimality'],atol=1e-10,rtol=1e-8)
        if label=='returned':
            np.testing.assert_allclose(r@r,row['objective'],atol=1e-10,rtol=1e-9)
            np.testing.assert_allclose(z,row['normalized_depths'],atol=1e-12,rtol=1e-12)
        support=sampled_support(a,s.x,'saved_support',state=s)
        offsets,co=p.unpack(s.x);xyz=np.vstack([p.spline((np.asarray(o['frames'])-offsets[o['camera_id']])/25)@co[gi] for gi,gr in enumerate(p.groups) for o in gr['observations']])
        raw_dirs=[(f'weak_{i}',V[i]) for i in range(len(V)-1,max(-1,len(V)-5),-1)]
        if np.linalg.norm(G):raw_dirs.append(('gradient',G/np.linalg.norm(G)))
        if len(trace)>1:
            delta=(np.asarray(trace[-1]['x'])-np.asarray(trace[-2]['x']))/a.scale
            if np.linalg.norm(delta):raw_dirs.append(('last_saved_step',delta/np.linalg.norm(delta)))
        H=a.hessian(s);directions=[];seen=set()
        for name,v in raw_dirs:
            v=canonical(v);b=bytes_of(v)
            if b in seen:continue
            seen.add(b);directions.append(dict(label=name,vector=v.tolist(),exact_hessian_action=(H@v).tolist(),gradient_projection=float(G@v),
                residual_motion_norm=float(np.linalg.norm(J[:2*p.n]@v)),exactly_residual_null=bool(np.all(J[:2*p.n]@v==0))))
        Bdepth=None if mu is None or np.any(g<=0) else np.asarray(-mu*D.T@(gp/g)).ravel().tolist()
        Bbounds=None
        if mu is not None and np.all(np.abs(s.q[:p.n_offsets])<1):
            b=np.zeros_like(s.q);free=s.q[:p.n_offsets];b[:p.n_offsets]=mu*(1/(1-free)-1/(1+free));Bbounds=b.tolist()
        records.append(dict(label=label,x=s.x.tolist(),canonical_q=s.q.tolist(),objective=float(r@r),residual=r.tolist(),singular_values=singular.tolist(),rank=int(np.sum(singular>tol)),rank_threshold=tol,subspaces=sub,
            data_singular_values=sd.tolist(),data_rank=int(np.sum(sd>td)),data_rank_threshold=td,data_subspaces=subd,column_norms=np.linalg.norm(J,axis=0).tolist(),support=support,
            G=G.tolist(),G_inf=float(np.linalg.norm(G,np.inf)),C_depth=None if Cd is None else Cd.tolist(),C_bounds=None if Cb is None else Cb.tolist(),KKT=None if KKT is None else KKT.tolist(),KKT_inf=None if KKT is None else float(np.linalg.norm(KKT,np.inf)),
            multiplier_KKT_available=KKT is not None,unavailable_reason=None if KKT is not None else 'historical callback/failed return did not serialize multipliers',
            complementarity_original=comp,B_depth=Bdepth,B_bounds=Bbounds,barrier_parameter=mu,trust_radius=state.get('trust_radius',trace[-1]['trust_radius'] if trace else None),depths=z.tolist(),
            minimum_depth=float(np.min(z)),maximum_coefficient=float(np.max(np.abs(co))),observable_xyz=xyz.tolist(),maximum_observable=float(np.max(np.abs(xyz))),directions=directions,transformation_flags=flags))
    summary=dict(reference=ref,archived_qualified=row.get('valid',False),archived_status=row.get('status'),archived_message=row.get('message',row.get('error')),
        archived_seed_offset=row.get('seed_offset'),archived_seed_start=row.get('seed_start'),archived_initialization=row.get('initialization_transfer'),states=records,
        trust_contractions=sum(b['trust_radius']<a['trust_radius'] for a,b in zip(trace,trace[1:])),repeated_callback_states=sum(a['x']==b['x'] for a,b in zip(trace,trace[1:])),iterations=len(trace),
        missing_seed=not row.get('executed',True),accounting=reconcile(a.export()))
    return summary


def diagnose(p,output,predecessor):
    from basketball_shared_workflow_v9 import check
    # The admitted manifest lives in the account stage's frozen predecessor chain.
    frozen=read(predecessor/'frozen.json');manifest_path=next(Path(f).parent/'benchmark-manifest.json' for f in frozen['source_sha256'] if f.endswith('/prepare-resumed/result.json') or f.endswith('/prepare/result.json'))
    manifest=read(manifest_path);refs=saved_references(manifest);byfile=defaultdict(list)
    for ref in refs:byfile[ref['source']].append(ref)
    records=[];artifacts=[]
    for i,(file,items) in enumerate(sorted(byfile.items())):
        check(p,'diagnose');data=compressed_read(file);local=[]
        for ref in items:
            assert sha256(file)==ref['source_sha256']
            local.append(analyze(ref,get_row(data,ref),lambda:check(p,'diagnose')))
        target=output/f'saved-states-{i:02d}.json.gz';compressed_write(target,dict(records=local))
        artifacts.append(dict(path=str(target),sha256=sha256(target)))
        records.extend(local)
    infeasible=[r for r in records if r['reference']['kind']=='conditional_target' and r['archived_message']=='no feasible deterministic initialization']
    xtol=[r for r in records if r['reference']['kind']=='conditional_target' and r['archived_status']==2]
    missing=[r for r in records if r['missing_seed']]
    iterations=[r for r in records if r['reference']['kind']=='conditional_target' and r['iterations']==200 and not r['archived_qualified']]
    assert len(xtol)==3
    summary=dict(passed=True,references=len(records),artifacts=artifacts,manifest=str(manifest_path),manifest_sha256=sha256(manifest_path),
        infeasible_cold=[dict(reference=r['reference'],minimum_depth=r['states'][0]['minimum_depth'],reason='destination triangulation/spline cold state crosses positive-depth feasibility margin') for r in infeasible],
        xtol=[dict(reference=r['reference'],KKT=r['states'][-1]['KKT_inf'],trust_radius=r['states'][-1]['trust_radius'],contractions=r['trust_contractions']) for r in xtol],
        iteration_limit_targets=[dict(reference=r['reference'],KKT=r['states'][-1]['KKT_inf'],rank=r['states'][-1]['rank'],columns=len(r['states'][-1]['singular_values']),contractions=r['trust_contractions']) for r in iterations],
        missing_seeds=[dict(reference=r['reference'],reason='no qualifying source in archived directional schedule; see declared fresh source dependencies') for r in missing],
        interpretation='Weak/full-rank scaling, support activation and trust contraction coexist. No causal proof or coefficient deletion; test one fixed full-coordinate metric, one analytical feasible initialization, and removal of premature xtol stopping separately.',
        intermediate_multiplier_KKT_inferred=False,scientific_solves=0)
    write(output/'diagnostic-decision.json',summary)
    # Reuse independent escape/recovery arithmetic within the fresh stage deadline; no solves.
    from basketball_shared_verify_v8 import verify_escape,verify_recovery
    # Their historical helper has a 30-minute bound. Use the real remaining diagnostic deadline, never extend it.
    inherited_clock=dict(p,investigation_started_unix=p['investigation_started_unix']+15*60)
    verify_escape(inherited_clock,output/'escape-reuse.json')
    verify_recovery(inherited_clock,Path('docs/experiments/basketball-shared-timing-v8/recover'),output/'historical-recovery-reuse.json')
    import inspect
    from scipy.optimize._trustregion_constr.minimize_trustregion_constr import _minimize_trustregion_constr
    installed=inspect.getfile(_minimize_trustregion_constr)
    write(output/'stopping-reference.json',dict(url='https://docs.scipy.org/doc/scipy/reference/optimize.minimize-trustconstr.html',accessed_utc='2026-09-08',installed_source=installed,installed_sha256=sha256(installed),
        xtol='trust radius termination; inequalities also require barrier_parameter < barrier_tol',gtol='Lagrangian gradient and constraint violation',unchanged_original_stationarity=1e-6))
    implementation={str(f):sha256(f) for f in Path('scripts').glob('basketball_shared_*_v9.py')}
    freeze=dict(frozen_unix=time.time(),manifest=str(manifest_path),manifest_sha256=sha256(manifest_path),implementation_sha256=implementation,
        policies=[dict(name='baseline',conditioned_conditional=False,repair=False,disable_xtol=False),dict(name='metric',conditioned_conditional=True,repair=False,disable_xtol=False),
                  dict(name='initialization',conditioned_conditional=False,repair=True,disable_xtol=False),dict(name='stopping',conditioned_conditional=False,repair=False,disable_xtol=True)],
        joint_conditioning_common=True,initialization_minimum_target_depth=1e-6,stopping_xtol=0.,numerical_metric=p['v9']['conditioning'],
        numerical_screen=p['v9']['screen'],iteration_screen_targets=sorted({t['id']+'/'+l['reference']['path'] for t in manifest['targets'] for l in t['labels'] if l['stratum'] in ['cold_iteration','directional_iteration','support_changing_iteration']}),all_policies_use_full_manifest=True,maximum_policies=5,maximum_attempts=520,
        baseline_denominators='freeze independently recomputed positive baseline KKT after baseline completes and before candidate fits',
        standalone_preservation='all archived qualified controls must qualify without cost deterioration',
        final_union='only standalone arms passing all their screens may enter a single fresh final benchmark; if none pass, final benchmark remains unassessed',
        no_retuning=True,full_screens_authorized=False)
    write(output/'candidate-freeze.json',freeze);check(p,'diagnose')
    return dict(status='passed',terminal_kind=None,blockers=[],executed_counts=dict(scientific_attempts=0))
