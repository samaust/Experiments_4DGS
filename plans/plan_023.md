# Plan 023 — Centered image errors and analytical objective symmetry on four retained states

## Objective, scope and authority

Implement [iteration 007 Review R1–R7](../docs/continuous-improvement/20260908-plan016/iteration-007-recommendations.md)
for the unchanged [objective](../docs/continuous-improvement/20260908-plan016/objective.md)
and [assessment](../docs/continuous-improvement/20260908-plan016/iteration-007-assessment-01-review.md).
Create v16 with direct centered image errors and independently constructed
symmetric analytical objective Hessians. After admission and frozen readiness,
adjudicate **original cases 12 then 13, cold and returned only**, once. This is
an arithmetic prerequisite for SC-01/SC-03 and reproducibility work for SC-05;
it cannot establish Basketball timing, reconstruction or the measured comparison.
Preserve supported SelfCap SC-02/SC-04 and recorded historical SC-05 limitations.

Read AGENTS.md, objective, status, latest assessment, Review and this plan before
Implementation and after context loss. Never read `prompts` content; no delegation.
Parent owns authorization, criterion assessments, status and checkpoint artifacts.
Implementation owns v16 source, tests, results and coordinated task-only milestone
commits. All interruption, git-failure and single safe same-command escalated
retry/permission stop rules apply. Source inspection is an implementation check,
not a request for additional user approval.

Standing approval AGENTS.md `b62f2ea` and the explicit same-objective resume cover
these Review-recommended, Plan-finalized allocations within existing ceilings.
Before dispatch parent records this plan/objective hashes, source scope, approved
limits, historical consumption, approval basis and fresh T0 with absolute UTC and
monotonic deadlines in `iteration-007-plan023-authorization.json` in the run
folder. This Plan starts no clock or numerical invocation.

## 1. Finalized finite allocation

| Scope | Hard limit |
| --- | --- |
| Entire Implementation: admission, source, toys, science, cleanup, retention, validation and commits | 5,400 elapsed seconds from parent T0 |
| Read-only admission finished | T0 + 600 seconds |
| Frozen source coverage and final applicable passing readiness finished | T0 + 3,600 seconds |
| Science and all owned processes stopped | T0 + 4,500 seconds |
| Science invocation, including imports/setup/comparisons/I/O/cleanup | One, at most 600 wall seconds, also bounded by T0 + 4,500 |
| Fixed 22-group readiness suite | At most two supervised invocations, at most 120 wall seconds each |
| Scientific methods and entries | One Candidate, one independent Reference; section 6's exact 211 entries |
| Numerical concurrency | One numerical worker and supervisor, one thread per library; no overlapping toys/science |
| Optimizer, initialization, local fit, restoration, diagnostic ray, finite difference, new scientific state or fixture | Zero |
| Training, rendering, GPU/device, network/download/install | Zero |

Use the existing `.local/envs/calibration-global/bin/python`, installed NumPy/SciPy
and stdlib. Set OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS and
NUMEXPR_NUM_THREADS to `1` before startup. Numerical deadline is
`min(invocation_start + invocation_cap, absolute_cleanup_deadline) - 5`;
the five-second reserve is for TERM/KILL/reap. Retain Plan 022 group 20's two
three-second process-tree subcases and two-second cleanup reserve. Check deadlines
inside observation, pair, basis/setup, rational and comparison loops. The final
900 phase seconds are reserved for retention, validation and commits.

Suite 2 requires a documented source correction to a failed suite 1, with
unchanged frozen test/fixture/assertion bytes. Retain original source mapping and
a source-only correction attestation; no test repair, omitted-coverage addition,
unchanged green rerun or third suite. Missing admission/readiness forbids science.
No pilot/profiling/ad hoc numerical import, post-science repair or scientific
retry is allocated. Launch consumption is terminal even when startup fails.
Unused elapsed time does not authorize extra attempts. Permission retry rules
remain binding but never duplicate a consumed or partially changed invocation.

Every previous allocation is terminal. Preserve Plan 022's one toy
`2.557443101` seconds, one science `893.138139580` seconds and final phase
`3878.114624024` seconds, commits `fda79c9`, `6592cba`, `63a1c59`, and all older
consumption recorded in [Plan 022 section 1](plan_022.md). Training remains
**22523.417254 charged seconds** under the unchanged 24-hour total and
7200-second method/scene ceilings. No redistribution or budget-stopped restart.
No overall loop/Review/Plan ceiling was supplied. This plan's exhaustion ends its
execution allocation; otherwise authorized fresh Review/Plan can continue.

## 2. Versioned surfaces, commands and admission

