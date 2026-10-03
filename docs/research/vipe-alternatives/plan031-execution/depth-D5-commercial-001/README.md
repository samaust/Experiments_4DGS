# D5 commercial permission assessment

Status: actual CPU002 manifest bound; independent commercial permission review passed.

## Scope

This assessment covers MoGe-2 ViT-L D5 inference on the user's owned RTX 4090 workstation, using the exact completed setup `plan069-D5-setup-001`. It covers local commercial execution and use of resulting depth maps/images. It does not authorize redistribution of the installed environment, a public hosted service, SDK sublicensing, or unrelated input-media rights. No model import or GPU operation was performed for this assessment.

## Code and weights

The pinned [MoGe code LICENSE](https://raw.githubusercontent.com/microsoft/MoGe/74fbce054ebed49800de42d0ad0e83495065719a/LICENSE) contains MIT permission and Apache 2.0 terms for incorporated components. Both permit commercial execution. The setup source revision is `74fbce054ebed49800de42d0ad0e83495065719a`.

The pinned [model card](https://huggingface.co/Ruicheng/moge-2-vitl/raw/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/README.md) explicitly declares MIT. Its complete 24-byte content is retained in `primary/model-card.md`, together with response headers. This is the primary release declaration for checkpoint revision `39c4d5e957afe587e04eec59dc2bcc3be5ecd968`; it is assessed separately from the code license. MIT permits commercial inference and does not impose a model-output use restriction.

The exact installed utils3d_moge, pipeline and FlexGEMM source licenses are MIT. FlexGEMM's two administrative cache-path changes preserve its license; retain the setup derivation provenance and copyright notices if redistributed.

## Actual runtime closure

`installed-license-index.json` indexes all 90 installed distributions and retains available exact installed license/notice files, supplemented by pinned release texts for missing licenses, plus embedded Gradio/OpenCV notices and CPython terms. The successful CPU002 manifest binds these same 90 package versions and 104 installed notice records; its exact file record is retained in `manifest-binding.json`. Package metadata classifiers are not substituted for installed license text: groovy and safehttpx declare MIT classifiers but ship Apache 2.0 text, which this assessment uses.

PyTorch 2.6.0+cu124 and torchvision 0.21.0+cu124 provide BSD licenses and bundled notices. gradio_client 2.7.2 and tqdm 4.70.1 omit installed license texts; their version-bound upstream Apache 2.0 and MIT/MPL release texts are retained as explicit supplements. Triton 3.2.0 omits installed license text; its [exact release LICENSE](https://raw.githubusercontent.com/triton-lang/triton/v3.2.0/LICENSE) is retained and grants MIT use. LLVM/compiler components and CUDA toolchain binaries retain their upstream terms; no compiler or runtime redistribution is authorized here.

NVIDIA CUDA 12.4 libraries and cuDNN 9.1.0.70 ship SDK license texts granting installation/use under their conditions. NCCL 2.21.5 ships BSD terms. cuSPARSELt 0.6.2 omits the installed license file: NVIDIA's [official 0.6.2 manifest](https://developer.download.nvidia.com/compute/cusparselt/redist/redistrib_0.6.2.json) explicitly identifies the [SDK license](https://developer.download.nvidia.com/compute/cusparselt/redist/libcusparse_lt/LICENSE.txt), both retained. That license grants SDK installation/use. The attempted versioned documentation URL returned 404 and is not evidence. This verdict applies to the owned workstation, with NVIDIA's authorized-use, export, safety and distribution conditions; it is not a claim that the closure is entirely MIT/Apache.

NumPy/SciPy carry BSD/OpenBLAS notices and GCC runtime exceptions for libgfortran/libquadmath. OpenCV ships Apache/MIT and bundled FFmpeg LGPL notices. PyTorch includes additional LGPL terms. These permit local commercial execution; distribution may require notices, source/relinking arrangements and the applicable exceptions. MPL 2.0 components certifi/orjson/tqdm permit commercial execution and require appropriate source obligations on redistribution of covered changes. CPython carries PSF and incorporated third-party terms. The remaining packages and bundled notices permit the scoped local commercial execution. Pillow and CUDA notices also include copyleft/toolchain components; redistribution must honor their specific license and source obligations. Gradio's shipped vendor notices are retained. Its browser assets and Node server are outside the execution scope: the worker does not start a web UI. This assessment does not establish a separate commercial deployment license closure for that unused UI.

## Outputs and obligations

The assessed licenses do not claim generated depth maps, point maps or image pixels as licensed copies of the runtime merely because it produced them. Commercial use of these outputs is permitted by the assessed code/weight/runtime terms. This is an inference from the retained license grants and scopes, not an express guarantee that every output is copyrightable or that source media is cleared. Keep this report and original license notices with the evidence. Reassess distribution, hosting, runtime changes or newly introduced external tools; host FFmpeg publication is a separate executable closure if used, and has not been silently included in the inference environment verdict.

## Installed packages

| Package | Version | Primary declared terms |
|---|---|---|
| annotated-doc | 0.0.5 | MIT |
| annotated-types | 0.8.0 | MIT |
| anyio | 4.15.1 | MIT |
| brotli | 1.2.0 | MIT |
| certifi | 2026.7.22 | MPL-2.0 |
| charset-normalizer | 3.5.2 | MIT |
| click | 8.5.0 | BSD-3-Clause |
| contourpy | 1.3.3 | BSD 3-Clause License |
| cycler | 0.12.1 | Copyright (c) 2015, matplotlib project |
| fastapi | 0.142.2 | MIT |
| filelock | 4.0.9 | MIT |
| flex_gemm | 1.0.0 | MIT License |
| fonttools | 4.66.1 | MIT |
| fsspec | 2026.9.0 | BSD-3-Clause |
| glcontext | 3.0.0 | MIT |
| gradio | 6.29.1 | Apache-2.0 |
| gradio_client | 2.7.2 | Apache-2.0 |
| groovy | 0.1.2 | Apache-2.0 (installed text) |
| h11 | 0.16.0 | MIT |
| hf-gradio | 0.4.1 | MIT |
| hf-xet | 1.6.0 | Apache-2.0 |
| httpcore | 1.0.9 | BSD-3-Clause |
| httpcore2 | 2.13.1 | BSD-3-Clause |
| httpx | 0.28.1 | BSD-3-Clause |
| httpx2 | 2.13.1 | BSD-3-Clause |
| huggingface_hub | 2.1.1 | Apache-2.0 |
| idna | 3.20 | BSD-3-Clause |
| Jinja2 | 3.1.6 | BSD (installed text) |
| kiwisolver | 1.5.1 | ========================= |
| markdown-it-py | 4.2.0 | MIT (installed text) |
| MarkupSafe | 3.0.4 | BSD-3-Clause |
| matplotlib | 3.11.2 | License agreement for matplotlib versions 1.3.0 and later |
| mdurl | 0.1.2 | MIT (installed text) |
| moderngl | 5.12.0 | MIT |
| mpmath | 1.3.0 | BSD |
| networkx | 3.6.1 | BSD-3-Clause |
| numpy | 2.1.3 | Copyright (c) 2005-2024, NumPy Developers. |
| nvidia-cublas-cu12 | 12.4.5.8 | NVIDIA Proprietary Software |
| nvidia-cuda-cupti-cu12 | 12.4.127 | NVIDIA Proprietary Software |
| nvidia-cuda-nvrtc-cu12 | 12.4.127 | NVIDIA Proprietary Software |
| nvidia-cuda-runtime-cu12 | 12.4.127 | NVIDIA Proprietary Software |
| nvidia-cudnn-cu12 | 9.1.0.70 | NVIDIA Proprietary Software |
| nvidia-cufft-cu12 | 11.2.1.3 | NVIDIA Proprietary Software |
| nvidia-curand-cu12 | 10.3.5.147 | NVIDIA Proprietary Software |
| nvidia-cusolver-cu12 | 11.6.1.9 | NVIDIA Proprietary Software |
| nvidia-cusparse-cu12 | 12.3.1.170 | NVIDIA Proprietary Software |
| nvidia-cusparselt-cu12 | 0.6.2 | NVIDIA Proprietary Software |
| nvidia-nccl-cu12 | 2.21.5 | NVIDIA Proprietary Software |
| nvidia-nvjitlink-cu12 | 12.4.127 | NVIDIA Proprietary Software |
| nvidia-nvtx-cu12 | 12.4.127 | NVIDIA Proprietary Software |
| opencv-python-headless | 5.0.0.93 | Apache 2.0 |
| opentelemetry-api | 1.45.0 | Apache-2.0 |
| orjson | 3.12.0 | MPL-2.0 AND (Apache-2.0 OR MIT) |
| packaging | 26.3 | Apache-2.0 OR BSD-2-Clause |
| pandas | 3.0.6 | BSD 3-Clause License |
| pillow | 12.3.0 | MIT-CMU |
| pipeline | 1.0.0 | MIT |
| pydantic | 2.13.5 | MIT |
| pydantic_core | 2.46.5 | MIT |
| pydub | 0.25.1 | MIT |
| Pygments | 2.21.0 | BSD-2-Clause |
| pyparsing | 3.3.3 | MIT |
| python-dateutil | 2.9.0.post0 | Dual License |
| python-multipart | 0.0.32 | Apache-2.0 |
| pytz | 2026.4 | MIT |
| PyYAML | 6.0.3 | MIT |
| requests | 2.34.2 | Apache-2.0 |
| rich | 15.0.0 | MIT |
| safehttpx | 0.1.7 | Apache-2.0 (installed text) |
| scipy | 1.17.1 | Copyright (c) 2001-2002 Enthought, Inc. 2003, SciPy Developers. |
| semantic-version | 2.10.0 | BSD |
| setuptools | 84.0.0 | MIT |
| shellingham | 1.5.4 | ISC License |
| six | 1.17.0 | MIT |
| starlette | 1.7.0 | BSD-3-Clause |
| sympy | 1.13.1 | BSD |
| tomlkit | 0.14.0 | MIT |
| torch | 2.6.0+cu124 | BSD-3-Clause |
| torchvision | 0.21.0+cu124 | BSD |
| tqdm | 4.70.1 | MPL-2.0 AND MIT |
| trimesh | 5.1.1 | The MIT License (MIT) |
| triton | 3.2.0 | MIT (installed text) |
| truststore | 0.10.4 | MIT |
| typer | 0.27.2 | MIT |
| typing_extensions | 4.16.0 | PSF-2.0 |
| typing-inspection | 0.4.4 | MIT |
| urllib3 | 2.8.0 | MIT |
| utils3d_moge | 1.7 | MIT |
| uvicorn | 0.54.0 | BSD-3-Clause |
| wheel | 0.48.0 | MIT |
