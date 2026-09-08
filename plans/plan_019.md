# Plan 019 — Exact references for six retained acceleration-gradient states

## Purpose and authority

Implement the [iteration 003 review](../docs/continuous-improvement/20260908-plan016/iteration-003-recommendations.md)
for the unchanged [objective](../docs/continuous-improvement/20260908-plan016/objective.md)
and [assessment](../docs/continuous-improvement/20260908-plan016/iteration-003-assessment-01-review.md).
Adjudicate the six selected components of each of six saved physical states
against two independently expressed exact acceleration calculations. This is a
prerequisite for Basketball timing/preparation (SC-01), its missing measured
comparison (SC-03), and reproducible evidence (SC-05). It does not qualify timing,
produce a reconstruction, or complete the main objective. SC-02/SC-04 retain
their existing supported SelfCap evidence and limitations.

The plan-specific limits below receive standing approval under AGENTS.md at
`b62f2ea` in the explicitly resumed loop. Before implementation dispatch, the
parent must compare them with applicable ceilings, save the approval basis and
one T0/deadline record, and reread objective/status/latest assessment. Historical
Plan 018 approval-request text does not require renewed routine confirmation.
Planning has started no implementation clock or scientific execution.

Read AGENTS.md, objective, current status, latest assessment and this plan before
implementation and after context loss. Do not delegate or read `prompts` content.
Parent owns status/assessments/authorization. Preserve historical evidence and
sources; obey the single safe escalated retry and stop rules and git-failure
stops. This plan is a new allocation, never a transfer of Plan 018/016 capacity.

## Fixed scope and enforceable limits

| Allocation scope | Hard ceiling |
| --- | --- |
| Implementation inspection through admission, development, tests, packaging, validation and local commits | 1,800 elapsed seconds from one parent-recorded T0 |
| Scientific setup and exact-reference invocation, including imports and numerical I/O | 120 wall seconds, included in the phase |
| Scientific physical states | Six fixed retained byte strings; no regenerated states |
| Reference bundles | Six per method, 12 total; each returns acceleration cost and six partials once |
| Reference gradient outputs | 72 scalar values, paired into 36 exact-reference checks |
| Reference setup | One independently constructed knot/quadrature/basis setup for method A and one knot/quadrature/difference setup for method B |
| Concurrency | One single-thread numerical worker plus one supervisor; no additional run worker |
| Toy validation | At most two suite invocations, at most the 12 fixed cases below per invocation; no scientific fixtures |
| Data/image residual or gradient, depth/Jacobian, full floating evaluator replay | Zero entries |
| Finite differences, Hessians, new rays, analytical limits, optimizers or local fits | Zero entries |
| Real-data fits, full screens, training, rendering, GPU, network, installs/downloads | Zero |

Admission must finish by T0+600 seconds; implementation/source freeze and toy
readiness by T0+1200; all numerical work must stop by T0+1320; phase and commits
must finish by T0+1800. Missing an intermediate deadline stops its dependent work
and leaves time only for permitted evidence retention. Elapsed time and entry
counts are separate: unused time cannot replace or repeat a consumed slot. Tests
cannot load selected states, scientific knots, archived evaluators or fitting
fixtures. There is no scientific pilot, adaptive precision search, third toy
invocation, post-correction pass or production arithmetic correction here.

Use `.local/envs/calibration-global/bin/python`. Set OMP, OPENBLAS, MKL and NUMEXPR
thread counts to 1 before worker startup. Exact calculations use standard-library
`fractions.Fraction`; installed NumPy may be imported solely to reproduce the
pinned binary64 quadrature operation. Do not import historical evaluator modules
or call SciPy in this implementation. Hash their files as provenance only.

The workload is bounded by 18 coefficients, 150 quadrature samples, six states
and two formulations. Precomputing each method's state-independent exact operands
once makes 120 seconds plausible, not measured or guaranteed. If engineering or
arithmetic exceeds its limit, retain failure/partial evidence and return to
authorized Review/Plan; do not enlarge this allocation.

## New files and commands

Create only these implementation surfaces, plus parent-owned run bookkeeping:

