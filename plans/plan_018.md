# Plan 018 — Diagnose the growing v10 Basketball trajectories

## Objective and authorization boundary

Iteration 002 of the [saved objective](../docs/continuous-improvement/20260908-plan016/objective.md),
from the [review](../docs/continuous-improvement/20260908-plan016/iteration-002-recommendations.md)
and [assessment](../docs/continuous-improvement/20260908-plan016/iteration-002-assessment-01-review.md).
Determine what the actual conditioned cold trajectories and their fixed
displacement rays support: competitive feasible escape directions, finite drift,
or unresolved behavior. This advances the Basketball timing prerequisite for
SC-01 and SC-03, with bounded reproducibility under SC-05. Completing this
diagnostic does not complete those criteria or the reconstruction objective.

**Planning is authorized; implementation and all new numerical work below are
proposed and require execution authorization before dispatch.** The user resumed
the same objective without adding numerical resources. Plan 016 consumed its
405 scheduled scientific attempts and six preflight allocations, with scientific
work finished at minute 16.67 and audit at 22.11; neither unused historical time
nor this plan renews those allocations. The 24-hour training ledger and its
method/scene allocations cannot fund this work.

Read AGENTS.md, the objective, status and latest assessment before implementation
and after context loss. No further delegation; never read `prompts`. Preserve
historical sources, fixtures, flags, thresholds, ledgers and evidence. Follow the
single escalated retry/stop rule for suspected sandbox/permission failures and
stop on staging or commit failure. Parent owns loop status and assessments.

## Proposed scope and hard limits

Ask for exactly one diagnostic implementation phase:

| Scope | Ceiling |
| --- | --- |
| Implementation through validation, packaging and local commits | 30 minutes hard elapsed, starting before implementation inspection |
| All scientific reconstruction/evaluation and independent verification | 120 seconds cumulative wall, included in the 30 minutes |
| Execution concurrency | One numerical worker; single-thread libraries; at most two CPU processes including supervisor |
| Primary finite-state slots | 48 saved snapshots + 24 rays × 23 amplitudes = 600 |
| Independent finite-state slots | The same 600 slots, one pass |
| Analytical limits | 24 primary + 24 independent |
| Residual/Jacobian entries | At most one per finite slot/pass: 1,200 total |
| Depth/Jacobian entries | At most one per finite slot/pass: 1,200 total |
| Optimizer/local-fit attempts, Hessians, finite differences | Zero |
| Full screens, real-data fitting, training, rendering, GPU, downloads/installs | Zero |

Slots cannot transfer between inputs, passes or purposes. A repeated callback,
cache hit, zero ray, infeasible probe, exception or denial consumes its scheduled
slot without replacement. Record actual entries separately from scheduled slots.
No retries of scientific passes, including after a code correction; retain
partial evidence and seek a separately planned allocation if needed. The
repository's permission retry rule still applies when it is safe: resume only
the denied operation with unconsumed slots and unchanged deadlines, never replay
successful evaluations. If safe continuation cannot be established, stop.

Parent records authorization and T0 (UTC and monotonic) before dispatch, with
absolute deadlines T0+600 seconds for input admission, T0+1200 for implementation
and regression readiness, T0+1320 for the end of numerical work, and T0+1800 for
the entire phase. Missing an intermediate deadline stops its dependent work;
package available evidence. No historical clock edits or resets.

Start the numerical clock **before** constructing basis/derivative arrays,
coordinate mappings, trajectory normalization or analytical limits for the
scientific inputs. Use one supervised worker invocation for the complete primary
then independent sequence; its wall time, including imports, freezing and I/O,
is the cumulative numerical charge. Supervisor starts the child in its own
process group, gives it deadline `min(now+120, T0+1320)`, and terminates that group
on expiry or interruption (TERM, then KILL after at most two seconds, with TERM
early enough to finish by the hard deadline). Flush allocation/entry records
before numerical calls; persist completed slots as they finish. Supervisor
retains exit status, PID/group, elapsed time and observed journal counts even
if the child fails. Parent independently enforces T0+1800 and stops any run jobs.
No more than one worker can be alive; record thread environment and process count.

The 120-second estimate is conservative, not a guarantee: existing v9 diagnosis
took 16.15519 s and v10 cohort reverification up to 9.73552 s; twice their sum is
51.78142 s for different scopes. Stop with partial evidence if the estimate fails.

