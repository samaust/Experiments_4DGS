# S1 recovery — iteration 12 IMPLEMENT

Implementing [Plan 042](../../../plans/plan_042.md): bounded exact-text declaration parse reuse with fresh file reads and defensive copies. Objective: [objective.md](objective.md). Criteria: [assessment-027-plan.json](assessment-027-plan.json). Dispatch: [implementation-dispatch-012.json](implementation-dispatch-012.json).

New allocation: 1800 seconds from before inspection; cutoff 1620 and final 180 for evidence. At most three focused runs of 120 seconds and two aggregates of 300 seconds, with justified repeats only. Durable launch note must succeed before every invocation. Eight CPU workers maximum, all four thread pools one, existing bounded script children inside collected tests. Zero GPU/model/production/setup/download operations.

Prior technical milestones retain support, with Plan041 historical exceptions preserved. S1-1/S1-4 supported; S1-2/S1-3 remain unmet. Live admission is not ready. Status frozen with durable snapshot s1-recovery-status-implement-012.md.
