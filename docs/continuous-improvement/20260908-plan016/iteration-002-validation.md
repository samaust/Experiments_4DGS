# Iteration 002 validation — Plan 018

Implementation and package checks pass; the complete scientific diagnostic fails
independent gradient verification. These outcomes are deliberately separate.
See [implementation](iteration-002-implementation.md) and
[the full report](../../experiments/basketball-shared-timing-v11.md).

## Focused regression checks

Final command:

```bash
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .local/envs/calibration-global/bin/python -m unittest discover -s tests -p test_basketball_shared_trajectory_v11.py -v
```

Twelve distinct tests passed in 0.032 seconds. Two earlier 10-test runs also
passed; 32 toy test invocations total, with retained
[first](../../experiments/basketball-shared-timing-v11/tests.log),
[second](../../experiments/basketball-shared-timing-v11/tests-02.log), and
[final](../../experiments/basketball-shared-timing-v11/tests-03.log) logs.
Tests use hand-authored data only and perform no scientific fixture loading or fits.
They cover fixed caps/deadlines, duplicate/skipped ownership, actual-entry bytes,
interruption charge retention, receipt/state/multiplier/returned identity tampering,
constructor/optimizer/Hessian exclusions, known projective/acceleration limits,
exact support versus tiny nonzero slope, depth rejection before objective, direct
worker denial, degenerate direction handling and the unchanged growth floor.

No broad solver-heavy test suite or scientific rerun was executed.

## Scientific evidence validation

The one supervisor invocation is in
[commands](../../experiments/basketball-shared-timing-v11/commands.log);
[budget](../../experiments/basketball-shared-timing-v11/budget.json) charges
7.84522387 numerical seconds. All fixed slots complete and
both entry audits reconcile: 1,200 depth, 332 residual/gradient and 48 analytical
entries in total, no duplicates/unallocated entries, no errors or interruptions.
Worker and supervisor exited; no running jobs remain.

[Verification](../../experiments/basketball-shared-timing-v11/verification.json)
reports 537/600 finite-slot comparisons passed and 63 failed. All 48 snapshots,
all 24 analytical-limit comparisons, all 24 ray derivations, physical state
identities and saved callback/returned checks pass. All 63 failures are probe
`G` component comparisons at unchanged `atol=1e-10, rtol=1e-8`.
[Failure extraction](../../experiments/basketball-shared-timing-v11/verification-failures.json)
is JSON-only subtraction/comparison of retained arrays, not another gradient
evaluation. It lists 367 failed components and exact error/tolerance ratios.
No post-run scientific code change, arithmetic reevaluation or tolerance relaxation
occurred. A2/A3 are failed, not scientifically unresolved or passed.

## Package, identity and repository checks

[Package validation](../../experiments/basketball-shared-timing-v11/package-validation.json)
passes JSON-only schedule/budget/failure-honesty checks, 40 Markdown links, 182
historical source/artifact hashes and 1,664 final execution source/installed-file
hashes. Historical v10 inputs and sources remain unchanged. No training ledger,
scientific gate, threshold or accepted timing was modified. Output files reject
replacement; the separate admission and final execution-source identities explain
the implementation work between input admission and numerical readiness.

`git diff --check` and `git diff --cached --check` passed. The staged diff was
inspected before local commit `b6422ad4084dcc1438db3f5e4e35c28ca79f41c7`. The commit contains only the two v11
scripts, focused test, v11 report and its complete evidence directory, plus the
four parent-owned resume changes explicitly authorized for inclusion:

- `docs/continuous-improvement/20260908-plan016/objective.md`
- `docs/continuous-improvement/20260908-plan016/status.md`
- `docs/continuous-improvement/20260908-plan016/iteration-002-assessment-03-resume.md`
- `docs/continuous-improvement/20260908-plan016/iteration-002-plan018-authorization.json`

The implementation did not edit those four parent files. Exact staged paths are
available from `git show --name-only b6422ad4084dcc1438db3f5e4e35c28ca79f41c7`. The two iteration result files
are staged separately for the final handoff checkpoint after their Markdown links
and diff checks pass; the orchestrator receives that commit ID and final elapsed
time. No permission/sandbox denial, retry requirement or git failure occurred.

Remaining gaps: independent arithmetic on 63 control probes is not validated;
Basketball has no qualifying timing solution, prepared reconstruction comparison,
or completed quality/motion/speed/resource evidence. Plan 018 neither advances
any scientific gate nor completes SC-01/03. The concrete next investigation and
proposed separate resource allocation are in the implementation handoff.
