# STG evaluation pipeline and longer Lite integration

This continues [the growth/offline validation](contender-growth-20260906.md).
The selected profiles, source hashes, upstream schedule, crop configuration
and central training budgets are unchanged. It does not complete plan 004.

## Implementation

`scripts/evaluate-stg-checkpoint.py` runs two fresh network-restricted native
renders sequentially, verifies checkpoint/manifest identity between them,
compares all held-out and sweep PNGs, evaluates PSNR/SSIM/LPIPS-Alex using
cached weights, and packages the fixed crops, contact sheets and videos.
It records commands and stage logs, stops on the first subprocess error, and
writes `evaluation.json` only after every stage succeeds. It does not launch
training or consume training allocation. See the [training guide](../local-creation.md)
for the complete invocation.

`scripts/compare-render-reloads.py` requires exact nonempty filename sets and
the expected frame count, uniform dimensions and RGB mode. It reports separate
byte and pixel equality plus per-frame and aggregate absolute pixel error.
This closes a gap in the older descriptive sequence analyzer: counting matching
files alone did not reject extra or missing files in the other reload. This is
still quantized PNG comparison, not proof of floating-point state equality.

Seven new tests cover exact reloads, metadata-only PNG changes, numerical
differences, wrong frame counts, extra files, dimensions/mode mismatches,
pipeline failure propagation, absent cached weights and existing-output safety.
All 35 research-environment tests pass.

The NVIDIA catalog list query succeeded; no skills were installed. The ATGS
[source audit](009-atgs.md) now identifies the native build, manifest-camera,
checkpoint and output-format adaptations still required. No ATGS training was
launched and no incompatible representation was substituted.

## Lite continuation

The supervised run resumes iteration 2000 from
`.local/runs/stg-lite-selfcap-ems-20260906/checkpoint.pt`, with
`--max-steps 3000` targeting iteration 5000. This boundary does not shorten
the upstream 30,000-iteration optimization schedule. Output:
`.local/runs/stg-lite-selfcap-5000-20260906`; measurement:
`.local/runs/stg-lite-selfcap-5000-measurement-20260906`.

The default opacity reset at iteration 3000 is followed by pruning from
602,153 to 399,274 points at iteration 3100. This is the existing densify-3
schedule, not a new memory-saving profile change. Logged losses remained
finite across this boundary. No other GPU experiment or heavy CPU evaluation
ran concurrently with this training command.

The run completed iteration 5000 with 367,125 points and final logged loss
0.0451672673. Supervisor wall time was 414.151057 seconds; the measurement
wrapper recorded 414.215701 seconds. Framework peak allocated/reserved memory
was 1,447,914,496 / 3,810,525,184 bytes. Device-wide 200 ms sampling recorded
a 1,504 MiB baseline and 5,623 MiB peak, including baseline usage; it can miss
brief peaks. Do not compare raw device peaks without accounting for the
different baseline in the earlier Full run.

The resumable checkpoint is 140,077,761 bytes and exported PLY is 46,992,777
bytes. The checkpoint remains marked incomplete against the 30,000-step
schedule. Evaluation output is
`.local/runs/stg-lite-selfcap-5000-evaluation-20260906`.

This attempt charged 414.152408 seconds to Lite's SelfCap allocation. All Lite
attempts now total 709.725114 seconds, leaving 6,490.274886 of the original
7,200 seconds. Full remains at 326.851688 seconds charged; unused time has not
been moved between methods or scenes.

## Held-out evaluation and image inspection

All 60 held-out PNGs and 20 frozen-time sweep PNGs are byte-exact between
fresh offline reloads, with zero maximum and mean pixel differences. The
native no-grad renderer measured **449.311252 FPS**, using ten warmups and
100 synchronized renders at 1890×1061, excluding setup/saving/encoding.

All 60 held-out frames give PSNR **22.082603 dB**, SSIM **0.827138**, and
LPIPS-Alex **0.270207**. Compared with Lite at iteration 2000, the arithmetic
changes are +1.987522 dB PSNR, +0.032121 SSIM and −0.061754 LPIPS. These
show progress within one training run, not a matched-budget method ranking.
Full has not yet been extended to this iteration or budget charge.

The prediction sheet at frames 4120/4150/4179 retains sharp bookcase structure
relative to the moving person. The face at 4179 is more defined than in the
earlier Lite sheet, but hair still blends into the background. At 4120 the
arm/head region remains severely blurred and ghosted; at 4150 a broad hair
trail overlaps the bookcase. Improved aggregate metrics do not resolve these
moving-boundary failures. Ground truth also contains motion blur, so these
images alone do not isolate reconstruction error from source blur.

This is a sampled-sheet inspection, not a full-video flicker assessment.
The unchanged ground-truth-selected crop bounds are used throughout.

The sweep sheet at poses 0/10/19 shows softened hand/knee boundaries and
patchy floor appearance; endpoint head clipping follows the shared camera
framing. No ground-truth quality metric is assigned to the interpolated views.

The complete pipeline exited successfully and wrote `evaluation.json` with
checkpoint/manifest/helper hashes and reload summaries. `evidence/` contains
three MP4s, full-image and fixed-crop contact sheets, 480 crop PNGs and packaging
provenance. Native PNG dimensions remain unchanged; videos use the previously
documented single-row padding. Final `git diff --check` passes.
