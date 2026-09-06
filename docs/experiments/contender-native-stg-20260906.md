# Completed native STG schedules on SelfCap

Both matched STG variants completed their native 30,000-step schedules on
2026-09-06. Each resumed its existing iteration-5,000 checkpoint with the same
source, configuration, seed and shared SelfCap manifest. No training allocation
was redistributed. Basketball remains blocked on matching calibration.

## Results and resources

All metrics cover 60 camera-0015 frames at 1890×1061. Warm throughput uses ten
warmups followed by 100 synchronized renders, excluding loading and image saving.

| Measurement | STG Lite | STG Full |
| --- | ---: | ---: |
| Completed iteration | 30,000 | 30,000 |
| Final Gaussians | 72,587 | 50,607 |
| PSNR dB | 22.418750 | 24.496753 |
| SSIM | 0.851204 | 0.864213 |
| LPIPS-Alex | 0.219363 | 0.214612 |
| Warm FPS | 317.056 | 224.135 |
| Continuation command wall | 3109.387550 s | 3835.337033 s |
| Total charged training, including earlier attempts | 3819.048855 s | 4652.027359 s |
| Per-scene training limit | 7200 s | 7200 s |
| Device baseline / sampled peak | 833 / 7158 MiB | 866 / 7292 MiB |
| Framework peak allocated bytes | 1,128,926,208 | 1,265,730,560 |
| Framework peak reserved bytes | 6,266,290,176 | 6,148,849,664 |
| Complete checkpoint bytes | 34,044,289 | 29,778,653 |
| Evaluation wall | 162.867046 s | 161.512231 s |

Device sampling is every 200 ms with a two-second baseline and can miss brief
peaks. Framework allocator statistics and device-wide measurements have different
coverage and should not be treated as interchangeable.

Checked aggregate and per-frame comparison:
`.local/runs/stg-selfcap-final-comparison-20260906.json`. Full minus Lite is
+2.078003 dB PSNR, +0.013010 SSIM and -0.004752 LPIPS-Alex. Both native schedules
are complete, although charged training time and final model size differ.

## Reload and visual evidence

Each variant passed two fresh network-disabled reloads with byte-exact PNGs for
all 60 held-out frames and 20 frozen-time sweep poses. The STG evaluator checks
quantized PNG bytes/pixels; raw floating-point render equality was not measured.
The earlier summary's claim of Lite float equality has been corrected.

Evidence directories:

- `.local/runs/stg-lite-selfcap-final-evaluation-20260906/evidence`
- `.local/runs/stg-full-selfcap-final-evaluation-20260906/evidence`

Both contain PNG sequences, MP4s, contact sheets, the fixed ground-truth-selected
crops, camera/time metadata and sequence diagnostics. Full's start/middle/end
predictions were inspected beside ground truth at frames 4120, 4150 and 4179,
along with the body-boundary and book-text crops and sweep poses 0, 10 and 19.
Shelves and book spines are recognizable, but small text remains soft. Full's
head/hair and arm/hand boundaries are strongly blurred or ghosted at 4120 and
4150 relative to the reference; the slower pose at 4179 is better represented.
The midpoint sweep retains these foreground failures. Sampled sheets do not
establish a flicker ranking. Lite's completed evidence likewise retains strong
motion blur. Full's metric improvement therefore does not establish sharp
reconstruction of the fastest motion; Lite retains higher measured throughput.

## Artifacts and reproduction

Run directories follow `.local/runs/stg-VARIANT-selfcap-final-20260906`,
measurements `.local/runs/stg-VARIANT-selfcap-final-measurement-20260906`, and
evaluations `.local/runs/stg-VARIANT-selfcap-final-evaluation-20260906`.
Each run retains configuration, source/input provenance, loss and point logs,
the resumable `checkpoint.pt`, and final inference exports. Full includes its
appearance decoder state.

Checkpoint SHA-256:

- Lite: `8eac0b3373167db5ff2e5a17c757e9fe5938e60f4b0c8ad55820eff5b9d20d9c`
- Full: `1c810245d4faa182df201eaf00372b8dd7bc23b6e5a2ae8c1f7d0fb8a461a65a`

The exact Full continuation and evaluation commands are recorded below. Existing
directories must be retained; use new output names for a new execution, and
respect the shared ledger's remaining allocation. The [training guide](../local-creation.md)
also records the Lite continuation.

```bash
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-render/bin/python scripts/measure-experiment.py --output .local/runs/stg-full-selfcap-final-measurement-20260906 --cwd /home/auss/git_repos/samaust/Experiments_4DGS -- /home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-render/bin/python scripts/train-stg-manifest.py --checkout .local/SpacetimeGaussians --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --initialization .local/data/selfcap/dance1-initialization-20260906 --output .local/runs/stg-full-selfcap-final-20260906 --model full --resume .local/runs/stg-full-selfcap-5000-20260906/checkpoint.pt
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-render/bin/python scripts/evaluate-stg-checkpoint.py --checkout .local/SpacetimeGaussians --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --checkpoint .local/runs/stg-full-selfcap-final-20260906/checkpoint.pt --crops configs/detail-crops.selfcap-dance1.json --torch-cache .local/cache/torch --output .local/runs/stg-full-selfcap-final-evaluation-20260906
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-render/bin/python scripts/compare-stg-evaluations.py --first .local/runs/stg-lite-selfcap-final-evaluation-20260906 --second .local/runs/stg-full-selfcap-final-evaluation-20260906 --output .local/runs/stg-selfcap-final-comparison-20260906.json
```
