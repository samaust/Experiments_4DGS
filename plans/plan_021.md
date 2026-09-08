# Plan 021 — Integrate the full evaluator on 32 retained operating states

## Objective and authority

Implement [iteration 005 Review](../docs/continuous-improvement/20260908-plan016/iteration-005-recommendations.md)
against the unchanged [objective](../docs/continuous-improvement/20260908-plan016/objective.md)
and [post-review assessment](../docs/continuous-improvement/20260908-plan016/iteration-005-assessment-01-review.md).
Extend the qualified Decimal80 acceleration design to a coherent complete
objective/gradient/Hessian, constraints and owned-state reporting. Validate one
candidate against one independent full-component reference on the fixed actual
operating cohort below. This advances the evaluator prerequisite for SC-01/SC-03
and reproducibility evidence for SC-05; it cannot establish accepted Basketball
timing, reconstruction, or measured reconstruction comparison. Preserve applicable
SC-02/SC-04 evidence and historical SC-05 limitations.

Read AGENTS.md, objective, current status, latest assessment and this plan before
implementation and after context loss. Do not delegate or read `prompts` content.
The parent owns authorization, status and assessments. Implementation owns new
v14 sources, evidence and validated milestone commits. Preserve historical sources
and artifacts byte-for-byte. Follow the single safe same-command escalated retry
and all permission/git/interruption stops in AGENTS.md.

AGENTS.md `b62f2ea`, the explicit same-objective resume and this Review-recommended,
Plan-finalized allocation provide standing approval. Before dispatch, the parent
must record the saved plan hash/link, one T0, absolute monotonic/UTC deadlines,
scope and historical consumption in
`docs/continuous-improvement/20260908-plan016/iteration-005-plan021-authorization.json`.
No routine budget confirmation is needed. This Plan stage performs source reads,
retained-JSON inspection, byte hashing and documentation only; it starts no
implementation clock and consumes no scientific entries.

## 1. Fixed execution limits

| Scope | Hard ceiling |
| --- | --- |
| Implementation, admission, development, toys, supervision, evidence and commits | 5,400 elapsed seconds from parent T0 |
| Read-only admission complete | T0 + 900 seconds |
| Frozen candidate/reference and passing applicable toy readiness | T0 + 3,600 seconds |
| All scientific work and owned-process cleanup ended | T0 + 4,500 seconds |
| One supervised scientific invocation, including imports/setup/comparisons/I/O/cleanup | 900 wall seconds within the above deadlines |
| Candidate choices / independent methods / scientific invocations | 1 / 1 / 1; no replacements or retries |
| Cases / cold-plus-returned case-state slots | 16 / 32 |
| Candidate complete bundles | 96: 16 cold and 80 returned (five per case) |
| Dedicated cold-transform residual/J constructions / coefficient SVD calls | 16 / 16 |
| Independent complete bundles | 32: one per case-state slot |
| Candidate / independent acceleration geometry setups | At most 2 / 2, keys fixed by weight 0 then 1 |
| Frozen toy suite | At most 2 invocations of the same 20 cases in section 7 |
| Numerical concurrency | One numerical worker plus its supervisor, one thread per numerical library |
| Optimizer, local fit, initialization fit, restoration or training attempts | 0 |
| Scientific finite differences, new displacements/rays/limits, pilots/full screens | 0 |
| Training, rendering, GPU, network, download, installation | 0 |

Use `.local/envs/calibration-global/bin/python`, installed NumPy/SciPy, and stdlib
Decimal/Fraction only. Set OMP_NUM_THREADS, OPENBLAS_NUM_THREADS, MKL_NUM_THREADS
and NUMEXPR_NUM_THREADS to `1` before process startup. No NVIDIA skill is needed.
Scientific import/setup is forbidden in admission/readiness/packaging. Toy imports
and toy arithmetic are charged to the toy invocation and implementation phase.
Missed admission/readiness deadlines prohibit dependent science; retain evidence
within the remaining phase. No post-science arithmetic/source repair or scientific
rerun is allocated. Unused time does not buy entries, attempts or another toy suite.

Preserve all 405 Plan 016 outcomes and six preflights; Plan 018's consumed pass,
7.84522387 numerical seconds and 1498.589622 phase seconds; Plan 019's two setups,
twelve bundles, two toy suites, 1.026992965 numerical seconds and 1125.515842279
final phase seconds; Plan 020's one setup, six bundles, two toy suites,
0.12248898699181154 numerical seconds and 914.2315437420039 final phase seconds.
Training remains 22523.417254 charged seconds under 24 hours and unchanged
7200-second method/scene ceilings. This plan adds zero training seconds and
cannot restart or redistribute stopped method allocations. These are new
plan-specific evaluator limits, not reset historical clocks or a new overall
loop limit. Subsequent authorized Review/Plan may continue after this allocation
finishes unless a loop stop applies.

## 2. Files and command contract

Create these new surfaces; do not edit hash-bound v2/v6/v9/v10/v11/v12/v13 code:

- `scripts/basketball_acceleration_decimal_v14.py`: Decimal80 full acceleration
  cost, all coefficient partials, full Hessian and conditioning residual/J.
- `scripts/basketball_shared_components_v14.py`: explicit data/acceleration
  components, full sum, residual/J, depth derivatives and weighted curvature.
