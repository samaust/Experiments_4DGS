# Plan 040 — Validate S1 row/result numerical envelopes and script entrypoints

Iteration 10 PLAN, 2026-09-20. This completes the local numerical-envelope
portion of R9-6 (**R10-1**) and the six-suite direct-script compatibility repair
(**R10-2**). It advances S1-2/S1-3 prerequisites. It does not complete wider
implementation acceptance, live admission, or the saved recovery objective.

Authority: [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md),
[review-010](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-010.md),
[assessment-020-review](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-020-review.json),
and the explicitly resumed continuous-improvement-loop skill. Plans 031–039
remain immutable and their unclosed requirements carry forward. Follow AGENTS.md;
never read `prompts`. Main owns status and local commits. One fresh stage agent
implements this plan directly, with no nested delegation or git writes.

## Allocation and execution boundaries

Finalize a **new plan-specific 1,800 wall-second IMPLEMENT allocation**, whose
UTC/monotonic start is captured in the first implementation action, before
inspection. Reserve the final **180 seconds for evidence and handoff**; stop
execution/refinement at elapsed **1,620 seconds**. Historical consumed time and
attempts remain consumed. Main records standing-approval authority and compares
this allocation with all applicable remaining ceilings before dispatch.

Within that same wall allocation, permit at most **three focused invocations,
120 seconds each**, and **two complete aggregates, 300 seconds each**. The full
timeout of a proposed invocation must fit before the execution cutoff. Reserve
space for one complete final aggregate before optional refinement. The second
aggregate needs a recorded source change or concrete concern invalidating the
first, saved before launching; a passing unchanged run is not repeated routinely.
Every launch consumes an invocation, including discovery failures. A permission
retry consumes wall time and another invocation if a new test process launches.
Apply the one safe outside-sandbox retry and subsequent stop/report rules in
AGENTS.md; do not replace a denied operation with another access route.

All suites and script children run serially; native/helper pools and
`OMP_NUM_THREADS`, `OPENBLAS_NUM_THREADS`, `MKL_NUM_THREADS`, `NUMEXPR_NUM_THREADS`
are one. Maximum **eight CPU workers including owned processes/native threads**.
The selected script regressions are nested work inside a prescribed focused or
aggregate invocation, not extra top-level diagnostic allocations. Each test
invocation executes that regression at most once: six children, each at most
**10 seconds execution plus 2 seconds termination/reap**, sequentially, at most
**72 seconds total**. Parent invocation and plan deadlines remain the tighter
limits. These children cannot launch the regression or a whole suite again.
Retain child argv, completion/timeout, durations and raw output in the parent
captured evidence. No standalone script probes outside the three/two caps.

Zero GPU attempts/device probes, model evaluations, live controller calls
(including dry runs), production ledger API calls/mutations, production job
directories, setup/download/smoke jobs or scientific reruns are allocated.
Disposable fixture controller/ledger calls inside collected CPU tests remain
permitted. Read-only standard-library file/hash/JSON/AST and git-diff inspection
are evidence work, not authority for extra test invocations. Preserve algorithms,
native detections, semantic rules, thresholds, weights, precision, preprocessing,
SAM refinement/tracking, pins, annotations and existing substantive assertions.

## Starting evidence and exact source scope

Review-010 matched 74 source/config/test records, 38 frozen records and the exact
447-event ledger to saved evidence. Committed Plan 039 (`44686a2`) has a final
157-method/213-callback aggregate at 92.21503551599744 seconds. These are prior
observations, never new hardcoded counts or a substitute for this plan's run.
Plan 039's two aggregate attempts are consumed.

Allowed implementation files are precisely:

- `scripts/vipe_benchmark/s1_evidence.py`: small shared local numerical guards,
  called by row qualification and terminal result validation.
- `scripts/vipe_benchmark/s1_recovery.py`: only the local numerical helper call
  in `resolved_result`, using a local import to avoid its existing import cycle.
- `tests/test_vipe_benchmark_s1_recovery.py`: truthful row/result fixture fields,
  collected numerical/integration/script regressions and literal declarations.
