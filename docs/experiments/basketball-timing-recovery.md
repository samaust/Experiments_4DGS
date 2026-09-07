# Basketball synchronization recovery

Status: first recovery fit blocked; declared dense RoMa stage in progress.
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
