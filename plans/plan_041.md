# Plan 041 — Bind S1 first results to the reservation clock before advancement

Iteration 11 PLAN, 2026-09-20. Implement **R11-1**, the trusted first-result
clock and publication/advancement portion of R9-3. This is an S1-2/S1-3 CPU
prerequisite milestone. It preserves S1-1/S1-4 and does not complete the whole
recovery implementation, live admission, or the objective.

Authority: [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md),
[review-011](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-011.md),
[assessment-023-review](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-023-review.json),
and the explicitly resumed continuous-improvement-loop skill. Plans 031–040
and their unclosed requirements remain immutable. Follow AGENTS.md, never read
`prompts`, use one direct implementation agent with no nested delegation, and
leave status transitions, staging and commits to main.

## Allocation and actual capture limits

Finalize a **new 2,400 wall-second IMPLEMENT allocation**, starting with recorded
UTC and monotonic timestamps before inspection. Execution/refinement cutoff is
**2,160 seconds**; the last **240 seconds** are reserved for evidence/handoff.
Allow at most **three focused invocations of 120 seconds each** and **two full
aggregates of 300 seconds each**, within the same wall allocation. Main records
standing-approval authority and compares unchanged overall/method ceilings
before dispatch. No historical time or attempt allocation is reset or reused.

This intentionally narrows Review's proposed 180/360-second invocation caps:
`s1_validation_capture.capture` permits only 120 diagnostic / 300 aggregate
seconds, and `s1_validation_contract.validate_execution` permits at most 300.
Keep both source files and all capture/receipt contracts unchanged. The last
complete aggregate took 182.62408705499547 seconds; keep new matrices cheap
enough to fit the supported 300-second cap. A timeout is incomplete validation,
not authority to enlarge caps or bypass capture. Do not silently request the
review's unsupported 180/360 values.

Before every launch record elapsed time, remaining invocations and remaining
execution time. The **entire requested timeout must fit before 2,160**. Retain
space for one full 300-second final aggregate before optional refinement: a
120-second diagnostic preceding that aggregate requires at least 420 seconds
of execution time remaining. A second aggregate needs a recorded source change
or concrete concern invalidating the first; never repeat an unchanged pass
routinely. Every launch, including failed discovery, consumes an invocation.
Permission retry time counts, and a newly launched test process consumes a new
invocation. Apply AGENTS.md's one safe outside-sandbox retry and stop/report
rules. Time remaining does not authorize extra attempts.

Suites and child processes run serially; native/helper pools and OMP, OpenBLAS,
MKL and NUMEXPR thread variables are one. At most **eight CPU workers including
owned processes and native/helper threads**. Retain the six direct-script
regression children inside their collected parent invocation, each at most
10 seconds execution + 2 seconds cleanup, 72 seconds total, no recursion or
standalone probes. Parent and plan deadlines are tighter limits. Those children
must retain exact argv, raw logs and actual completion evidence.

Allocate **zero** GPU/device probes or attempts, model evaluations, production
controller calls including dry runs, production ledger API calls/mutations,
production job directories, setup/download/smoke jobs or scientific reruns.
Only disposable fixture controller/ledger calls inside collected CPU tests may
execute those APIs. Standard-library read-only file/hash/JSON/AST and git-diff
inspection are evidence work. No benchmark/scientific thresholds, algorithms,
native detections, semantic assignments, preprocessing, weights, SAM or tracking
changes are authorized.

## Evidence and exact implementation scope

Review reconciled 74 current source/config/test records, all 38 frozen records
and the original 447-event ledger. Its current-source saved aggregate has 162
methods / 310 typed callbacks, all passing. These historical counts are not
future acceptance constants. Receipt milestone `44686a2` and numerical/script
milestone `91b13b5` remain supported. Plan 040 used three focused invocations and
one aggregate; its allocation is complete. Preserve its failed/partial logs.

Change only these implementation paths:

