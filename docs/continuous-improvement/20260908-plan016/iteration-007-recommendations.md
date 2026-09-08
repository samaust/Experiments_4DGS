# Iteration 007 Review — centered image residuals and structural Hessian symmetry

Recommend one narrowly scoped arithmetic intervention, followed by one evaluation
of the **original cases 12 and 13, each cold and returned**. Construct image errors
without first adding the principal point to a pixel prediction, and construct
analytical objective Hessians and their congruences from one value per unordered
index pair. Preserve independent candidate/reference methods and every existing
comparison tolerance. This is a proposed repair whose effectiveness must be
measured; the retained evidence does not establish that it will resolve KKT.

Do not change the coordinate API in this plan. All sixteen v15 new-transform
public replay rejections remain failures. A passing four-state arithmetic subset
would establish that subset's result only, not qualification of the 32-state
cohort, the legacy public-y protocol, timing, or the main objective.

## Context, assessment and completed baseline

The Review read [AGENTS.md](../../../AGENTS.md), the unchanged
[objective and criteria](objective.md), [status](status.md), and the
[post-implementation assessment](iteration-006-assessment-03-implementation.md)
before work. It then inspected [Plan 022](../../../plans/plan_022.md),
[implementation](iteration-006-implementation.md),
[validation](iteration-006-validation.md),
[checkpoint](iteration-006-checkpoint.md), the
[v15 report](../../experiments/basketball-shared-timing-v15.md), retained comparison
operands/errors, all six v15 source surfaces and relevant readiness test paths.
No evaluator, numerical import, test, fit, device operation or network request was
run by this Review. Retained-array inspection used stdlib JSON/gzip/struct only.

| Criterion | Status | Remaining gap / applicable evidence |
| --- | --- | --- |
| SC-01 | not met | Basketball timing, preparation and reconstruction remain unqualified. The arithmetic and public-coordinate failures are prerequisites. [v15 decision](../../experiments/basketball-shared-timing-v15/decision.json). |
| SC-02 | met | Supported SelfCap model/reload evidence remains applicable with the historical limitations in the latest assessment; no model or training changes. |
| SC-03 | not met | The required Basketball reconstruction and measured comparison are still absent. An evaluator subset cannot establish this criterion. |
| SC-04 | met | The supported SelfCap [workflow recommendation](../../selfcap-workflow.md) remains applicable with its stated limitations. |
| SC-05 | met | Retained source, input, readiness, schedule, process and comparison evidence supports reproducibility, with the already recorded historical limitations. Preserve this evidence and add a separately scoped experiment. |

Plan 022 is complete and terminal: all 20 readiness groups passed with exact
inventory; one science invocation completed all 1,651 entries, 96 canonical
comparisons, 80 public probes, 16 new-P comparisons and 16 historical comparisons.
Source coverage, package integrity, exact schedule and historical corroboration
pass. Canonical comparison reports pass in 91/96 contexts; new-P in 15/16.
The failed canonical and new-P contexts have the same nine required failures.
The public dimension has 16 replay rejections plus 72 repeated wrapper-report
failures, not 88 different numerical mechanisms. All dimensions are complete.

Evidence: [retained summary](../../experiments/basketball-shared-timing-v15/retained-summary.json),
[package validation](../../experiments/basketball-shared-timing-v15/package-validation.json),
[comparison summary](../../experiments/basketball-shared-timing-v15/comparison-summary.json),
[readiness](../../experiments/basketball-shared-timing-v15/readiness.json),
[toy summary](../../experiments/basketball-shared-timing-v15/toy-readiness-summary.json),
[source coverage](../../experiments/basketball-shared-timing-v15/coverage-source-review.md),
[schema](../../experiments/basketball-shared-timing-v15/comparison-schema.json),
[schedule](../../experiments/basketball-shared-timing-v15/expected-schedule.json).

## What the retained operands establish

### D1. The physical Hessian failure is a one-ULP asymmetric contraction

