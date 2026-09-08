# Plan 020 — Qualify one Decimal acceleration kernel on six retained states

## Objective, authority and boundary

Implement [iteration 004 recommendations](../docs/continuous-improvement/20260908-plan016/iteration-004-recommendations.md)
under the unchanged [objective](../docs/continuous-improvement/20260908-plan016/objective.md)
and [assessment](../docs/continuous-improvement/20260908-plan016/iteration-004-assessment-01-review.md).
Test one fixed arithmetic candidate against the saved exact v12 oracle. This
advances SC-05 and an evaluator prerequisite for SC-01/SC-03. Six-state kernel
qualification cannot establish production evaluator accuracy, timing acceptance,
or the main reconstruction objective. SC-02/SC-04 retain supported SelfCap evidence
and limitations. Acceleration weight zero makes this change algebraically inactive;
it cannot repair the historical weight-zero solver failures.

Read AGENTS.md, objective, status, latest assessment and this plan before work
and after context loss. Do not delegate or read `prompts` content. Parent owns
status, assessments and authorization; implementation owns its results and local
milestone commits. Preserve every historical source, scientific gate and artifact.
Obey the single safe same-command escalated retry, permission-failure stops and
git-failure stops. No implementation clock or scientific execution began in Plan.

AGENTS.md `b62f2ea` gives standing approval to these Review-recommended,
Plan-finalized limits in the explicitly resumed loop. Parent must compare them
with remaining applicable ceilings and save the approval basis, one T0 and all
absolute deadlines before dispatch. No routine budget question is required.

## Fixed allocations and deadlines

| Scope | Hard limit |
| --- | --- |
| Implementation admission, development, tests, packaging, validation and local commits | 1,800 elapsed seconds from parent T0 |
| Admission complete | T0 + 600 seconds |
| Final arithmetic/source freeze and passed toy readiness | T0 + 1,200 seconds |
| All numerical work, including cleanup, ended | T0 + 1,320 seconds |
| One scientific invocation, including imports, decoding, setup and I/O | 120 wall seconds within the phase |
| Candidate / setup / state bundles | 1 / 1 / 6, no replacements or repeats |
| Scientific outputs | Exactly 6 costs and 36 selected partials on complete execution |
| Toy suites | At most 2 invocations of the same fixed 12 cases below |
| Concurrency | One single-thread numerical worker plus its owning supervisor |
| New exact references, archived floating replay, full residual/depth/Jacobian, Hessian, finite difference | 0 |
| New states/rays/analytical limits, optimizer/local fits, pilots/full screens | 0 |
| Training/rendering/GPU/network/download/installation | 0 |

Use `.local/envs/calibration-global/bin/python` and standard-library Decimal,
serialization, hash and process tools only. Set OMP_NUM_THREADS,
OPENBLAS_NUM_THREADS, MKL_NUM_THREADS and NUMEXPR_NUM_THREADS to `1` before worker
startup. Do not import NumPy/SciPy or any historical scientific evaluator. The
candidate uses saved quadrature bytes; it does not regenerate quadrature.

Intermediate expiry stops dependent execution and leaves remaining phase time
for retention. The final deadline stops this plan's work. Failures consume entries
and elapsed time; unused seconds cannot buy another entry, candidate, toy suite,
or precision setting. Read-only next Review/Plan remains separately authorized
if the objective is unmet and no loop stop applies; no overall loop deadline is
inferred from historical suggested stage allowances.

Preserve Plan 016's 405 scheduled outcomes/six preflights; Plan 018's consumed pass,
7.84522387 numerical seconds and 1498.589622 phase seconds; Plan 019's two setups,
twelve bundles, two toy suites, 1.026992965 numerical seconds and 1125.515842279
final phase seconds. Preserve 22523.417254 charged training seconds under the
24-hour allocation and unchanged 7200-second method/scene ceilings. This plan
charges zero training seconds and cannot restart budget-stopped methods.

## New files and command contract

Create these surfaces only, plus parent-owned bookkeeping:

- `scripts/basketball_acceleration_decimal_v13.py`: pure Decimal candidate,
  binary64 decode/export and fixed-context validation; no oracle access.
