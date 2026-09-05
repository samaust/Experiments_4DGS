# Local Python and CUDA environments

[Overview](../README.md) · [Pretrained experiments](pretrained-experiments.md) · [Specifications](../environments/README.md)

## Policy and current status

Use standard GIL CPython 3.14, uv, **PyTorch 2.13.0+cu130 and torchvision 0.28.0+cu130**, and `/usr/local/cuda-13.0`. These are prebuilt Torch wheels, not instructions to compile Torch. The official index supplies CPython 3.14 Linux wheels. This is a selected recent pair, not a claim about the latest release. Sources: [PyTorch version pairs](https://pytorch.org/get-started/previous-versions/), [cu130 Torch wheels](https://download.pytorch.org/whl/cu130/torch/), [torchvision wheels](https://download.pytorch.org/whl/cu130/torchvision/), [uv PyTorch integration](https://docs.astral.sh/uv/guides/integration/pytorch/).

No Conda, automatic interpreter downgrade, older CUDA toolkit, or CPU-wheel fallback is part of this workflow. An incompatible method remains **adaptation pending**. Upstream historical stacks in the research notes are provenance, not installation choices. Do not run upstream environment/setup scripts wholesale.

The STG candidate dependencies have been resolved, installed and checked locally. The requested base versions import in the research environments; full method dependencies and GPU checks have separate statuses in the [execution record](experiments/environment-validation.md). Browser experiments remain independent of these ports.

## 1. Select the existing tools and workspace

Run from the repository root in every new Bash terminal. Do not modify system Python or shell startup files. Stop on any failed command; do not paste later stages after a failure.

```bash
GS_ROOT="$(git rev-parse --show-toplevel)"
export GS_ROOT
export GS_WORK="$GS_ROOT/.local"
export UV_CACHE_DIR="$GS_WORK/cache/uv"
export UV_PYTHON_INSTALL_DIR="$GS_WORK/tools/python"
export UV_PYTHON_DOWNLOADS=never
export HF_HOME="$GS_WORK/cache/huggingface"
export TORCH_HOME="$GS_WORK/cache/torch"
export XDG_CACHE_HOME="$GS_WORK/cache/xdg"
mkdir -p "$GS_WORK"/{envs,tools,cache,downloads,data,weights,runs}
mkdir -p "$UV_CACHE_DIR" "$HF_HOME" "$TORCH_HOME" "$XDG_CACHE_HOME"
uv --version
/usr/bin/python3.14 -c 'import sys, sysconfig; print(sys.executable, sys.version); assert sys.version_info[:2] == (3, 14); assert not sysconfig.get_config_var("Py_GIL_DISABLED")'
export CUDA_HOME=/usr/local/cuda-13.0
export PATH="$CUDA_HOME/bin:$PATH"
export CC=/usr/bin/gcc
export CXX=/usr/bin/g++
export CUDAHOSTCXX="$CXX"
export TORCH_CUDA_ARCH_LIST=8.9
command -v nvcc
nvcc --version
"$CXX" --version
nvidia-smi --query-gpu=name,memory.total,driver_version --format=csv
git check-ignore .local/envs/example .local/weights/example.ply
```

The explicit CUDA path avoids reliance on `.bashrc`. Native 8.9 targets the RTX 4090. Check host compiler support before building; Torch's CUDA runtime does not supply the development toolkit. Driver capability displayed by `nvidia-smi` is not the installed compiler version. A sandbox device failure must be distinguished from host failure in an authorized terminal. [NVIDIA CUDA installation](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/), [Ada compatibility](https://docs.nvidia.com/cuda/ada-compatibility-guide/).

## 2. Create and resolve one environment

Choose one name: `stg-render`, `stg-colmap`, `hust`, `mango-render`, or `nopo4d`. STG training and rendering share `stg-render`; preprocessing is separate. Run the tracked setup script from the repository root; it derives paths independently of stale shell variables, reuses an existing prefix after checking its Python version, and stops on errors. Each attempt creates a separate log directory beneath `.local/runs/`.

```bash
bash scripts/setup-environment.sh stg-render
```

Repeat with `stg-colmap`, `hust`, `mango-render`, and `nopo4d` as needed. The script installs the fixed Torch base, resolves the method candidate and build tools together, installs that resolution, runs `uv pip check`, saves the package inventory and verifies base imports. It does not clear existing packages. A failed resolution can leave an environment containing only the base; rerun the same command after resolving the cause. Successful setup does not include deferred upstream source packages.

The script normally uses the network. For a cached replay, `UV_OFFLINE=1 bash scripts/setup-environment.sh stg-render` has been executed successfully. An offline "not found in the cache" error requires a network-enabled retry; it is not evidence that the package is incompatible with Python 3.14. Preserve the failure log and the successful retry separately.

To use the selected environment in later manual commands, set these variables explicitly in that terminal (change the method name deliberately):

```bash
GS_ROOT="$(git rev-parse --show-toplevel)"
export GS_ROOT GS_WORK="$GS_ROOT/.local"
export GS_ENV=stg-render
export GS_PY="$GS_WORK/envs/$GS_ENV/bin/python"
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions/$GS_ENV-py314-torch213-cu130"
mkdir -p "$TORCH_EXTENSIONS_DIR" "$GS_WORK/runs/environment-$GS_ENV"
```

uv's explicit Torch backend routes Torch packages to the cu130 index while ordinary dependencies use PyPI. Exact local-version constraints reject CPU/other CUDA builds and incompatible Torch requirements. Keep that constraint and backend on **every subsequent research package installation**, including editable installs. Resolution failure is evidence to record, not permission to relax the base. Candidate resolution excludes the deferred sources listed below; it is not a full method lock. Record build-tool versions too.

For the independent download CLI, run `bash scripts/setup-environment.sh downloads`. The script checks `hf --help` after installation. No Torch or compiler is needed. Browser serving and the checkpoint resolver can use `/usr/bin/python3.14` directly.

## 3. Port and build the selected method

| Method | Required compatibility work before a native experiment |
| --- | --- |
| STG | Apply the tracked Python 3.14/CUDA 13 patch in the pretrained guide: CUDA headers, NumPy/SSIM APIs, and lazy training-only `mmcv.ops.knn` import. Native checkpoint rendering does not require MMCV; training interpolation still does. Build all five extensions against the fixed ABI. |
| HUST | Audit legacy MMCV configuration APIs; deliberately port callers or select a compatible implementation. Modern MMCV is not a drop-in replacement. HUST is separate from STG's training-only KNN dependency. |
| STG preprocessing | Install/check the native COLMAP executable independently. Compare every CLI flag used by the pinned preprocessing source with the installed release; adapt and record differences before touching a working data copy. |
| Mango-GS | Select and record a full PyTorch3D revision compatible with Python 3.14/Torch 2.13, then build it and both local CUDA extensions. Do not install the unpinned Git dependency from upstream requirements unchanged. |
| NoPo4D / backbone | Run `bash scripts/setup-nopo4d.sh` to apply the Python 3.14/NumPy 2 metadata patches and install both sources with full dependency resolution. Installation, CPU smoke checks and full bundled GPU reconstruction pass, including an exact offline rerun; see [experiment 005](experiments/005-nopo4d.md). Open3D remains an optional benchmark dependency. |
| splaTV / stdlib helpers | No Torch dependency; browser WebGL2 and Python 3.14 serving/tests are separate checks. |

Inspect upstream requirements and imports against the candidate specification, adding missing dependencies before calling it complete. Keep failures, selected source revisions, and reusable patches. Do not change checkpoint loading globally to unrestricted pickle: only explicitly trusted legacy checkpoints may need a narrowly scoped compatibility change. See [Torch load semantics](https://docs.pytorch.org/docs/stable/generated/torch.load.html).

For Mango's PyTorch3D build, use the concrete revision below. It built as PyTorch3D 0.7.9 with CUDA enabled in `mango-render`, using Python 3.14.6, Torch 2.13.0+cu130 and CUDA 13.0. Imports, CPU checks, GPU KNN forward/backward and GPU point rasterization pass; see the [execution record](experiments/environment-validation.md). Complete section 2 for `mango-render` before running this block.

Paste the entire parenthesized block. It runs in a subshell with error handling, so a failed check stops subsequent commands without closing your terminal. A standalone `${variable:?message}` in an interactive shell does not prevent later pasted commands from running.

```bash
(
set -euo pipefail
GS_ROOT="$(git rev-parse --show-toplevel)"
GS_WORK="$GS_ROOT/.local"
GS_PY="$GS_WORK/envs/mango-render/bin/python"
GS_PYTORCH3D_REV=0a7d4c1a171e8b768c63f15b17564f9ad495f49b
if [ ! -x "$GS_PY" ]; then
  printf '%s\n' 'Create mango-render using section 2 before building PyTorch3D.' >&2
  exit 1
fi
export CUDA_HOME=/usr/local/cuda-13.0
export PATH="$CUDA_HOME/bin:$PATH"
export CC=/usr/bin/gcc CXX=/usr/bin/g++ CUDAHOSTCXX=/usr/bin/g++
export TORCH_CUDA_ARCH_LIST=8.9
export FORCE_CUDA=1
export MAX_JOBS="${MAX_JOBS:-2}"
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions/mango-render-py314-torch213-cu130"
export UV_CACHE_DIR="$GS_WORK/cache/uv"
"$GS_PY" -c 'import sys, torch; assert sys.version_info[:2] == (3, 14); assert torch.__version__ == "2.13.0+cu130"; print(sys.executable, torch.__version__)'
if [ ! -e "$GS_WORK/pytorch3d" ]; then
  git clone https://github.com/facebookresearch/pytorch3d.git "$GS_WORK/pytorch3d"
fi
if [ -n "$(git -C "$GS_WORK/pytorch3d" status --porcelain)" ]; then
  printf '%s\n' 'PyTorch3D has local changes; preserve and review them before switching revisions.' >&2
  exit 1
fi
git -C "$GS_WORK/pytorch3d" checkout --detach "$GS_PYTORCH3D_REV"
git -C "$GS_WORK/pytorch3d" rev-parse HEAD
uv pip install --python "$GS_PY" --torch-backend cu130 \
  --constraint "$GS_ROOT/environments/constraints-cu130.txt" \
  --no-build-isolation "$GS_WORK/pytorch3d"
"$GS_PY" -c 'import torch; import pytorch3d; from pytorch3d import _C; print(pytorch3d.__version__, _C.__file__)'
"$GS_PY" "$GS_ROOT/scripts/verify-environment.py" --gpu --pytorch3d
)
```

`FORCE_CUDA=1` requests CUDA compilation even when the build process cannot see a GPU; it still requires the toolkit and does not grant GPU access. The default `MAX_JOBS=2` limits parallel compilation memory; this workstation's build used eight jobs after checking available RAM. Set `MAX_JOBS` before the block to override the default. The final check requires device access and executes KNN forward/backward and point rasterization, beyond an extension import. If reusing an older CPU-only build, rebuild in a fresh source/build directory with these settings rather than treating its successful import as CUDA validation. The pinned source exposes `knn_check_version` only when compiled with CUDA; the verifier checks that marker too.

Import `torch` before directly importing `pytorch3d._C`: Torch loads the shared libraries needed by the extension, including `libc10.so`. If the earlier block installed into `stg-render`, check that existing installation with the command below. A successful check does not require reinstalling it; Mango still uses its own environment.

```bash
"$GS_WORK/envs/stg-render/bin/python" -c 'import torch; import pytorch3d; from pytorch3d import _C; print(torch.__version__, pytorch3d.__version__, _C.__file__)'
```

The method guides show source-build commands **conditional on completing this audit/port**. `--no-build-isolation` is appropriate for these Torch extensions when their build scripts import the already installed Torch to obtain ABI/header settings; the preceding `build.in` installation provides initial build tools. Inspect each backend for additional requirements and install/record them first. Do not use this flag as a blanket fix for unrelated packages.

For preprocessing, obtain COLMAP through the host's native package/build workflow; installing `pycolmap` does not supply the required CLI. Record the installed version and compare help to the script before running it:

```bash
command -v colmap
colmap -h
colmap feature_extractor -h
colmap exhaustive_matcher -h
colmap point_triangulator -h
```

If absent, the Ubuntu package is an initial option (`sudo apt install colmap`); its CLI still needs verification. No particular system COLMAP version is certified here. [COLMAP installation](https://colmap.github.io/install.html), [CLI documentation](https://colmap.github.io/cli.html).

## 4. Validate in stages and retain evidence

First validate the base in each research environment. The tracked verifier performs the exact Python/Torch/torchvision/runtime assertions, then a synchronized CUDA tensor operation. Add `--pytorch3d` for Mango's extension/kernel checks. Omitting `--gpu` checks versions and imports only.

```bash
(
set -euo pipefail
"${GS_PY:?Select an environment first}" "$GS_ROOT/scripts/verify-environment.py" --gpu
uv pip check --python "$GS_PY"
mkdir -p "$GS_WORK/runs/environment-$GS_ENV"
uv pip freeze --python "$GS_PY" > "$GS_WORK/runs/environment-$GS_ENV/installed.txt"
uv --version
git rev-parse HEAD
git submodule status --recursive
)
```

Run the Git inventory commands in the selected upstream checkout, and record independent dependency revisions as well. Repeat the base assertions after all source/editable installations. Then check imports and CLI help, compile/load extensions, execute a real rasterization, and finally reload a complete trusted checkpoint in a fresh process and render multiple timestamps. A tensor check does not test a rasterizer; an extension import does not prove its kernels work. Record each stage separately in the [experiment template](experiments/template.md), with exact commands and logs.

Only after successful full resolution should a lock be promoted into tracked specifications. Only after checkpoint rendering should a method be marked render-validated. Training and quality/VRAM measurements remain later stages.

Repository-only checks, requiring no research installation:

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3.14 -m unittest discover -s tests -p 'test_*.py' -v
node tests/splatv-time-controls.test.cjs
git diff --check
```