- `tests/test_vipe_benchmark_s1_semantics.py`,
  `tests/test_vipe_benchmark_backends.py`,
  `tests/test_vipe_benchmark_contracts.py`,
  `tests/test_vipe_benchmark_component_recovery.py`, and
  `tests/test_vipe_benchmark_supervisor.py`: canonical case-table lookup only.
- `scripts/vipe_benchmark/s1_validation_runner.py`: if needed, extend only the
  diagnostic class selector to include the new numerical/script test classes.
  The aggregate path, collection order, launcher, receipt and CPU guards stay
  unchanged. Placing focused tests in its existing selected class instead is
  also permitted and avoids this edit.
- New immutable iteration-10 evidence files under
  `docs/continuous-improvement/plan031-s1-recovery-20260919/`; main separately
  owns current `status.md` and its pre-dispatch snapshots.

No changes to stages, supervisor, ledger, scientific/configuration source,
receipt contract, capture module, other tests, or existing artifacts. Fixture
and child-capture support belongs inside the named recovery test file. New
read-only audit scripts belong in the run directory. A newly exposed unrelated
failure is a saved handoff finding; it does not expand this package.

## 1. Local numerical contracts and actual arithmetic

The current `stages.segment` starts `native_seconds = 0.`, chooses calibration
`size = 1`, computes each elapsed value once as a monotonic subtraction, adds it
to native_seconds, then serializes that same value on its singleton row. It
finally serializes native_seconds and the two allocator integer peaks. Retain
that emission format and all field names.

For each qualified row require both `native_group_wall_seconds` and `group_size`.
Duration accepts exact Python `int` or `float` only (never bool), finite and
nonnegative. Zero is valid. Reject missing, null, strings, nonfinite values,
negatives and numerically coercible foreign types; conversion/overflow cannot
escape as acceptance. Group size is exact `int` equal to **1**, not bool or
float `1.0`. Make errors identify the field/contract.

Apply this row guard through `qualify_row`, including first-result verification.
Keep `produced_row` structural: a correctly serialized row with invalid numerical
qualification still counts as produced. `reconcile_rows` must retain that
identity in `produced_identities` and exclude it from `qualified_identities`,
recording the qualification error. No new file discovery, progress protocol or
clock authority is introduced.

A shared result numerical helper accepts only the bounded in-memory calibration
rows (a list of exactly the configured calibration identity count, currently
510). It validates every row's numerical fields, required result
`native_wall_seconds` with the duration rule above, and required
`peak_allocated_bytes`/`peak_reserved_bytes` as exact nonnegative `int`.
Require allocated <= reserved and each <=
`config['gpu_peak_device_gib_limit'] * 2**30` (currently 22 GiB). Equality and
zero pass. Do not coerce floats, strings or booleans. Configuration remains the
existing trusted loaded configuration; no new memory allowance. This is allocator
consistency only; sampled total-device memory and its freshness remain separate.

Use **`math.fsum` of the validated singleton group durations** as the reference
sum `S`, and let `n` be their bounded count. Reject overflow/nonfinite reference
or computed tolerance. Require exact zero total when S is zero. Otherwise use
the explicit absolute rounding allowance **`T = (n + 1) * math.ulp(S)`**, and
require `abs(native_wall_seconds - S) <= T`, with no other absolute/relative
floor. This accounts conservatively for the n serial binary64 additions in
`native_seconds += elapsed` versus fsum, plus its final rounding. All terms are
nonnegative, so intermediate sums do not exceed the final sum except rounding;
JSON round trips preserve binary64 input values and add no decimal-truncation
allowance. At S=3600 and n=510, T is about 2.324e-10 seconds. This is a numerical
representation bound, not a scientific or timing budget threshold. Integer
inputs must be finite/representable for this same binary64 arithmetic; reject
overflow explicitly. Include finite-large values whose accumulation overflows.

Test the stage-style sequential accumulator, exact reference, values safely
inside/on/outside T, both mismatch signs where nonnegative, and the all-zero
special case. For boundary fixtures choose a binary-exact S away from an exponent
boundary and use `math.nextafter`/ULPs so rounding cannot collapse outside to
inside. Compute expected boundaries independently in tests. Literal declarations
use finite primitive case labels (for example `kind='nan'`); create NaN/inf only
inside the case body because the receipt contract prohibits nonfinite parameters.