- `scripts/basketball_acceleration_candidate_v13.py`: admission, source/readiness
  freeze, supervisor, durable ledger, worker dispatch and retained-data packaging.
- `tests/test_basketball_acceleration_candidate_v13.py`: twelve fixed toy cases.
- `docs/experiments/basketball-shared-timing-v13/`: immutable admitted input,
  oracle/source maps, allocation and entry journals, toy logs, commands,
  per-setup/bundle results, exact comparisons, budget, decision, package checks.
- `docs/experiments/basketball-shared-timing-v13.md`: measured result and limits.
- `docs/experiments/basketball-shared-timing-v13-integration.md`: mandatory
  source-based integration and remaining timing-gate map.
- Run-directory `iteration-004-implementation.md` and
  `iteration-004-validation.md` beneath
  `docs/continuous-improvement/20260908-plan016/`.

Expose `admit`, `ready`, `run`, `package` on the harness, with fixed output root
above and parent authorization
`docs/continuous-improvement/20260908-plan016/iteration-004-plan020-authorization.json`.
The test script owns a durable `toy-suite-01`/`02` entry record before unittest
dispatch. `ready` only freezes sources after a passing applicable toy run; it
performs no candidate calculation. An internal `worker` entry point requires
the owning supervisor's token/PID and exclusive consumed marker. Direct invocation
is rejected before setup. Record exact executed commands, failures and exit codes.
Reproduction requires a fresh planned allocation and namespace; these commands
cannot delete markers or authorize reruns.

## 1. Admit inputs and bind the retained oracle (SC-05)

Let V12 be `docs/experiments/basketball-shared-timing-v12/`. Before creating v13,
reject existing output paths and verify the following pinned files:

| V12 file | SHA-256 |
| --- | --- |
| inputs.json | `022552d14297dba718d7ee9f758e54c0827a72d8a246305cb3cec0f2c442f897` |
| admission.json | `1fe783903e0b83dcc421a172f0c5e7def8e970c74cba49220b10c52255058513` |
| A-setup.json | `5bfcfc40889306a87188a61c544f0af84e29ba6bb9647e521da800dec8b657bd` |
| B-setup.json | `77c30063aa6d382ca2415471156292893e90810b09b2da54d4e47f644946deb9` |
| comparisons.json | `7d3f6d4925e5fb0f9d6507c41a236dbc96b91cf3feffd1beffe9caacd5b071f1` |
| decision.json | `8e4211665ae25d09401241944b768f18db4e3ed00f150d7310fd7f9537167105` |
| package-validation.json | `59191f1d93dc7ddfc92e7ca54ebaec4d1d40779a413342129d383043dbb9a367` |
| execution-sources.json | `023fe33a35af2066829539f930c235ff7fca4ea0b1ec4dbcc054ef45369b9bc4` |
| budget.json | `713a664392cb16be80fccace52b2e0b252ad551b56f0473ca2cb0da716da6553` |
| entries.jsonl | `bfff876073c7e79b449c028a1e282a49805e1e9c80bed7a5bf8f5a30c550b4a8` |
| original-v11-failures.json | `672284899958ad7aa790e58d5a3d79d0291eb3a4034039561eb34c3f83cfb3b0` |

Bind all twelve oracle results to these planning-read identities:

| Index | A SHA-256 | B SHA-256 |
| --- | --- | --- |
| 0 | `359b8ca2ce9c6663f9354633cdd199b7bddd2fab9a7e3f4f3cf4ca392389ba9d` | `145ece8be66ec6cc751b662d17f5e8b5ea3c9e374801c41afefe09ef73ec4086` |
| 1 | `bf2aeb91ac8a80686641d8f059ec15a017e6a9fdcae517753042aee2a394fa21` | `e1061b356d2a0a6332f700942d8534e2d52ee37dacdbe5dd16e173c981d41354` |
| 2 | `d345a3f7e3fbf4e9368e80f6bf698bcb4ebb3fa2501c04ab6b985616c9de5774` | `22580810f78b675be319d6346483b9c7371ae7174e842ed5e7280dbfc634e657` |
| 3 | `55a5f266fc61a1e3ea2e54d9b904861b183002b506fca4933c33b33743c925e4` | `b47b97e478ee774934394a1ec0f1dbb88a6b76641acfb64ffb4df09329c3afc6` |
| 4 | `d0f8dc2e9d94121c8b19cc8af335882306f6424c122f3220f63057ac11616d2a` | `5ce140d62481248c67ed6e28d9d12fb6ba0674a5061ae08500ccf4ce2192bcd4` |
| 5 | `812250b5daeeae57e5e0304bac2bfea10e0dd472032376ca31f09d4c6ee2b4b8` | `5c7a4c671c016b16033bd890104227274560dd11e85921017a70750a48c00da9` |

