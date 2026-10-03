# D11 exact installed commercial permission findings

## Assessed operation

Private commercial inference and depth-image generation on the existing owned
RTX 4090 workstation, using the exact pinned Marigold V2 Log-stage2 adapter,
Qwen-Image-Edit-2509 base and prepared D11 runtime. This assessment concerns
copyright/software-license permission for that operation. It does not assess
redistributing runtimes, hosted services, datacenter deployment, codec patent
clearance, critical applications or rights in input media.

Pinned Marigold source LICENSE is Apache-2.0. Exact Marigold model card revision
cdf9810fb690886391a63aec012b5f501064fb0d releases its weights under Apache-2.0
and preserves the base model's own terms. Exact Qwen card revision
d3968ef930e841f4c73640fb8afa3b306a78167e declares Apache-2.0. These terms permit
commercial execution of the code/weights; no additional noncommercial or
output-specific restriction was identified. Ordinary generated depth images
are not automatically copies of the software merely because the software
produced them. This output finding does not establish general ownership or
third-party input rights. Source and card bytes/URLs are bound in the manifest.

## Installed dependency findings

All 109 installed distributions are included. Full inventory revalidation checked
31,986 file hashes and lengths (8,313,698,601 bytes); active no-extra Requires-Dist
closure checked 177 edges. Exact delivered notices, metadata and native binaries
are bound separately with the full inventory/lock. Native package qualification
uses only metadata with the prepared absolute interpreter; it imports no model
and performs no CUDA operation. These checks do not certify loading, peak GPU
memory, timing or output quality.

Independent read-only reviewer runtime_resume/d11_license_review checked the
installed NVIDIA and major native bundle terms and found no blocker for the
stated owned-workstation private commercial operation:

- NVIDIA CUDA 12.8-family, cuFile, NVSHMEM, cuDNN and cuSPARSELt grant install/use,
  with NVIDIA platform/GPU restrictions satisfied here. cuda-bindings 12.9.4 has
  NVIDIA-only application and modification/reverse-engineering restrictions;
  assessed unmodified local inference fits that scope. These are proprietary
  dependencies; MIT/Apache model terms do not replace their terms.
- Torch/torchvision and Triton have BSD/MIT licenses plus bundled notices.
  bitsandbytes is MIT; Diffusers, Transformers, Accelerate, PEFT, HF Hub and
  safetensors are Apache-2.0. Full delivered notices remain authoritative.
- NumPy/SciPy include BSD/OpenBLAS/LAPACK and GCC runtime-library exceptions,
  with LGPL libquadmath. Private commercial execution is permitted; software
  distribution entails separate obligations.
- OpenCV headless includes MIT package terms, LGPL FFmpeg and Intel IPP
  unmodified binary-use terms. Its Qt notice applies to non-headless packages;
  no Qt dependency is claimed for this headless wheel.
- Pillow has MIT-CMU plus codec notices; h5py/HDF5 allow commercial purposes;
  PyArrow is Apache-2.0 plus bundled third-party terms. NCCL is BSD and NVTX
  Apache-2.0. No private commercial execution blocker was identified.
- certifi MPL-2.0, tqdm MPL-2.0/MIT and regex Apache-2.0/CNRI-Python permit
  execution; their software redistribution requirements remain separate.
- LPIPS wheel LICENSE is BSD-2-Clause despite UNKNOWN metadata. Jinja2,
  markdown-it-py, mdurl, OmegaConf, safetensors and Triton have delivered
  permissive notices despite absent metadata license strings. Missing notices
  for ANTLR 4.9.3, tokenizers 0.22.2, tqdm 4.67.3 and tensorboard-data-server
  0.7.2 are supplemented by bound primary upstream license research and exact
  installed metadata. TensorBoard's 2.20.0 Apache license cross-check supports
  the data-server's explicit Apache metadata; it is not a claim that the
  server's independent version is 2.20.0.

Installed NVIDIA driver libcuda 595.91.07 and its package copyright were rehashed
from previously assessed host records. Its own-use/owned infrastructure and
NVIDIA-platform grants support this local inference scope. Commercial hosting
and GeForce datacenter deployment are outside that grant assessment. The driver
terms are separate from CUDA wheel terms. Host /usr/bin/ffmpeg and ffprobe,
linked host libraries and notices were revalidated from the prior host manifest.
The GPL-enabled host tools run as separate processes; private commercial
execution and ordinary clip output are permitted, without a binary
redistribution or codec-patent clearance claim.

The official CUDA 12.8 EULA corroborates platform/use restrictions; its current
wording differs from the older text delivered in these wheels. Retain exact
installed texts and the official cross-check. The SDK artifact reverse-
engineering restriction does not apply to simply generating depth images
without reverse-engineering SDK output for non-NVIDIA platforms.

## Exact distribution index

