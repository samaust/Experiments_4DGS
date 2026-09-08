# Timing and runtime milestone

Local checkpoint following Plan 025; this is not completion of Plan 024.

`scripts/sync_timing.py` implements the versioned `camera-timing/v1` interchange,
nullable disconnected offsets, explicit seconds/sign convention, supported source
intervals, shared normalization, gauge conversion and union temporal exclusions.
Its robust graph solver reports components, bridges and edge residuals without
inventing uncertainty for unverified cameras. The reference gauge is fixed;
rebasing unknown marginal uncertainty does not invent a covariance model.

Validation in the isolated runtime:

```text
python -m pytest -q -p no:cacheprovider tests/test_sync_timing.py tests/test_sync_motion_fixtures.py
13 passed in 0.60s
```

The container used no network or GPU and mounted only scripts/tests read-only.
The [analytic results](analytic-fixtures.json) were generated separately with
`scripts/sync_motion_fixtures.py`. They use independent continuous 3D trajectories
sampled at physical camera times and projected through a known pinhole stereo
pair. The estimator interpolates observations; ground truth is analytic, not
interpolated video. Adverse cases cover occlusion, wrong correspondences, dropped
frames, stationary motion, motion along epipolar lines, rate mismatch and
disconnected camera graphs. These are interface/identifiability controls, not
benchmarks of either learned baseline or evidence of physical subframe accuracy
on Basketball. A bridge can have zero fitted residual while its timing is wrong.

The original VisualSync `estimate_global_offsets_robust` was imported in an
offline CPU container and tested with one 13-ms edge and an isolated camera:
relative sign agrees and the isolated camera remains NaN. The external result
must be adapted to nullable JSON and the fixed Basketball reference before use.
No claim about the full VisualSync pipeline follows from this component check.

MultiViewUnsynch's `reconstruction.common.Scene` and synchronization module import
in the isolated runtime. Upstream identity-comparison SyntaxWarnings are retained;
no trajectory reconstruction has run. Input requires single-target detections.

Runtime construction uses a pinned upstream image digest in
`configs/sync-pivot/Dockerfile`. The resolved [dependency lock](runtime-requirements.lock)
includes transitive versions. The built runtime config/image ID is
`sha256:d338675d51d3a7e281caa34db2c809274c4b572e5595b1bb914489adf17448a9`.
Python is 3.11 in this image; Torch 2.5.1/CUDA 12.4 follows VisualSync's documented
Torch/CUDA versions. This is an isolated compatibility choice, not an exact
reproduction of its documented Python 3.10 environment. No repository environment
or host driver changed. Sync-NeRF requires an additional tiny-cuda-nn build;
its setup is tracked separately in [setup accounting](setup-accounting.json).

Basketball adapters, full model reloads, rendering/metric validation, paper/code
matrix and real-data pilots remain unfinished. No final timing window was opened.

## Reconstruction evaluation preparation

Native training adapters and initial frozen protocol are committed in `79b2cf0`.
A prelaunch provenance supplement pins the consumed native model/optimizer files.
The [evaluation protocol v2](evaluation-protocol-v2.json) retains the earlier
protocol and explains the pre-prediction addition of foreground-pixel PSNR/MAE.
Mask preparation covers all 350 evaluation images; no motion region is empty.
The median bounding rectangle covers 81.37% of the image while the median motion
mask covers 3.37%, so the crop and foreground-only results must remain distinct.
The held-out camera0/10/20/30 frame22 overlay was visually inspected; it largely
follows people and includes some display/sideline motion. It is not semantic truth.

CPU validation: 20 scene/timing/fixture/mask tests passed, and four seed/block
summary tests passed including exact paired effects and mismatched-checkpoint
rejection. Native environment package inventories and source-license identities
are retained. Fresh GPU model reload and rendered metrics are still pending.
