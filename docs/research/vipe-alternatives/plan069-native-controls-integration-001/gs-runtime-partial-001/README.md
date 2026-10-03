# CPU preparation of the existing FreeTimeGS runtime

All eight mandatory installed dependency records are present and frozen:
Torch 2.13.0+cu130, NumPy 2.5.2, SciPy 1.18.1, Pillow 12.3.0,
torchvision 0.28.0+cu130, torchmetrics 1.9.0, gsplat 1.5.3, fused-ssim 0.0.0.
Each exact METADATA/RECORD pair belongs to the selected existing environment:
`/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/freetimegs`.

Its explicit interpreter invocation is `.../bin/python`; its pinned file record
resolves to `/usr/bin/python3.14`. Both within-environment native binary records
exist: `gsplat/csrc.so` and `fused_ssim_cuda.cpython-314-x86_64-linux-gnu.so`.
The documented Torch cache already contains the required offline checkpoint:
`/home/auss/git_repos/samaust/Experiments_4DGS/.local/cache/torch/hub/checkpoints/alexnet-owt-7be5be79.pth`
(244,408,911 bytes; SHA256
`7be5be791159472b1fbf3c69796f7cb30dca7ad8466c2df70058c37116cdee02`).

All 20 runtime file records were independently rehashed after preparation.
No package installation, native library import, model/GPU/network operation or
live ledger write occurred. This directory alone was written. Existing source
preparation is retained in `../gs-inventory-audit-001/source-inventory.json`.

**The sole missing assembly input is the resolved native configuration.** It
must bind the actual selected D* scene, positive similarity normalization and
historical normalized scene scale, exact native default-keyframe configuration
and typed frame interval 0/50. That choice is still pending. Do not invent a
configuration or call this partial preparation a qualified runtime inventory.
Once supplied, use these exact records with canonical `prepare_inventory` and a
fresh immutable output path, then qualify the combined sources/runtime. #34/#35
remain open; these files grant no native execution authority.
