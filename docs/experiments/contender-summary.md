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