- New `scripts/vipe_benchmark/s1_clock.py`: small model-free immutable clock
  value, serialized contract, strict numeric validation and phase/deadline checks.
- `scripts/vipe_benchmark/s1_recovery.py`: active/historical authority resolution,
  acceptance context and narrow reconciliation plumbing.
- `scripts/vipe_benchmark/s1_evidence.py`: explicit context in first/failure/result
  evidence, verified publication/reuse and clock checks.
- `scripts/vipe_benchmark/supervisor.py`: derive/transport context from the
  captured reservation and pass existing config/context to reconciliation.
- `scripts/vipe_benchmark/s1_cpu_helper.py`: derive trusted helper context from
  its existing reservation/command arguments and pass it explicitly.
- `scripts/basketball_vipe_worker.py`: bootstrap before stage/model setup, checked
  CLI/request/local binding, and context-aware early failure handling.
- `scripts/vipe_benchmark/stages.py`: narrow optional context signature plumbing
  in `run`/`segment`, real first publication barrier and pre-input deadline gate.
- `tests/test_vipe_benchmark_s1_recovery.py`: collected `ReservationClockTests`,
  literal typed declarations, truthful existing fixtures and real-guard coverage.
- `tests/test_vipe_benchmark_supervisor.py`: only if necessary for a captured
  environment/helper transport assertion using existing disposable fixtures.
- `scripts/vipe_benchmark/s1_validation_runner.py`: change only the existing
  focused selector from `NumericalEnvelopeTests` to `ReservationClockTests`.
  Aggregate selection/order/collection/receipts remain unchanged.
- New immutable iteration-11 evidence under the run directory; main separately
  owns current `status.md` and actual status snapshots.

No `execution.py` change is needed: S1 acceptance already uses the helper with
captured reservation/command. No generic ledger/accounting, capture/receipt,
configuration, other test-suite or scientific/backend source edits are allowed.
Unrelated failures are handoff findings rather than scope expansion.

## 1. One explicit clock contract and its authority

Use a frozen clock value with a serialized `reservation_clock` mapping containing
`schema='plan041-s1-reservation-clock/v1'`, `job_id`, strict request file record,
reservation `{sequence,event_sha256}`, `boot_id`, `monotonic_start`,
`effective_seconds`, `cleanup_reserve_seconds`, `total_deadline`, and
`work_deadline`. Derive it from the **actual captured admitted reserve event**:
T = reservation.seconds, C = min(30,T/4), D = start+T, W = D-C. Never infer T
from nominal job configuration or a default 3,600. Require 0 < T <= 3600.
Keep this runtime mapping outside canonical request/config bytes and argv.

Exact `int`/`float` numeric types only, excluding bool; finite nonnegative start
and observations; positive finite T; exact nonnegative integer sequence; strict
hash/request records; nonempty boot identifier matching the authoritative event.
Reject nonfinite/overflowing arithmetic and unrepresentable windows (W must be
strictly greater than start and less than D). Validate all derived values with
the same arithmetic and exact equality, no tolerance/clipping/coercion. Clock
equality is typed, so bool or numeric string cannot equal a trusted scalar.

Separate evidence-time validation from permission to do more live work:

- Stored pass elapsed must be finite, nonnegative and strictly < W-start.
  Failure/not-reached elapsed may be <= T, including exactly D, never above D.
- Live checks read this boot identity and monotonic clock, require the recorded
  boot, observation >= start and **observation < W** before work advancement.
  An observation at W fails. Compute actual elapsed without clipping/backdating.
- Recorded/historical checking compares context with its authoritative recorded
  reservation and recorded elapsed bounds. It never consults today's boot or
  compares old monotonic values to today's clock. It cannot authorize live work.
  Cleanup may inspect/preserve a previously valid pass using this evidence-only
  mode after W; it cannot reuse that mode for worker advancement.

Authority and transport are concrete:

1. Supervisor uses the object returned by `ledger.reserve`, after existing
   canonical admission. Derive the context from that captured event, retain the
   existing effective deadlines, and serialize it in **`VIPE_S1_RESERVATION_CLOCK`**
   for the worker. Bare `VIPE_RESERVATION_START` is no S1 authority; non-S1 behavior
   need not change. Do not trust a second independent allocation supplied by env.
2. Worker bootstrap derives local root from its canonical request path
   `<local>/requests/<JOB>.json`, reads the actual active event through existing
   ledger/active-binding code, and validates admission/canonical request and
   captured event. Compare transported mapping with context reconstructed from
   that real event. Check CLI operation=component, request/config/output paths
   and worker/interpreter against the canonical command: actual interpreter
   resolves to the frozen runtime interpreter, actual script resolves to the
   current worker, all prescribed arguments/paths match. No env-supplied local
   root or output may choose an unrelated authority. Factor existing
   `active_binding` internals as needed to return the checked reservation with
   the document without changing existing callers' contract.
3. Bootstrap runs inside the worker's failure-handling scope, before importing
   stages/model setup. Pass the trusted value explicitly to `stages.run`,
   `segment` and early/row failure handling. Direct S1 `segment` callers must
   supply a trusted context; no missing-context fallback. Non-S1 callers retain
   their prior signatures/behavior via an optional keyword.
4. Prelaunch/accept/reconcile helper operations already carry the actual captured
   reservation. Resolve it against the active ledger and canonical command,
   derive the same context, and pass it to acceptance/reconciliation. Add the
   existing config to reconcile arguments if necessary. No helper consults the
   controller's start environment. New clock work does not redesign helper
   process startup, pipe transport, resource sampling or finalization.
5. Historical `resolved_result` uses the unique recorded reserve already bound
   to its registration/finish/event snapshot. Reconstruct context from that
   event and validate first and acceptance clock fields against it. Do not read
   a new active reservation or demand the old boot still be live.

The immutable typed value represents an internally checked reservation; its
type or JSON hash alone is not external authority. Public acceptance and worker
bootstrap must perform the actual active/history resolution above. No test-only
fallback or caller-created mapping may bypass those production entrypoints.

## 2. First/failure evidence and barriers

Retain first envelope schema `plan032-s1-first-result/v1` and add required
`reservation_clock` for this recovery. Old records missing it fail this current
S1 contract; do not migrate/rewrite historical frozen failures. Pass explicit
context to `first_record`, `verify_first`, `reconcile_first`, `preserve_failure`
and `validate_result`. `elapsed(request)` must no longer obtain S1 timing from
environment. Keep recorded elapsed named as construction time; it is **not**
publication-completion time.

For a new passed first result:

1. Construct the envelope using actual context-relative elapsed. Run the real
   runtime, row, native array, semantic, numerical and enclosing file checks.
2. Observe the live clock **after** qualification and reject at/after W before
   writing a pass. Existing stage qualification before `first_record` also has
   a live post-qualification check so no later expensive phase starts after W.
3. Publish using existing immutable `write_json`, hash/read back exact bytes,
   reverify the persisted envelope through the real guards, then observe live
   time again. If write, hash, read-back or requalification crosses W, retain
   the file/raw evidence, raise the deadline error and prevent advancement.
4. Immediately before the next input load, observe live time once more. Gate
   each subsequent loop input so a delayed print/loop transition cannot start
   new work at/after W. Keep the first file record from completed publication
   for comparison; no repeated whole-row verification on every later frame.

Identical pass reuse must verify the existing persisted pass, compare matching
context and content (construction elapsed retains the existing value), hash/read
back, and pass the same live completion check. Failed/not-reached/stale or
conflicting evidence cannot become a pass. Reuse may not refresh start, elapsed,
T or reservation. New failure handling may preserve an earlier verified pass
using evidence-only checks; it must never overwrite it or its raw records.
Record the live completion observation in test/handoff evidence separately from
the pre-write envelope timestamp. No new finalization acknowledgment protocol
or self-referential completion timestamp is required by this milestone.

