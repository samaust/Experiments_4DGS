# Iteration 005 Review — integrate and qualify the evaluator on operating states

Recommend one versioned **full-component evaluator integration and qualification**
on the fixed retained cohort below. Use the passing Decimal80 acceleration design,
extend it to every coefficient and its Hessian, and check the complete objective,
constraints, coordinate maps and state ownership against an independent reference.
Include both acceleration weights and actual free-offset states. Do not run another
extreme-ray or precision ladder. Do not fit or select timing in this next plan.

The required [objective and criteria](objective.md), [saved status](status.md),
[latest assessment](iteration-004-assessment-03-implementation.md) and repository
[instructions](../../../AGENTS.md) were read before this Review. SC-01 and SC-03
remain not met. Existing SC-02/04 evidence and SC-05's historical limitations remain
applicable; no new model, timing acceptance or comparison is established here.

## Evidence and the gap this work addresses

- [Plan 020](../../../plans/plan_020.md), its [implementation](iteration-004-implementation.md)
  and [validation](iteration-004-validation.md) establish one consumed setup/six
  bundles and all 42 passing comparisons: six costs and 36 selected partials.
  [Decision](../../experiments/basketball-shared-timing-v13/decision.json),
  [package checks](../../experiments/basketball-shared-timing-v13/package-validation.json),
  [comparisons](../../experiments/basketball-shared-timing-v13/comparisons.json) and
  [budget](../../experiments/basketball-shared-timing-v13/budget.json) were inspected
  as retained JSON. Numerical time was 0.12248898699181154 seconds; final phase
  time was 914.2315437420039 seconds, including commits `f78afee`/`38ffef8`.
- The [v13 integration map](../../experiments/basketball-shared-timing-v13-integration.md)
  correctly identifies unqualified components: the other 48 gradient entries,
  image/depth terms, free offsets, full curvature, conditioned callbacks and
  returned-state KKT. Current objective callbacks and return reporting separately
  use `r@r` and `2*J.T@r`; replacing six entries cannot integrate the new arithmetic.
- [V11](../../experiments/basketball-shared-timing-v11.md) retained 48 passing
  operating snapshots, but failed 63 regularized-ray gradient comparisons.
  V12's exact reference and v13's six-state pass do not adjudicate the other 57
  failures or change v11 A2/A3. The old direct floating evaluator is useful
  corroboration on operating states, but is not an unquestioned reference.
- [V10](../../experiments/basketball-shared-timing-v10.md) still has six missing
  required seeds and eight target-path disagreements. Conditioning's median KKT
  ratio 0.2419725969 fails 0.1; the final policy qualifies 50/81 and preserves
  47 archived controls. The large weight-zero trajectory growth and nonstationary
  returns are unaffected algebraically by an acceleration replacement.
- The four saved metric joint targets add the missing free-offset coverage.
  Retained JSON shows one qualified weight-one joint return (group 11, objective
  2.966302546090876, KKT 2.3176996496692532e-7) and three unqualified weight-zero
  returns (groups 2/9/11, KKT 0.0005590247821062276 / 0.2013183434466703 /
  0.5168447305159112). All have free camera `[3]`, 55 parameters, 300 observations,
  an exact owned cold-transform state and a last callback matching the returned
  state. These are retained observations, not newly computed diagnostics.

This next step advances the applicable evaluator-integrity prerequisite for
**SC-01/SC-03**, while its source/entry/validation evidence advances **SC-05**.
It cannot establish the broader timing or reconstruction gates by itself.

## R1 — freeze the actual operating cohort and its provenance (SC-01/03/05)

Use exactly these 16 retained cases, in the order shown. For each, admit (a) the
returned state and (b) its unique `cold_transform` state from `row.accounting.events`
and the associated `row.accounting.states` entry. Thus there are exactly 32
case/state slots; repeated cold physical bytes across weights/arms remain separately
owned slots. No state may be replaced because it is inconvenient or fails.

