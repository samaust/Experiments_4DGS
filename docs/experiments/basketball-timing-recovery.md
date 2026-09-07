# Basketball synchronization recovery

Status: both recovery fits blocked; complementary-edge diagnostic also fails.
The user authorized autonomous choice of recovery solutions and continuation
until completion or an evidenced blocker. The [accepted calibration and scale](basketball-rev2.md)
remain unchanged. Timing selection/final validation and downstream experiments
have not run.

## Declared recovery protocol

[The recovery protocol](../../configs/basketball-rev2/timing-recovery.json) was
frozen before new fits. All recovery uses original frames 50–149; 150–199 remain
for timing selection and 200–249 for a separately frozen final timing check.
Reverified calibration/profile/frozen-artifact and all 34 source-video hashes.
The original downstream allowance at entry is 27,719.362447 GPU seconds; the
conditional extension and all Basketball training allocations remain unused.

The first stage uses the saved hash-bound SIFT tracks with a temporal score that
removes one constant signed epipolar residual per track. This nuisance offset
models spatial correspondence bias and never changes camera parameters. It
requires nonlinear motion to identify timing: constant-velocity ambiguity is an
explicit synthetic rejection case. Every lag uses the same observed reference
samples, valid over the entire ±25-frame search. Fractional refinement is 0.05
frame, bootstrap halfwidth remains ≤0.25 frame, and signed graph cycles must
close within 0.25 frame. Original spatial epipolar residuals are also checked.

Pairs are selected from eight nearest geometric neighbors with at least 100
commonly visible static map points, producing 146 candidate edges. Numerical
camera-ID adjacency does not select the graph. Graph failures do not exclude
cameras. The first fitting-eligible stage would be frozen for reserved checks;
failed final validation cannot choose another stage.

The second stage uses the unchanged EDGS-pinned RoMa checkout
`370117431ffc5dc000fb46f6e581b74bdb2c3ff8` and its already verified indoor/DINOv2
weights. It matches camera A/frame 100 to camera B/frames 75, 100 and 125,
requires ≥0.95 confidence and dynamic support at both endpoints, and deduplicates
source cells before looking at timing. RoMa's continuous half-integer pixel
coordinates explicitly convert to OpenCV integer centers by subtracting 0.5.
Bidirectional forward/backward-checked optical flow tracks the resulting seeds
strictly within fitting frames. It uses the same temporal scoring and acceptance
gates. Equal seed-frame numbers do not imply zero offsets.

This is a bounded two-stage recovery. If both fail, retain evidence and block
reserved timing and downstream execution rather than relaxing thresholds or
starting an unbounded correspondence search.

## First-stage result

The [SIFT temporal fit](basketball-timing-recovery/sift-fit.json) passes **67/146
edges**, but 26 cameras remain disconnected from camera 1. Rejections include
63 uncertainty failures, 16 support failures and two original spatial-support
failures (categories can overlap). CPU fit wall time was 19.105 seconds. No GPU
inference or training time was charged for this stage. The change improves the
number of individually usable edges but does not establish full-rig timing.

Five new tests pass: fractional-lag recovery with constant spatial bias,
constant-velocity ambiguity rejection, fixed search-support/no extrapolation,
confidence-only deduplication across target-time hypotheses, and bidirectional
optical-flow frame identity. Existing accepted artifacts and old timing adapters
are preserved. Dense-stage results and required report updates follow its gate.

## Dense-stage outcome

The [RoMa temporal fit](basketball-timing-recovery/roma-fit.json) passes **0/146
edges**. All **438 matcher calls** completed on the required host GPU runtime.
Only **355** confidence-filtered, source-cell-deduplicated dynamic seeds remained;
forward/backward tracking retained **252 camera-side trajectories** (two endpoints
are required per cross-camera track). **145 pairs fail full-search track support**;
the one remaining supported pair fails the unchanged timing-uncertainty gate.
This corrects the preliminary description that every pair lacked support: one
had enough tracks, but none passed all gates.

The inference worker took 55.111574 seconds, with 2,746,998,784 / 3,361,734,656
peak allocated/reserved bytes. The supervised attempt charged **56.904159 GPU
seconds**, including startup/provenance checks, and completed without retries.
Dense tracking and scoring used CPU, taking 20.234250 and 0.333458 seconds.
These are local measurements of this pinned indoor matcher and declared dynamic
support policy, not evidence that synchronization is impossible for the dataset.

## Complementary fitting diagnostic

The [fixed-priority compatibility policy](../../configs/basketball-rev2/timing-complementary.json)
was declared before testing the union: prefer an already-passing temporal-bias
edge, otherwise an already-passing original absolute-epipolar edge. It cannot
choose by offset value or prune by cycle residual. This additional read-only
fitting diagnostic costs no GPU time and changes no acceptance threshold.

