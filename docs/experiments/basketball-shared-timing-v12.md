# Basketball v12: exact acceleration reference adjudication

The two independent exact references agree on all six selected acceleration
costs, all 36 paired gradient components and every retained signed summand.
The reference experiment passes [Plan 019](../../plans/plan_019.md). Both archived
floating implementations have gradient errors outside the inherited tolerance:
25 of 36 primary values and 17 of 36 independent values fail. All twelve saved
acceleration costs pass their objective tolerance. These results do not qualify
Basketball timing or establish the main reconstruction objective.

| Saved case / group | Exponent | Primary components outside / 6 | Independent components outside / 6 |
| --- | --- | --- | --- |
| conditional-03 / 2 | 4 | 3 | 0 |
| conditional-03 / 2 | 44 | 6 | 6 |
| conditional-10 / 9 | 4 | 2 | 0 |
| conditional-10 / 9 | 44 | 6 | 6 |
| conditional-16 / 11 | 4 | 2 | 0 |
| conditional-16 / 11 | 44 | 6 | 5 |

The table describes amplitude exponents in the original saved slots; no ray was
regenerated. [Comparisons](basketball-shared-timing-v12/comparisons.json) retain
exact normalized numerator/denominator strings for each reference, forward error
and allowed error, plus the saved binary64 values and tolerance bytes. Tolerances
remain `1e-10 + 1e-8*abs(saved_gradient)` and
`1e-10 + 1e-9*abs(saved_acceleration_cost)`, with binary64 multiplication then
addition before exact comparison. Acceleration cost is compared only with saved
acceleration cost, never the full data-plus-acceleration objective.

The first [A reference](basketball-shared-timing-v12/A-0.json) and
[B reference](basketball-shared-timing-v12/B-0.json), and their five numbered
successors per method, contain all 150 signed contributions and their absolute
sums for each selected partial. For example, group 2 at exponent 4 has a row-0 X
reference derivative about `1.1398328310624221e-8` with absolute summand sum about
`2011.7176781872975`. The exact rational records, rather than these display
approximations, decide agreement. Large cancellation and measured errors support
an arithmetic-conditioning concern; this experiment does not isolate an
individual floating operation as the cause or justify snapping values to zero.

## Provenance and independence

[Admission](basketball-shared-timing-v12/admission.json) pins all six physical
SHA-256 identities, all ten specified v11 input identities, historical/source
maps, original v10 chained journals and matching v11 entry streams. It retains
all 54 physical coefficients per state and both archived full gradients,
objectives and depth records in [inputs](basketball-shared-timing-v12/inputs.json).
Each saved result is finite and its retained minimum depth exceeds `1e-8`.
All 300 observations in each of the three cases have corrected time at least 2,
strictly past row-0/1 support ends 1.4 and 1.7999999999999998. Thus the image and
depth partials in these rows are exactly zero by support separation.

[Method A](../../scripts/basketball_acceleration_reference_v12.py) uses a rational
basis-derivative recurrence. [Method B](../../scripts/basketball_acceleration_control_v12.py)
independently differentiates the coefficient control polygon and propagates
adjoints through both difference operators. Both decode the original binary64
knots and all coefficients independently; neither calls SciPy or historical
evaluators. Each independently reproduces the pinned NumPy binary64 quadrature
and converts its 150 exact saved binary64 values to rational numbers. Their
[A](basketball-shared-timing-v12/A-setup.json) and
[B](basketball-shared-timing-v12/B-setup.json) quadrature bytes match. The exact
objective uses weight/150, without substituting a rounded squared residual scale.
Repeated endpoints and interior-knot conventions are covered by independent toy
expectations.

The [original v11 failures](basketball-shared-timing-v12/original-v11-failures.json)
are retained byte-for-byte. The remaining 57 failed v11 states, including the
intermediate ladder maximum, are outside this adjudication. Historical v11 A2/A3
remain failed. Accepted timing, production candidate and final-validation
protocol remain null, and `ready_for_full_screens=false` in the
[decision](basketball-shared-timing-v12/decision.json). Plan 015 thresholds,
200-iteration/200-distinct-state local limits, conditioning/scalar/combined-pilot
and evaluator gates are unchanged.

## Validation and consumption

