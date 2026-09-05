# Environment guide execution

Status: partially validated, with successful host GPU checks. Date: 2026-09-05. Target: Ubuntu 24.04 / RTX 4090.

## Follow-up after download and GPU authorization

The earlier sandbox/cache failures recorded below are historical, not current
host failures. STG, STG preprocessing, Mango, NoPo4D candidate dependencies and
the download CLI have since installed; `hf --help` passes. STG's five native
extensions and Mango's two native extensions built with tracked source patches.
The Mango environment passes the verifier's synchronized CUDA tensor operation,
PyTorch3D CUDA KNN forward/backward and CUDA point rasterization on the RTX 4090.
The STG native renderer also produced a three-frame checkpoint preview.
See the [pretrained execution record](pretrained-validation.md) for artifacts,
source revisions and remaining gates. Native COLMAP is absent; complete NoPo4D
installation has Python/NumPy/Open3D conflicts despite candidate installation.

## Earlier environment-only attempts

This record distinguishes executed checks from method compatibility still to establish.
The initial attempts below did not perform training, downloaded scene rendering,
or measured GPU throughput; the follow-up above supersedes their GPU status.

## Verified tools and dependencies

Observed tools: uv 0.11.32, standard GIL Python 3.14.6 at
`/usr/bin/python3.14`, CUDA toolkit 13.0 V13.0.88 at
`/usr/local/cuda-13.0`, and GCC/G++ 13.3.0.

| Environment | Executed result | Remaining work |
| --- | --- | --- |
| stg-render | Candidate plus build tools resolve from cache; installation, package consistency, base versions and all candidate imports pass | STG source/MMCV/rasterizer ports and GPU execution |
| stg-colmap | Python 3.14 and Torch 2.13.0+cu130 / torchvision 0.28.0+cu130 installed; base imports pass | Candidate resolution needs uncached opencv-python-headless; native COLMAP absent |
| hust | Same fixed base installed; base imports pass | Candidate resolution needs uncached imageio-ffmpeg and other dependencies; source ports |
| mango-render | Fixed base and build tools installed; PyTorch3D CUDA build, imports, CPU KNN forward/backward and CPU point rasterization pass; package consistency passes | Full candidate resolution needs downloads; GPU kernels and Mango source integration remain pending |
| nopo4d | Same fixed base installed; base imports pass | Candidate resolution needs uncached einops and other dependencies; full backbone/model metadata and sources |
| downloads | Standard Python 3.14 environment created | huggingface-hub is uncached; CLI not installed or validated |

The missing-cache examples are first resolver failures, not exhaustive missing-package
lists or proven incompatibilities. An online Mango resolution attempt failed with
`Temporary failure in name resolution` while accessing PyPI from the sandbox.
Host/network execution requires the execution tool's permission path.

## Reproduction and logs

The tracked [setup script](../../scripts/setup-environment.sh) creates a unique run
directory, preserving failed attempts and inventories. The following completed:

```bash
UV_OFFLINE=1 bash scripts/setup-environment.sh stg-render
```

Successful STG logs and resolved candidate specification:
`.local/runs/environment-stg-render-AAfJtavJ/` (`setup.log`, `candidate.txt`,
`installed.txt`). The resolution includes 49 packages; the existing environment
has 52 because the user's earlier PyTorch3D installation and its extra dependencies
remain installed. The candidate specification is not a complete STG source lock.

Other setup attempts, preserving their errors:

- `.local/runs/environment-stg-colmap-Yw5EGJky/`
- `.local/runs/environment-hust-BwH5ZQRo/`
- `.local/runs/environment-mango-render-4NB54Dg5/`
- `.local/runs/environment-nopo4d-3rLXa6NS/`
- `.local/runs/environment-downloads-1KyJZN6U/`

Retry the same setup script without `UV_OFFLINE=1` once network execution is
available. It checks and reuses the existing interpreter rather than recreating it.

## PyTorch3D and GPU checks

Source revision: `0a7d4c1a171e8b768c63f15b17564f9ad495f49b`, package 0.7.9.
The existing STG installation loads when Torch is imported first, exposes the
CUDA-only `knn_check_version` binding, and passes CPU KNN and CPU point rasterization.
These observations do not establish GPU execution.

The Mango rebuild completed successfully with `FORCE_CUDA=1`,
`TORCH_CUDA_ARCH_LIST=8.9`, CUDA 13.0, GCC/G++ 13.3.0 and the same source revision.
The completed invocation used eight build jobs after checking that the host had
111 GiB available RAM. uv reported 7m 13s preparation for the final invocation;
this is not a clean-build benchmark because earlier interrupted invocations
left reusable object files.

The newly installed Mango extension imports successfully and exposes its CUDA
binding. CPU KNN returns the expected squared distances and nonzero gradients;
CPU point rasterization produces occupied pixels. `uv pip check` passes with
40 installed packages. These checks use the newly built Mango installation,
not just the earlier STG package. Its inventory is saved at
`.local/runs/environment-mango-render-4NB54Dg5/installed-after-pytorch3d.txt`.
Compiler flags and object-build records remain under
`.local/pytorch3d/build/temp.linux-x86_64-cpython-314/`.

Executed build command (from the repository root, after the cached base/build
dependencies were installed):

```bash
UV_CACHE_DIR="$PWD/.local/cache/uv" FORCE_CUDA=1 \
  CUDA_HOME=/usr/local/cuda-13.0 TORCH_CUDA_ARCH_LIST=8.9 MAX_JOBS=8 \
  CC=/usr/bin/gcc CXX=/usr/bin/g++ CUDAHOSTCXX=/usr/bin/g++ \
  uv pip install --offline --python .local/envs/mango-render/bin/python \
  --torch-backend cu130 --constraint environments/constraints-cu130.txt \
  --no-build-isolation .local/pytorch3d
```

An online rerun of the complete Mango candidate setup remains blocked by sandbox
DNS access, logged in `.local/runs/environment-mango-render-BC20cx8j/setup.log`.
The PyTorch3D build does not imply that the full Mango candidate is installed.

The [verifier](../../scripts/verify-environment.py) asserts the fixed ABI and can
test synchronized CUDA matrix multiplication, PyTorch3D KNN forward/backward,
and point rasterization. In the sandbox, `torch.cuda.is_available()` returns false
and `nvidia-smi` cannot communicate with the driver. The failed STG GPU check is
saved at `.local/runs/environment-stg-render-AAfJtavJ/gpu-check.log`. This does not
diagnose the host driver. Repeat from authorized host execution before marking
any GPU check passed.

## Corrections made during execution

- Use an explicit method argument and interpreter; avoid stale `GS_PY` values.
- Reuse existing environments and record each attempt without clearing packages.
- Resolve build tools with candidate dependencies and save both the resolution
  and installed inventory.
- Run compound setup/build blocks with error handling so failures stop later commands.
- Import Torch before loading PyTorch3D's compiled extension.
- Explicitly request CUDA compilation and test real extension operations.

Repository Python tests (six) and viewer JavaScript tests (five) pass. They do not
validate research model compatibility.
