# Plan 037 — Correct S1 CPU helper integration and validate final source

Iteration 6 PLAN, 2026-09-19. **Implementation acceptance is incomplete. Live
S1 calibration recovery remains NOT READY.**

## Authority, scope and limits

Continue the [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md)
using [review-006](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-006.md),
[assessment-010](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-010.json),
[Plan 036](plan_036.md),
[validation-005](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-validation-005.json),
[implementation-review-004](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-implementation-review-004.md),
[preparation-005](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-preparation-005.md)
and [status](../docs/continuous-improvement/plan031-s1-recovery-20260919/status.md).

This PLAN stage creates only this document and `plan-link-006.md`. No source
editing, test execution, GPU/model/device work, production controller calls,
ledger mutation, staging, commits or delegation. Never read `prompts`, including
through aliases. The explicit user restrictions override standing commit and
delegation instructions in AGENTS.md and the objective.

The later IMPLEMENT stage is a **CPU-only helper correction checkpoint**:
correct F6-1/F6-2/F6-3, collect their regressions, finish the narrow runner support
needed to measure them, then run the exact final current-source aggregate below.
Do not turn this checkpoint into a rewrite of all five Plan 036 packages. Their
unclosed requirements remain binding acceptance gates, not implicitly completed
or waived by this plan. The aggregate must still run after the scoped correction
when time and execution access permit; open broader gates must be reported
separately from its pass/fail result.

Capture UTC and monotonic start **before implementation inspection**. Limit the
whole continuation, including inspection, edits, diagnostics, aggregate and
handoff, to **1,800 wall seconds**, with the final **180 seconds reserved for
evidence**. Maximum **eight CPU workers including helper/native threads**;
run suites serially and keep helper thread pools at one. Budget for the aggregate
before beginning optional refinements. Never extend or restart the clock to
finish it. On exhaustion or explicit stop, retain actual partial evidence and
mark acceptance incomplete; explain exactly whether/why the aggregate was not
started, interrupted or failed. No old result may fill the gap.

Use disposable test ledgers and job roots only. **No production ledger mutation
during implementation, validation or preparation, even after a passing run.**
Do not call the production controller for a dry run, create production job
directories, authorize, register or reserve. No staging, commits or delegation
in the planned continuation. Preserve the S0 token-sum amendment and native
phrases, boxes, scores, strict thresholds, weights, precision, preprocessing,
SAM refinement, tracking, environment pins and annotation policy. No scientific
reconstruction, R-S, aggregation/report rerun, new inputs, setup, downloads,
model forwards or smoke jobs. The CPU test aggregate is not a scientific rerun.

Abbreviations: `C = docs/continuous-improvement/plan031-s1-recovery-20260919`,
`L = .local/vipe-alternatives/plan031-20260913T032700Z`,
`J = S1-calibration-recovery-001`.

## Reviewed starting point

The 13-method focused diagnostic passed in 41.147 seconds on intermediate
iteration-5 source. Subsequent spawned-helper and strict-sampling edits were
not tested. Validation-005 has `tests=[]`; the final nine-suite aggregate was
never attempted because implementation ended on the user's finalization
request. There was no recorded aggregate failure or permission denial causing
that omission. Static collection of 135 methods and 16 parameterized methods
is not execution evidence, nor a fixed target count for this iteration.

Review-006 recorded five CPU diagnostic cases in three invocations. Stdin spawn
failed with child `<stdin>` FileNotFoundError and parent EOFError; an importable
guarded-file control succeeded. Worker sampling rejected its own PID when the
worker context was omitted. A helper returning false from `close()` still
allowed accepted work. Diagnostic harness exit zero means those observations
were captured, not that the helper passed. The startup error is a Python
integration defect, not a sandbox denial.

The read-only PLAN audit matched all **71 source/config/test records**, **38
frozen scientific records**, **40 prior-loop records** and **five bookkeeping
transition records** in assessment-010. Requested references, current status,
index and tracked diff also match. The tracked diff is 61,085 bytes, SHA-256
`3dcdcd9da017754f4c4f3b9af1b18e38baab2686dfcc4b86fdc2a3fc7f61b242`.
Retain those existing changes; edit only demonstrated helper integration gaps.