In case 13 returned, weight zero, candidate H/Hdata entries `[52,54]` and
`[54,52]` are respectively `14925438.532865137` and `14925438.532865139`.
The stored symmetry error is `1.862645149230957e-9`; the frozen allowance is
`1e-10`. These are the only two failing physical/q symmetry indices. They are
the X/Z cross term of the last coefficient row. The independent physical/q
Hessians pass. Their y congruences introduce additional asymmetric rounding:
saved-P candidate H has 158 failed symmetry indices and reference H has 144;
new-P has 150 and 158 respectively. Hdata repeats those counts.

The candidate uses independent directed `einsum` contractions for projection,
spatial and coefficient curvature; both report implementations and the driver's
new-P transport use ordinary two-stage dense congruences. Mathematical symmetry
does not make those independently rounded directed entries byte-identical.
This explains a representation problem, not a justification to weaken the
absolute symmetry gate or repair a completed failing matrix after comparison.

Evidence: [canonical comparison](../../experiments/basketball-shared-timing-v15/comparison-13-returned-1.json.gz),
[new-P comparison](../../experiments/basketball-shared-timing-v15/newP-comparison-13.json.gz),
[candidate curvature](../../../scripts/basketball_shared_components_v15.py),
[candidate report](../../../scripts/basketball_shared_accounting_v15.py),
[reference](../../../scripts/basketball_shared_reference_v15.py),
[driver](../../../scripts/basketball_shared_evaluator_v15.py).

### D2. The y-KKT mismatch is inherited from image G, before force summation

The two failed saved-P y-KKT components are:

| Index | Candidate | Reference | Stored error | Stored allowance |
| --- | --- | --- | --- | --- |
| 51 | `1.2176909390902019e-6` | `1.2175704794496756e-6` | `1.2045964052631586e-10` | `1.000121757047945e-10` |
| 54 | `-1.1764498426547476e-5` | `-1.176488141398091e-5` | `3.8298743343379016e-10` | `1.0011764881413981e-10` |

At those indices y-G already differs by approximately the same amounts.
Candidate/reference y-Cd agree and y-Cb is zero. For example, at 54 y-G is
`0.035533928744805925` versus `0.0355339283618185`, while both y-Cd are
`-0.03554569324323247`. G passes its relative allowance, but cancellation with
the depth force leaves a smaller KKT reference and therefore a tighter allowance.
Changing only KKT addition order cannot address this upstream discrepancy.

Physical G's largest retained errors are at 52, 53 and 54:
`2.9857671890454185e-11`, `1.4887800194041123e-11`, and
`2.2717444245201612e-12`. The source and retained observation intermediates
localize a concrete cancellation exposure at **observation 199: camera 2,
frame 149, clamped endpoint with B equal to the last coefficient unit row**.
The original normalized depth is `0.005086693377829299`; image Jacobian entries
are about 157,000, while pixel errors are only about `[-4.0709e-5,3.4945e-6]`.
The retained candidate spatial gradient there is
`[-0.042694139123196126, 0.0036665824383693003, -0.003967987107487926]`;
the independent Jet gradient is
`[-0.04269413915300273, 0.003666582423469364, -0.00396798710975469]`.
The observation-level differences have the scale and location of the aggregate
G discrepancy. This is strong localization, not an unperformed exact error
decomposition or proof that one operation explains every bit.

Candidate errors currently evaluate `(focal_projection + principal) - observed`.
Reference Jet errors evaluate `focal_projection + (principal - observed)`.
The candidate therefore rounds a roughly 400-pixel prediction before subtracting
a nearly equal observation. Its small residual then drives a large projection
Jacobian. Neither higher acceleration precision nor a blanket summation change
targets this specific loss of residual information.

