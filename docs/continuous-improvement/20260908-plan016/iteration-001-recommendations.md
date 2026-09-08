# Iteration 001 review: available evidence and next authorized milestone

Reviewed on 2026-09-08 against [the objective and unchanged success criteria](objective.md),
[initial assessment](iteration-001-assessment-00.md), [run status](status.md), and
[repository instructions](../../../AGENTS.md). This is the review stage only.
The review used local documents, saved JSON records, source inspection, file
inventories and SHA-256 checks. It launched no optimization, GPU work, training,
downloads or subagents and made no commits. No historical experiment was modified.

## Decision for the orchestrator

**Proceed to planning a bounded milestone that audits and interprets existing
SelfCap evidence, publishes a practical workflow decision, and repairs the current
entry documentation.** This advances SC-02 through SC-05 without restarting an
exhausted experiment or requiring a new compute allocation. Plan 004 explicitly
requires rendered-artifact inspection, reproducible instructions and a comparison
recommendation, and tracks evaluation separately from training. Its unaffected
documentation and saved-artifact work is still within the broader objective.

**Do not dispatch new Basketball numerical work.** Plan 016 exhausted its five
81-attempt scientific policies and six preflight allocations. Its final candidate
failed the scientific gate; no continuation budget was issued. A new focused
scientific phase needs explicit scope, elapsed-time and attempt authorization.
The old 90-minute clock cannot restart, and unused training allocations cannot
pay for an unauthorized continuation. Full screens also remain scientifically
gated even if more time were authorized.

The proposed evidence milestone cannot establish the entire objective: accepted
Basketball synchronization and downstream reconstruction are still absent. Once
useful authorized evidence consolidation is complete, stop at that authorization
blocker instead of repeatedly refining the solver or declaring success.

## Evidence examined and checks performed

### Plan 016 / v10

Read [Plan 016](../../../plans/plan_016.md), the
[implementation report](../../experiments/basketball-shared-timing-v10.md),
[terminal decision](../../experiments/basketball-shared-timing-v10/package/terminal-decision.json),
[workflow verification](../../experiments/basketball-shared-timing-v10/verify/result.json),
[independent report](../../experiments/basketball-shared-timing-v10/independent-report.json)
and [terminal hash manifest](../../experiments/basketball-shared-timing-v10/evidence.json).

- Recomputed all 1,560 artifact and 12 source hashes indexed by `evidence.json`:
  **1,572 checked; zero mismatches or missing files**. This checks retained bytes,
  not a new execution of the numerical verifier.
- The independent report records 405 scientific outcomes, 366 optimizer
  invocations, 97,268 numerical entries and 260 repeated policy qualifications.
  The terminal count of 410 completed outcomes additionally includes five
  completed preflight records; one preflight attempt remains explicitly incomplete.
- The initialization-only final policy has 50/81 qualifying outcomes, six missing
  required seeds and eight conditional-path disagreements. All 47 required
  archived controls retain acceptable costs. Conditioning fails its unchanged
  median KKT-ratio gate, 0.2419725969 versus 0.1; stopping qualifies two of three
  required targets. Feasible initialization alone does not qualify the fits.
- `ready_for_full_screens=false`; accepted timing, production candidate,
  final-validation protocol, candidate hash and continuation budget are null.
  Persistence/verification `passed` is compatible with scientific rejection.
- The clock began 04:52 UTC, with scientific stop at 06:07 and terminal deadline
  at 06:22. The independent audit finished at 22.11 elapsed minutes and the final
  evidence record at 25.81 minutes. Finishing early did not create new policies,
  retries or a renewable time allowance.
- Saved test records report 253 Basketball tests, seven budget tests and three
  SelfCap tests, plus eight additional saved-evidence/supervisor regressions.
  Tests were not rerun in this review. The terminal manifest retains milestone
  commits `d567247`, `d6f84be` and `89860e9`.

This supersedes older timing summaries as the latest current outcome. V9's empty
baseline and previously unverified qualifications remain historical evidence;
they do not become usable seeds or denominators through this review.

### SelfCap models and evaluations