- `scripts/basketball_shared_accounting_v14.py`: immutable canonical state,
  multiplier-aware component caches, public coordinate admission and entry audit.
- `scripts/basketball_shared_solver_v14.py`: coherent callback/returned/interrupted
  report path; versioned solver wiring, with no actual optimizer invocation here.
- `scripts/basketball_shared_reference_v14.py`: independent scalar basis and
  second-order spatial jets, rational acceleration, full chain assembly.
- `scripts/basketball_shared_evaluator_v14.py`: stdlib admission/readiness,
  fixed supervisor/worker schedule, comparison and retained-data packaging.
- `tests/test_basketball_shared_evaluator_v14.py`: the fixed 20-case suite.
- `docs/experiments/basketball-shared-timing-v14/`: immutable inputs, provenance,
  setup/entry/result records, comparisons, decision, process and budget evidence.
- `docs/experiments/basketball-shared-timing-v14.md` and run-directory
  `iteration-005-implementation.md`, `iteration-005-validation.md`.

The harness exposes `admit`, `ready`, `run`, `package` and guarded internal
`worker`. It has one fixed output root and the parent authorization path above.
Tests consume `toy-suite-01` or `toy-suite-02` by exclusive create before imports
and dispatch. `ready` freezes applicable passing test/source hashes without
evaluating. `run` owns exactly one durable invocation; direct `worker` calls fail
before numerical import/setup. Record exact commands and failures. Reproduction
requires another authorized plan/namespace; no command removes consumed markers.

## 3. Admission: exact cohort and original operands

Use exactly the 16 cases in Review R1, in its order: baseline conditional
00,07,13,03,10,16; metric conditional 00,07,13,03,10,16; metric joint
00/descending,01/cold,02/ascending,03/ascending. The conditional paths all end
in `/cold`. The first twelve are the ordered `cases` in
`docs/experiments/basketball-shared-timing-v11/inputs.json`, SHA-256
`7a4b5aebeb5652051298ab88103a44af63a13ed69163eda988b333169cdf11f0`.
The last four use the exact v10 gzip artifact paths and SHA-256 pins in Review
R1. Review's 16 returned physical hashes are binding, not illustrative.

Each case contributes `cold` followed by `returned`. Obtain cold by requiring
one unique `cold_transform` event/state in `row.accounting`, and returned from
the exact `row.returned_state` ledger entry. Conditional last selected snapshot
and all last callbacks must agree with the owned return and its multipliers.
Do not choose first/middle callbacks or substitute another path. Cold canonical
and physical SHA-256 values are equal for each of these retained cold states;
both fields must independently match this additional read-only pin table:

| Cases | Cold q SHA-256 and cold x SHA-256 |
| --- | --- |
| Both arms conditional 00 and 03 | `849b99238f58dceb28465f58905c35f4bba1c1ba0b43dc794c92ad6967ba4e9d` |
| Both arms conditional 07 and 10 | `7623d26719bcc2e67ae62e0f27e220458099249b45f7feafe1e5d29f6f054b57` |
| Both arms conditional 13 and 16 | `39df69e0ce47977ace256d87704492edcf8a62a4355c3660a410bba5b3192be2` |
| metric joint-00/descending | `82daae22162a53c414a840902052562517bc960bbaa9d99b33a31e001d00805d` |
| metric joint-01/cold | `f0b5078087e21a08d5e06f05a2bb19b56ef41ac43df509298d64fa688b37a789` |
| metric joint-02/ascending | `42e19435abf7d0798143d24ea883cf7b1cdf8d5cf4ae9ccca9ca4d42aa85507b` |
| metric joint-03/ascending | `f7da9896e5af60d6447a54a6611a240d15ad15c15c9e5f692c0be57ab7cb733a` |

Each conditional state has 54 parameters, the joints 55 with free camera `[3]`.
All have one group, 18 cubic coefficient rows, 300 image observations, window
`[50,149]`, spacing 10, and 150 quadrature samples. Seven cases have weight one
(six conditional plus joint-00); nine have weight zero. Record explicit case
roles/group/weight/free-offset metadata; repeated bytes are separately owned slots.

Admission is stdlib parsing/serialization/hash/metadata only. Before any scientific
arithmetic, publish all of the following in `admission.json` and immutable inputs:

1. Complete per-slot little-endian binary64 q/x bytes and hashes; saved returned
   y bytes; last-callback depth and bound multiplier bytes, shapes and hashes;
   exact saved P, origin and scale bytes; cold and returned ledger/event identity.
   Serialize JSON floats with `struct.pack`, not a numerical coordinate transform.
   Preserve signed zero. Verify duplicated serialized fields by bytes, not allclose.
2. Original observations, frames, xy, calibration, offsets/free map, gauge 1,
   role `synthetic-fit-50-149`, window, spacing, weight, knots, center, diameter,
   n/nacc and ordering. Bind the historical synthetic benchmark origin explicitly;
   these are evaluator operating fixtures, not new reconstruction evidence.
   Preserve training/held-out exclusions; do not generate synthetic observations.