Evidence: [candidate returned report](../../experiments/basketball-shared-timing-v15/candidate-13-returned-1.json.gz),
[reference returned report](../../experiments/basketball-shared-timing-v15/reference-13-returned.json.gz),
[candidate actual preparation](../../experiments/basketball-shared-timing-v15/entry-output-candidate_13_returned_1_prepare_4.json.gz),
[reference actual preparation](../../experiments/basketball-shared-timing-v15/entry-output-reference_13_returned_prepare_2.json.gz),
[reference objective/Jet output](../../experiments/basketball-shared-timing-v15/entry-output-reference_13_returned_objective_residual_3.json.gz),
[candidate objective output](../../experiments/basketball-shared-timing-v15/entry-output-candidate_13_returned_1_objective_residual_5.json.gz).

### D3. The replay failure has a separate coordinate mechanism

All 64 saved-y probes pass; all 16 sequence-5 new-P inverse/forward probes fail.
The actual public mapping correctly refuses to allocate or evaluate the rounded
replacement state. Case 13's new-P replay has 21 mismatching q components; case
0 has 23. For example, case 13 component 7 maps to `-0.22457838452416037` instead
of the admitted `-0.22457838452416043`.

This is consistent with the specified binary64 inverse/forward arithmetic.
More precise image G cannot make that coordinate round trip exact. Preserve
the original cold origin, P, saved y, actual vg/vby and canonical state identity;
do not search nearby y, preload a y-cache with saved q, snap, reanchor, or call
canonical fallback a successful public replay. Plan 015 section 3 permits a
separately labeled coordinate-contract change with its own equivalence checks;
none is recommended for execution in this arithmetic plan.

Evidence: [case 13 replay](../../experiments/basketball-shared-timing-v15/public-13-5.json),
[case 0 replay](../../experiments/basketball-shared-timing-v15/public-0-5.json),
[Plan 021 public contract](../../../plans/plan_021.md),
[Plan 015 accounting contract](../../../plans/plan_015.md).

## Recommendations for the next Plan

### R1 — Freeze the existing four-state subset and provenance (SC-05; SC-01/03 prerequisite)

Use original case indices **12 then 13**, preserving all original labels and
hashes: `metric/joint-00/descending`, weight one, as the passing control; then
`metric/joint-01/cold`, weight zero, as the failing case. Each contributes the
original cold and returned slots. Both are dimension 55, free camera `[3]`,
18 coefficient rows, 300 observations, and the existing 150 quadrature samples.
Do not renumber the cases or choose new callbacks, coefficients or multipliers.
Verify both full v15 input files and the entire prior admission chain before
extracting separately owned candidate/reference subset manifests. Bind the
subset to the complete original input hash and per-slot identities; extraction
is stdlib serialization of retained bytes, not a coordinate transformation.

Keep every v15 and earlier source/evidence byte unchanged. Create separately
versioned v16 source, tests and evidence. Versioning the acceleration module is
permitted for import ownership only; retain its Decimal80 mathematics unchanged.
Preserve the 200 state/iteration caps and the actual low-level operand observer,
immutable cache keys, source chain, supervisor and strict decision machinery.

### R2 — Evaluate centered pixel errors directly (SC-01/03 prerequisite; SC-05)

Expose the distorted focal-plane projection **before** principal-point addition
inside the candidate's first-order and full projection paths. At observation
preparation form `centered_observation = observed - principal` once, then
`error = focal_projection - centered_observation`. Freeze this operation order,
the existing division/multiplication order, camera/observation order and all
normalizations in source and the plan. Do not recover the focal term by
subtracting the principal point from an already rounded pixel prediction.

Use this one retained error consistently for authoritative image F/G/H and
robust residual/J. Preserve the mathematical soft-L1 definition, normalization,
projection/depth guards, physical/q scale factors, acceleration and constraint
definitions. The transform-only path must use the same first-order error route
and still never enter curvature/depth preparation. Preserve an explicit pixel
prediction output if existing helper callers need it, but do not feed that
rounded prediction back into error calculation.

Keep the independent scalar basis/Jet method independent. Its existing
principal-minus-observation form already supplies the centered residual; do not
make it consume candidate errors, basis arrays, projections or gradients.
Retain both actual paths' error and spatial-gradient intermediates during their
already allocated preparation/objective entries, particularly observation 199;
record values that were consumed, without recalculating them for diagnostics.
No adaptive precision, alternate residual formula ladder or post-science repair.