The first twelve cases are the exact ordered `cases` in
[v11 inputs](../../experiments/basketball-shared-timing-v11/inputs.json), SHA-256
`7a4b5aebeb5652051298ab88103a44af63a13ed69163eda988b333169cdf11f0`.
They have 54 parameters. The last four are direct v10 metric attempt artifacts,
with paths given after the table. Returned physical-byte hashes below were read
from owned ledger bytes and hashed without scientific evaluation.

| Case | Weight | Returned physical SHA-256 |
| --- | ---: | --- |
| baseline/conditional-00/cold | 0 | `db11fab16ab476b5d9df521b157a3b1072c1f3031ea033a4eb18cc04765a23ca` |
| baseline/conditional-07/cold | 0 | `dc9bf15e54fe30d67c632c97bd11a0f90a2b4bb5984a05af4b8d08aabca0c0b1` |
| baseline/conditional-13/cold | 0 | `02e4f7ab85a134e1e7f1bd77198709f3079c3065f51ca9bc86d2422c3c63066e` |
| baseline/conditional-03/cold | 1 | `ffb23e539ccabb9498085a8c50cc541a95985d0cc172337f8ce35b64b87af951` |
| baseline/conditional-10/cold | 1 | `d68099a6af70fbf533d86bafaf659f32730169c70682a45cd61e3e9342d15452` |
| baseline/conditional-16/cold | 1 | `7b8feca7b4dd9280e2a3380df2d4e495ae11a23b2c53fedd899d6a3b357d13dc` |
| metric/conditional-00/cold | 0 | `d87dcae3a930c1b774b275ac990b4a2103ed83bac250a8650d09db6d2005a20f` |
| metric/conditional-07/cold | 0 | `b02eace66a282357ad63027e276a3f61c166876fe72197a3b848bedb16d1c76c` |
| metric/conditional-13/cold | 0 | `94543bc6cc617c8a38d8042a2b49cb79aa5e75add4bde964b5a54f6cb4558414` |
| metric/conditional-03/cold | 1 | `9367a4edb6a3b747e812591ef8c79c92615ddd3cf689a5e0b626cf801c584af8` |
| metric/conditional-10/cold | 1 | `6553abcbfbed90ce1584ee2baa8996af95059906ff6aab2de48f902ab52a036d` |
| metric/conditional-16/cold | 1 | `5dbe1efc337cbcb23591b0ba64fb5201a5e0342b2d81a4bfddb77d8bb51bfffa` |
| metric/joint-00/descending | 1 | `3b2383823e8f8a331b00bef1e3e85a2a1df4564ec6240782924c011cc1770bbc` |
| metric/joint-01/cold | 0 | `a355224c50e7af771f43410feaf3e6171902ae1dd6a3557a458552b5e016884d` |
| metric/joint-02/ascending | 0 | `667bd576fae8f08e8d84543a20f53cb41d698f172aa69c196d0f55787240111e` |
| metric/joint-03/ascending | 0 | `fa8fb254063db7c159cc4855979f40c127b72791728f324397a0cffabc759369` |

Joint files are under
`docs/experiments/basketball-shared-timing-v10/adapt/metric/`:

| Relative artifact | SHA-256 |
| --- | --- |
| joint-00/descending/attempt.json.gz | `a2fb9d0a21f64e5ee6a0c36be4e3b44f427ecb7a06e31382db695e03e17c9a00` |
| joint-01/cold/attempt.json.gz | `d9a17bc42c285590e958db87f6ac7a34da23a8b7ce7992ee8759d98629f558c5` |
| joint-02/ascending/attempt.json.gz | `c5eed24abdc478c65122879ff90f4b887e4396c44bfe6096d65633fddf92a980` |
| joint-03/ascending/attempt.json.gz | `55a455004532ecc30329d766f74298948440ad735c5b2145c4dc4a760b0ec4cc` |

Plan must pin the exact cold canonical/physical hashes, returned q/y, multiplier
bytes, transform/origin/scale, problem definitions, journals/receipts, source
substitution maps and relevant installed dependencies during read-only planning
or admission, before arithmetic. Bind observations/calibration/offset conventions,
gauge, training role/window `[50,149]`, spacing 10, weight, knots, quadrature and
normalization. Preserve held-out exclusions. Reconstruct from admitted metadata
without `SplineProblem.__init__`, synthetic-data generation, initialization fits,
calibration, quadrature regeneration or any optimizer. A missing or inconsistent
identity fails admission; it does not permit a substitute.

