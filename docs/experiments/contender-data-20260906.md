# Plan 004 data preparation — 2026-09-06

This record describes the earlier data/compatibility stages. The later
[training integration record](contender-training-20260906.md) supersedes its
not-started training and missing-supervisor statuses.

SelfCap source revision: `9ab7e2ce156f7e9f4e09b50a85599fd11753296a`.
Basketball source revision: `8592b0ddd27938e2c12dbd592fca2ecca54dec38`.
Both are recorded in the local Hugging Face download metadata and tracked
profile files. Basketball DG SHA-256:
`ab7d7a11f92eeb8a5103d0249124c3db62bf015b0fed39d92ab0dd05dca8d3f7`.
The DG archive contains 34 videos (0–33) and no calibration. Camera 0 probes as
1920×1080, 25 FPS, 250 frames. The profile has been corrected accordingly.

## SelfCap processing

`scripts/prepare-selfcap.py` uses native COLMAP through pycolmap 4.2.0,
`blank_pixels=0`, then OpenCV INTER_AREA half-resolution resizing. It stores
world-to-camera transforms, centers, source distortion, processed intrinsics,
source-video hashes, and per-image timestamps and hashes. The calibration-only
run is `.local/data/selfcap/dance1-calibration-20260906/manifest.json`.
Full output location: `.local/data/selfcap/dance1-processed-20260906/`.
Only a completed run writes `manifest.json` with status `prepared`.
The full run completed and `verify-prepared-scene.py` passed: 1,440 images,
1,380 training images, 60 held-out images, and 20 sweep poses. Verification
checked every image hash and dimension, rotations/centers, per-camera corrected
timestamps, frame membership, held-out exclusions, and sweep endpoints.

The common time domain starts at 68.65473750854532 seconds and spans
1.0247243251651525 seconds, including every camera's corrected samples.
All source frame IDs 4120–4179 are retained. Fractional offsets are not rounded
to frames or clamped. Training adapters must consume this mapping explicitly.
Per-camera time correction is metadata; visual cross-camera synchronization
has not yet been established by a reprojection test.

Held-out camera 0015 produces 1890×1061 images. Output dimensions vary slightly
between cameras because COLMAP selects blank-free intrinsics before resizing.
Nearest training camera: 0014. The 20-pose path interpolates camera centers
linearly and rotations with SLERP at held-out frame 4150, using held-out
intrinsics throughout. Supplied point clouds remain excluded from initialization
because their held-out image provenance has not been audited.

The seek to source frame 4120 for camera 0000 was checked against the earlier
FFmpeg original-resolution PNG: maximum absolute pixel difference zero.
Processed held-out start/middle/end inspection:
`.local/data/selfcap/dance1-calibration-20260906/processed-camera0015.png`.
Static bookcase detail is clear, with substantial hair and hand motion blur at
the middle frame. No quantitative calibration accuracy is inferred from this
sheet. Source compression and motion blur are part of the evaluation targets.

Basketball inspection extracts frames 0, 25, 49 from cameras 0, 10, 20, 30,
4, 12, 21, 29 into `.local/data/vru-basketball/inspection-20260906`.
`test-camera0.png` shows recognizable player/ball motion and stable court
markings. Missing calibration prevents matched model evaluation at this stage.

## Renderer and evaluator checks

The STG Lite helper now implements ten warmup renders followed by 100 timed,
CUDA-synchronized renders, excluding loading/saving/encoding. The existing
1352×1014 sear_steak preview measured 658.625 FPS in this run. Evidence:
`.local/runs/stg-benchmark-20260906/preview.json`. CPU SelfCap preprocessing ran
concurrently; this is not a matched-scene or full-paper performance claim.
All three saved images still match the historical preview byte-for-byte.

Shared evaluator identity check including LPIPS-Alex passed: PSNR infinity,
SSIM 1, LPIPS-Alex 0. Evidence:
`.local/runs/stg-smoke-20260906/identity-lpips.json`. Eleven automated tests
pass, including deliberately darkened-image PSNR/SSIM checks. LPIPS used the
existing AlexNet cache on CPU; model GPU rendering was tested separately.

## Training-only initialization and checkpoint groundwork

`scripts/initialize-selfcap.py` completed CPU SIFT extraction, exhaustive
matching, and fixed-calibration triangulation at source frame 4150. Only the
23 training cameras entered the database; camera 0015 was excluded. The run
produced 5,077 points with mean reprojection error 0.5190233951 pixels in
17.915 seconds. All 23 registered poses match the supplied calibration within
the script's tolerance. Evidence and input hashes:
`.local/data/selfcap/dance1-initialization-20260906/result.json` and `inputs.json`.
The cloud is `initialization.ply` in that directory. This is sparse midpoint
initialization, not proof of dynamic-region coverage or corrected temporal
synchronization. Moving correspondences can be rejected during triangulation.

`scripts/stg_checkpoint.py` adds iteration-boundary serialization for Lite and
Full, including motion/temporal tensors, Full decoder, optimizer, densification
statistics, training options, caller-provided loop state, and RNG state.
It checks provenance and missing state, rejects uncleared gradients, and uses
an atomic checkpoint-file replacement. CPU synthetic tests reproduce the next
optimization step exactly for both representations. The native Lite and Full
classes also passed synthetic CUDA optimizer restoration on the RTX 4090 using
`scripts/verify-stg-checkpoint.py`: next-step losses and all optimized tensors
were exactly equal. Synthetic checkpoint sizes were 29,992 and 35,076 bytes;
these are not scene-model sizes. The test exposed and fixed serialization of
NumPy scalar learning rates. It does not exercise rasterizer backward,
densification, EMS, or fresh-process scene rendering. The caller still needs
to provide its sampler/EMS state
and maintain a separate durable budget ledger that counts failed attempts.

Training has not started. Remaining integration includes auditing initialization
coverage, method loaders for corrected timestamps, end-to-end resume validation,
and enforcement of the per-scene training budgets.

## Manifest-native STG renderer validation

`scripts/stg_scene.py` now loads the completed SelfCap manifest, excludes 0015
from training keys, groups batches by source frame while retaining each camera's
corrected time, and loads individual RGB images with hash checks on demand.
It supplies full calibrated projection matrices and Full decoder rays without
the upstream camera class's conditional principal-point offset handling.
COLMAP continuous coordinates map to rasterizer pixel indices minus 0.5;
synthetic off-center projection and rotated-camera ray tests verify this.
The loader also consumes the shared frozen-time sweep poses.

GPU evidence: `.local/runs/stg-manifest-renderer-20260906/result.json`.
Both native `train_ours_lite` and `train_ours_full` completed synthetic forward
and backward on the RTX 4090 using camera 0000 at its processed 1872×1052
resolution and corrected time 0.4990413947275212. All 64 synthetic points were
visible. Gradients were present and finite for position, appearance, motion,
rotation/angular velocity, scale, opacity, and temporal parameters; Full also
passed decoder and temporal-appearance gradient checks. The PNGs in this run
are synthetic validation artifacts, not reconstructed SelfCap predictions.

`scripts/training_budget.py` provides conservative durable attempt accounting
with a shared ledger lock, fixed per-method/scene/stage allocations, and atomic
records. Failed attempts count; missing final records retain the entire
reservation. Tests cover retries, serialization, MoE stage limits, and explicit
overrun reporting. This helper is not a watchdog and has not been wired into
a training entry point. A supervisor and iteration-boundary checkpoint policy
remain necessary before launching the budgeted experiments. No scene-training
allocation has been consumed by these synthetic compatibility checks.
