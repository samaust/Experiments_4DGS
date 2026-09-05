# Experiment 003: native STG sear_steak lite

Status: **completed and reproduced exactly**. Date: 2026-09-05.

## Purpose and reproduction

Question: does the released checkpoint render correctly through its own CUDA
renderer, providing a reference for the browser conversion? This run uses
upstream `test_ours_lite` through `scripts/render-stg-preview.py`, without COLMAP,
dataset preprocessing, training, or held-out evaluation.

Source/revision/patch/compiler details are in the [shared record](section6-evidence.md).
The release is `n3d_sear_steak_lite_allcam.zip` from the
[STG model collection](https://huggingface.co/stack93/spacetimegaussians/tree/main).
Its archive hash and complete scene provenance are in [experiment 002](002-stg-splatv.md).
The rendered PLY is `.local/weights/stg-sear-steak/n3d_sear_steak_lite_allcam/
point_cloud/iteration_25000/point_cloud.ply`, 13,865,353 bytes, SHA-256
`0f0dd4ed584811c3b4f13b7048b3449eb8878a8de87a3ce336f7cc6aa7ad376c`.
The release includes `cfg_args` and calibrated `cameras.json`; the lite path
successfully renders this complete checkpoint without additional learned networks.

Environment: `.local/envs/stg-render/bin/python`; resolved packages in
`evidence-inventory-20260905/stg-render-installed.txt`. All five native extensions
were built in the preceding setup; this run exercises the installed lite kernel.
Historical build logs: `.local/runs/pretrained-validation/stg-build-patched.log`.
Setup used the fixed Torch constraint and `patches/stg-python314-cu130.patch`;
the shared inventory repeats base assertions after installation.

Exact argv/environment are in
`.local/runs/evidence-stg-native-20260905-a/command.json`. The run uses
`--resolution 2`, camera index 0, and `--times 0 0.02 ... 0.98` (50 arguments).
Outputs: `frames/00000.png`–`00049.png`, `frames/preview.json`, `preview.mp4`,
`contact.png`, `analysis.json`, `run.log`, and `gpu.csv` in that directory.
Camera `cam00` is restored from released camera-to-world rotation/position;
the adapter computes translation `-R.T @ position`. Output is 1352×1014,
focal length 731.0626328456394 pixels, black background. Physical source window
is not recovered from the release; these are normalized model times.

Encoding command, executed after rendering from the run directory:

```bash
ffmpeg -v error -n -framerate 30 -i frames/%05d.png -frames:v 50 \
  -c:v libx264 -pix_fmt yuv420p preview.mp4
```

## Measurements

| Observation | Value | Boundaries |
| --- | --- | --- |
| Setup | Reused patched source and compiled extensions | Prior compatibility work not timed |
| Fresh-process render wall time | 12.27 s | Imports, checkpoint load, 50 renders and PNG saving; excludes video encoding |
| GPU memory | 1,835 MiB peak / 1,081 MiB baseline | Device-wide, 200 ms CSV; reprocessed header |
| Output/log directory | 43,164,548 bytes | Snapshot includes PNGs, MP4 and inspection sheet |
| Playback | 50 frames at 30 FPS, 1352×1014 | 1.67-second chosen playback; not recovered capture duration |
| Repeatability | 50/50 PNGs byte-identical | Compared with `.local/runs/stg-native-sequence/` |
| Isolated first load / warm rendering throughput | Not measured | No separate synchronized timing inside this helper |

No FPS is derived from the end-to-end command time. Renderer resolution/imports,
build and actual checkpoint rendering pass; training operations remain outside
the validation scope.

## Visual inspection

[Overview and crops](../../.local/runs/evidence-stg-native-20260905-a/contact.png)
show coherent head, hand and utensil movement at 0, 0.5 and 0.98. Blinds, shelf
and countertop remain recognizable and largely stable. Fine facial/clothing
detail is soft, and the moving utensil is thin/indistinct. No major frame-wide
collapse is visible in these sampled states.

Across all 49 adjacent pairs, mean absolute RGB change averages 0.265 on a
0–255 scale, with maximum pair mean 0.332. The stationary blinds crop
`x=250:950,y=80:320` averages 0.172. These are descriptive change measurements,
not flicker scores: real motion and lighting also contribute. Looping the last
frame to the first changes the pose; seamless looping is unproven.

The helper renders a fixed released camera. It supports selecting another
released camera, but no new camera sweep or frozen-time orbit was run here;
newly exposed surfaces and off-camera geometry therefore remain unassessed.
This is an all-camera checkpoint, so `cam00` is not held-out evidence. The
matched-intrinsics browser reference in experiment 002 shows extra ghosting;
native image quality should not be inferred solely from the converted viewer.

## Decision

**Investigate rendering further.** Keep this renderer as the reference while
auditing the browser conversion. The next STG-specific check is a calibrated
camera sweep on the same checkpoint, followed by paired frozen-time native/browser
captures. Existing image quality and exact reloads justify that work; they do
not yet justify a training commitment.