## R2 — one coherent versioned candidate (SC-01/03/05)

Use new v14 modules and namespace; do not change the hash-bound v2/v6/v9/v10/v11,
v12 or v13 sources/artifacts. Recommended concrete surfaces:

- `scripts/basketball_acceleration_decimal_v14.py`: extend the v13 fixed Decimal80
  control-difference/transpose formulation to all 54 coefficient partials and the
  full acceleration Hessian. Retain exact binary64 decoding, context, input order
  and all directions. Compute curvature from that same linear acceleration map
  before final export, not from the old rounded `A.T@A`. Explicitly return zero
  acceleration cost/gradient/Hessian at weight zero without evaluating an inactive
  penalty. No precision adaptation, coefficient truncation, snapping or tuning.
- `scripts/basketball_shared_components_v14.py`: expose separately owned data and
  acceleration cost/gradient/Hessian, full sum, residual/J used for conditioning,
  raw depth/Jacobian and weighted raw-depth curvature. Factor the existing data
  expressions into a data-only path; never recover them by subtracting a rounded
  acceleration contribution from a rounded full result. The inherited v6 data
  Hessian may be reused through an explicit data-only view, with its q-coordinate
  convention declared. For conditioning, publish the derivative of the same
  residual representation, including the new acceleration map. Do not interpret
  its floating `r@r` as the authoritative stable objective.
- `scripts/basketball_shared_accounting_v14.py`: add canonical objective-component
  ownership/cache entries; have `fun`, `jac` and `hess` use the coherent result.
  Preserve exact state bytes, immutable states, separate scopes, both 200 caps,
  and pre-entry ledger plus independent actual-entry observation. Cold transform
  construction must be an owned residual/J numerical entry, including its SVD.
- `scripts/basketball_shared_solver_v14.py`: route callback and returned-state
  reporting to one reusable owned-state report function, including interrupted
  returns. Remove the separate `2*J.T@r`/`r@r` return calculation. Exercise this
  reporting function with actual retained states/multipliers and with dummy solver
  callbacks in toys. No SciPy optimizer is invoked in this plan; therefore actual
  optimizer convergence/callback behavior remains a subsequent qualification.
- `scripts/basketball_shared_reference_v14.py`: independent full-state reference
  described below, with no candidate mathematical imports/results.
- `scripts/basketball_shared_evaluator_v14.py` and
  `tests/test_basketball_shared_evaluator_v14.py`: admission, fixed readiness,
  owned one-pass supervisor/worker, comparisons and retained-data packaging.
- `docs/experiments/basketball-shared-timing-v14/`, its sibling Markdown report,
  and iteration-005 implementation/validation artifacts in this run directory.

Freeze one candidate and one independent method before scientific entry. Setup
memoization may share identical immutable knot/quadrature geometry, never fitted
state results between distinct adapter/request-order instances. Record all work,
including construction/imports/reference evaluation and failures.

## R3 — independent full-component validation (SC-01/03/05)

Use an independent local second-order differentiation reference for the scalar
image loss and raw/bounded depth, constructed from admitted original operands.
A concrete feasible design is second-order forward jets for the three spatial
coordinates, then full coefficient/free-offset chain assembly using independently
constructed scalar Cox–de Boor basis values and first/second derivatives. This
avoids copying `projection_second` or the candidate's assembled Hessian. Include
camera rotation/translation, radial distortion, intrinsics, normalization and
robust loss; retain supported observation rows and all mixed/offset curvature.
The independent residual/J representation must also be differentiated directly,
so the conditioning interface is checked beyond merely sharing the candidate J.