Use the exact ordered slot/group/physical SHA table in [Plan 019](plan_019.md),
Work 1: groups 2/9/11, ray IDs `0/1`, `2/-1`, `2/-1`, each exponent 4 then 44.
Require all six original slot strings, case/group/ray ownership and 432-byte
physical identities. Decode 54 little-endian binary64 coefficients as 18x3,
all finite. Require 22 identical knot bytes, window `[50,149]`, spacing 10,
weight 1, no free offsets, offsets `{1:0,2:-25,3:-25}` and one group per case.
Require both saved setup knot and quadrature hex strings agree, 150 finite
quadrature values, and matching setup/bundle entry and completion ownership.

Verify V12 execution-source and original historical/v11 source maps against
current files, including its admission-source snapshot and readiness identities.
Retain a complete predecessor manifest including authorization, started/consumed,
readiness, final-integrity and result files. Check all retained A/B rational
costs, gradients, summands and absolute sums agree exactly, with normalized
positive denominators and retained sums matching saved totals. This is arithmetic
on saved outputs, not new reference evaluation. Check V12 passed package and
reference decision, exact-reference agreement and original failure counts.
Do not repair a mismatch, select replacements or import reference methods.

Reread the support certificates and saved observations: all corrected observation
times are at least 2 and strictly beyond coefficient-row 0/1 supports. Retained
depth minima are finite and above the original `1e-8` threshold. Recheck these
retained-data relationships only. The six selected acceleration partials are
full-objective partials solely because the associated image/depth derivatives
are structurally zero; the other 48 components remain unvalidated.

Write a minimal worker `inputs.json` containing only original state identities,
coefficient bytes, knots/quadrature bytes, weight and shape/window metadata.
Oracle values, basis/acceleration arrays, summands, old gradients and observations
belong in a separate admission/oracle manifest used only by the supervisor or
packager. The candidate worker never reads them. Source hashes may be verified
as bytes without importing historical modules. Reject paths containing `prompts`.
All admission steps have zero scientific entries.

## 2. Freeze the one candidate and its operation order (SC-05)

The candidate is an independent implementation of the control-polygon and
transpose formulation inspected in
[method B](../scripts/basketball_acceleration_control_v12.py), with no import of
that calculator. No square-root residual scaling, existing rounded basis, fused
multiply-add, compensated alternative, rational candidate, adaptive precision,
zero snapping or precision retry is allowed.

Create an explicit `decimal.Context(prec=80, rounding=ROUND_HALF_EVEN,
Emin=-999999, Emax=999999, capitals=1, clamp=0)` inside `localcontext` for setup
and each bundle. Enable traps for InvalidOperation, DivisionByZero, Overflow,
Underflow and FloatOperation; disable Inexact/Rounded traps and retain flags.
Do not inherit caller precision, rounding or traps. Exact `Decimal.from_float`
decoding is exempt from context rounding: retain the exact binary64 input value,
without unary-plus normalization or `Decimal(str(float))`. Use exact integer
constants. All subsequent arithmetic uses the fixed context; reject nonfinite
operands/results and invalid dimensions/domain/order. Export uses `float(d)` once
per final scalar; reject overflow/nonfinite binary64 and retain any finite
underflow/signed zero as produced, subject to unchanged acceptance tolerance.

One setup consumes its slot before decoding and mathematical construction:

1. Decode original U and Q; require nondecreasing U and Q, `n=len(U)-4`, `n>=4`,
   Q nonempty and every Q within `[U[3],U[n]]`. Scientific shape is fixed above.