The production ledger was read without opening the Ledger append/lock API.
Its **447-event hash chain** is valid, **332,437 bytes**, SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
head `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
It is byte-identical to assessment-010: no active reservation or S1 recovery
event, original failed finishes 250/255 and R-S skip 256 retained. Historical
GPU accounting remains 30 attempts, 4,374.044265462899 seconds, zero reserved.
All other recorded resource totals remain unchanged. This is an accounting
audit, not a device-availability check.

Correction-004 and transition-005-1 are the latest recorded lineage. Keep the
original baseline, scientific records and ledger prefix. Historical P31-5,
unavailable older status bytes and missing inspection-inclusive timing remain
unresolved; do not reconstruct history or recast old elapsed times as compliant.

## Ordered implementation checkpoint

### 1. F6-1 — Make spawned startup work under the prescribed stdin launcher

Inspect `_Helper` and `monitored_call` in `scripts/vipe_benchmark/supervisor.py`
and the existing `s1_cpu_helper.py`. Use an importable guarded bootstrap and
top-level serializable operations. Preserve spawned interpreter isolation; no
return to fork or transport of local closures. Make the fixed runner below
importable under multiprocessing bootstrap, with suite execution protected by
`if __name__ == '__main__'`. An explicit importable helper executable is also
permitted if needed to make the production entry path safe. Do not fix the
problem merely by replacing the prescribed stdin launcher with a file command.

Handle child startup failure, EOF and broken transport as typed helper failures
with phase and ownership information. Constructor failure after process creation
must retain responsibility for that process. Startup, readiness and transport
must use bounded waits; no native/model imports or device sampling in regression
children. A returned constant is insufficient until its helper is confirmed
reaped. Any broader unbounded transport/startup issue left open remains P2.

Collect a real spawned constant-operation regression inside the actual stdin
runner, plus an importable guarded-file control. Exercise the runner bootstrap
without recursively launching the aggregate. Collect bootstrap failure and
EOF-before-result cases with bounded return, preserved error and no lost child.
Run a small diagnostic first, then include the same collected methods in the
final aggregate. A mocked process cannot be the only positive startup test.

### 2. F6-2 — Preserve worker ownership and shared resource peaks

Pass the captured worker context (`worker=process`) and the shared `peak` mapping
into the `worker_sample` monitored call. Preserve the context through subsequent
phases; do not infer ownership from a PID alone or whitelist arbitrary readings.
Initial/prelaunch ownership stays empty. Keep the unreaped exited worker in
ownership enumeration while its identity is still established, without treating
a zombie as a live survivor. Do not weaken foreign-PID checks or signal foreign
processes. Sampling within nested calls must not lose the highest observed
device/artifact/download values.

Collect separate owned live PID success, owned unreaped exited PID success,
foreign-only rejection, mixed owned/foreign rejection and empty-prelaunch
ownership cases. Use deterministic fake resource readings and CPU processes;
never invoke `gpu_reading` or `nvidia-smi`. Assert the actual inner monitor and
supervisor call path, exact rejection phase/category, shared peak maxima and
no foreign signals. Empty GPU-PID positive fixtures alone cannot close F6-2.

### 3. F6-3 — Retain unsettled helpers and propagate cleanup uncertainty

Replace fire-and-forget `close()` use with explicit lifecycle ownership shared
with the supervisor. Track task/sample helpers and owned descendants across
result, exception and finalization paths. A helper returning false, raising,
or reporting unknown ownership remains tracked until bounded reaping confirms
termination; do not clear its reference or let a `closed` flag prevent later
reaping. Confirmed cleanup must be idempotent. No blocking join or unbounded
destructor may escape the monitor's deadline.

Use nonblocking reap and bounded TERM/KILL within the current phase allocation.
Retain the original failure and attach cleanup errors as secondary observations.
Propagate unresolved helper/descendant cleanup into `cleanup_uncertain`,
`cleanup_confirmed=false` and `stop_required=true`; an empty worker survivor
list is insufficient. After reservation this is a consumed failed/unresolved
stop, never successful acceptance or successful result resolution. Before
reservation, block without consuming J. Failed finalization/publication must
not convert unknown cleanup to success or silently discard ownership evidence.

Collect task and sample cleanup on success, error and timeout; false-then-reaped
and permanently-false close; close/enumeration/kill/reap exceptions; repeated
close; descendant survival; and unresolved helper cleanup with an empty worker
survivor list. Use controlled CPU children for a real reap/descendant test and
fakes for deterministic failures. Assert bounded completion, retained ownership,
primary/secondary error identity and consumed stop behavior in a disposable
supervisor fixture. If the deadline cannot establish cleanup, report uncertainty
truthfully and keep admission blocked.

Limit code edits to the existing helper/supervisor, necessary failure propagation
in S1 evidence/recovery or execution, the fixed runner and the prescribed tests.
Do not change scientific backend behavior to make a fixture pass. Keep generic
S1 rejection and S2 recovery regressions intact.

## Final current-source aggregate — required after the scoped correction

Add `scripts/vipe_benchmark/s1_validation_runner.py` as the fixed CPU unittest
runner, covered by exact `source_paths()` membership. Finalize its code and all
test/case declarations before this run. From the repository root, use exactly:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .local/envs/stg-colmap/bin/python -B - <<'PY'
import runpy
import sys
sys.path.insert(0, "scripts")
runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})
PY
```

