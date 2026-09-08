# Iteration 006 Review — correct evaluator readiness and qualify the fixed cohort

Recommend one new **v15 correction and conditional full-cohort qualification**
allocation. Correct the concrete v14 source, interface, comparison and evidence
gaps below; freeze a suite that calls the complete implementations; then perform
the same 16-case/32-state operating experiment exactly once if readiness passes.
The next step is not another acceleration arithmetic ladder or a helper-only
readiness milestone. Keep Decimal80, the independent scalar-jet/rational method,
the original operating operands and all scientific thresholds unchanged.

The [objective](objective.md), [status](status.md),
[latest assessment](iteration-005-assessment-03-implementation.md),
[repository instructions](../../../AGENTS.md), [Plan 021](../../../plans/plan_021.md),
[implementation](iteration-005-implementation.md), [validation](iteration-005-validation.md)
and complete v14 source/test surfaces were read before making these recommendations.
SC-01 and SC-03 remain **not met**: evaluator qualification is their prerequisite,
not accepted Basketball timing or a reconstruction comparison. SC-02/SC-04 remain
met on their existing supported SelfCap evidence. SC-05 remains met with the
[recorded historical limitations](iteration-001-assessment-03-implementation.md);
this Review does not supply new model or numerical evidence.

## Retained baseline and scope

- [V14 report](../../experiments/basketball-shared-timing-v14.md),
  [admission](../../experiments/basketball-shared-timing-v14/admission.json),
  [coverage gaps](../../experiments/basketball-shared-timing-v14/readiness-coverage.json),
  [static finding](../../experiments/basketball-shared-timing-v14/static-findings.json),
  [package validation](../../experiments/basketball-shared-timing-v14/package-validation.json)
  and [budget](../../experiments/basketball-shared-timing-v14/budget.json) establish
  admitted inputs and incomplete readiness, with zero scientific invocations or
  entries. Both frozen toy invocations passed their implemented assertions;
  neither exercised the missing integrations.
- Both v14 input copies hash to
  `1b4779b8c0328f9f893af6c2cd1b2fa9133bdad337467a2f805525d8913c1eed`.
  Admission hashes to
  `7f294998d9ee7f12448740710bd7951ec503f111297a96582024f843e240611c`.
  The frozen test hash is
  `4328425c083266f87fc38594d293a148becee179be4a8660cde777eefd834cdc`.
  These hashes were checked by byte reading only in this Review.
- Plan 021 is terminal: two toy slots, 2.873430340 toy seconds,
  1653.358525463 final phase seconds, zero scientific time/entries/invocations,
  commits `147e0cb` and `0c5100b`. Its unused science is not available to v15.
- The [v13 integration map](../../experiments/basketball-shared-timing-v13-integration.md),
  [iteration 005 Review](iteration-005-recommendations.md) and
  [Plan 015](../../../plans/plan_015.md) still describe the remaining full evaluator,
  focused solver, screen and reconstruction gates. V13 qualified only six costs
  and 36 selected partials. V11 A2/A3 failures, V12's 25/36 primary and 17/36
  independent gradient failures, and the other 57 unadjudicated ray failures
  remain unchanged.

Use new `_v15.py` versions of the six v14 modules, a new v15 test file and
`docs/experiments/basketball-shared-timing-v15/`. Preserve v14 source and evidence
byte-for-byte, including its unsuccessful readiness. The acceleration method
itself is carried forward without a precision/method change; versioning permits
clean source binding and toy instrumentation without touching historical pins.

## Findings that must be closed before the next frozen suite

These are static source findings and missing validation, not newly measured
scientific discrepancies. Each R item advances SC-05 and the evaluator
prerequisite of SC-01/SC-03.

