# Iteration 003 review — adjudicate the six acceleration-gradient failures

Recommend a separately versioned **exact-arithmetic check of six retained states**,
restricted to the six gradient components that can fail. Reuse the saved floating
results and depths; do not repeat either full evaluator. Two independent exact
acceleration calculations can establish which saved values meet the inherited
tolerance. Repeating the two disagreeing float64 calculations alone cannot do so.
This is bounded prerequisite work for SC-01/SC-03 and evidence repair under SC-05;
it neither qualifies timing nor completes the reconstruction objective.

Read [objective](objective.md), [status](status.md), [latest assessment](iteration-002-assessment-04-implementation.md),
AGENTS.md, [Plan 018](../../../plans/plan_018.md), its
[implementation](iteration-002-implementation.md), [validation](iteration-002-validation.md),
and the sources/artifacts below. This review used source inspection and
standard-library JSON/gzip decoding of retained evidence only. No scientific
evaluation, optimizer, test suite, GPU, installation or network request ran.
Only this file is written; parent owns assessments, status and commits.

## Findings that determine the next step

The [v11 report](../../experiments/basketball-shared-timing-v11.md),
[verification](../../experiments/basketball-shared-timing-v11/verification.json),
[component failures](../../experiments/basketball-shared-timing-v11/verification-failures.json),
[decision](../../experiments/basketball-shared-timing-v11/decision.json), and
[package checks](../../experiments/basketball-shared-timing-v11/package-validation.json)
consistently distinguish package integrity from scientific verification:

- All 48 snapshot comparisons, 24 ray derivations and 24 analytical-limit pairs
  pass. All twelve weight-zero rays eventually violate original depth constraints.
  Those particular directions therefore do not establish a feasible escape; they
  do not exclude other directions or establish a finite minimizer or timing.
- The 63 failed finite comparisons are exclusively gradient components in
  coefficient rows 0 and 1: 367 failed components, on three weight-one rays at
  every even exponent from 4 through 44. No saved cost, depth, identity or
  multiplier comparison failed. Plan 018 A2/A3 remain failed.
- At exponent 4, the three rays' maximum error/tolerance ratios are respectively
  1.7120335, 2.3918594 and 4.5510253. At exponent 44 they are 1262779.97,
  8887.03 and 34382.33. These are copied from retained failure rows, not fresh
  gradient evaluations. The largest ratio over the complete ladder is
  2036763.2; the six selected endpoints do not cover that intermediate maximum.

There is a useful exact support deduction from
[the admitted inputs](../../experiments/basketball-shared-timing-v11/inputs.json).
For all affected cases the cubic knot vector starts
`[1,1,1,1,1.4,1.7999999999999998,...]`. Basis coefficient 0 has support ending
at knot 4, `1.4`; coefficient 1 ends at knot 5, `1.7999999999999998`.
Observation frames are 50–149; camera offsets are 0, -25 and -25 and the time
formula is `(frame-offset)/25`. Thus every image observation is at time at least
2, strictly beyond both supports. The data objective and depth constraints have
**exactly zero coefficient partials in these two rows**, independent of the
state magnitude. The full objective gradient there is the acceleration gradient.
This is a structural argument, not thresholding small basis values to zero;
the next admission must certify it from all admitted observation times.

The two arithmetic paths are algebraically equivalent but have different
rounding sequences:

- [Primary wrapper](../../../scripts/basketball_shared_trajectory_diagnostic_v11.py)
  uses the pinned [SplineProblem evaluator](../../../scripts/basketball_shared_spline_v2.py):
  differentiate the identity-coefficient basis, form `A @ C`, scale residuals and
  Jacobian entries by `sqrt(weight/nacc)`, then compute the sparse `2*J.T@r`.
- [Independent evaluator](../../../scripts/basketball_shared_trajectory_verify_v11.py)
  differentiates a scalar spline carrying each actual coefficient column, then
  uses `2*weight/nacc * A.T @ acceleration`. The installed SciPy derivative source,
  bound by [execution sources](../../experiments/basketball-shared-timing-v11/execution-sources.json),
  forms successive coefficient differences and divides by knot differences in
  `_fitpack_impl.splder`.

Consequently cancellation/rounding is a concrete candidate, but source inspection
does not identify the true gradient at any failed physical state or assign fault
to one path. The retained records do not contain separately computed acceleration
gradient terms. A reference is needed before proposing a correction. The image
term need not be reevaluated to adjudicate the failing components.

## Recommended work and criterion mapping

**R1 — Freeze the smallest discriminating input set (SC-05; prerequisite to
SC-01/SC-03).** Admit exactly these six existing `physical_hex` records from
[probes](../../experiments/basketball-shared-timing-v11/probes.json.gz), with the
matching independent journal completions and original input/source identities:

| Ray ID | Group | Fixed amplitude exponents |
| --- | --- | --- |
| `metric/conditional-03/cold/ray/0/1` | 2 | 4, 44 |
| `metric/conditional-10/cold/ray/2/-1` | 9 | 4, 44 |
| `metric/conditional-16/cold/ray/2/-1` | 11 | 4, 44 |

Retain all 54 coefficient bytes, knots, weight, window/quadrature definition,
archived gradients, depths, objective and the exact six original slot IDs.
Bind v11 input/ray/probe/independent-journal/failure/source hashes and their v10
provenance. Decode stored state bytes directly: do not regenerate `base+a*d`,
normalize, round through decimal text, delete unsupported coefficients, introduce
a new ray, or replace a slot. Verify primary/independent physical-byte equality
and their saved feasible status by JSON/bytes inspection. Certify the support
exclusion above without a scientific basis evaluation. Freeze a new output
namespace and reject collisions; preserve v11 and all historical sources.

**R2 — Compute two independent exact acceleration references (SC-05;
SC-01/SC-03 prerequisite).** Use the original mathematical quadratic

`F_acc = weight/nacc * sum_k,axis S_axis''(t_k)^2`,

with the admitted binary64 knots, physical coefficient bytes and quadrature
samples treated as exact rational numbers. Construct the quadrature with the
pinned binary64 operation before conversion and retain its bytes. Do not replace
binary64 knot/time values with ideal decimal fractions such as 7/5, or replace
the physical state with an ideal real-valued ray. All scientific setup and
reference calculations belong inside the new numerical charge.

Use standard-library rational arithmetic, with no adaptive-precision search or
new dependency. Recommend these independently expressed methods:

1. Exact B-spline basis/derivative recurrence, yielding the second-derivative
   basis; form exact acceleration and the six entries of
   `2*weight/nacc * A.T @ (A @ C)` for rows 0/1.
2. Exact differentiation of the coefficient control polygon twice, exact
   evaluation of the resulting degree-one spline, and transpose propagation
   through those two difference operators to rows 0/1.

Each method independently decodes immutable operands and constructs its own
mathematical intermediates. Share only serialization, slot/deadline and journal
helpers. No SciPy-produced basis/acceleration array or other method's computed
results may supply the independent reference. Both calculate the acceleration
cost and the six targeted derivatives once per fixed state; all 54 coefficients
remain inputs. Handle repeated end knots and endpoints according to the pinned
spline domain, and prove this convention on hand-authored cases before entry.

Require exact rational equality between the reference methods for all retained
costs and targeted gradients. Compare each archived float64 gradient against
that common reference using the inherited `atol=1e-10, rtol=1e-8`, with the
archived value as the scale reference, and retain the exact errors/allowed errors.
Also retain the original primary-versus-independent failure unchanged. Report
each archived method as within tolerance, outside tolerance or unverified;
agreement between archived methods is not a substitute for the reference.

Within the same reference bundle, retain signed summands and their sum of absolute
values for the six targeted derivatives. Report these alongside the derivative
and forward error, without inventing a cancellation threshold. Exact support
zeros establish the absent data term; numerical cancellation does not establish
zero acceleration or justify snapping a derivative to zero. Large cancellation
and reference error can support a conditioning diagnosis, but this experiment
does not identify an individual floating operation as the cause without evidence.

**R3 — Validate the reference and publish an honest consequent decision (SC-05;
SC-01/SC-03 prerequisite; preserve SC-02/SC-04).** Before the single scientific
invocation, use a focused hand-authored suite covering exact constant/linear and
known curved splines, repeated-knot endpoints, a nonuniform knot vector,
cancellation in signed derivative sums, support-based zero data partials,
state/hash tampering, slot limits and interruption accounting. Such tests must
not load scientific fixtures or invoke fitting. Include independent analytic
expectations; a test that merely agrees with the implementation is insufficient.

Package exact reference values, source/physical bytes, all original failed
comparisons, new per-method error comparisons, entry journals, elapsed charges,
and preserved historical hashes. Check links/diffs and commit only validated
task-related work under AGENTS.md. Add no production evaluator correction in
this phase: without a reference outcome, choosing a replacement arithmetic
scheme would be premature. If a code defect is discovered after the fixed pass,
retain that failure; correction does not renew any consumed evaluation slot.

The deliverable must recommend one next step from the outcome, with concrete
resources, without executing it. If both exact references agree, the report can
adjudicate the **36 selected gradient components** (six states × six components)
and scope any subsequent correction/qualification work. If references disagree,
or provenance/time/entry checks fail, report the check as failed or incomplete.
Unverified arithmetic must not be labeled mathematical uncertainty or passed
verification. Six states do not validate the other 57 failed v11 states or
retrospectively make v11 A2/A3 pass.

## Recommended resource envelope for Plan to finalize

