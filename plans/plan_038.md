# Plan 038 — Correct aggregate subtest evidence and validate final source

Iteration 7 PLAN, 2026-09-19. **Live S1 admission remains NOT READY;
implementation acceptance is incomplete.**

## Scope and authority

Continue the [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md)
from [review-007](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-007.md),
[assessment-012](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-012.json),
[Plan 037](plan_037.md),
[validation-006](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-validation-006.json),
[implementation-review-005](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-implementation-review-005.md),
[preparation-006](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-preparation-006.md)
and [status](../docs/continuous-improvement/plan031-s1-recovery-20260919/status.md).
AGENTS.md, the current diff and production ledger were also reviewed.

This PLAN stage creates only this file and `plan-link-007.md`. No source edits,
test execution, GPU/model/device operations, production controller calls, ledger
mutation, staging, commits or delegation. Never read `prompts`, including via
aliases. The explicit user restrictions override standing commit/delegation
instructions. The command below is for a later IMPLEMENT stage, not this PLAN.

The later checkpoint has exactly three tasks: change the existing contracts
subtest label to `item.record()` while retaining its original guard input; run
the exact fresh nine-suite aggregate; independently review source-bound evidence.
Only `tests/test_vipe_benchmark_contracts.py` may receive an implementation edit,
and only the one line below. Preserve all preexisting changes. Do not change
Identity, guard, the runner/serializer, production receipt validation, helper
implementation, case declarations, scientific code or configuration. Inherited
gaps remain acceptance blockers for later work, not additional tasks here.

Capture UTC and monotonic start **before any implementation inspection**. Keep
Plan 037's **1,800-second inspection-inclusive wall cap**, including the edit,
aggregate, reconciliation and handoff, with the final **180 seconds reserved for
evidence**. Use at most **eight CPU workers including helper/native threads**,
serial suites and one-thread helper pools. Reserve time for the full aggregate;
do not restart or extend the clock. At exhaustion, interruption or an out-of-scope
failure, preserve actual results and explain the incomplete checkpoint. Do not
expand implementation to repair a newly discovered failure.

Use disposable test ledgers/job roots only. **No production ledger mutation
during implementation, validation, review or preparation, even after a pass.**
Do not invoke a production controller as a dry run, create production job roots,
authorize, register or reserve. No staging, commits or delegation in this
checkpoint. No GPU/device probe, model forward, setup, download or smoke job.
No reconstruction, R-S or scientific aggregation/report rerun. The prescribed
CPU test aggregate is the only planned rerun.

## Reviewed baseline

Iteration 6's exact aggregate failed: **148 methods, 83 recorded callbacks,
zero failures, one error, zero skips, exit 1**, elapsed 48.213986296 seconds.
`Result.addSubTest` attempted strict JSON serialization of an Identity instance.
The first expected ValueError assertion had succeeded; callback encoding then
raised and aborted the remaining seven iterations. That method recorded zero
callbacks. The method count does not establish complete case coverage.

Review-007's unchanged-method CPU control passed all eight guard assertions with
standard unittest and reproduced one error/zero callbacks with the aggregate
Result. Its diagnostic exit zero confirms those observations only. It neither
repairs the old run nor replaces a final-source aggregate. Prior semantic support
and the 13 helper methods/12 declared helper cases remain limited to their
recorded scope; helper and overall acceptance remain incomplete.

The read-only PLAN audit matched assessment-012's **72 source/config/test
records, 38 frozen records, 40 prior-loop records, six bookkeeping transitions,
five aggregate evidence files and 69 preexisting loop snapshot records**, plus
requested references, current status and index. The tracked diff remains 79,284
bytes, SHA-256 `d08127f2dc779e89a31343514c1eef797f171f326cecde20fc03eb6d957459a5`.
Assessment-012 is 130,823 bytes, SHA-256
`9db6647de79757df1df7a047e960cc83657a28f954ead7fad7f069da9e03b0fe`.

The production ledger at
`.local/vipe-alternatives/plan031-20260913T032700Z/ledger.jsonl` was read directly,
without the append/lock API. Its **447-event chain is valid**, 332,437 bytes,
SHA-256 `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
head `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
All recomputed resource totals match assessment-012: GPU remains **30 attempts,
4,374.044265462899 seconds elapsed, zero reserved**. No active reservation or S1
recovery event exists. Failed finishes 250/255 and R-S skip 256 remain intact.
This read-only accounting check makes no device-availability claim.

Preserve the original baseline, correction-005 and transition-006-1 lineage.
Historical P31-5, unavailable older status bytes and missing inspection-inclusive
timing remain unresolved; do not retrospectively certify or reset them.

## 1. Minimal correction and predeclared expectation

In `AccessTests.test_heldout_final_window_wrong_branch_and_pair_rejected`, replace
only `self.subTest(item=item)` with `self.subTest(item=item.record())`:

```python
with self.subTest(item=item.record()), self.assertRaises(ValueError):
    guard(item, self.config)
```