Missing first evidence during reconciliation uses the trusted supervisor/helper
context and actual current elapsed to publish a minimal `not_reached` envelope,
with request/amendment/authorization and original error/phase. Verify the newly
published envelope before returning a verified file record. Verified existing
worker failed/not-reached records retain **exact original bytes, time, error,
phase and raw hashes**, even if reconciliation occurs later. Failure evidence
never permits progression.

If context is unavailable/invalid or current failure observation exceeds D,
preserve primary error and available raw data as **unqualified evidence**. Use
explicit `clock_status='unverified'` with the clock-validation error and actual
observation; actual relative elapsed is retained when derivable from a trusted
start, otherwise null is allowed only on this explicitly unqualified record.
Never pass that record through a verified-first summary. Preserve invalid clock
observations truthfully in JSON-safe diagnostic form rather than emitting NaN.
Worker bootstrap failures therefore still produce `failure.json`/raw failure
evidence without falsely claiming a verified reservation clock. The existing
primary exception must survive best-effort persistence failures.

Extend `accept_result` with a required trusted captured reservation (resolved
against active binding within the acceptance path), require `validate_result`
to receive its clock, and persist `reservation_clock` in acceptance. Require
matching first/result/request/acceptance context at real acceptance and historical
resolution. Historical resolution also checks stored pass elapsed bounds before
its existing first<=finish<=T inequality; keep numerical/allocator guards intact.
Do not equate first elapsed with native inference duration: loading and
qualification lie outside native wall time. Full first/native/result/receipt/
finish/acknowledgment ordering remains R9-5 work. Terminal receipt schema and
capture/aggregate/wrapper contracts remain unchanged.

Preserve `produced_row` as structural evidence. A serialized row remains produced
if a clock/semantic/numerical qualification later fails; do not erase its identity
or promote it to qualified. Keep Plan 040 numerical rules and direct-script cases.

## 3. Collected validation that reaches real guards

Use one literal typed `ReservationClockTests` class in the recovery suite for
focused selection. Reuse bounded positive fixtures within each test method;
do not create a full controller or scan 510 image/NPZ rows per clock mutation.
Cheap pure clock matrices can use a context taken from one actually admitted
disposable reservation. At least full T=3600 and reduced T=90 contexts originate
from real fixture `Ledger.reserve`, with isolated histories for each.

Upgrade existing controller, terminal/numerical and real segment fixtures to
carry explicit trusted contexts. Keep all prior substantive assertions; old
start-env-only fixtures must not be grandfathered. Existing controller synthesis
of 510 rows remains controller evidence, never worker-execution evidence.

Required groups, declared literally with canonical module lookup:

| Boundary | Required cases and assertion |
| --- | --- |
| Context construction/transport | Real full/reduced reserve positives; missing/null/bool/string/nonfinite/negative scalar fields, nonpositive/oversized T, invalid sequence/hash/request/boot, overflow/unrepresentable derived windows; wrong start/T/C/W/D/reservation sequence/hash/job/request; coherently rederived forged values still fail equality with actual authority. Patch clock/boot observations explicitly, never active binding into a pass. |
| Phase bounds | Pass immediately before/at/after W; failure at D and after D; zero elapsed; negative/nonfinite observation; live wrong boot rejects, recorded old-boot match passes without consulting current boot/time; recorded mismatching boot rejects. Use `nextafter` or exact binary values, no real sleeps. |
| Bootstrap/helper routing | Valid worker transport is accepted before setup; missing/forged context and wrong CLI/root/output/request/command fail before backend/setup calls; valid context survives a deliberate pre-model exception. Acceptance/reconciliation helpers use captured reservation with controller `VIPE_RESERVATION_START` absent or misleading. |
| Failure reconciliation | Missing file creates finite verified supervisor-relative not_reached at valid time; existing verified failed/not_reached time/error/phase/raw bytes stay unchanged; unavailable/late context is retained unqualified, never verified/null-clock; later failure preserves earlier passed first bytes and raw hashes. |
| Real segment barrier | Real serialized positive first row with fake backend/device/runtime capture and real RGB/row/runtime/first guards. Advance a controlled clock across W during qualification, immutable write, read-back/reverification and identical-pass reuse. Every case prevents frame 62 load and second adapter call. A before-W positive is durably visible and reverified before frame 62; stop deliberately at that second input or later-row failure and assert preserved first/raw hashes. Include crossing after publication but before the next input gate. |
| Acceptance/history | One genuine disposable successful controller positive reaches real accept_result and resolved_result. Coherently rehash mutated first->result->acceptance->terminal/finish records for wrong start, boot, effective T/deadlines and reserve identity, so each reaches the clock guard rather than only failing stale file hashes. Update all legitimate outer records/references while keeping the authoritative reservation/event snapshot unchanged. |