3. Copy quadrature bytes from v13 `inputs.json`, SHA-256
   `5cdc33308ad68dacd70522ab423286b42f060c53c02343e90b05a377a75034fc`.
   Require matching knot bytes/window/spacing/nacc in every case and the retained
   v12/v13 provenance chain. No `arange`, quadrature regeneration or calibration
   normalization is permitted. Geometry mismatch fails admission.
4. Verify v10 attempt receipts and hash-linked journals, allocation identity,
   problem key and dependency provenance; bind each source map, benchmark manifest,
   policy, source dependency artifact and saved return. Conditional v11 source
   substitution maps must be resolved explicitly: preserve old and replacement
   hashes/paths and their existing attestation, never silently accept current
   source as historical. Hash the actual joint source maps and their dependencies.
5. Freeze historical sources used for inspection/reuse, including spline v2,
   solver/curvature v6, accounting/solver/storage v10, v11 evaluator/verify,
   v12 rational/control sources and v13 Decimal kernel. Pin the interpreter,
   NumPy/SciPy package metadata, numerical extension/shared-library files and
   relevant stdlib/Decimal implementation by read-only file hashing. No imports
   are needed for admission. At readiness, add exact new source/test hashes and
   resolve every mathematical import; imports outside the frozen set fail entry.

The candidate and reference receive separate immutable inputs containing original
operands and metadata only. Neither receives archived G/H/KKT, old acceleration
arrays, candidate/reference results or historical classifications as numerical
inputs. Keep archived comparisons in a packager manifest. Source hashes may be
checked as bytes; reference must not import candidate mathematics. Preserve the
original admission script bytes if it changes during permitted toy development.
No `SplineProblem.__init__`, initialization/sanitize/support fit, solver, inherited
scientific fixture or hidden constructor arithmetic is allowed. A lightweight
explicit operand container is constructed in the charged worker; missing identity
or unresolved provenance ends admission, with no replacement source/state.

## 4. Fixed mathematical implementation

### Candidate acceleration and data ownership

Use v13's explicit Decimal context: precision 80, ROUND_HALF_EVEN,
Emin -999999, Emax 999999, capitals 1, clamp 0, local context, exact
`Decimal.from_float` decode; trap InvalidOperation, DivisionByZero, Overflow,
Underflow and FloatOperation, retain Inexact/Rounded flags. Do not inherit ambient
context, adapt precision, snap zeros, discard coefficients, or change state bytes.
Keep v13's alpha/beta differences, right half-open span/final left limit convention,
sample-major then X/Y/Z order and its control differences/transpose. Extend the
transpose to rows 0 through 17 in ascending order. Every axis and every row is
retained, including inactive and null directions.

During the weight-one setup, construct the linear second-derivative row L at each
quadrature point by applying the same fixed alpha/beta/two-span map to coefficient
unit columns in ascending order, entirely in Decimal80. Accumulate the symmetric
coefficient Hessian as `2*(weight/nacc)*sum(L_i*L_j)` in saved sample order,
ascending i then j; same-axis blocks only, zero offset/cross-axis blocks. This
curvature never uses the old rounded `A.T@A`. Reuse immutable geometry/Hessian
within that setup key. Coefficient evaluation uses the control-difference map,
full transpose gradient and cost; export each final scalar once to binary64.
Compute the conditioning residual/J from this same map and Decimal square-root
factor `sqrt(weight/nacc)`, then export final entries. It is a representation for
conditioning; `r@r` is not the authoritative objective. Weight-zero setup is an
explicit metadata/zero result: no inactive acceleration mapping, cost, gradient,
Hessian or residual-block evaluation. Zero acceleration cost/G/H is exact.

Factor v2 image expressions into a data-only path and v6 data curvature into an
explicit data-only path. It is permissible to reuse pinned candidate projection
helpers; reference cannot. Never subtract a rounded acceleration term from a
rounded full value. Compute the authoritative scalar image loss
`sum(2*(sqrt(1+e.e)-1))/n`, point gradient/curvature and matching robust residual/J
using the inherited normalization and operation order. Save separate Fdata/Facc,
Gdata/Gacc, Hdata/Hacc and full sums. Sum data then acceleration once, with no
loss/gradient reconstruction from exported residuals. Preserve projection-plane
rejection and all original nonfinite checks.

Each complete bundle prepares observation B/B'/B'', trajectory/projection and
point intermediates once, then retains them for its component operations. Image
Hessian, depth and weighted curvature must not independently rebuild the basis
or reproject observations. A transform-only context prepares its own residual/J
geometry; no fitted-state result crosses adapter contexts. Geometry setup may
share only immutable knot/quadrature geometry under the two authorized keys.

### Independent full-state reference

Implement one reference method in the new module. Compute scalar Cox–de Boor
basis values, first and second derivatives from original knots and each state's
actual corrected frame times, independently of SciPy/candidate basis arrays.
Use ascending basis/observation/axis orders, skip zero knot denominators and use
the same mathematical endpoint convention; no finite difference. The recurrence
is v12 method A's degree/basis derivative recurrence, independently extended.

