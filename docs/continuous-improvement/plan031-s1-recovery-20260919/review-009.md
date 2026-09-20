# Iteration 9 REVIEW — Current defects and a bounded receipt milestone

Fresh review complete. Plan 038's correction and saved aggregate pass are valid
for the current implementation. Live S1 admission remains **not ready**. The next
implementation should close the receipt declaration and metadata gate; it should
not attempt all five inherited packages in one checkpoint.

This reviewer performed the REVIEW directly, without delegation. The earlier
review-008 capability claim is not a technical finding and is not a blocker for
this stage. Read the objective, current and preserved statuses, assessments
013–016, reviews 005–008, Plan 036–038 requirements, relevant earlier plan
requirements, saved validation/audit/preparation, and the current admission,
semantic, evidence, worker, supervisor, runner, ledger and test code. Bound inputs,
source records and fresh read-only reconciliation are in
[assessment-017-review.json](assessment-017-review.json).

No tests, model jobs, GPU/device operations, production controller calls, ledger
APIs or mutations, source edits, git writes or scientific reruns were performed.
Only this review and its assessment are added to the repository. Earlier
uncommitted files and the main agent's concurrent status/resume artifacts are
preserved. Findings below are source inspection conclusions unless explicitly
identified as saved executed evidence.

## What is already supported

Current HEAD is `3085c6b00345a531b00bedd035734e6adc47e636`. All **72** current
source/config/test records match validation-007. Its aggregate-006-002 records
**148 methods, 91 callbacks, zero failures/errors/skips and exit 0**, with
47.81817000600131 seconds between its recorded start/end. The five aggregate
artifact hashes match; static method order agrees with the receipt. The saved
independent audit and recorded external process completion support that pass.
This review did not rerun it. The earlier inspection-inclusive timing limitation
is retained; a passing aggregate is distinct from full implementation acceptance.

The eight contracts callbacks restored by Plan 038 remain in the receipt. Do not
repeat the one-line correction or relabel the previous failed aggregate as passed.

Several old defect descriptions are now obsolete and should not drive repeat
implementation:

| Earlier issue | Current source disposition |
| --- | --- |
| Consumed request could change to reconstruction | `lifecycle` calls `canonical_dispatch` on reserve; `active_binding` compares the captured active reservation and launch command; the accept helper calls it too. The old missing canonical comparison is implemented. The full boundary/race matrix is still missing evidence. |
| Generic CLI list/scalar authorization escaped protected decoding | `basketball_vipe_benchmark.py:168` checks the object and string fields inside the protected parse path; publication errors are attached to the original exception. The old unchecked `.get` report is no longer current. Storage and real CLI tables remain incomplete. |
| Two `{}` partial files counted as two produced rows | `produced_row` now requires admitted identity, parent bindings and real serialized artifacts; `reconcile_rows` deduplicates qualified structural candidates. The old readable-file counter is replaced. Full duplicate/category/partial tables remain incomplete. |
| Missing sample fields treated as zero | `validate_sample` now rejects missing or malformed required fields. Temporal freshness remains missing. |
| Empty worker survivor fallback implied successful cleanup | The supervisor tracks `cleanup_uncertain`, retained helper ownership and errors independently. Complete real helper failure and descendant coverage remains open. |
| Native helper spawn unavailable under required launcher | Saved real spawn and guarded-file cases passed. The current issue is transport/startup boundedness, not missing spawn capability. |

## Current findings

**R9-1 — Admission does not enforce the CPU evidence it claims to require
(F7-2, Plan 036 package 5; S1-2).** At `s1_recovery.py:40–84`, production
`validation_record` never reads callback `parameters`. Any distinct nonempty
passing callback list is sufficient for a parameterized method. Nonparameterized
methods are allowed extra callbacks. `subtests_run`, per-suite counters and
`diff_check.exit_code` lack exact integer type checks; ordinary equality can
accept equivalent floats or booleans. At `s1_validation_runner.py:70–77,149–150`,
only `HELPER_CASES` literals are loaded and Python equality compares them. There
are **18** parameterized methods and only **two** declared methods, covering
12 of the 91 recorded callbacks. AST declaration merging can silently overwrite
duplicate method keys.

