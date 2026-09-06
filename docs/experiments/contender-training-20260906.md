# Plan 004 training integration — 2026-09-06

STG Lite and Full now execute real SelfCap optimization steps through the
native upstream training loop. These are deliberately short integration runs,
not completed contender experiments or useful quality comparisons.

## Implementation

`scripts/train-stg-manifest.py` supplies lazy manifest cameras and the audited
5,077-point training-only midpoint cloud to the pinned upstream trainer.
`scripts/stg_train_source.py` rejects unexpected upstream source hashes and
saves the adapted source in each run. Loss, batch-gradient accumulation,
densification and EMS remain upstream code. Adaptations are explicit:

- Group camera batches by source frame; use each camera's corrected time.
- Keep camera names stable across frames for upstream EMS dictionaries.
- Use two-entry CPU-image and GPU-camera caches at unchanged resolution.
- Initialize point times at the mean corrected training-camera midpoint time.
- Use upstream Techni-style densification mode 3, avoiding the N3D-specific
  world-z=4.5 floor cutoff in SelfCap's supplied coordinates.
- Use a three-channel Lite background and nine-channel Full background.
- Use Full's `sandwich` decoder; retain upstream optimizer defaults and seed 0.
- Perform the final iteration's optimizer update before saving a resumable state.
- Save complete state every 60 seconds and at requested stop boundaries.

The central ledger is `.local/runs/plan-004-training-budget.json`.
`training_supervisor.py` supplies an early checkpoint deadline, sends SIGTERM
with 30 seconds left, and SIGKILL to the worker process group with two seconds
left if necessary. Linux parent-death signaling protects the worker if its
supervisor dies. Synthetic process tests cover graceful shutdown, forced
termination, normal completion and failure. This is not hard-real-time
scheduling: overruns are detected and recorded rather than hidden.

## Executed runs

All paths below are under `.local/runs/`:

| Run | Completed iteration | Supervisor wall seconds |
| --- | ---: | ---: |
| `stg-lite-selfcap-integration-20260906` | 2 | 8.424811 |
| `stg-lite-selfcap-resume-20260906` | 4, resumed from 2 | 8.453392 |
| `stg-lite-selfcap-continuous-20260906` | 4, uninterrupted control | 9.135696 |
| `stg-full-selfcap-integration-20260906` | 2 | 9.097009 |
| `stg-full-selfcap-resume-20260906` | 4, resumed from 2 | 8.780564 |

Every run exited successfully, saved `checkpoint.pt`, and exported final PLY
state; Full additionally exported the decoder sidecar. No forced kill was
needed. Each run records source/input hashes, actual training configuration,
losses, point counts, framework memory peaks and incomplete-training status.
Ledger charges include surrounding supervisor overhead: Lite 26.031233 seconds,
Full 17.887226 seconds. They are deducted from their respective 7,200-second
SelfCap allocations. These numbers do not consume another method's budget.

Lite's uninterrupted and resumed logged step-3 loss both equal
0.2538366913795471. At step 4 they are 0.23876407742500305 and
0.2387639582157135. The models are **not bit-exact**: maximum parameter absolute
differences include xyz 1.4305e-5, scaling 0.00129795 and rotation 0.00653227.
The cause has not been isolated; do not attribute it definitively to CUDA
atomic-order nondeterminism or claim end-to-end exact resume. Synthetic
optimizer-only resume remains exact. Full fresh-process batched resumption
also exercised the repaired decoder-gradient-cache initialization.

## Renderer integration

`scripts/render-stg-manifest.py` rendered Full's iteration-4 checkpoint into
`stg-full-selfcap-render-20260906`: all 60 held-out PNGs at 1890×1061, the shared
20-pose sweep, checkpoint/manifest hashes and explicit camera/time metadata.
The no-grad native training rasterizer benchmark used ten warmups and 100
synchronized timed renders, measuring 302.266 FPS at frame 4150. The model has
only 5,077 points and four optimization steps: **this is not a meaningful
trained-method throughput comparison**. Network isolation was not enforced;
the fresh-process render does not satisfy the offline-reload acceptance gate.

## Remaining gates

Before extending these runs, validate densification and EMS, audit sparse-cloud
coverage and moving-region synchronization, investigate resume differences,
and complete offline reload checks. The two-step tests did not reach any
densification or EMS threshold. Source inspection also found an apparent Lite
EMS call/signature mismatch. **Correction after further inspection:** Lite's
`densification_postfix()` accepts `dummy=None`, so the extra temporal-feature
argument is supported and this is not a blocker. Both models' zero-initialized
EMS rotations were subsequently shown to cause nonfinite positions during
splitting; see the tracked `stg-ems-quaternion.patch` and growth-validation
record. The earlier mismatch claim is withdrawn.

Basketball calibration and the other contender adapters remain unfinished.
No quality ranking, held-out metric comparison, artifact assessment or full
two-hour training result is claimed by this record.