Call the helper from the real `validate_result` path without weakening existing
membership/order, runtime, first-result/configuration or semantic checks. Place
cheap local numerical rejection before expensive repeated semantic work where
practical. Also call it from `resolved_result` after loading/binding result and
acceptance, before returning success. That resolver check is a bounded in-memory
pass, not a recursive filesystem scan or a rerun of full row semantics. Keep
all existing cleanup, acceptance, referenced-byte and timing guards intact.
Neither helper compares native timing with charged/effective reservation time;
trusted clocks and that comparison belong to later R9-3/R9-5 work.

## 2. Truthful positives and target-reaching mutation coverage

Upgrade `synthetic_row` and the controller result fixture with the real emitted
fields. Baseline rows use explicit finite durations and group_size=1; result
total uses the same ordered accumulation as stage emission and integer peaks
consistent with the configured ceiling. Keep fixture provenance synthetic and
all real semantic/runtime/serialization checks. Do not patch qualification,
numerical validation or result acceptance to claim a positive.

Organize small focused fixtures so table rows do not each launch a controller
or rescan 510 heavyweight image/NPZ rows. A shared local helper matrix may use
in-memory rows after its positive envelope passes. Real row tests start from
a serialized positive accepted by `produced_row` and `qualify_row`; full-result
integration starts from a fixture accepted by actual `validate_result` and
`resolved_result`. Reuse immutable positive artifacts only within their own
disposable fixture, deep-copy mutation containers, and restore byte/hash state
between cases. Every mutation demonstrates the unmutated positive passes first.

Required literal case groups, with focused error assertions:

| Surface | Required cases |
| --- | --- |
| Row duration and result total | Missing, None, string, bool, NaN, +/-inf, negative; valid integer/float zero and nonzero; unrepresentable huge integer; overflowing finite accumulation for result |
| group_size | Missing, None, string, bool, fractional float, float 1.0, zero, negative, 2; exact int 1 passes |
| Each allocator field | Missing, None, string, bool, nonfinite float, negative int, fractional float and integral float; exact integer zero/nonzero pass |
| Allocator relationships | allocated > reserved, reserved cap+1 with allocated valid, allocated cap+1 with reserved coherently cap+1; exact cap passes; smaller copied config cap verifies use of configuration rather than hardcoded 22 GiB |
| Group sum | All-zero/zero total pass; all-zero/positive total fails; nonzero ordered stage accumulation passes; within/on/outside ULP allowance; wrong total and changed non-first row duration fail |
| Produced versus qualified | Serialize an otherwise valid row with bad duration or wrong group_size; real produced guard accepts, qualified guard rejects, reconciliation reports produced lower bound 1 and qualified 0 with its numerical error |
| Full integration | Positive real terminal guard and recovered-result resolver pass; representative total, peak and non-first-row mutations reach and fail the local guard through both entrypoints |

For resolver mutations, update legitimate enclosing result/acceptance/terminal
receipt file records and referenced-record lists in a disposable graph as needed
to reach the inner guard. Pass an internally coherent mutated finish object and
existing fixture events; do not rewrite the production ledger or fabricate a
passing validator. A stale outer hash rejection alone does not cover numeric
resolution. Preserve all existing membership/runtime/assertion cases and add
no live events. Keep zero-detection/oversized-box scientific matrices as later
work; numerical zero observations here do not claim that coverage.

## 3. Canonical lookup and bounded real script regression

Replace `SUBTEST_CASES[self.id()]` in all six affected suites with a canonical
lookup independent of `__main__`, for example a module filename stem plus the
test class name and `_testMethodName`. Keep literal keys, declared parameter
types/order and actual `self.subTest(**case)` iteration unchanged. No rewriting
class `__module__`, renaming tables to `__main__`, fallback to an empty case list,
or weakening the static parser/callback checks.

Add one collected literal regression table in the recovery suite selecting these
existing methods by real direct entrypoint:

| Script suite | Explicit unittest selector |
| --- | --- |
| s1_semantics | `S1SemanticsTests.test_contract_rejects_missing_or_tampered_assignment` |
| s1_recovery | `ReceiptContractTests.test_typed_primitive_callbacks` |
| backends | `AssetAndDetectorTests.test_phrase_ambiguity_and_capacity_fail_before_casting` |
| contracts | `AccessTests.test_heldout_final_window_wrong_branch_and_pair_rejected` |
| component_recovery | `ComponentRecoveryTests.test_scope_validation_and_cumulative_cap_are_not_relaxed` |
| supervisor | `HelperIntegrationTests.test_cleanup_failures` |

Each child is `[sys.executable, '-B', absolute_test_script, selector, '-v']`
with repo cwd and the one-thread/CPU environment. These selected methods use
CPU/disposable/fake inputs; none calls real GPU probing or starts real supervisor
workers. They run the retained `unittest.main()` path under `__main__`. Derive
expected nonempty method/declaration membership from static source declarations,
not callbacks observed during this run. Assert actual successful completion and
execution of the requested single method; retain raw logs. Counts for parent
aggregate callbacks derive from the new literal table. Do not infer child
callback counts from `OK` text or hardcode the historical 213.

Use the caps above, with child kill/wait cleanup on timeout and finally cleanup
on parent interruption. No recursion: explicit selections never include the new
entrypoint regression, no whole-file runs, and no in-child discovery launches.
Complete source and declaration edits before the final aggregate.

## 4. Validation and independent evidence

Use the existing capture module for both focused diagnostics and full aggregates,
retaining immutable `s1-cpu-aggregate/v2` inner, `s1-cpu-execution/v1` outer and
`plan031-s1-recovery-validation/v2` wrapper evidence. New attempt directories are
`s1-recovery-diagnostic-010-001` etc. and `s1-recovery-aggregate-010-001` etc.;
never overwrite an attempted directory. Diagnostic source selectors and all
child subprocesses are recorded. They cannot qualify as the final aggregate.

The full aggregate keeps `.local/envs/stg-colmap/bin/python -B -` with the exact
existing four-line stdin bytes (one final newline), repo cwd, diagnostic mode
unset and CPU/thread environment:

```python
import runpy
import sys
sys.path.insert(0, "scripts")
runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})
```

Serial suite order stays `s1_semantics`, `s1_recovery`, `backends`, `contracts`,
`component_recovery`, `execution`, `budgets`, `supervisor`, `review_annotations`.
No suite removal, skipped cases or relaxed receipt guard. Compare fresh static
collection/declarations to every executed method and typed callback in order;
derive new counts from final source. Final validation must bind current source
membership, both unchanged pre/post snapshots, exact argv/interpreter/stdin/env,
runner/capture snapshots, closed logs, timings, actual wait/returncode and the
new correction. Source edits after a pass invalidate that pass.

Independently reconcile these bindings and callbacks with a read-only audit
script saved in the run directory; invoking the production validator alone is
not the independent audit. Record actual tool/session completion and reconcile
it with outer capture, including child outputs/timeouts. Keep the acyclic graph
source/logs -> inner -> outer -> wrapper; artifacts do not hash themselves or
future documents. Save `git diff --check` command/stdout/stderr/exit status. If
time/attempts expire or a failure remains, retain every failed/partial attempt
and report incomplete acceptance without extending this allocation.

## 5. Preservation, status transitions and handoff

Main first saves PLAN status as `s1-recovery-status-before-implement-010.md`,
sets IMPLEMENT status, and freezes current status during this implementation.
Report that fixed status hash to main before finalizing correction. Keep
correction-007, validation-008 and all existing files unchanged.

Create next-unused `s1-recovery-baseline-correction-008.json` preserving its
predecessor's original baseline, frozen records, ledger snapshot, bookkeeping
baseline and complete transition prefix. Bind Plan 040 and review-010. Append
new `plan034-s1-bookkeeping-transition/v1` transitions for these actual bytes:

1. The post-009 change from `s1-recovery-status-implement-009.md` (897 bytes,
   `32bacd28...`) to `s1-recovery-status-before-plan-010.md` (845 bytes,
   `0fce2a67...`). Preserve the existing noncanonical
   `s1-recovery-bookkeeping-transition-post-009.json` unchanged. Add a new
   canonical transition with the same old/new records and a strict reference to
   that preserved note; do not append the note's wrong schema into the canonical
   transition list.