### R3 — Represent analytical symmetry at construction (SC-01/03 prerequisite; SC-05)

For the candidate's analytical projection curvature, spatial objective curvature,
coefficient Hdata, Hdata+Hacc and their x/q/y reports, define one ordered
calculation for each unordered pair `(i,j), i<=j`, then store that calculated
value in both positions. Apply the same representation to objective-H congruence
outputs in saved-P/new-P reporting. Compute each selected congruence entry from
the original symmetric operand and P; do not compute a failing full result and
then average its triangles. Retain H/Hdata as distinct required comparison fields.

The reference must independently implement symmetric scalar second-derivative
pairs in Jet propagation and its physical Hessian assembly, and independently
transport the resulting symmetric objective matrices. It must not import the
candidate's assembly or congruence calculator. The driver's new-P transport of
retained reference H/Hdata needs the same explicitly defined reference contract;
otherwise the driver reintroduces the transport asymmetry after a correct report.
Plan must fix pair order, contraction/reduction order and source call sites for
both methods before toys. Matrix-valued interfaces may stay dense while their
construction stores a single analytical value per pair.

This recommendation does **not** permit symmetrizing an arbitrary supplied
matrix, averaging a detected failure, zeroing small entries, changing the
comparator, or suppressing either independent symmetry check. Preserve the
unchanged absolute `1e-10` gate and full independent component comparisons.
Keep Hz/Hg/acceleration mathematics unchanged; retain their existing full gates.
Validate the proposed symmetric primitive's precondition and reject an
asymmetric supplied objective-H operand before any transport. Analytical source
construction must establish the invariant, not a repair tolerance.

### R4 — Retain full readiness, add two fixed stress groups (SC-05; SC-01/03 prerequisite)

Carry forward all 20 actual v15 readiness groups and their coverage; adapt source
maps to v16, never replace production coverage with helper-only assertions.
Freeze **two** additional groups before suite 1, with an exact inventory:

1. One integrated weight-zero constant cubic scene through the real complete
   Candidate and independent Reference, one report each. Four identical control
   rows are `[2^-21 + 2^-62, 2^-22 - 2^-63, 2^-8]`; clamped knots are
   `[0,0,0,0,1,1,1,1]`; Q is `[0,0.5,1]`; one gauge camera has frames
   `[0,12.5,25]`, identity R, t/center zero, diameter 1, k zero, focal diagonal
   1024, principal `[512,256]`, and observed pixels `[512+1/8,256+1/16]`.
   There are no free offsets, n=3, dimension 12, actual vg/vby zero. Reuse the
   existing inactive four-column setup by its exact mathematical key; no active
   map or SVD. The exact image errors are `[2^-44,-2^-45]`. Check their values
   explicitly, all full/split components, every Hessian entry and report frames.
   Use the closed constant/Bernstein trajectory and independently evaluated
   analytic projection derivatives as the oracle, including the small residual
   before multiplication by the large Jacobian. Plan freezes a dyadic nonidentity
   report transform/inverse using the existing toy block, not a searched matrix.
2. A standalone three-dimensional symmetric congruence with fixed dyadic operands
   `H=[[2^40,2^20,-2^18],[2^20,3,-1],[-2^18,-1,2]]` and
   `P=[[1,1/2,0],[1/2,2,1/4],[0,1/4,1]]`. Run one real candidate and one
   independent reference congruence. Compare **all nine** entries to an exact
   Fraction double-sum oracle and require exact stored symmetry. Then provide
   one copied input with only H[0,1] increased by 1; both production primitives
   must reject before transporting it. Keep the existing comparator's deliberate
   asymmetric-output rejection as a separate unchanged readiness assertion.