| ID | Evidence and practical implication | Required correction and observable validation |
| --- | --- | --- |
| R1 | [Components](../../../scripts/basketball_shared_components_v14.py), `projection_second` and `Candidate.prepare`: `residual_only` does not skip HP/HT/Hcam/H. Preparation also creates/evaluates the second spline derivative and assembles normalized constraint depth even for a transform context. The retained finding covers the projection omission; source inspection identifies the rest of that path. | Factor a real first-derivative preparation path. Cold-transform preparation may build projection values/J and necessary B/B', but must not enter projection curvature, B'', objective-gradient/Hessian or constraint-depth/curvature assembly. A real transform-only Candidate call must produce residual/J while throwing sentinels on those forbidden boundaries remain unentered. Distinguish projection camera-z needed for perspective from the separate normalized constraint-depth calculation. |
| R2 | [Tests](../../../tests/test_basketball_shared_evaluator_v14.py) never call `Candidate.evaluate` or `Reference.evaluate`. Case 12 builds independent B/T factors directly; case 13 builds a weighted Hessian from arbitrary J/Hz; case 11 tests spatial helpers only with zero center/unit diameter. Thus neither full image/acceleration assembly, free-offset mixed curvature, normalization, full reference chain nor real bounded curvature is covered. | Execute both full calculators on the fixed tiny integrated fixture below for both weights. Check every split/full component and physical/q/y derivative, especially free-offset and coefficient-offset Hessian entries, actual z/Jz/g/Jg/Hz/Hg, and inactive acceleration. Compare against closed-form cubic derivatives and an independently assembled spatial chain; do not manufacture candidate outputs or use candidate basis arrays as the reference. |
| R3 | Case 14 sets `counts['T']=1`. The real transform builder is nested inside [worker](../../../scripts/basketball_shared_evaluator_v14.py) and cannot be tested through a small reusable production entry. The SVD helper retains a second-SVD fallback, guarded only at this one worker call site. | Extract the actual cold residual/J plus metric/SVD construction into a callable used by both toys and worker. Put the rows>=coefficient-columns guard at that entry before SVD; exactly one SVD, no fallback. Execute an actual `TransformCache` first request and repeat with an independently observed residual/preparation/SVD counter and throwing repeat calculator. Verify rank/scale/subspace coverage, inverse, symmetry, inactive scales and exact nuisance identity/cross blocks. |
| R4 | Worker traversals call `Adapter.request(field, public=True)` rather than `fun/jac/hess/constraint/constraint_hessian`. `request('G'/'H'/'C'/'CH')` returns physical arrays even when its public admission flag is true; the wrappers select y arrays from the report. Existing mock tests use identity D/P and do not call the derivative/constraint wrappers. A report comparison therefore does not qualify the actual public callback surface. | Give canonical requests explicit coordinate semantics and use the real y callback methods for an admitted public traversal. All six public surfaces and their repeats must agree with the independently transported y outputs. Do not count a guard flag as callback coverage. Exercise a nonidentity D/P toy and both accepted and rejected replay branches; rejected public requests must enter no new evaluation. Keep the prescribed canonical traversal on rejected operating replays and classify the public failure separately. |
| R5 | [Accounting](../../../scripts/basketball_shared_accounting_v14.py) freezes cached arrays but stores mutable `Adapter.input` and an unfrozen `bound_inverse`; `Candidate.case/setup` are mutable containers. The toy checks result/State arrays, not those governing operands. `Audit.observe` is reached using `dict(state)` supplied by the same wrapper; its negative toy manually calls the audit instead of tracing actual decoded Candidate/Reference inputs. | Own immutable copies of state/multiplier/transform and shared geometry operands, including the saved bound transform used by sequence 5. Observe actual decoded x/coefficient/multiplier bytes and setup-key operands at the production entry boundaries. Test these real paths, caller mutation isolation, wrong multiplier/state rejection before math, no cross-adapter result reuse and interrupted-entry retention. Preserve both 200 caps and immutable scope identity. Do not describe a copied expected label as independently observed operands. |
| R6 | [Harness](../../../scripts/basketball_shared_evaluator_v14.py), `run`/`worker`: launch checks current sources/environment, but does not fully revalidate readiness-to-admission/input/auth links before scientific input consumption. `ready` trusts an externally authored coverage `passed` field without binding each required behavior to the frozen source/test/outcome. Existing guard test calls `worker_guard` only; source-mutation test calls `hashes` only. | Add one read-only admission/readiness chain verifier shared by ready/run/worker and bind all immutable inputs, auth, source/test, historical/environment manifests and deadlines. Verify before invocation consumption/spawn and again before worker numerical imports. Freeze a coverage map with fixture IDs, actual production call sites, independently observed boundaries and concrete output assertions; require matching passing results and source hashes for every row. Test launch rejection for mutated input/auth/source and an incomplete coverage map using tiny temporary JSON/byte fixtures. |
| R7 | `comparisons`/new-P loop: new-P `Hz/Hg` use `(2e-5,3e-5)` instead of frozen `(2e-5,2e-5)`; `KKT_inf` is skipped. New-P symmetry is not checked for each transported Hessian. Saved-P inverse/symmetry and exact nuisance blocks are not explicitly adjudicated. Weight-zero arrays receive approximate comparisons despite the exact-zero contract. `archive.json` is retained but never compared. | Use one frozen field/frame comparison specification, with required keys/shapes and the original orientation/tolerances. Include new-P norm/constraint-Hessian/symmetry checks, saved and new transform algebra, exact zero/identity contracts, and actual/remapped multipliers. Compare retained historical returned fields with the already computed independent reference within the same returned comparison context, labeling discrepancies and preserving historical decisions. Exercise the production comparison driver with fixed tiny passing/failing arrays, missing field/shape, asymmetric tolerance, rational forward-error and strict constraint-Hessian cases; no tolerance tuning. |
| R8 | `package` checks only entry upper caps, pairs entered/actual lists, and treats a worker-complete file plus clean process exit as complete. It does not require the exact schedule, all completed receipts, all 96 canonical report comparisons, 80 public probes or 16 new-P comparisons. Comparison contexts are journaled after arithmetic. Missing summary/check rows can yield zero failures. | Freeze an expected schedule manifest. Consume comparison/transport contexts before their math, retain completion/hash receipts, and enforce exact identities, fields, counts and ordering for qualification. Reconcile entered/completed/interrupted/unknown records and every output/comparison hash. Test the actual retained-only validator/decision reducer with a complete tiny schedule and fixed missing/duplicate/interrupted/wrong-hash cases; absent evidence must be incomplete. Keep known failures visible when other work is missing. Packaging must work after failed readiness or partial execution and must not require a passing last toy just to retain a failure. |

