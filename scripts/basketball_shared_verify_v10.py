"""Reload artifacts, independently recompute physical arithmetic, and inspect entry journals."""
import hashlib
from pathlib import Path
import numpy as np
from basketball_shared_storage_v10 import read,sha,encode,journal_prefix,PersistenceError
from basketball_shared_accounting_v10 import problem_identity,bytes_of
from basketball_shared_diagnose_v9 import make_problem
from basketball_shared_verify_v9 import verify_row

def exact_hashes(hashes):
    for path,expected in hashes.items():
        if sha(path)!=expected:raise PersistenceError('execution source mismatch '+path)

def verify_item(item,directory):
    directory=Path(directory);identity=item['identity'];row=item['row'];ref=item['reference']
    assert item['id']==identity['attempt_id']
    assert row['policy']==identity['policy'] and identity['run_id']=='basketball-shared-v10-1788843120'
    exact_hashes(identity['execution_sha256'])
    assert sha(identity['policy_file'])==identity['policy_sha256']
    assert sha(identity['manifest'])==identity['manifest_sha256']
    policy=read(identity['policy_file']);assert policy['name']==identity['policy']
    assert identity['reference']==ref
    prefix=journal_prefix(directory/'journal.jsonl');assert prefix['complete']
    events=prefix['events'];allocated=[e for e in events if e['event']=='allocated']
    assert len(allocated)==1 and allocated[0]['identity']==identity
    actual=[e for e in events if e['event']=='numerical_entry']
    returns=[e for e in events if e['event']=='numerical_return']
    calls=[e for e in events if e['event']=='solver_invocation']
    seed=row.get('seed');assert seed==identity['dependency_provenance']
    if seed is not None:
        assert seed['policy']==identity['policy']
        assert seed['artifact_sha256']==sha(seed['artifact'])
        source=read(seed['artifact']);source_dir=Path(seed['artifact']).parent;receipt=read(source_dir/'receipt.json')
        assert inspect_attempt(source_dir,verify=False)['completed']
        source_completion=[e for e in journal_prefix(source_dir/'journal.jsonl')['events'] if e['event']=='completed'][0]
        assert source_completion['unix']<=allocated[0]['unix']
        assert receipt['artifact_sha256']==seed['artifact_sha256'] and source['row']['valid']
        assert source['identity']['run_id']==identity['run_id'] and source['identity']['policy_sha256']==identity['policy_sha256']
        assert source['id']==seed['id'] and source['row']['returned_state']==seed['state']
        np.testing.assert_array_equal(row['seed_initial_x'],source['row']['x'])
        for k in ['group_id','weight']:assert source['reference'][k]==ref[k]
        if 'offset' in ref:assert source['reference']['lag']==ref['lag']
        assert seed['coordinate']==source['reference']['offset' if 'offset' in ref else 'lag']
    if not row['executed']:
        assert not actual and not calls and seed is None
        assert not row['valid'] and row.get('accounting') is None
        proof=verify_row(ref,row)
        return dict(passed=True,physical=proof,solver_invocations=0,numerical_entries=0,distinct_states=0,missing_seed=True)
    a=row['accounting'];p=make_problem(ref)
    key,data=problem_identity(p,identity['namespace'],identity)
    assert a['problem_key']==key and a['problem']==data
    problems=[e for e in events if e['event']=='problem'];assert len(problems)==1 and problems[0]['problem_key']==key and problems[0]['problem']==data
    states=[{k:e[k] for k in ['identity','scope','canonical_hex','physical_hex']} for e in events if e['event']=='state']
    assert states==a['states']
    transform=next((e for e in reversed(events) if e['event'] in ['transform','problem']),None)
    assert transform['transform_hex']==a['transform_hex'] and transform['origin_hex']==a['origin_hex']
    assert problems[0]['scale_hex']==a['scale_hex']
    n=len(p.x0);P=np.frombuffer(bytes.fromhex(a['transform_hex']),dtype='<f8').reshape(n,n);origin=np.frombuffer(bytes.fromhex(a['origin_hex']),dtype='<f8')
    np.testing.assert_allclose(P,P.T,atol=1e-12,rtol=1e-12)
    scale=np.frombuffer(bytes.fromhex(a['scale_hex']),dtype='<f8')
    for request in a['events']:
        yhex=request.get('conditioned_hex')
        if yhex is not None:
            y=np.frombuffer(bytes.fromhex(yhex),dtype='<f8');state=next(s for s in states if s['identity']==request['state'])
            assert bytes_of(origin+P@y).hex()==state['canonical_hex']
    assert len(actual)==len(returns)==len(a['observed_numerical_entries'])==len(a['entries'])
    byreturn={e['index']:e for e in returns};assert len(byreturn)==len(returns)
    for i,(event,observed,entry) in enumerate(zip(actual,a['observed_numerical_entries'],a['entries'])):
        assert event['index']==i and event['kind']==observed['kind']==entry['kind']
        assert event['physical_hex']==observed['physical_hex'] and event['state']==entry['state']
        assert event['seq']<byreturn[i]['seq'] and byreturn[i]['status']==observed['status']==entry['status']=='completed'
    assert len(calls)==int(row['solver_invoked'])<=1
    proof=verify_row(ref,row)
    # Independently verify all available initialization depths, including rejected cold starts.
    from basketball_shared_accounting_v10 import NumericalEntries
    raw=NumericalEntries(p);byid={s['identity']:s for s in states}
    for check in row.get('initialization_transfer',{}).get('checks',[]):
        state=byid[check['state']];x=np.frombuffer(bytes.fromhex(state['physical_hex']),dtype='<f8')
        assert check['finite']==bool(np.isfinite(x).all())
        assert check['bounds']==bool(np.all(np.abs(x[:p.n_offsets])<=25))
        if check['minimum_depth'] is not None:
            z,_=raw.depth(x);np.testing.assert_allclose(min(z),check['minimum_depth'],atol=1e-12,rtol=1e-12)
            assert check['valid']==bool(check['finite'] and check['bounds'] and min(z)>2e-8)
    init=row.get('initialization_transfer',{})
    if init.get('cold_x') is not None:
        cold=np.asarray(init['cold_x']);depth,_=raw.depth(cold)
        assert init['cold_valid']==bool(np.isfinite(cold).all() and np.all(np.abs(cold[:p.n_offsets])<=25) and min(depth)>2e-8)
        if calls:
            conditioned=policy['conditioned_conditional'] if 'offset' in ref else True
            if conditioned:
                from basketball_shared_solver_v4 import ConstrainedProblem
                from basketball_shared_curvature_v6 import deterministic_svd
                base=ConstrainedProblem(p);_,J=base.evaluate(cold/base.scale)
                singular,V,tol,_=deterministic_svd(J.toarray()[:,p.n_offsets:])
                factors=np.ones(len(singular));active=singular>tol;factors[active]=np.clip(1/singular[active],1e-3,1e3)
                expected=np.eye(n);expected[p.n_offsets:,p.n_offsets:]=(V.T*factors)@V
                np.testing.assert_allclose(P,expected,atol=1e-12,rtol=1e-12)
                assert bytes_of(cold/scale)==bytes_of(origin)
            else:
                np.testing.assert_array_equal(P,np.eye(n));np.testing.assert_array_equal(origin,np.zeros(n))
    return dict(passed=True,physical=proof,solver_invocations=len(calls),numerical_entries=len(actual),distinct_states=len(states),missing_seed=False)

