# Contender experiments 006–010

This is the execution guide for the matched comparison in [plan 004](../plans/plan_004.md).
The two checked-in JSON files under `configs/` are metadata starting points, not
method configurations. SelfCap has 24 verified camera IDs. The downloaded DG
archive has 34 cameras and 25 FPS; its calibration remains to be obtained.

## Shared protocol

Executed preprocessing and renderer checks are documented in the
[data preparation record](experiments/contender-data-20260906.md).
Reproduce SelfCap preparation using the [training guide](local-creation.md),
then validate the completed output:

```bash
.local/envs/stg-colmap/bin/python scripts/verify-prepared-scene.py \
  .local/data/selfcap/dance1-processed-20260906/manifest.json
```

Create one manifest per scene, and give the same manifest to every adapter. The
generator validates half-open frame ranges, camera uniqueness, held-out
membership, and source hashes. Its nominal `frame_offset / count` mapping is
not the corrected SelfCap training time. Use the processed manifest produced by
`prepare-selfcap.py` for corrected timestamps, camera matrices, and output sizes.
Use training cameras only for initialization and audit supplied point clouds.

The generic command wrapper records provenance only; it does not implement
method loaders, enforce the training budget, or make checkpoints resumable.
Method integration remains pending. Example wrapper syntax:

```bash
python3.14 scripts/method-adapter.py --method METHOD \
  --manifest .local/data/manifests/SCENE.json --config CONFIG.json \
  --cwd .local/METHOD --output .local/runs/exp-00N/SCENE \
  -- METHOD_COMMAND --manifest .local/data/manifests/SCENE.json
```

The wrapper records command, manifest/config hashes, selected CUDA environment,
exit status, and wall time. Put checkpoints and rendered PNG/MP4/contact-sheet
outputs under that run directory; never overwrite a prior run.

## Experiment matrix

| ID | Method | Required implementation note | Status |
| --- | --- | --- | --- |
| 006 | STG Full | `oursfull`, appearance decoder sidecar, fused native renderer | pending source/data validation |
| 007 | FreeTimeGS | author implementation; label vanilla/reproduction separately | pending source/data validation |
| 008 | MoE-GS | four exact experts plus router; validate modified STG expert format | pending source/data validation |
| 009 | ATGS | hash encoder and the 60/50-frame windows | pending source/data validation |
| 010 | FreeTimeGS++ | fixed B configuration for both scenes; no scene-wise selection | pending source/data validation |
| baseline | STG Lite | matched scenes and same held-out cameras | pending training |

For each successful pair, render all held-out timestamps, the shared 20-pose
frozen-time path, and lossless PNGs before encoding MP4. Evaluate with:

```bash
.local/envs/stg-render/bin/python scripts/evaluate-reconstruction.py \
  --predictions RUN/SCENE/predictions --ground-truth RUN/SCENE/ground-truth \
  --output RUN/SCENE/metrics.json --lpips-alex
```

Run the evaluator once on identical directories and once after a deliberate
pixel perturbation. Report per-frame and aggregate PSNR, SSIM, and LPIPS-Alex
separately for each scene. Keep artifact observations in the experiment report;
do not turn them into a combined score.

## Reports

These are intentionally marked pending until the authorized host has the
datasets, checkpoints, and compatible implementations:

- [006 STG Full](experiments/006-stg-full.md)
- [007 FreeTimeGS](experiments/007-freetimegs.md)
- [008 MoE-GS](experiments/008-moe-gs.md)
- [009 ATGS](experiments/009-atgs.md)
- [010 FreeTimeGS++](experiments/010-freetimegs-plus-plus.md)
- [Comparison summary](experiments/contender-summary.md)

Earlier `sear_steak` outputs remain historical evidence and are not replaced.


The current user-authorized Basketball variant excludes physical camera 5:
29 training cameras, four held-out cameras (0, 10, 20, 30), and 1,650 expected
images. The raw archive still contains all 34 videos. See the
[revision-one calibration record](experiments/basketball-rev1.md) for the
current expanded-prior and independent-window stability blockers. Training remains gated on accepted
estimated calibration and synchronization; original allocations are unchanged.
