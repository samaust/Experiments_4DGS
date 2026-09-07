"""Reconstruct all rejected v3 attempts and probe saved coefficient directions."""
import numpy as np
from basketball_scale import read,write
from basketball_audit import sha256
from basketball_continuation_audit import verify_hashes
from basketball_shared_spline_v2 import SplineProblem
from basketball_shared_synthetic_v2 import synthetic
from basketball_shared_solver_v3 import rank_record,objective_agreement
from basketball_shared_solver_v4 import support,ConstrainedProblem


def state_record(p,x,rank=True):
    x=np.asarray(x);offsets,coeff=p.unpack(x);r,J=p.evaluate(x)
    observations=[]
    for gi,g in enumerate(p.groups):
        for o in g['observations']:
            B=p.spline((np.asarray(o['frames'])-offsets[o['camera_id']])/25)
            xyz=B@coeff[gi];camera=p.cameras[o['camera_id']]
            depth=(xyz*p.diameter+p.center)@np.asarray(camera['R'])[2]+camera['t'][2]
            observations.append(dict(group_id=g['group_id'],camera_id=o['camera_id'],frames=np.asarray(o['frames']).tolist(),
                normalized_xyz=xyz.tolist(),normalized_depth=(depth/p.diameter).tolist()))
    row=dict(x=x.tolist(),coefficient_magnitudes=np.linalg.norm(coeff,axis=2).tolist(),support=support(p,x),
        observations=observations,jacobian_column_norms=np.sqrt(J.power(2).sum(axis=0)).A1.tolist(),
        residual=r.tolist(),objective=float(r@r))
    if rank:row['rank']=rank_record(p,x)
    return row


def diagnose(p,output):
    import time
    def check():
        if time.time()>=p['investigation_started_unix']+5400:raise TimeoutError('90-minute diagnosis deadline')
    evidence=read(p['diagnostic_evidence'])
    for key in ['source_sha256','artifacts_sha256']:verify_hashes(evidence[key])
    file=p['rejected_profiles'];raw=read(file);groups,cameras,_,window=synthetic('direction_changes',0.,-.1,100,groups=12)
    audit=[]
    for state in raw['states']:
        gid=state['group_id']
        for lag,attempts in state['attempts'].items():
            for attempt in attempts:
                if attempt['valid']:continue
                check();lag=float(lag);sl=attempt['seed_lag'];sl=lag if sl is None else sl
                def problem(l):return SplineProblem([groups[gid]],cameras,{1:0.,2:l,3:0.},window,10,0.,(1,2),check)
                source=problem(sl);destination=problem(lag);seed=np.asarray(attempt['initial_x'])
                cold_source=source.x0.copy()
                records=dict(source_cold=state_record(source,cold_source),source_seed=state_record(source,seed),destination_seed=state_record(destination,seed),
                    destination_final=state_record(destination,np.asarray(attempt['x'])),destination_cold=state_record(destination,destination.x0))
                # Include every weak source block and every unusually large saved displacement.
                displacement=(seed-cold_source)[source.n_offsets:].reshape(source.nc,3)
                final_displacement=(np.asarray(attempt['x'])-destination.x0)[destination.n_offsets:].reshape(destination.nc,3)
                blocks=sorted(set(records['source_seed']['support'][0]['unsupported']) |
                              set(np.flatnonzero(np.linalg.norm(displacement,axis=1)>10)) |
                              set(np.flatnonzero(np.linalg.norm(final_displacement,axis=1)>10)))
                blocks=list(map(int,blocks))
                probes=[]
                for origin,delta,base in [('seed',displacement,cold_source),('final',final_displacement,destination.x0)]:
                    for block in blocks:
                        vector=delta[block];norm=float(np.linalg.norm(vector))
                        if norm==0:continue
                        direction=vector/norm
                        for fixed,prob in [('source',source),('destination',destination)]:
                            baseline=state_record(prob,base,False)['objective']
                            for sign in [-1,1]:
                                for exponent in range(0,45,2):
                                    check();amplitude=10.**exponent;x=base.copy();i=prob.n_offsets+3*block;x[i:i+3]+=sign*amplitude*direction
                                    try:
                                        row=state_record(prob,x,False)
                                        depths=np.concatenate([o['normalized_depth'] for o in row['observations']]);xyz=np.concatenate([o['normalized_xyz'] for o in row['observations']])
                                        probes.append(dict(origin=origin,block=block,fixed=fixed,sign=sign,amplitude=amplitude,saved_displacement_norm=norm,
                                            objective=row['objective'],baseline_objective=baseline,agrees_with_baseline=objective_agreement(row['objective'],baseline),
                                            min_depth=float(min(depths)),max_depth=float(max(depths)),max_xyz=float(np.max(np.abs(xyz))),
                                            residual=row['residual'],observations=row['observations']))
                                    except FloatingPointError as exc:probes.append(dict(origin=origin,block=block,fixed=fixed,sign=sign,amplitude=amplitude,error=str(exc)))
                filename=output/f'rejected-{len(audit):02d}.json'
                write(filename,dict(group_id=gid,lag=lag,start=attempt['start'],source_lag=sl,source_start=attempt['seed_start'],
                    saved_attempt=attempt,states=records,suspect_blocks=blocks,probes=probes))
                # Finite probes can establish local weak-support activation, never global nonexistence.
                escaping=[r for r in probes if r.get('min_depth',-1)>0 and r.get('max_xyz',0)>1e6 and
                          (r['objective']<r['baseline_objective'] or r['agrees_with_baseline'])]
                audit.append(dict(group_id=gid,lag=lag,start=attempt['start'],source_lag=sl,artifact=str(filename),sha256=sha256(filename),
                    suspect_blocks=blocks,probes=len(probes),positive_depth_large_trajectory_probes_retaining_fit=len(escaping)))
                print('audited',gid,lag,attempt['start'],len(probes),'probes',flush=True)
    if len(audit)!=12:raise ValueError('expected exactly 12 saved v3 rejected attempts')
    write(output/'diagnosis.json',dict(attempts=audit,source=str(file),source_sha256=sha256(file),
        amplitude_definition='Euclidean amplitude along normalized saved displacement from cold; both signs; seed and final displacement',
        distinctions=['exact zero sampled support','weak sampled support becoming observable after transfer','observable trajectory displacement','positive-depth large-coordinate probes retaining fit'],
        finite_probes_do_not_prove_global_minimum=True,observable_escape_resolved=False,
        conclusion='Weak-block activation is diagnosed; finite amplitude probes do not resolve observable escape or certify a finite optimum. Constrained exact retest remains required.'))
    return dict(status='passed',terminal_kind=None,blockers=[],rejected_attempts_audited=12,observable_escape_resolved=False)
