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

## Full native qualification

Both frozen initializers completed two native updates, saved complete state,
reloaded in fresh worker processes, and advanced to exactly update three. Both
`restore-validation.json` records pass with no differences across saved native
parameters, optimizers, schedulers, sampler, RNG, and method state. These six
updates total are validation work, not production consumption.

A resource-summary property-access error occurred after all four GPU jobs had
completed successfully. It was corrected and the CPU-only projection rerun;
no GPU validation was repeated. A regression test now exercises the measured
filesystem projection and checkpoint corruption rejection. The qualified
projection also includes later native strategy buffers and the larger memory
peak from each save/reload pair.

Full-data deterministic fusion checks pass for both recipes; see
[fusion coarse](fusion-determinism-coarse.json) and
[fusion cropped](fusion-determinism-cropped.json). The original coarse assembly
was not timed independently; its separately charged CPU repeat took 26.59 seconds.
The cropped record includes original assembly and validation-repeat timings.

Four existing temporal-geometry tests and one person-crop mapping test pass.

The reusable visual verifier passed on all 48 first-phase full/crop PNGs and all
12 videos; see [all-panel evidence](visual-validation-all-panels-005000.json).
Every image column matches its original source pixels exactly. A temporary copy
with one changed image pixel and a refreshed artifact hash was rejected with
`panel source pixels differ`, confirming the comparison is independent of the
panel's own hash. The temporary test did not alter retained visual artifacts.