Create `_v16.py` versions of the six v15 modules in `scripts`: acceleration
Decimal, components, accounting, solver, independent reference and evaluator.
Create `tests/test_basketball_shared_evaluator_v16.py`, the
`docs/experiments/basketball-shared-timing-v16/` evidence directory and sibling
`.md` report, and run artifacts `iteration-007-implementation.md` and
`iteration-007-validation.md`. Every v15 and earlier source/evidence byte stays
immutable. Acceleration Decimal80 mathematics, exponent/trap policy, exact decode,
ROUND_HALF_EVEN context and rational reference acceleration remain unchanged;
version/import ownership and deadline plumbing alone may change there.

Preserve the stdlib harness commands `admit`, `toy`, `ready`, `run`, `package`,
and guarded internal `worker`/`toy-worker`. Invoke the installed Python with
`scripts/basketball_shared_evaluator_v16.py <command>` from the repository root.
Admission and packaging import no numerical module. Numerical imports occur only
inside owned supervised toy/science workers after exclusive consumption markers,
source/auth/input checks and PID/PGID/SID/token checks. Keep markers permanently;
collisions fail. Record exact environment and commands. No direct test entry.

Admission first verifies both complete v15 input files against
`1b4779b8c0328f9f893af6c2cd1b2fa9133bdad337467a2f805525d8913c1eed`
and v15 admission against
`0b64d71529fb0ac06e9a48998e53c3957b2d76249f64e3b1c48d96eaf32d1b18`.
Verify its full admission/source/readiness/environment/package chain and the
original v10 journals, receipts, callback/state/dependency identities and v11–v14
pins/substitution attestations required by [Plan 022 section 3](plan_022.md).
Read-only provenance verification still covers the complete original input set;
no numerical work on excluded cases is permitted.

Then serialize separately owned candidate/reference subset input manifests using
stdlib only, selecting original indices 12 then 13 without reindexing:

| Original index | Original ID | Weight | Slots |
| --- | --- | --- | --- |
| 12 | metric/joint-00/descending | 1 | original cold, returned |
| 13 | metric/joint-01/cold | 0 | original cold, returned |

Both have dimension 55, free camera `[3]`, 18 coefficient rows, 300 observations
in original camera 1/2/3 and frame 50..149 order, 150 retained quadrature samples,
one original group, spacing 10, gauge camera 1. Preserve every case/state field,
actual vg/vby, saved y, q/x, D, P, origin and original ledger identities. Bind
complete-input hashes and each selected case/slot payload hash in a selection
manifest. Derive no coordinates, quadrature, multipliers or states during
extraction. Keep historical archive entries indexed by original index (a keyed
driver-only mapping prevents accidentally selecting archive element 0 or 1).
Archive/classifications are unavailable to mathematical methods and are read by
the comparison driver only after both methods finish.

Keep the shared `verify_chain` graph from Plan 022: parent auth -> admission
source/input/provenance/environment/historical leaves -> frozen coverage/test/
source/readiness -> consumed marker/worker identities -> per-entry receipts ->
retained-only package validation. Extend it with v15 originals and subset
selection leaves. Validate actual leaf bytes and paths at admission, ready, run
before consumption and worker before numerical import; reject excluded paths.
Freeze expected substitutions explicitly; rewriting a manifest is not evidence
that changed bytes were authorized. Preserve all old hashes at packaging.

## 3. Fixed image-error arithmetic and analytical pair contract

Only objective-image arithmetic and its representation change. Preserve first
order division/multiplication, robust soft-L1, guards, scale factors, time/basis
and camera/observation order, acceleration, z/Hz/Hg and public coordinates.

### 3.1 Direct centered residual

In candidate `projection_first` and `projection_second`, retain the distorted
focal term immediately after
`(u * (1 + k * sum(u*u, axis=1))[:,None]) @ K2.T`, before principal addition.
Keep existing `c=(xyz*diameter+center)@R.T+t`, `u=c[:,:2]/z[:,None]`, projection
Jacobians and their operation order. Preserve pixel prediction as
`focal + principal` for existing helper callers. Use an optional
`return_focal=True` keyword: first-order returns prediction/J/focal; full returns
prediction/J/H/focal. Default tuple arity remains two/three for existing tests.
The full projection must not call `projection_first` as an extra helper entry.

At each prepared camera batch calculate `centered_observation=observed-principal`
once, then `e=focal-centered_observation` once. Never subtract principal from an
already rounded prediction. Retain and reuse this exact e for pointwise image
F/G/H and robust r/J. Full preparation keeps
`s=sqrt(1+sum(e*e,axis=1))`, `point_g=2*e/(n*s[:,None])` and existing spatial-G
contraction. F and G retain v15's camera-batch reduction order. Transform-only
preparation follows the first-order route and cannot enter B'', projection
curvature, objective G/H or normalized constraint/depth preparation.

