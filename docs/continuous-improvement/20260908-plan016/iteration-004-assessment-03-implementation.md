# Iteration 004 assessment after Decimal candidate qualification

The orchestrator reread [objective](objective.md) and inspected
[implementation](iteration-004-implementation.md), [validation](iteration-004-validation.md),
[v13 decision](../../experiments/basketball-shared-timing-v13/decision.json),
[package checks](../../experiments/basketball-shared-timing-v13/package-validation.json),
[budget](../../experiments/basketball-shared-timing-v13/budget.json), and
[integration/gate map](../../experiments/basketball-shared-timing-v13-integration.md).
Local commits: `f78afee` implementation/evidence, `38ffef8` checkpoint/handoff.

| Criterion | Status | Reason and evidence |
| --- | --- | --- |
| SC-01 | not met | The candidate passes six-state arithmetic qualification only. Full evaluator and timing gates remain unmet, and acceleration cannot affect weight-zero failures. [Integration map](../../experiments/basketball-shared-timing-v13-integration.md). |
| SC-02 | met | Supported SelfCap complete-model/reload evidence remains applicable with [historical limitations](iteration-001-assessment-03-implementation.md); no new model claimed. |
| SC-03 | not met | Basketball reconstruction and measured quality/motion/speed/resource comparison remain absent. [Implementation](iteration-004-implementation.md). |
| SC-04 | met | Existing supported-profile [workflow recommendation](../../selfcap-workflow.md) remains applicable. |
| SC-05 | met | Plan 020 A1–A4 pass: fixed input/oracle/source ownership, all 42 exact-error comparisons, two fixed 12-case toy suites, complete bounded evidence and local commits. [Validation](iteration-004-validation.md). Historical v11 failures and other 57 states remain unchanged. |

Parent inspection confirms kernel_status qualified_on_six_retained_states,
42 passed/zero failed comparisons, one setup and six entries/completions,
0.12248898699181154 supervised numerical seconds and worker_stopped true.
Both toy slots are consumed. Final implementer post-commit monotonic
273265.268525092 gives 914.2315437420039 phase seconds, below 1800 and original
phase deadline. The worktree is clean and no jobs, git or permission failure remain.
No source or scientific gate changed; no training or other forbidden entries ran.

Main objective is not attained. No stop condition applies. Advance automatically
to iteration 005 fresh xhigh Review of a finite full-component integration and
evaluator qualification on actual retained v10/v11 operating states, including
weight-zero controls. The next Review/Plan must freeze concrete interfaces,
independent full-state checks and resource limits. Do not repeat this consumed
pass, enlarge the extreme ladder by default, or equate arithmetic accuracy with
optimizer qualification. All historical ceilings and criteria stay binding.