This table indexes installed versions and metadata strings. Delivered notice
files and primary supplemental licenses, rather than metadata alone, support
the findings above. The dependency manifest binds each selected file hash.

| Distribution | Version | Metadata license (first line) | Delivered notice files |
|---|---|---|---:|
| absl-py | 2.5.0 | Apache-2.0 | 1 |
| accelerate | 1.13.0 | Apache | 1 |
| annotated-doc | 0.0.5 | MIT | 1 |
| annotated-types | 0.8.0 | MIT | 1 |
| antlr4-python3-runtime | 4.9.3 | BSD | 0 |
| anyio | 4.15.1 | MIT | 1 |
| bitsandbytes | 0.49.2 | MIT | 1 |
| certifi | 2026.7.22 | MPL-2.0 | 1 |
| charset-normalizer | 3.5.2 | MIT | 1 |
| click | 8.5.0 | BSD-3-Clause | 1 |
| cloudpickle | 3.1.2 | BSD-3-Clause | 1 |
| contourpy | 1.3.3 | BSD 3-Clause License | 1 |
| cuda-bindings | 12.9.4 | LicenseRef-NVIDIA-SOFTWARE-LICENSE | 1 |
| cuda-pathfinder | 1.8.3 | Apache-2.0 | 1 |
| cycler | 0.12.1 | Copyright (c) 2015, matplotlib project | 1 |
| diffusers | 0.38.0 | Apache 2.0 License | 1 |
| filelock | 4.0.9 | MIT | 1 |
| fonttools | 4.66.1 | MIT | 2 |
| fsspec | 2026.9.0 | BSD-3-Clause | 1 |
| gitdb | 4.0.12 | BSD License | 1 |
| GitPython | 3.2.0 | BSD-3-Clause | 1 |
| grpcio | 1.84.0 | Apache-2.0 | 1 |
| h11 | 0.16.0 | MIT | 1 |
| h5py | 3.16.0 | BSD-3-Clause | 3 |
| hf-xet | 1.6.0 | Apache-2.0 | 1 |
| httpcore | 1.0.9 | BSD-3-Clause | 1 |
| httpx | 0.28.1 | BSD-3-Clause | 1 |
| huggingface_hub | 1.8.0 | Apache-2.0 | 1 |
| idna | 3.20 | BSD-3-Clause | 1 |
| ImageIO | 2.38.0 | BSD-2-Clause | 1 |
| importlib_metadata | 9.0.1 | Apache-2.0 | 1 |
| Jinja2 | 3.1.6 | None | 1 |
| joblib | 1.6.0 | BSD-3-Clause | 1 |
| kiwisolver | 1.5.1 | ========================= | 1 |
| lazy-loader | 0.6 | BSD-3-Clause | 1 |
| lpips | 0.1.4 | UNKNOWN | 1 |
| Markdown | 3.11 | BSD-3-Clause | 1 |
| markdown-it-py | 4.2.0 | None | 2 |
| MarkupSafe | 3.0.4 | BSD-3-Clause | 1 |
| matplotlib | 3.10.8 | License agreement for matplotlib versions 1.3.0 and later | 3 |
| mdurl | 0.1.2 | None | 1 |
| mpmath | 1.3.0 | BSD | 1 |
| networkx | 3.6.1 | BSD-3-Clause | 1 |
| numpy | 2.2.5 | Copyright (c) 2005-2024, NumPy Developers. | 4 |
| nvidia-cublas-cu12 | 12.8.4.1 | NVIDIA Proprietary Software | 1 |
| nvidia-cuda-cupti-cu12 | 12.8.90 | NVIDIA Proprietary Software | 1 |
| nvidia-cuda-nvrtc-cu12 | 12.8.93 | NVIDIA Proprietary Software | 1 |
| nvidia-cuda-runtime-cu12 | 12.8.90 | NVIDIA Proprietary Software | 1 |
| nvidia-cudnn-cu12 | 9.10.2.21 | LicenseRef-NVIDIA-Proprietary | 1 |
| nvidia-cufft-cu12 | 11.3.3.83 | NVIDIA Proprietary Software | 1 |
| nvidia-cufile-cu12 | 1.13.1.3 | NVIDIA Proprietary Software | 1 |
| nvidia-curand-cu12 | 10.3.9.90 | NVIDIA Proprietary Software | 1 |
| nvidia-cusolver-cu12 | 11.7.3.90 | NVIDIA Proprietary Software | 1 |
| nvidia-cusparse-cu12 | 12.5.8.93 | NVIDIA Proprietary Software | 1 |
| nvidia-cusparselt-cu12 | 0.7.1 | NVIDIA Proprietary Software | 1 |
| nvidia-nccl-cu12 | 2.27.5 | BSD-3-Clause | 1 |
| nvidia-nvjitlink-cu12 | 12.8.93 | NVIDIA Proprietary Software | 1 |
| nvidia-nvshmem-cu12 | 3.4.5 | LicenseRef-NVIDIA-Proprietary | 1 |
| nvidia-nvtx-cu12 | 12.8.90 | Apache 2.0 | 1 |
| omegaconf | 2.3.0 | None | 1 |
| opencv-python-headless | 4.13.0.92 | Apache 2.0 | 5 |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause | 3 |
| pandas | 2.3.3 | BSD 3-Clause License | 1 |
| peft | 0.18.1 | Apache | 1 |
| pillow | 12.1.1 | MIT-CMU | 1 |
| platformdirs | 4.12.2 | MIT | 1 |
| protobuf | 7.36.2 | 3-Clause BSD License | 1 |
| psutil | 7.2.2 | BSD-3-Clause | 1 |
| pyarrow | 18.0.0 | Apache Software License | 2 |
| pydantic | 2.13.5 | MIT | 1 |
| pydantic_core | 2.46.5 | MIT | 1 |
| Pygments | 2.21.0 | BSD-2-Clause | 1 |
| pyparsing | 3.3.3 | MIT | 1 |
| python-dateutil | 2.9.0.post0 | Dual License | 1 |
| pytz | 2026.4 | MIT | 1 |
| PyYAML | 6.0.3 | MIT | 1 |
| regex | 2026.9.29 | Apache-2.0 AND CNRI-Python | 1 |
| requests | 2.34.2 | Apache-2.0 | 2 |
| rich | 15.0.0 | MIT | 1 |
| safetensors | 0.8.0 | None | 1 |
| scikit-image | 0.25.2 | Files: * | 1 |
| scikit-learn | 1.7.2 | BSD-3-Clause | 3 |
| scipy | 1.15.3 | Copyright (c) 2001-2002 Enthought, Inc. 2003-2024, SciPy Developers. | 5 |
| sentry-sdk | 2.71.0 | MIT | 1 |
| setuptools | 80.9.0 | MIT | 24 |
| shellingham | 1.5.4 | ISC License | 1 |
| six | 1.17.0 | MIT | 1 |
| smmap | 5.0.3 | BSD-3-Clause | 1 |
| sympy | 1.14.0 | BSD | 2 |
| tabulate | 0.10.0 | MIT | 1 |
| tensorboard | 2.20.0 | Apache 2.0 | 1 |
| tensorboard-data-server | 0.7.2 | Apache 2.0 | 0 |
| threadpoolctl | 3.7.0 | BSD-3-Clause | 1 |
| tifffile | 2026.3.3 | BSD-3-Clause | 1 |
| tokenizers | 0.22.2 | None | 0 |
| torch | 2.10.0+cu128 | BSD-3-Clause | 2 |
| torchvision | 0.25.0+cu128 | BSD | 1 |
| tqdm | 4.67.3 | MPL-2.0 AND MIT | 0 |
| transformers | 5.4.0 | Apache 2.0 License | 1 |
| triton | 3.6.0 | None | 1 |
| typer | 0.27.2 | MIT | 2 |
| typing-inspection | 0.4.4 | MIT | 1 |
| typing_extensions | 4.16.0 | PSF-2.0 | 1 |
| tzdata | 2026.5 | Apache-2.0 | 2 |
| urllib3 | 2.8.0 | MIT | 1 |
| wandb | 0.26.1 | MIT License | 1 |
| Werkzeug | 3.1.9 | BSD-3-Clause | 2 |
| wheel | 0.48.0 | MIT | 1 |
| zipp | 4.1.1 | MIT | 1 |