2. In ascending i order, compute `da=U[i+4]-U[i+1]` for i=0..n-2 and
   `db=U[i+4]-U[i+2]` for i=0..n-3. Reject nonpositive denominators;
   `alpha[i]=3/da`, `beta[i]=2/db` in that order.
3. Set `W=U[2:-2]`. For each q in saved order, select the unique nonempty
   right-hand half-open span `s` in 1..n-3 satisfying `W[s]<=q<W[s+1]`.
   At `q==U[n]`, choose the last nonempty span ending there (left endpoint
   limit from inside the domain). Reject missing/ambiguous span or nonpositive
   span width. Compute `theta=(q-W[s])/(W[s+1]-W[s])`, then `left=1-theta`.
   Save `(s,left,theta)` in that order, with context metadata/flags.
4. Compute `scale=weight/Decimal(nacc)` then `twoscale=2*scale` once. Scientific
   weight is exactly 1. Store setup result once; subsequent bundles reuse it.

Each bundle consumes its slot before coefficient decoding, then performs:

1. For ascending i and axis X,Y,Z, `D[i,a]=alpha[i]*(C[i+1,a]-C[i,a])`;
   then ascending i/axis `E[i,a]=beta[i]*(D[i+1,a]-D[i,a])`.
2. Initialize `squares=0` and six gradient accumulators to Decimal zero.
   Iterate Q in saved order. For each axis in X,Y,Z compute separately
   `a=(left*E[s-1,a])+(theta*E[s,a])`, square as `a*a`, then add to `squares`
   in sample-major axis order. No reassociation or vectorized sum.
3. For each same sample/axis, `h=twoscale*a`. Initialize adjD entries for
   sorted distinct indices `{s-1,s,s+1}` to zero. Process pairs
   `(s-1,left*h)` then `(s,theta*h)`; for each pair compute
   `v=beta[i]*adjE`, then `adjD[i]=adjD[i]-v`,
   `adjD[i+1]=adjD[i+1]+v` in that order.
4. Initialize selected `adjC[0:2]` to zero. Visit adjD indices in ascending
   order; compute `v=alpha[i]*adjD[i]`, subtract from adjC[i] when i<2,
   then add to adjC[i+1] when i+1<2. Add each row contribution to
   `gradient[3*row+axis]` in row 0 then row 1 order. Retain the 150 signed
   contributions per selected component in the same bundle, with no replay.
5. After all samples, compute `cost=scale*squares`. Retain final Decimal
   cost/gradient as exact strings and `as_tuple` metadata; convert the seven
   final values once to finite binary64 and save little-endian bytes and
   display numbers. Save state, setup and execution-manifest hashes, timings,
   flags and consumed entry identity. No other candidate arithmetic follows.

All 54 coefficient operands affect acceleration; selecting six partial outputs
does not permit discarding input rows. Operation-order changes are source changes
and require remaining toy readiness before the single scientific invocation.
80 digits is a fixed engineering choice, not a proved bound. No runtime or solver
throughput claim is made until measured; v12's 1.026992965 seconds supports only
feasibility of this small workload.

## 3. Fixed toy readiness and durable execution (SC-05)

Freeze the twelve case definitions and test source before suite 1; both invocations
run the same complete suite. No selected states, scientific knots, old evaluator,
scientific fixtures or inherited scientific suites may be used. Use analytic
expectations; a test cannot invoke a reference calculator. A correction may use
suite 2 within the deadline, but no third invocation or corrected scientific rerun.
After both slots are consumed, an arithmetic/ledger/supervisor change lacks
readiness and prevents science. Pure retained-data packaging improvements may be
statically checked without rerunning mathematics; document any such change.

For cases 1–4 use U=`[0,0,0,0,1,1,1,1]`, Q=`[0,0.5,1]`, weight 1,
X controls below and zero Y/Z unless specified. Expected selected gradient is
row0 X,0,0,row1 X,0,0. Exact assertions apply where arithmetic is exact; for
nonterminating intermediates use a fixed Decimal absolute `1e-65` toy assertion
only, never replacing the scientific tolerance.