## Fixed inputs and narrow implementation surface

Let `V10=docs/experiments/basketball-shared-timing-v10`. Admit these twelve
`<arm>/conditional-<NN>/cold/{attempt.json.gz,receipt.json,journal.jsonl}` records:

| NN | Group | Weight | Baseline callbacks / selected ordinals | Metric callbacks / selected ordinals |
| --- | --- | --- | --- | --- |
| 00 | 2 | 0 | 200 / 0,66,132,199 | 200 / 0,66,132,199 |
| 07 | 9 | 0 | 200 / 0,66,132,199 | 200 / 0,66,132,199 |
| 13 | 11 | 0 | 200 / 0,66,132,199 | 200 / 0,66,132,199 |
| 03 | 2 | 1 | 38 / 0,12,24,37 | 32 / 0,10,20,31 |
| 10 | 9 | 1 | 39 / 0,12,25,38 | 32 / 0,10,20,31 |
| 16 | 11 | 1 | 36 / 0,11,23,35 | 30 / 0,9,19,29 |

Baseline arm is `baseline/policy`; metric arm is `adapt/metric`. All have camera
offsets `{1:0,2:-25,3:-25}`, 54 coefficient parameters, 300 depth multipliers
and 54 bound multipliers at every selected callback. The stored order rule is
`[0, floor((n-1)/3), floor(2*(n-1)/3), n-1]`. Callback ordinals are not distinct
evaluated-state counts (the failing metric records have 200 callbacks and 193
distinct states). Planning inspected JSON only and confirmed each last callback's
state equals `row.returned_state`; recheck exact physical bytes on admission.

Create only:

- `scripts/basketball_shared_trajectory_diagnostic_v11.py`: admission, supervised
  evaluation-only reconstruction, primary snapshot/ray analysis and packaging.
- `scripts/basketball_shared_trajectory_verify_v11.py`: separate independent
  arithmetic and journal/identity verification, invoked by the same worker after
  primary artifacts are closed and reloaded.
- `tests/test_basketball_shared_trajectory_v11.py`: non-optimizing regressions.
- `docs/experiments/basketball-shared-timing-v11/`: immutable `admission.json`,
  `inputs.json`, `execution-sources.json`, `rays.json`, primary and independent
  journals, `snapshots.json.gz`, `probes.json.gz`, `limits.json`, `verification.json`,
  `budget.json`, `decision.json`, and retained test/command logs.
- `docs/experiments/basketball-shared-timing-v11.md`: per-case findings, limitations,
  measured budget and concrete next recommendation.
- Run artifacts `iteration-002-implementation.md` and
  `iteration-002-validation.md` under the existing continuous-improvement directory.

Reject existing output files/directories before writes; do not silently select
a new experiment or overwrite evidence. Record a blocker if these names collide.
Use the installed `.local/envs/calibration-global/bin/python`, with OMP,
OPENBLAS, MKL and NUMEXPR thread counts set to 1 before scientific imports.
Freeze the exact reproduction commands in admission; provide CLI operations
`admit`, `run` (supervised primary+independent), and `package` (JSON-only).
`run` requires the admission and authorization record and refuses expired,
started or consumed execution. A future reproduction requires a fresh explicit
allocation; documentation must not imply a free rerun.

## Work 1 — Admit immutable data and execution identities (SC-05)

Before scientific entry, use JSON/bytes/hashes only to bind the twelve records
to `V10/package/attempt-index.json`, `prepare/benchmark-manifest.json`, both
policies, `prepare/execution-sources.json`, terminal/independent reports and
the historical analytical audit references. Check complete journal prefixes,
allocation identity, receipt/artifact/completion hashes, policy and reference
matches, null seed provenance, mathematical-problem identity and source hashes.
Check the archived `problem` event matches `row.accounting.problem`, and final
transform event matches saved P/origin/scale bytes. Retain all original identities;
give new evaluations a distinct plan/pass/slot namespace. Do not invoke existing
`verify_item`, `verify_row`, `detailed_evidence`, or `make_problem` here: these
perform numerical work outside this diagnostic's slot accounting.

