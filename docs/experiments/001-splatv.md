# Experiment 001: splaTV bundled scene

Status: **completed, viewpoint limitations observed**. Date: 2026-09-05.

## Purpose and reproduction

Question: can the existing animated representation be loaded locally, paused,
scrubbed, and inspected from a displaced viewpoint? The bundled scene depicts
a person and a bright flame in a garage-like setting; no capture ID or physical
frame-rate provenance was established.

Source: [splaTV](https://github.com/antimatter15/splaTV), revision and source-license
notes in the [shared record](section6-evidence.md). Complete scene asset:
`.local/splaTV/model.splatv`, 22,216,610 bytes, SHA-256
`672fe189fc8e81e52bf0e1529993f95641ee54883391f5e5ea93badd130f10e9`.
It contains 2,254 camera entries, not necessarily that many independent physical
cameras. No Python reconstruction model or training data was needed.

Applied setup is `patches/splatv-time-controls.patch` plus the copied
`patches/splatv/time-controls.js`. Source revision, patched status, package
inventory and browser/GPU configuration are in the shared record. Browser
automation uses `.local/envs/downloads/bin/python`; Torch/CUDA build assertions
are not applicable to this viewer.

Exact command and measurements:
`.local/runs/evidence-splatv-bundled-20260905/{command,measurement}.json`.
The executed inspection command from the workspace root was:

```bash
.local/envs/downloads/bin/python scripts/inspect-splatv.py \
  --output .local/runs/evidence-splatv-bundled-20260905/browser --scene model.splatv
```

Use a fresh output path for another run. The script selects embedded camera 0
(`camera_0001`), whose matrix/intrinsics are recorded in `browser/browser.json`.
Time is normalized 0–1; the default five-second viewing cycle is arbitrary.

## Measurements

| Observation | Value | Boundaries |
| --- | --- | --- |
| Setup | Reused patched viewer; installed Playwright/Chromium | Historical setup hours not measured |
| Local first load | 0.79 s | Navigation to visible-scene condition; warm OS cache possible |
| Automated inspection | 34.75 s | Includes waits and screenshots; not render throughput |
| Browser FPS | 60 in all ten samples | Hardware WebGL2, 1352×1014, DPR 1; about 2.5 s |
| GPU memory | 1,198 MiB sampled peak; 1,116 MiB baseline | Device-wide, 200 ms sampling |
| Evidence size | 37,935,778 bytes | Screenshots, 20-frame clip, contact sheet and logs at snapshot |
| Video playback | 20 frames at 10 FPS | Two-second inspection encoding of sampled normalized times |
| Reconstruction / warm CUDA timing | Not applicable / not measured | Existing viewer asset |

The inspection clip is `preview.mp4` in the run directory. It was encoded with
`ffmpeg -framerate 10 -i browser/sequence/%05d.png -frames:v 20 -c:v libx264
-pix_fmt yuv420p preview.mp4`. Input frames sample `i/20`, not physical timestamps.

## Visual inspection

[Contact sheet](../../.local/runs/evidence-splatv-bundled-20260905/contact.png)
shows time 0, 0.5, 0.98 and the orbit at 0.5. The flame expands visibly;
illumination changes on the wall and figure. Bright flame detail is saturated,
and fine surfaces are soft. The fixed camera preserves a recognizable scene.

A 100-pixel horizontal mouse drag while paused changes the camera matrix and
leaves time at 0.500. The displaced view shows strong stretched ceiling/foreground
surfaces, translucent floaters and a disrupted figure outline. The useful range
is therefore demonstrably limited; no metric radius or angular limit was measured.
Dark/unseen areas do not gain reliable geometry by orbiting. Fire-related changes
cannot be separated from transparency/sorting errors without an original reference.

Play advances time, pause stops it, restart returns to zero, and numeric control
editing keeps the camera fixed. External HTTP requests were denied and cache
disabled during reload; scene/scripts loaded from loopback and reproduced the
middle view. No page errors occurred. A return from late flame state to time zero
is a reset, not an established seamless physical loop. Tab hiding was not tested.
There is no paired ground truth, so neither reconstruction accuracy nor conversion
loss is measured.

## Decision

**Investigate rendering further.** The local viewer and independent time/camera
controls work well enough for exploration. Before adopting it as a general viewer,
test small camera excursions on a representation with an original-renderer
reference; the successful default view does not imply free-viewpoint completeness.
