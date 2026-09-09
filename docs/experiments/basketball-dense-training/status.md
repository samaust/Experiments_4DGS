# Plan 027 execution state

Implementation in progress under [plan 027](../../../plans/plan_027.md).
This is a fixed experiment; the continuous-improvement loop is inactive.

Authorized production allocation: six dense trajectories, 50,000 updates each
(300,000 updates total), one GPU job at a time, no time or GPU-hour ceiling.
Validation is charged separately. Production consumption: zero updates.

Current stage: full person-cropped geometry generation. Shared full-keyframe masks
and the full coarse initializer are complete; see [preparation evidence](preparation-001.json).
Coarse geometry has 7,568,463 temporal Gaussians after deterministic static fusion. Historical Plan
026 visual rejection remains unchanged. Both recipes are authorized for
experimental training with known visual defects, subject to technical validity.

Large artifacts and the new append-only ledger are under
`.local/basketball-dense-training/`. GPU host access passed after the prescribed
outside-sandbox retry. Initial free disk space was approximately 247 GB; full
initializer save/reload validation must establish production resource requirements.

Validated milestone: `669cdde` (fusion, recipe-aware training, historical hash verification).
Native full-initializer save/reload and resource qualification remain pending.
