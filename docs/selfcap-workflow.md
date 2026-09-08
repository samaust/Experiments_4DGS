# Practical SelfCap reconstruction workflow — 2026-09-08

Choose **STG Full as the default compact, completed-schedule workflow for this retained 60-frame SelfCap dance1 profile**. Its complete checkpoint is about 29.8 MB, its 30,000-step schedule completed, and its saved held-out quality improves on Lite with 224.135 warm FPS. This is a practicality recommendation: Full has substantial excess face/hair and body-boundary blur during fast motion. It does not satisfy a demand for sharp hair or high-fidelity fast motion.

Choose the **dense-initialized FreeTimeGS reproduction** when the measured aggregate image-quality gain and clearer sampled face/body detail justify greater preparation effort, 3.20 GB complete resume state and lower throughput. It leads PSNR/SSIM/LPIPS on this profile but remains at 42,061/70,000 steps, still smears fast hair/forearms, and shows haze in the ending book region. Lite is the fastest measured renderer. ATGS offers locally clearer book lettering, but its foreground artifacts, worse aggregates and large incomplete resume state give no overall reason to prefer it here.

[The final evidence audit](experiments/selfcap-evidence-20260908/audit-02.md), [actual temporal/crop inspection](experiments/selfcap-evidence-20260908/inspection.md), [offline selector](experiments/selfcap-evidence-20260908/inspection.html) and [full contender comparison](experiments/contender-summary.md) support these choices. All metrics use the same 60 held-out camera-0015 frames at 1890×1061. These are measured local adaptations, not a six-method ranking, equal-compute comparison, long-sequence result or full-paper convergence claim.

| Method | PSNR / SSIM / LPIPS-Alex | Warm FPS | Charged training seconds | Complete state bytes | Schedule |
| --- | --- | ---: | ---: | ---: | --- |
| stg-lite | 22.418750 / 0.851204 / 0.219363 | 317.056 | 3819.048855 | 34,044,289 | 30,000 / 30,000 |
| stg-full | 24.496753 / 0.864213 / 0.214612 | 224.135 | 4652.027359 | 29,778,653 | 30,000 / 30,000 |
| freetimegs | 25.496026 / 0.881698 / 0.137213 | 182.781 | 7026.107790 | 3,199,531,938 | 42,061 / 70,000 |
| atgs | 22.180802 / 0.842141 / 0.239707 | 256.625 | 7026.233249 | 3,904,977,664 | 61,008 / 100,000 microsteps; 20,336 updates |

Warm FPS excludes model loading, camera setup, saving and encoding; it uses 10 warmups and 100 samples at camera 0015/frame 4150. Complete state includes optimizer/resume data and is not an inference-only payload. Device-wide sampled peaks (Lite 7,158; Full 7,292; FreeTimeGS 7,532; ATGS 8,633 MiB) differ from allocator peaks and include baselines (833/866/825/792 MiB). Final-continuation wall seconds are 3,109.387550 / 3,835.337033 / 6,460.046399 / 6,349.703736; these are not total charged time. The machine audit retains exact measurement commands, sampled baselines and allocator peak bytes.

## Fixed inputs, source and complete saved state

Run commands from the repository root, retaining `.local/` artifacts. The processed manifest is `.local/data/selfcap/dance1-processed-20260906/manifest.json`, SHA-256 `f9cbfe6b1f01eba1a6b284579985356bc8497955bd18d696a31e4eb166a48199`. It binds 24 cameras and 1,440 images, source frames [4120,4180), 60 FPS, test camera 0015 and 23 training cameras. Dimensions vary by camera. Times are `(frame_id / fps - camera_offset_seconds - origin_seconds) / duration_seconds`, with origin `68.65473750854532` and duration `1.0247243251651525`; do not substitute frame-offset/count.

Sparse training-only midpoint geometry is `.local/data/selfcap/dance1-initialization-20260906/initialization.ply`, SHA-256 `13f1131ccca5f91868999deac74ff8fce1b98661ddf79085ce136c6808222d09`. Its `inputs.json` and `result.json` bind all 23 midpoint images and exclude held-out RGB. FreeTimeGS instead uses `.local/data/selfcap/dance1-freetimegs-edgs-initialization-20260906/initialization.npz`, SHA-256 `e2753700453c55fa59f30fe5d9c14ba74627016445cefb6bc5176019d57de6b4`; `result.json` links 24 training-only keyframe/successor clouds. Its native normalization uses the sparse midpoint reference. Source-video hashes are retained provenance with presence checks, not a fresh video rehash.

