# Plan 027 initial implementation validation

The historical Plan 026 adapters and evidence remain unchanged. New adapters use
`.local/basketball-dense-training/` and a separate ledger with hash links to
historical accounting and the saved specification.

- All 30 historical checkpoint, render-index, and metric-file hashes passed;
  see [baseline reuse](baseline-reuse.json).
- Shared pinned ViPE masks completed for 30 training cameras and all nine
  keyframe/successor pairs (540 masks), with fresh tracker state per pair.
- The common normalized voxel width is `0.0060388131825168485`, calculated from
  unique historical sparse static points before constructing either initializer.
  The immutable machine record is `.local/basketball-dense-training/voxel-width.json`.
- Six fusion unit/integration tests pass, covering deterministic medians,
  observation mappings, foreground temporal separation, zero unsupported/static
  velocities, excluded times, corrupted archives, and cross-recipe rejection.
- Four historical study training tests and three split/supervisor tests pass.
- New adapters compile. Full native save/reload and production resource checks
  remain pending full cloud generation; production training has not started.

Commands use `.local/envs/freetimegs/bin/python -m unittest discover -s tests -p`
with `test_basketball_dense_fusion.py`, `test_basketball_study_train.py`, and
`test_basketball_study.py` respectively.

## Evaluation and execution adapters

Thirteen dense-related tests pass, including the new serial-order/resource-gate
tests and a synthetic 60-result report integration test. The latter verifies
four distinct cohorts despite the shared native `freetimegs` method, matched
coarse/cropped contrasts, and initialization-duration interactions. Synthetic
test outcomes are not experiment quality evidence.

New adapters retain the frozen renderer and metric worker, separate recipe
output paths, verify checkpoint/recipe bindings, and support all 30 dense
checkpoint reloads and ten recipe/checkpoint metric cohorts. The fixed visual
adapter requires twelve trajectories and five panels (ground truth plus four
arms). End-to-end GPU evaluation and visual generation remain pending.

Two additional job-accounting tests pass. They verify that failed attempts stay
charged and that overlapping, unpaired, unclosed, or cleanup-failed GPU jobs
cannot pass the final audit. The new native trajectory auditor also requires
exactly updates 1–50,000 per dense trajectory and fixed initializer point counts.
