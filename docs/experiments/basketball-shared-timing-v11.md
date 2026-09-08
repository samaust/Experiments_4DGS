# Plan 018 — Saved v10 trajectory and displacement-ray diagnostic

The single diagnostic pass completed its schedule, but **independent verification
failed** on 63 regularized-control probe gradients. Plan acceptance A1 is met;
A2 and A3 fail. All 48 saved callback snapshots and all 24 analytical-limit pairs
passed their applicable comparisons. This is retained diagnostic evidence, not
an accepted timing solution or completion of the reconstruction objective.

[Plan 018](../../plans/plan_018.md), [admission](basketball-shared-timing-v11/admission.json),
[inputs](basketball-shared-timing-v11/inputs.json),
[execution identities](basketball-shared-timing-v11/execution-sources.json),
[decision](basketball-shared-timing-v11/decision.json), and
[independent verification](basketball-shared-timing-v11/verification.json) bind the result.
Admission used JSON/bytes/hashes only. Final execution sources were frozen after
regression readiness and before the worker; the separate admission-source hash
retains the earlier admission implementation identity.

## Saved failed trajectories

The sampled magnitude is maximum absolute normalized XYZ across original
observation times. The KKT norm is in original coefficient coordinates, with
actual saved multipliers; solver-coordinate optimality was compared only after
applying the saved transform. Four callback ordinals per input are retained in
[snapshots](basketball-shared-timing-v11/snapshots.json.gz).

| Group | Arm | Initial → returned sampled magnitude | Growth ratio | Returned objective | Original KKT infinity norm |
| --- | --- | ---: | ---: | ---: | ---: |
| 2 | baseline | 4.09954 → 13.57810 | 3.312 | 3.96323597 | 0.00055716137 |
| 2 | metric | 4.09954 → 1093.05435 | 266.629 | 3.94376360 | 0.0018840031 |
| 9 | baseline | 4.44951 → 14.37630 | 3.231 | 3.60557126 | 0.0045570042 |
| 9 | metric | 4.44951 → 1113.91138 | 250.345 | 3.58844503 | 0.0022050429 |
| 11 | baseline | 4.54950 → 12.88995 | 2.833 | 3.51476316 | 0.003654987 |
| 11 | metric | 4.54950 → 1039.81796 | 228.557 | 3.49711535 | 0.0052445154 |

The unchanged flag `final > max(1e6, 100*initial)` is false for every case.
The metric trajectories grow 229–267 times while remaining below the one-million
floor. Their original KKT norms remain above qualification. Conditioning lowered
the three weight-zero objectives but did not establish stationary solutions.

## Weight-one controls

These are different objectives and are not competitive-cost references for the
weight-zero rays. Their own returned objectives are used for all ray comparisons.

| Group | Arm | Returned magnitude | Returned objective | Original KKT infinity norm |
| --- | --- | ---: | ---: | ---: |
| 2 | baseline | 4.10197945 | 3.99413524247 | 1.5126191e-07 |
| 2 | metric | 4.10197863 | 3.99413524247 | 1.4179382e-07 |
| 9 | baseline | 4.45105432 | 3.63385477484 | 3.4495545e-07 |
| 9 | metric | 4.45105744 | 3.63385477483 | 1.367683e-07 |
| 11 | baseline | 4.55085638 | 3.54126406067 | 5.5380538e-07 |
| 11 | metric | 4.55085123 | 3.54126406067 | 4.3019751e-08 |

## Fixed displacement rays

`first` and `two-thirds` identify the saved operand subtracted from returned
coefficients. Signs apply after normalizing by maximum sampled XYZ displacement.
All 54 coefficients are preserved. The [ray manifest](basketball-shared-timing-v11/rays.json)
precedes every probe and limit entry. [Limits](basketball-shared-timing-v11/limits.json)
retain per-sample affine depths, exact-support certificates, transition scales,
acceleration terms, endpoint gaps and classifications. [Probes](basketball-shared-timing-v11/probes.json.gz)
retain the fixed 23-amplitude ladder, original depths and all feasible objectives.