- `scripts/basketball_acceleration_reference_v12.py`: stdlib admission, fixed
  schedules, supervisor/journal helpers, method A, verification and JSON-only packaging.
- `scripts/basketball_acceleration_control_v12.py`: independent method B; it may
  share serialization/deadline/entry helpers but no computed mathematical operands.
- `tests/test_basketball_acceleration_reference_v12.py`: the fixed toy cases.
- `docs/experiments/basketball-shared-timing-v12/`: immutable admission/inputs,
  source and readiness manifests, test and command logs, allocation marker,
  per-method entry journals/results, exact comparisons, budget, decision and
  package validation. Preserve original v11 failure rows in this package too.
- `docs/experiments/basketball-shared-timing-v12.md`: result, limits and next step.
- Run files `iteration-003-implementation.md` and `iteration-003-validation.md`
  under `docs/continuous-improvement/20260908-plan016/`.

Expose `admit`, `run`, `package` on the first script with the fixed output root
and authorization path
`docs/continuous-improvement/20260908-plan016/iteration-003-plan019-authorization.json`.
Refuse collisions at admission; use exclusive creation for immutable outputs.
Do not pick another namespace or overwrite an existing result. `run` requires
admission, frozen readiness, valid authorization and unexpired deadlines;
`package` only reads retained data and never calls either reference calculator.
Document exact executed commands and that reproduction needs a fresh planned
allocation and namespace; these commands do not confer free reruns.

## Work 1 — Freeze identities and certify structural exclusion (SC-05)

Let V11 denote `docs/experiments/basketball-shared-timing-v11/`. Select the six
records from `probes.json.gz.records` by these exact original slot IDs, in order:

| Original slot | Group | SHA-256 of decoded `physical_hex` bytes |
| --- | --- | --- |
| `metric/conditional-03/cold/ray/0/1/amplitude/4` | 2 | `769ea991fdd2cf581d162e0487e459953b4b2620dd24eaf0932372e8c94642b4` |
| `metric/conditional-03/cold/ray/0/1/amplitude/44` | 2 | `57d287a53d42eca3249f20ddb68ae1bf113a61f9b3126249052ac978ed57f4bf` |
| `metric/conditional-10/cold/ray/2/-1/amplitude/4` | 9 | `7adfdfa02ca0c938ff2f32edc1e3af1ca403dc5770d16679892e0542a312f40c` |
| `metric/conditional-10/cold/ray/2/-1/amplitude/44` | 9 | `3592cd5f894a29a851a1950720dbb550017db1c6ba197847e7df61607ba0f8ef` |
| `metric/conditional-16/cold/ray/2/-1/amplitude/4` | 11 | `53e4de694aa7bd54b0716315cd5c84cd602954befafbaedb300ca6bac95e5542` |
| `metric/conditional-16/cold/ray/2/-1/amplitude/44` | 11 | `59944338d4e2729e044de9a91afecf00e0f3e718d502871bc5b8bb000822f2f8` |

Freeze these source identities, checked from existing bytes during planning:

| V11 input | SHA-256 |
| --- | --- |
| `inputs.json` | `7a4b5aebeb5652051298ab88103a44af63a13ed69163eda988b333169cdf11f0` |
| `rays.json` | `f8d0aad1f2b7f3a3de991bdab68ca3d1f37bc2306e06b7321a0f6491f8305a8c` |
| `probes.json.gz` | `f386896d04ad764fa17ae7b487fe30504a3967179f026347c1979d26e5b21c4e` |
| `primary.jsonl` | `f544aab2fc6f18ee22076128761a826865613c2a71836514a9b7a2821a2c8fd5` |
| `independent.jsonl` | `39cf317220fe6fd7b4e4b773e75b8462e2acac09de3dec1eeb6352e08c582a57` |
| `admission.json` | `f262a40682dac776dfaacb36792f171a055ed21b63c3edf1dc3473efa9453268` |
| `execution-sources.json` | `285845798284eecc2b421da25f4c435fcedd18e5705d51c15b68b3f62904f50a` |
| `verification.json` | `4be416f5567f35da5aa549770ef5392e45700c9d271f21cf1a7e986db094f944` |
| `verification-failures.json` | `672284899958ad7aa790e58d5a3d79d0291eb3a4034039561eb34c3f83cfb3b0` |
| `budget.json` | `2c2c488b6ed60257216e81f8e9b7809f431651319109a39dd3dd422b375abeca` |