The independent scalar `spatial` retains its existing Jet error sum starting at
`Jet(principal-observed)` and then focal terms in axis order. It cannot read
candidate e/basis/projection/G or mathematical helpers. Add an optional consumed-
intermediate sink to `spatial` (default return API unchanged): append existing
error Jet values and existing loss.g after calculation, without reevaluation.
Reference data output retains these alongside observation index/camera/frame;
candidate preparation already retains e/spatial and adds focal/centered values.
Both paths retain all consumed observation errors/spatial gradients, specifically
observation 199. The existing allocated prepare/objective receipts own these
bytes; diagnostics create no numerical entry or recalculation.

### 3.2 Pair construction and exact reduction order

For each analytical symmetric matrix, enumerate pairs in lexicographic upper
order `(0,0),(0,1),...,(1,1),...`. Calculate one binary64 value per pair and assign
that identical value to both positions. All finite contractions below use
separate multiplication/addition with no FMA: a sum is a left fold from `+0.0`
in the stated increasing index order. Elementwise vectorization over independent
pairs/observations is permitted; reduced axes cannot use BLAS/einsum or an
unspecified tree reduction. `np.add.accumulate(...,axis=0,dtype=float64)[-1]`
implements the prescribed observation left fold. Empty sums are positive zero.
No adaptive precision, averaging, triangle selection after a full result,
thresholding or tolerance change.

Candidate call sites in `components_v16`:

1. `projection_second`: assign HP's analytical mixed entries once per pair;
   construct HT pairs with the existing expression
   `2*k*((a==i)*u[j]+(a==j)*u[i]+(i==j)*u[a])`, left associated. For each Hcam
   pair `(k,l)` and output a, first left-fold `(b,i,j)` in 2x2x2 order of
   `(((K[a,b]*HT[b,i,j])*P[i,k])*P[j,l])`, then add the left-fold `(b,i)`
   term `(K[a,b]*T[b,i])*HP[b,k,l]`. Rig H pair `(k,l)` is the left-fold
   `(i,j)` term `(R[i,k]*Hcam[a,i,j])*R[j,l]`, then multiply by `diameter**2`.
   Store each HP/HT/Hcam/H pair twice; retain first-order J mathematics unchanged.
2. `Candidate.evaluate.hessian`: W pairs use existing
   `(2/n)*(delta/s-(e[a]*e[b])/s**3)`. Spatial curvature pair `(i,j)` is
   the left-fold `(a,b)` term `(P[a,i]*W[a,b])*P[b,j]`, plus the left-fold
   a term `point_g[a]*HP[a,i,j]`. For each coefficient/offset pair `(i,j)`,
   each observation's contribution is the left-fold `(a,b)` term
   `(T[a,i]*cur[a,b])*T[b,j]`. Reduce observations in retained order within
   each camera; accumulate camera contributions in original order.
3. For that camera's actual free offset j, add the mixed value computed once
   per coefficient/axis as minus the observation left fold of
   `Bp[obs,col]*spatial[obs,axis]`. Add the offset diagonal as the observation
   then axis left fold of `spatial[obs,axis]*(Bpp@C)[obs,axis]`, keeping the
   existing Bpp@C calculation. Apply mixed/diagonal corrections in the original
   camera position, then write completed upper pairs to both positions.
4. `full_sum`: H pair is `Hdata[i,j]+Hacc[i,j]`, stored twice. Hdata and H
   remain separate required outputs. Convert only these objective matrices
   q->x with ordered `(H[i,j]/scale[i])/scale[j]` for each pair, stored twice.
   Other G/J/Hz/Hg/Hacc conversion mathematics remain v15.

Reference call sites, independently implemented in `reference_v16`:

1. Jet addition, negation, multiplication, reciprocal and sqrt produce one
   scalar second derivative per upper pair using their existing scalar formulas.
   Multiplication h pair is left-associated
   `((self.h*o.v + o.h*self.v) + self.g[i]*o.g[j]) + o.g[i]*self.g[j]`;
   reciprocal pair is `(2*(g[i]*g[j]))/v**3 - h[i,j]/v**2`;
   sqrt pair is `h[i,j]/(2*root) - (g[i]*g[j])/(4*root**3)`.
   Addition/negation preserve their existing scalar expression. Jet values and
   gradients are unchanged. Validate any supplied h is finite and exactly
   symmetric; do not repair arbitrary h. Scalar constants retain zero h.