The four Python lines above are the exact stdin, including their final newline;
the shell delimiter is not part of stdin. The runner must use its importable
module identity during spawn and guard main execution. Record original stdin
Python argv `['-']` separately from argv inside `runpy` and the actual launcher
argv `['.local/envs/stg-colmap/bin/python', '-B', '-']`; verify the resolved
interpreter rather than silently substituting another environment. No arbitrary
stdin that merely names the suites is equivalent.

Discover and execute these patterns in **one serial aggregate**, in this order:

1. `tests/test_vipe_benchmark_s1_semantics.py`
2. `tests/test_vipe_benchmark_s1_recovery.py`
3. `tests/test_vipe_benchmark_backends.py`
4. `tests/test_vipe_benchmark_contracts.py`
5. `tests/test_vipe_benchmark_component_recovery.py`
6. `tests/test_vipe_benchmark_execution.py`
7. `tests/test_vipe_benchmark_budgets.py`
8. `tests/test_vipe_benchmark_supervisor.py`
9. `tests/test_vipe_benchmark_review_annotations.py`

Use actual unittest callbacks to capture ordered method IDs, literal typed
subtest parameter dictionaries and outcomes, discovery errors, per-suite and
aggregate counters. Retain stdout/stderr, exit status, exact stdin and runner
bytes/hashes, thread environment, UTC and monotonic start/end/elapsed, and
source/config/test membership and hashes before and after execution. Record
per-suite timing and process invocation, not invented metadata. Discover each
suite once; helpers must not reenter test execution. Run no GPU/model/native
operation or production controller in tests; replace external boundaries with
CPU fixtures and fail unexpected calls.

Declare literal ordered tuples for the new parameterized regressions beside
their methods and reconcile them independently against actual callbacks. Retain
Plan 036 package 5's requirement for exact declarations across all nine suites
and strict receipt metadata validation. If broader declarations or receipt guards
remain unimplemented, record those coverage/acceptance gaps explicitly even if
every executed test passes. Do not fabricate expected coverage from the receipt
itself, accept arbitrary subtest strings or hardcode the old 135/79 counts.

Independently reconcile invocation, logs, emitted outcomes and exact source
bytes before recording a pass. Require zero failures/errors/skips and agreement
of every per-suite/aggregate total; absent, interrupted or mismatched evidence
is incomplete. Do not merge disjoint focused runs into an aggregate. A later
source/test/runner/case-table edit invalidates the run and requires a fresh full
aggregate within the same wall cap; otherwise retain incomplete acceptance.
No further routine tests after a successful final run without a new concern.

Also run the preservation check:

```sh
git diff --check -- . ':(exclude)prompts/**' ':(exclude)**/prompts/**'
```

Follow AGENTS.md's single scoped outside-sandbox retry rule for an actual or
suspected access restriction, after checking for partial effects. The recorded
stdin integration defect is not such a restriction. On denied/failed retry,
stop affected work, retain the exact command/error and rule status, and report
the blocker without alternative access workarounds.

