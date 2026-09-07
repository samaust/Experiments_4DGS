# Basketball calibration revision 1

Historical 33-camera record. **Current status:** the [20% camera-set rerun](basketball-intrinsic20.md)
retains 24 cameras and completes all A/B/C tests, with a remaining pose blocker
at camera 19. The historical prior and Stage A failures below are preserved. The [revised plan](../../plans/plan_005_rev1.md) is saved and
the first implementation milestone is committed. This report supersedes the
[previous recovery status](basketball-no-camera5.md); it does not claim the
remaining gated implementation or experiments are complete.

The variant remains 33 cameras, excluding physical camera 5, with 29 training
cameras and held-outs 0, 10, 20, 30. No camera was removed or threshold relaxed.

## Intrinsic constraints: eight reconstructions completed

The new runner starts from the original window-specific GeoCalib priors and
copies the existing SIFT or SIFT+RoMa database into a fresh directory. A shared
native options builder fixes the principal point during incremental mapping,
absolute-pose registration and final adjustment; the second policy also fixes
fx/fy. Runtime assertions checked fixed parameters after both mapping and final
adjustment. Parameters remain separate for each physical camera and independent
between fitting windows. No new feature extraction or dense inference was used
in Stage A.

All eight reconstructions registered all 29 training cameras, and all eight
final adjustments reported CONVERGENCE. None passed the original independent
pose gate after the unchanged single similarity alignment:

| Policy and observations | Maximum rotation | Maximum center / diameter |
| --- | ---: | ---: |
| Fixed principal point, SIFT | 2.7716 degrees | 2.2063% |
| Fixed principal point, SIFT + existing RoMa | 3.3474 degrees | 1.3603% |
| Fixed all intrinsics, SIFT | 91.0602 degrees | 30.7911% |
| Fixed all intrinsics, SIFT + existing RoMa | 90.8551 degrees | 29.7526% |
| Required maximum | 0.5 degrees | 1% |

Fixing principal points improved the prior result, but did not establish an
accepted rig. Fixing the current focal estimates made the geometry much less
stable. Fixed zoom is compatible with constant intrinsics over time, but does
not establish that those estimated intrinsic values are correct.

## Expanded observations hit the unchanged prior gate

The expansion reused all 165 original retained-camera observations and their
verified image/mask/depth artifacts, then estimated the 165 missing observations
at frames 62, 87, 99, 112 and 137. All 330 intrinsic observations were completed.
Applying the unchanged `(maximum - minimum) / median <= 0.25` check to ten
observations per camera failed for:

| Physical camera | Relative focal range |
| --- | ---: |
| 4 | 25.2414% |
| 8 | 26.5828% |
| 17 | 41.1882% |

This is variation in GeoCalib estimates, not evidence that physical zoom changed.
The adapter stopped before generating additional semantic masks when the prior
gate failed. Original representative depth maps and masks were preserved.

The automatic focus screen measured static-patch tracks on the five existing
masked timestamps for every retained camera. It found no sustained sharpness or
scale flags on that subset. All 33 full ten-frame checks are explicitly
**inconclusive**, because masks for the five new timestamps were not generated
after the prior failure. This does not confirm constant focus, and no camera was
discarded based on blur. The focus utilities include contrast-normalized local
sharpness, affine-support handling and deterministic best-observation selection;
their integration into Stage B matching remains gated.

## Budget, evidence and remaining work

The expanded GPU worker took 132.2426 seconds; the supervised ledger charged
135.3704 seconds. Cumulative calibration usage is **853.6835 / 28,800 GPU-seconds**,
leaving **27,946.3165 seconds**. Failed attempts remain charged. No additional
eight-hour allowance was activated, and no Basketball training allocation was
used or changed.

Stage A and focus screening ran on CPU. The new Stage B feature recipes,
additional RoMa inference, Stage C initialization search, pooled/held-out
validation, synchronization, initialization, preparation and training did not
run. Their prerequisites have failed. Reserved selection, final-validation and
experiment frames remain unused by this recovery.

[Machine-readable evidence](basketball-rev1-result.json) records all Stage A
commands, per-camera pose comparisons, failing prior statistics, artifact/log
hashes, focus summaries and complete GPU accounting. Local detailed artifacts
are under `.local/calibration/basketball-v1/rev1/`; `search.json` was frozen before
reconstruction. Historical status was copied to `previous-status.json` before
updating the current status pointer.

Validation: 27 Basketball tests, three calibration-budget tests and four existing
training-budget tests; native fixed-parameter assertions in all eight real runs;
evidence hashes, source membership, original-artifact reuse, documentation links,
compilation and `git diff --check`. The ViPE checkout remains unchanged, and the
original training ledger retains SHA-256
`d0b4daa1aee79361580af3a1bf8fbc597148db7775b26f169a0a1b2e6ac90957`.

Example Stage A command (each combination uses a fresh output; the evidence JSON
contains the exact eight executed commands):

```bash
.local/envs/stg-colmap/bin/python scripts/basketball_recovery.py \
  --source .local/calibration/basketball-v1/no-camera5-early \
  --priors .local/calibration/basketball-v1/no-camera5-priors/result.json \
  --output .local/calibration/basketball-v1/rev1/A-fixed-principal-sift-early \
  --frames 50 75 --policy fixed-principal
```

Further progress requires an explicit revision of the intrinsic-prior strategy
or its acceptance policy. More runtime alone does not address this blocker.