| Case | Fixed fixture and independent assertions |
| --- | --- |
| 1 | Constant controls all 7 in all axes: zero cost and all selected gradients. |
| 2 | X controls `[0,1,2,3]`: linear 3t, zero cost/gradient. |
| 3 | X controls `[0,0,1,3]`: quadratic 3t², acceleration 6, cost 36, selected X partials 36 and -36. |
| 4 | X controls `[0,0,0,1]`: cubic t³, acceleration 6t, cost 15, selected X partials 6 and 18. |
| 5 | Nonuniform U=`[0,0,0,0,1,2,2,2,2]`, X controls `[0,1,3,5,6]`, Q=`[0,0.5,1,1.5,2]`: linear 3t, zero acceleration, right span at 1 and final left limit at 2. |
| 6 | Repeated interior U=`[0,0,0,0,1,1,2,2,2,2]`, all controls zero, Q=`[0,0.5,1,1.5,2]`: span indices `[1,1,3,3,3]`, theta `[0,0.5,0,0.5,1]`, zero outputs; reject q outside domain and nonpositive difference denominator. |
| 7 | Add exact 2^40 to every X control in case 2: cancellation still algebraically zero; retain signed-zero behavior without snapping. |
| 8 | Decode binary64 0.1 and negative zero: exact Decimal identity/tuple and round-trip input bytes; reject nonfinite/short/wrong-hash input. |
| 9 | Change ambient precision/rounding/traps, run case 4, require same output bytes as fixed-context expected and ambient context restored; assert candidate context/traps exactly. |
| 10 | Export exact Decimal 0.1, -0 and a too-large finite Decimal: binary64 bytes match analytic 0.1/-0 expectations, overflow rejected; malformed output/nonfinite rejected. |
| 11 | Nonscientific dummy schedule: consume before callback failure; refuse second call, wrong state/source hash, direct worker, seventh entry and immutable output/allocation collisions without callback entry; retained failure remains charged. |
| 12 | Dummy sleeping child and dummy ledger: expired setup/entry deadline blocks entry; supervisor interruption and timeout preserve entry/partial output and reap owned session/process group within its short toy deadline. |

Toy case 12 uses no numerical worker and no other concurrent child. Record test
source/hash, entry/return times and pass/fail for both slots. Source manifest must
cover both scripts, tests, resolved interpreter, loaded stdlib files and Decimal's
extension implementation; record Decimal/libmpdec versions without installing.
Bind original admission source snapshot if harness changes after admission.

For science, validate all hashes, authorization/readiness/deadlines before creating
one exclusive `started.json`; it durably consumes the invocation even on launch
failure. Token-gate a worker in its own session. The supervisor owns the actual
PID/PGID/SID and namespace identity, handles SIGINT/SIGTERM, stops the entire child
group on timeout/interruption and reaps it. Do not mistake namespace PID for host
PID. Use numerical end `min(start+120,T0+1320)`, reserving two seconds within this
ceiling for TERM/KILL/reap. Persist start before spawn so imports are charged.

Append and fsync setup/entry records before each calculation, including expected
slot/physical bytes, source hashes, monotonic time and count; check time before
and after setup/bundles. Exactly one setup followed by bundle indices 0..5, no
skips/substitutions/repeats. Persist immutable `setup.json`, `candidate-0.json`
through `candidate-5.json` by exclusive create, then append completion/hash.
On any arithmetic/ownership/source error, stop the worker and preserve the
attempted prefix; never continue to a replacement state. Supervisor records
counts, failures, partial outputs, time, cleanup and worker-stopped evidence
even when no scientific output exists. A setup failure consumes its setup.

## 4. Compare saved binary64 outputs and package the result (SC-05)

`package` reads retained files and hashes only, imports no candidate module and
performs no new basis/acceleration/gradient calculation. For each of six costs
and 36 partials, let v be decoded saved candidate binary64 and g the common saved
rational oracle. Compute the allowed error in binary64 using separate multiply
then add: `allowed=1e-10 + rtol*abs(v)`, rtol=`1e-9` for cost, `1e-8` for partials.
Compare exactly
`abs(Fraction.from_float(v)-g) <= Fraction.from_float(allowed)`.
Retain normalized rational forward/allowed errors, v/allowed bytes, oracle
file/hash/component ownership and pass/fail. Costs use acceleration-only oracle.
Do not compare against the rounded display oracle or relax near-zero tolerance.