The fixes are bounded to these existing evaluator interfaces. Do not turn the
injected/mock `solve` function into a general optimizer implementation in this
allocation. Its evidence must remain explicitly callback/completed/interrupted
report wiring at owned states, with optimizer invocations zero. Wrong state or
multiplier returns must retain an error and cannot be labeled a successful solver
return. No claim of focused solver qualification follows from a mocked callback.

## A concrete readiness design that exercises the production path

Plan should retain 20 named fixture groups, preserving the useful v14 analytic
kernel/jet cases 1–11 and replacing or extending cases 12–20 as mapped below.
Freeze the complete definitions, subcases, expected output fields, call sites,
entry counts and test source before suite 1. A green suite is insufficient if a
required coverage row is missing. Perform a source-only map review before that
freeze, including the production worker call graph and comparator/decision path.

Use one small deterministic integrated scene, in weight-zero and weight-one
variants, rather than archived operating states or generated random data:

- Cubic Bezier knots `[0,0,0,0,1,1,1,1]`, quadrature `[0,0.5,1]`, one group;
  controls `[[0,0,4],[1,0,4],[1,1,5],[2,1,6]]`, free camera `[3]`, offset zero.
- Cameras 1 and 3 each observe fixed frames `[0,5,10,15,20,25]`, fixed xy zeros;
  center `[1,-2,3]`, diameter 2, n=12. Camera 1 is identity R/K, t=0, k=0.
  Camera 3 has R mapping `(X,Y,Z)` to `(-Y,X,Z)`, t=`[1,-1,2]`,
  K=`[[2,0,0.25],[0,3,-0.5],[0,0,1]]`, k=1/8. This exercises normalization,
  distinct camera geometry, nonzero motion and all offset/mixed derivative terms.
- D=`diag(25,1,...,1)`. For an exactly replayable saved-transform toy use origin
  zero, offset P block 1, first two coefficient coordinates block
  `[[1.25,0.75],[0.75,1.25]]` and remaining coefficient diagonal 2. Its inverse
  and these state operations are dyadic. Retain the existing large-origin replay
  rejection fixture separately. Use fixed nonzero, nonuniform depth and bound
  multipliers; Plan must list their exact bytes/formula before freeze.
