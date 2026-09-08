# Basketball shared timing v7: required historical multipliers missing

[Plan 013](../../plans/plan_013.md) ends with a documented **`numerical_failure` at the saved-evidence gate**. The lowest qualified historical reference for each of the nine cost failures is a v4 descending-path fit. None of these nine records saves its returned depth or bound multipliers. The v4 solver computes the KKT norm from `result.v`, then discards `result.v` when serializing. Its scalar saved optimality cannot reconstruct the signed multiplier contributions.

[Baseline verification](basketball-shared-timing-v7/prepare/baseline.json) · [cross-version manifest](basketball-shared-timing-v7/prepare/cross-version-manifest.json) · [diagnostic decision](basketball-shared-timing-v7/diagnose/diagnostic-decision.json) · [terminal package](basketball-shared-timing-v7/package/result.json) · [independent verification](basketball-shared-timing-v7/verification-final.json).

## Why this stops the plan

Section 2 requires recomputing signed objective, depth-multiplier, bound-multiplier and barrier contributions at the frozen states, including the lowest historical reference for each cost failure. It explicitly allows unavailable multiplier KKT at intermediate trace states, and says: “Missing required evidence blocks continuation.” These are missing **returned-state** multipliers. Neither central-path estimates, a newly solved fit, nor a slightly higher-cost v5 reference supplies the actual multipliers of the required immutable v4 states.

The [manifest](basketball-shared-timing-v7/prepare/diagnostic-manifest.json.gz) records the exact nine sources, lags, starts and missing fields. Both compressed exports and the original v4 state cache are checked. No historical fit was rerun and no coefficients were removed. This outcome concerns evidence completeness; it does not establish that conditioning or nuisance search would fail.

## Baseline and available diagnosis

The original v6 objective, depths, multiplier conversion, original-coordinate KKT and physical seed sanitation are independently reevaluated. The baseline reproduces 94/144 qualifications: 72 regularized and 22 data-only. All 50 failures reach 200 iterations. Five three-start disagreements, nine historical cost failures and three missing required data-only transfers remain. All nine cost failures are regularized groups 2/9/11 at outer lags −25, −20 and −19.

All 432 first/middle/returned v6 references and nine historical returned states are frozen before diagnosis. Parameter bytes are deduplicated within each identical problem, retaining every reference and source hash. [Compressed diagnostic records](basketball-shared-timing-v7/diagnose/states.json.gz) retain full singular spectra and deterministic repeated-subspace projectors, parameter/gradient projections, exact zero columns, inherited sampled-support classifications, observable trajectories, saved coefficient steps, linearized image changes, trust radii and barrier parameters.

Every v6 returned-state KKT is recomputed with actual multipliers. Intermediate multiplier KKT remains unavailable. Historical objective gradients and barriers are recomputed, but actual multiplier contributions and independently verified KKT remain null; saved v4 KKT norms are labeled separately. Historical barriers use v4's raw depth constraint, not v6's bounded transform. Maximum direct-objective disagreement is 4.00e-15; maximum depth disagreement is 3.56e-15.

| Group | Outer lag | Historical nuisance | v6 nuisance | Historical cost | v6 cost |
| --- | --- | --- | --- | --- | --- |
| 2 | −25 | −24.578836 | −0.161318 | 3.986748 | 4.009159 |
| 2 | −20 | −19.419952 | −0.604328 | 3.467314 | 3.488722 |
| 2 | −19 | −18.353266 | −0.703984 | 3.347918 | 3.363460 |
| 9 | −25 | −24.531552 | −0.178614 | 3.626136 | 3.641051 |
| 9 | −20 | −19.353574 | −0.657028 | 3.146353 | 3.162529 |
| 9 | −19 | −18.278887 | −0.765768 | 3.035791 | 3.047369 |
| 11 | −25 | −24.517997 | −0.184005 | 3.533458 | 3.546540 |
| 11 | −20 | −19.334371 | −0.672477 | 3.063903 | 3.078853 |
| 11 | −19 | −18.257373 | −0.783808 | 2.955626 | 2.966303 |

