# Plan 014: historical recovery and independent solver experiments

The four-hour clock began at **2026-09-08 02:25:00 UTC**, before inspection. Recovery and admission are due at 02:55, conditioning at 03:35, scalar search at 05:15, scientific computation at 06:05, and packaging and commits at 06:25. The [frozen policy](../../configs/basketball-rev2/timing-shared-v8.json) preserves both 200-state/iteration caps and all inherited scientific settings.

## Historical recovery

The [admission](basketball-shared-timing-v8/prepare/baseline.json) reconfirms 94/144 qualified v6 attempts (72 regularized, 22 data-only), 50 iteration-limit failures, five three-start disagreements, nine historical reference-cost failures, and three missing required data-only transfers. The exact v7 manifest supplies 432 v6 diagnostic references and nine unchanged lowest historical references. Neither historical nor replay states may seed development or the combined pilot.

The [recovery decision](basketball-shared-timing-v8/recover/recovery-decision.json) and [supplement](basketball-shared-timing-v8/recover/supplement.json.gz) distinguish reconstruction from replay evidence. All 288 v5/v6 returned records passed full multiplier, signed contribution, complementarity, and KKT comparisons. Two instrumented v4 raw-depth synthetic solves captured actual returned and callback multipliers. All nine historical states passed reconstruction; no historical replay was executed. A preliminary adapter check repeated this diagnostic validation before the final source freeze; its successful preparation/recovery outputs are retained locally under `.local/calibration/basketball-rev2/shared-v8/prototype`. These checks did not alter or optimize any saved historical state.

## Installed SciPy source audit

The [implementation manifest](basketball-shared-timing-v8/prepare/implementation.json) binds the installed SciPy 1.18.1 source, including all seven files used in reconstruction and returned-state ownership. Admission also checks the two installed solver hashes inherited from v6.

- `canonical_constraint.py` concatenates the nonlinear depth constraint before bounds. A lower depth bound contributes `-Dz`; each offset interval contributes its upper row followed by its lower row. Returned signed bound multipliers are upper minus lower. Unbounded coefficient coordinates have zero bound multipliers.
- `minimize_trustregion_constr.py` expands finite bounds with `nextafter`. The adapter uses these expanded bounds when reconstructing slacks, preserving the solver's arithmetic.
- `tr_interior_point.py`, `BarrierSubproblem._compute_function`, overwrites every `keep_feasible` slack with minus the canonical inequality. All constraints in these attempts have `keep_feasible=True`. Thus no unknown slack variable needs estimation. The scaled gradient is `[G, -mu]`; the scaled Jacobian is `[C, diag(slack)]`.
- `equality_constrained_sqp.py` computes `v = -LS.dot(c)` using `projections(..., 'AugmentedSystem')`, before the first callback and after accepted steps. Reconstruction uses that installed least-squares operator and exact sparse assembly. It does not substitute central-path `mu/slack` estimates.
- Rejected steps retain the accepted `x`, gradient, Jacobian and multipliers. `update_state_sqp` does not replace those fields after rejection. Barrier updates recompute the gradient, Jacobian and multipliers before reporting the new barrier. Acceptance also checks equality of the saved returned and last callback parameters.
- v4 uses raw slacks `depth - 1e-8`. v5/v6 use `(depth - 1e-8)/hypot(1, depth - 1e-8)` and map transformed multipliers back through the exact depth derivative. These representations are audited separately.

The [independent verifier](../../scripts/basketball_shared_verify_v8.py) uses a dense SVD least-squares solve and independent physical projection/objective evaluation for the historical supplement. It does not call the recovery projection or sparse assembly. The unchanged v5 analytical audit is reevaluated, including all 172 rays, 3,956 existing probes and corrected finite-reference comparisons; no rays or amplitudes are added.

## Experimental gates

Conditioning retains all coefficients, supported and null directions, and identity nuisance blocks. Each local attempt charges its feasible destination-cold derivative evaluation, freezes transform bytes and uses exact objective/constraint chain rules. Both transformed stopping tolerance and original-coordinate stationarity are required.