STG’s checkout `.local/SpacetimeGaussians` is pinned to `427abfc58309a4a5213843dd673fb22c4529306c`, with the retained Python/CUDA compatibility patch and adapted native training file. The exact native `train.py` bytes are pinned by `scripts/stg_train_source.py`; each run retains its `adapted_train.py`. The separate stack93 `9534842` release-archive audit found a Lite archive and does not identify the Full model used here. Consult [Full source provenance](experiments/006-stg-full.md), [environment setup](environments.md), [STG environment inputs](../environments/stg-render.in), [preparation inputs](../environments/stg-colmap.in), [constraints](../environments/constraints-cu130.txt) and [resolved installed inventory](../.local/runs/evidence-inventory-20260905/stg-render-installed.txt). These are resolved snapshots, not a completely hash-locked installer.

FreeTimeGS source/environment pins and `uv.lock` are documented in [its native-build record](experiments/007-freetimegs.md); checkout `.local/FreeTimeGsVanilla` revision `911dcf4157a3ddf5c96d9147f97627480268fe0f` with its retained `uv.lock`, environment `.local/envs/freetimegs`. ATGS uses `.local/ATGS` revision `10388ebf973658a1cee219901a74128148bca051` and `.local/envs/atgs`; [its build record](experiments/009-atgs.md) identifies explicitly pinned replacement dependencies and compatibility changes. The audit checks recorded FreeTimeGS AST/config/source identities and gsplat/fused-SSIM binaries, and ATGS configuration source hashes/helper ASTs/renderer/indexed extension bytes/package metadata. Current indexed source bytes match retained evidence. Historical STG native-binary attestation is unavailable. No new GPU reload or environment build was performed in this audit.

Complete models and exact current hashes:

- **stg-lite:** `.local/runs/stg-lite-selfcap-final-20260906/checkpoint.pt` — SHA-256 `8eac0b3373167db5ff2e5a17c757e9fe5938e60f4b0c8ad55820eff5b9d20d9c`, 34,044,289 bytes.
- **stg-full:** `.local/runs/stg-full-selfcap-final-20260906/checkpoint.pt` — SHA-256 `1c810245d4faa182df201eaf00372b8dd7bc23b6e5a2ae8c1f7d0fb8a461a65a`, 29,778,653 bytes.
- **freetimegs:** `.local/runs/freetimegs-selfcap-final-20260906/checkpoint-042061.pt` — SHA-256 `49d732ee75bbc85863acf4eb4b621683b3df51720a69d9e536197fa2a66f7856`, 3,199,531,938 bytes.
- **atgs:** `.local/runs/atgs-selfcap-final-20260906/checkpoint-061008-011/bundle.json` — SHA-256 `7e4d1157c133e7ec57b53aeeb11ef4b66c7cd38aec82ed956021941a39e3f621`, 1,969 bytes (marker only; preserve all 11 indexed components totaling 3,904,977,664 bytes).

STG Full’s `checkpoint.pt` contains Gaussian/spacetime parameters, temporal features and appearance decoder, optimizer, buffers, RNG and loop state. A Gaussian PLY alone omits needed appearance/state. FreeTimeGS’s checkpoint includes temporal positions/velocity/duration parameters, SH, optimizers/scheduler, strategy/relocation accumulators, source/config, RNG and sampler state. ATGS requires `bundle.json` **and all 11 adjacent components**: `point_cloud.ply`, four MLPs, `voxel_grid.pth`, `FDHash.pth`, both optimizers, `auxiliary.pth` and `loop.pth`. Preserve complete directories and their configuration/provenance. These requirements follow [STG loader](../scripts/stg_checkpoint.py), [FreeTimeGS loader](../scripts/freetimegs_checkpoint.py) and [ATGS bundle loader](../scripts/atgs_bundle.py); the audit hashes files without deserializing the large models.

## Preparation and training reproduction

The existing prepared artifacts above are the exact inputs for the saved models. Preparation to a new directory, when needed under applicable authorization:

```bash
.local/envs/stg-colmap/bin/python scripts/prepare-selfcap.py --videos .local/data/selfcap/hair-release/videos --calibration .local/data/selfcap/hair-calib/optimized --output .local/data/selfcap/dance1-processed-NEW
.local/envs/stg-colmap/bin/python scripts/initialize-selfcap.py --manifest .local/data/selfcap/dance1-processed-NEW/manifest.json --output .local/data/selfcap/dance1-initialization-NEW --frame-id 4150
```

Validate hashes, camera membership/splits, timing/calibration and image sizes before training; the original SelfCap [preparation record](experiments/contender-data-20260906.md) describes those gates. New preparation can change metadata such as wall time and output paths, so do not substitute its manifest into an old checkpoint’s provenance. For FreeTimeGS dense initialization, follow the training-only EDGS keyframe/successor commands and exclusion gates in [the retained initialization record](experiments/007-freetimegs.md); this was a local EDGS adaptation, not the author FreeTimeGS initializer.

