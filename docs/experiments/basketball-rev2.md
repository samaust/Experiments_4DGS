# Basketball Plan 005 revision 2 continuation

Status: provenance and camera conventions passed; scale and synchronization
remain pending. No Basketball initialization, training or evaluation has run.
The accepted [Plan 006 calibration](basketball-calibration-alternatives.md) remains
immutable, with all 34 cameras and held-outs 0, 10, 20, 30.

## Provenance and conventions

The [provenance audit](basketball-rev2/provenance.json) rehashed every source video,
the pinned calibration/profile and frozen map/anchor artifacts. All 34 videos
decoded to 250 frames at 1920×1080 and 25 fps, with unchanged timestamps.
The pinned ViPE branch/revision and clean tree passed. The static validation
consumption marker remains intact; no final static images were evaluated.

The [saved-observation reload](basketball-rev2/export-reload.json) reproduced all
79,835 saved final projections with zero error change. The scale adapter's
undistortion maps agree with native COLMAP radial projections within 0.00004 px
across a full-image sample for every camera. Output K explicitly uses (480,270)
principal points to match the unmodified pinned ViPE depth wrapper, with the
accepted per-camera focal. This half-pixel change is part of the image remap;
the immutable source K retains OpenCV (479.5,269.5) principal points.

## Frozen scale protocol

[The protocol](../../configs/basketball-rev2/scale.json) is frozen before depth
inference. Fit on training cameras at frame 100; check the frozen scale at frame
175 only if fitting passes. Generate fresh ViPE UniDepth depth on undistorted
images; older depth used other intrinsics on distorted images and is not reused.
The native ViPE checkout is unchanged. Source, extension and weight hashes must
match the earlier audited environment before inference, with offline weight reuse.
The NVIDIA catalog check found no strong match needed for this existing pipeline;
no skills were installed.

Use equal-camera median log depth/map-z ratios, a camera-cluster bootstrap and
predeclared support/consistency gates. Require at least 100 points and six image
grid cells per training camera, local log MAD ≤0.25, each camera scale within 25%
of the global value, and bootstrap relative halfwidth ≤10%. Reserved-frame scale
disagreement must be ≤10%. These new scale-specific criteria are separate from
GeoCalib prior trust and are not adjusted after inference. The bootstrap cannot
measure common monocular metric bias; no measured ground-truth metric accuracy
is claimed. Frame-100 preparation retains 424–1,049 static points per camera.

## Reproduction and accounting

Use fresh output directories for new measurements. Initial commands:

```bash
.local/envs/calibration-global/bin/python scripts/basketball_continuation_audit.py --output .local/calibration/basketball-rev2/provenance
.local/envs/calibration-global/bin/python scripts/basketball_scale.py prepare --protocol configs/basketball-rev2/scale.json --audit .local/calibration/basketball-rev2/provenance/result.json --role fit --output .local/calibration/basketball-rev2/scale-fit-inputs
```

CPU provenance/preparation does not charge GPU time. Preserve the original
calibration ledger and its 1,056.087320-second starting charge. GPU inference and
failed attempts use that ledger; the conditional downstream extension remains
unused. Plan 006's uncapped investigation is separate. Every method retains its
two-hour Basketball training allocation; no training seconds have been charged
by this continuation.

Verification: two provenance/split rejection tests and four scale/distortion
tests pass, including synthetic known scale with outliers, cross-camera bias,
reserved-frame drift, support/leakage and nonfinite rejection. Synchronization,
shared preprocessing and method regression checks remain later gates under
[revision 2](../../plans/plan_005_rev2.md).
