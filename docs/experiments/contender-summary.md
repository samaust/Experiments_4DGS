# Contender comparison summary

Status: **partial execution; matched comparison incomplete**.

Lite and Full have completed their native SelfCap schedules and final evaluations.
ATGS and FreeTimeGS still require continuation within their existing budgets.
MoE-GS and FreeTimeGS++ retain the source gates in their experiment reports;
Basketball remains blocked on matching calibration.

Earlier records cover [initial execution](contender-progress-20260906.md),
[data preparation](contender-data-20260906.md),
[training integration](contender-training-20260906.md),
[growth/offline validation](contender-growth-20260906.md),
[Lite evaluation integration](contender-evaluation-pipeline-20260906.md) and
[Full's 5,000-step pilot](contender-full-5000-20260906.md). Their historical
statuses and measurements are superseded where newer results are given below.

## SelfCap dance1 — completed native STG schedules

Both variants reached 30,000 steps within their individual two-hour limits.
All metrics cover the same 60 camera-0015 frames at 1890×1061. The
[completed STG record](contender-native-stg-20260906.md) contains resource use,
checkpoint hashes, commands, visual findings and evidence paths.

| Method | PSNR dB | SSIM | LPIPS-Alex | Δ vs Lite (PSNR / SSIM / LPIPS) | Δ vs Full (PSNR / SSIM / LPIPS) | Warm FPS |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| STG Lite | 22.418750 | 0.851204 | 0.219363 | 0 / 0 / 0 | -2.078003 / -0.013010 / +0.004752 | 317.056 |
| STG Full | 24.496753 | 0.864213 | 0.214612 | +2.078003 / +0.013010 / -0.004752 | 0 / 0 / 0 | 224.135 |

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

## VRU Basketball DG

No quantitative results yet: the downloaded DG archive has no calibration,
and matching calibration remains unresolved for every method. Do not substitute
another Basketball release's cameras or claim an evaluated result.

The matched comparison is incomplete until experiments 006–010 and the STG Lite
baseline produce reproducible outputs or record a specific method/scene blocker.
Present separate SelfCap dance1 and VRU Basketball tables, including differences
from STG Lite and STG Full. Keep unfinished training and unmatched checkpoints
visible rather than inferring wins or failures.
