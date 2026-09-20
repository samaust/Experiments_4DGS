# S1 recovery — iteration 13 IMPLEMENT

Implement [Plan 043](../../../plans/plan_043.md): fixed helper session, bounded startup/ownership, nonblocking transport and fresh correlated samples. Latest assessment: [assessment-030-plan.json](assessment-030-plan.json). Objective: [objective.md](objective.md).

Main compared the new CPU allocation against unchanged ceilings and recorded standing approval in implementation-dispatch-013.json. Limits: 3,600 wall seconds from agent inspection start, 3,300 execution cutoff, 300 evidence reserve; three focused120s/two aggregate300s; 24 new child scenarios per invocation, each2s+1s cleanup; eight total CPU workers and native thread values1. Zero GPU/device/model/production operations. Historical allocations are not reset.

S1-1/S1-4 remain met on reviewed evidence; S1-2/S1-3 remain unmet. Historical Plan041 strict exceptions remain preserved. Live admission is not ready. This status is frozen during implementation and has a durable snapshot; main owns commits and subsequent continuation.