## Acceptance and immutable handoff

Report three separate outcomes: helper checkpoint completion, current-source
aggregate execution/pass, and overall implementation acceptance. A pass of the
first two does not close untested inherited gates. Keep a disposition for every
Plan 036 package, with actual collected method/tuple evidence where completed:

| Inherited gate | Obligations still open at this PLAN stage |
| --- | --- |
| 1 / L1-L2 | Applicable-boundary mutations, real synchronized locked contenders, continuation and consumed replay cases |
| 2 / P1 | Trusted reservation clock/effective allocation, structured primary/secondary failures, corruption/storage/death/CLI tables |
| 3 / P1 | Exact unique produced/qualified partial counts and 340/170 categories, incremental durable summary surviving helper timeout |
| 4 / P2 | Fixed ready helper set before reservation, bounded readiness/transport/descendants, fresh timed samples, continuous monitoring through cleanup and ledger lock/append/fsync, reserve subdivision, conservative finalization charge and durable acknowledgment |
| 5 / A1-A4 | Complete literal tuple declarations and receipt guards, remaining numerical/runtime/envelope cases, real `stages.segment` progression before frame 62 through 510 ordered rows |
| V1 | Exact final invocation, outcomes, logs and source binding with independent reconciliation; execution is required by this checkpoint |

Plan 036 contains the full acceptance matrices and deadline contracts; none is
relaxed. Keep `implementation_acceptance_complete=false` and
`ready_for_live_admission=false` while any gate remains open. CPU success alone
does not satisfy S1-2's production admission or S1-3's live outcome. S1-1 retains
prior semantic support within its tested scope; S1-4 requires a preservation audit.

Use next unused immutable artifacts under C, currently:

- `s1-recovery-baseline-correction-005.json`, extending correction-004 with this
  plan/review-006/assessment-010 and unchanged original baseline and lineage.
- `s1-recovery-validation-006.json`, containing actual final-source evidence,
  checkpoint/aggregate/acceptance distinctions, open cases, timing and audit.
- `s1-recovery-implementation-review-005.md`, independently reconciling the
  receipt and giving F6-1/F6-2/F6-3 plus all inherited gate dispositions.
- `s1-recovery-preparation-006.md`, a non-executable handoff with blockers and
  exact bound correction/validation/review references, never live authority.

Check suffix availability again during implementation; advance occupied names
without overwriting them. Retain raw logs and exact stdin as immutable companions.
Prefer leaving status unchanged. If implementation changes status, save its old
bytes and an explicit old/new hash/byte/reason transition before finalizing the
successor correction. Finalize correction, validation, review, then preparation.
Bind resolved absolute paths, SHA-256 and integer byte counts; event references
use sequence/hash. Reject aliases, conflicts and nonfinite JSON values.

Rehash frozen records, prior loop records, status lineage, source membership,
full production ledger/prefix/chain/head/totals and index. Preserve original
failures and no new production recovery events. Do not reset historical caveats.
End the checkpoint after evidence and handoff; do not proceed to a live attempt.

## Unchanged later calibration ceiling

Only a separately authorized later DO stage, after **all** CPU gates pass and
fresh bound evidence/resource checks succeed, may consider J. There remains
**one calibration attempt and one 3,600-GPU-second cap**, within the existing
93,600 cumulative GPU seconds:

`effective_seconds = min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)`

Require positive allocation. Cleanup/finalization reserve
`min(30, effective_seconds/4)` stays inside it; loading, qualification, hashing,
acceptance, serialization, publication, cleanup and finalization are charged.
Reservation consumes J even without launch. No retry, renamed attempt or reset.
Retain one exclusive GPU group, 22 GiB device memory, eight CPU workers, 150 GiB
artifacts, 60 GiB downloads and existing 57,600-second preparation/setup ceilings.
No new setup/download/smoke allocation. Reconstruction needs separate later
authorization after calibration review; R-S and scientific aggregate/report
reruns remain excluded. Neither document created in this PLAN stage grants
production authority or asserts validation success.