Bind the matching `inputs.json.cases` rows and `rays.json` records, original v10
problem/attempt identities and historical hash map. Verify all referenced
historical/source hashes and retain their mapping; never read excluded paths.
Freeze the installed interpreter, NumPy files used for quadrature, new scripts,
tests and imported stdlib implementation files in an execution source manifest.
In particular retain the pinned historical `basketball_shared_spline_v2.py`, v11
primary/independent scripts, and installed SciPy `_bsplines.py`/`_fitpack_impl.py`
identities from V11's source manifest. No source repair is authorized on mismatch.

Inspect journals as JSON, respecting their actual schema (v11 entry journals are
plain event streams; v10 chained journals retain their existing chain checks).
Require exactly one allocation and completion per selected original slot and
method, with one depth entry/return and one residual entry/return, matching saved
physical bytes and finite status. Check archived depth arrays/minima and feasibility against original
`1e-8` depth threshold by retained-value comparisons only. Copy all 54 G values,
cost/data/acceleration/depth fields, selected original comparison failures and
physical bytes from both archived results; do not recompute any of them.

Require 432 physical bytes decoded as 54 little-endian binary64 values in
row-major 18×3 order; no nonfinite values. Retain 22 knot values as binary64
bytes, weight exactly one, one group, free-offset set `[]`, window `[50,149]`,
spacing 10 and offsets `{1:0,2:-25,3:-25}`. Require identical knot/window/weight
definitions across the three admitted cases, which permits one setup per method.
Never form `base + amplitude*direction`, normalize, truncate coefficients or
substitute ideal real-valued rays for the saved rounded states.

Certify using all saved observation frames and offset identities that every
corrected observation time `(frame-offset)/25` is at least 2, while the cubic
supports of rows 0/1 end at knot indices 4/5, respectively binary64 `1.4` and
`1.7999999999999998`. Integer-frame/rational ordering suffices here; no scientific
basis evaluation is allowed at admission. The strict separation from those
support ends certifies exact zero image-objective and depth partials for rows
0/1, independently of the physical state. If any observation or support violates
this certificate, stop admission without selecting alternatives. This is the
full-objective-gradient justification for the six acceleration-only partials.

## Work 2 — Two exact mathematical references (SC-01/03 prerequisite, SC-05)

All following setup and scientific arithmetic runs only inside the single
charged worker. Decode immutable operands independently in each method using
`struct`/`Fraction.from_float`; do not share decoded rational knots, coefficients,
quadrature arrays, basis values, acceleration arrays or reference outputs.

For each method reproduce the pinned expression
`np.arange(window[0]-25, window[1]+26, dtype=float)/25`, then retain its exact
little-endian binary64 bytes before conversion to rational values. This yields
150 samples, from binary64 1 through binary64 6.96 inclusive. Require both
methods' quadrature bytes match. The original admitted knots are authoritative;
do not regenerate them with decimal fractions or a different `arange`. In
particular `1.4` is its binary64 rational value, not 7/5. The domain is the
closed interval `[U[3], U[18]]`; reject outside-domain samples, no extrapolation.

With all physical C values retained, use the mathematical objective

`F_acc = (w/nacc) * sum(k=0..149, axis=0..2) S_axis''(q_k)^2`.

Here `w=1`, `nacc=150`, and the division and all subsequent reference arithmetic
are exact rational operations. Do not replace this with the rounded squared
residual scale `sqrt(w/nacc)^2`; the reference is the original quadratic, not a
simulation of one floating arithmetic path. Gradient outputs are precisely
row-major indices 0..5 (rows 0/1, axes X/Y/Z).

Implement the same algorithms with coefficient-count bounds derived from input
length for the fixed toy fixtures; production admission fixes that count to 18.
For n coefficients, the two control differences have n-1 and n-2 rows, and the
degree-one span range is 1..n-3. This generality authorizes no additional
scientific shape, state or setup.

### Method A: basis derivative recurrence

