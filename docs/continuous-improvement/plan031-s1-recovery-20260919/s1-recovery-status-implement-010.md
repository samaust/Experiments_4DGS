# S1 recovery — iteration 10 IMPLEMENT

Implementing [Plan040](../../../plans/plan_040.md): local row/result numerical envelopes and direct-script lookup compatibility. Objective: [objective.md](objective.md). Latest criteria: [assessment-021-plan.json](assessment-021-plan.json). Authority: [implementation-dispatch-010.json](implementation-dispatch-010.json).

New allocation: 1800 wall seconds from before inspection; final180 seconds for evidence; at most3 focused120-second runs and2 aggregate300-second runs with justified repetition only, all within total. Eight CPU workers maximum, thread pools one. Six selected script children run serially inside collected tests, each10 seconds plus2 cleanup. Zero GPU/model/production/setup/download operations.

S1-1/S1-4 retain support; S1-2/S1-3 and other recovery gates remain open. Live admission is not ready. Status frozen during implementation; PLAN bytes preserved in s1-recovery-status-before-implement-010.md.
