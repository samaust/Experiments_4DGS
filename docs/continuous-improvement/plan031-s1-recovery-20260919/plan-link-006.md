# PLAN 006 — CPU helper correction and final current-source validation

Created [Plan 037](../../../plans/plan_037.md) from [objective](objective.md),
[review-006](review-006.md), [assessment-010](assessment-010.json),
[Plan 036](../../../plans/plan_036.md),
[validation-005](s1-recovery-validation-005.json),
[implementation-review-004](s1-recovery-implementation-review-004.md),
[preparation-005](s1-recovery-preparation-005.md), [status](status.md), AGENTS.md,
the current diff and production ledger. **Live S1 recovery remains NOT READY.**

The next implementation checkpoint is CPU-only:

1. Correct F6-1 with an importable guarded spawned bootstrap under the unchanged
   stdin launcher; collect actual-launcher and constant-operation controls.
2. Correct F6-2 by passing captured worker ownership and shared peaks into
   sampling; collect owned, foreign and unreaped exited-worker cases.
3. Correct F6-3 by retaining unsettled helpers/descendants, bounding reaping and
   propagating unresolved cleanup into a consumed stop that cannot resolve as
   success.
4. After final helper/test/runner changes, run the exact current-source aggregate
   specified in Plan 037. Its fixed stdin invokes the importable guarded runner
   using `OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1
   .local/envs/stg-colmap/bin/python -B -`. Suite order is s1_semantics,
   s1_recovery, backends, contracts, component_recovery, execution, budgets,
   supervisor, review_annotations. Preserve exact invocation, stdin, logs,
   timing, every method/literal subtest outcome, counters and source hashes.

The aggregate follows this bounded correction; remaining Plan 036 gates are
reported separately and stay binding. Passing the helper checkpoint or executed
tests does not establish complete acceptance. All five inherited safety packages
remain open at planning time. No old focused result, static collection count,
diagnostic harness exit or synthetic receipt substitutes for final-source
execution. Later source/test/runner changes invalidate the aggregate.

The implementation cap is **1,800 wall seconds measured before inspection**,
including diagnostics and aggregate, with **180 seconds reserved for evidence**,
and **eight CPU workers including helper/native threads**. Use disposable test
ledgers only. No production ledger mutation during implementation, validation or
preparation, even after tests pass. On exhaustion or interruption retain truthful
incomplete results and the exact reason. No staging, commits or delegation.

Current successor artifact suffixes are correction-005, validation-006,
implementation-review-005 and preparation-006; recheck availability and preserve
occupied records. Extend correction-004 and existing bookkeeping lineage without
resetting the original baseline. Prefer unchanged status; preserve old bytes and
a hash-bound transition if a later implementation updates it. The final handoff
is non-executable and explicitly lists remaining live-admission blockers.

The read-only PLAN audit matched all 71 source/config/test records, 38 frozen
scientific records, 40 prior-loop records and five bookkeeping transition
records in assessment-010. References, status, index and tracked diff match.
The production ledger remains **447 valid chained events / 332,437 bytes**,
SHA-256 `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
head `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
No active reservation or S1 recovery event exists in this snapshot. Historical
GPU totals remain 30 attempts / 4,374.044265462899 seconds / zero reserved.
Failures 250/255 and R-S skip 256 are retained, as are P31-5 and historical
timing/status-byte limitations. This is not a device-availability check.

Only a separately authorized later DO stage after all CPU gates pass and fresh
checks may consider `S1-calibration-recovery-001`: **one attempt, 3,600 GPU
seconds maximum**, positive effective allocation
`min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)` with cleanup and
finalization inside the cap. Reservation consumes the identity without launch.
Existing device, CPU, disk, download and preparation/setup ceilings remain.
No reconstruction, R-S or scientific aggregation/report rerun; reconstruction
requires separate later authorization after calibration review.

This PLAN stage creates only Plan 037 and this link. No source edits, tests,
GPU/model/device work, production mutations, staging, commits or delegation.
No `prompts` content was read. Neither document authorizes live admission.