The historical final-continuation commands below reproduce the saved lineage from their explicitly named earlier checkpoints. They are **procedures, not authorization to launch more training**. Preserve `.local/runs/plan-004-training-budget.json`: 7,200 seconds per method/scene and 24 hours global, failures included, no redistribution. Do not reset that ledger or silently drop `--resume`. Lite/Full completed schedules; FreeTimeGS and ATGS have only about 173.89/173.77 seconds left, below the existing 185-second restart/reserve gate. More training requires new authorization. All exact original commands, configurations and worker results remain in the [machine audit](experiments/selfcap-evidence-20260908/audit.json); only output destinations below use new names.

**stg-lite final continuation:** configuration `.local/runs/stg-lite-selfcap-final-20260906/training-config.json`, provenance `.local/runs/stg-lite-selfcap-final-20260906/provenance.json`.

```bash
.local/envs/stg-render/bin/python scripts/train-stg-manifest.py --checkout .local/SpacetimeGaussians --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --initialization .local/data/selfcap/dance1-initialization-20260906 --output .local/runs/stg-lite-selfcap-reproduction-NEW --model lite --resume .local/runs/stg-lite-selfcap-5000-20260906/checkpoint.pt
```

**stg-full final continuation:** configuration `.local/runs/stg-full-selfcap-final-20260906/training-config.json`, provenance `.local/runs/stg-full-selfcap-final-20260906/provenance.json`.

```bash
.local/envs/stg-render/bin/python scripts/train-stg-manifest.py --checkout .local/SpacetimeGaussians --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --initialization .local/data/selfcap/dance1-initialization-20260906 --output .local/runs/stg-full-selfcap-reproduction-NEW --model full --resume .local/runs/stg-full-selfcap-5000-20260906/checkpoint.pt
```

**freetimegs final continuation:** configuration `.local/runs/freetimegs-selfcap-final-20260906/training-config.json`, provenance `.local/runs/freetimegs-selfcap-final-20260906/provenance.json`.

```bash
.local/envs/freetimegs/bin/python scripts/train-freetimegs-manifest.py --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --initialization .local/data/selfcap/dance1-freetimegs-edgs-initialization-20260906 --reference-cloud .local/data/selfcap/dance1-initialization-20260906 --torch-cache .local/cache/torch --output .local/runs/freetimegs-selfcap-reproduction-NEW --resume .local/runs/freetimegs-selfcap-5000-20260906/checkpoint-005000.pt --checkpoint-interval 5000
```

**atgs final continuation:** configuration `.local/runs/atgs-selfcap-final-20260906/training-config.json`, provenance `.local/runs/atgs-selfcap-final-20260906/provenance.json`.

```bash
.local/envs/atgs/bin/python scripts/train-atgs-manifest.py --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --initialization .local/data/selfcap/dance1-initialization-20260906 --output .local/runs/atgs-selfcap-reproduction-NEW --resume .local/runs/atgs-selfcap-5000-20260906/checkpoint-005000-004 --checkpoint-interval 5000
```

## Exact-model offline reload and evaluation

With the retained inputs, matching source and installed environment, this STG Full command renders all 60 held-out times and the shared 20-pose frozen-midpoint sweep. Choose genuinely new output directory names; never overwrite a retained run. The following commands are copyable procedures checked against parsers and shell syntax; they were not executed during this saved-evidence milestone.

```bash
.local/envs/stg-render/bin/python scripts/offline-python.py scripts/render-stg-manifest.py --checkout .local/SpacetimeGaussians --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --checkpoint .local/runs/stg-full-selfcap-final-20260906/checkpoint.pt --output .local/runs/stg-full-selfcap-user-evaluation-NEW/reload-a --benchmark
```

```bash
.local/envs/stg-render/bin/python scripts/offline-python.py scripts/render-stg-manifest.py --checkout .local/SpacetimeGaussians --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --checkpoint .local/runs/stg-full-selfcap-final-20260906/checkpoint.pt --output .local/runs/stg-full-selfcap-user-evaluation-NEW/reload-b
```

```bash
.local/envs/stg-render/bin/python scripts/compare-render-reloads.py --first .local/runs/stg-full-selfcap-user-evaluation-NEW/reload-a/images/0015 --second .local/runs/stg-full-selfcap-user-evaluation-NEW/reload-b/images/0015 --expected-count 60 --output .local/runs/stg-full-selfcap-user-evaluation-NEW/compare-heldout.json
```