Scalar search fixes camera 3 at all 51 integer offsets for all 48 problems, with cold, ascending and descending coefficient paths. Refinement retains inclusive ties and endpoints and evaluates every required path at each new coordinate. The omitted camera-offset objective and Lagrangian derivatives are published explicitly; conditional qualification does not imply joint qualification.

The combined pilot requires both independent screens to pass and starts with fresh caches and problems. Accepted timing, production candidate and final protocol remain null. Selection and final-validation consumption markers remain unchanged.

## Conditioning decision

The [conditioning screen](basketball-shared-timing-v8/condition/conditioning-decision.json) completed all 144 attempts and **rejected** the adapter. It qualified 116 attempts, preserved 93 of the 94 previously qualified attempts, and recovered 23 of the 50 previous failures across all three groups. The median new/old original-coordinate KKT ratio was 0.2500454, exceeding the required 0.1. The required recovery count was 25. Group 11, weight 1, outer lag −19, descending path was the previously qualified attempt that was not preserved.

No observable-growth issue was detected by the inherited threshold. The local records retain original costs, KKT vectors, transform bytes, physical and internal states, initialization sanitation and distinct-state ledgers. The largest recorded distinct-state count was 193 and the largest iteration count was 196; neither 200 limit was increased. Per-attempt elapsed times are recorded. Stage `cpu_seconds` and maximum RSS describe the controller process, not aggregate worker usage.

## Scalar-search decision and terminal outcome

The [scalar screen](basketball-shared-timing-v8/basins/basin-decision.json) completed all 48 profiles and **rejected** scalar search. Its 7,344 initial path attempts plus 4,782 refinement attempts produced 12,126 scheduled records. Of these, 10,596 invoked a conditional fit and 8,485 qualified. Another 1,530 required directional attempts had no valid seed and were retained without retry. The 3,641 failed required attempts include those missing fits. Costs disagreed across paths at 835 points.

All nine historical basins were recovered within 0.05 frames at qualifying detected minima and acceptable original costs. The [independent coverage verifier](basketball-shared-timing-v8/coverage-verification.json) checks actual minima and complete hundredth-frame flat intervals, rather than accepting an arbitrary nearby sampled point. Basin recovery does not override the all-fits and path-agreement requirements.

The [development verifier](basketball-shared-timing-v8/development-verification.json) independently recomputes physical objectives, depths, original-coordinate KKT values and omitted offset derivatives. It also verifies the refinement schedule and conditioning transform/state ledgers, and retains comparative runtimes, three-start disagreements, historical reference costs and required transfers.

The terminal outcome is a **completed scientific rejection**, documented in the [package](basketball-shared-timing-v8/package/result.json), [development decisions](basketball-shared-timing-v8/package/development-decisions.json), and [search ledgers](basketball-shared-timing-v8/package/search-ledgers.json). The combined pilot remains **unassessed** because neither independent screen passed. There were no historical replays, joint releases or complete combined searches. No arithmetic/provenance failure or deadline exhaustion was needed to reach this outcome.

## Validation and provenance

The final suite passed 217 Basketball tests (including 14 v8 regressions), seven budget tests and three SelfCap tests. The immutable v7 runner preserves the scoped historical v6 test-clock harness; no inherited tests were edited or skipped. Additional regressions cover rejected-state ownership, stale barrier rejection, conditional versus joint derivatives, changing support, cross-problem seeds and unknown execution counts when no worker artifact exists.

The [final verification](basketball-shared-timing-v8/verification-final.json) checks stage hashes, inherited v7 evidence and consumption-marker hashes. The [evidence manifest](basketball-shared-timing-v8/evidence.json) binds all v8 sources, tests, decisions and artifacts. All work, verification and local commits completed within the fresh four-hour budget. Accepted timing, production candidate and final-validation protocol remain null; selection and final-validation consumption markers are unchanged.

Run the workflow with the installed offline interpreter `.local/envs/calibration-global/bin/python` and `scripts/basketball_shared_workflow_v8.py`. Stages are `prepare`, `recover`, `diagnose`, `condition`, `basins`, `pilot`, and `package`, each with `--config`, a fresh `--output`, and a hashed `--predecessor` after preparation. Frozen absolute deadlines apply to every stage.
