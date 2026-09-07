# Experiment 006: STG Full

Status: **SelfCap native 30,000-step schedule and final evaluation complete;
Basketball blocked on calibration**.

The [completed native STG comparison](contender-native-stg-20260906.md) records
the final Full result: PSNR 24.496753, SSIM 0.864213, LPIPS-Alex 0.214612 and
224.135 FPS. All 80 PNGs reload byte-exactly offline. Total charged training is
4652.027359 seconds; the final model contains 50,607 Gaussians. The records below
describe earlier integration and pilot milestones.

Full completed initial training/resume checks, then a fresh 2,000-step run
including densification and two EMS insertions, ending at 667,064 Gaussians.
It rendered all 60 held-out timestamps and the 20-pose sweep offline. This does not
establish quality at the agreed training budget. Basketball is still blocked
on calibration. See the [training integration record](contender-training-20260906.md)
for commands, budget charges, limitations and remaining gates.

Full subsequently resumed to iteration 5000, ending at 211,618 Gaussians after
the default opacity reset/pruning. The [5,000-step record](contender-full-5000-20260906.md)
contains the longer run, offline evaluation, checked Lite comparison and current
budget charges. The subsequent native continuation above completes the schedule.

Release audit, 2026-09-06: downloaded `techni_Birthday_allcam_allpoints.zip`
from `stack93/spacetimegaussians` revision `9534842`. Despite its unsuffixed
filename, saved `cfg_args` explicitly identifies `model='ours_lite'`; the
archive has no decoder `.pt`. It is not suitable for validating Full. Local
archive: `.local/downloads/stg-full/techni_Birthday_allcam_allpoints.zip`.

Use the shared [contender protocol](../contender-experiments.md), the STG source
revision and compatibility patch recorded in [section 6](section6-evidence.md).
This run must retain and validate the appearance decoder state. The native
preview helper accepts `--model full --decoder PATH` and refuses a missing or
mismatched decoder.

Provisional held-out metrics, reload checks, and visual findings are recorded in
the [growth/offline record](contender-growth-20260906.md). The native warm-render
benchmark at iteration 2000 is 293.384 FPS at 1890×1061. The complete checkpoint
retains the appearance decoder and optimizer state; exported inference files
include both the PLY and decoder sidecar. Do not use the all-camera `sear_steak`
checkpoint as held-out evidence.

Native Full forward/backward compatibility is now validated on synthetic points
through a full-size SelfCap manifest camera, including finite decoder gradients.
Native synthetic optimizer checkpoint restoration also passes exact next-step
equality. See the [data and integration record](contender-data-20260906.md).
These checks do not constitute matched-scene training or quality evaluation.

## Plan 005 Basketball calibration update — 2026-09-06

The [ViPE pilot](basketball-calibration-20260906.md) audited all 34 videos but
stopped at camera 4 intrinsic instability: 20.2948% focal range relative to the
median, above the 20% pilot threshold fixed before inference. No accepted
estimated calibration or synchronization was produced. Basketball training and
evaluation remain blocked; this task charged zero training seconds and left
the existing method allocations unchanged.

The subsequent user-authorized **25%** pilot passed. The
[all-camera continuation](basketball-calibration-20260906.md#all-camera-continuation-outcome-blocked-at-camera-5)
then stopped at camera 5 (**26.0539% > 25%**); the other 33 cameras passed the
intrinsic check. This supersedes camera 4 as the current calibration blocker.
Shared geometry, synchronization and Basketball training remain unexecuted.
Cumulative calibration charge is 323.0525 seconds; training charge remains zero.


### Current 24-camera variant under the 20% gate

The user restored the intrinsic-prior gate to 20% and excluded all failing
cameras. The current variant has 24 cameras: 21 training and held-outs 0, 10, 30,
with 1,200 expected images (150 held-out). [The complete bounded rerun](basketball-intrinsic20.md)
finished all 32 independent reconstructions. Its best comparison is **0.7182
degrees / 1.1185% of rig diameter**, failing the unchanged 0.5 degree / 1% gate
only at training camera 19. All retained priors and ten-frame focus screens pass.
Calibration remains blocked; training/evaluation did not start. Cumulative GPU
calibration charge is 1,056.0873 seconds; original training budgets are unchanged.