```bash
.local/envs/stg-render/bin/python scripts/compare-render-reloads.py --first .local/runs/stg-full-selfcap-user-evaluation-NEW/reload-a/sweep --second .local/runs/stg-full-selfcap-user-evaluation-NEW/reload-b/sweep --expected-count 20 --output .local/runs/stg-full-selfcap-user-evaluation-NEW/compare-sweep.json
```

```bash
.local/envs/stg-render/bin/python scripts/offline-python.py scripts/evaluate-reconstruction.py --predictions .local/runs/stg-full-selfcap-user-evaluation-NEW/reload-a/images/0015 --ground-truth .local/data/selfcap/dance1-processed-20260906/images/0015 --output .local/runs/stg-full-selfcap-user-evaluation-NEW/metrics.json --lpips-alex
```

STG comparisons establish quantized PNG equality. For the complete orchestration with the fixed crop package, use a different new destination:

```bash
.local/envs/stg-render/bin/python scripts/evaluate-stg-checkpoint.py --checkout .local/SpacetimeGaussians --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --checkpoint .local/runs/stg-full-selfcap-final-20260906/checkpoint.pt --crops configs/detail-crops.selfcap-dance1.json --torch-cache .local/cache/torch --output .local/runs/stg-full-selfcap-user-complete-evaluation-NEW
```

Alternative exact-model reloads (their renderers install offline restrictions internally):

```bash
.local/envs/freetimegs/bin/python scripts/render-freetimegs-manifest.py --checkout .local/FreeTimeGsVanilla --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --checkpoint .local/runs/freetimegs-selfcap-final-20260906/checkpoint-042061.pt --training-config .local/runs/freetimegs-selfcap-final-20260906/training-config.json --provenance .local/runs/freetimegs-selfcap-final-20260906/provenance.json --output .local/runs/freetimegs-selfcap-user-evaluation-NEW/reload-a --benchmark
```

Repeat with `reload-b` as output, then use the `compare-heldout`, `compare-sweep` and `metrics` argv in [the saved freetimegs commands](../.local/runs/freetimegs-selfcap-final-evaluation-20260906/commands.json), replacing only the evaluation output prefix with `freetimegs-selfcap-user-evaluation-NEW`. Preserve the exact checkpoint/configuration/provenance arguments. The saved FreeTimeGS/ATGS renderer records also contain historical raw-float hashes; they were not recomputed here.

```bash
.local/envs/atgs/bin/python scripts/render-atgs-manifest.py --checkout .local/ATGS --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --checkpoint .local/runs/atgs-selfcap-final-20260906/checkpoint-061008-011 --training-config .local/runs/atgs-selfcap-final-20260906/training-config.json --provenance .local/runs/atgs-selfcap-final-20260906/provenance.json --output .local/runs/atgs-selfcap-user-evaluation-NEW/reload-a --benchmark
```

Repeat with `reload-b` as output, then use the `compare-heldout`, `compare-sweep` and `metrics` argv in [the saved atgs commands](../.local/runs/atgs-selfcap-final-evaluation-20260906/commands.json), replacing only the evaluation output prefix with `atgs-selfcap-user-evaluation-NEW`. Preserve the exact checkpoint/configuration/provenance arguments. The saved FreeTimeGS/ATGS renderer records also contain historical raw-float hashes; they were not recomputed here.

## Candidate and Basketball boundary

There are four evaluated SelfCap pairs and eight blocked pairs. **MoE-GS:** retained availability audit dated 2026-09-06 found no validated standalone training route or matching pretrained state for its modified SH-based STG expert. Its model/rasterizer code exists; ordinary STG Full is not a compatible replacement, and its router entry points expect pretrained experts. **FreeTimeGS++:** the 2026-09-06 retained release audit identified no author implementation for fixed configuration B. These are availability/integration blockers for both profiles, with no online refresh in this milestone; they are not quality failures.

Basketball is currently blocked by [Plan 016/v10’s scientific rejection](experiments/basketball-shared-timing-v10.md), with [accepted timing null](experiments/basketball-shared-timing-v10/package/terminal-decision.json). Accepted static calibration covers all 34 cameras; estimated scale is 1.31506947 metres per calibration unit, with held-outs 0/10/20/30 and 30 training cameras. The older 23-camera and v4/v5/v6 pilot statuses are historical. No accepted timing means no validated final Basketball preparation, initialization, reconstruction or method ranking.

The next necessary Basketball numerical phase requires **user-approved concrete scope, elapsed-time cap and attempt caps**. Plan 016’s five 81-attempt policies and six preflight allocations are consumed; its 90-minute window cannot restart. No numerical total is proposed for an unspecified solver. Unspent training/calibration allocations do not authorize timing experiments; full screens/final validation still require scientific gates. Coverage by a result or a specific blocker does not achieve the reconstruction objective.