- Expected trajectory derivatives use the closed cubic Bernstein polynomials
  and their first/second derivatives, including `-B'C/25`, `B''C/625` and
  `-B'/25`. The already analytically checked independent spatial jet rules can
  assemble the spatial chain, but candidate B/T/curvature outputs cannot become
  the oracle. Verify the independent Reference's assembled output too. Compare
  every entry, not selected directions or transport self-consistency alone.

| Fixture group | Required real calls and assertions (mapping) |
| --- | --- |
| 1–11 | Preserve fixed kernel/jet/spatial analytic checks, Decimal context, exact weight-zero and invalid-domain behavior; do not add an arithmetic ladder. R1/R2 prerequisites. |
| 12 | Full `Candidate.evaluate` and `Reference.evaluate` on both integrated weights; analytic full/split F/G/H/r/J and free-offset/mixed chain in x/q/y, with nonzero center/diameter and both cameras. R2/R4. |
| 13 | Actual integrated z/Jz/g/gp/gpp/Jg and weighted raw/bounded Hessians for the fixed multipliers; returned force/KKT/complementarity and new/saved bound-transform remap. The old arbitrary J/Hz hand calculation may be corroboration only. R2/R5/R7. |
| 14 | Five fresh real Candidate adapters for each weight, actual public callbacks when replay is exact, canonical fallback on a rejected replay, complete repeats with independent low-level counters. Real cold-transform production entry/cache repeat for both weights; forbidden second-order/preparation repeats throw. Include actual SVD/metric assertions and one fixed undersized-matrix rejection before SVD. R1/R3/R4/R5. |
| 15 | Mock optimizer calls all supplied callbacks with nonidentity D/P and a real provider; ordinary callback, completed and interrupted report share the coherent owned result, actual multipliers and identity. Wrong return state/multipliers stay errors. Keep a deliberate cached fixture where authoritative F/G differ from residual-derived arithmetic to detect accidental `r@r`/`2J.T r` reporting. R4/R5. |
| 16–18 | Existing byte/signed-zero/scope/cap/exception tests plus actual input/setup/transform immutability, real low-level operand sentinel, rejected multiplier, consumed interruption and unchanged entry counts on repeats. Fixed integer 200-state toy only, no fit. R5/R8. |
| 19 | Real launch/readiness chain validation on tiny temporary manifests; public rejection before evaluator entry; production comparison/decision reducer with the fixed positive/negative cases listed in R6–R8. Required field and complete-schedule checks cannot be replaced by a `passed=True` fixture. R4/R6/R7/R8. |
| 20 | Supervised real tiny process tree for deadline and interruption, direct-worker rejection before numerical import, exclusive markers and retained partial logs. R6/R8. |

Recommend per-suite limits of at most 20 complete toy Candidate bundles, six
complete toy Reference bundles, two real toy cold residual/J/metric constructions
and two SVD calls, with the existing fixed kernel-helper calls in cases 1–11
separately enumerated by Plan. The undersized rejection allocates no SVD. These
are ceilings, not a reason to repeat calculations: case 13 may consume case 12's
retained complete outputs for assertions, and repeated callbacks use their owned
cache. Plan must freeze the exact subcase call inventory before Implementation;
any actual new toy numerical work must appear there. Kernel-only setup calls,
full integrated bundles and SVDs must not be hidden in one generic toy count.

Allow at most two supervised suite invocations, each 120 wall seconds including
imports, checks, I/O and process cleanup. Use suite 2 only for a justified
implementation correction after suite 1, with identical frozen test definitions;
do not rerun an unchanged green suite routinely. If the frozen test itself omits
a requirement, retain incomplete readiness under this plan. No ad hoc evaluator
import, finite difference, archived-fixture test or development numerical probe
outside those suite slots is recommended.

## Conditional scientific qualification and complete adjudication