Use second-order forward jets `(value, three-gradient, 3x3-Hessian)` for normalized
spatial X/Y/Z. Supply elementary add/multiply/reciprocal/sqrt with analytic jet
rules and propagate original camera R/t, diameter/center, radial k, K and scalar
soft-L1 image loss. Differentiate the robust residual representation directly
with jets as well. Do not copy `projection_second`, candidate G/H/J, or differentiate
the candidate program. Assemble full physical coefficient/free-offset derivatives
from independent B/B'/B'': offset trajectory derivative `-B'C/25`, offset second
derivative `B''C/625`, coefficient/offset mixed derivative `-B'/25`. This includes
all supported observation rows and all mixed/offset curvature.

For acceleration use exact Fraction decoding of original binary64 knots,
quadrature and coefficients, scalar derivative recurrence, exact full cost/G
and constant Hessian. Setups for weight 0/1 are separate; zero skips inactive work.
For conditioning residual/J, export the independent exact acceleration/map values
and use binary64 square root of the saved scale, with frozen source order.
Save rational acceleration outputs plus final binary64 full reference arrays.
The reference's data/constraint arrays are independent binary64 calculations,
not a proved exact image oracle; disagreement/uncertainty remains visible.

### Coordinates, constraints and reports

Retain `x=Dq`, `q=origin+Py`, D=25 on free offsets and 1 on coefficients:
`Gq=D.T Gx`, `Gy=P.T Gq`, `Hq=D.T Hx D`, `Hy=P.T Hq P`.
V6 objective Hessian returns q coordinates despite accepting x: the candidate
must not apply D twice. Its raw-depth unit-scale wrapper likewise accepts x and
differentiates q. Explicitly expose physical, q and y derivative arrays and verify
offset/mixed factors against the independently physical reference. No x-to-q
round trip is permitted to identify an archived return.

Raw depth is normalized camera z. With `s=z-1e-8`, preserve v6's stable
`g=s/hypot(1,s)`, `gp=inv^3`, `gpp=-3*g*inv^4`, and derivative-underflow checks.
For one frozen depth multiplier vector vg per state, compute
`vd=vg*gp`, `Hz_weighted=sum(vd_i*Hz_i)` and
`Hg_weighted=Hz_weighted + Jz.T diag(vg*gpp) Jz`.
Save z/Jz, g/Jg, both weighted Hessians and gp/gpp. The raw weighted Hessian's
weight is vd, explicitly labeled; it is not a second weighting experiment.
Returned slots use actual last-callback vg and conditioned bound vby. Cold slots
use exactly 300 ones as vg for derivative validation only; cold KKT, optimality
and complementarity claims are null. Multipliers are immutable cache-key bytes.

One reusable owned-state report function serves ordinary callback, completed
return and interrupted return. It reads the coherent cached objective/gradient,
never `r@r` or `2*J.T@r`. Returned report computes in q coordinates:
`Cd=Jzq.T@vd`, `Cb=inv(P_saved).T@vby`, `KKT=(Gq+Cd)+Cb`,
`complementarity=vd*(z-1e-8)`; expose corresponding x/y force arrays and norms.
Preserve actual historical multipliers and qualification fields as archived
comparisons, not a claim that v14 ran an optimizer. Wire v14 solve/callback to
this function, with mocked optimizer only in toys. No sampled-support calculator
or initialization is called by this evaluator report.

## 5. State ownership, request order and public-y decision

Use exact immutable q/x and separately owned case/scope/adapter identity. Each
adapter has both 200-distinct-state and 200-iteration caps, including setup scopes;
an attempted 201st entry is rejected before mathematics. Immutable results are
keyed by state, component, multiplier bytes and transform identity as applicable.
No approximate key, mutable view or cross-adapter fitted-state result reuse.

For each case first compute one complete cold bundle in its own `cold-component`
adapter. Then create five fresh returned adapters in this exact order. `O`, `G`,
`H`, `C`, `CH`, `R` mean objective, gradient, objective Hessian, bounded constraint
value/J, weighted constraint Hessian, full owned-state report:

| Sequence | First full traversal; then repeat the same traversal exactly once |
| --- | --- |
| 1 objective-first | O, G, H, C, CH, R |
| 2 gradient-first | G, O, H, C, CH, R |
| 3 Hessian-first | H, O, G, C, CH, R |
| 4 constraint-first | C, O, G, H, CH, R |
| 5 transform-first | Dedicated cold transform T, then O, G, H, C, CH, R; repeat T as a cache hit and then O, G, H, C, CH, R |

Sequences 1–4 install saved P/origin by bytes, without cold evaluation or SVD.
Sequence 5 owns exactly one fresh cold residual/J and one coefficient SVD and
builds Pnew with v10's symmetric metric policy: threshold/grouping/canonical
subspaces from pinned deterministic_svd, active inverse-singular scales clipped
to `[1e-3,1e3]`, inactive scales one, full `V.T*scales@V`, offset block identity,
origin=cold q. Every cohort residual has at least as many rows as 54 coefficient
columns; enforce this before SVD so v6's second-SVD shape fallback cannot run.
Compute inverse once, retain all singular values/projectors/scales, verify
invertibility/symmetry/full null and active coverage. No Pnew is retroactively
attributed to historical optimizer output. Cold-transform output may be reused
as immutable transform metadata; its residuals do not seed another adapter cache.

The complete bundle may be eager: the first requested surface computes its
fixed internal components once, regardless of public order. All repeated requests
must return the same owned cached mathematical outputs with no low-level entry.
`R` is finalized once and cached; repeated callback/interrupted report requests
retain that state and multipliers. Both saved-transform and new-transform algebra
are exercised on the already computed q derivatives in sequence 5, without new
objective/depth/Hessian evaluations.