[The combined graph](basketball-timing-recovery/complementary.json) contains **71
passing edges** and reaches **33 cameras** from camera 1. **Camera 14 remains
disconnected**. The [connected-component diagnostic](basketball-timing-recovery/component-cycles.json)
also finds four bridges without cycle support: **7–9, 8–9, 12–13 and 13–15**.
That diagnostic does not authorize a reduced-camera protocol or export offsets;
all 34 physical cameras remain required. Even the connected component cannot
supply the required independently checked cycle graph.

The tested approaches therefore stop at a concrete synchronization blocker.
Calibration and scale remain accepted, but **no full-rig offsets**, timing
selection, timing final validation, 1,700-image downstream preparation, Gaussian
initialization, training or evaluation are produced. The static final-validation
marker is intact. A different future correspondence/uncertainty protocol would
still require fitting evidence and independently frozen reserved timing checks;
neither zero offsets nor the partial graph can substitute for those gates.

## Provenance, budgets and verification

[The evidence inventory](basketball-timing-recovery/evidence.json) records every
seed-file and track-file hash, source/configuration/result hashes, exact GPU
command, resources and test logs. It verifies all immutable upstream artifacts.
The original calibration/downstream ledger now totals **1,137.541712 seconds**,
leaving **27,662.458288 seconds**. The conditional extension is unused; training
charges remain zero and the original two-hour allocation per method is intact.
MoE-GS and FreeTimeGS++ retain their independent implementation blockers.

**64 Basketball tests, seven budget tests and three SelfCap initialization
regressions pass**. Additional compatibility tests enforce fixed source priority
and reject reserved-role or changed-calibration inputs. Local documentation
links, JSON artifacts, frozen hashes, command syntax and `git diff --check` pass.
No existing SelfCap adapter/checkpoint or accepted static calibration was changed.

Executed commands use fresh outputs and preserve failures:

```bash
.local/envs/calibration-global/bin/python scripts/basketball_timing_recovery.py freeze --protocol configs/basketball-rev2/timing-recovery.json --audit .local/calibration/basketball-rev2/provenance/result.json --output .local/calibration/basketball-rev2/timing-recovery/frozen
.local/envs/calibration-global/bin/python scripts/basketball_timing_recovery.py fit --protocol .local/calibration/basketball-rev2/timing-recovery/frozen/protocol.json --tracks .local/calibration/basketball-rev2/timing-fit-tracks-precise --stage sift-temporal-bias --output .local/calibration/basketball-rev2/timing-recovery/sift-fit.json
python3 scripts/calibration_budget.py --ledger .local/calibration/basketball-v1/gpu-ledger.json --seconds 1800 --log .local/calibration/basketball-rev2/timing-recovery/roma-infer.log -- .local/envs/roma/bin/python scripts/basketball_timing_roma.py infer --protocol .local/calibration/basketball-rev2/timing-recovery/frozen/protocol.json --roma .local/RoMa-edgs --weights .local/weights/roma-edgs --output .local/calibration/basketball-rev2/timing-recovery/roma-seeds
.local/envs/calibration-global/bin/python scripts/basketball_timing_roma.py track --protocol .local/calibration/basketball-rev2/timing-recovery/frozen/protocol.json --audit .local/calibration/basketball-rev2/provenance/result.json --seeds .local/calibration/basketball-rev2/timing-recovery/roma-seeds --output .local/calibration/basketball-rev2/timing-recovery/roma-tracks
.local/envs/calibration-global/bin/python scripts/basketball_timing_recovery.py fit --protocol .local/calibration/basketball-rev2/timing-recovery/frozen/protocol.json --tracks .local/calibration/basketball-rev2/timing-recovery/roma-tracks --stage roma-temporal-bias --output .local/calibration/basketball-rev2/timing-recovery/roma-fit.json
.local/envs/calibration-global/bin/python scripts/basketball_timing_complementary.py --protocol configs/basketball-rev2/timing-complementary.json --temporal .local/calibration/basketball-rev2/timing-recovery/sift-fit.json --absolute .local/calibration/basketball-rev2/timing-fit-precise.json --output .local/calibration/basketball-rev2/timing-recovery/complementary.json
.local/envs/calibration-global/bin/python scripts/basketball_timing_recovery_package.py --workspace .local/calibration/basketball-rev2/timing-recovery --output docs/experiments/basketball-timing-recovery
```

Each fitting/compatibility command returns exit code 1 for its documented gate
failure. This is an experimental rejection, not a sandbox or permission error.
