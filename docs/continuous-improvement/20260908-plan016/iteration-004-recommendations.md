# Iteration 004 review — one arithmetic candidate, then return to timing gates

Recommend one **fixed 80-digit Decimal acceleration calculation** on the same six
saved states, judged against the already verified exact references. Use the
differentiated control polygon and transpose propagation throughout; increasing
precision only at the last summation cannot repair rounded intermediate operands.
This is a bounded kernel qualification, with an explicit solver-integration
handoff. It does not elect a production evaluator or explain the weight-zero
solver failures. Do not expand the extreme-ray ladder by default.

This review read [AGENTS.md](../../../AGENTS.md), [objective](objective.md),
[status](status.md), [latest assessment](iteration-003-assessment-03-implementation.md),
[Plan 019](../../../plans/plan_019.md), the
[implementation](iteration-003-implementation.md) and
[validation](iteration-003-validation.md) handoffs, and the retained evidence and
source listed below. Only this recommendations file is written; the parent owns
assessment, status, authorization and commits. No delegation or git mutation.

## What the saved evidence establishes

The [v12 report](../../experiments/basketball-shared-timing-v12.md),
[comparisons](../../experiments/basketball-shared-timing-v12/comparisons.json),
[decision](../../experiments/basketball-shared-timing-v12/decision.json), and
[package validation](../../experiments/basketball-shared-timing-v12/package-validation.json)
establish agreement of two exact formulations on six costs, 36 partials and all
paired signed summands. Every archived acceleration cost passes its inherited
tolerance. The gradient result is different:

| Original case / group | Exponent | Primary outside / 6 | Independent outside / 6 |
| --- | --- | ---: | ---: |
| conditional-03 / 2 | 4 | 3 | 0 |
| conditional-03 / 2 | 44 | 6 | 6 |
| conditional-10 / 9 | 4 | 2 | 0 |
| conditional-10 / 9 | 44 | 6 | 6 |
| conditional-16 / 11 | 4 | 2 | 0 |
| conditional-16 / 11 | 44 | 6 | 5 |

All 18 selected independent components pass at exponent 4; 17/18 fail at exponent
44. The primary totals are 7/18 and 18/18 failures respectively. Replacing the
primary with the archived independent binary64 calculation is therefore rejected
as a general correction. Agreement of costs alone cannot qualify derivatives.

The retained rational summands show substantial cancellation. For example,
[A-0](../../experiments/basketball-shared-timing-v12/A-0.json) gives row-0 X about
`1.1398328310624221e-8` from absolute summands totaling about `2011.7176781872975`.
Across the 36 retained components, the largest ratio of the saved absolute sum
to the absolute saved exact derivative is about `2.420656648e11` (group 2,
exponent 44, row-1 X). These are summaries of retained rational values, not new
derivative evaluations or a new acceptance threshold. They support using more
precision throughout the calculation. They do not isolate one faulty operation,
prove a precision bound, or justify zeroing small derivatives.

[Admission](../../experiments/basketball-shared-timing-v12/admission.json) and
[inputs](../../experiments/basketball-shared-timing-v12/inputs.json) certify that
every observation time is at least 2, strictly beyond the supports of coefficient
rows 0/1. Their image and depth partials are exactly zero. Thus the six selected
acceleration partials are also the full-objective partials for these cases. This
certificate does not establish accuracy of the remaining 48 components.

The [v11 report](../../experiments/basketball-shared-timing-v11.md) retains 63
failed gradient states; v12 adjudicates six. The other 57, including the ladder's
largest discrepancy, remain unadjudicated. Historical v11 A2/A3 remain failed.
The passed 48 actual callback comparisons and 24 analytical-limit comparisons
are useful within their recorded scope. No result establishes a finite minimizer,
absence of all escape directions, or accepted timing.

## Critical assessment of the proposed correction

The v12 proposal is useful as a small arithmetic acceptance experiment, with
three necessary boundaries:

1. **Use original operands at higher precision.** The
   [primary evaluator](../../../scripts/basketball_shared_spline_v2.py) forms
   `A @ C`, scales residuals/Jacobian entries by `sqrt(weight/nacc)`, then uses
   sparse `2*J.T@r`. The
   [independent evaluator](../../../scripts/basketball_shared_trajectory_verify_v11.py)
   evaluates differentiated scalar coefficient splines and uses
   `2*weight/nacc * A.T @ acceleration`. Both fail against the exact oracle.
   Merely using compensated summation, a wider accumulator on either path's
   existing binary64 arrays, or the independent path unchanged has no validated
   accuracy guarantee. Select one fixed candidate instead of testing a menu.
2. **A six-partial kernel is not a solver correction.**
   [CanonicalAdapter](../../../scripts/basketball_shared_accounting_v10.py)
   computes the objective and gradient from residuals and `2*J.T@r`; the
   [solver's returned-state report](../../../scripts/basketball_shared_solver_v10.py)
   independently recomputes that gradient for KKT. The
   [exact Hessian implementation](../../../scripts/basketball_shared_solver_v6.py)
   adds `2*weight/nacc * A.T@A`, and the
   [independent verifier](../../../scripts/basketball_shared_verify_v9.py)
   has another acceleration-gradient path. A future integration must consistently
   address cost, full gradient, Hessian, coordinate transforms, KKT reporting,
   independent verification and charged cache ownership. Substituting six output
   values after the old evaluator, or subtracting a rounded erroneous gradient
   from a rounded full gradient, is not this integration.
3. **Acceleration accuracy does not resolve the principal data-only failures.**
   The [v10 benchmark](../../experiments/basketball-shared-timing-v10.md) had six
   missing directional seeds and eight conditional path disagreements. The
   conditioning arm's six iteration-limit targets include weight-zero cold
   failures in all three groups; its median KKT ratio was `0.2419725969`, above
   the unchanged `0.1` gate. Acceleration weight zero makes this correction
   algebraically inactive. The v11 metric cold trajectories grew 229–267 times
   and still failed KKT, while all twelve tested weight-zero directions were
   eventually infeasible. These findings do not identify an effective solver
   adaptation. A claim that the proposed kernel will recover those targets
   would be unsupported.

The final initialization-only v10 policy qualified 50/81 outcomes and preserved
all 47 archived qualified controls. All three repaired cold starts became feasible
but none subsequently qualified; the separate stopping arm qualified only two of
its three targets. Preserve these distinctions when choosing the next solver
intervention: feasibility, derivative accuracy and optimizer qualification are
separate requirements.

Accordingly, accept the report's small single-candidate workload, but describe
the outcome as **qualified on six retained states** or **rejected/incomplete**.
Do not describe it as a production correction, mark historical verification as
passed, or rerun the other 57 extreme states merely to complete a table. Preserve
the evidence needed for a later applicable evaluator gate.

## Recommendations and acceptance

**R1 — Reuse and bind the exact oracle (SC-05; prerequisite for SC-01/SC-03).**
Admit the exact six physical identities and order from Plan 019: groups 2/9/11,
original ray IDs ending respectively `ray/0/1`, `ray/2/-1`, `ray/2/-1`, each at
exponents 4 and 44. Read all 54 little-endian binary64 coefficients directly from
saved bytes. Preserve original binary64 knot and quadrature bytes, window
`[50,149]`, 18 coefficients, weight 1 and 150 samples. Reuse the saved quadrature
bytes after checking both reference setups agree; do not regenerate quadrature,
rays, states, image observations or a floating basis.

Bind both A/B exact result files, their setup files, comparisons, admission,
inputs, execution-source manifests and original provenance. Require exact A/B
agreement and matching state ownership using retained-data checks only. Reread
the structural support certificate and original failed comparisons. Reject
mismatch or output collisions; do not repair historical sources or select a
replacement state. Freeze a fresh v13 namespace and candidate source before any
scientific entry. The candidate worker receives only original input operands,
never saved reference gradients, summands, accelerations or basis arrays.

Acceptance: six exact identities admitted, complete oracle/provenance map, no
unexplained mismatch, unchanged predecessor hashes. Resources: source/JSON/hash
inspection within the recommended phase below; zero scientific entries for R1.

**R2 — One fixed Decimal candidate (SC-05; SC-01/SC-03 prerequisite).**
Use standard-library `decimal` with a local context fixed before execution to
precision 80 and `ROUND_HALF_EVEN`, with explicit finite/error handling. Decode
binary64 values with exact float-to-Decimal conversion, not short decimal
renderings. Retain those exact input values; every subsequent numerical operation
in the candidate uses the fixed context. The precision is an engineering choice
with ample headroom relative to the observed cancellation, not a proved bound or
new quality threshold. No adaptive precision increase, candidate switch or retry.

Use the independently checked control-polygon formulation from
[Plan 019](../../../plans/plan_019.md) and
[method B](../../../scripts/basketball_acceleration_control_v12.py), implemented
in the new candidate rather than importing the exact-reference calculator:

- Compute `alpha[i]=3/(U[i+4]-U[i+1])` and
  `beta[i]=2/(U[i+4]-U[i+2])` from exact-decoded knots in Decimal arithmetic.
- Form `D[i]=alpha[i]*(C[i+1]-C[i])` and
  `E[i]=beta[i]*(D[i+1]-D[i])`. Evaluate the degree-one derivative spline by
  the fixed interval/endpoint rules, retaining all coefficient inputs.
- Compute `weight/nacc * sum(acceleration**2)` directly, without a rounded
  squared square-root scale. Propagate `2*weight/nacc * acceleration` through
  interpolation and both difference operators in Decimal, collecting exactly
  row-major partials 0–5. Freeze all operation orders.
- Convert the final cost and six partials to finite binary64 once for the proposed
  interface. Retain those bytes and the final Decimal values; signed Decimal
  summands may be retained within the same bundle, with no second evaluation.

One setup constructs factors and interpolation operands for the common knots and
quadrature. Exactly six bundles each return one cost and six partials, in fixed
order. All arithmetic, including setup and imports, is charged inside one
supervised invocation. No scientific exact-reference calculation is repeated.

Acceptance: compare the six candidate binary64 costs and 36 candidate binary64
partials with the common saved rational oracle. Use exactly the v12 tolerance
rule, substituting the candidate saved binary64 value for `v`:
`abs(Fraction(v)-g) <= Fraction.from_float(1e-10 + rtol*abs(v))`, where multiplication
then addition occur in binary64, `rtol=1e-8` for gradients and `1e-9` for cost.
Retain exact errors and allowed errors. Every comparison must pass for the
six-state kernel qualification. Missing outputs, nonfinite values, source
mismatch or any failed component mean incomplete/rejected qualification; a
passed cost never overrides a failed partial. No new numerical threshold.

Resources: one setup and six candidate bundles, six costs and 36 partials total,
at most 120 wall seconds including imports/setup/I/O. Zero full residual/depth,
finite-difference, Hessian, reference, optimizer or new-state entries.

**R3 — Validate and retain a reviewable milestone (SC-05; preserve SC-02/SC-04).**
Freeze at most 12 hand-authored toy cases before the first suite, with at most
two suite invocations. Cover analytic constant/linear/quadratic/cubic behavior,
nonuniform/repeated-knot endpoint rules, a cancellation example with an exact
zero justified by algebra, exact binary64 decoding, fixed-context isolation,
final binary64 export, state/hash tampering, consumed-slot/collision rejection,
deadline/entry enforcement and child interruption cleanup. Combine related
assertions into the fixed cases; do not add scientific fixtures or run inherited
scientific suites as uncharged tests. Use independent analytic expectations.

Preserve counts at entry, failures and partial results, one allocation marker,
immutable results and source manifests. Package from saved outputs only. Include
the original v11/v12 outcomes unchanged, measured setup/bundle/total worker time,
final phase time including commits, exact commands and explicit reproduction
requirements. Check task-related links/diff and make local commits under AGENTS.md.
If both toy slots are consumed, a later arithmetic change lacks test readiness;
do not give it an uncharged scientific run.

Acceptance: the permitted tests and package provenance/ownership/budget checks
pass; worker is reaped; no job remains; result clearly states the scientific
pass/failure boundary. Resources: at most two fixed 12-case toy suites and
read-only packaging within the phase; no additional scientific slots.

**R4 — Publish the route back to actual timing qualification (SC-01/SC-03;
SC-05, preserving SC-02/SC-04).** The same implementation handoff must include
a source-based integration map for all cost/gradient/Hessian/KKT/verifier paths
above, including physical-to-canonical-to-conditioned chain rules and durable
entry ownership. It must identify which parts have only toy or six-component
evidence and which still need actual-state validation. Do not install the new
kernel in historical or production sources in this narrow phase.

Include the following unresolved gate table and prioritize the next review around
it. This is a mandatory artifact-only return to the timing task, not permission
to execute later stages under this allocation:

| Gate / criterion | Required future evidence; current gap |
| --- | --- |
| Applicable evaluator integrity, SC-01/05 | Full cost/gradient/Hessian/constraint/KKT consistency on the actual benchmark states and coordinate paths; six unsupported-row partials do not establish it. Historical v11 remains failed. |
| Focused solver qualification, SC-01/03 | Plan 015 section 6: all required targets/dependencies qualify within both 200 caps, controls/costs and all three paths agree, no missing seeds, unresolved transforms/support/growth or initialization/stopping failures. V10 fails these conditions. |
| Full conditioning, SC-01/03 | Original 144 attempts: preserve 94 v6 qualifications/costs, recover at least 25/50 across groups, median KKT ratio at most 0.1. No newly qualified policy or fresh screen exists. |
| Independent scalar screen, SC-01/03 | Original 48 problems, 7,344 initial path attempts plus frozen inclusive 0.05/0.01 refinements; every conditional fit/path and all nine basin/cost comparisons pass. |
| Combined pilot and evaluator qualification, SC-01/03 | Both full screens pass before the fresh combined pilot; all 144 complete outer paths and required transfers/basins qualify, then the separately planned evaluator/selection/final-validation gates. |
| Basketball reconstruction and comparison, SC-01/02/03/04/05 | Accepted timing and shared validated split/preparation, training-only initialization, supported methods' complete saved/reloaded models and time/view renders, quality/motion/speed/resource comparison within remaining method/scene allocations. No Basketball result exists. |

Retain Plan 015's original KKT `<=1e-6`, qualification depth `>1e-7`, objective
agreement `1e-6 + 1e-4*max(abs(F1),abs(F2))`, all coefficients/null directions,
data partitions and original scientific gates. The accepted timing, production
candidate and final-validation protocol stay null, and full-screen readiness
stays false. A kernel pass permits planning integration; it does not waive gates.

On a kernel pass, the next Review should use source and retained actual v10/v11
operating-state evidence to select one finite integration/qualification plan,
with the unchanged failed solver strata and weight-zero limitation explicit.
On a failure, it should decide from the retained forward errors whether the
candidate has a correctable implementation defect or the proposed scheme is
rejected; do not automatically increase precision or add another ray ladder.
In either case it must recommend a concrete next experiment tied to a failed
timing gate, with fresh allocations finalized by Plan. A second large-ray study
needs an explicit explanation of which gate decision it changes; collecting more
extreme-state examples alone is not a recommendation.

Acceptance: the handoff contains this gate map, concrete integration surfaces,
the measured candidate result and its limits, and one outcome-dependent next
action for the next Review. Resources: source/retained-data inspection only,
within the same phase; zero integration evaluations, local fits or GPU work.
The next Review/Plan may proceed under standing approval with zero scientific
entries until its new plan is finalized; do not invent an overall loop deadline
from the previous report's suggested ten-minute stage allowances.

## Recommended new allocation for Plan to finalize

| Scope | Recommended hard limit |
| --- | --- |
| Implementation admission/development/tests/packaging/validation/local commits | 1,800 elapsed seconds from one parent-recorded T0 |
| Admission complete | T0 + 600 seconds |
| Final arithmetic source and toy readiness frozen | T0 + 1,200 seconds |
| All numerical work ended | T0 + 1,320 seconds |
| Candidate numerical invocation, imports/setup/I/O included | 120 wall seconds, within the phase |
| Candidate choices / scientific setup / state bundles | 1 / 1 / 6; no replacements or repeats |
| Scientific output | 6 costs and 36 selected partials; optional same-bundle summands |
| Concurrency | One single-thread numerical worker plus owning supervisor; no other numerical workers |
| Toy validation | At most 2 invocations of at most 12 frozen toy cases |
| New references / old floating evaluator replay / residual / depth / Hessian / finite difference | 0 |
| Rays / limits / optimizer / local fits / pilot / full screens | 0 |
| Training / rendering / GPU / network / downloads / installation | 0 |

Use the installed `.local/envs/calibration-global/bin/python` and standard-library
Decimal/serialization/process tools. No dependency installation or accelerator is
needed. Set the usual numerical-library thread environment variables to 1 before
worker startup. Reuse validated supervision/accounting patterns without importing
historical scientific evaluators. One setup and six short 18-control/150-sample
bundles are plausibly within 120 seconds given v12's complete two-method exact
pass took 1.026992965 seconds; this is a feasibility estimate, not a measured
Decimal runtime or a solver-throughput forecast. Preserve timing uncertainty.

An intermediate deadline stops its dependent execution, leaving remaining time
for retention. The final deadline stops this plan's work. Neither a consumed
attempt nor a deadline resets; failures remain charged, and unused time permits
no extra entries. Under AGENTS.md `b62f2ea`, eligible Review-recommended,
Plan-finalized allocations have standing approval in the explicitly resumed
loop. The parent must compare the saved plan with applicable ceilings and record
that approval basis before dispatch. No routine budget question is necessary.

Historical charges remain: Plan 016's 405 scheduled outcomes and six preflights;
Plan 018's 7.84522387 numerical seconds, 1498.589622 phase seconds and consumed
pass; Plan 019's 2 setups, 12 bundles, 2 toy suites, 1.026992965 numerical seconds
and 1125.515842279 final phase seconds. These allocations are not reused.
The 24-hour training ledger retains 22523.417254 charged seconds with unchanged
7,200-second method/scene limits and no redistribution. This plan charges zero
training seconds and cannot restart budget-stopped SelfCap methods.

## Evidence identities and review closure

Read-only hashing during this review retained these anchors for Plan admission;
the new plan should bind the complete A/B result and predecessor manifests too:

| v12 path relative to its result directory | SHA-256 |
| --- | --- |
| inputs.json | `022552d14297dba718d7ee9f758e54c0827a72d8a246305cb3cec0f2c442f897` |
| comparisons.json | `7d3f6d4925e5fb0f9d6507c41a236dbc96b91cf3feffd1beffe9caacd5b071f1` |
| decision.json | `8e4211665ae25d09401241944b768f18db4e3ed00f150d7310fd7f9537167105` |
| package-validation.json | `59191f1d93dc7ddfc92e7ca54ebaec4d1d40779a413342129d383043dbb9a367` |
| budget.json | `713a664392cb16be80fccace52b2e0b252ad551b56f0473ca2cb0da716da6553` |
| A-setup.json | `5bfcfc40889306a87188a61c544f0af84e29ba6bb9647e521da800dec8b657bd` |
| B-setup.json | `77c30063aa6d382ca2415471156292893e90810b09b2da54d4e47f644946deb9` |

SC-01 and SC-03 remain not met. SC-02 and SC-04 retain the supported SelfCap
evidence and recommendation; SC-05 retains the measured provenance/accounting
evidence and historical limitations. The main objective remains unmet.

Review used source reading, JSON/gzip inspection, hashes, and arithmetic summaries
of saved rational values only. No scientific basis/gradient/solver/pilot
evaluation, scientific test, GPU, network or install occurred. Some exploratory
reads used nonexistent guessed filenames and the unavailable `python` alias;
these were ordinary missing-path/command errors, with no state changes or
permission denial. Subsequent reads used actual filenames and `python3`.
No sandbox/permission failure or git mutation occurred. Read-only git status/diff
checks and a Markdown link/whitespace check passed; all 24 local links resolve.
No process/job was
started beyond completed read-only commands; no jobs remain to stop.