Preserve exactly Plan 021 sections 3–6 and 8's cohort, independent mathematics,
request order, public replay decision and scientific entry ceilings, adjusted
only for the concrete correctness/evidence fixes above. Read-only admission may
copy the two pinned v14 input files into separately owned v15 input directories
after verifying their complete original provenance chain; this is explicitly
authorized source reuse, not replacement of failed network access. Revalidate
the historical original operands/identities, dependency/source substitutions,
quadrature and environment bytes; never generate observations, knots or a state.

The same 16 cases and 32 cold/returned slots remain mandatory. There are still
96 complete Candidate contexts, 32 complete Reference contexts, 16 cold-transform
contexts, 16 coefficient SVDs, two geometry setups per method keyed weight 0/1,
49 active Candidate acceleration traversals and 14 active Reference traversals.
Both 200 caps remain unchanged, including scopes. The exact low-level matrix
from Plan 021 section 6 remains the maximum, with added explicit comparison/
transport receipts inside its already allocated 32 component and 16 new-P
comparison contexts. No added operating-state evaluation is needed for R7/R8.

The schedule must establish all 16 cold plus 80 returned Candidate results,
32 Reference results, 96 canonical report comparisons, 80 public replay decisions,
16 new-P comparisons and corresponding cache/request records. Report cold,
returned, weight-zero, regularized-control and joint-offset strata separately.
Require exact completion and all required checks, not merely counts below caps.
Canonical/reference calculations remain independent; Pnew enters only the later
comparison driver after Reference is closed. No rounded replacement public state
or search for an exactly replaying y is allowed. Preserve original actual bound
multipliers in all returned reports; remapped multipliers are algebra tests only.
Historical-field comparisons are a separately labeled corroboration stratum;
they do not replace the independent reference, retrospectively change historical
qualification, or turn a disagreement with old arithmetic into a failure of a
new component that agrees with the independent reference. Plan must freeze that
separation in its decision schema before results.

Keep every Plan 021 tolerance and comparison orientation, including strict
constraint-Hessian tolerance in new-P checks. Scalar/array comparison policy
must be centralized to avoid branch drift. Retain per-entry candidate/reference,
error/allowed binary64 bytes and failed indices, plus exact rational acceleration
oracles/errors. Dense shape-tagged byte arrays may replace millions of repeated
JSON dictionaries without dropping entries or changing comparisons. This storage
choice helps fit the finite pass; it does not authorize approximations or fewer
comparisons. Check deadlines within long comparison/rational/setup loops, and
consume each context before its arithmetic. Package afterward from retained
JSON/bytes/hash/counts only, with no scientific imports or recomputation.

Use distinct statuses for source/coverage readiness, package integrity, schedule
completion, canonical numerical qualification, public API qualification and
overall fixed-cohort qualification. A missing result/check is incomplete; an
observed mismatch is failed even if later work is missing. Record both. An
integrity failure stops dependent execution immediately. A normal numerical
failure may retain the remaining already scheduled independent slots within the
same invocation/deadline; it never permits a repair, retry or replacement state.

## Recommended new allocation and standing approval

| Scope | New hard ceiling |
| --- | --- |
| Entire v15 Implementation, including admission, source work, toys, supervision, evidence and local commits | 7,200 elapsed seconds from a new parent T0 |
| Read-only admission completed | T0 + 900 seconds |
| Complete frozen readiness, including real coverage and final applicable suite | T0 + 4,800 seconds |
| Scientific pass and owned-process cleanup ended | T0 + 6,300 seconds |
| One supervised scientific invocation, including imports, setup, all comparisons, I/O and cleanup | 1,500 wall seconds, also bounded by T0 + 6,300 |
| Candidate / independent reference methods / scientific invocations | 1 / 1 / 1; no retry |
| Scientific states, bundles, setups, SVDs and component entries | Unchanged fixed limits stated above and in Plan 021 section 6 |
| Frozen toy suite invocations / per-invocation elapsed limit | At most 2 / 120 seconds, all within readiness and phase |
| Numerical concurrency | One numerical worker and its supervisor; one thread per numerical library; no overlapping toys/science |
| Optimizer/local-fit/initialization/restoration attempts; scientific finite differences, rays, pilots/full screens | 0 |
| Training, rendering, GPU/device work, network/download/install | 0 |