## Primary cross-checks

- [Pinned Marigold source](https://github.com/huawei-bayerlab/marigold-v2/blob/bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85/LICENSE)
- [Pinned Marigold weight card](https://huggingface.co/huawei-bayerlab/marigold-v2-0/blob/cdf9810fb690886391a63aec012b5f501064fb0d/README.md)
- [Pinned Qwen base card](https://huggingface.co/Qwen/Qwen-Image-Edit-2509/blob/d3968ef930e841f4c73640fb8afa3b306a78167e/README.md)
- [CUDA 12.8 EULA](https://docs.nvidia.com/cuda/archive/12.8.0/eula/index.html)
- [NVIDIA driver agreement](https://www.nvidia.com/en-us/drivers/nvidia-license/)
- [ANTLR 4.9.3](https://github.com/antlr/antlr4/blob/4.9.3/LICENSE.txt)
- [Tokenizers 0.22.2](https://github.com/huggingface/tokenizers/blob/v0.22.2/LICENSE)
- [tqdm 4.67.3](https://github.com/tqdm/tqdm/blob/v4.67.3/LICENCE)
- [TensorBoard 2.20.0 Apache text](https://github.com/tensorflow/tensorboard/blob/2.20.0/LICENSE)

Actual extracted source/assets, installed commercial permission and CPU metadata
readiness remain distinct from actual native loading or GPU qualification. No
GPU activity, setup attempt or live-ledger write was performed by this review.