Keep the eight original Identity fixtures, their order, `assertRaises(ValueError)`
and `guard(item, self.config)` unchanged. `Identity.record()` already returns all
four fields through `dataclasses.asdict`. This is evidence-label normalization;
the guard must still receive the original Identity object. Do not use a general
serializer, `default=str`, repr, field coercion, exception suppression, case
removal or skips. Keep `True` a boolean and absent pair_start a JSON null.

Before execution, retain this independent ordered expected parameter list for
`test_vipe_benchmark_contracts.AccessTests.test_heldout_final_window_wrong_branch_and_pair_rejected`:

```json
[
  {"item":{"branch":"reconstruction","camera":0,"frame":0,"pair_start":0}},
  {"item":{"branch":"calibration","camera":1,"frame":200,"pair_start":null}},
  {"item":{"branch":"depth","camera":0,"frame":100,"pair_start":null}},
  {"item":{"branch":"depth","camera":1,"frame":176,"pair_start":null}},
  {"item":{"branch":"reconstruction","camera":1,"frame":21,"pair_start":null}},
  {"item":{"branch":"reconstruction","camera":1,"frame":22,"pair_start":20}},
  {"item":{"branch":"calibration","camera":1,"frame":21,"pair_start":null}},
  {"item":{"branch":"calibration","camera":true,"frame":100,"pair_start":null}}
]
```

All eight outcomes must be `passed`. Compare order, multiplicity, exact keys,
values, primitive types and outcomes against this list and assessment-012, never
against expectations generated from the new receipt. Use canonical strict JSON
(`allow_nan=False`) or recursive type-aware comparison; ordinary Python equality
conflates `True` and `1`. Perform this independent check during evidence review
without editing the runner's existing declaration comparator.

## 2. Exact fresh final-source aggregate