More directly, `tests/test_vipe_benchmark_s1_recovery.py:184–194` deliberately
builds a synthetic positive receipt with arbitrary `(synthetic)` subtest IDs,
no parameters, and the command string `synthetic test-only aggregate; NOT
execution evidence`. That fixture passes the real validator in saved aggregate
tests. This is source-bound evidence of the validator's weak contract; no new
tampering probe was run in this review. The receipt guards also ignore argv,
stdin/runner/log records, interpreter, environment, discovery errors,
before/after source equality and timing metadata. A truthful synthetic fixture
does not establish actual execution; production must check structural coherence
and the final implementation review must independently reconcile real execution.

**R9-2 — Helper deadlines are not hard bounds (F6-1 and package 4; S1-2/S1-3).**
`_Helper.__init__` calls synchronous `Process.start` before the monitor regains
control (`supervisor.py:104`); `poll` calls `Connection.recv` after readability
(`:122`). Readability does not establish that a complete framed payload has
arrived. Neither operation has a monitor-controlled bound. Helpers are freshly
spawned per operation/sample rather than a fixed ready set. `validate_sample`
has no timing fields, and the ready branch precedes sample timeout handling.
The existing constant/error/EOF tests do not demonstrate bounded blocked
startup or partial transport. Retain those tests; later implement bounded
readiness and nonblocking framed completion with owned process identities and
real blocked-operation/descendant tests, within Plan 036's existing contract.

**R9-3 — Failure qualification uses the wrong clock authority (package 2;
S1-3).** `s1_evidence.elapsed` reads only `VIPE_RESERVATION_START` from the
environment. `supervise` sets it in the worker's Popen environment, while the
reconciliation helper inherits the controller environment. If first evidence is
absent, `reconcile_first` can publish a `not_reached` record with elapsed `null`
(`s1_evidence.py:25–29,67–68`). The failed/not-reached path does not verify that
new record before returning it. `verify_first` and `reconcile_first` still use
the constant 3,600, despite `Ledger.reserve` supporting reduced effective
allocations; the existing reduced-allocation test only asserts reservation
seconds. Pass trusted reservation start, boot identity, allocation and work
deadline explicitly through worker/helper qualification. Require a durable
verified first pass before advancing and preserve actual failed-record times.

**R9-4 — Timeout discards reconciliation progress (package 3; S1-3).**
`reconcile_rows` stores verified identity lists only in process-local memory and
returns one summary at the end (`s1_evidence.py:185–250`). `monitored_call`
returns only after receiving a completed task and a subsequent resource sample.
If the helper is stopped during reconciliation, or that final sample fails,
`supervise` leaves `evidence_summary=None`; terminal publication substitutes
zero verified lower bounds and unknown totals (`s1_recovery.py:609`). This is
conservative rather than an invented count, but loses already verified evidence
required by the plan. Persist bounded incremental summaries before the work
deadline; terminal publication must consume the last verified summary without a
new recursive scan or qualification. Existing 340/170 assertions cover complete
synthetic results, not interrupted partial evidence.

**R9-5 — Later errors overwrite primary classification, and finalization remains
uncharged/unmonitored (packages 2/4; S1-2/S1-3).** `supervise` turns its primary
exception into a string, then assigns new `failure_kind` values for
reconciliation, cleanup and publication (`supervisor.py:409–486`). Earlier text
may survive concatenation, but a structured primary identity and ordered
secondary failures do not. The helper-level primary-preservation test does not
cover this supervisor path. Cleanup invokes `stop_group` without resource
sampling. Elapsed is measured before a possible additional helper reap and the
direct `ledger.finish` call; its blocking lock/append/flush/fsync occur outside
the monitor (`:477–492`, `ledger.py:47–76,201–210`). There is no durable
finalization acknowledgment in `resolved_result`. Therefore the final charge and
successful resolution do not establish the full deadline contract. These are
source defects, not merely omitted negative cases. A later bounded lifecycle
milestone must implement Plan 036's reserve subdivision, conservative charged
cutoff, acknowledgment and continuous observation together.