2. In `Reference.evaluate.hessian`, each observation contributes the left-fold
   `(a,b)` of `(T[a,i]*loss.h[a,b])*T[b,j]`, plus the left-fold a of
   `loss.g[a]*second[a,i,j]`. Add that observation in original order to each
   upper pair. Vectorization over independent upper pairs is allowed, using
   reference-owned T/second and scalar Jet results. Never import candidate pair
   assembly. `full_sum` independently constructs Hdata+Hacc by pairs.
3. Reference raw depth, weighted Hz, bounded Hg, rational acceleration and
   original G/Cd/Cb/KKT expressions remain unchanged. Jet symmetry is analytical
   representation; it does not authorize modifying constraint formulae or gates.

### 3.3 Objective transports only

Define `symmetric_objective_congruence(H,P,check=...)` independently in candidate
accounting and reference. Before any multiplication reject nonfinite, nonsquare,
shape-incompatible or exactly asymmetric H (`H[i,j] != H[j,i]`, no tolerance).
The primitive accepts the symmetric analytical objective contract only. P need
not be symmetric. The output has exact stored pair symmetry.

Candidate computes B[a,j] by left-fold k of `H[a,k]*P[k,j]`, then each upper
output `(i,j)` by left-fold a of `P[a,i]*B[a,j]`. Reference independently computes
L[i,b] by left-fold a of `P[a,i]*H[a,b]`, then each upper output `(i,j)` by
left-fold b of `L[i,b]*P[b,j]`. These two contraction orders are frozen;
neither calculates a full answer then copies or averages a triangle.

Candidate `accounting.report`: preserve x H/Hdata; construct q pair as
`(scale[i]*Hx[i,j])*scale[j]`; call candidate congruence once per matrix for y.
Reference `report`: preserve x H/Hdata; independently construct q with the same
specified diagonal pair expression; use reference congruence once per matrix
with `M=diag(scale)@P` on physical H/Hdata for y. This preserves reference's
direct physical-to-public route. Driver `transport_reference` uses reference
congruence for H/Hdata only, from completed reference q and retained Pnew;
importing the independent reference primitive here is allowed after methods
close. Hacc/Hz/Hg continue existing transport paths, with all their full gates.
No general `startswith('H')` dispatch to the new primitive.

Add instrumentable boundaries once per call/batch for focal output, centered
errors, HP/HT/Hcam/rig objective pairs, spatial pairs, data assembly, full sum,
objective pair scaling, congruence validation and contraction, plus independent
Jet operations and reference assembly. Validate source call coverage before
freeze; these are inner work receipts under already allocated component entries,
not a new low-level evaluation pool. Deadline checks run inside their loops.

## 4. Freeze all 20 prior groups plus exactly two stress groups

[Plan 022 section 5](plan_022.md) and the actual v15 test define groups 01–20,
all fixture bytes, real call coverage, analytic tolerances, negative assertions,
process checks, and byte-only cases. Retain them in full with v16 source maps.
Preserve the full integrated Bernstein oracle and separate reference basis/Jet
method; no helper-only substitute for a real evaluator.

One necessary routing change is fixed now: group 19 variant 7's deliberately
asymmetric supplied output goes to `newp_comparisons(...,transported=reference)`
using its already constructed reference report. Both existing candidate/reference
symmetry rejection assertions remain unchanged. This tests the comparator on
asymmetric output without calling a transport whose input contract now rejects
it. Variants 5/6 still exercise real new-P transport. Group 22 below separately
tests both actual transport input rejections. The ten comparison calls and eight
retained-validator calls remain exactly ten/eight.

### Group 21: fixed integrated centered-error scene

One complete Candidate and one complete Reference, one real report each, weight
zero, no free offsets, dimension 12, scale all ones. Four identical C rows are
`[2^-21+2^-62, 2^-22-2^-63, 2^-8]`; U=`[0,0,0,0,1,1,1,1]`, Q=`[0,0.5,1]`.
One gauge camera 1 has frames `[0,12.5,25]`, offset zero, R identity, t/center
zero, diameter 1, k=0, K=`[[1024,0,512],[0,1024,256],[0,0,1]]`, observed xy
`[512+1/8,256+1/16]` at all three frames; n=3, nacc=3. State is returned with
q=x=row-major C, vg length 3 and vby length 12 exactly zero. Reuse the separately
owned group 12 inactive setups with exact `(U bytes,Q bytes,weight=0)` keys;
no new setup, map, active acceleration, metric, SVD or inverse computation.