For acceleration, use the independent rational Cox–de Boor derivative recurrence
in [v12 method A](../../../scripts/basketball_acceleration_reference_v12.py),
extended in the new reference module to all coefficients and its constant full
Hessian. This is a newly charged reference allocation on operating states, not a
rerun of v12. Exact rational coefficient derivatives isolate acceleration from
the rounded floating transpose that previously failed. The new reference may use
NumPy for image/chain assembly and stdlib Fraction for acceleration; no dependency
installation is needed. Do not reuse candidate basis/J/gradient/Hessian arrays,
autodifferentiate the candidate, or use old float agreement as ground truth.
Independent agreement qualifies this finite cohort only; reference uncertainty
or disagreement must remain visible rather than being resolved by tolerance tuning.

At each of the 32 case/state slots, save full cost splits, every gradient and
Hessian component, residual/J, raw depth/Jacobian, and a weighted raw/bounded-depth
Hessian. At returned states use the actual last-callback bounded-depth and bound
multipliers. At cold states use a fixed all-ones depth weight only for derivative
validation; label it synthetic and make no cold KKT/solver claim from that weight.
Publish candidate/reference component errors and every failed index, not just
aggregate maxima. Check the candidate report's full KKT and complementarity at
all 16 returned states against independently reconstructed forces, then compare
with applicable archived values without changing historical qualifications.

Preserve `x=Dq`, `q=origin+Py`, `Gq=D.T Gx`, `Gy=P.T Gq`,
`Hq=D.T Hx D`, and `Hy=P.T Hq P`. D is 25 for the free camera offset and 1 for
coefficients. V6's objective Hessian already returns q coordinates: do not apply
D twice. Its raw-depth entry accepts physical x through the v10 unit-scale
wrapper but differentiates q; explicitly declare/check that convention, especially
the free-offset factors and mixed terms. Test bounded-depth first/second chain
rules, `vd=vg*gp`, `Cbq=P^(-T) vby`, original stationarity and complementarity.
Check every component in physical, q and y coordinates with correctly converted
multipliers. Preserve nonfinite/underflow rejection and all exact/null directions.

Use saved P/origin and actual saved multipliers for historical returned-state
checks. Separately evaluate the candidate cold-transform path and its full
invertibility, null/active subspaces and identity offset block. A newly computed
P must not inherit old conditioned multipliers as if an optimizer produced them;
any remapping for an algebraic check must be explicit. A physical→q→y→q round trip
does not establish returned ownership: retained q is authoritative. Public y
requests must identify the actual q/x bytes they compute, and any extra rounded
state must be separately charged and must not replace the saved return.

Use the inherited component tolerances, with Plan freezing each comparison's
reference orientation and floating operation order before entry:

- Objective: `atol=1e-10, rtol=1e-9`; full gradients/forces/KKT:
  `atol=1e-10, rtol=1e-8`; depths: `atol=rtol=1e-12`; multipliers:
  `atol=1e-12, rtol=1e-10` ([v11 tolerances](../../../scripts/basketball_shared_trajectory_diagnostic_v11.py)).
- Full Hessian consistency: inherited `atol=2e-5, rtol=3e-5`, symmetry absolute
  `1e-10` ([v6 Hessian checks](../../../tests/test_basketball_shared_hessian_v6.py)).
  Raw/bounded-depth derivative and weighted-curvature checks retain their existing
  derivative tolerances in [v6 inherited checks](../../../tests/test_basketball_shared_inherited_v6.py).
- Transform inverse/symmetry and exact identity checks retain their existing
  thresholds/contracts in [v10 accounting](../../../scripts/basketball_shared_accounting_v10.py).
  Plan must state the residual/J and newly exposed split-component comparison
  rules using their applicable inherited checks; no post-result relaxation.

These are implementation checks, not new reconstruction-quality thresholds.
Do not run inherited scientific-fixture tests invisibly under a toy allocation.

## R4 — request order, ownership and finite execution (SC-05; prerequisite SC-01/03)

For each returned case, run exactly five fresh adapter sequences, first requested
as (1) objective, (2) gradient, (3) objective Hessian, (4) constraint, and
(5) cold transform followed by the returned-state requests. Fix the remaining
request order in Plan and repeat each cached request once. Exercise constraint
Hessian, full report and both saved-transform and new-transform algebra at the
same explicitly owned state. All sequences must agree on the physical objective
and derivatives, with no duplicate mathematical work on a cache hit and no state
replacement hidden by an approximate key. The cold state is evaluated once per
case, reused only as immutable input/reference evidence; each actual cold-transform
calculation remains an explicitly counted entry.