The larger finite development window covers the newly identified real interface
and adjudication fixes; the 1,500-second supervised allowance covers full rational
Hessian transports and detailed complete-array evidence rather than adding any
operating evaluation. This is a new plan allocation, not measured runtime or a
guarantee of completion. No pilot timing probe is proposed. Retain partial work
if a deadline is missed. Reserve the final five numerical seconds for TERM/KILL/
reap and 900 phase seconds after the science deadline for evidence and commits.

Use the existing `.local/envs/calibration-global/bin/python`, installed NumPy/SciPy
and stdlib Decimal/Fraction; set the four existing numerical thread variables to
one before startup. Training remains **22523.417254 seconds** under the 24-hour
total and unchanged 7200-second method/scene ceilings. Historical Plan 016–021
clocks and consumption remain unchanged, and no stopped method is restarted.
No overall loop ceiling was supplied; these limits apply to the new plan only.

AGENTS.md standing approval `b62f2ea` and the explicit active same-objective resume
cover these Review-recommended limits once finalized by Plan. Parent must compare
the saved decision-complete plan against remaining user ceilings, record its hash,
scope, T0/deadlines, historical consumption and approval basis, then dispatch
Implementation automatically if eligible. No routine execution-budget question
is needed. The Planner may make routine implementation choices but must not add
methods, states, suite invocations, optimizer attempts or change gates to fit them.

## Acceptance and the following review

Require R1–R8's frozen coverage map, admission, bounded owned execution, complete
independent comparison evidence or explicit missing/failed evidence, final budget
and job reconciliation, and validated task-only local commits. Source checks and
readiness can pass while operating qualification fails; a properly retained
failure remains a valid implementation milestone. Parent owns criterion/status
assessments and must not equate that milestone with main-objective attainment.

If the fixed cohort qualifies, move directly to Review of one finite
full-coordinate focused solver intervention with a fresh baseline, using the
retained failed starts/returned KKT and the now-qualified full evaluator. Address
weight-zero initialization/stopping/observable-growth evidence explicitly;
acceleration arithmetic cannot fix an inactive term. If canonical components
fail, choose the exact recorded component/coordinate defect for repair. If only
public replay fails, choose a finite solver-coordinate/state-ownership design.
If readiness/execution is incomplete, identify the precise missing prerequisite
from its retained coverage/schedule record. Do not default to an expanded passing
cohort or another extreme-state precision ladder.

All [Plan 015 sections 6 and 8](../../../plans/plan_015.md) gates remain binding:
all focused targets and dependencies qualify within both 200 caps; preserve
controls/costs and all-three-path agreement; resolve missing seeds, transform,
support, growth, initialization and stopping failures. Full conditioning remains
144 attempts/48 problems, all 94 prior v6 qualifications preserved, at least 25/50
recoveries across groups and median KKT ratio <=0.1. Independent scalar screening
retains 7,344 initial paths, inclusive 0.05/0.01 refinements and all nine basin/cost
comparisons. Both screens precede the 144-path combined pilot and subsequent
evaluator, selection and final-validation gates before accepted Basketball timing,
validated preparation/reconstruction and measured quality/motion/speed/resources.
Keep KKT <=1e-6, qualification depth >1e-7 and competitive objective tolerance
`1e-6 + 1e-4*max(abs(F1),abs(F2))`; preserve the existing splits and held-outs.

Publish `accepted_timing=null`, `production_candidate=null`,
`final_validation_protocol=null`, `ready_for_full_screens=false` and
`main_objective_attained=false` for this evaluator plan under every outcome.
SC-01/SC-03 stay not met until their complete saved outcomes are established.
An eligible subsequent Review/Plan continues automatically after this finite
allocation; no spent allowance is reusable and no historical evidence is revised.

## Review execution record

This Review read local Markdown/source and retained JSON, inspected Git status
read-only and computed file hashes. It performed no scientific imports,
evaluations, tests, transforms, fits, training, GPU/network/install work or Git
mutations. Only this recommendations file was written. No subagents were
delegated, no commands failed, no permission retry was needed and no jobs remain.
There is no blocker to the next sequential Plan stage. Parent owns criterion
assessments, status and any local documentation commit.