Bind each selected callback to its existing state record, journal and full
multiplier arrays; freeze callback x/q/y bytes, state ID, objective, min-depth,
solver optimality, barrier parameter and trust radius. Freeze returned x/q,
state and row multipliers separately. If returned and last callback bytes do not
match, stop admission: no replacement callback or 49th snapshot. Missing
multipliers/provenance are unavailable evidence, never reconstructed from barrier
parameter. Hash exact source files used by both new modules plus their imported
mathematical dependencies and installed NumPy/SciPy provenance. Freeze inputs,
schedule, output paths, tolerances, exclusions and deadlines before evaluation.

## Work 2 — Reconstruct and assess 48 fixed snapshots (SC-01, SC-03, SC-05)

Reconstruct an **evaluation-only** `SplineProblem` instance without calling its
constructor, `initialize_coefficients`, synthetic generation, triangulation,
least squares, `sanitize`, `set_transform` or any fit. The saved
`accounting.problem` contains observations, calibration, offsets, free set,
window, spacing, weight and provenance; row contains knots, center and diameter.
Decode keys/arrays preserving ordering and float64 values; require fixed free
set `[]`, fit frames 50–149, window `[50,149]`, spacing 10, one listed group,
18×3 coefficients. Populate the existing evaluate/unpack fields directly:
groups/cameras/offsets/window/spacing/weight/check, saved center/diameter,
`BSpline(saved_knots, eye(18), 3, extrapolate=False)`, quadrature from the pinned
`basis` formula `(window[0]-25 .. window[1]+25 inclusive)/25`, accel from its
second derivative, `n`, `nacc`, empty index/free, n_offsets=0, nc=18 and caches.
If a shape-only `x0` is needed by a raw-depth wrapper, use saved first callback
bytes and label it as such; never use it for initialization or optimization.
Check knots/quadrature/rig normalization against pinned formulas within the
numerical charge, without generating new observations or fits.

Use physical x bytes as authoritative evaluation arguments; do not round-trip
them through x→q→x. Restore saved `q`, `P`, `origin`, `scale`; verify
`q=origin+P@y` and `x=scale*q` against the archived canonical/physical bytes using
the original operation order. All twelve scales must be exactly one. Evaluate
depth/Jacobian once first and residual/Jacobian once if feasible and finite,
through entry wrappers observing the actual passed bytes; no hidden Hessian,
SVD/conditioning reconstruction or support-helper evaluations.

At each snapshot save trajectories and camera/frame/corrected-time links,
max-absolute sampled normalized XYZ and coefficient magnitude, objective split
into the original pointwise one-pixel soft-L1 mean and weighted acceleration,
all normalized depths, G=`2 J.T r`, actual multiplier terms, KKT and norms.
For depth slack s=`z-1e-8`, transformed g=`s/sqrt(1+s²)`, use saved depth
multiplier vg to obtain vd=`vg*g'(s)`; bound force is `inv(P).T@vb_y`.
Original KKT is `G + D.T@vd + bound_force` (q and physical x coincide here).
Save `vd*s`, raw/transformed slacks, saturation/underflow flags and
`P.T@KKT` for comparison with callback solver optimality. Callback
`optimality` is in solver coordinates; do not compare it directly to original
KKT. Keep barrier parameter as context, never a replacement multiplier.

Compare snapshot objective/min-depth and transformed KKT norm to applicable
callback fields. At the matching returned snapshot also compare all saved
G/C_depth/C_bounds/KKT/depths/multipliers/complementarity fields. Inherit objective
`atol=1e-10,rtol=1e-9`, depths `1e-12,1e-12`, G/forces/KKT `1e-10,1e-8`,
multiplier mapping `1e-12,1e-10`, and exact state/source identity checks from
v9/v10 verification. Do not loosen tolerances after observing results; retain
an arithmetic mismatch as verification failure. Report original growth values
and ratios alongside the unchanged flag `final > max(1e6,100*initial)`.

## Work 3 — Freeze and evaluate only 24 displacement rays (SC-01, SC-03)

Use only the six metric records. At exact returned physical coefficients C*,
take Δ=C*−C_first and Δ=C*−C_two-thirds, then both signs: four rays per input.
Let m=max absolute component over **all original observation-time normalized
XYZ displacements** BΔ. For m>0, direction d=±Δ/m, preserving all 54 entries;
ray coefficients are C(a)=C*+a d. Save Δ, m, d, base bytes, operand state IDs,
equations, source hashes and exact little-endian float64 direction bytes in
`rays.json` before any probe/limit evaluation. Independent verification repeats
this derivation from source snapshots. No reconditioning, coefficient deletion,
bounds, offset change, added regularization or alternate direction.