**Public-y replay is a checked request, not authority for another state.** Before
the returned traversal, each of sequences 1–4 performs one charged coordinate
probe with exact saved y: compute `P@y` then `origin+product`, separately multiply
q by D, record actual q/x bytes and compare to the admitted return. Sequence 5
performs one probe `ynew=inv(Pnew)@(q_saved-origin_new)`, followed by that same
forward operation and byte comparison. Cache each probe mapping/decision; repeated
public requests do not recompute it. Do not preload the y-cache with saved q to
force agreement, snap to saved q, change origin, or perturb any operand.

If bytes match, the six requests and their repeats exercise the public-y API
backed by that exact state. If they differ, the public API must reject before
state allocation/numerical entry, saving actual candidate bytes and the rejected
request. The prescribed canonical owned-state O/G/H/C/CH/R traversal still runs
at saved q in that fresh adapter, separately labeled `canonical_only`.
This expected guard rejection is a measured public-path failure; it is not
an integrity breach or a reason to cancel independent canonical/reference slots.
An actual evaluation on an unadmitted state, a forged cache hit, wrong source,
wrong multiplier, or failed journal ownership is an integrity breach and stops
dependent work immediately. No replacement public-y state is allocated, even
if its bytes happen to equal another case's input.

Report `canonical_components` and `public_y_replay` separately. Any nonidentical
replay makes public-y qualification fail and prevents the overall evaluator label
`qualified_on_fixed_cohort`, even when canonical derivatives pass. It does not
erase canonical evidence or become `unverified`. New-P algebraic derivative
checks remain valid as explicitly labeled chain-rule checks, not successful
public replay or optimizer evidence. No search for an exactly replaying y is
allocated. This resolves the fixed-cohort restriction without hiding rounded states.

## 6. Exact numerical entry schedule and ceilings

Consume each invocation/setup/context/component/transport slot before its
arithmetic, with an independently observed low-level entry recording actual
q/x and multiplier bytes. Bundle records do not replace this audit. One complete
bundle contains exactly one observation-geometry preparation, objective/residual
operation, data objective-Hessian operation, raw depth/J operation, weighted raw
curvature operation, bounded curvature assembly and report/coordinate assembly.
Shared intermediates are immutable within that bundle only. A transform context
contains one geometry preparation, residual/J-only operation and SVD/transform
assembly; it computes no additional objective/Hessian/depth. Candidate acceleration
Hessian is read from its owned setup, never recomputed in state bundles.

| Mathematical boundary | Candidate maximum | Reference maximum | Ownership/detail |
| --- | ---: | ---: | --- |
| Geometry setup keys, weight 0 then 1 | 2 | 2 | Weight zero is explicit inactive metadata; weight one constructs acceleration map/Hessian once |
| Complete state contexts | 96 | 32 | Candidate: 16 cold + 80 returns; reference: 16 cold + 16 returns |
| Transform-only contexts | 16 | 0 | Only sequence 5 cold; no other cold cache-cold replay |
| Observation basis/trajectory/projection preparations | 112 | 32 | One per context; up to 300 rows, 18 B/B'/B'' entries per row; no repeated preparation in component calls |
| Objective/data-gradient plus residual/J evaluations | 96 | 32 | Full split arrays; reference jets include all data G/H in this same preparation |
| Additional residual/J-only evaluations | 16 | 0 | Cold transform; thus total residual/J boundaries 112 / 32 |
| Data objective-Hessian assembly | 96 | 32 | Reference reuses its jet results; candidate excludes old acceleration Hessian |
| Full objective-Hessian sum | 96 | 32 | One sum of owned data plus setup acceleration H; no residual call |
| Raw depth/J assembly | 96 | 32 | One per complete context |
| Weighted raw-depth Hessian assembly, weight vd | 96 | 32 | One traversal of retained B'/B'' geometry; no second raw_depth evaluation |
| Bounded-depth value/J/weighted Hessian chain assembly | 96 | 32 | Reuses z/Jz/weighted Hz and one gp/gpp calculation |
| Report assembly with actual returned multipliers | 80 | 16 | Cold reports contain components only, no synthetic KKT |
| Cold component packaging/coordinate assembly | 16 | 16 | No cold KKT |
| Coefficient SVD and Pnew/inverse construction | 16 | 0 | One SVD exactly per transform context, no retry/fallback |
| Saved transform inverse construction | 80 | 16 | Once per candidate returned adapter; reference once per returned case; cold component uses identity |
| Public-y coordinate probes | 80 | 0 | 64 saved-y forward probes, 16 new-y inverse-plus-forward probes; no objective entries on mismatch |
| Extra sequence-5 saved-transform report transport | 16 | 0 | Same cached q components/forces, actual saved P/vby; no new components |
| Independent new-P algebra transport/comparison contexts | 16 | 0 | After both calculators finish; reference q outputs transported using retained Pnew as explicit test operand |
| Saved/cold component comparison contexts | 32 | 0 | Compare five returned results against one independent returned result; no reevaluation |