**R9-6 — Remaining numerical and worker evidence is incomplete, with a narrow
real envelope gap (package 5; S1-1 support and S1-3).**
`s1_evidence.validate_result` checks identity/order/runtime/first/row contents but
never validates the result's `native_wall_seconds`, `peak_allocated_bytes` or
`peak_reserved_bytes`, nor the row's `native_group_wall_seconds` and `group_size`.
The controller positive fixture omits these fields and synthesizes 510 rows
before launching a trivial child (`test_vipe_benchmark_s1_recovery.py:318–350`).
It proves the controller/acceptance path within that fixture, not successful real
`stages.segment` progression. The only actual segment fixture has three first
failure cases. Existing optional `synthetic_row(zero=True/skip=True)` inputs have
no collected calls. Other native/runtime mutation tables are coverage gaps;
this review found no new defect in the S0 semantic assignment algorithm. Add
missing time/memory envelope guards and genuine CPU segment progression in a
later small milestone using fake device/backend boundaries and real row guards.

The full applicable-boundary mutations, synchronized S1 admission/registration/
reservation contenders, identical continuation and consumed replay table remain
**unverified coverage**, not demonstrated duplicate execution. Generic reservation
concurrency tests and canonical comparisons are already present. The lifecycle
currently validates `started`/temporary events principally by order; their full
typed identity/reference matrix still requires an intended-boundary review and
tests. Do not claim every matrix cell is a proven production defect.

## Smallest next implementation scope

Recommend a new CPU plan for **R9-1 only**, with necessary fixture and immutable
bookkeeping support. The planner should finalize these concrete requirements:

1. Introduce one AST-readable literal declaration contract beside tests for all
   existing parameterized methods in the nine suites. Drive cases from the same
   ordered tables; keep scientific assertions and inputs intact. Detect missing,
   dynamic, duplicate and extraneous declarations before aggregate acceptance.
   Flatten nested callbacks to exact primitive parameter dictionaries; preserve
   bool/int/null distinctions. Keep nonparameterized callback lists empty.
2. Share strict parameter identity/comparison and receipt schema validation
   between the runner and production validator, without importing test modules
   during admission. Check exact order, multiplicity, typed values, statuses,
   derived counters, source membership/bytes before and after, and all required
   execution metadata. Bind the prescribed stdin, current runner, stdout/stderr,
   actual argv/interpreter, thread environment, UTC/monotonic timing and external
   exit evidence. Reject nonfinite/negative/inconsistent times and boolean counts.
   Choose one coherent normalized aggregate representation; validation-007's
   incomplete wrapper cannot become acceptable merely by changing its status.
3. Update the synthetic positive fixture to that complete contract and collect
   targeted receipt mutations: missing/substituted/reordered/duplicate tuples,
   primitive type changes, extra callbacks, parent pass with failed callback,
   missing/stale files or sources, discovery failure, wrong counts/types,
   argv/stdin/interpreter/environment discrepancies, invalid times, and disjoint
   receipts. Every negative begins from a passing disposable fixture and checks
   the intended rejection. Synthetic evidence remains explicitly fixture-only;
   no production bypass for fixture markers.
4. Finalize source and declarations, then run the exact serial nine-suite
   aggregate through the existing four-line stdin/runpy launcher. Independently
   reconcile collection, every typed callback, per-suite totals, source hashes,
   raw files and actual process completion. New tests change counts: do not
   hardcode 148/91 or generate expected case tuples from observed callbacks.
   Save a successor validation with distinct aggregate/milestone/overall
   acceptance flags. Keep all later R9-2–R9-6 and inherited coverage gates open.