Both permitted invocations of the fixed [twelve toy cases](../../tests/test_basketball_acceleration_reference_v12.py)
passed: [suite 1](basketball-shared-timing-v12/toy-suite-01.log) and
[suite 2](basketball-shared-timing-v12/toy-suite-02.log). The suite covers analytic
constant/linear/quadratic/cubic and nonuniform examples, repeated endpoints,
cancellation, support certificates, tampering, entry limits and owned child
interruption/timeout cleanup. No scientific fixture enters a test. The final
JSON-only package ownership checks were strengthened after suite 2 and inspected
and syntax-checked; no arithmetic, supervisor, ledger or test changed afterward,
and no third invocation occurred. [Readiness](basketball-shared-timing-v12/readiness.json)
and [execution sources](basketball-shared-timing-v12/execution-sources.json)
freeze final source, interpreter, NumPy and stdlib identities.

Admission finished 226.219442 seconds after the single authorized T0; readiness
finished about 742.160149 seconds after T0. The one supervised numerical invocation
consumed **1.026992965 seconds of 120**, including worker startup/imports, setup,
all calculations, journals and I/O. All 2 setup slots and all 12 bundle slots
are consumed; unused time permits no repeat. Exactly 72 gradient outputs and
12 cost outputs were retained. [Budget](basketball-shared-timing-v12/budget.json)
and [package validation](basketball-shared-timing-v12/package-validation.json)
reconcile ownership, sources, counts and timestamps. The worker exited 0 and was
reaped; [process identities](basketball-shared-timing-v12/processes.json) record
its actual namespace, distinct session and process group. No scientific job
remains running. Forbidden evaluator/depth/optimizer/ray/GPU/training/rendering,
network and installation entries are zero.

The [command record](basketball-shared-timing-v12/commands.json) includes the
initial JSON-only admission serialization error and its correction, the two toy
runs and final commands. The original admission-stage source is retained with
its matching hash. Historical Plan 018's 7.84522387 numerical seconds and
1498.589622 phase seconds, Plan 016's 405 attempts/six preflights, and the
24-hour training allocation with 22523.417254 charged seconds remain unchanged.
This phase charges zero training seconds. Commit IDs and final phase accounting
are recorded in the [implementation handoff](../continuous-improvement/20260908-plan016/iteration-003-implementation.md)
and [validation handoff](../continuous-improvement/20260908-plan016/iteration-003-validation.md).

The executed entry points were:

```bash
.local/envs/calibration-global/bin/python scripts/basketball_acceleration_reference_v12.py admit
.local/envs/calibration-global/bin/python tests/test_basketball_acceleration_reference_v12.py
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 MKL_NUM_THREADS=1 NUMEXPR_NUM_THREADS=1 .local/envs/calibration-global/bin/python scripts/basketball_acceleration_reference_v12.py run
.local/envs/calibration-global/bin/python scripts/basketball_acceleration_reference_v12.py package
```

These commands consume an immutable namespace and do not authorize reproduction
for free. A fresh planned allocation and namespace are required; do not modify
or delete the consumed marker to repeat this experiment.

## Next action and objective handoff

Recommend one bounded acceleration-gradient arithmetic correction and
qualification plan, using these saved exact references as the acceptance oracle.
The independent float path passes the three lower-amplitude states but fails the
three higher-amplitude state aggregates, so simply replacing the primary with
that path is not a validated general correction. Review should select one
cancellation-aware candidate from the identified arithmetic paths and require
honest rejection when its unchanged tolerance cannot be met. Do not broaden the
extreme-ray ladder or elect a production replacement from cost agreement alone.

Recommend budgeting the next Review and Plan stages at most 10 elapsed minutes each, one
fresh agent at a time and zero scientific entries. They should finalize a single
candidate and a concrete correction-validation allocation: recommended 30-minute
implementation phase, at most 120 numerical seconds, one single-thread worker
plus supervisor, six candidate acceleration/partial bundles on these same saved
states, zero new reference bundles, no adaptive candidates/rays or full
residual/depth calls, and at most two fixed toy suites. This proposal is not
executed here; the next saved plan must establish acceptance and any necessary
changes within applicable authorization. Reuse the now verified exact outputs
rather than consuming another exact-reference experiment.

That correction is a timing-evaluator prerequisite. A subsequent review must
return to the still-failed Basketball timing qualification gates and missing
Basketball reconstruction/quality/motion/speed/resource comparison. SC-01 and
SC-03 remain unmet; the supported SelfCap model/reload evidence and recommendation
under SC-02/SC-04 are preserved. This narrow reference success advances SC-05
evidence integrity and establishes no new complete reconstruction outcome.
