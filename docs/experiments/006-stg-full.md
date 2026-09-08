# Experiment 006: STG Full

Status: **SelfCap native 30,000-step schedule and final evaluation complete;
Basketball blocked on synchronization**.

## Current Basketball continuation — 2026-09-07

[Plan 010](basketball-shared-timing-v4.md) adds a separately versioned
positive-depth constrained evaluator and deterministic weak-column seed repair.
The exact control remains numerically unqualified: both integer
searches retain all 12 groups but have no complete qualified group profile
in either sweep direction.
The saved v3 failures and amplitude probes also leave observable escape
unresolved. Real fitting and the later independent controls remain gated;
selection, final validation and Basketball training are untouched. The 1,890
production controls and unchanged admission were verified for reuse.

[Plan 009](basketball-shared-timing-v3.md) repairs the independent solver's
previous evaluation-cap failures, but timing remains blocked: the exact noiseless
control has only 11/12 complete ascending and 10/12 complete descending data-only
group profiles because some fits converge with negative depth. The best-of-three
estimate recovers −0.10 frames but cannot qualify without both sweep directions.
No real fitting, selection reevaluation, final validation or Basketball training
was performed. The unchanged 1,890 production controls and Plan 008 admission
were hash-verified; all six real configurations remain unassessed.

[Plan 008](basketball-shared-timing-v2.md) resolves the multiview admission
failure: all 72 edges pass with 667 whole groups per half and at least 19 groups
per edge per half. Timing remains blocked at independent synthetic validation:
71/612 data-only nuisance fits hit the 200-evaluation cap on a noiseless
100-frame direction-change control, leaving 0/12 complete group profiles.
The spline optimizer and evaluator are implemented; no real offsets were fitted
or selection reevaluated. Final frames 200–249 and Basketball training remain
untouched.

The earlier [Plan 007 shared-trajectory investigation](basketball-shared-timing-v1.md)
recorded an admission blocker for the revised method: 16/72 fixed edges lack
12 multiview groups in both deterministic halves. The estimator audit and
all-camera native fitting extraction are complete; spline fitting and selection
reevaluation did not start. The previous failed selection remains evidence.
Final frames 200–249 and all Basketball training allocations remain untouched.

[Plan 006](basketball-calibration-alternatives.md) accepted all 34 static cameras;
[revision 2](basketball-rev2.md) verified provenance/conventions and passed the
training-view estimated scale check (1.31506947 estimated metres per calibration
unit, 3.13% reserved disagreement).
[Fine native fitting](basketball-cycle-refinement.md) yields a qualified 72-edge,
bridge-free graph covering all 34 cameras at the unchanged 0.25-frame cycle gate.
[Separately frozen timing selection](basketball-timing-selection.md) then passes
only 36/72 connections on frames 150–199; the passing graph is disconnected.
Uncertainty/ambiguity and temporal-half checks block acceptance. No final timing
validation,
1,700-image preparation, Gaussian initialization or Basketball training/evaluation
was launched. Held-outs remain 0, 10, 20, 30, with 30 training cameras. The
original per-method two-hour Basketball allocation is unchanged and uncharged.

## Prior implementation and experiment evidence


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


### Current 23-camera variant after camera 19 removal

The user also removed camera 19. The current variant has 23 cameras: 20
training and held-outs 0, 10, 30; 1,150 expected images (150 held-out).
[The rebuilt 23-camera search](basketball-no-camera19.md) completed 32 independent
reconstruction commands. Its best result is **5.8807 degrees / 7.1892% of rig
diameter**, failing the unchanged pose gates. All retained priors and full focus
screens pass, but calibration and downstream training/evaluation remain blocked.
No new GPU inference was used; cumulative calibration charge remains 1,056.0873
seconds and the original training budgets are unchanged.