Saved origin zero. P is the existing dyadic toy block
`[[5/4,3/4],[3/4,5/4]]` on coordinates 0/1, diagonal 2 elsewhere and zero cross
entries. Its explicitly supplied inverse has block
`[[5/4,-3/4],[-3/4,5/4]]`, diagonal 1/2 elsewhere. Construct y once with exact
Fraction algebra on these fixed operands then serialize to binary64, no search.
These report operands do not create an additional public adapter/probe or state.
Check P/inverse products in the existing report algebra assertions.

Independent oracle: use closed cubic Bernstein B, B', B'' at t=0,1/2,1;
constant xyz is exactly the retained C row. From Fraction inputs construct focal
`1024*X/Z,1024*Y/Z`, errors **`[2^-44,-2^-45]`**, projection first derivatives
`1024/Z` and `-1024*Xaxis/Z^2`, and second derivatives mixed axis/z
`-1024/Z^2`, z/z `2048*Xaxis/Z^3`, other entries zero. Do not call either
production projection/spatial/basis or consume their derivative results.
Construct this constant spatial oracle once and expand through the three closed
B rows (coefficient trajectory is linear; second coefficient derivatives zero).

Use one fixed explicit Decimal80 ROUND_HALF_EVEN sqrt of `1+e0^2+e1^2`, with
Fraction-to-Decimal exact numerator/denominator conversion. Define loss/point-G/
W and spatial curvature analytically from that root, using the same mathematical
soft-L1 and n=3, with Decimal80 operations then final binary64 output. Define the
robust oracle weight with two scalar binary64 sqrt calls:
`sqrt(float(2/(root+1)))/sqrt(3)`; derivative is `-w/(4*q*(q+1))`, q=float(root).
These fixed three sqrt calls (one Decimal, two math) are shared across the three
observations, not a precision ladder. The very small true F may round to zero in
production; compare with unchanged tolerances and explicitly test e exactly.
Independently compute z/Jz and bounded values using the existing bounded
mathematics and one scalar math.hypot on constant `Z-1e-8`; vd/Hz/Hg/forces and
complementarity are exactly zero. KKT equals G, transported in each frame.
Acceleration is exact zero with empty r/J; build every full/split field and
x/q/y report independently. Use exact Fraction double sums for transport of
binary64 oracle H entries and dyadic M, no production congruence call.

Compare every physical and report entry, both errors explicitly, every H/Hdata
entry and their exact stored symmetry, inactive zeros/empty blocks, shapes and
all frames against the oracle. Also run one production canonical comparison
between the two retained reports. Toy atol `1e-12`, rtol `1e-11` and all exact
contracts stay unchanged; do not invent a tighter global acceptance threshold.

### Group 22: fixed standalone symmetric congruence

H=`[[2^40,2^20,-2^18],[2^20,3,-1],[-2^18,-1,2]]`,
P=`[[1,1/2,0],[1/2,2,1/4],[0,1/4,1]]`.
Call candidate and reference congruence once each. Construct all nine oracle
entries independently with exact Fraction double sum
`sum_a sum_b P[a,i]*H[a,b]*P[b,j]`, a then b increasing, convert only each final
entry to float. Compare all nine entries exactly and require identical stored
transpose bytes. Then copy H and change only H[0,1] by +1. Call each production
primitive once on this input and require rejection before its contraction
boundary. Exactly two successful and two rejected standalone calls; no complete
evaluator, report, inverse or alternative operand. Retain the oracle exact pairs.

## 5. Frozen work inventory and source inspection

Before suite 1 publish `toy-definitions.json`, `readiness-coverage.json`,
`coverage-source-review.md`, `comparison-schema.json`, `expected-schedule.json`
and `arithmetic-contract.json` (formulae, pair/reduction order, call-site map and
inner-work count expressions). Source-only review includes all six modules,
test, worker, admission/launcher, actual wrappers/calculators/observers and
retained decision reducer. Parent can inspect these files during Implementation;
no extra agent or routine user approval is required. Every row binds stable
assertion IDs, actual boundaries, expected count and source/test hashes. Numerical
counts must be independently incremented at actual entry, never assigned.

Per suite retain every Plan 022 inventory entry, with these exact totals/deltas:

| Work | v16 fixed count |
| --- | --- |
| Candidate complete attempts | 17: 15 successful (14 prior + group 21), two prescribed group 18 rejections |
| Reference complete attempts | Five: three successful, two group 18 rejections |
| Candidate evaluate entries including transforms | 19 = 17 complete attempts + two transform-only |
| Candidate successful full prepare/component paths | 15 each; plus two first-order prepare/residual paths and original failed pre-math preparation |
| Reference successful full prepare/component paths | Three each; plus original failed pre-math preparation |
| Real metric/SVD; undersized metric rejection | Two/two; one rejection before SVD |
| Candidate setup/bundle/map | 15/19/61, unchanged; Reference setup two, unchanged |
| Reference basis calls | 91 = prior 82 + three observations x three orders |
| Reference spatial calls | 41 = prior 38 + three group 21 observations |
| Candidate projection-second / projection-first / robust-residual helpers | 32 / four / 35 |
| Candidate full/first preparation boundaries | 15 / two |
| Candidate B'' / normalized-depth / objective-geometry batches | 29 each |
| Candidate focal output / centered-error batches | 36 / 33 |
| Candidate HP, HT, Hcam and rig curvature pair batches | 32 each, including three unchanged group 11 helper calls |
| Candidate spatial curvature pair batches / data assembly / full sums | 29 / 15 / 15 |
| Candidate q->x objective matrix scaling | 30 matrix calls |
| Candidate real primary reports / extra saved-P reports | 15 / two; also unchanged one dummy authoritative report = 18 total report calls |
| Candidate report q objective scaling / y congruences | 36 / 36 matrix calls |
| Reference data assembly / full sum / primary reports | Three / three / three |
| Reference report q objective scaling / y congruences | Six / six matrix calls |
| Driver toy reference transports | Four: two group 14 and two group 19 (5/6), two objective congruences each |
| Standalone successful/rejected congruences | One success and one rejection per method, group 22 |
| Total candidate congruence validation / contraction | 38 / 37 |
| Total reference congruence validation / contraction | 16 / 15 (six report + eight driver + one standalone successful) |
| Added group 21 oracle | One constant projection/soft-L1 oracle, three closed Bernstein rows, one full physical/report oracle, one retained production comparison |
| Added group 22 oracle | Nine Fraction double sums of nine terms, 81 terms total |

Kernel-only groups 01–09, seven direct basis calls, Jet group 10, group 11 helper
fixtures, 12 original integrated oracle spatial calls, eight mock solve calls,
200-state/iteration byte fixtures, ownership/guard/mutation/comparator/process
subcases and all inactive/active acceleration counts remain Plan 022's exact
inventory. Reference Jet operations receive counted boundaries; before freeze
expand their counts from the unchanged group 10 expressions plus exactly 41
`spatial` invocations and the fixed scalar expressions, recording a source-only
expression/call graph rather than discovering counts through a numerical run.
Pair work is deterministically `d*(d+1)/2` per d-dimensional family/batch and
its formula's frozen contraction dimensions; retain formulas by batch size
(13/12 toy, 55 science; spatial 3, distorted 2). This is execution bookkeeping,
not discretion to add helper calls. Group 21 uses no production Jet oracle.

Add all new curvature/contraction boundaries to transform-only throwing
sentinels; focal/centered/first derivative/residual boundaries remain allowed.
Reuse existing output objects for every later assertion; no hidden evaluator.
Readiness requires the entire 22-group suite, exact inventory, source coverage,
comparison schema and successful guard/process evidence from the current source
version. Missing assertions cannot pass through an aggregate `passed` flag.

## 6. Exact science schedule: original indices 12 then 13

Keep [Plan 022 sections 4, 6 and 7](plan_022.md)'s immutable contexts, actual
operand observations, wrappers, original multiplier ownership, 200 state and
iteration caps, repeat/cache contracts and complete per-case schedule. Only the
selected case list and arithmetic above change.

1. Candidate setups weight 0 then 1, separately owned immutable keys. For case
   12 then 13: cold complete/report, then returned sequences 1..5. Orders are
   `[O,G,H,C,CH,R]`, `[G,O,H,C,CH,R]`, `[H,O,G,C,CH,R]`,
   `[C,O,G,H,CH,R]`, `[O,G,H,C,CH,R]`. Sequence 5 first calls the actual cold
   residual/J-only transform/SVD once; its repeat is cached. Each returned
   sequence owns saved inverse, one public probe, the six actual callbacks or
   explicitly rejected replay with canonical fallback, and identical traversal
   repeat without new low-level work. Sequence 5 adds one saved-P report.
2. Close Candidate. Reference setups weight 0 then 1, then each original case's
   cold/returned complete reports; saved inverse only for returned. Reference
   never sees Candidate outputs or new P while evaluating. Close Reference.
3. Driver consumes four component contexts in case/cold-returned order. Each
   cold yields one canonical comparison, each returned five; total 12. Compare
   actual retained wrappers and every independent component inside those contexts.
   Include one historical corroboration per returned context, two total.
4. Consume two new-P contexts in original case order before transport/rational
   checks; use retained reference q and candidate Pnew, original bound multipliers,
   all norms/remap/contracts and sequence-5 admitted wrapper outputs.

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

