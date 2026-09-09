# Plan 027 execution state

[Plan 027](../../../plans/plan_027.md) is active as a fixed experiment; the
continuous-improvement loop is inactive.

Both full initializers are frozen for experimental training with known visual
defects. The historical Plan 026 visual rejection remains unchanged.

- Coarse: 684,967 physical static points, 6,164,703 temporal static copies,
  1,403,760 foreground observations; 7,568,463 total Gaussians.
- Cropped: 686,740 physical static points, 6,180,660 temporal static copies,
  1,452,616 foreground observations; 7,633,276 total Gaussians.
- Both full-data fusion repeats have identical archive, mapping, and source-index hashes.
- Both native two-update saves and resumes to update three passed complete saved-state
  restoration checks. GPU training is not claimed to be bitwise reproducible.
- [Qualified resource projection](resources-qualified.json): approximately 253 GB
  remaining production retention, with approximately 432 GB available after validation.
  The user freed additional disk space before qualification.

Current stage: initialization diagnostics complete; starting all six 5,000-update endpoints
in seed order, coarse then cropped. Verified completed production milestones: both seed-0 recipes and coarse seed 1 at 5,000 updates (15,000 completed updates), each with all 350 targets and 13 reload probes passing. Cropped seed 1 is running; live consumption is recorded in loss logs. Authorized
production remains six trajectories of 50,000 updates each (300,000 total), one GPU
job at a time, with no time or GPU-hour ceiling. Validation is charged separately.

[Preparation evidence](preparation-002.json), [implementation validation](implementation-validation.md),
and [historical reuse](baseline-reuse.json) retain compact evidence. Large artifacts,
per-job logs, the linked append-only ledger, and live state are under
`.local/basketball-dense-training/`.

Milestones: `669cdde` fusion/training adapters; `80f7a75` execution and four-arm
analysis; `54773cb` trajectory and GPU-accounting audit.

Full initializer/native qualification milestone: `9f54536`.
[Initialization diagnostics](initial-diagnostics.json) retain all twelve fixed views per recipe.

[First completed dense endpoint](endpoint-coarse-seed0-005000.json).

[Cropped seed-0 first endpoint](endpoint-cropped-seed0-005000.json).

[Coarse seed-1 first endpoint](endpoint-coarse-seed1-005000.json).