| Conditional | Weight | Operand / sign | Analytical classification | First positive feasibility boundary | Finite ladder trend |
| --- | ---: | --- | --- | ---: | --- |
| conditional-00 | 0 | first / + | infeasible at infinity | 78218818 | higher than returned |
| conditional-00 | 0 | first / − | infeasible at infinity | 1093.0544 | higher than returned |
| conditional-00 | 0 | two-thirds / + | infeasible at infinity | 2842496.9 | higher than returned |
| conditional-00 | 0 | two-thirds / − | infeasible at infinity | 1093.0544 | indistinguishable |
| conditional-07 | 0 | first / + | infeasible at infinity | 1.2139353e+08 | higher than returned |
| conditional-07 | 0 | first / − | infeasible at infinity | 1113.9114 | higher than returned |
| conditional-07 | 0 | two-thirds / + | infeasible at infinity | 35833027 | higher than returned |
| conditional-07 | 0 | two-thirds / − | infeasible at infinity | 1113.9114 | indistinguishable |
| conditional-13 | 0 | first / + | infeasible at infinity | 95403394 | higher than returned |
| conditional-13 | 0 | first / − | infeasible at infinity | 1039.818 | higher than returned |
| conditional-13 | 0 | two-thirds / + | infeasible at infinity | 33535114 | higher than returned |
| conditional-13 | 0 | two-thirds / − | infeasible at infinity | 1039.818 | indistinguishable |
| conditional-03 | 1 | first / + | divergent objective | none | higher than returned |
| conditional-03 | 1 | first / − | infeasible at infinity | 50.979582 | insufficient finite probe trend |
| conditional-03 | 1 | two-thirds / + | infeasible at infinity | 4.1019786 | insufficient finite probe trend |
| conditional-03 | 1 | two-thirds / − | infeasible at infinity | 198.02195 | higher than returned |
| conditional-10 | 1 | first / + | infeasible at infinity | 2572.6564 | higher than returned |
| conditional-10 | 1 | first / − | infeasible at infinity | 63.958245 | insufficient finite probe trend |
| conditional-10 | 1 | two-thirds / + | infeasible at infinity | 4.4510574 | insufficient finite probe trend |
| conditional-10 | 1 | two-thirds / − | divergent objective | none | higher than returned |
| conditional-16 | 1 | first / + | infeasible at infinity | 838.69777 | higher than returned |
| conditional-16 | 1 | first / − | infeasible at infinity | 68.390979 | insufficient finite probe trend |
| conditional-16 | 1 | two-thirds / + | infeasible at infinity | 4.5508512 | insufficient finite probe trend |
| conditional-16 | 1 | two-thirds / − | divergent objective | none | higher than returned |

All twelve weight-zero rays eventually violate an original depth constraint;
none is a certified indefinitely feasible escape direction. Small finite cost
decreases on three forward two-thirds rays are within the prescribed competitive
tolerance and occur on eventually infeasible rays. They do not establish escape.
The six corresponding first/two-thirds positive directions can have feasibility
boundaries millions of normalized displacement units away; the fixed full
coefficient displacements contain small negative depth slopes elsewhere.
This evidence does not prove a finite minimizer exists, exclude other directions,
explain necessary solver behavior, or establish outer timing identifiability.

The controls have nine eventually infeasible rays and three feasible rays with
quadratically divergent acceleration cost. All 24 primary/independent analytical
classifications agree, with no cancellation/sign disagreement. Those individual
passed checks remain useful evidence, but do not turn the whole failed diagnostic
into a verified result.

## Verification failure retained without a rerun

Exactly 63 of 600 paired finite-slot checks fail, all in `G`; no snapshot,
objective, depth, multiplier/force, state identity, ray derivation or analytical
limit comparison fails. Each affected ray fails at every exponent 4, 6, …, 44:

- `metric/conditional-03/cold/ray/0/1`
- `metric/conditional-10/cold/ray/2/-1`
- `metric/conditional-16/cold/ray/2/-1`

The 367 failing gradient components and their actual allowed errors are in
[verification-failures.json](basketball-shared-timing-v11/verification-failures.json).
At amplitude 1e4, maximum component-error/tolerance ratios are 1.712, 2.392,
and 4.551 respectively. Across all failed components the largest ratio is
2,036,763.2. The inherited check is componentwise
`abs(independent − primary) <= 1e-10 + 1e-8*abs(primary)`; it was not loosened.
Large absolute maxima such as a 3.99e30 gradient difference at amplitude 1e44
are not, by themselves, the pass/fail rule. All objective and depth checks still
pass their own relative/absolute tolerances, even at large amplitudes.