Exactly **159 Candidate + 46 Reference + four driver component + two new-P =
211 entries** for complete execution, with 12 canonical comparisons, 10 public
probe results, two new-P comparisons and two historical corroborations. No
failure-driven extra case, evaluation, report or rerun. Retain actual entered/
observed/completed/interrupted records, deterministic original-index identities,
input/state/vg/vby/transform/setup/source hashes, wrapper results and all repeated
output bytes. Exact ordered identities and receipts are required, not merely
counts below caps. Each numerical inner helper is nested under its allocated
component entry and cannot consume an unrecorded evaluation allowance.

Candidate science full geometry has 36 camera batches and first-order has six;
projection-second 36, projection-first six, robust-residual 42, focal/centered
42 each, full spatial pair batches 36, data/full sums 12 each. Objective q->x
scaling has 24 matrix calls. Fourteen candidate reports (12 primary + two extra)
give 28 q scaling and 28 congruences. Reference has 1200 spatial observations,
3600 observation basis calls plus 150 active setup basis rows; four assembly/
full/report calls, eight q scaling and eight report objective congruences.
Two driver new-P transports add four reference congruences. These helper counts
exclude only nonnumerical guard callbacks and unchanged nested Jet primitives,
whose expression-derived per-spatial counts remain frozen in the source map.
No added standalone scientific congruence/oracle fixture is permitted.

Actual public replay remains `product=P@y; q=origin+product; x=q*scale`, exact
admitted byte equality. Keep original saved P/origin/y and actual bound inverse;
sequence 5 inverse/forward arithmetic may still reject. Do not search nearby y,
snap/reanchor, preload caches, replace admitted q/x, reinterpret fallback as
public success or modify the API. New P changes due to the centered J are saved
as new results, never substituted for original saved transforms.

## 7. Strict comparisons, retention and decisions

[Plan 022 section 7](plan_022.md) remains normative in full: centralized required
field/shape schema, all x/q/y full/split F/G/H/r/J/z/Jz/g/gp/gpp/vg/vd/vby,
Hz/Hg, forces/KKT/norm/complementarity, both inverse orientations, full subspace
coverage, exact inactive/offset-zero contracts, rational acceleration forward
error, source/input/multiplier identity and historical orientation. For these
cases n=300, m=55, image residual rows 600 and acceleration rows 450 or zero.

| Category | atol | rtol |
| --- | ---: | ---: |
| F/Fdata/Facc | 1e-10 | 1e-9 |
| G families, forces/KKT/norm, complementarity | 1e-10 | 1e-8 |
| z/g | 1e-12 | 1e-12 |
| vg/vd/vby, remap/back-map | 1e-12 | 1e-10 |
| H/Hdata/Hacc | 2e-5 | 3e-5 |
| Jz/Jg/gp/gpp | 2e-6 | 2e-5 |
| Hz/Hg, including new-P | 2e-5 | 2e-5 |
| Residual/J families | 2e-5 | 2e-4 |
| Inverse products/coverage | 1e-10 | 1e-10 |
| P symmetry | 1e-12 | 1e-12 |
| All five Hessian-family symmetry checks, both methods/every frame | 1e-10 | 0 |

Use `abs(candidate-reference) <= atol + rtol*abs(reference)` with binary64
multiply then add; rational forward error uses exact Fraction as in Plan 022.
Retain both values, shapes, every error/allowance and failed index; missing fields
are incomplete, not vacuous passes. Independent H/Hdata symmetry checks remain
mandatory even with symmetric construction. No exceptions for Hz/Hg/Hacc.

Keep separate completeness and known-failure dimensions for source/readiness,
package integrity, exact schedule, canonical arithmetic, actual public API,
new-P algebra and historical corroboration. Include the actual repeated wrapper
failures, not just their parent replay/report count. Historical archive comparison
keeps original classifications and Plan 022's field mapping/reference orientation;
archive disagreement is its own stratum and cannot repair/veto an otherwise
independently agreeing component. Missing historical evidence remains incomplete.

Name the current successful numerical dimension `arithmetic_on_selected_four_states`;
report selected original indices and full-cohort coverage `4/32`. If the generic
reducer keeps `qualified_on_fixed_cohort` internally, attach this explicit subset
scope and never expose it as 32-state or overall qualification. Any rejected
public probe means legacy public qualification remains rejected. All unexecuted
changed-source states remain unverified; v15's 91 passing comparisons do not
qualify them for v16. Desired arithmetic result is every required canonical and
new-P numerical check passing on all four selected states with no case-12 control
regression. It does not require relabeling failed public replay as passing.