These add exactly one successful complete Candidate, one successful complete
Reference and one primary report each to v15's suite, with no new metric/SVD
or active-acceleration work. Per suite totals become 17 Candidate complete
attempts (15 successful plus two prescribed rejected entries), five Reference
complete attempts (three successful plus two prescribed rejected entries), and
the same two cold transforms/two SVDs. Plan must enumerate the fixed extra
standalone congruence calls, oracle arithmetic and rejection entries separately,
plus all new instrumented projection/pair-construction boundaries. No hidden
complete evaluator or additional scientific fixture in the toy process.

Both full methods must meet the existing toy and production tolerances. The
stress oracle may use one fixed explicit Decimal80 sqrt for its analytic soft-L1
factors and exact Fraction algebra for dyadic projection/congruence; this is an
oracle definition, not a candidate precision experiment or ladder. Preserve all
fixture/test bytes after freeze. Suite 2 remains conditional on a documented
implementation correction to a failed suite 1, with unchanged frozen tests.

### R5 — One subset pass, strict strata and no qualification shortcut (SC-05; SC-01/03 prerequisite)

For original cases 12 and 13 retain v15's complete per-case schedule: one cold
Candidate/report, all five returned request sequences and repeats, one cold
residual/J/SVD transform, the five public probes, saved-P extra transport for
sequence 5; then one independent cold/returned pair and all component/new-P/
historical comparisons. Save all actual wrappers, consumed operands and receipts.

The exact planned science count is **211 low-level entries**:

| Boundary | Candidate | Reference |
| --- | ---: | ---: |
| Setup | 2 | 2 |
| Complete | 12 | 4 |
| Transform-only context | 2 | 0 |
| Preparation | 14 | 4 |
| Objective/residual | 12 | 4 |
| Residual-only | 2 | 0 |
| Data H / full sum / raw depth / bounded values / weighted Hz / bounded Hg | 12 each | 4 each |
| Returned report / cold report | 10 / 2 | 2 / 2 |
| Metric/SVD | 2 | 0 |
| Saved inverse | 10 | 2 |
| Public probe | 10 | 0 |
| Extra saved-P transport | 2 | 0 |
| Active acceleration | 7 | 2 |

These are 159 Candidate and 46 Reference entries, plus four driver component
contexts and two new-P contexts. There must be 12 canonical report comparisons,
10 public probe results, two new-P comparisons and two historical corroborations.
The new scalar/pair arithmetic belongs inside its enumerated component entry;
freeze real helper counts without adding an unrecorded evaluation pool. No
failure-driven extra case or rerun is allocated. Candidate/reference setups are
separately owned. Historical archive values remain available only after both
methods finish and only to the comparison driver.

Retain all production shapes, reference-oriented error formulas, rational
acceleration checks, inactive exact-zero contracts, symmetry checks, actual
multiplier checks, transformed norms and remap checks. New-P changes caused by
the centered residual/J are measured and retain their own bytes; never replace
the original saved P/origin. The two new-P public probes may continue to fail;
record them separately and keep the legacy public dimension rejected. Do not
change that outcome to pass because canonical or algebra checks improve.

Plan acceptance is complete, audited implementation/readiness and a retained
adjudication within its bounds; the desired arithmetic result is every required
canonical/new-P numerical check passing on all four selected states with no
control regression. If it fails, retain the original and new exact residual,
spatial G, G/Cd/Cb/KKT and H operands and continue to a later authorized Review.
Even a desired arithmetic result is explicitly a subset result. No old pass is
automatically promoted to qualification of changed source on an unexecuted case.

### R6 — Scoped resources and automatic handoff (SC-05)

Recommend the following new plan-specific allocation for Plan to finalize and
parent to bind in a new authorization artifact before Implementation:

