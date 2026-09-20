# S1 recovery — iteration 11 IMPLEMENT

Implementing [Plan 041](../../../plans/plan_041.md): trusted first-result reservation clock and publication/advancement barriers. Objective: [objective.md](objective.md). Criteria: [assessment-024-plan.json](assessment-024-plan.json). Dispatch: [implementation-dispatch-011.json](implementation-dispatch-011.json).

New allocation: 2400 seconds before inspection through handoff; execution cutoff 2160 seconds and final 240 for evidence. At most three focused runs of 120 seconds and two aggregates of 300 seconds with justified repetition only, within total. Eight CPU workers maximum, one-thread pools; existing bounded script children remain inside collected invocations. Zero GPU/model/production/setup/download operations.

S1-1/S1-4 retain support; S1-2/S1-3 and remaining recovery gates are open. Live admission is not ready. Status frozen during implementation; previous PLAN bytes saved in s1-recovery-status-before-implement-011.md.