Read [Plan 004](../../../plans/plan_004.md), the
[comparison summary](../../experiments/contender-summary.md),
[native STG completion](../../experiments/contender-native-stg-20260906.md),
[FreeTimeGS final continuation](../../experiments/007-freetimegs.md#final-budget-limited-selfcap-continuation),
[ATGS final continuation](../../experiments/009-atgs.md#final-budget-limited-selfcap-continuation),
the [preparation report](../../experiments/contender-data-20260906.md), and local
final `evaluation.json`, `metrics.json`, `compare-heldout.json`,
`compare-sweep.json`, `reload-a/render.json` and `evidence/sequence-analysis.json`
under each directory below:

- `.local/runs/stg-lite-selfcap-final-evaluation-20260906/`
- `.local/runs/stg-full-selfcap-final-evaluation-20260906/`
- `.local/runs/freetimegs-selfcap-final-evaluation-20260906/`
- `.local/runs/atgs-selfcap-final-evaluation-20260906/`

All four saved evaluations report successful fresh network-disabled reloads,
60 held-out camera-0015 frames and 20 frozen-time sweep renders. The two STG
comparisons establish byte/pixel-exact PNGs; they do not measure raw floating-point
equality. FreeTimeGS and ATGS additionally retain raw-float hashes in render
records. Existing JSON files, PNG sequences, MP4s, contact sheets and fixed crops
are present. The review inspected metadata and prior visual observations; it did
not replay the videos or independently inspect every image.

Recomputed complete final model checksums:

| Model artifact | Bytes | SHA-256 / result |
| --- | ---: | --- |
| `.local/runs/stg-lite-selfcap-final-20260906/checkpoint.pt` | 34,044,289 | `8eac0b3373167db5ff2e5a17c757e9fe5938e60f4b0c8ad55820eff5b9d20d9c` — matches |
| `.local/runs/stg-full-selfcap-final-20260906/checkpoint.pt` | 29,778,653 | `1c810245d4faa182df201eaf00372b8dd7bc23b6e5a2ae8c1f7d0fb8a461a65a` — matches |
| `.local/runs/freetimegs-selfcap-final-20260906/checkpoint-042061.pt` | 3,199,531,938 | `49d732ee75bbc85863acf4eb4b621683b3df51720a69d9e536197fa2a66f7856` — matches |
| `.local/runs/atgs-selfcap-final-20260906/checkpoint-061008-011/` | 3,904,977,664 component bytes | All 11 component hashes and sizes match `bundle.json`; marker hash `7e4d1157c133e7ec57b53aeeb11ef4b66c7cd38aec82ed956021941a39e3f621` matches |

The processed manifest's current SHA-256 is
`f9cbfe6b1f01eba1a6b284579985356bc8497955bd18d696a31e4eb166a48199`, matching all
four evaluations. It records the half-open interval `[4120,4180)`, source 60 FPS,
24 cameras, held-out 0015, 23 training cameras and 1,440 image records. Its time
formula retains camera-specific synchronization corrections. Sparse midpoint
initialization records 23 training inputs and explicitly excludes 0015. All six
STG evaluator/helper hashes recorded by the final evaluation match current files.
The full input image collection, all retained rendered-image hashes, and all
method-specific source/runtime records were not independently checked in this
review; the next milestone should save that audit rather than imply these checks
already happened.

The saved aggregates corroborate the comparison:

| Method | Progress | PSNR / SSIM / LPIPS-Alex | Warm FPS |
| --- | --- | --- | ---: |
| STG Lite | 30,000 steps, native complete | 22.418750 / 0.851204 / 0.219363 | 317.056 |
| STG Full | 30,000 steps, native complete | 24.496753 / 0.864213 / 0.214612 | 224.135 |
| FreeTimeGS reproduction | 42,061 / 70,000 steps | 25.496026 / 0.881698 / 0.137213 | 182.781 |
| ATGS | 61,008 / 100,000 microsteps | 22.180802 / 0.842141 / 0.239707 | 256.625 |

Benchmarks use ten warmups and 100 timed midpoint renders; these are measured
renderer throughput, not end-to-end video throughput. Existing reports distinguish
device-wide sampled memory from allocator peaks and complete training-state size
from inference-only size. Retain those distinctions.

The current motion evidence consists chiefly of start/middle/end observations at
4120, 4150 and 4179, fixed crops and selected sweep poses. It identifies excess
foreground blur/ghosting, including face/hair and hands. Every saved
`sequence-analysis.json` explicitly says adjacent differences include real motion
and do not establish temporal fidelity. They cannot supply a flicker ranking.
Ground-truth-aligned adjacent-frame inspection remains a useful unfinished task.

### Source blockers and current entry documentation

The recorded 2026-09-06 [MoE-GS audit](../../experiments/008-moe-gs.md#prior-implementation-and-experiment-evidence)
finds the modified model and rasterizer source but no validated released
standalone modified-STG expert training route or matching pretrained state.
Router trainers expect experts. The recorded
[FreeTimeGS++ audit](../../experiments/010-freetimegs-plus-plus.md#prior-implementation-and-experiment-evidence)
identifies no usable author fixed-B implementation. Both are availability blockers,
not failed reconstruction quality. This review did not refresh online availability;
date the claims accordingly and do not manufacture a paper implementation.

[The contender entry guide](../../contender-experiments.md) still labels method
integration and all experiment statuses pending, says Basketball calibration must
be obtained, calls an older v4 timing investigation current, and identifies the
23-camera variant as current. These conflict with completed SelfCap runs and the
later accepted 34-camera static calibration/estimated scale. The
[comparison summary](../../experiments/contender-summary.md) also leads with older
v6/v5 timing outcomes and includes the obsolete 23-camera status. Update the
current overview and clearly label retained history; do not alter frozen v10 data.

## Reconciled budgets and authorization boundaries

Read `.local/runs/plan-004-training-budget.json`, `scripts/training_budget.py`
and the training entry points. The ledger has 22 settled `completed` reservation
records, zero live reservations and zero overrun seconds. Those reservation
statuses do not assert native-schedule completion; failed earlier work is included
in charged totals and detailed run evidence.

| Allocation | Charged seconds | Nominal unspent seconds | Executable meaning |
| --- | ---: | ---: | --- |
| STG Lite / SelfCap | 3,819.048855 | 3,380.951145 | Native schedule already complete; this is not permission to change its prescribed schedule or redistribute time |
| STG Full / SelfCap | 4,652.027359 | 2,547.972641 | Same |
| FreeTimeGS / SelfCap | 7,026.107790 | 173.892210 | Below existing restart gate; do not restart or reduce reserves |
| ATGS / SelfCap | 7,026.233249 | 173.766751 | Below existing restart gate; do not restart or reduce reserves |
| MoE-GS / SelfCap | 0 | 7,200 | Source/asset route blocked; preserve 4 × 1,500 s expert + 1,200 s router stages |
| FreeTimeGS++ / SelfCap | 0 | 7,200 | Released fixed-B route blocked |
| All six Basketball allocations | 0 | 43,200 total | Each retains its own 7,200 s; synchronization/input gates prevent training |
| Global 24-hour training allocation | **22,523.417254** | **63,876.582746** | **6.256505 h used / 17.743495 h unspent; no redistribution** |

FreeTimeGS and ATGS use a restart check of available time greater than
`checkpoint_reserve + step_reserve + 35`: default `120 + 30 + 35 = 185` seconds.
Their remaining time is insufficient. The phase-specific Plan 016 no-GPU scope
does not impose a global ban on later authorized GPU evaluation, but there is no
reason to launch such work merely to inspect already-saved evidence.

Historical calibration allocations are separate input-gate allocations. The
comparison records 1,137.541712 seconds in the historical calibration ledger and
an unused conditional extension; that is neither transferable training time nor
authorization to revive a finished calibration phase for timing optimization.
No new numeric loop budget was supplied. Ordinary review/documentation and reading
saved artifacts do not consume the finite scientific-attempt allocation.

## Recommendations mapped to criteria

### R1 — Save an audit of existing SelfCap evidence (SC-01, SC-02, SC-03, SC-05)

Plan and implement a read-only evidence auditor with explicit final-run paths.
Record hashes and existence of required model state, input manifest and
initialization provenance, both reloads, all 60 held-out and 20 sweep records,
saved commands, metrics and resource/budget evidence. Bind filenames to camera,
source frame, normalized time, split, dimensions and shared sweep. Compare
retained PNGs to both reload manifests/comparison hashes. Reconcile existing
aggregate/per-frame metrics and budget totals without rerunning training or
introducing a new score. Retain applicable historical offline reload evidence;
do not call a hash audit a fresh render.

Acceptance: a saved machine-readable inventory and readable audit identify each
check as passed, failed or unavailable, with source evidence paths and hashes.
The four model states and saved output counts must reconcile. Source differences
must be explicitly explained from pinned/archived evidence, never silently
treated as current execution. A missing or changed required file blocks the
corresponding claim. Avoid the existing inventory helper's hardcoded older assets
and output destinations; preserve every prior run.

### R2 — Complete ground-truth-linked motion inspection (SC-03, SC-04)

Use the existing 60-frame sequences and ground-truth-selected crop definitions.
Compare every method at the same frame IDs and timestamps, including adjacent
frames around the documented fast-motion failures. Record which actual frames,
temporal transitions and sweep poses were inspected, with direct image/artifact
references. Where useful, produce a local inspection sheet or playback page from
the retained PNGs; this is evidence presentation, not new reconstruction.

Acceptance: observations distinguish reference motion blur, excess predicted
blur, persistent ghosting, changing boundary errors and unsupported flicker
claims. Describe uncertainty when the evidence cannot isolate a cause or support
an ordering. Raw adjacent MAE is descriptive only; the old analyzer's blinds
crop is not applicable to SelfCap. Do not invent a quantitative flicker metric,
combined score, quality threshold or new scene to manufacture a winner.

### R3 — Publish a usable, profile-qualified workflow decision (SC-02, SC-04, SC-05)

Turn R1/R2 into a decision for the measured SelfCap profile and a concise local
run/reload/evaluation guide. Compare the actual complete model requirements,
initialization differences, charged time, memory and throughput. The present
evidence suggests distinct tradeoffs to assess: FreeTimeGS has the strongest
aggregate metrics but unfinished training and a large resume checkpoint; STG
Full has a completed native schedule, compact complete state and stronger
aggregate metrics than Lite; Lite is the fastest measured renderer; ATGS is not
supported as a quality upgrade on this profile. Final observations should decide
the recommendation and explicitly state its limits rather than defer everything
to unspecified future inspection.

Acceptance: a reader can locate and reload the exact recommended complete model
and render time/view outputs using recorded commands, source/configuration and
environment references. Training instructions respect existing ledger/reserve
gates and are reproduction procedures, not commands to execute in this milestone.
Update current contender-entry and comparison statuses with the v10 rejection,
34-camera Basketball calibration/scale status and synchronization blocker;
preserve historical reports as historical. Include all six candidates and both
profiles in coverage, with dated exact blockers for unavailable methods. Link
checks, command syntax and `git diff --check` should pass before task-only commits.

R1–R3 form one decision-complete next plan. They require no new training, numerical
attempts, downloads or dependency installation. Routine local evidence reading,
presentation and documentation are authorized; do not add numerical experiments
to the plan merely because GPU evaluation was historically separately accounted.

### R4 — Preserve the Basketball prerequisite and surface the next decision (SC-01, SC-02, SC-03, SC-04, SC-05)

Carry the unresolved synchronization dependency into the milestone's final report.
Any proposal for another solver must first define its concrete change and a new,
bounded elapsed-time/attempt allocation for user approval; Plan 016 permits no
post-result tuning or additional policy. The saved costs can inform a proposal,
but they do not justify a precise new total for an unspecified numerical method.
Full screens, production fitting, selection and reserved final validation retain
their separate scientific gates. Accepted timing is required before shared
Basketball inputs, training-only initialization and the unspent method budgets
can produce a two-profile comparison.

Acceptance for the evidence milestone is an explicit dependency and authorization
record, not an accepted Basketball result. After R1–R3, if this remains the next
necessary work, stop the loop for the user's budget/scope decision. Do not
substitute SelfCap success or a clean scientific rejection for the main objective.

## Criterion assessment for the parent to record

| Criterion | Proposed status | Reason and evidence |
| --- | --- | --- |
| SC-01 | not met | SelfCap preparation/split/time provenance exists and matches the shared manifest. Basketball accepted timing and resulting validated shared reconstruction inputs remain absent in the verified v10 terminal evidence. |
| SC-02 | unverified | Strong positive historical evidence: four complete matching model inventories, 60 held-out + 20 sweep offline reloads per method and saved commands. This review verified model bytes but did not independently bind all current rendered files and every method's runtime/source inventory; R1 should establish applicability and record the result. Blocked methods are not failed reloads or successful runs. |
| SC-03 | not met | Shared quality, throughput and resource results exist for four SelfCap runs. Motion/temporal interpretation remains incomplete beyond sampled reports; Basketball has no measured reconstruction results. R2 can finish the supported-profile motion assessment without fabricating a two-scene ranking. |
| SC-04 | not met | The comparison presently recommends further inspection, and the main entry guide has stale statuses. R2/R3 can produce a practical qualified recommendation from existing measurements while preserving Basketball and unavailable-method limitations. |
| SC-05 | unverified | Model/v10 hashes and training charge totals reconcile, with no budget overruns. Full retained input/output/source applicability and a current reproducible decision package remain to be recorded and committed. No applicable budget authorizes another timing solve. |

**Next stage may proceed without new user input only for R1–R3 and documenting
R4's boundary.** Main objective attainment is not established. No permission or
sandbox denial occurred during this review, no background work remains, and the
parent owns assessment/status updates and local commits.