The last two rows belong to the comparison driver, not candidate/reference
calculators, and are included in the scientific 900-second pass. Physical/q/y
array transports and KKT/complementarity occur only in the allocated report or
comparison context, once per named field/frame; cache repeated requests. For
Pnew, transform saved `Cbq` to `vby_new=Pnew.T@Cbq` solely for an algebraic check,
then inverse-transpose back; label this remapped vector, never an actual optimizer
multiplier. Reference uses its own saved-P inverse and original multipliers.
Candidate's Pnew cannot enter the independent calculator; comparison receives
already completed independent q arrays after the reference is closed.

At most 49 candidate active acceleration state traversals occur: 42 weight-one
complete bundles plus seven weight-one transforms. Reference has 14 active
acceleration state bundles. The 54 candidate complete/9 transform and 18 reference
weight-zero contexts perform no inactive acceleration arithmetic. All 54
coefficient gradient entries and full 54x54 acceleration Hessians are exposed;
joint outputs prepend an exact zero acceleration offset row/column. Low-level
counts are nested ceilings, not additive fit attempts. Each entry records its
parent context and subentry ordinal so accidental recomputation cannot fit inside
an opaque bundle count. A helper that repeats basis/projection work is out of
plan even if exported top-level counters look correct.

Scientific order is fixed: consume candidate setups weight 0 then 1; for case
0..15 execute cold bundle and sequences 1..5 in order; close candidate numerical
outputs; consume reference setups weight 0 then 1 and case 0..15 cold/returned
bundles; close reference; execute 32 component comparisons in case/state order,
then 16 new-P algebra comparisons in case order. Candidate/reference use separate
objects/modules/input directories and cannot read one another's result files
while calculating. No compiled candidate helper is imported by the reference.
No preflight evaluator, pilot subset, old direct replay or extra probe is allowed.

## 7. Fixed toy readiness

Freeze all 20 definitions and test source before suite 1. Both invocations run
the same complete suite; group assertions inside the fixed cases. A correction
may use suite 2 before readiness. No third invocation, scientific fixture,
archived operating state or inherited scientific-fixture suite is a toy. No
state sweep or random fixture generation is allowed. Scientific source changes
after the final applicable passing suite prohibit science.

For cases 1–5 use cubic Bezier U=`[0,0,0,0,1,1,1,1]`, Q=`[0,0.5,1]`, weight 1.
The hand-derived second-derivative coefficient row is
`a(t)=[6*(1-t), -12+18*t, 6-18*t, 6*t]`; expected Hessian is
`(2/3)*sum(a(t).T*a(t))` per axis, with exact cross-axis zeros. This is a frozen
analytic fixture formula, not a candidate-derived oracle. Analytic toy comparisons
use atol `1e-12`, rtol `1e-11`; Decimal internal nonterminating identities use
absolute `1e-65`. Exact bytes/zeros/identities use exact equality.

| Case | Frozen fixture and assertions |
| --- | --- |
| 1 | Controls all 7 in X/Y/Z: zero cost/G, full analytic Hessian and constant null mode |
| 2 | X controls `[0,1,2,3]`, Y=2X, Z=-X: linear null cost/G and Hessian applied to each linear/constant null vector |
| 3 | X `[0,0,1,3]`, Y/Z zero: cost 36, full G from analytic rows, full H above |
| 4 | X `[0,0,0,1]`, Y=2X, Z=-X: nontrivial cubic, each full gradient component/Hessian and residual/J from analytic rows |
| 5 | Case 2 translated by exact `2^40` in all axes; no snapping and unchanged zero cost/G; all coefficient inputs retained |
| 6 | Eighteen-row hand-authored U with endpoints 0/15 repeated four times and interior integers 1..14; Q=`[0,0.5,7,14.5,15]`; controls at Greville abscissae in X, constants Y/Z: every output row present, linear null and exact independent recurrence agreement, no scientific knots |
| 7 | Nonuniform U=`[0,0,0,0,1,2,2,2,2]`, X `[0,1,3,5,6]`, Q=`[0,0.5,1,1.5,2]`: linear null and exact endpoints; repeated-knot variant U=`[0,0,0,0,1,1,2,2,2,2]`, zero controls: known spans; reject invalid domain/denominator |
| 8 | Weight-zero case 4: exact zero Facc/Gacc/Hacc, absent acceleration residual block, sentinel inactive calculator must never enter |
| 9 | Ambient precision/rounding/trap changes around case 4 and exact binary64 0.1/-0 decoding: same output bytes, restored context, invalid/nonfinite/overflow and underflow rejection |
| 10 | Independent jet at `(1,2,3)` for `X*Y+Z*Z`, reciprocal of `1+X`, and square root of `1+X`: exact analytic gradients/Hessians; no candidate helper |
| 11 | Toy identity camera R, t=0, center=0, diameter=1, K identity, k=0, point `(1,2,4)`, observed xy=0: analytic perspective/residual derivatives against independent jets; second variant k=1/8 and R mapping `(X,Y,Z)` to `(-Y,X,Z)` checks distortion/rotation |
| 12 | Toy cubic trajectory case 4 at t=1/2, camera offset scale 25; physical/q/y with diagonal P `(2,3,...)` and origin 1: analytic offset and coefficient/offset mixed derivative factors, no duplicate D |
| 13 | Raw toy depth `z(c,q)=2+c*q+q*q` at `(c,q)=(1,2)`, vg=3: analytic raw/bounded first/second chains, vd conversion, weighted curvature and complementarity; fixed large-depth input triggers underflow rejection |
| 14 | Six-scalar hand-authored component provider with entry sentinels: all five fixed request orders and cache repeats yield same immutable values, one entry per component, cold transform counted separately |
| 15 | Mock optimizer callback then ordinary return and exception/interrupted return on identical q/multipliers: one owned report, coherent F/G/KKT, no x-to-q replacement or residual-derived reporting |
| 16 | Adjacent binary64 q values 1 and next representable value (explicit bytes), ±0, same q in distinct scopes/adapters; exact cache separation and immutable input/output mutation rejection |
| 17 | Dummy state/iteration ledger allocates exactly 200 integer-labeled toy states and iterations; 201st fails before sentinel math; no scientific evaluator invoked |
| 18 | Dummy entered calculator throws: slot remains consumed; wrong source/state/multiplier bytes, unallocated entry and duplicate immutable result rejected before any new math |
| 19 | Direct-worker token/PID rejection and source/admission/output collision guards; exact public-y replay accepted and deliberately inexact toy transform replay rejected without substitute evaluation; canonical-only evidence remains distinct |
| 20 | Dummy sleeping process tree, no scientific calculator: supervisor deadline and SIGTERM interruption preserve partial entries, terminate/reap own process group within fixed 3-second toy deadline; no descendant remains |