Reconcile invocation/setup/bundle entry and completion uniqueness, exact order,
time bounds, source/readiness/admission ownership and output hashes. Check Decimal
strings/tuples agree and saved binary64 serialization is self-consistent by
retained-data parsing only; do not re-evaluate signed Decimal summands to create
new mathematical evidence. Require full 6/36 finite output coverage, 42 passing
comparisons and all integrity/budget/readiness checks to label the kernel
`qualified_on_six_retained_states`. Any completed failed comparison means
`rejected`; missing output, invalid provenance or incomplete execution means
`incomplete` (retain any known failures). A passed cost never overrides a partial.

Keep separate package-integrity and scientific-qualification statuses, so a
properly retained rejection is still a reviewable implementation milestone.
Retain original v11 failures byte-for-byte and link the unchanged v12 result:
primary 25/36 gradient failures, independent 17/36, both costs 6/6 passing; other
57 failed v11 states remain unadjudicated and v11 A2/A3 remain failed. No historical
check is retrospectively passed. Decision fields `accepted_timing`,
`production_candidate`, `final_validation_protocol` remain null,
`ready_for_full_screens=false`, `main_objective_attained=false`.

Report measured setup, six bundle, total supervised numerical and final phase
times, imports/I/O accounting, consumed/returned counts, both toy slots, zero
forbidden work, exact commands, source provenance and reproduction requirements.
Perform task-related Markdown link/whitespace/diff and retained JSON/hash checks.
Create local validated milestones with explicit task paths, separate escalated
git add/commit and staged-diff inspection per AGENTS.md; no push/amend/history
rewrite. Include commit IDs and phase time including commits in handoffs. Stop
immediately on staging/commit failure. No worker/job may remain at handoff.

## 5. Mandatory source-only route to timing qualification (SC-01/SC-03/SC-05)

Publish the integration report even for rejection/incompletion, using source and
retained artifacts only. No production or historical evaluator integration is
authorized. Locate concrete functions and current formulas at these surfaces,
and identify future changes and evidence requirements rather than implementing:

| Surface | Required integration analysis |
| --- | --- |
| `basketball_shared_spline_v2.py`: setup/evaluate | Rounded basis A, square-root weight residual/J blocks; future coherent acceleration cost/full-gradient interface must consume original operands. Replacing six outputs or subtracting old rounded gradient from a rounded full gradient is insufficient. |
| `basketball_shared_accounting_v10.py`: CanonicalAdapter residual/fun/jac/hessian/set_transform, Ledger/NumericalEntries | Full cost and derivative cache ownership at one canonical state, all request orders including cold transform/Hessian/constraint first, durable charged entries, conditioned transform construction still depends on residual J. |
| `basketball_shared_solver_v10.py`: solve returned-state reporting | Independently computes objective `r@r` and gradient `2*J.T@r`; future callback and returned-state KKT must use the same qualified objective/gradient and owned state. |
| `basketball_shared_solver_v6.py`: exact_objective_hessian, depth/transform | Separate `2*weight/nacc*A.T@A` block, physical/canonical convention, data curvature and constraint chain rules; kernel has no Hessian evidence. |
| `basketball_shared_verify_v9.py`: direct_gradient/verify_row; `basketball_shared_trajectory_verify_v11.py`: independent evaluator/KKT | Separate direct acceleration derivative, independent data/depth/constraint verification and coordinate/multiplier convention; preserve independent arithmetic and actual entry observation in any future qualification. |

Spell out current `x=Dq`, `q=origin+Py`: `Gq=D.T Gx`,
`Gy=P.T Gq`, `Hq=D.T Hx D`, `Hy=P.T Hq P`; the existing v6 Hessian
already returns q coordinates and must not be scaled twice. Raw depth and
bounded-depth chain rules and multipliers must preserve original-coordinate
stationarity; returned conditioned bound multipliers use inverse-transpose.
Distinguish toy-only, six unsupported-row partial evidence, historical actual
callback evidence and still-required full-state evidence for every surface.