2. REVIEW to PLAN: the actual `...before-plan-010.md` snapshot to main's
   `...before-implement-010.md` snapshot.
3. PLAN to the frozen IMPLEMENT endpoint in current `status.md`.

Use actual full hashes/byte sizes from each snapshot, reasons and old/new snapshot
records; carry any additional main-created status transition as its own real
snapshot transition. Never invent missing bytes or overwrite old records.
Main owns later status changes, preserving old bytes and appending a successor
transition/correction when a new current binding is needed.

Create next-unused validation-009, audit-009, independent-audit-009.py,
implementation-review-008, preparation-009, timing-010, ledger-audit-010,
process-observation-010, wrapper-check-010 and the next assessment-022-implement
artifacts. Verify unused suffixes at write time; retain failed attempts too.
Preparation is a non-executable handoff and explicitly says live admission is
not ready. Record timing consumption separately from invocation counts and the
scope of each allocation; unused time grants no extra attempts.

Audit all 38 frozen records and the original ledger by read-only bytes. Required
ledger state remains 447 events, 332,437 bytes, SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`, chain head
`00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`, no active
job or recovery event. Preserve 30 historical GPU attempts / 4,374.044265462899
seconds / zero reserved, failed finishes 250/255 and account/skip 256. Preserve
prior failures, scientific aggregates/report, amendment and S0/native sources.
Historical P31-5 and unavailable older timing/status evidence stay explicit.

After validated handoff, main inspects the task-only staged diff and creates
the required local commit; no push/amend/history rewrite. Commit is a checkpoint:
the authorized loop proceeds to fresh REVIEW while the objective is unmet.

## Acceptance and remaining work

This plan is accepted only when: (1) typed local numerical guards apply at row,
terminal and recovered-result boundaries; (2) produced/qualified distinction and
all specified positive/mutation groups pass real guards; (3) all six canonical
lookups and bounded real-script regressions pass; (4) a fresh final exact
nine-suite aggregate passes with independent current-source execution audit;
and (5) immutable correction, preservation and resource handoff is complete.
Report partial milestone completion separately from full plan acceptance.

| Criterion | Plan effect and status required in handoff |
| --- | --- |
| S1-1 | Preserve its met amendment/source/CPU evidence and pass existing semantic assertions. No live semantic-output claim. |
| S1-2 | Advance R10-1/R10-2 admission prerequisites; remains not met overall. No production authorization/registration. |
| S1-3 | Advance result evidence prerequisites; remains not met because no calibration recovery runs here. |
| S1-4 | Reverify immutable scientific bytes/ledger; preserve bookkeeping through canonical append-only transitions. |

Use distinct `aggregate_passed`, `numerical_envelope_milestone_complete`,
`direct_script_compatibility_complete`, `plan_acceptance_complete`,
`implementation_acceptance_complete`, `ready_for_live_admission` and
`objective_complete` values. The final three remain false even if this plan
passes. Retain the previously achieved receipt milestone with its own evidence.

Later work remains R9-2 bounded helper startup/transport/fresh samples; R9-3
trusted reservation clocks/effective allocation; R9-4 durable incremental
progress; R9-5 structured failures, observed cleanup/finalization/charge and
acknowledgment; remaining native/runtime/envelope matrices; actual segment
progression through 510 identities and first-result reuse/later failure;
applicable-boundary/contender/replay/typed-lifecycle coverage. No execution budget
for those repairs is conferred here.

Only a later authorized DO after all CPU gates close may consider the single
`S1-calibration-recovery-001` attempt, with effective seconds
`min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)` positive and
cleanup reserve `min(30, effective_seconds/4)` inside its cap. Preserve charging
for preparation/loading/qualification/publication/cleanup/finalization; a
reservation consumes the attempt even without launch. One exclusive GPU group,
22 GiB memory, eight CPU workers, 150 GiB artifacts, 60 GiB downloads and existing
57,600-second preparation/setup ceilings remain. No setup/download/smoke
allocation is reopened; reconstruction requires separate later authorization.