Candidate-independent full-reference arithmetic on these hand-authored fixtures
is part of the single frozen reference method, not another scientific method.
Record test hash, candidate/reference hashes, results, invocation times and cleanup.
Readiness requires all applicable 20 cases pass, all required implementation
surfaces exist, independent imports/output isolation hold by source inspection,
entry ceilings are encoded, and all admission identities are bound. Static
compile checks may occur inside each toy suite; do not run ad hoc scientific
imports or numerical development checks outside those two suite slots.

## 8. Frozen comparisons and process supervision

For each scalar comparison let v be saved candidate binary64 and r saved
independent binary64. Use `abs(v-r) <= atol + rtol*abs(r)`; separately compute
multiply then add in binary64, no FMA, no symmetric max reference or tolerance
tuning. For rational acceleration components use exact forward error
`abs(Fraction.from_float(v)-r_exact)` against
`Fraction.from_float(atol + rtol*abs(float(r_exact)))`. Retain exact oracle,
reference-rounded bytes, error/allowed bytes or rational pairs and each failed
array index. Rational overflow/nonfinite export fails comparison; never silently
switch orientation. Full data+acceleration reference arrays have fixed binary64
sum order, while acceleration-only comparisons retain the exact rational oracle.

| Field/check, in each applicable x/q/y frame | atol | rtol |
| --- | ---: | ---: |
| Full and split costs | 1e-10 | 1e-9 |
| Full/split gradients, constraint forces, KKT, complementarity | 1e-10 | 1e-8 |
| Raw/bounded depth values | 1e-12 | 1e-12 |
| Original/remapped multipliers | 1e-12 | 1e-10 |
| Full/data/acceleration objective Hessians | 2e-5 | 3e-5 |
| Raw/bounded depth Jacobians and scalar gp/gpp | 2e-6 | 2e-5 |
| Weighted raw/bounded constraint Hessians | 2e-5 | 2e-5 |
| Residuals, data/acceleration residual Jacobians | 2e-5 | 2e-4 |
| Transform inverse product vs identity | 1e-10 | 1e-10 |
| Symmetric P vs P.T | 1e-12 | 1e-12 |

Objective/force/depth/multiplier tolerances inherit v11. Hessian tolerances
inherit `test_basketball_shared_hessian_v6.py`; residual/J and raw/bounded depth
derivative/curvature thresholds inherit the applicable checks in
`test_basketball_shared_inherited_v6.py`, now applied elementwise to independently
derived full arrays rather than to selected finite-difference directions. Cost
and gradient split components use their same-category full-component thresholds.
All H symmetry checks use absolute `1e-10`, rtol zero. Identity nuisance blocks,
zero-weight acceleration, input/cache ownership and repeated-request outputs are
exact contracts. Check candidate and reference symmetry separately, not by
symmetrizing a failure. Reference remains the right operand for comparisons;
archive comparisons use newly independent value as reference and do not revise
historical qualification. All comparison rules are frozen before results.

Compare all 32 slots, every full/split gradient/Hessian entry, r/J, z/Jz, g/Jg,
gp/gpp, weighted raw/bounded H and coordinate transports. At all 16 returned
states compare every force, KKT component, infinity norm and original
complementarity. Preserve weight-zero and qualified-control strata separately.
Report each sequence's exact cache/request/public-replay result, not just maxima.
No fit-convergence claim follows from replayed report functions or synthetic cold
weights. Transport self-consistency alone is not independent derivative evidence.

Before spawn, `run` verifies frozen hashes/readiness/auth/deadlines and exclusively
writes `started.json` consuming the invocation even on launch failure. Worker
has supervisor token, PID/PGID/SID and exclusive consumed marker; supervisor owns
the actual process group and records namespace identities. Numerical end is
`min(start+900,T0+4500)`; reserve the last five seconds for TERM/KILL/reap.
Persist/fsync context and low-level entry before arithmetic, output via exclusive
create, then completion/hash. Check deadline before and after each entry and
inside observation/setup loops. Import time, failures, comparison and I/O count.

