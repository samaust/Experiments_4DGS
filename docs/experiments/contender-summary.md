# Contender comparison summary

Status: **partial execution; matched comparison incomplete**.

See the [2026-09-06 execution record](contender-progress-20260906.md) for the
successful native Lite regression render, evaluator fixes, and current gates.
The subsequent [data preparation record](contender-data-20260906.md) supersedes
its missing-Basketball and missing-pycolmap statuses and adds benchmark evidence.
The [training integration record](contender-training-20260906.md) now supersedes
the earlier not-started status for STG Lite and Full on SelfCap: both completed
short, budget-counted training/resume checks. Full's held-out rendering path
also executed. Long training remains incomplete.
The [growth/offline record](contender-growth-20260906.md) adds the EMS fix,
Lite and Full iteration-2000 metrics, fixed visual evidence, and exact offline reload
for all held-out frames and sweep poses. These are provisional results, not
completion of the allocated two-hour experiments.
The [evaluation-pipeline continuation](contender-evaluation-pipeline-20260906.md)
extends Lite to iteration 5000 and adds strict reload comparison and an automated
offline evaluation workflow. The equal-step table below remains the historical
iteration-2000 comparison; it must not be relabeled as final-budget results.
At iteration 5000, Lite measures 22.082603 dB PSNR, 0.827138 SSIM and
0.270207 LPIPS-Alex, with 449.311 FPS warm rendering. All 80 reload PNGs
remain byte-exact. The [Full continuation](contender-full-5000-20260906.md)
now reaches the same iteration and adds timed evaluation plus checked per-frame
and aggregate deltas.

## SelfCap dance1 — provisional 5,000-step checkpoints

Same 60 held-out camera-0015 frames, shared metric protocol and 1890×1061
resolution. Both remain incomplete; equal steps do not mean equal budget usage.

| Method | PSNR dB | SSIM | LPIPS-Alex | Δ vs Lite (PSNR / SSIM / LPIPS) | Δ vs Full (PSNR / SSIM / LPIPS) | Warm FPS |
| --- | ---: | ---: | ---: | --- | --- | ---: |
| STG Lite | 22.082603 | 0.827138 | 0.270207 | 0 / 0 / 0 | −1.370350 / −0.005722 / −0.008946 | 449.311 |
| STG Full | 23.452953 | 0.832861 | 0.279153 | +1.370350 / +0.005722 / +0.008946 | 0 / 0 / 0 | 275.750 |
| ATGS | 21.637782 | 0.802142 | 0.341477 | -0.444821 / -0.024997 / +0.071270 | -1.815171 / -0.030719 / +0.062324 | 281.242 |

The checked comparison is `.local/runs/stg-selfcap-5000-comparison-20260906.json`.
Full has higher PSNR/SSIM, while Lite has lower LPIPS and higher measured warm
throughput. Both retain strong blur/ghosting around the moving person; no final
artifact-quality winner is established. Both have byte-exact offline reloads
for all 80 PNGs. Total charged training time is 709.725114 seconds for Lite and
816.799333 seconds for Full, including earlier attempts.

[ATGS](009-atgs.md) now has a 5,000-microstep checkpoint (1,666 optimizer updates),
with 676.653776 seconds charged and all 80 offline renders exact in PNG bytes and
raw float hashes. Its moving-person reconstruction remains heavily blurred,
and its metrics trail both current STG baselines. Equal iteration labels do not
mean equal update counts, time budgets or converged quality. Checked ATGS deltas
are `.local/runs/atgs-vs-lite-selfcap-5000-20260906.json` and
`.local/runs/atgs-vs-full-selfcap-5000-20260906.json`. All three are provisional.

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
