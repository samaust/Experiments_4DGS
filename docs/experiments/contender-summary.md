# Contender comparison summary

Status: **plan's result-or-specific-blocker coverage complete: four evaluated
SelfCap pairs and eight blocked pairs. A full six-method/two-scene ranking is unavailable.**

Lite and Full have completed their native SelfCap schedules and final evaluations.
FreeTimeGS and ATGS have completed their budget-limited runs and evaluations at
42,061 steps and 61,008 microsteps respectively; their native schedules remain unfinished.
MoE-GS and FreeTimeGS++ retain the source gates in their experiment reports;
Basketball now has accepted static calibration and estimated scale, but remains
blocked on synchronization; see [revision 2](basketball-rev2.md).

Earlier records cover [initial execution](contender-progress-20260906.md),
[data preparation](contender-data-20260906.md),
[training integration](contender-training-20260906.md),
[growth/offline validation](contender-growth-20260906.md),
[Lite evaluation integration](contender-evaluation-pipeline-20260906.md) and
[Full's 5,000-step pilot](contender-full-5000-20260906.md). Their historical
statuses and measurements are superseded where newer results are given below.

## SelfCap dance1 — final native-schedule or budget-stop checkpoints

Both STG variants reached 30,000 steps within their individual two-hour limits.
FreeTimeGS stopped at 42,061 / 70,000 steps to preserve its shutdown reserve.
ATGS stopped at 61,008 / 100,000 microsteps (20,336 optimizer updates).
All metrics cover the same 60 camera-0015 frames at 1890×1061. The
[completed STG record](contender-native-stg-20260906.md) contains resource use,
checkpoint hashes, commands, visual findings and evidence paths.

| Method | PSNR dB | SSIM | LPIPS-Alex | Δ vs Lite (PSNR / SSIM / LPIPS) | Δ vs Full (PSNR / SSIM / LPIPS) | Warm FPS |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| STG Lite | 22.418750 | 0.851204 | 0.219363 | 0 / 0 / 0 | -2.078003 / -0.013010 / +0.004752 | 317.056 |
| STG Full | 24.496753 | 0.864213 | 0.214612 | +2.078003 / +0.013010 / -0.004752 | 0 / 0 / 0 | 224.135 |
| FreeTimeGS reproduction (incomplete schedule) | 25.496026 | 0.881698 | 0.137213 | +3.077277 / +0.030494 / -0.082150 | +0.999274 / +0.017485 / -0.077399 | 182.781 |
| ATGS (incomplete schedule) | 22.180802 | 0.842141 | 0.239707 | -0.237948 / -0.009063 / +0.020344 | -2.315951 / -0.022072 / +0.025096 | 256.625 |

Checked deltas: `.local/runs/stg-selfcap-final-comparison-20260906.json`.
Charged training totals are 3819.048855 seconds for Lite and 4652.027359 seconds
for Full, including earlier attempts. Both reload byte-exactly for 60 held-out
PNGs and 20 sweep PNGs in fresh offline processes. Raw floating-point render
equality was not measured by the STG evaluator; the earlier Lite float-equality
claim was incorrect.

Full improves all three aggregate metrics, while Lite has higher measured
throughput. Both retain substantial head/hair and body-boundary blur in fast
motion, especially frames 4120 and 4150 relative to ground truth. Static shelves
are recognizable but small book text remains soft. The metric improvement does
not establish a sharp reconstruction of fast motion or a flicker ranking.

[FreeTimeGS's final record](007-freetimegs.md#final-budget-limited-selfcap-continuation)
records 7026.107790 seconds charged, no overrun, a 3,199,531,938-byte complete
checkpoint and exact offline PNG/raw-float reloads for all 80 images. Checked
deltas are `.local/runs/freetimegs-vs-lite-selfcap-final-20260906.json` and
`.local/runs/freetimegs-vs-full-selfcap-final-20260906.json`.
Its static shelves and moving person are much more coherent than in the pilot,
but frame 4120 face/forearm smearing, frame 4150 excess hair blur, soft book text
and oversmoothed hands remain. It leads these aggregate metrics at higher
charged training time, with dense initialization and lower measured FPS than
either STG variant. This supports further artifact inspection, not a claim of
full-paper convergence, equal-compute superiority or an established flicker win.

[ATGS's final record](009-atgs.md#final-budget-limited-selfcap-continuation)
records 7026.233249 seconds charged, no overrun, 3,904,977,664 bundle component
bytes and exact PNG/raw-float reloads for all 80 views. Checked deltas are
`.local/runs/atgs-vs-lite-selfcap-final-20260906.json` and
`.local/runs/atgs-vs-full-selfcap-final-20260906.json`.
Static book lettering improves over its pilot, but severe foreground smearing
at 4120, excess hair/arm blur at 4150 and soft/distorted boundaries at 4179
persist. Its final aggregate metrics trail both STG variants despite higher
charged training time. Defer it as an artifact-quality upgrade for this profile;
native no-growth settings and incomplete training limit generalization.

### Budget and interpretation

| Method | Final progress | Charged training seconds / 7,200 | Command wall for final continuation | Device baseline / sampled peak MiB | Complete checkpoint bytes |
| --- | --- | ---: | ---: | ---: | ---: |
| STG Lite | 30,000 steps, native complete | 3,819.048855 | 3,109.387550 s | 833 / 7,158 | 34,044,289 |
| STG Full | 30,000 steps, native complete | 4,652.027359 | 3,835.337033 s | 866 / 7,292 | 29,778,653 |
| FreeTimeGS reproduction | 42,061 steps, budget stop | 7,026.107790 | 6,460.046399 s | 825 / 7,532 | 3,199,531,938 |
| ATGS | 61,008 microsteps, budget stop | 7,026.233249 | 6,349.703736 s | 792 / 8,633 | 3,904,977,664 |

Checkpoint accounting follows each method's complete saved state; FreeTimeGS
and ATGS include large optimizer/resume state, so these sizes are not comparable
inference-only payloads. ATGS reports summed bundle components. Sampled peaks
are device-wide and can miss brief peaks; framework peaks are in each report.
The ledger totals **22,523.417254 seconds (6.256505 hours) / 24 hours**, including
earlier attempts, with zero overruns and no live reservations. Downloads, builds,
initialization and evaluation are separate; unused scene/method budgets were not
redistributed. The small remaining ATGS/FreeTimeGS allowances are below their
restart/reserve gates.

For further **inspection**, prioritize the dense-initialized FreeTimeGS
reproduction: sampled foreground/background coherence and aggregate metrics
improved substantially. Its severe fast-motion blur still prevents an
unqualified quality recommendation. Keep STG Full as the completed native
comparison and Lite as the faster measured renderer. This conclusion is based
on the local artifacts, not paper scores or an invented combined artifact score.
No measured flicker ranking or long-sequence claim is established.

## SelfCap dance1 — provisional 5,000-step checkpoints

Same 60 held-out camera-0015 frames, shared metric protocol and 1890×1061
resolution. These historical checkpoints precede native-schedule completion for
Lite and Full; equal iteration labels do not imply equal updates or budget usage.

| Method | PSNR dB | SSIM | LPIPS-Alex | Δ vs Lite (PSNR / SSIM / LPIPS) | Δ vs Full (PSNR / SSIM / LPIPS) | Warm FPS |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| STG Lite | 22.082603 | 0.827138 | 0.270207 | 0 / 0 / 0 | −1.370350 / −0.005722 / −0.008946 | 449.311 |
| STG Full | 23.452953 | 0.832861 | 0.279153 | +1.370350 / +0.005722 / +0.008946 | 0 / 0 / 0 | 275.750 |
| ATGS | 21.637782 | 0.802142 | 0.341477 | -0.444821 / -0.024997 / +0.071270 | -1.815171 / -0.030719 / +0.062324 | 281.242 |
| FreeTimeGS reproduction | 19.153970 | 0.682328 | 0.528610 | -2.928633 / -0.144810 / +0.258403 | -4.298983 / -0.150533 / +0.249456 | 162.731 |

The checked comparison is `.local/runs/stg-selfcap-5000-comparison-20260906.json`.
At this earlier checkpoint, Full has higher PSNR/SSIM, while Lite has lower LPIPS and higher measured warm
throughput. Both retain strong blur/ghosting around the moving person; no final
artifact-quality winner is established. Both have byte-exact offline reloads
for all 80 PNGs. Charged training time at that point was 709.725114 seconds for Lite and
816.799333 seconds for Full, including earlier attempts.

[ATGS](009-atgs.md) now has a 5,000-microstep checkpoint (1,666 optimizer updates),
with 676.653776 seconds charged and all 80 offline renders exact in PNG bytes and
raw float hashes. Its moving-person reconstruction remains heavily blurred,
and its metrics trail both current STG baselines. Equal iteration labels do not
mean equal update counts, time budgets or converged quality. Checked ATGS deltas
are `.local/runs/atgs-vs-lite-selfcap-5000-20260906.json` and
`.local/runs/atgs-vs-full-selfcap-5000-20260906.json`.

[FreeTimeGS](007-freetimegs.md) now adds a 5,000-step third-party reproduction
pilot using training-only dense EDGS geometry. It has 567.387962 seconds charged
and exact offline PNG/float reloads for all 80 renders. The inspected dancer,
background and fixed book-text crop remain strongly blurred, with thin colored
streaks/floaters. Checked deltas are
`.local/runs/freetimegs-vs-lite-selfcap-5000-20260906.json` and
`.local/runs/freetimegs-vs-full-selfcap-5000-20260906.json`. Its native 70,000-step
schedule is unfinished. All four results are provisional, not final-budget
rankings; no final artifact-quality winner is established.

## SelfCap dance1 — provisional 2,000-step checkpoints

All metrics cover 60 held-out camera-0015 frames at 1890×1061. Higher PSNR/SSIM
and lower LPIPS are better. Deltas are arithmetic differences, not claims of
statistical significance or matched-budget superiority.

| Method | PSNR dB | SSIM | LPIPS-Alex | Δ vs Lite (PSNR / SSIM / LPIPS) | Δ vs Full (PSNR / SSIM / LPIPS) | Warm FPS |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| STG Lite | 20.095080 | 0.795017 | 0.331961 | 0 / 0 / 0 | −1.969455 / −0.010166 / −0.008994 | 527.717 |
| STG Full | 22.064535 | 0.805183 | 0.340954 | +1.969455 / +0.010166 / +0.008994 | 0 / 0 / 0 | 293.384 |

Both models reload byte-exactly offline for all 60 held-out images and 20 sweep
poses. Both show moving-person blur and ghosting in the sampled sheets; Full's
higher PSNR and SSIM do not translate into lower LPIPS at this stage. Do not
recommend a final winner from these unfinished runs. The growth record links
the full evidence, resource measurements and budget accounting.

## VRU Basketball DG — blocked on synchronization

[Plan 006](basketball-calibration-alternatives.md) accepted all 34 cameras.
[Revision 2](basketball-rev2.md) passed source/calibration/profile provenance,
pixel/distortion conventions and estimated scale validation: frozen scale
1.31506947 estimated metres per calibration unit, with 3.13% reserved-frame
disagreement. The full rig has 30 training cameras and held-outs 0, 10, 20, 30.

Dynamic timing is blocked: 24/71 candidate edges pass, leaving 19 cameras
unreachable from reference camera 1. Forty-five edges exceed the 0.25-frame
uncertainty limit and two lack support. Timing selection/final validation,
preparation, initialization, training and model evaluation remain unexecuted.

| Method | Basketball metrics | Remaining blocker |
| --- | --- | --- |
| STG Lite | Not measured | Validated full-rig synchronization, then shared inputs and fresh initialization |
| [STG Full](006-stg-full.md) | Not measured | Same synchronization/input gates |
| [FreeTimeGS reproduction](007-freetimegs.md) | Not measured | Same gates, then training-only temporal EDGS/RoMa initialization |
| [MoE-GS](008-moe-gs.md) | Not measured | Same gates plus a validated modified-STG expert training route or checkpoint |
| [ATGS](009-atgs.md) | Not measured | Same synchronization/input gates |
| [FreeTimeGS++](010-freetimegs-plus-plus.md) | Not measured | Same gates plus a validated author implementation of fixed B |

Basketball training charges remain zero and each method retains its two-hour
allocation. Revision 2 charged 24.550233 GPU seconds for scale, bringing the
historical calibration ledger to 1,080.637553 seconds; its conditional extension
is unused. These are input-gate results, not method-quality measurements.

## Unexecuted SelfCap methods

| Method | Specific blocker | Training charged | Decision |
| --- | --- | ---: | --- |
| [MoE-GS](008-moe-gs.md) | Modified SH-based STG model/rasterizer source exists, but its standalone released expert-training route or matching pretrained state is unvalidated; router trainers expect pretrained experts | 0 s | Defer until that route or asset is available; original STG Full is not equivalent |
| [FreeTimeGS++](010-freetimegs-plus-plus.md) | No author implementation of fixed B was identified in the recorded source audit | 0 s | Defer until a usable release is identified; paper-only reimplementation is outside scope |

All twelve method/scene pairs now have a reproducible final-budget result or
the specific blocker above, with reports 006–010 and the matched Lite record.
The blocked pairs require validated synchronization or a usable released training
route/implementation; they are not quality failures. Further training beyond
the existing reserve gates requires a new budget decision. No paper-only
implementation, calibration substitution or budget redistribution was performed.

Final validation rechecked both budget-stop evaluations, 80 exact offline views
per method, retained PNG/video/crop evidence, complete 60-frame comparison
records and the ledger's absence of overruns/live reservations. All 167 local
documentation links resolve, 76 Bash blocks in the training/preview guides pass
`bash -n`, and `git diff --check` passes. Earlier integration reports retain
camera/split/time, missing-state, evaluator and regression-test evidence; this
final documentation-only milestone did not change the validated training adapters.

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
