"""Shared-budget physical sanitation and optional analytical feasible cold construction."""
import numpy as np
from basketball_shared_solver_v6 import support, MARGIN


def sampled_support(a,x,kind,source_lag=None,endpoint=None,state=None):
    p=a.p;scope='destination' if source_lag is None else f'source-camera-{endpoint}-offset-{float(source_lag).hex()}'
    s=a.state_x(x,kind,scope) if state is None else a.ledger.request(state.q,kind,scope=scope)
    previous=None if endpoint is None else p.offsets[endpoint]
    try:
        if source_lag is not None:p.offsets[endpoint]=source_lag
        def calculate(physical):
            event=a.numerical.observe('support',physical)
            try:value=support(p,physical)
            except BaseException:event['status']='interrupted';raise
            event['status']='completed';return value
        return a.ledger.enter(s,'support',calculate)
    finally:
        if source_lag is not None:p.offsets[endpoint]=previous


def repair_cold(a,cold,minimum_depth=1e-6):
    """One analytical positive-z shift, verified at the destination; no optimization."""
    s=a.state_x(cold,'feasibility_original');z,_=a.raw(s)
    slopes=np.concatenate([np.full(len(o['frames']),np.asarray(a.p.cameras[o['camera_id']]['R'])[2,2]) for g in a.p.groups for o in g['observations']])
    if np.any(slopes<=0):return None,dict(applied=False,reason='uniform positive-z direction not strictly feasible for this calibration')
    delta=max(0.,float(np.max((minimum_depth-z)/slopes)))
    delta=np.nextafter(delta,np.inf) if delta else 0.
    x=s.x.copy();x[a.p.n_offsets+2::3]+=delta
    t=a.state_x(x,'feasibility_analytical_trial');depth,_=a.raw(t)
    good=bool(np.isfinite(t.x).all() and np.min(depth)>2*MARGIN)
    return (t.x.copy() if good else None),dict(applied=True,delta=delta,minimum_target_depth=minimum_depth,minimum_observed_depth=float(np.min(depth)),feasible=good,iterations=0)


def sanitize(a,seed=None,source_lag=None,endpoint=None,repair=False):
    p=a.p;cold=p.x0.copy();checks=[];replaced=[];source=[];restoration=None
    def valid(x,kind):
        s=a.state_x(x,kind);finite=bool(np.isfinite(s.x).all());bounded=bool(np.all(np.abs(s.x[:p.n_offsets])<=25))
        z=a.raw(s)[0] if finite and bounded else np.array([np.nan])
        good=bool(finite and bounded and np.isfinite(z).all() and np.min(z)>2*MARGIN)
        checks.append(dict(state=s.identity,finite=finite,bounds=bounded,minimum_depth=float(np.min(z)) if np.isfinite(z).all() else None,valid=good))
        return good,s.x.copy()
    cold_valid,cold=valid(cold,'cold_initialization')
    if not cold_valid and repair:
        new,restoration=repair_cold(a,cold)
        if new is not None:cold_valid,cold=valid(new,'restored_cold')
    original=cold.copy() if seed is None else np.asarray(seed,float).copy()
    if original.shape!=cold.shape:raise ValueError('seed parameterization mismatch')
    original_valid,original=valid(original,'seed_initialization')
    sanitized=original.copy()
    if seed is not None:
        if endpoint is None or source_lag is None:raise ValueError('warm seed needs source coordinate and endpoint')
        source=sampled_support(a,original,'source_support',source_lag,endpoint)
        for row in source:
            for block in row['unsupported']:
                begin=p.n_offsets+row['group_index']*p.nc*3+block*3
                sanitized[begin:begin+3]=cold[begin:begin+3]
                replaced.append(dict(group_id=row['group_id'],block=block))
    selected=None;fraction=None
    for fraction in [2.**-k for k in range(21)]+[0.]:
        trial=cold.copy() if fraction==0 else sanitized.copy() if fraction==1 else cold+fraction*(sanitized-cold)
        good,trial=valid(trial,'sanitation_trial')
        if good:selected=trial;break
    destination=sampled_support(a,cold,'destination_support')
    return selected,cold,dict(original_x=original.tolist(),cold_x=cold.tolist(),sanitized_x=sanitized.tolist(),selected_x=None if selected is None else selected.tolist(),
        source_lag=source_lag,destination_lag=None if endpoint is None else p.offsets[endpoint],replaced_blocks=replaced,source_support=source,destination_support=destination,
        original_valid=original_valid,cold_valid=cold_valid,blend_fraction=fraction if selected is not None else None,checks=checks,restoration=restoration,iterations=0)