Build the full knot-based recurrence independently for each sample, memoizing
state-independent values within this method only. For degree zero use
`N[i,0](q)=1` when `U[i] <= q < U[i+1]`, otherwise zero. At the final domain
endpoint `q=U[18]`, choose the last positive-width interval ending there (index
17 for admitted U), assigning that degree-zero value one and the others zero.
This evaluates the left endpoint limit of the final span. At interior knots use
the right interval. Repeated zero-width spans contribute zero, never 0/0.

For degree p=1..3 use

`N[i,p] = (q-U[i])/(U[i+p]-U[i]) * N[i,p-1]`
`         + (U[i+p+1]-q)/(U[i+p+1]-U[i+1]) * N[i+1,p-1]`.

Omit a whole term if its denominator is zero. Derivative recurrences for m=1,2
are `D^m N[i,p] = p/(U[i+p]-U[i]) * D^(m-1) N[i,p-1]`
`- p/(U[i+p+1]-U[i+1]) * D^(m-1) N[i+1,p-1]`, using zero for derivatives above
the lower degree. Apply the same zero-denominator and endpoint conventions.
Store `A[k,i]=D^2 N[i,3](q_k)` for i=0..17 once. In each owned state bundle form
`a[k,axis]=sum_i A[k,i]*C[i,axis]`, exact F_acc, and
`G[j,axis]=(2*w/nacc)*sum_k A[k,j]*a[k,axis]` for j=0,1.
Retain each of the 150 signed summands and their absolute-value sum per partial.

### Method B: differentiated control polygon and transpose propagation

Do not call method A or use any basis/acceleration array from it. Independently
decode original U/C and quadrature. Form positive difference factors
`alpha[i]=3/(U[i+4]-U[i+1])` for i=0..16 and
`beta[i]=2/(U[i+4]-U[i+2])` for i=0..15. These admitted denominators must be
positive; unexpected zero denominators fail setup rather than invent a rule.
Compute `D[i]=alpha[i]*(C[i+1]-C[i])`, then
`E[i]=beta[i]*(D[i+1]-D[i])`. The derivative knot vectors are U[1:-1] at degree
two and `W=U[2:-2]` at degree one, preserving repeated clamped endpoints.

Evaluate E by direct linear interpolation: find span s in 1..15 with
`W[s] <= q < W[s+1]`, and at the final endpoint choose s=15. Let
`theta=(q-W[s])/(W[s+1]-W[s])` and
`a=(1-theta)*E[s-1]+theta*E[s]`. At the initial endpoint use the first positive
span; interior-knot equality selects its right span. Compute exact cost from
these accelerations once in the bundle.

For each sample/axis seed adjoint `h=(2*w/nacc)*a`; distribute it to E[s-1]
and E[s] with weights 1-theta/theta. Propagate each E adjoint to D[i] with
`-beta[i]` and D[i+1] with `+beta[i]`; propagate each D adjoint to C[i] with
`-alpha[i]` and C[i+1] with `+alpha[i]`. Accumulate only the six requested
output partials; other internal adjoints are not new evaluated states/outputs.
Retain each sample's signed contribution and absolute-value sum for those six
partials within the same bundle. No finite differences or secondary arithmetic
pass is needed. This factorization follows the pinned coefficient-difference
mathematics but uses exact rational operations and independent intermediates.

### Exact agreement and archived-value comparisons

Serialize rationals as normalized decimal numerator/positive-denominator strings;
decimal display approximations cannot determine pass/fail. Require exact equality
of the two costs and each of six partials for every selected state. Retain both
sets of signed summands; their per-sample equality is also checkable without new
scientific evaluation. Any reference disagreement makes that state unverified,
with both outputs and errors retained; no fallback reference is elected.

When reference equality and provenance pass, compare each archived float64 G
component v against common rational g using exact `abs(Fraction(v)-g)`.
Preserve inherited `atol=1e-10, rtol=1e-8` and archived-value scale. For an exact
representation of the existing tolerance computation, calculate binary64
`allowed=1e-10 + 1e-8*abs(v)` with multiplication then addition and convert that
result to a Fraction; retain its float bytes and exact rational value. Do not
round the reference before comparing. Classify each archived component as within
tolerance, outside tolerance or unverified; each method/state aggregate passes
only if all its selected components pass. Also compare each saved acceleration
cost to the common exact F_acc using the inherited objective tolerance
`1e-10 + 1e-9*abs(saved_acceleration_cost)` by the same rule. This does not compare
the full saved objective to an acceleration-only cost.

