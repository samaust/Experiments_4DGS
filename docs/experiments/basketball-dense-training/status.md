# Plan 027 execution state

Implementation in progress under [plan 027](../../../plans/plan_027.md).
This is a fixed experiment; the continuous-improvement loop is inactive.

Authorized production allocation: six dense trajectories, 50,000 updates each
(300,000 updates total), one GPU job at a time, no time or GPU-hour ceiling.
Validation is charged separately. Production consumption: zero updates.

Initial stage: shared full-keyframe masks, followed by both measured cloud recipes
and deterministic static fusion. No initializer is frozen yet. Historical Plan
026 visual rejection remains unchanged. Both recipes are authorized for
experimental training with known visual defects, subject to technical validity.

Large artifacts and the new append-only ledger are under
`.local/basketball-dense-training/`. GPU host access passed after the prescribed
outside-sandbox retry. Initial free disk space was approximately 247 GB; full
initializer save/reload validation must establish production resource requirements.