After the one-line change is final, ensure `S1_HELPER_DIAGNOSTIC` is **unset**
(value `1` selects a helper-only diagnostic). From the repository root execute
exactly the following invocation, with the four Python stdin lines and their
final newline unchanged:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .local/envs/stg-colmap/bin/python -B - <<'PY'
import runpy
import sys
sys.path.insert(0, "scripts")
runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})
PY
```

Use the existing importable guarded runner. Do not substitute a contracts-only
command, ordinary unittest pass, helper diagnostic or module-file launcher.
Verify actual launcher argv `['.local/envs/stg-colmap/bin/python', '-B', '-']`,
original Python argv `['-']`, runpy argv and resolved interpreter (currently
`/usr/bin/python3.14`). Record actual environment values and process exit status,
not only the receipt's asserted status.

Discover each suite once and execute all nine serially in this exact order.
Each pattern is under `tests/`:

| Order | Pattern | Predicted methods | Predicted callbacks |
| --- | --- | ---: | ---: |
| 1 | `test_vipe_benchmark_s1_semantics.py` | 5 | 6 |
| 2 | `test_vipe_benchmark_s1_recovery.py` | 13 | 37 |
| 3 | `test_vipe_benchmark_backends.py` | 35 | 24 |
| 4 | `test_vipe_benchmark_contracts.py` | 15 | 8 |
| 5 | `test_vipe_benchmark_component_recovery.py` | 3 | 4 |
| 6 | `test_vipe_benchmark_execution.py` | 10 | 0 |
| 7 | `test_vipe_benchmark_budgets.py` | 31 | 0 |
| 8 | `test_vipe_benchmark_supervisor.py` | 28 | 12 |
| 9 | `test_vipe_benchmark_review_annotations.py` | 8 | 0 |
| Total | | 148 | 91 |

These are predictions for the one-line correction, **not executed results or
permanent hardcoded targets**. Independently reconcile current method membership
and callback evidence; unexpected membership or counts require explanation and
an incomplete disposition, not silently adjusted expectations. Added tests or
declarations would exceed this checkpoint's implementation scope.

Require zero discovery errors, failures, errors and skips, exit zero, all ordered
method IDs accounted for, all recorded outcomes passed, and exact typed evidence
for the eight restored callbacks. Reconcile stdout/stderr, per-suite totals,
aggregate totals and actual process completion independently. Keep complete
callback records across all suites; do not claim that this narrow check closes
the inherited full-declaration coverage gap.

Retain exact stdin and runner bytes/hashes, stdout/stderr, actual exit status,
argv/interpreter/thread environment, UTC and monotonic start/end/elapsed,
per-suite timing and source/config/test membership and hashes before and after.
Verify the full `source_paths()` membership, including the runner and corrected
test. Pre-run, post-run and review-time records must agree. Relative to the
review baseline only the specified test line may change; record its old/new
hashes and exact diff. New evidence documents are outside that implementation
source set. A later source/test/runner edit invalidates validation and requires
another complete aggregate within the same cap; otherwise report incomplete.
Do not splice old/focused results into the new aggregate or repeat routine tests
after a reconciled pass without a new concern.

Run the preservation check:

```sh
git diff --check -- . ':(exclude)prompts/**' ':(exclude)**/prompts/**'
```

Follow AGENTS.md's single scoped outside-sandbox retry for an actual or suspected
access restriction, checking partial effects before retrying only the failed
operation. The Identity encoding error is an integration defect, not such a
restriction. If the retry is denied, unavailable or fails, stop affected work and
report the exact command/error and permission/rule status without workarounds.

## 3. Source-bound review and immutable handoff

Preserve `s1-recovery-aggregate-006-001` and validation-006 as failed evidence.
The unchanged runner still hardcodes label `006` and advances its run number;
the next unused directory at planning time is `s1-recovery-aggregate-006-002`.
Recheck availability and retain the actual generated name. Explain that this is
the iteration-7 run from the unchanged runner in successor validation; do not
rename the directory, edit the runner to change the label, or overwrite history.

Under `docs/continuous-improvement/plan031-s1-recovery-20260919`, use next unused
immutable evidence names (all currently available):

- `s1-recovery-baseline-correction-006.json`: extend correction-005 with this
  plan, review-007 and assessment-012, preserving original baseline and lineage.
- `s1-recovery-validation-007.json`: actual invocation, complete fresh receipt,
  source binding, timing, minimal-change audit and distinct checkpoint/aggregate/
  overall acceptance outcomes, including failures or missing evidence.
- `s1-recovery-implementation-review-006.md`: independent reconciliation against
  this plan and source, including the literal eight-case expectation and all
  inherited gate dispositions.
- `s1-recovery-preparation-007.md`: non-executable handoff with exact bound
  evidence references and remaining blockers; no live authority.

Recheck every name; advance occupied suffixes without overwriting. Retain raw
companions. Bind resolved absolute paths, SHA-256 and integer byte counts; ledger
event references use sequence/hash. Reject aliases, conflicting records and
nonfinite JSON. Finalize correction, validation, review, then preparation.
Keep current status and all earlier evidence unchanged for this narrow checkpoint.
Rehash frozen records, prior loop records, original ledger/prefix/chain/head and
resource totals, status, index and implementation membership before handoff.

Report separately whether F7-1's harness correction is complete, whether the
fresh aggregate ran and passed, and whether overall acceptance is complete.
Preserve these inherited dispositions without implementing them here:

| Gate | Required disposition |
| --- | --- |
| F7-1 / V1 | Open until the minimal correction and exact aggregate pass with eight typed callbacks and independently reconciled final-source evidence. |
| F7-2 / package 5 | Open: only two of 18 parameterized methods have runner-loaded declarations (12 helper cases); ordinary equality conflates bool/int; production receipts check nonempty callbacks rather than exact typed tuples. Full declarations, metadata guards, numerical/runtime/envelope cases and real 510-row `stages.segment` progression remain incomplete. |
| F6-1 | Partial: stdin spawn/control passed previously; synchronous Process.start/Connection.recv bounds and readiness coverage remain open. |
| F6-2 | Narrow worker context/shared-peak correction supported; later-phase ownership matrix remains open. |
| F6-3 | Partial: ownership/cleanup-stop evidence supported; fake exception labels do not prove real enumeration/kill/reap failure handling; worker descendants do not prove spawned-helper descendant cleanup. |
| Plan 036 package 1 | Applicable-boundary mutations, synchronized locked contenders, continuation and consumed replay matrix remain incomplete. |
| Package 2 | Trusted reservation clock/allocation, structured primary/secondary failures and corruption/storage/death/CLI tables remain incomplete. |
| Package 3 | Exact unique produced/qualified partial counts, 340/170 categories and incremental durable evidence surviving helper timeout remain incomplete. |
| Package 4 | Ready helper set, bounded transport/descendants, sample freshness, monitoring through cleanup/finalization, reserve subdivision, conservative charge and durable acknowledgment remain incomplete. |

Keep `implementation_acceptance_complete=false` and
`ready_for_live_admission=false` while any inherited gate is open, even if the
new aggregate passes. Zero-error validation is necessary and is not sufficient
for live admission. S1-1 retains prior semantic support within its tested scope;
S1-2 and S1-3 remain unmet; S1-4 requires the preservation audit. End after the
evidence handoff. Do not proceed to live admission or recovery.

## Unchanged later calibration budget

Only a separately authorized later DO stage, after every CPU acceptance gate
passes and fresh bound authority/resource checks succeed, may consider
`S1-calibration-recovery-001`. Preserve **one calibration attempt and one
3,600-GPU-second cap** within the existing 93,600 cumulative GPU seconds:

`effective_seconds = min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)`

Require a positive allocation. Cleanup/finalization reserve
`min(30, effective_seconds/4)` remains inside the cap. Loading, qualification,
hashing, acceptance, serialization, publication, cleanup and finalization are
charged. Reservation consumes the attempt even without launch; no retry, renamed
attempt or reset. Retain one exclusive GPU group, 22 GiB device memory, eight CPU
workers, 150 GiB artifacts, 60 GiB downloads and existing 57,600-second
preparation/setup ceilings. No new setup/download/smoke allocation.

Preserve the S0 token-sum amendment, native phrases/boxes/scores, strict
thresholds, weights, precision, preprocessing, SAM refinement, tracking,
environment pins and annotation policy. Reconstruction requires separate later
authorization after calibration review; R-S and scientific aggregation/report
reruns remain excluded. This plan grants no production authority and makes no
claim of fresh validation success.
