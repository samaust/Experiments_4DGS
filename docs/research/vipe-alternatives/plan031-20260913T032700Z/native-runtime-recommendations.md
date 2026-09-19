# Native runtime handoff — inspected recipes, not qualified environments

The seven targets and their one-attempt / 16-hour shared setup allocation remain
the protocol's limits. These recommendations are inputs to the controller's
single recorded resolution/build attempt. No commands below were executed.
The full resolved dependency/wheel/source lock must be saved before admission;
an open dependency below is not a claim that an arbitrary future version works.

Use a separate environment and source/build tree for each target. Install its
exact torch/torchvision wheel pair before evaluating native package build
metadata. For E1/E2/E5/E7 use the official `cu124` index, E4 `cu130`, E3 `cu128`, E6
`cu118`, retaining the protocol's exact versions. Constrain these packages
during every subsequent resolution/install. A complete lock should also pin
the build frontend, setuptools/wheel, native source revisions and source
archives, compiler/toolkit, build flags and produced extension hashes.

| Target | Required dependencies/build input in addition to fixed torch, torchvision and NumPy |
| --- | --- |
| E1: S1, Python 3.11 | Install pinned SAM source and native Grounding DINO source. Expose the exact AOT source as the SAM-Track `aot` subtree and on its native `configs`/`networks` import path. Starting dependency pins from SAM-Track's own script: `transformers==4.30.2`, `addict==2.4.0`, `yapf==0.40.2`, `timm==0.4.5`, `opencv-python==4.10.0.84`, `Pillow==10.4.0`, `scikit-image==0.24.0`, `matplotlib==3.9.2`, `supervision==0.22.0`, `pycocotools==2.0.8`. Resolve/pin the native correlation extension; `spatial-correlation-sampler==0.5.0` is an available concrete source-package candidate. Do not execute the upstream installer, which creates a different environment and clones unpinned dependencies. |
| E2: S2/S4, Python 3.11 | `transformers==4.51.3`; native Grounding DINO requirements (`addict`, `yapf`, `timm`, OpenCV, `supervision>=0.22.0`, `pycocotools`) plus SAM 2 requirements (`tqdm>=4.66.1`, `hydra-core>=1.3.2`, `iopath>=0.1.10`, `pillow>=9.4.0`). Resolve remaining versions once under the fixed NumPy 1.26.4/torch constraints. Build both native extensions. |
| E3: S3, Python 3.12 | Native SAM 3 defaults: `timm>=1.0.17`, `ftfy==6.1.1`, `regex`, `iopath>=0.1.10`, `typing_extensions`, `huggingface_hub`, `tqdm`. Core image/video imports additionally need `einops`, `scipy`, `pycocotools`, `psutil`, OpenCV/Pillow and the exact resolved transitives. Preserve the `pkg_resources` requirement in its builder (`setuptools==80.9.0` is the source install script's available compatibility candidate). No FA3, notebooks/train extras or multiplex checkpoint. Import qualification must cover both original builders, processor and video model. |
| E4: D1, Python 3.11 | Amended 2026-09-19: torch `2.13.0+cu130`, torchvision `0.28.0+cu130`, torchaudio `2.13.0+cu130`, NumPy `2.1.3`; resolve native `xformers>=0.0.26` once under those exact constraints and hash-lock the result. Python 3.11 wheel availability and xFormers/native compatibility remain unqualified. Its requirements also include `einops>=0.7.0`, `gradio`, `h5py>=3.10.0`, `huggingface-hub>=0.22.0`, `imageio`, `matplotlib`, OpenCV, `pandas`, `pillow>=10.2.0`, `protobuf>=4.25.3`, `scipy`, `tables`, `tabulate`, `termcolor`, `timm`, `tqdm`, `trimesh`, `triton>=2.4.0`, `wandb`. The training-only KNN extension is not required by this inference adapter. See Plan 031's explicit amendment; the frozen protocol and earlier failure evidence retain their original cu124 targets. |
| E5: D2, Python 3.11 | Install DA3 defaults, with `xformers==0.0.28.post3` and NumPy 1.26.4 constrained. Preserve all default dependencies, including `pre-commit`, `trimesh`, `einops`, HF Hub, `imageio`, OpenCV, `open3d`, `fastapi`, `uvicorn`, `requests`, `typer>=0.9.0`, Pillow, `omegaconf`, `evo`, `e3nn`, `moviepy==1.0.3`, `plyfile`, `pillow_heif`, `safetensors`, `pycolmap`. No `app`, `gs` or `all` extras. Build frontend requires `hatchling>=1.25`, `hatch-vcs>=0.4`. |
| E6: D3, Python 3.10 | Preserve `xformers==0.0.21` and NumPy 1.23.1. Native requirements include OpenCV, Pillow, `DateTime`, `matplotlib`, `plyfile`, `HTML4Vision`, `timm`, `tensorboardX`, `imgaug`, `iopath`, `imagecorruptions`, `mmcv`. `mmcv==1.7.2` is a concrete configuration-API candidate to resolve before the single build, because the hub first imports `mmcv.utils.Config`; its fallback requires a separately pinned `mmengine`. Do not silently upgrade the old torch/NumPy pair to satisfy a modern dependency. Shared benchmark hashing must support Python 3.10 (the original `hashlib.file_digest` call needs a chunked equivalent). |
| E7: D4, Python 3.11 | Native Depth Pro defaults: `timm`, `pillow_heif`, `matplotlib`, NumPy<2 (fixed to 1.26.4); native build metadata requires `setuptools` and `setuptools-scm`. Resolve these once with exact hashes and retain the official full checkpoint and transform. |

## Request lists for the controller

These are concrete initial requirement inputs, to be resolved once under
`TARGETS`, then retained as an exact inventory/lock. They are not already
qualified locks. Prepend `common_requirements` to each environment's
`requirements`; constraints alone do not cause installation. Native sources
come from the already pinned asset records, never a package-index replacement.
The source manifests linked below justify defaults; `addict` is also needed by
DA3's imported output processor even though absent from its declared defaults.

```json
{
  "common_requirements": [
    "torch", "torchvision", "numpy", "pip", "setuptools==80.9.0",
    "wheel", "ninja", "packaging", "Pillow", "opencv-python"
  ],
  "E1": {
    "requirements": [
      "transformers==4.30.2", "addict==2.4.0", "yapf==0.40.2",
      "timm==0.4.5", "opencv-python==4.10.0.84", "Pillow==10.4.0",
      "scikit-image==0.24.0", "matplotlib==3.9.2", "supervision==0.22.0",
      "pycocotools==2.0.8", "tqdm"
    ],
    "editable_sources": ["sam_source", "grounding_source"],
    "post_torch_native_build": "spatial-correlation-sampler==0.5.0"
  },
  "E2": {
    "requirements": [
      "transformers==4.51.3", "addict", "yapf", "timm",
      "supervision>=0.22.0", "pycocotools", "tqdm>=4.66.1",
      "hydra-core>=1.3.2", "iopath>=0.1.10", "pillow>=9.4.0"
    ],
    "editable_sources": ["grounding_source", "sam2_source"]
  },
  "E3": {
    "requirements": [
      "timm>=1.0.17", "ftfy==6.1.1", "regex", "iopath>=0.1.10",
      "typing_extensions", "huggingface_hub", "tqdm", "einops",
      "scipy", "pycocotools", "psutil"
    ],
    "editable_sources": ["sam3_source"]
  },
  "E4": {
    "requirements": [
      "xformers>=0.0.26", "torchaudio==2.13.0+cu130",
      "einops>=0.7.0", "gradio", "h5py>=3.10.0",
      "huggingface-hub>=0.22.0", "imageio", "matplotlib", "pandas",
      "pillow>=10.2.0", "protobuf>=4.25.3", "scipy", "tables",
      "tabulate", "termcolor", "timm", "tqdm", "trimesh",
      "triton>=2.4.0", "wandb"
    ],
    "editable_sources": ["unidepth_source"]
  },
  "E5": {
    "requirements": [
      "xformers==0.0.28.post3", "hatchling>=1.25", "hatch-vcs>=0.4",
      "pre-commit", "trimesh", "einops", "huggingface_hub", "imageio",
      "open3d", "fastapi", "uvicorn", "requests", "typer>=0.9.0",
      "omegaconf", "evo", "e3nn", "moviepy==1.0.3", "plyfile",
      "pillow_heif", "safetensors", "pycolmap", "addict"
    ],
    "editable_sources": ["da3_source"]
  },
  "E6": {
    "requirements": [
      "xformers==0.0.21", "DateTime", "matplotlib", "plyfile",
      "HTML4Vision", "timm", "tensorboardX", "imgaug", "iopath",
      "imagecorruptions", "mmcv==1.7.2", "yapf==0.40.1"
    ],
    "editable_sources": []
  },
  "E7": {
    "requirements": ["timm", "pillow_heif", "matplotlib", "setuptools-scm"],
    "editable_sources": ["depth_pro_source"]
  }
}
```

E1's correlation source build needs installed torch and the matching toolkit;
do not put its sdist in an initial isolated build that can fetch a different
torch. Resolve the exact sdist URL/hash before installing it with
`--no-deps --no-build-isolation`. SAM-Track and AOT are source trees, not editable
Python projects: create only the recorded `samtrack_source/aot` symlink to the
declared `aot_source`, and let the backend's explicit source paths handle their
imports. E6 uses the exact local Metric3D hub source and needs no editable
installation. Its `yapf` pin preserves the older `mmcv` formatter API.

For E3 the original builder imports `pkg_resources`; setuptools 81+ cannot be
assumed compatible. For E6 record `MMCV_WITH_OPS=0` for the configuration-only
`mmcv` package, which is what this native hub path uses. These flags do not
disable any requested model extension. After editable installation, preserve
the original source archive evidence and inventory generated/changed files
(Grounding DINO writes `groundingdino/version.py`, for example) before freezing
the adapter's source file hashes.

The E1 starting pins come from the exact
[SAM-Track install script](https://github.com/z-x-yang/Segment-and-Track-Anything/blob/99ca4bd5074a6ed62db4664285073ab669503926/script/install.sh).
The available correlation source package is recorded by
[PyPI](https://pypi.org/project/spatial-correlation-sampler/0.5.0/).
The remaining source manifests are
[Grounding DINO](https://github.com/IDEA-Research/GroundingDINO/blob/856dde20aee659246248e20734ef9ba5214f5e44/requirements.txt),
[SAM 2](https://github.com/facebookresearch/sam2/blob/2b90b9f5ceec907a1c18123530e92e794ad901a4/setup.py),
[SAM 3](https://github.com/facebookresearch/sam3/blob/660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7/pyproject.toml),
[UniDepth](https://github.com/lpiccinelli-eth/UniDepth/blob/8d8cfe4c7ee15297099983607febf0d4f32eb3d6/requirements.txt),
[DA3](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/pyproject.toml),
[Metric3D](https://github.com/YvanYin/Metric3D/blob/eb5b6fac0dc155e4e52f576e304fbf11655ff339/requirements_v2.txt), and
[Depth Pro](https://github.com/apple/ml-depth-pro/blob/9e65e4dbe9568d23c546fcec53302b10445e109e/pyproject.toml).

## Native extension commands and required gates

After resolving/installing the exact prerequisite lock in each new environment,
the source installations should use these command shapes, substituting only
explicit recorded absolute paths. `NATIVE_PYTHON`, `NATIVE_GROUNDING`,
`NATIVE_SAM`, `NATIVE_SAM2` and `NATIVE_CORRELATION` are task-specific variables.
Never let a model checkpoint or source revision float during this step.

```bash
"$NATIVE_PYTHON" -m pip install --no-deps --no-build-isolation -e "$NATIVE_SAM"
CUDA_HOME=/explicit/cuda-12.4 TORCH_CUDA_ARCH_LIST=8.9 MAX_JOBS=1 "$NATIVE_PYTHON" -m pip install --no-deps --no-build-isolation -e "$NATIVE_GROUNDING"
CUDA_HOME=/explicit/cuda-12.4 TORCH_CUDA_ARCH_LIST=8.9 MAX_JOBS=1 "$NATIVE_PYTHON" -m pip install --no-deps --no-build-isolation "$NATIVE_CORRELATION"
CUDA_HOME=/explicit/cuda-12.4 TORCH_CUDA_ARCH_LIST=8.9 MAX_JOBS=1 SAM2_BUILD_CUDA=1 SAM2_BUILD_ALLOW_ERRORS=0 "$NATIVE_PYTHON" -m pip install --no-deps --no-build-isolation -e "$NATIVE_SAM2"
```

SAM 2 normally suppresses extension build errors; the explicit environment flag
above and an import check of `sam2._C` prevent that incomplete installation from
qualifying. Grounding DINO's setup may install an unpinned torch if none is
present; preinstallation plus no build isolation avoids that path. AOT catches
failed correlation imports and chooses another implementation; require the
declared correlation module and `networks.layers.attention.enable_corr=True`.
The backend enforces the SAM 2/AOT import gates again before inference.

Host driver CUDA capability and the CUDA compiler toolkit are different inputs.
If the only available compiler is CUDA 13, it cannot be silently substituted for
the cu124 extension builds: PyTorch's
[extension version check](https://github.com/pytorch/pytorch/blob/v2.5.1/torch/utils/cpp_extension.py)
rejects a different CUDA major version. The controller must record the actual
toolkit, compiler and build outcome. An absent matching toolkit or a failed
allowed build is a recorded block under the existing limits, not permission to
change the wheel target, disable an extension or consume another attempt.

No strong skill-catalog match was found for this exact pinned multi-framework
build task after consulting the NVIDIA skill finder and its current catalog.
No skill installation or host modification was performed.

## Isolated CUDA 12.4 build dependency

The planned environment build can acquire its matching compiler within that
same E1/E2 setup allocation; this neither changes the torch target nor creates
another environment attempt. Count all received bytes, unpacked storage and
elapsed time against the existing 60 GiB / 150 GiB / 16-hour limits, and record
reuse when the second environment uses the same verified toolkit. This is an
interpretation of the existing setup scope, not an additional allocation.

The official [CUDA 12.4.1 redistributable manifest](https://developer.download.nvidia.com/compute/cuda/redist/redistrib_12.4.1.json)
pins these Linux x86-64 compiler/runtime building blocks. URLs have prefix
`https://developer.download.nvidia.com/compute/cuda/redist/` followed by the
relative path shown. No archive was downloaded during this inspection.

| Component | Relative path | SHA-256 | Compressed bytes |
| --- | --- | --- | ---: |
| nvcc | `cuda_nvcc/linux-x86_64/cuda_nvcc-linux-x86_64-12.4.131-archive.tar.xz` | `7ffba1ada0e4b8c17e451ac7a60d386aa2642ecd08d71202a0b100c98bd74681` | 51,184,484 |
| cudart | `cuda_cudart/linux-x86_64/cuda_cudart-linux-x86_64-12.4.127-archive.tar.xz` | `0483bff9a36e7a44465db3cd42874f6f70f019297dcf803fbefcbf58d7448c8f` | 1,099,680 |
| CCCL | `cuda_cccl/linux-x86_64/cuda_cccl-linux-x86_64-12.4.127-archive.tar.xz` | `e1636f27a142d24e73dfd831c54bbf5575b498fd5900648d7372fae46f824fdf` | 1,157,180 |

Together these are 53,441,344 bytes (50.97 MiB). Extract verified members into a
run-local toolkit tree, preserving relative `bin`, `include`, `nvvm` and library
layout and executable modes; create the toolkit-local `lib64` link if the
archive uses `lib`. Never point its CUDA include search at CUDA 13. The native
build environment then sets the explicit `CUDA_HOME`, prepends its `bin` to
`PATH`, and uses the flags above.

This reduced recipe relies on additional **matching cu124 wheel headers**:
[PyTorch 2.5.1's CUDA context](https://github.com/pytorch/pytorch/blob/v2.5.1/aten/src/ATen/cuda/CUDAContextLight.h)
includes `cusparse.h`, `cublas_v2.h`, `cublasLt.h` and `cusolverDn.h`. Include
their verified `nvidia/{cusparse,cublas,cusolver}/include` directories from the
installed exact torch dependency stack via explicit `CPATH` entries, retaining
those wheel hashes. Confirm this header closure before consuming the native
compile step; the three small archives alone are not a full CUDA toolkit.
Missing matching headers are a setup block, not permission to use CUDA 13
headers. All compiler and extension artifacts remain unqualified until the
single admitted environment build succeeds.

NVIDIA also documents [a reduced Conda toolkit installation](https://docs.nvidia.com/cuda/archive/12.4.1/cuda-installation-guide-linux/index.html#upgrading-from-cudatoolkit-package)
using compiler plus development-library packages. The explicit redist recipe
above avoids adding a second package manager. NVIDIA's Python CUDA packages
must not be assumed to contain a complete `nvcc` developer toolchain merely
because their names include `nvcc`.