The disagreement is concentrated in coefficient rows 0 and 1 in the retained
large regularized states. Cancellation in equivalent acceleration-gradient
formulas is a candidate explanation from source inspection, **not an established
cause**: no additional derivative computation was performed. Agreement between
these two implementations also does not identify either as ground truth at the
failed components. No failed arithmetic is relabeled as a mathematical unknown.

## Resources and validation

The numerical worker used **7.84522387 seconds** of its 120-second ceiling, including imports, reconstruction, primary arithmetic, independent reload, verification and I/O. Supervisor and worker both exited normally; the worker was waited/reaped, with `worker_stopped=true`.

| Per pass | Scheduled | Actual entries / outcomes |
| --- | ---: | --- |
| Saved snapshots | 48 | 48 feasible residual/depth bundles |
| Ray probes | 552 | 118 feasible residual bundles; 434 infeasible after depth |
| Depth/Jacobian | 600 maximum | 600 |
| Residual/Jacobian | 600 maximum | 166 |
| Analytical limits | 24 | 24 |
| Total owned slots | 624 | 624 completed; zero entry errors or interruptions |

Both passes together consumed 1,200 depth entries, 332 residual entries and 48
analytical-limit entries. There were zero optimizers, fits, Hessians, finite
differences, GPU jobs, training, rendering, downloads or installs. Single-thread
libraries and one worker plus supervisor were enforced. Slot capacity and unused
wall time cannot transfer to a rerun. [Budget](basketball-shared-timing-v11/budget.json)
and [primary](basketball-shared-timing-v11/primary.jsonl) /
[independent](basketball-shared-timing-v11/independent.jsonl) journals retain the counts.
No scientific correction or second pass was launched.

Twelve distinct toy tests passed in the final run, after two earlier 10-test
runs (32 total toy test invocations). They cover pre-entry caps/deadlines/physical
bytes, interruption accounting, skipped slots, tampered receipt/state/multiplier
ownership, returned identity, constructor/optimizer/Hessian exclusions, known
projective/acceleration limits, exact-support versus tiny nonzero slopes, depth
rejection, direct-worker denial and the historical growth floor. Tests neither
load scientific fixtures nor execute fits. See [final test log](basketball-shared-timing-v11/tests-03.log)
and [readiness](basketball-shared-timing-v11/readiness.json).

## Reproduction and next investigation

The frozen CLI operations are `admit`, `run`, and `package` with
`.local/envs/calibration-global/bin/python scripts/basketball_shared_trajectory_diagnostic_v11.py`.
The completed output directory is immutable: `admit` rejects it, `run` rejects
the consumed allocation, and `package` rejects overwriting its decision.
Reproduction requires a fresh explicit allocation and a separately planned output
namespace; the listed commands are the historical commands, not a free rerun.

Recommend one focused follow-on: isolate the regularized acceleration-gradient
arithmetic disagreement using the six already saved states at amplitudes 1e4
and 1e44 on the three failed rays. First inspect retained component evidence and
formulas, add a hand-authored cancellation regression, then independently evaluate
only those six fixed states once per implementation if a new plan authorizes it.
Proposed resources: 20 minutes implementation/validation/commit, at most 60 seconds
cumulative numerical wall, one single-thread worker plus supervisor, six states
per pass, at most 12 residual/gradient and 12 depth entries in total, zero new rays,
limits, optimizers, training or GPU work. Preserve inherited tolerances and retain
uncertainty if no independently justified arithmetic correction resolves it.
These resources are a recommendation for Review/Plan, not execution under the
spent Plan 018 pass. This investigation is not launched here.

The near-margin initialization finding remains a separate future topic.
`ready_for_full_screens=false`; accepted timing, production candidate and final
validation protocol remain null. Plan 015 conditioning, scalar, combined-pilot
and evaluator gates still precede Basketball preparation/reconstruction. SC-01
and SC-03 remain not met; no new saved-model/reload evidence changes SC-02 or
SC-04. This diagnostic is not overall objective attainment.