The v6 column uses the lowest returned v6 objective at each problem. The separated fitted nuisance offsets are consistent with distinct basins, subject to the missing historical stationarity evidence. They are not proof of global minima. Rank deficiency alone does not justify removing coefficients or predict a conditioning improvement.

## Implemented scope and unexecuted stages

The [v7 workflow](../../scripts/basketball_shared_workflow_v7.py), [diagnostic module](../../scripts/basketball_shared_diagnose_v7.py), [reporter](../../scripts/basketball_shared_report_v7.py) and [configuration](../../configs/basketball-rev2/timing-shared-v7.json) implement admission, diagnosis and blocker packaging. The CLI exposes all planned stage names and rejects scientific continuation after a failed predecessor. Separate conditioning, solver, basin-search and qualification adapters are **not implemented or invoked** after the required-evidence gate; this is a completed blocker investigation, not an operational v7 evaluator.

The [experiment freeze](basketball-shared-timing-v7/prepare/experiments-freeze.json) records both schedules and screening thresholds before fitting. [Development decisions](basketball-shared-timing-v7/package/development-decisions.json) report conditioning, scalar basin coverage and combined qualification as **unassessed**, with `passed: null`. The [search ledgers](basketball-shared-timing-v7/package/search-ledgers.json) distinguish 144 scheduled conditioning attempts, 7,344 initial conditional fits and 144 conditional-on-development combined outer searches; all executed counts are zero. Adaptive refinement/joint schedules are null because no curve exists from which to schedule them. Missing scheduled counts are retained, without pretending that unexecuted fits failed numerical tests.

The v5 analytical escape evidence is hash-bound, but [reuse](basketball-shared-timing-v7/diagnose/escape-reuse.json) remains unassessed and was not invoked. No ray grid was enlarged. Runtime projections, profiles, candidate, intervals and final protocol remain null. No selection or final validation was consumed; accepted timing remains null. Production remains immutable v2, with no real-data fitting.

## Validation and resources

The conservative first-action clock is 2026-09-08 01:50:50 UTC. The original deadlines are fixed at 30/60/105/120/165/195/220/240 minutes. The workflow checks the relevant absolute deadline and has an external watchdog that terminates the entire process group, including descendants whose leader has exited. Timeout packaging works before worker initialization. This run used one numerical process at a time for scientific diagnostics, with single-thread numerical libraries; no GPU jobs, downloads or training ran. Independent regression processes also remain below the eight-worker ceiling. [Resource projections](basketball-shared-timing-v7/package/resources.json) are unassessed because the admission blocker prevents benchmarking.

[Seven v7 regressions](basketball-shared-timing-v7/v7-tests.log) cover deadlines, policy preservation, missing multipliers, raw v4 barrier derivatives, tampered predecessor hashes, pre-initialization timeout packaging and process-group termination. The complete [Basketball suite](basketball-shared-timing-v7/basketball-tests.log), [seven budget tests](basketball-shared-timing-v7/budget-tests.log) and [three SelfCap tests](basketball-shared-timing-v7/selfcap-tests.log) are retained.

The [initial Basketball run](basketball-shared-timing-v7/basketball-initial-tests.log) hit one pre-existing wall-clock-dependent v6 test: its immutable config's investigation clock had expired before the intended corrupt-control assertion. The [v7 regression harness](../../scripts/basketball_shared_regressions_v7.py) fixes only that test's diagnostic-module clock to one second after its historical start. It keeps every original assertion, the actual deadline check and all immutable test/source/config bytes; it does not skip tests or alter the scientific clock.

The [independent verifier](../../scripts/basketball_shared_verify_v7.py) rechecks all 441 states, singular spectra, exact zero columns, 144 v6 returned KKT vectors, historical raw-cache multiplier omissions, original/current hashes, 667/667 partition, 72 edges, consumption markers and documentation links. Existing v2–v6 documentation, source bytes, configurations, corrections and evidence remain unchanged.
