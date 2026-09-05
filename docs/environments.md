# Local Python and CUDA environments

[Overview](../README.md) · [Pretrained experiments](pretrained-experiments.md) · [Specifications](../environments/README.md)

## Policy and current status

Use standard GIL CPython 3.14, uv, **PyTorch 2.13.0+cu130 and torchvision 0.28.0+cu130**, and `/usr/local/cuda-13.0`. These are prebuilt Torch wheels, not instructions to compile Torch. The official index supplies CPython 3.14 Linux wheels. This is a selected recent pair, not a claim about the latest release. Sources: [PyTorch version pairs](https://pytorch.org/get-started/previous-versions/), [cu130 Torch wheels](https://download.pytorch.org/whl/cu130/torch/), [torchvision wheels](https://download.pytorch.org/whl/cu130/torchvision/), [uv PyTorch integration](https://docs.astral.sh/uv/guides/integration/pytorch/).

No Conda, automatic interpreter downgrade, older CUDA toolkit, or CPU-wheel fallback is part of this workflow. An incompatible method remains **adaptation pending**. Upstream historical stacks in the research notes are provenance, not installation choices. Do not run upstream environment/setup scripts wholesale.

The tracked specifications are unresolved candidates. No complete research environment, extension build, checkpoint render, or GPU benchmark has been validated by this documentation update. Browser experiments remain independent of these ports.

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

Choose one name: `stg-render`, `stg-colmap`, `hust`, `mango-render`, or `nopo4d`. STG training and rendering share `stg-render`; preprocessing is separate. Repeat this section for each method, without activation. Do not recreate an existing prefix: inspect its interpreter and inventory first, or choose a new prefix for a changed stack.

```bash
GS_ENV=stg-render
export GS_ENV
export GS_PY="$GS_WORK/envs/$GS_ENV/bin/python"
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions/$GS_ENV-py314-torch213-cu130"
mkdir -p "$TORCH_EXTENSIONS_DIR" "$GS_WORK/runs/environment-$GS_ENV"
uv venv --python /usr/bin/python3.14 "$GS_WORK/envs/$GS_ENV"
uv pip install --python "$GS_PY" --torch-backend cu130 \
  -r "$GS_ROOT/environments/base-cu130.in"
uv pip compile --python "$GS_PY" --torch-backend cu130 \
  --constraint "$GS_ROOT/environments/constraints-cu130.txt" \
  "$GS_ROOT/environments/$GS_ENV.in" \
  --output-file "$GS_WORK/runs/environment-$GS_ENV/candidate.txt"
uv pip install --python "$GS_PY" --torch-backend cu130 \
  --constraint "$GS_ROOT/environments/constraints-cu130.txt" \
  -r "$GS_WORK/runs/environment-$GS_ENV/candidate.txt" \
  -r "$GS_ROOT/environments/build.in"
uv pip check --python "$GS_PY"
```

uv's explicit Torch backend routes Torch packages to the cu130 index while ordinary dependencies use PyPI. Exact local-version constraints reject CPU/other CUDA builds and incompatible Torch requirements. Keep that constraint and backend on **every subsequent research package installation**, including editable installs. Resolution failure is evidence to record, not permission to relax the base. Candidate resolution excludes the deferred sources listed below; it is not a full method lock. Record build-tool versions too.

For the independent download CLI, use `uv venv --python /usr/bin/python3.14 "$GS_WORK/envs/downloads"`, then `uv pip install --python "$GS_WORK/envs/downloads/bin/python" -r "$GS_ROOT/environments/downloads.in"`. No Torch or compiler is needed. Browser serving and the checkpoint resolver can use `/usr/bin/python3.14` directly.

## 3. Port and build the selected method

| Method | Required compatibility work before a native experiment |
| --- | --- |
| STG / HUST | Audit legacy MMCV configuration APIs; port the bundled implementation or deliberately adapt callers to a maintained config library. Modern MMCV is not a drop-in replacement. Audit NumPy/science APIs, SSIM `multichannel` versus `channel_axis` and explicit `data_range`, and Torch checkpoint-loading behavior. Build every imported CUDA extension against the fixed ABI. |
| STG preprocessing | Install/check the native COLMAP executable independently. Compare every CLI flag used by the pinned preprocessing source with the installed release; adapt and record differences before touching a working data copy. |
| Mango-GS | Select and record a full PyTorch3D revision compatible with Python 3.14/Torch 2.13, then build it and both local CUDA extensions. Do not install the unpinned Git dependency from upstream requirements unchanged. |
| NoPo4D / backbone | Resolve complete model and backbone metadata under the base constraint, including xFormers and gsplat. Old exact Torch/xFormers and NumPy restrictions may block Python 3.14. Audit/patch metadata only after checking source compatibility; do not bypass dependencies. Record compatible wheels or pinned source builds. |
| splaTV / stdlib helpers | No Torch dependency; browser WebGL2 and Python 3.14 serving/tests are separate checks. |

Inspect upstream requirements and imports against the candidate specification, adding missing dependencies before calling it complete. Keep failures, selected source revisions, and reusable patches. Do not change checkpoint loading globally to unrestricted pickle: only explicitly trusted legacy checkpoints may need a narrowly scoped compatibility change. See [Torch load semantics](https://docs.pytorch.org/docs/stable/generated/torch.load.html).

For Mango's deferred PyTorch3D build, select a full compatible revision during the audit and set `GS_PYTORCH3D_REV` to it. The following deliberately stops if no revision has been chosen; it does not invent a known-good pin. Run with `GS_ENV=mango-render` and its `GS_PY`/extension cache selected:

```bash
: "${GS_PYTORCH3D_REV:?Set the audited full PyTorch3D Git revision first}"
git clone https://github.com/facebookresearch/pytorch3d.git "$GS_WORK/pytorch3d"
git -C "$GS_WORK/pytorch3d" checkout --detach "$GS_PYTORCH3D_REV"
git -C "$GS_WORK/pytorch3d" rev-parse HEAD
uv pip install --python "$GS_PY" --torch-backend cu130 \
  --constraint "$GS_ROOT/environments/constraints-cu130.txt" \
  --no-build-isolation "$GS_WORK/pytorch3d"
"$GS_PY" -c 'import pytorch3d; from pytorch3d import _C; print(pytorch3d.__version__)'
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

First validate the base in each research environment:

```bash
"$GS_PY" - <<'PY'
import sys, sysconfig, torch, torchvision
print(sys.executable, sys.version)
print(torch.__version__, torchvision.__version__, torch.version.cuda)
assert sys.version_info[:2] == (3, 14)
assert not sysconfig.get_config_var("Py_GIL_DISABLED")
assert torch.__version__ == "2.13.0+cu130"
assert torchvision.__version__ == "0.28.0+cu130"
assert torch.version.cuda == "13.0"
assert torch.cuda.is_available()
print(torch.cuda.get_device_name(0), torch.cuda.get_device_capability(0))
x = torch.ones((32, 32), device="cuda")
y = x @ x
torch.cuda.synchronize()
assert y[0, 0].item() == 32
PY
uv pip check --python "$GS_PY"
uv pip freeze --python "$GS_PY" > "$GS_WORK/runs/environment-$GS_ENV/installed.txt"
uv --version
git rev-parse HEAD
git submodule status --recursive
```

Run the Git inventory commands in the selected upstream checkout, and record independent dependency revisions as well. Repeat the base assertions after all source/editable installations. Then check imports and CLI help, compile/load extensions, execute a real rasterization, and finally reload a complete trusted checkpoint in a fresh process and render multiple timestamps. A tensor check does not test a rasterizer; an extension import does not prove its kernels work. Record each stage separately in the [experiment template](experiments/template.md), with exact commands and logs.

Only after successful full resolution should a lock be promoted into tracked specifications. Only after checkpoint rendering should a method be marked render-validated. Training and quality/VRAM measurements remain later stages.

Repository-only checks, requiring no research installation:

```bash
PYTHONDONTWRITEBYTECODE=1 /usr/bin/python3.14 -m unittest discover -s tests -p 'test_*.py' -v
node tests/splatv-time-controls.test.cjs
git diff --check
```
