# D8 exact installed commercial permission findings

## Assessed operation

Private commercial inference and depth/point-map image generation on the
existing owned RTX 4090 workstation, using the exact pinned MetricAnything
Student PointMap model and the recovered D8 runtime
(`plan069-D8-setup-recovery-001`). Not assessed: redistribution of software,
weights or environment; hosted services; datacenter deployment; training;
rights in input media; output copyrightability.

## Findings

- **Code — allowed.** Pinned `metric-anything` LICENSE (revision
  `616a5e6762f5fc40d1a4ef990fee04c800532f59`) is Apache-2.0 (Copyright 2026
  Li Auto Inc.). Bundled DINOv2 files carry Meta Apache-2.0 headers; MoGe-derived
  files follow upstream microsoft/MoGe (MIT plus Apache-2.0). utils3d (revision
  3fab839f) is MIT. All permit the operation; the missing bundled MoGe MIT notice
  matters only for redistribution (out of scope).
- **Weights — allowed.** The model card at revision
  `8f1f08c53c683d4e19864601dfaf78515f29a63b` declares `license: apache-2.0` with no
  additional use, field-of-use or output restriction (matches survey row
  `i38-metricanything-pointmap`).
- **Dependencies — allowed.** All 90 installed distributions in the capture
  manifest were reviewed (182 license files read): 71 permissive (MIT/BSD/
  Apache/ISC/PSF, including torch 2.14.1+cu130 and the added moderngl/glcontext),
  3 MPL-2.0 used unmodified (certifi, orjson, tqdm), and 14 NVIDIA proprietary
  CUDA/cuDNN/cuSPARSELt wheels under the CUDA Toolkit SLA / NVIDIA SDK License,
  which grant install and use subject to: NVIDIA-GPU systems only (satisfied),
  no reverse engineering or DRM circumvention, no open-source relicensing, no
  life-critical use without agreement. The cuda-toolkit meta-package installs no
  code. Bundled GPL/LGPL components (libgfortran with GCC exception, FFmpeg,
  FreeType) carry distribution-only obligations.
- **Inference outputs — allowed.** Neither Apache-2.0, MIT nor the NVIDIA terms
  restrict generated outputs; the card adds no output terms.

Independent review: read-only license reviewer (Claude agent), 90/90 packages,
182 license files, no blockers or unresolved items.