Retain this future gate table and original [Plan 015](plan_015.md) section 6/8:

| Gate | Required future evidence and present gap |
| --- | --- |
| Applicable evaluator integrity — SC-01/05 | Full cost/gradient/Hessian/constraints/KKT consistency on actual benchmark states and coordinate paths. Six partials do not qualify it; v11 remains failed. |
| Focused solver qualification — SC-01/03 | All required targets/dependencies qualify within both 200-iteration and 200-distinct-state caps; controls/costs and all three paths agree; no missing seeds or unresolved transform/support/growth/initialization/stopping failures. V10 failed. |
| Full conditioning — SC-01/03 | Original 144 attempts on 48 problems/three paths: preserve 94 v6 qualifications/costs, recover at least 25/50 across groups, median KKT ratio <=0.1. No qualified new policy/screen exists. |
| Independent scalar screen — SC-01/03 | Original 48 problems, 7344 initial path attempts and frozen inclusive 0.05/0.01 refinements; all conditional fits/paths and nine basin/cost comparisons pass. |
| Combined pilot/evaluator qualification — SC-01/03 | Both full screens pass before fresh combined pilot; all 144 complete outer paths, transfers/basins and historical cost controls qualify, then separately planned evaluator/selection/final-validation gates. |
| Basketball reconstruction/comparison — SC-01/02/03/04/05 | Accepted timing, shared validated preparation/split and training-only initialization, complete saved/reloaded supported models and time/view renders, quality/motion/speed/resource comparison within remaining method/scene ceilings. Basketball results absent. |

Preserve KKT `<=1e-6`, qualification depth `>1e-7`, objective agreement
`1e-6 + 1e-4*max(abs(F1),abs(F2))`, all coefficients/null directions,
data partitions and original scientific gates. Also report the v10 six missing
directional seeds/eight path disagreements, conditioning median KKT ratio
`0.2419725969` and weight-zero cold failures in all three groups; retain distinction
between final policy's 50/81 qualifications, preserved 47 controls, repaired
feasibility and still-unqualified cold starts. Acceleration arithmetic cannot
solve the zero-weight strata.

On kernel qualification, recommend that next Review select a finite, consistent
full-component integration/evaluator-qualification experiment on retained actual
v10/v11 operating states, with cost/gradient/Hessian/KKT/ownership validation and
an explicit weight-zero control stratum. It must finalize concrete state counts,
implementation scope and budgets in the next Plan before execution; no solver
fit or integration evaluation is allocated here. On rejection, use saved forward
errors and source order to decide a concrete defect-correction qualification or
rejection of this scheme, tied to the same failed evaluator gate. On incomplete
execution, identify its precise prerequisite blocker. Do not automatically raise
precision or propose another extreme ladder. Any later extreme-state study must
explain which timing-gate decision it changes. The report must choose one next
action from its actual outcome and identify the still-failed timing gate it advances.

## Acceptance and handoff

| ID | Plan acceptance and criterion mapping |
| --- | --- |
| A1 | Six exact identities, complete bound common oracle and source/support provenance, no unexplained mismatch or historical mutation; SC-05 prerequisite for SC-01/03. |
| A2 | Frozen candidate with applicable passed fixed toy readiness, one owned setup/six owned bundles at most, immutable complete or honestly partial outputs and enforced limits; SC-05. |
| A3 | All available outputs adjudicated by exact unchanged tolerance; six-state qualification only if all 42 pass with complete valid execution; rejection/incompletion honestly recorded; SC-05 prerequisite for SC-01/03. |
| A4 | Package/source/ownership/budget checks, report, source integration/gate map, concrete outcome-linked next action, validated local milestone and no jobs; SC-05 while preserving SC-02/04. |

Report acceptance status and evidence for every item; distinguish completed
implementation from successful kernel qualification and from the unchanged main
objective. SC-01/SC-03 remain not met under every possible six-state outcome.
Parent reassesses all criteria and, absent a stop, automatically advances to
fresh Review after this handoff. A completed plan or local commit is a checkpoint.
