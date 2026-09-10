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

Current stage: Plan 027 is complete. All six dense trajectories reached exactly
50,000 updates (300,000 production updates), retained the required 5k/10k/20k/
30k/50k checkpoints, passed complete saved-state restoration, and passed 13
reload probes per endpoint. The [final analysis](analysis-final/artifact-index.json)
contains 60 complete result records with no missing results. The [final audit](audit-final/trajectories.json)
reports six trajectories, one-job concurrency,
and no failures. The [50k held-out visual validation](visual-validation-050000.json)
passes all 48 PNG panels and 12 videos. Trained diagnostics cover both endpoints
for all six trajectories; fixed diagnostic panels are under
`.local/basketball-dense-training/diagnostic-panels/`. The measured storage and
qualified estimate are recorded in [storage-final.json](storage-final.json).

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

[Cropped seed-1 first endpoint](endpoint-cropped-seed1-005000.json).

[Coarse seed-2 first endpoint](endpoint-coarse-seed2-005000.json).

[Cropped seed-2 first endpoint](endpoint-cropped-seed2-005000.json).

[Coarse seed-0 final endpoint](endpoint-coarse-seed0-050000.json).

[Cropped seed-0 final endpoint](endpoint-cropped-seed0-050000.json).

[Coarse seed-1 final endpoint](endpoint-coarse-seed1-050000.json).

[Cropped seed-1 final endpoint](endpoint-cropped-seed1-050000.json).

[Coarse seed-2 final endpoint](endpoint-coarse-seed2-050000.json).

[Cropped seed-2 final endpoint](endpoint-cropped-seed2-050000.json).

[Final analysis](analysis-final/artifact-index.json).

[Final audit](audit-final/trajectories.json).

[Final visual validation](visual-validation-050000.json).

[Final storage measurement](storage-final.json).
