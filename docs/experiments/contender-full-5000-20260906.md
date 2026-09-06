# Full 5,000-step continuation and checked comparison

This continues the [Lite evaluation-pipeline record](contender-evaluation-pipeline-20260906.md)
and [Full growth validation](contender-growth-20260906.md). It is a provisional
equal-step comparison, not completion of either two-hour training allocation.

## Implementation and protocol

The evaluation pipeline now records UTC start/end timestamps, monotonic wall
seconds, exit codes and status per stage, including failed launches. Total
evaluation wall time is separate from the training ledger. It does not retry
failed commands or bypass offline restrictions.

`scripts/compare-stg-evaluations.py` verifies common manifest hashes, metric
protocols, rendered camera/time samples, sweep identity, metric frame sets and
internal report consistency before calculating aggregate and per-frame deltas.
It preserves incomplete-training labels, reports whether iterations match,
and emits null instead of undefined infinite-PSNR subtraction. No significance
test or composite artifact score is implied. See the [training guide](../local-creation.md)
for both evaluation and comparison commands.

The updated suite has 45 passing tests, including nine comparison tests and
one additional pipeline launch-error test. Failure tests use synthetic mocked
errors; no real sandbox/device permission failure occurred during these tests.

## Training command

The command below resumes the pinned Full checkpoint at iteration 2000 and
stops after 3,000 additional iterations. All upstream optimization settings,
the shared manifest, training-only initialization and fixed detail crops are
unchanged. The central ledger counts this and earlier attempts toward Full's
SelfCap allocation. GPU experiments run sequentially.

```bash
.local/envs/stg-render/bin/python scripts/measure-experiment.py \
  --output .local/runs/stg-full-selfcap-5000-measurement-20260906 \
  --cwd /home/auss/git_repos/samaust/Experiments_4DGS -- \
  /home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-render/bin/python \
  scripts/train-stg-manifest.py --checkout .local/SpacetimeGaussians \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --initialization .local/data/selfcap/dance1-initialization-20260906 \
  --output .local/runs/stg-full-selfcap-5000-20260906 --model full \
  --resume .local/runs/stg-full-selfcap-growth-20260906/checkpoint.pt --max-steps 3000
```

Output directories must be new. This is an integration boundary within the
30,000-step schedule, not a replacement schedule or a final-budget quality claim.

The default opacity reset at iteration 3000 is followed by pruning from
536,984 to 247,637 points at iteration 3100. Logged losses remain finite
across that boundary. No source/configuration change or resolution reduction
was made to compensate for this change in point count.

## Training result and budget

Full completed iteration 5000 with 211,618 Gaussians and final logged loss
0.0503363460. Supervisor wall time was 489.946381 seconds; the device-measurement
wrapper recorded 490.029610 seconds. Framework peak allocated/reserved memory
was 1,825,054,720 / 3,823,108,096 bytes. The 200 ms device-wide sampler recorded
a 974 MiB baseline and 5,328 MiB peak, including baseline usage. Brief peaks
can be missed. No other GPU experiment or heavy CPU evaluation overlapped.

The complete checkpoint is 99,336,477 bytes; inference export includes the
32,166,842-byte PLY and 2,373-byte decoder sidecar. The checkpoint remains
marked incomplete against the upstream 30,000-iteration schedule.

This attempt charged 489.947644 seconds. All Full SelfCap attempts now total
816.799333 seconds, leaving 6,383.200667 of the original 7,200 seconds. Lite
remains at 709.725114 seconds charged with 6,490.274886 seconds remaining.
No time has been redistributed between methods or scenes.

Evaluation output: `.local/runs/stg-full-selfcap-5000-evaluation-20260906`.
The command is the training guide's evaluation pipeline with the Full
checkpoint/output paths. Offline render processes and CPU metric/packaging
stages execute sequentially after training has exited.

## Offline results and observed artifacts

Both fresh offline reloads produced byte-identical PNGs for all 60 held-out
frames and 20 sweep poses; maximum and mean pixel differences were zero.
Native warm rendering measured **275.749748 FPS** at 1890×1061 using ten
warmups and 100 CUDA-synchronized renders, excluding setup, saving and encoding.

All 60 held-out frames give PSNR **23.452953 dB**, SSIM **0.832861** and
LPIPS-Alex **0.279153**. The unchanged shared evaluator and cached AlexNet weights
ran under the offline restriction. Per-frame values are in `metrics.json`.

At frames 4120 and 4150, the prediction sheet shows pronounced face/hair blur
and smeared head/arm boundaries against the clearer bookcase. At 4179 the face
is recognizable but remains soft, with hair blending into the background. The
static shelves/book spines are better defined than the moving person. These
observations do not establish that every blurred region is reconstruction error:
the source ground truth also has motion blur.

This is sampled-image inspection, not a completed video flicker assessment.
Improved PSNR/SSIM alone do not establish an artifact-quality winner.

The sweep sheet at poses 0/10/19 shows soft hand/knee boundaries and patchy
floor appearance. Endpoint framing cuts off the head along the shared camera
path; that clipping alone is not a reconstruction artifact. No ground-truth
metrics are assigned to these interpolated views.

The pipeline completed in **160.990306 seconds**, separate from training:
first reload/benchmark 27.129722 s, second reload 26.586320 s, held-out
comparison 4.113517 s, metrics 57.731849 s and packaging 44.031091 s.
The remaining time includes sweep comparison and orchestration; exact stage
timestamps/durations are in `commands.json` and `evaluation.json`.
The earlier Lite report predates stage timing, so its missing times are not
backfilled or inferred.

The final evidence package contains three MP4s, full-image and fixed-crop
contact sheets, 480 crop PNGs and provenance. PNGs retain 1890×1061 dimensions;
videos retain the established one-row padding, with no profile reduction.

## Checked equal-step comparison

`scripts/compare-stg-evaluations.py` completed against the existing Lite and new
Full evaluations and wrote
`.local/runs/stg-selfcap-5000-comparison-20260906.json`. Full minus Lite:
**+1.370350 dB PSNR**, **+0.005722 SSIM**, **+0.008946 LPIPS-Alex**. Thus the
aggregate metrics disagree about the better checkpoint: Full improves the
first two, while Lite has lower LPIPS. Both are unfinished and charged different
training wall times, so these are not final-budget rankings. Per-frame deltas
are included in the JSON and the [comparison summary](contender-summary.md)
retains the earlier iteration-2000 results separately.

Final validation: all 45 tests pass and `git diff --check` passes. Remaining
plan work includes longer training, other contender adapters, matching
Basketball DG calibration and full temporal artifact review.