During the single invocation, numerical mismatch allows remaining scheduled
independent work within limits; integrity/source/ownership/permission/interruption/
deadline failures immediately stop dependent work. Retain original v15 and new
v16 actual e, spatial G, G/Cd/Cb/KKT and H operands for the selected failure/control
states, with receipt paths. Report observed errors and allowances; do not rerun
an evaluator to diagnose them or claim an unperformed exact error decomposition.

`package` uses retained stdlib JSON/bytes/hashes only, including admission/toy
failure and partial science. No numerical recomputation or new comparisons.
Record explicit missing artifacts, entered/observed/completed/interrupted/unknown
IDs, hashes, decision strata, consumed slots, worker identity/exit/process-tree
cleanup, per-boundary inclusive times and disjoint invocation/phase wall times.
Nested inclusive times must not be added as disjoint consumption. Retain stdout,
errors, partial outputs and source versions for both toys if used.

## 8. Acceptance, commits and next handoff

| Plan acceptance | Observable required evidence | Criterion advanced |
| --- | --- | --- |
| A1 provenance | Verified full predecessor chain plus exact owned four-state selection/auth chain before deadline | SC-05; prerequisite SC-01/03 |
| A2 implementation readiness | Frozen formula/source map and all 22 groups with actual exact inventory, independent oracle and unchanged gates | SC-05; prerequisite SC-01/03 |
| A3 bounded adjudication | One exact 211-entry pass and complete strata, or explicit consumed/partial/failure records when a gate/deadline prevents completion | SC-05; prerequisite SC-01/03 |
| A4 retention and isolation | Immutable historical bytes, all available evidence and honest subset/public scope, reconciled limits, no owned processes | SC-05 |
| A5 validated milestone | Source/AST, retained JSON/hash/link, whitespace checks and task-only local commit with title and description | SC-05 |

Distinguish achieved acceptance from partial/failure retention: missing admission
or readiness cannot be called A1/A2 passed merely because its blocker is saved.
A fully audited numerical rejection is a completed implementation milestone;
it is not the desired arithmetic pass or objective attainment. Parent reassesses
every saved criterion from applicable evidence. SC-01/SC-03 remain not met until
their full required outcomes exist. Preserve SC-02/04 and historical limitations.

Coordinate one commit owner. Stage explicit task paths with escalated `git add`,
inspect staged diff, then separate escalated `git commit` with title/body, using
repository working directory, task-specific justifications and the mandated
prefixes. No push/amend/history rewrite. Git failure stops the loop; preserve
available work and exact error. Final phase elapsed includes commits.

Always retain `accepted_timing=null`, `production_candidate=null`,
`final_validation_protocol=null`, `ready_for_full_screens=false`,
`main_objective_attained=false`. Preserve v11/v12 failures, other 57 unadjudicated
ray failures, v13's six costs/36 partials, v15 canonical/new-P failures and all
16 legacy replay rejections as historical evidence.

If all selected arithmetic checks pass, next fresh Review chooses a concrete
coordinate/state protocol design preserving authoritative canonical ownership
and separately failed legacy replay; any new protocol requires its own fixed
identity/equivalence/derivative checks. If arithmetic fails, next Review examines
the exact remaining retained operation. If incomplete, identify its precise
missing prerequisite. None of these branches grants another numerical execution.

[Plan 015 sections 6 and 8](plan_015.md) remain fully binding: focused benchmark,
all-three-path agreement, controls/costs/support/initialization/stopping gates,
144-attempt/48-problem conditioning screen, preservation of 94 original
qualifications, at least 25/50 recoveries and median KKT ratio <=0.1; scalar
screen starting with 7,344 required paths, inclusive 0.05/0.01 refinements and
all nine basin/cost comparisons, then gated 144-path combined pilot and later
selection/final-validation gates. Keep KKT <=1e-6, depth >1e-7, competitive cost
`1e-6+1e-4*max(abs(F1),abs(F2))`, held-out exclusions and all 200 caps.

No jobs/blockers are present at planning handoff. Parent compares the saved plan
with applicable ceilings, records authorization/hash/T0, and dispatches fresh
Implementation automatically under standing approval. After finite execution,
continue authorized Review/Plan unless a real loop stop applies; a local commit
or arithmetic milestone alone is not a loop stopping condition.

## Plan-stage record

Read instructions/objective/status/assessment/Review, Plan 022, relevant Plan 015
gates, all six v15 source surfaces, test paths and retained implementation/
validation evidence. Performed only source/retained-text/hash inspection and
Markdown creation. No numerical imports, tests, evaluations, fits, training,
device/network operations, Git mutation or delegation. Only this next-unused
plan and the iteration plan-link are Planner writes; parent owns the preexisting
status change. No implementation T0 or worker was started.
