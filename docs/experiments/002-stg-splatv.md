# Experiment 002: STG sear_steak lite in splaTV

Status: **completed, visible browser/native differences**. Date: 2026-09-05.

## Purpose and reproduction

Question: does converting the complete released STG scene yield a repeatable,
animated browser preview, and how does it differ from native rendering?
Release: [STG model collection](https://huggingface.co/stack93/spacetimegaussians/tree/main),
`n3d_sear_steak_lite_allcam.zip`, 16,148,391 bytes, SHA-256
`e017d214b6bc695d1a7da8c75598eab1393e1be9507d250976658bc66c31eca2`.
The original download used `main`; its historical remote commit was not recovered.
The archive hash identifies the evaluated bytes. Source/asset license distinction,
viewer commit, patches and environment are in the [shared record](section6-evidence.md).

A fresh conversion ran using `scripts/convert-stg-to-splatv.cjs` with
`--viewer .local/splaTV`, the released `point_cloud/iteration_25000/point_cloud.ply`,
the release's `cameras.json`, and output
`.local/splaTV/evidence-sear-steak-20260905.splatv`. It contains 108,317 Gaussians,
1,052 camera entries, and 7,343,047 bytes. SHA-256
`60dcab6db3e1500faa8a136bb6a2b81afd2edcdf0270a70119815a7ea2528fba`
matches the earlier conversion exactly. The full paths are given in section 2
of the [execution guide](../pretrained-experiments.md).

Measured run: `.local/runs/evidence-splatv-stg-20260905/`, with exact argv in
`command.json`. The command uses `inspect-splatv.py --scene
evidence-sear-steak-20260905.splatv`. Browser packages are inventoried in
`evidence-inventory-20260905/downloads-installed.txt`. No model training or
source compilation was required for conversion/playback.

## Measurements

| Observation | Value | Boundaries |
| --- | --- | --- |
| Setup effort | Reused viewer; fresh deterministic conversion | Conversion time not separately measured |
| Local first load | 0.76 s | Visible-scene condition; OS cache may be warm |
| Automated inspection | 41.12 s | Includes screenshots, control waits and reload |
| Browser FPS | Ten samples of 60 FPS | Hardware WebGL2, 1352×1014, DPR 1 |
| GPU memory | 865 MiB peak; 716 MiB baseline | Device-wide, 200 ms sampling |
| Evidence size | 53,204,135 bytes | Main run directory at snapshot |
| Clip | 20 frames, 10 FPS | Arbitrary playback rate, not capture rate |
| Warm native throughput / reconstruction | Not measured / not applicable | Converted existing scene |

`preview.mp4` uses the same 20-frame ffmpeg encoding recipe as experiment 001.
Physical STG capture-window alignment remains unknown; time is normalized.

## Visual inspection

The [default-view sheet](../../.local/runs/evidence-splatv-stg-20260905/contact.png)
shows coherent changing head/arm poses, but a ghosted face at time zero and soft
moving boundaries. The default browser uses the original focal length at a smaller
viewport and is more zoomed-in than the half-resolution native render.

For the [matched-framing sheet](../../.local/runs/evidence-splatv-stg-20260905/native-match.png),
the browser uses released `cam00`, focal lengths 731.0626328456394 pixels,
1352×1014 viewport, black background, and times 0, 0.5, 0.98. Camera matrices and
intrinsics are saved in `browser/browser.json`. Scene framing now aligns with
the [native STG reference](003-stg-native.md). Browser output still has more
translucent/ghosted face and arm boundaries and less clean background detail.
These are combined conversion/rendering differences; no experiment isolates
opacity quantization, sorting, or color handling as the sole cause. UI overlays
are present in screenshots, so no whole-image PSNR comparison is claimed.

The modest frozen-time orbit stays recognizable and exposes more of the shelf;
some soft/doubled boundaries remain. Wide viewpoint range and unseen surfaces
are unvalidated. The fixed-view blinds remain largely stable in the inspected
states; a perceptual flicker rating was not established. End-to-start looping
changes the pose and was not shown to be seamless. This checkpoint used all
cameras: the native/browser comparison is not held-out evaluation.

Play, scrub, pause, restart, orbit and local-only cache-disabled reload pass;
there are no page errors. The first control test used exact float equality and
flagged camera movement during numeric editing. The follow-up in
`evidence-splatv-controls-20260905/browser/browser.json` measured only
`2.22e-16` maximum matrix change, passing a `1e-9` tolerance. This was numerical
drift in the test, not a meaningful camera movement. No viewer change was made.

## Decision

**Investigate rendering further.** Retain this as a portable preview, with native
STG as the reference. Audit the conversion/rendering treatment of dynamic opacity
and moving edges before treating browser appearance as the model's native quality.