Known component numerical failures may retain later already scheduled independent
slots within this one pass; they never trigger another method/state/precision.
Expected public-y guard rejection follows section 5. Actual source/provenance,
unadmitted entry, ownership, permission, interruption or deadline failure stops
dependent work; no exhausted limit can be bypassed through packaging. Parent and
supervisor interrupt/reap owned work on loop stops. Retain partial outputs and
unknown/interrupted counts honestly. No scientific worker/job may remain at handoff.

## 9. Evidence, acceptance and next handoff

Perform numerical comparisons inside the supervised pass. `package` afterward
uses retained JSON/bytes/hash/count validation only, imports no evaluator and
does not recompute derivatives/transforms/forces. Retain inputs and source maps,
entry/actual-entry journals, per-setup/context arrays, rational outputs, transport
and comparison records, commands/toy logs, process cleanup, deadline/consumption
reconciliation, and decision. No arbitrary repeated packaging mathematics.

| Acceptance | Required evidence and criterion mapping |
| --- | --- |
| A1 admission | All 16 cases/32 slots and original operands/provenance pinned, unchanged history, no substitute state/source; SC-05 prerequisite for SC-01/03 |
| A2 implementation/integrity | One fixed coherent full candidate and independent reference, applicable 20-case readiness, owned finite execution within every ceiling, honestly retained partial/failure evidence; SC-05 |
| A3 canonical numerical qualification | All prescribed cold/returned components and five canonical request orders complete and independently within frozen tolerances, including offset/mixed curvature, constraints and actual-multiplier returned reports; evaluator prerequisite SC-01/03 |
| A4 public-coordinate qualification | Every prescribed public replay is byte-exact, accepted at the actual state, all cache/request checks pass, both saved/new transform algebra passes; otherwise explicitly failed or missing, never concealed by A3 |
| A5 retained milestone | Report/decision, all available components adjudicated, scope/budget/source/process checks, no jobs, validated task-only local commits; SC-05, preserve SC-02/04 evidence |

Keep package integrity, implementation completion, canonical qualification,
public-path qualification and overall evaluator qualification separate. A
properly retained numerical rejection is a completed reviewable implementation
milestone. `qualified_on_fixed_cohort` requires complete A1–A5 and every prescribed
component/request comparison passing. A known failed comparison/replay means
`rejected`; missing/incomplete execution means `incomplete`, with known failures
still explicit. No tolerance relaxation or post-science repair is authorized.

Report exact measured setup/component/reference/comparison and supervised times,
final phase including commits, consumed/returned/interrupted/unknown counts,
both toy slots and zero forbidden/training work. Validate task-related Markdown
links, whitespace/diff and retained JSON/hash consistency. Stage explicit task
paths using separately escalated `git add`, inspect staged diff, and separately
escalated `git commit` with title and description per AGENTS.md. No push/amend
or history rewrite. A staging/commit failure stops the loop; parent records it.

Publish `accepted_timing=null`, `production_candidate=null`,
`final_validation_protocol=null`, `ready_for_full_screens=false`,
`main_objective_attained=false` under every result. Preserve v11 A2/A3 failures,
v12 failures and the other 57 unadjudicated ray failures; v14 operating-cohort
evidence cannot retrospectively relabel them.

If the entire fixed cohort qualifies, next Review must use this evidence and
retained cold failures to select one finite full-coordinate solver intervention
and fresh baseline addressing the remaining focused solver gate, including
weight-zero stopping/initialization failures. Do not default to another arithmetic
ladder or enlarged passing cohort. If canonical components fail, next Review
selects a finite repair of the exact recorded component/coordinate defect. If
only public replay fails, next Review selects an explicit solver-coordinate/state
ownership design and finite allocation for that interface; do not infer a
derivative failure or evaluate rounded replacement states under this spent plan.
If execution is incomplete, identify the precise missing prerequisite. No routine
budget question replaces this outcome-linked next Review/Plan work.

[Plan 015 sections 6 and 8](plan_015.md) remain binding: all focused targets and
dependencies qualify within both 200 caps, controls/costs and all three paths
agree; missing seeds/transform/support/growth/initialization/stopping gaps must
be resolved before screens. Full conditioning requires original 144 attempts/48
problems, preserved 94 v6 qualifications, at least 25/50 recoveries across groups
and median KKT ratio <=0.1. Independent scalar screening retains 7,344 initial
paths, inclusive 0.05/0.01 refinements and all nine basin/cost comparisons. Both
screens precede the 144-path combined pilot, then evaluator/selection/final
validation gates before accepted timing and Basketball preparation/reconstruction
and measured quality/motion/speed/resource comparison. Keep KKT <=1e-6,
qualification depth >1e-7 and competitive objective tolerance
`1e-6 + 1e-4*max(abs(F1),abs(F2))`. Preserve all splits and scientific gates.
SC-01/SC-03 remain unmet until their saved required outcomes are evidenced.
Parent reassesses every criterion and continues the active loop unless a stop
applies; this plan's completion/local commit is a checkpoint.