Wrap real qualifier/writer/reader functions to advance a fake clock **after their
real operation**, rather than patching them to return success. Assert boundary
and phase-specific failures, actual loader/adapter counts, persisted records and
target clock guard error text. A tested positive must pass the same guard before
mutation. To keep aggregate cost bounded, use local envelope/context validators
for exhaustive cheap scalar combinations and a small representative set through
the full controller/resolver. Do not drop any required boundary or retain a
passing claim when its test timed out.

Only external model/device/runtime-capture and clock observations may be faked;
no patch of real row/runtime/first/result acceptance to force a pass. Worker
entrypoint may be invoked in-process with fixture argv/env and a deliberately
stopped stage boundary; it must execute real bootstrap. Short real-segment tests
prove the first barrier only. Full successful 510-row order and 340/170 split,
remaining native/runtime/zero-detection/oversized-box matrices, and broad
lifecycle/race/replay coverage remain separate milestones.

## 4. Aggregate, immutable lineage and handoff

Use existing capture for diagnostic directories `s1-recovery-diagnostic-011-001`
through `003` and aggregate directories `s1-recovery-aggregate-011-001` through
`002`, never overwrite a launched attempt. Focused selection is the new clock
class. Full aggregate keeps `.local/envs/stg-colmap/bin/python -B -`, repo cwd,
diagnostic unset and the exact existing four-line stdin with final newline:

```python
import runpy
import sys
sys.path.insert(0, "scripts")
runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})
```

Retain suite order `s1_semantics`, `s1_recovery`, `backends`, `contracts`,
`component_recovery`, `execution`, `budgets`, `supervisor`, `review_annotations`.
Derive final source membership and ordered methods/typed callbacks from AST;
the new clock module enters existing source glob automatically. No hardcoded
historical totals, omitted suites, skipped declarations or relaxed receipt checks.
Bind complete unchanged pre/post source snapshots, exact launcher/interpreter/
stdin/environment, runner/capture snapshots, closed raw logs, elapsed timestamps,
actual wait/returncode and independent tool/session completion. A source edit
after a pass invalidates it. Focused passes alone do not complete this plan.

Save a new read-only independent audit script and its output; reconcile raw
receipt and outer capture, current source/typed membership, child outcomes,
correction/frozen/ledger bindings independently of merely invoking the production
validator. Preserve acyclic source/logs->inner->outer->wrapper bindings. Record
`git diff --check` scope, stdout/stderr and exit code truthfully. Main records
staged checks separately. Prior full staged check exited 2 only for four raw
failed/partial log whitespace findings; preserve their bytes and disposition.