The prior 20-minute/60-second suggestion identified useful states, but proposed
two repeated floating evaluators with no independent accuracy reference. Replace
that workload with the bounded exact check above. Recommend the following new
plan-specific limits; this is not reuse of Plan 018's allocation:

| Allocation scope | Recommended hard ceiling |
| --- | --- |
| Implementation inspection through tests, packaging, validation and local commits | 30 minutes elapsed; one recorded T0, no reset |
| Scientific setup plus both exact reference passes, imports and numerical I/O | 120 cumulative wall seconds, included in the 30 minutes |
| Scientific states | Six immutable states; one pass per exact method |
| Acceleration-only cost/partial-gradient bundles | Six per method, 12 total; at most 72 reference component outputs, paired into 36 checks |
| Scientific setup | One knot/quadrature/basis or coefficient-difference setup per method; no alternate discretization |
| Execution concurrency | One single-thread numerical worker plus one supervisor; no other run worker |
| Focused toy validation | At most two suite invocations, at most 12 fixed hand-authored cases per invocation; counted separately |
| Full residual/image-gradient or depth/Jacobian entries | Zero; reuse admitted retained results |
| Float64 evaluator replay, finite differences, Hessians, ray/limit entries, optimizers/local fits | Zero |
| Full screens, real-data fits, training, rendering, GPU, installs/downloads | Zero |

The 120 seconds is an estimate for a small rational calculation, not an observed
runtime or permission to enlarge it. No pilot on scientific inputs is authorized.
Plan 018's different 1,248-slot computation used only 7.84522387 numerical seconds,
but its implementation and final handoff took 1498.589622 seconds. A 30-minute
phase allows for two new arithmetic implementations and independent toy
expectations without assuming that their engineering fits a 20-minute phase.
If the selected limits prove insufficient, preserve partial evidence and return
to authorized review/planning; do not extend clocks or replay calls.

Suggested absolute milestones are input admission by T0+600 seconds, source
freeze/toy readiness by T0+1200, all numerical work stopped by T0+1320, and
package/commits by T0+1800. The parent records T0/deadlines and the standing
approval basis before implementation. Use one supervised invocation with an
atomic consumed/started marker, write entry ownership before scientific calls,
persist every completed state, and terminate/reap its process group on timeout
or interruption. A skipped, failed, repeated or denied slot cannot transfer or
gain a replacement. No post-correction scientific rerun is included. Follow the
repository's one safe escalated retry rule if a permission failure occurs;
never replay successful entries or restart the allocation.

Plan should preserve this narrow distinction: **plan acceptance** means a
complete, independently agreeing exact reference and honest accuracy findings
within these limits; it does not require either historical float implementation
to pass. **Main objective attainment** still requires every objective criterion.

## Budget and broader-objective handoff

Current AGENTS.md at `b62f2ea` provides standing approval for Review-recommended,
Plan-finalized plan-specific allocations in an explicitly active loop. The
parent must check applicable ceilings and save that basis before dispatch;
routine additional budget confirmation is not required. Historical artifacts
requesting approval do not override this instruction. No new whole-loop or
review/planning exhaustion is recorded.

Plan 018's single primary/independent pass is consumed: 600 depth and 166
residual entries plus 24 limits per pass; 7.84522387 numerical seconds and
1498.589622 final phase seconds. Its unspent seconds and skipped residual
capacity do not authorize this new work. Plan 016's 405 scheduled attempts and
six preflight allocations remain consumed and its clock remains historical.
The 24-hour training allocation and method/scene limits are unchanged; the
[comparison](../../experiments/contender-summary.md) retains 22523.417254 charged
training seconds overall and zero Basketball training charges. Do not transfer
remaining method allocations, restart budget-stopped methods, or fund the
diagnostic from training allowances.

SC-01 remains not met because Basketball timing/preparation is not qualified;
SC-03 remains not met because Basketball reconstruction and its measured
quality/motion/speed/resources comparison are absent. SC-02 and SC-04 retain
their supported SelfCap model/reload and practical recommendation evidence;
SC-05 retains its evidence-integrity status with the recorded failed-arithmetic
limitation. No criterion becomes newly met from this review.

Keep accepted timing, production candidate and final-validation protocol null,
and `ready_for_full_screens=false`. Preserve the
[Plan 015](../../../plans/plan_015.md) qualification/depth/objective thresholds,
200-iteration/200-distinct-state local limits and conditioning, scalar,
combined-pilot and evaluator gates. Do not bundle the separately motivated
near-margin initialization study or another optimizer policy into the exact
reference check. Once the arithmetic finding is resolved, the next review must
return to those timing prerequisites and the missing Basketball reconstruction
comparison, not expand into an unbounded study of extreme control rays.

No commands or jobs from this review remain running. No permission or git
failure occurred; no commit or source edit was attempted by this stage.