Save signed reference derivatives, summand absolute sums, exact forward errors
and allowed errors together. Do not impose a cancellation-ratio threshold, snap
near-zero values to zero or attribute error to a particular floating operation
without evidence. Keep the entire original v11 failure report unchanged alongside
these new comparisons. Agreement adjudicates only these 36 selected components;
the other 57 failed v11 states, including an intermediate ladder maximum, remain
outside this plan. Neither v11 A2/A3 nor timing gates become retrospectively met.

## Work 3 — Validation, enforcement and publication (SC-05)

Freeze exactly these 12 hand-authored test cases before the first suite invocation.
Use simple rational toy operands, no archived scientific fixture loading:

1. Constant cubic Bezier controls: zero acceleration/cost/partials.
2. Linear cubic Bezier controls `[0,1,2,3]`: zero second derivative and cost.
3. On `[0,1]`, controls `[0,0,1/3,1]`, samples `[0,1/2,1]`, w=1:
   S=t², acceleration 2, cost 4, G(row0)=12 and G(row1)=-12 in its active axis.
4. Same domain/samples with controls `[0,0,0,1]`: S=t³, cost 15,
   G(row0)=6 and G(row1)=18; sample accelerations 0,3,6.
5. Explicit repeated-clamped endpoint assertions against Bezier formulas
   `N0''=6*(1-t)`, `N1''=-12+18*t`, `N2''=6-18*t`, `N3''=6*t` at both ends;
   reject out-of-domain values and exercise zero-width recurrence terms.
6. Nonuniform U=`[0,0,0,0,1/2,2,2,2,2]`, controls `[0,0,1/3,2,4]`:
   S=t², acceleration 2 at `[0,1/2,2]` including interior-knot equality, cost 4.
7. Cancellation case on unit Bezier domain: controls `[0,0,-1/6,1/2]`,
   samples `[0,1/2,1]`; acceleration `6*t-1`, cost 10, G0=0, G1=24,
   signed-summand absolute sums 8 and 32 respectively. Exact zero must follow
   algebra, never a threshold. Test inactive axes as zero.
8. Synthetic frame/support certificate accepts strict separation and rejects
   equality/overlap; no basis evaluator is called for this check.
9. Tiny synthetic serialized-state and source-hash tampering is rejected;
   exact physical bytes rather than decimal regeneration own a slot.
10. Toy ledger rejects duplicate/unallocated/wrong-method/over-cap entries,
    preserves consumed failures and enforces deadlines before callbacks.
11. Toy supervisor interruption/timeout retains entry consumption and partial
    results and reaps its owned process group; no scientific child is launched.
12. Direct-worker, consumed-allocation and output-collision rejection; package
    checks distinguish exact-reference disagreement from archived float failure
    and retain unverified outcomes without altering scientific gates.

A test case may contain its stated fixed assertions but no random/property sweep
or extra sample ladder. Each started suite counts, including import/setup errors;
retain each log. One second invocation is available for necessary corrections
before scientific readiness. Freeze final sources/test identities and command
logs after tests pass. If source changes after the first scientific entry,
invalidate readiness for further scientific work; retain completed results and
do not rerun them. Pure report corrections must retain source identities.

The supervisor exclusively creates `started.json` before child startup, binding
authorization/admission/readiness hashes and all 12 slots. Start the numerical
clock before child startup/imports, with deadline
`min(start+120 seconds, T0+1320 seconds)`. Each method has one setup slot (separate
from its six result bundles); log setup ownership before construction. Run all
six A bundles, then all six B bundles in the single worker. Before each bundle,
flush method/slot/physical-byte/source ownership and entry counts; compare actual
argument bytes to the allocation. No cache hit, exception, interrupted entry,
denial or skipped slot creates a replacement. Finish/persist each bundle before
the next. Stop on malformed provenance, forbidden entry or reference exception.

