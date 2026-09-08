# Iteration 002 planning handoff

- Plan: [Plan 018 — Diagnose the growing v10 Basketball trajectories](../../../plans/plan_018.md).
- Basis: [review](iteration-002-recommendations.md), [latest assessment](iteration-002-assessment-01-review.md), and unchanged [objective](objective.md).
- Planning inspected saved JSON/source only, confirmed all twelve callback multiplier arrays and last-callback/returned-state matches, and specified evaluation-only problem reconstruction to avoid constructor initialization. No scientific evaluation, derivative reconstruction, optimizer, GPU, training or download was run.
- Proposed execution request: one 30-minute implementation phase including a 120-second cumulative numerical cap; one single-thread numerical worker and at most two CPU processes; zero optimizer attempts; at most 600 primary plus 600 independent finite-state slots, 24+24 analytical limits, 1,200 residual/Jacobian entries and 1,200 depth/Jacobian entries overall. No resource transfer, adaptive probes or rerun.
- Readiness: decision-complete scope, fixed identities, acceptance, verification, deadlines and stop behavior are saved. Execution is **not authorized** by this plan or the user's resume; parent must obtain applicable execution authorization before implementation dispatch.
- Acceptance A1–A4 concerns a complete bounded diagnosis with independently verified explicit unknowns. It does not attain the main objective or qualify Basketball timing. All historical flags and downstream scientific gates remain unchanged.
- Planner changed only this link and the new plan; parent owns assessment, status and local planning commit.
