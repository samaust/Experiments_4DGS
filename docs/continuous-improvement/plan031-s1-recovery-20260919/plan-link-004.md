# PLAN 004 — Minimum S1 admission and publication closure

Created [Plan 035](../../../plans/plan_035.md) for iteration 4 from the
[objective](objective.md), [review-004](review-004.md),
[assessment-006](assessment-006.json), [Plan 034](../../../plans/plan_034.md),
[validation-003](s1-recovery-validation-003.json) and
[implementation-review-002](s1-recovery-implementation-review-002.md).

The recorded aggregate passed 135 methods and 79 subtests, but validation-003
remains incomplete and live admission remains closed. Plan 035 maps all remaining
L1/L2/A1–A4/P1/P2/V1 criteria to the minimum source fixes and collected CPU cases:
exact `baseline_correction` bindings; real controller lifecycle and ordered
event guards; boundary mutations/races/continuation/replay; numerical/runtime/
first-result adversarial coverage; robust minimal failure and partial evidence;
charged, externally monitored acceptance/publication/cleanup; and exact required
subtest identities with adversarial receipt checks.

Implementation is CPU-only, capped at 1,800 wall seconds from inspection and
eight workers, with disposable ledgers only and no production ledger mutation.
A fresh nine-suite aggregate on final sources, successor correction, immutable
validation, review and non-executable preparation are required. Old evidence
remains unchanged. CPU completion ends at review/preparation; it does not create
production authority or establish S1-2/S1-3 completion.

Only a later authorized execution stage, after every criterion and fresh live
gate passes, may admit `S1-calibration-recovery-001`: one attempt capped at
3,600 GPU seconds within the existing 93,600-second cumulative ceiling.
Acceptance, publication and cleanup remain inside the allocation; reservation
consumes the identity even without launch. No reconstruction, R-S or scientific
aggregate/report rerun. Reconstruction requires separate later authorization
after calibration review.

This PLAN stage creates only Plan 035 and this link. No source edits, tests,
GPU/model/device work, production controller calls, ledger writes, staging,
commits or delegation occurred; `prompts` was not read. The read-only audit
verified all 70 source/config/test records, 38 frozen scientific records and
447 chained ledger events, with no active reservation or S1 recovery event.
The ledger remains 332,437 bytes, SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`.
Historical GPU use remains 4,374.044265462899 seconds across 30 attempts, zero
reserved. Current bookkeeping transitions match status; historical timing and
P31-5 limitations remain. Source, index, prior plans and protected evidence
remain unchanged.
