# PLAN 007 — Aggregate subtest correction and fresh evidence review

Created [Plan 038](../../../plans/plan_038.md) from [objective](objective.md),
[review-007](review-007.md), [assessment-012](assessment-012.json),
[Plan 037](../../../plans/plan_037.md),
[validation-006](s1-recovery-validation-006.json),
[implementation-review-005](s1-recovery-implementation-review-005.md),
[preparation-006](s1-recovery-preparation-006.md), [status](status.md), AGENTS.md,
the current diff and production ledger. **Live S1 admission remains NOT READY.**

The later CPU-only checkpoint is limited to:

1. Change only the contracts test's `subTest(item=item)` to
   `subTest(item=item.record())`. Retain the original Identity fixtures,
   `assertRaises(ValueError)` and `guard(item, self.config)` unchanged.
2. Run Plan 038's exact four-line stdin invocation through the existing guarded
   runner with `S1_HELPER_DIAGNOSTIC` unset, `OMP_NUM_THREADS=1`,
   `OPENBLAS_NUM_THREADS=1` and `.local/envs/stg-colmap/bin/python -B -`.
   Execute one serial aggregate in order: s1_semantics, s1_recovery, backends,
   contracts, component_recovery, execution, budgets, supervisor,
   review_annotations.
3. Independently reconcile invocation, process status, logs, ordered methods,
   typed callbacks, counters and final-source membership/hashes. All eight
   Identity callbacks must match the predeclared ordered records in Plan 038
   and assessment-012 and be passed, preserving boolean `true` and JSON null.
   Ordinary Python equality is insufficient. Require zero discovery errors,
   failures, errors and skips, and exit zero.

The predicted aggregate after only this edit is **148 methods / 91 callbacks**,
including contracts **15 / 8**. These are source-derived expectations, not results
or permanent hardcoded targets. The prior aggregate remains failed at
148 methods / 83 callbacks / one error / exit 1. Preserve validation-006 and
`s1-recovery-aggregate-006-001`; no older control or focused pass replaces fresh
execution. Any later source/test/runner edit requires another full aggregate.

Keep the runner unchanged. Its hardcoded `006` label means the next directory
is currently `s1-recovery-aggregate-006-002`; recheck availability and explain
iteration-7 provenance without renaming history. Next unused handoff names are
correction-006, validation-007, implementation-review-006 and preparation-007.
Extend correction-005 and transition-006-1 lineage; preserve status and earlier
evidence. The handoff stays non-executable.

The implementation cap remains **1,800 wall seconds measured before inspection**,
including aggregate and review, with **180 seconds reserved for evidence** and
at most **eight CPU workers including helper/native threads**. Serial suites and
one-thread helper pools remain required. On failure/interruption/exhaustion,
retain actual evidence and incomplete acceptance without expanding the repair.

F7-2's declarations/typed receipt guards, remaining F6 helper gaps and all open
Plan 036 package requirements stay binding acceptance gates outside this narrow
implementation scope. A passing repaired aggregate alone cannot complete overall
acceptance or authorize live admission. Keep both
`implementation_acceptance_complete=false` and `ready_for_live_admission=false`
while those gates remain open; S1-2 and S1-3 remain unmet.

The read-only PLAN audit matches all 72 source records, 38 frozen records,
40 prior-loop records, six transitions, five aggregate evidence files and
69 preexisting loop snapshot records, plus references/status/index. The tracked
diff matches assessment-012. The ledger remains **447 valid chained events /
332,437 bytes**, SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
head `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
GPU accounting remains 30 attempts / 4,374.044265462899 seconds / zero reserved;
all other resource totals match. No active reservation or S1 recovery event;
failures 250/255 and R-S skip 256 remain. Historical P31-5, status-byte and timing
caveats remain unresolved.

**No production ledger mutation during implementation, validation, review or
preparation, even after a pass.** Use disposable test ledgers only. No production
controller dry run, authorization, registration or reservation; no GPU/device
probe, model run, setup/download/smoke job, staging, commit or delegation.

Only separate later DO authority after all gates and fresh checks may consider
`S1-calibration-recovery-001`: **one attempt, one 3,600-GPU-second cap** with
positive `min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)` allocation
and all cleanup/finalization inside it. Reservation consumes the identity even
without launch. Existing resource ceilings remain; no retries or resets.
No reconstruction, R-S or scientific aggregation/report rerun. Reconstruction
requires separate later authorization after calibration review.

This PLAN stage creates only Plan 038 and this link. No source edits, tests,
GPU/model/device operations, ledger mutations, staging, commits or delegation.
No `prompts` content was read. Neither document grants live authority or asserts
fresh validation success.
