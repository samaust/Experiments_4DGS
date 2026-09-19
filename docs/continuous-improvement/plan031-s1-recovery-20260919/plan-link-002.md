# PLAN 002 — S1 CPU corrections and recovery preparation

Created [Plan 033](../../../plans/plan_033.md), the next unused plan, for the
[objective](objective.md), following [review-002](review-002.md),
[assessment-002](assessment-002.json), [Plan 032](../../../plans/plan_032.md) and
the preserved [failed validation](s1-recovery-validation-001.json).

The plan maps F2-0–F2-6 to S1-1..S1-4: correct the malformed-label fixture,
complete real amendment-aware lifecycle/first-result CPU tests and their required
guard/evidence fixes, issue fresh immutable validation and implementation review,
and prepare a non-executable recovery handoff. Preserve baseline-001 through an
explicit correction manifest; retain failed validation-001 as history.

The later CPU implementation pass is bounded to 1,800 wall seconds and eight
workers, with no production ledger mutation, live admission or GPU execution.
The future recovery remains exactly one calibration attempt of at most 3,600 GPU
seconds within the existing cumulative/resource ceilings, pending review and
applicable execution-stage authority. No reconstruction or report/aggregate rerun.
S1-2's live admission and S1-3's actual outcome remain pending.

This PLAN stage creates only Plan 033 and this link. No implementation edits,
test execution, GPU jobs, ledger writes, staging, commits or delegation. Plans
031/032, existing source/index and evidence remain unchanged; `prompts` was not
read. The read-only ledger audit verified 447 chained events, no active attempt
and no S1 recovery events, with the existing ledger hash unchanged.