Main already preserved REVIEW bytes as `s1-recovery-status-before-plan-011.md`
before PLAN. Before dispatch, save PLAN as
`s1-recovery-status-before-implement-011.md`, set IMPLEMENT, and freeze it through
this implementation. Supply its exact hash/bytes to the implementation agent.
Create next-unused **correction-009** from correction-008, preserving its original
baseline, 38 frozen records, original ledger snapshot, bookkeeping baseline and
complete transition prefix. Bind Plan 041/review-011 and append actual changes:

1. Preserve `s1-recovery-bookkeeping-transition-post-010.json` unchanged. Its
   schema is already canonical, but its `new_snapshot` points to the formerly
   current `status.md`, now changed. Create a new canonical
   `plan034-s1-bookkeeping-transition/v1` copy with identical old/new status
   hashes/bytes, durable old snapshot `s1-recovery-status-implement-010.md` and
   durable new snapshot `s1-recovery-status-before-plan-011.md`; add a strict
   reference to the preserved original transition. Append this newly resolvable
   transition, not the old dangling current-path snapshot.
2. Append actual REVIEW->PLAN from `...before-plan-011.md` to
   `...before-implement-011.md` and PLAN->frozen IMPLEMENT in `status.md`.
   Include each additional main-created status change only with actual saved
   before/after bytes. Never invent snapshots or amend old correction/validation.

Original ledger remains 447 events / 332,437 bytes / SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`, chain head
`00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`, no active
job and no recovery event. Historical GPU consumption remains 30 attempts /
4,374.044265462899 seconds / zero reserved; original finishes 250/255 and event
256 remain untouched. Inspect bytes read-only; no production ledger APIs.

Create next-unused `s1-recovery-validation-010.json`, `s1-recovery-audit-010.json`,
`s1-recovery-independent-audit-010.py`, `s1-recovery-implementation-review-009.md`,
`s1-recovery-preparation-010.md`, `s1-recovery-timing-011.json`,
`s1-recovery-ledger-audit-011.json`, `s1-recovery-bookkeeping-audit-011.json`,
`s1-recovery-process-observation-011.json` and `assessment-025-implement.json`.
Check vacancy before creation and choose the next unused suffix if necessary.
Preserve every failed/partial attempt and exact resource consumption. Main
inspects, stages explicit task paths, checks staged diff and commits the validated
milestone under AGENTS.md, then continues fresh REVIEW. Commit is a checkpoint.

## Acceptance and remaining objective

Plan acceptance requires all three: (A) real reservation authority/transport and
strict live/historical clock coverage, (B) first publication/reuse/pre-input
barriers and verified failure preservation through real guards, (C) fresh complete
passing aggregate plus independent current-source/preservation audit and bounded
truthful handoff. Keep separate flags for `reservation_clock_milestone_complete`,
`plan_acceptance_complete`, `implementation_acceptance_complete`,
`ready_for_live_admission`, and `objective_complete`. The last three remain false.

S1-1 remains supported if frozen semantics and the new aggregate hold; S1-4
requires byte-preserved historical evidence plus actual canonical status lineage.
S1-2/S1-3 remain not met: this milestone supplies clock prerequisites only. Open
work includes R9-2 helper transport/sample freshness, R9-4 durable progress,
R9-5 structured errors/cleanup/final charge/acknowledgment and remaining R9-3
timing consistency, full worker/native/lifecycle/race/replay matrices, current
production authorization/registration, and the eventual single live recovery.
Historical P31-5 and unavailable old timing/status evidence remain unclosed.

The sole later calibration allocation remains one attempt at
`min(3600,93600-gpu_elapsed_seconds-gpu_reserved_seconds)>0`, inclusive cleanup
`min(30,effective_seconds/4)`, one exclusive GPU group, 22 GiB device memory,
eight CPU workers, 150 GiB artifacts, 60 GiB downloads and existing 57,600-second
preparation/setup ceilings. This plan spends none of it. Reconstruction requires
separate later authorization. Stop on user interruption, exhausted applicable
limits, unresolved permissions or git failure as prescribed; retain incomplete
evidence and report remaining work rather than extending this allocation.
