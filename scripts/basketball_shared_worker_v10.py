"""One fresh job per worker; warm dependencies are usable only after durable completion."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='1'
import sys
import time
from pathlib import Path
import numpy as np
from basketball_shared_storage_v10 import Journal,publish,read,sha,commit_attempt,PersistenceError,journal_prefix
from basketball_shared_verify_v10 import verify_item,exact_hashes
from basketball_shared_benchmark_v9 import nearest
from basketball_shared_diagnose_v9 import make_problem
from basketball_shared_solver_v10 import solve
from basketball_shared_solver_v4 import ConstrainedProblem

def worker(root,policy_file,task_file,deadline,failure):
    root=Path(root);policy=read(policy_file);task=read(task_file);execution=read(policy['execution_index']);exact_hashes(execution)
    records=[];references=[]
    def check():
        if Path(failure).exists():raise PersistenceError('dispatch cancelled by failed sibling')
        if time.time()>=deadline:raise TimeoutError('frozen absolute policy deadline')
    def fit(ref,path,seed=None,allocation=None):
        check();ident=ref['id']+'/'+path;directory=root/(allocation or ref['id'])/path
        if directory.exists():raise PersistenceError('attempt already allocated; numerical resume forbidden '+str(directory))
        directory.mkdir(parents=True);j=Journal(directory/'journal.jsonl')
        reference={k:ref[k] for k in ['group_id','weight','lag','offset'] if k in ref}
        provenance=None if seed is None else dict(id=seed[1]['id'],coordinate=seed[0],policy=seed[1]['row']['policy'],state=seed[1]['row']['returned_state'],artifact=seed[1]['artifact']['artifact'],artifact_sha256=seed[1]['artifact']['sha256'])
        identity=dict(run_id='basketball-shared-v10-1788843120',attempt_id=ident,allocation=allocation,namespace='v10/'+policy['name']+'/'+(allocation or task['id'])+'/'+ident,policy=policy['name'],policy_file=str(policy_file),policy_sha256=sha(policy_file),manifest=policy['manifest'],manifest_sha256=sha(policy['manifest']),reference=reference,dependency_provenance=provenance,execution_sha256=execution)
        j.append('allocated',identity=identity)
        if seed is not None and seed[1]['row']['policy']!=policy['name']:raise PersistenceError('cross-policy seed')
        if path!='cold' and seed is None:
            row=dict(valid=False,converged=False,executed=False,solver_invoked=False,objective=None,error='missing required fresh qualifying source',policy=policy['name'],seed=None)
        else:
            problem=make_problem(reference,check);problem.journal=j
            row=solve(problem,None if seed is None else seed[1]['row']['x'],None if seed is None else seed[0],3 if task['kind']=='conditional' else 2,
                conditioned=policy['conditioned_conditional'] if task['kind']=='conditional' else True,repair=policy['repair'],disable_xtol=policy['disable_xtol'],namespace=identity['namespace'],provenance=identity)
            row.update(executed=True,solver_invoked=any(e['event']=='solver_invocation' for e in journal_prefix(j.path)['events']),policy=policy['name'],seed=provenance,seed_initial_x=None if seed is None else seed[1]['row']['x'])
            if 'offset' in reference and row.get('x') is not None:
                joint=make_problem({k:v for k,v in reference.items() if k!='offset'},check);a=ConstrainedProblem(joint);x=np.r_[reference['offset'],row['x']]
                j.append('diagnostic_entry',kind='omitted_offset_derivatives',physical_hex=np.asarray(x,dtype='<f8').tobytes().hex(),role='same physical state joint diagnostic; outside local coefficient solver budget')
                r,J=a.evaluate(x/a.scale);z,D=a.depth(x/a.scale)
                row['omitted_camera_offset_objective_derivative_per_frame']=float((2*J.T@r)[0]/25)
                vd=row.get('multipliers_depth');row['omitted_camera_offset_lagrangian_derivative_per_frame']=None if vd is None else float((2*J.T@r+D.T@vd)[0]/25)
                row['omitted_derivative_role']='read-only same-physical-state joint diagnostic; never qualifies joint state'
                j.append('diagnostic_return',kind='omitted_offset_derivatives')
        item=dict(id=ident,identity=identity,reference=reference,row=row)
        artifact=commit_attempt(directory,item,verify_item)
        receipt=read(directory/'receipt.json');item['verification']=receipt['verification']['physical'];item['artifact']=artifact
        records.append(item);references.append(artifact)
        return item
    cold={}
    if 'preflight' in task:
        for index,ref in enumerate(task['preflight']):fit(ref,'cold',allocation=task['id']+'-'+str(index))
    elif task['kind']=='conditional':
        for ref in sorted(task['dependencies']+task['targets'],key=lambda t:(t['offset'],t['id'])):cold[ref['offset']]=fit(ref,'cold')
        for path,reverse,side in [('ascending',False,'lower'),('descending',True,'upper')]:
            previous=None;directional={}
            for ref in sorted(task['targets'],key=lambda t:t['offset'],reverse=reverse):
                offset=ref['offset']
                if float(offset).is_integer():seed=previous if previous is not None else nearest(cold,offset)
                else:seed=nearest({**cold,**directional},offset,side)
                item=fit(ref,path,seed);directional[offset]=item
                if item['row']['valid']:previous=(offset,item)
    else:
        for ref in sorted(task['dependencies'],key=lambda t:t['lag']):cold[ref['lag']]=fit(ref,'cold')
        for ref in task['targets']:
            path=ref['path'];seed=None if path=='cold' else nearest(cold,ref['seed_lag'])
            if seed is not None and seed[0]!=ref['seed_lag']:seed=None
            fit(ref,path,seed)
    publish(root/(task['id']+'-summary.json'),dict(policy_sha256=sha(policy_file),task_sha256=sha(task_file),attempts=references,completed=True))

if __name__=='__main__':
    try:worker(Path(sys.argv[1]),Path(sys.argv[2]),Path(sys.argv[3]),float(sys.argv[4]),Path(sys.argv[5]))
    except BaseException as e:
        import traceback
        failure=Path(sys.argv[5]);detail=dict(worker_pid=os.getpid(),error=type(e).__name__+': '+str(e),traceback=traceback.format_exc(),unix=time.time())
        try:publish(failure,detail)
        except FileExistsError:pass
        traceback.print_exc();raise SystemExit(1)