Recommended **new plan-specific** allocation: 1,800 wall seconds from before
implementation inspection, final 180 seconds reserved for evidence; at most
eight CPU workers including native/helper threads; serial suites and one-thread
helper pools. At most three focused diagnostic invocations, each capped at
120 seconds, and at most two full aggregates, each capped at 300 seconds and
inside the same 1,800-second total. A second aggregate is allowed only after
a source change or a concrete failure/concern invalidates the first; it is not
routine repetition. If these limits are insufficient, retain the validated
partial milestone and exact remaining work; do not extend them silently. These
are CPU validation allocations, with **zero model evaluations, GPU attempts,
setup/download/smoke jobs or production mutations**. Historical allocations
and clocks are not reset. The skill's standing approval applies when PLAN
finalizes these limits within the user's constraints.

The next plan must also extend correction-006's bookkeeping lineage. Its last
status is `7ff80bbe…`/1,872 bytes, preserved verbatim in
`s1-recovery-status-before-008.md`; the subsequent blocked status is preserved in
`s1-recovery-status-before-009.md`. Current status has changed during the main
agent's authorized resume. `preservation` correctly rejects the old correction
against those new bytes as an unrecorded bookkeeping transition. Append actual
old/new transitions and a successor correction, preserving every snapshot and
original frozen record. This is routine evidence preparation, not scientific
corruption or missing authority. The main agent manages later status transitions
and task-related commits.

## Criteria and preservation

| Criterion | Fresh assessment |
| --- | --- |
| S1-1 | **Met for its specified amendment/source/CPU outcome.** The bound S0 function sums sigmoid token scores over period-delimited phrases and chooses the first maximum. Current detector code preserves native prediction outputs and attaches one assignment per retained query; five saved semantic methods cover empty/combined/disagreeing phrases, ties/subwords, alignment and SAM/tracking propagation. Frozen native prediction/preprocessing and source hashes match. This does not establish a live repaired output or complete adversarial coverage; those are still required before S1-3. Requiring a live result for S1-1 would add an unstated requirement. |
| S1-2 | **Not met.** Current admission guards and CPU evidence have the concrete gaps above; there is no production recovery authorization/registration. |
| S1-3 | **Not met.** No recovery reservation or calibration result exists. The original cleaned-up failures are preserved history, not a new recovery outcome. |
| S1-4 | **Met within this recovery's required preservation scope.** All 38 frozen records, prior failures, scientific aggregates/report and original ledger are unchanged; no unrelated allocation or rerun occurred. Historical P31-5 and unavailable older status/timing limitations remain explicit, with no retrospective certification. |

The ledger is byte-identical to the original baseline: **447 events**, 332,437
bytes, SHA-256 `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
valid chain ending `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
GPU accounting remains 30 historical attempts, 4,374.044265462899 seconds and
zero reserved; no active job or S1 recovery event exists. Failed finishes
250/255 and R-S skip 256 match. Of 162 prior audit records compared after
excluding the intentionally changing loop status, 161 match; the old `.git/index`
hash differs following the authorized implementation commit. Current tracked
changes are only loop status, with no source/scientific diff. An index comparison
to a precommit snapshot is not a scientific preservation failure.

Only a later authorized DO stage after all CPU gates close may consider the one
`S1-calibration-recovery-001` attempt, with positive effective seconds
`min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)`, inclusive cleanup
and finalization. Preserve one exclusive GPU group, 22 GiB device memory, eight
CPU workers, 150 GiB artifacts, 60 GiB downloads and existing preparation/setup
ceilings. Reservation consumes the attempt even without launch. Reconstruction
requires later separate authorization. D1 fit/check, R-S and scientific
aggregate/report reruns remain excluded.

Review timing is limited to the requested 15-minute stage. A clock was captured
after initial inspection, so no exact inspection-inclusive stopwatch value is
claimed. The assessment records the actual capture/end and this limitation.
The failed convenience invocation `python` returned `command not found`; using
installed `python3` for read-only JSON/hash analysis succeeded. This was a missing
command name, not a sandbox failure, and no permission workaround was used.