If m=0, retain all four affected sign/direction slots as applicable; distinguish
Δ exactly zero from nonzero coefficients with zero sampled displacement. Do not
divide, invent a norm or choose another ray. Report structural unobservability
only when certified; otherwise unresolved normalization. All 23 amplitude slots
remain present with their degenerate/skipped reason and cannot transfer.

For each nondegenerate ray evaluate exactly `10**e`, even e=0..44, in increasing
order: 23 planned slots. No amplitude-zero entry: reuse its selected returned
snapshot. Before objective entry check finite state bytes, then original depths
`z>1e-8`; retain nonfinite/infeasible states with null objective and no restoration.
Record attempted bytes and entry errors, including overflow, without using NaN
as a valid metric. Saturated depth transformation is diagnostic context; do not
silently change the original objective or call a solver. Save each finite
objective/data/acceleration cost, depths, sampled magnitude and comparisons to
its **own** saved returned objective; weight-one controls are different objectives
from weight-zero cases and cannot supply their competitive-cost reference.

## Work 4 — Analytical limits and independent verification (SC-01, SC-03, SC-05)

Adapt the mathematics in `basketball_shared_diagnose_v5.ray_limit` and the scalar
BSpline verifier in `basketball_shared_verify_v8.verify_escape`; do not execute
their historical campaigns, baseline searches or extra probes. For each original
sample retain camera-space b=(B C* diameter+center) R.T+t and
v=(B d diameter) R.T. Normalized depth is `(b_z+a*v_z)/diameter`.

- Any negative depth slope rules out an indefinitely feasible positive ray;
  report the first finite feasibility boundary from this affine formula.
  Zero slopes require positive base slack. Preserve strict original margin.
- Positive v_z has projective limit `v_xy/v_z`; certified zero v has constant
  projection `b_xy/b_z`; zero v_z with nonzero transverse v has divergent
  projection (under the pinned nondegenerate calibration). Apply the original
  radial distortion and pointwise robust loss, then average across all samples.
- For weight one, acceleration is A C*+a A d. Nonzero A d gives quadratic
  acceleration divergence; invariant acceleration contributes its base cost.
  Constant coefficient translation is a structural invariant. A numerical
  zero after cancellation alone is not a structural proof of invariance.
- Certify compact-support zeros from active coefficient indices and exact knot
  intervals, not from a rank or norm tolerance. Never turn a tiny nonzero depth
  slope into zero. Retain numerical values and structural-zero provenance
  separately; unsupported cancellation/sign disagreements, overflow or
  unverifiable zero limits remain unresolved. Do not add adaptive precision or
  numerical samples to force a classification.

Compute `max(abs(b_z/v_z))` on nonzero slopes and report endpoint/limit gaps
and transition-scale-to-1e44 ratio. An endpoint far from its limit can reflect
small depth slopes; do not extend the ladder or treat it as proof against the
analytical limit. Preserve per-ray flags and classify, in order: degenerate or
unresolved arithmetic; infeasible at infinity; structurally unobservable and
objective-invariant; divergent objective; finite noncompetitive limit; competitive
feasible finite limit. Competitive means F_limit≤F_return+τ, with
`τ=1e-6+1e-4*max(abs(F_limit),abs(F_return))`. Separately report strictly lower
by more than τ, indistinguishable, nonmonotonic, or insufficient finite-probe
trend using the same pairwise tolerance. A finite improvement on an eventually
infeasible ray is a finite observation, not a feasible escape classification.

Independent pass reloads closed primary files and original admitted records,
then reconstructs each scheduled snapshot/ray state and analytical limit once.
Use scalar coefficient BSplines and direct camera geometry/robust-cost and
point-loss gradient formulas (`verify_v9.direct_gradient` is a reference), not
primary residual/limit results as input. Construct depth Jacobians independently
from B and camera rotation; reconstruct original forces/KKT from saved multipliers.
Count each direct objective/gradient bundle as a residual/Jacobian entry and
each depth/Jacobian bundle as a depth entry, even without materializing a residual
Jacobian. Share immutable decoding/budget helpers only, not computed primary
arrays or classifications. Compare finite costs, depths, gradients and forces
at the inherited tolerances above; check analytical costs at objective tolerances
and classification comparisons at τ. Independent cancellation/feasibility
disagreement must remain explicit, not majority-voted away.