| Scope | Hard limit |
| --- | --- |
| Implementation including admission, source, toys, science, evidence and commits | 5,400 elapsed seconds from a fresh parent T0 |
| Read-only admission completed | T0 + 600 seconds |
| Frozen source coverage and applicable passing readiness | T0 + 3,600 seconds |
| Science plus every owned process stopped | T0 + 4,500 seconds |
| Scientific invocation | One, at most 600 wall seconds including imports/setup/comparison/I/O/cleanup, also bounded by the absolute cleanup deadline |
| Fixed 22-group toy suite | At most two supervised invocations, at most 120 wall seconds each |
| Scientific methods/cohort | One candidate / one independent reference; exactly cases 12 and 13 cold/returned and the 211-entry schedule above |
| Numerical concurrency | One numerical worker and its supervisor; one thread per numerical library; no overlapping toys/science |
| Optimizer / initialization / local fit / restoration / diagnostic ray / finite difference / new scientific state | Zero |
| Training / rendering / GPU/device / network/download/install | Zero |

Use the existing `.local/envs/calibration-global/bin/python`, installed
NumPy/SciPy and stdlib. Set OMP_NUM_THREADS, OPENBLAS_NUM_THREADS,
MKL_NUM_THREADS and NUMEXPR_NUM_THREADS to 1 before numerical startup. Preserve
the worker/token/source/admission guards and five-second termination reserve.
The final 900 phase seconds are for retention, validation and commits. The
600-second science cap allows substantial margin over v15's approximately
893-second full 16-case schedule for this two-case subset, while bounding the
new scalar symmetric assembly; that estimate is not a guarantee. Check deadlines
inside pair and observation loops. No profiling run or pilot is allocated.

Missing admission/readiness prohibits science. An invocation consumed at launch
is spent even if setup fails. No unchanged green rerun, ad hoc numerical import,
post-science source repair or numerical retry. Unused time does not authorize
more attempts. Required permission retry/stop rules remain binding independently
of numerical allocation; never silently duplicate partially completed work.

AGENTS.md standing approval `b62f2ea` and the explicit same-objective resume
cover Review-recommended/Plan-finalized eligible limits without routine budget
confirmation. Parent must compare the saved plan against applicable ceilings
and record the plan hash, T0/deadlines, limits, scope, historical consumption and
standing-approval basis before dispatch. This Review itself grants no invocation.

All previous allocations remain terminal. Plan 022 consumed one toy suite
`2.557443101` seconds, one science invocation `893.138139580` seconds, and final
phase `3878.114624024` seconds; its unused toy/time cannot be reused. Preserve
implementation commit `fda79c9`, checkpoint `6592cba` and assessment `63a1c59`.
Training remains **22523.417254 charged seconds**, unchanged under the 24-hour
total and 7200-second method/scene ceilings; no allocation redistribution or
budget-stopped restart. No overall loop/Review/Plan ceiling was supplied.

### R7 — Continue from the measured arithmetic result (SC-01/03; preserve SC-02/04/05)

If the subset arithmetic passes, the next fresh Review should choose a concrete
coordinate/state protocol design that preserves authoritative canonical ownership
and separately records the failed legacy inverse/forward contract. Any new
protocol needs its own fixed synthetic equivalence/derivative/identity checks and
must not count as a legacy replay pass. If arithmetic fails, diagnose the exact
remaining recorded operation before recommending another finite intervention.
Neither branch authorizes execution beyond the next plan above.

Keep [Plan 015 sections 6 and 8](../../../plans/plan_015.md) fully binding:
the focused benchmark, 144-attempt/48-problem conditioning screen, original
94 retained qualifications, recovery/KKT requirements, scalar search beginning
with 7,344 required path attempts and all refinement/path/basin checks, then the
gated combined pilot. No evaluator arithmetic result waives their requirements.
Keep `accepted_timing`, `production_candidate` and `final_validation_protocol`
null, and `ready_for_full_screens`/`main_objective_attained` false.

## Handoff and stop conditions

This Review created only this recommendation artifact. It started no numerical
worker or background job, used no delegation, made no commit and encountered no
permission, Git or execution failure. No jobs owned by this Review remain; the
prior implementation recorded clean shutdown. No user interruption, applicable
overall-budget stop or verified objective attainment applies. Parent should
inspect this artifact, assess all criteria, save/commit its checkpoint as required,
and automatically dispatch a fresh Plan stage. This is an active unmet objective,
not a blocked or successful-completion report.
