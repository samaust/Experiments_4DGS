# Execution record — 2026-09-06

Plan 004 remains incomplete. Training consumed **0 seconds** of the 24-hour
budget; no matched-scene quality measurements are available yet.

The native STG Lite GPU render succeeded using the absolute interpreter path:

```bash
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-render/bin/python \
  scripts/render-stg-preview.py --checkout .local/SpacetimeGaussians \
  --ply .local/weights/stg-sear-steak/n3d_sear_steak_lite_allcam/point_cloud/iteration_25000/point_cloud.ply \
  --cameras .local/weights/stg-sear-steak/n3d_sear_steak_lite_allcam/cameras.json \
  --output .local/runs/stg-smoke-20260906 --times 0 0.5 0.98
```

All three 1352×1014 PNGs match `.local/runs/stg-native-preview` byte-for-byte.
Evidence: `.local/runs/stg-smoke-20260906/reload-comparison.json`. This was a
fresh process, but network access was not disabled. Earlier approval waits do
not establish a renderer hang or a CUDA failure.

The Full adapter now requires an explicit supported decoder architecture and
the adjacent `.pt` sidecar required by upstream `load_ply`; it creates the ray
image required by the fused kernel. Full checkpoint rendering is still untested.

The evaluator now uses one fixed local SSIM formula, rejects differing PNG
filename sets, preserves infinite PSNR as the JSON string `Infinity`, and reads
LPIPS pairs individually to avoid retaining a whole sequence in RAM. Ten tests
pass under `.local/envs/stg-render/bin/python`, including identity/perturbation
SSIM and failure before CUDA imports for missing Full decoder state. LPIPS has
not yet been validated with the shared evaluator.

## Remaining execution gates

SelfCap source videos and calibration exist under `.local/data/selfcap`.
The v3 manifest records source hashes and offsets but is a source inventory;
it does not yet certify processed images, camera transforms, or synchronization
adaptation. `command -v colmap` finds no native executable. The inspection
`analysis.json` combines different cameras and duplicate naming schemes, so
its adjacency values must not be interpreted as temporal consistency evidence.

Basketball has not been downloaded into `.local/downloads`.

[ATGS source](https://github.com/WuJH2001/ATGS) was downloaded into `.local/ATGS`
at `10388ebf973658a1cee219901a74128148bca051`. It imports `tinycudann`,
`torch_scatter`, and `simple_knn`; its native environment is not built yet.
The supplied hash configuration uses `llffhold=10`, `downsample=2`, and
`open_sync_time=False`, which require an explicit shared-profile audit.
No LICENSE-named file was found in this checkout; source terms need resolution.

[MoE-GS upstream](https://github.com/cvsp-lab/MoE-GS) provides router commands
but still labels expert training scripts as coming soon. Its four experts are
Ex4DGS, E-D3DGS, 4DGaussians, and modified STG with spherical harmonics and the
Ex4DGS rasterizer. Matched expert checkpoints and their training route remain
unresolved for both scenes.

The [FreeTimeGS project](https://zju3dv.github.io/freetimegs/) links a renderer
and framework; a complete matching training path still needs auditing.
[FreeTimeGS++](https://arxiv.org/html/2605.03337v1) implementation availability
and fixed B configuration remain unresolved. Neither is a local result.