Before science, freeze at most twenty hand-authored toy cases and run the same
suite at most twice. Cover analytic full acceleration gradient/Hessian including
constant/linear null modes, a nontrivial cubic, all coefficient rows, weight zero,
ambient Decimal context, independent jet chain rules, physical/q/y offset and
mixed derivatives, bounded-depth curvature, all request orders, returned/interrupted
ownership, adjacent states, pre-entry rejection of a 201st state/iteration,
interrupted entries, source/state/multiplier tampering, direct-worker rejection,
immutable collisions, and supervisor timeout/descendant cleanup. Group related
assertions within the fixed cases; do not create an unbounded development suite.
No scientific fixture, archived operating state or constructor/fit is a toy.

Use a one-pass durable supervisor/worker schedule, with the candidate and reference
sequential in one single-thread numerical worker. Consume setup/state/sequence
entries before arithmetic; retain actual low-level entry bytes independently of
ledger exports. Candidate and reference must be unable to read one another's
mathematical outputs while computing. A comparison failure may retain other
already scheduled independent cases within the fixed pass; a provenance/ownership,
permission, interruption or deadline failure stops dependent work. There is no
scientific rerun or post-science repair. Preserve partial outputs and unknown
counts accurately; reap the owned process group before packaging/completion.

## Recommended plan-specific resources and limits

These are new limits recommended for Plan to finalize under standing approval
AGENTS.md `b62f2ea`, in this explicitly active same-objective loop. They do not
reuse Plan 016/018/019/020 clocks or consumed attempts. The complexity is materially
larger than v13's seven-output kernel, so recommend one 90-minute implementation
phase with a fixed 15-minute numerical allowance, rather than assuming v13's tiny
runtime predicts full reference/curvature work.

| Scope | Recommended hard ceiling |
| --- | --- |
| Implementation, admission, source, toys, numerical supervision, evidence and commits | 5,400 elapsed seconds from one parent-recorded T0 |
| Read-only admission finished | T0 + 900 seconds |
| Fixed candidate/reference and passing toy readiness | T0 + 3,600 seconds |
| All scientific work and cleanup ended | T0 + 4,500 seconds |
| Single scientific invocation, including imports/setup/reference/I/O/cleanup | 900 wall seconds within the above deadlines |
| Candidate choices / reference methods / scientific invocations | 1 / 1 / 1; no replacement or retry |
| Admitted cases / case-state slots | 16 / 32 (cold plus returned); no new rays or perturbed scientific states |
| Candidate returned request sequences | 80 (16 × 5); no additional cache-cold replay |
| Candidate cold component bundles | 16; one per case |
| Candidate cold-transform constructions / SVDs | 16 / 16; Plan fixes their ownership and reuse across the five sequences |
| Independent full-state bundles | 32; one per case-state slot |
| Shared acceleration geometry setups | At most 2 candidate and 2 reference, accounting separately for weights 0/1 |
| Scientific optimizer/local-fit/initialization/restoration attempts | 0 |
| Scientific finite differences, new displacements, analytical rays/limits, pilots/full screens | 0 |
| Fixed nonscientific toy suites | At most 2 invocations of at most 20 frozen cases |
| Numerical concurrency | One worker plus its supervisor; one thread per numerical library |
| Training, rendering, GPU, network, download or installation | 0 |

Plan must translate the 96 candidate component bundles, 16 transform entries and
32 independent bundles into an exact maximum entry table for objective/residual,
depth, objective Hessian and weighted constraint Hessian before dispatch. Bundles
must not conceal arbitrary recomputation. Resolve public-y byte ownership within
the fixed admitted-state restriction before readiness: a failing exact replay is
evidence to retain, not authority to create a perturbation sweep. All adapters
retain maximum 200 distinct canonical states and maximum 200 iterations, including
any setup/transform scope; these are ceilings, not an allocation of fits.