Both passes write requested slot IDs, operand/physical hashes, cache-hit status,
entry/return/error/skipped events and counters before dispatch. Deduplication may
save entries within a pass but never erase slot ownership, transfer capacity,
or reuse primary arithmetic as independent evidence. Independent audit
reconstructs counts from entry journals and expected fixed Cartesian schedule;
reject unallocated entry, duplicate entry type, extra pass/state/limit, source
mutation, missing completion or unreconciled interruption. No KKT is invented
for ray states: they have no fitted multipliers.

## Acceptance, validation and handoff

| Plan acceptance | Evidence | Main criteria advanced |
| --- | --- | --- |
| A1: Twelve immutable cases, 48 exact callback slots and 24 fixed ray slots admitted with actual multiplier/state ownership | Inputs/rays/source manifests and journal binding | SC-05 |
| A2: Complete scheduled snapshot/probe/limit records, with justified classifications and explicit mathematical unknowns | Per-case evidence and diagnosis | SC-01, SC-03 prerequisite only |
| A3: Independent arithmetic/identity/classification and entry-count verification passes within every cap | Verification, both journals and supervisor budget record | SC-05 |
| A4: Historical gates preserved, per-failure interpretation and one concrete consequent next step with proposed resources saved, validated work locally committed | Decision/report, run results, tests and commit | SC-01/03 prerequisite; SC-05 |

Unresolved **mathematical** classification is an acceptable A2 outcome if all
scheduled evidence is present and independently verified. Missing evaluations,
timeout, corrupt ownership or arithmetic mismatch make the corresponding
acceptance incomplete/failed; they cannot be laundered into scientific unknowns.

Before the single scientific run, run only focused non-optimizing regressions:
mock/tiny hand-authored cases for pre-entry caps and deadline denial; interruption
with retained counts; duplicate/skipped slots; tampered receipt/state/multiplier
ownership; failure to preserve last-callback/returned identity; analytically
known projective and acceleration limits; exact support zero versus tiny nonzero
slope; depth rejection before objective; and preservation of the original
growth-floor behavior. Verify optimizer/initialization/Hessian entry points are forbidden
by patching them to raise, including problem-constructor paths. Tests must not
load/evaluate the scientific fixture, run existing solver-heavy suites, or add
scientific probes outside these caps. Count toy tests separately and document
their scope. No implementation-mirroring numerical rerun is required.

Package the primary/independent measurements, maxima of verification errors,
counts and actual elapsed times; report accepted/attempted/skipped/interrupted
slots separately. For each failed group compare baseline versus metric snapshot
growth/KKT and metric ray evidence, with its regularized control labeled as
such. Keep the separate near-margin initialization finding as a future topic;
do not bundle an initialization policy or another optimizer arm. Recommend the
single next investigation justified by these results and its required resources;
do not execute it. A competitive feasible ray, even with decreasing finite
costs, does not prove absence of a finite minimizer, necessary solver escape,
or outer timing unidentifiability. Noncompetitive finite rays do not exclude
other directions.

Retain `ready_for_full_screens=false`, accepted timing, production candidate and
final-validation protocol null; no new qualifying solver result exists here.
All Plan 015 conditioning, scalar, combined-pilot and evaluator gates still
precede real Basketball preparation/reconstruction and the eventual saved-model,
reload/render and quality/motion/speed/resource comparison. SC-01 and SC-03 remain
not met; no fresh training/reload claim changes SC-02/04/05's existing evidence.

Check touched Markdown links, task diff and `git diff --check`, and confirm
historical input hashes unchanged. Save commands, acceptance outcomes, remaining
gaps and budget reconciliations in the two iteration result files. Stage only
explicit task paths with escalated `git add`; inspect staged diff; use a separate
escalated `git commit` with title and description per AGENTS.md. No push/amend.
Commit completed validated work within the phase deadline; record partial or
blocked work honestly. Parent reassesses every objective criterion and, if still
unmet, follows the authorized next review/planning stages without treating this
experiment's exhausted allocation as an overall-loop time limit.