def inspect_attempt(directory,verify=True):
    directory=Path(directory);prefix=journal_prefix(directory/'journal.jsonl');events=prefix['events']
    calls=sum(e['event']=='solver_invocation' for e in events);entries=sum(e['event']=='numerical_entry' for e in events);returns=sum(e['event']=='numerical_return' for e in events)
    completed=[e for e in events if e['event']=='completed'];artifact=directory/'attempt.json.gz';receipt=directory/'receipt.json'
    result=dict(directory=str(directory),journal_valid_prefix_bytes=prefix['valid_bytes'],journal_intact=prefix['complete'],solver_invocations=None,numerical_entries=None,solver_invocations_lower_bound=calls,numerical_entries_lower_bound=entries,numerical_returns_lower_bound=returns,persisted=artifact.exists(),completed=False,status='interrupted_or_unknown',qualified=None)
    if completed:
        assert len(completed)==1 and prefix['complete'] and artifact.exists() and receipt.exists()
        event=completed[0];assert event['artifact_sha256']==sha(artifact) and event['receipt_sha256']==sha(receipt)
        r=read(receipt);assert r['artifact_sha256']==sha(artifact)
        item=read(artifact);assert event['id']==r['id']==item['id']
        proof=verify_item(item,directory) if verify else r['verification']
        assert proof['passed']
        result.update(completed=True,status='verified_outcome',qualified=item['row']['valid'],solver_invocations=calls,numerical_entries=entries,verification=proof)
    return result

def verify_schedule(records,manifest):
    """Reconstruct frozen ordering and seed choices from independently reloaded outcomes."""
    from basketball_shared_benchmark_v9 import jobs,nearest
    byid={r['id']:r for r in records};assert len(byid)==len(records)==81
    visited=[]
    def take(ref,path,seed=None):
        ident=ref['id']+'/'+path;item=byid[ident];visited.append(ident)
        expected={k:ref[k] for k in ['group_id','weight','lag','offset'] if k in ref}
        assert item['reference']==expected
        actual=item['row'].get('seed');assert (actual is None)==(seed is None)
        if seed is not None:assert actual['id']==seed[1]['id'] and actual['coordinate']==seed[0]
        assert item['row']['executed']==bool(path=='cold' or seed is not None)
        return item
    for task in jobs(manifest):
        cold={}
        if task['kind']=='conditional':
            for ref in sorted(task['dependencies']+task['targets'],key=lambda t:(t['offset'],t['id'])):cold[ref['offset']]=take(ref,'cold')
            for path,reverse,side in [('ascending',False,'lower'),('descending',True,'upper')]:
                previous=None;directional={}
                for ref in sorted(task['targets'],key=lambda t:t['offset'],reverse=reverse):
                    offset=ref['offset']
                    seed=(previous if previous is not None else nearest(cold,offset)) if float(offset).is_integer() else nearest({**cold,**directional},offset,side)
                    item=take(ref,path,seed);directional[offset]=item
                    if item['row']['valid']:previous=(offset,item)
        else:
            for ref in sorted(task['dependencies'],key=lambda t:t['lag']):cold[ref['lag']]=take(ref,'cold')
            for ref in task['targets']:
                seed=None if ref['path']=='cold' else nearest(cold,ref['seed_lag'])
                if seed is not None and seed[0]!=ref['seed_lag']:seed=None
                take(ref,ref['path'],seed)
    assert len(set(visited))==len(visited)==81
    return dict(passed=True,scheduled=81,seed_selection_reconstructed=True)