Use an owned child process group and a deadline-aware supervisor; send TERM early
enough to allow KILL/reap within the hard deadline (at most two seconds grace).
Propagate interruption cleanup, retain PID/group identities in their actual
namespace, exit code, observed counts, start/end times and `worker_stopped`.
Never interpret sandbox namespace PIDs as host kill targets. Parent independently
enforces the phase deadline and required stops. Numerical wall accounting is the
whole supervised invocation including imports/setup/journaling/verification/I/O;
retain any cleanup time explicitly rather than hiding an overrun. No scientific
work may escape into `admit`, tests or `package`.

On a suspected sandbox/permission failure, inspect possible partial state and
request the one safe retry of only the failed operation outside the sandbox,
with unchanged clock and slot ownership. No full-pass restart. If denial/failure
or unsafe replay prevents continuation, stop and report exact command/error and
permission certainty under AGENTS.md. Notify parent immediately on any required
stop, including failed git add/commit. Do not relabel failed execution as a
mathematical unknown.

Package validation is JSON/bytes/hashes only: reconcile 2 setup ownerships,
12 scheduled bundles and observed entries/completions, 72 gradient outputs and
12 costs when complete, no duplicate states/slots, exact comparisons, archived
failure preservation, charge ceilings, source/historical hashes, and null gates.
Check Markdown links, `git diff --check`, and inspect task-related diffs. Stage
explicit task paths using separate escalated git add/commit calls with the
required prefixes and inspected staged diff; supply title and description.
Commit completed validated implementation/evidence milestones even if archived
floating values fail; an incomplete scientific package must be labeled as such.
Do not push, amend or rewrite history. Record commits and final elapsed time in
iteration implementation/validation handoff within the phase allowance.

## Acceptance and next decision

| Plan acceptance | Required evidence | Criterion advanced |
| --- | --- | --- |
| A1 | All six pinned physical identities, original input/source hashes, archived result ownership and structural support certificates pass | SC-05; SC-01/03 prerequisite |
| A2 | All 12 owned bundles finish within limits; two exact methods agree for all six costs and 36 paired partials, with retained signed summands | SC-05; SC-01/03 prerequisite |
| A3 | All 72 archived G comparisons and 12 archived acceleration-cost comparisons have justified within/outside classifications, or are explicitly unverified if A1/A2 fails; original failures remain unchanged | SC-05 |
| A4 | Fixed toy checks, package/link/diff/source/budget checks and local commits complete; report states limitations and one concrete next recommendation, with existing gates preserved | SC-05; preserve SC-02/04 |

Full plan acceptance requires A1/A2 and complete verified comparisons in A3;
explicitly unverified records preserve an honest partial result but do not pass
the plan. Neither archived floating implementation is required to pass its
tolerance for exact-reference plan acceptance. An error is a measured result.

The report must select one next action from the observed outcome, specify
concrete time/entry/concurrency resources for Review/Plan, and execute none of it:
if a reference or admission fails, recommend the smallest identified correction
and separately allocated fixed rerun; if references agree, use the archived
method findings to identify the arithmetic correction/qualification work actually
needed. Do not choose a production replacement before this result. The next
review must relate the finding back to timing qualification and missing Basketball
reconstruction comparison, not expand the extreme-ray study by default.

Keep accepted timing, production candidate and final-validation protocol null,
`ready_for_full_screens=false`, and all Plan 015 objective/depth/qualification
thresholds, 200-iteration/200-distinct-state local limits and conditioning,
scalar, combined-pilot and evaluator gates unchanged. No near-margin study is
bundled here. SC-01/SC-03 remain unmet after this arithmetic prerequisite alone;
only verification of every unchanged saved criterion establishes the objective.

Plan 018's single pass remains consumed (7.84522387 numerical seconds;
1498.589622 final phase seconds); its unused allowance is not transferable.
Plan 016's historical 405 attempts/six preflights stay consumed. The 24-hour
training allocation, 22523.417254 retained charged training seconds and all
method/scene ceilings remain unchanged; this plan consumes zero training time.
An exhausted individual plan returns the active loop to eligible Review/Plan,
subject to all interruption, whole-loop, authorization and permission stops.
