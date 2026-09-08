"""Validate the conditional exact Hessian against frozen independent FD actions."""
import os
for name in ['OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS','NUMEXPR_NUM_THREADS']:os.environ[name]='1'
import inspect
from pathlib import Path
import time
import numpy as np
from basketball_scale import read,write
from basketball_audit import sha256
from basketball_shared_diagnose_v5 import compressed_read,compressed_write,fixture
from basketball_shared_solver_v6 import ConstrainedProblem,provenance
from basketball_shared_diagnose_v6 import check
from basketball_continuation_audit import verify_hashes
from scipy.optimize._trustregion_constr import minimize_trustregion_constr, tr_interior_point


def validate(root):
    p=read('configs/basketball-rev2/timing-shared-v6.json');check(p)
    decision=read(root/'diagnose/diagnostic-decision.json');assert decision['passed']
    manifest=compressed_read(root/'prepare/diagnostic-manifest.json.gz')
    problems={};records=[];failures=[];start=time.monotonic();assemblies=0
    for artifact in decision['artifacts']:
        path=root/'diagnose'/artifact['path'];assert sha256(path)==artifact['sha256']
        for row in compressed_read(path)['records']:
            check(p);state=manifest['states'][row['state_key']];key=(state['group_id'],state['lag'],state['weight'])
            if key not in problems:problems[key]=fixture(*key,lambda:check(p))
            problem=problems[key];a=ConstrainedProblem(problem);q=np.asarray(state['x'])/a.scale
            H=a.hess(q);assemblies+=a.hessian_assemblies
            for index,probe in enumerate(row['analysis']['probes']):
                if probe['selected'] is None:continue
                u=np.asarray(probe['levels'][probe['selected']['level']]['action']);exact=H@probe['vector']
                error=float(np.max(np.abs(u-exact)));limit=1e-7+1e-3*max(np.max(np.abs(u)),np.max(np.abs(exact)))
                record=dict(reference=row['reference'],probe=index,absolute_error=error,limit=float(limit),passed=bool(error<=limit))
                records.append(record)
                if not record['passed']:failures.append(record)
    assert not failures,failures[:10]
    checks=compressed_write(root/'exact-hessian-actions.json.gz',dict(records=records,assemblies=assemblies,scientific_solves=0,
                    namespace='v6-exact-hessian-validation',wall_seconds=time.monotonic()-start))
    source={f:sha256(f) for f in ['scripts/basketball_shared_solver_v6.py','scripts/basketball_shared_profiles_v6.py',
            'scripts/basketball_shared_pilot_v6.py','scripts/basketball_shared_validate_hessian_v6.py',
            'tests/test_basketball_shared_hessian_v6.py','tests/test_basketball_shared_inherited_v6.py']}
    for name in ['exact-hessian-tests.log','inherited-v6-tests.log']:
        assert (root/name).read_text().rstrip().endswith('OK');source[str(root/name)]=sha256(root/name)
    reuse=read(root/'v5-reuse-verification.json');assert reuse['status']=='passed' and reuse['analytical_ray_limits']==172
    assert reuse['diagnostic_probes']==3956
    source[str(root/'v5-reuse-verification.json')]=sha256(root/'v5-reuse-verification.json')
    solver_sources={inspect.getsourcefile(m):sha256(inspect.getsourcefile(m)) for m in [minimize_trustregion_constr,tr_interior_point]}
    code=Path(inspect.getsourcefile(minimize_trustregion_constr)).read_text()
    assert 'H_objective.dot(p) + H_constraints.dot(p)' in code
    check(p)
    write(root/'exact-hessian-validation.json',dict(passed=True,escape_verified=True,source_sha256=source,
          installed_solver_sha256=solver_sources,solver=provenance(),actions=checks,stable_actions_checked=len(records),
          maximum_action_error=max(r['absolute_error'] for r in records),diagnostic_decision_sha256=sha256(root/'diagnose/diagnostic-decision.json'),
          escape_rays=172,escape_probes=3956,escape_grid_rerun=False,
          escape_scope='identical objectives and feasible sets; unchanged 12 v3 records; finite upper bounds are not qualified minima',
          solver_hessian_treatment='Installed LagrangianHessian adds objective Hessian and multiplier-weighted constraint Hessian; barrier is internal. Objective callable adds neither.',
          tests='fixed synthetic derivative tests and inherited unit-test solves, separate from the scientific cohort',
          initial_regression_corrections='coarse 1e-4 truncation error resolved by required stable 1e-5/1e-6 checks; inherited prepare test mock moved to v6 owner. No fitting outcome or solver policy tuning.',
          elapsed_seconds=time.time()-p['investigation_started_unix']))
    print('exact Hessian and escape reuse validated',len(records),'actions',flush=True)

if __name__=='__main__':validate(Path('docs/experiments/basketball-shared-timing-v6'))