Use the existing `.local/envs/calibration-global/bin/python` and installed NumPy/
SciPy plus stdlib Decimal/Fraction; set OMP/OPENBLAS/MKL/NUMEXPR threads to one.
No GPU or NVIDIA skill is needed for this CPU evaluator work. Stop scientific
entry on missed readiness/intermediate deadlines and use remaining phase time for
retention. A completed/exhausted plan prevents more execution under its allocation;
authorized next Review/Plan may continue if no loop stop applies.

Historical training remains 22523.417254 charged seconds under the 24-hour total
and unchanged 7200-second method/scene ceilings. This plan charges zero training
seconds and cannot restart or redistribute budget-stopped methods. Preserve all
405 Plan 016 outcomes/six preflights, Plan 018's one pass, Plan 019's two setups/
twelve bundles and Plan 020's one setup/six bundles/two toy suites and their
recorded elapsed consumption. Parent must record current approval basis, precise
plan link/deadlines and scope before implementation; no routine budget question
is required when these limits fit the unchanged user ceilings.

## Acceptance, decision and the next objective-directed handoff

Plan acceptance must distinguish complete retained evidence from a successful
numerical qualification. Require complete admitted identities, a fixed owned
execution, independent full-component results on every prescribed state/order,
preserved weight-zero and qualified-control reporting, immutable evidence/budget
reconciliation and local commits. Any failed or unavailable component prevents
claiming that the cohort's evaluator passed. Do not relabel a failure as unverified
merely because it is inconvenient; use unverified for missing/insufficient evidence.

If the fixed cohort passes, recommend the next Review move directly to the
remaining focused solver qualification: use the verified component/KKT results
and retained cold-failure trajectories to choose one justified full-coordinate
solver intervention and a fresh baseline, with the frozen target/dependency and
all-three-path requirements. In particular, weight-zero failures require a solver/
initialization/stopping explanation that an acceleration change cannot provide.
Do not default to another arithmetic ladder or broaden this passing cohort simply
to keep testing. If a component fails, identify the exact interface/coordinate/
arithmetic failure from retained differences and make that the finite next repair;
do not tune numerical tolerance or repeat the consumed experiment.

[Plan 015 sections 6 and 8](../../../plans/plan_015.md) remain binding: every
focused target/dependency qualifies within both 200 caps, qualified controls/costs
and three-path agreement are preserved, and missing seeds/transform/support/growth/
initialization/stopping gaps are resolved before full-screen readiness. Full
conditioning still requires the original 144 attempts/48 problems, 94 preserved
v6 qualifications, at least 25/50 recoveries across groups and median KKT ratio
at most 0.1. Independent scalar screening still starts with 7,344 required paths,
the original inclusive 0.05/0.01 refinements and all nine basin/cost comparisons.
Both screens must pass before the 144-path combined pilot. Subsequent evaluator,
selection and final-validation gates still precede accepted Basketball timing,
preparation/reconstruction and measured quality/motion/speed/resource comparison.
Keep KKT at most 1e-6, qualification depth above 1e-7 and competitive objective
tolerance `1e-6 + 1e-4*max(abs(F1),abs(F2))`; preserve all splits and scientific gates.

Publish `accepted_timing=null`, `production_candidate=null`,
`final_validation_protocol=null`, `ready_for_full_screens=false` for this evaluator
plan regardless of its local pass. SC-01 and SC-03 remain unmet until their saved
required outcomes are evidenced; an evaluator improvement is a prerequisite.

## Review execution record

This Review read source, Markdown and retained JSON/gzip JSON, inspected metadata
and computed byte hashes only. It did not import or execute scientific evaluators,
basis/gradient/Hessian/solver calculations, tests, GPU/network/install work or git
mutations. Two guessed read paths did not exist (joint-00/cold and an incorrectly
named v12 basis script); source/path inspection identified the actual descending
joint path and `basketball_acceleration_reference_v12.py`. These were ordinary
missing-file errors, not suspected permission restrictions; no restricted access
was retried or bypassed. Only this recommendation file was written. No subagents
were delegated and no jobs remain. Parent owns the assessment, status and commit.
