# Creating 4DGS data locally

[Repository overview](../README.md) · [Pretrained experiments](pretrained-experiments.md) · [Research](research.md) · [Input data](input-data.md) · [Rendering](rendering.md)

Target: Ubuntu 24.04 LTS, RTX 4090. Reviewed on 2026-09-05. The commands below are source-checked procedures, **not locally executed GPU results**. Older upstream environments are recorded explicitly; compatibility with this workstation still needs the checks below.

## Environment and workspace

First complete the [pretrained rendering experiments](pretrained-experiments.md). This guide is the later training phase; its training commands are not prerequisites for viewing downloaded models.

Use one environment per implementation, with separate dataset and output directories. Install Git, a Conda-compatible environment manager, a working NVIDIA driver, and the development tools required by the selected CUDA toolkit. A PyTorch CUDA runtime does not necessarily include `nvcc`, which these custom extensions need.

Run these checks before dependency installation:

```bash
nvidia-smi
nvcc --version
gcc --version
g++ --version
```

After installing PyTorch in each environment:

```bash
python -c 'import torch; print(torch.__version__, torch.version.cuda); assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0)); print(torch.cuda.get_device_capability(0)); print(torch.ones(1, device="cuda").sum().item())'
```

The CUDA version displayed by `nvidia-smi` describes driver capability, not the installed compiler. Compare it with `nvcc --version` and `torch.version.cuda`. Keep the compiler/runtime combination compatible and rebuild extensions after changing PyTorch or CUDA. [NVIDIA compatibility reference](https://docs.nvidia.com/datacenter/tesla/drivers/cuda-toolkit-driver-and-architecture-matrix.html)

### Ubuntu 24.04 and Ada compatibility

| Route | Reference stack | Status and adaptation |
| --- | --- | --- |
| HUST historical baseline | Python 3.7, PyTorch 1.13.1+cu116 | From upstream; not an Ubuntu 24.04 validation. Use an isolated environment and a CUDA 11.6-compatible host compiler. |
| SpacetimeGaussians historical baseline | Python 3.7.13, PyTorch 1.12.1, CUDA runtime 11.6; preprocessing Python 3.8 | Authors tested Ubuntu 20.04. Old MMCV/CUDA extensions are a particular build risk on a newer host. |
| Newer comparison | Mango-GS reports PyTorch 2.4.1+cu121; NoPo4D requires Python ≥3.10 | Independent implementations with newer dependency stacks; not drop-in dependency upgrades for the baselines. |

Sources: [HUST requirements](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/requirements.txt), [SpacetimeGaussians setup](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/script/setup.sh), [Mango-GS setup](https://github.com/htx0601/Mango-GS#installation), [NoPo4D setup](https://github.com/bralani/NoPo4D#installation).

Ada supports compatible Ampere binaries/PTX; native compute-8.9 compilation starts with CUDA 11.8. For a CUDA 11.6 baseline, a proposed extension-build setting is `TORCH_CUDA_ARCH_LIST="8.6+PTX"`. Verify the compiled extension with a real render; an import alone does not test its kernels. Do not ask an older compiler to compile `sm_89`. [NVIDIA Ada guide](https://docs.nvidia.com/cuda/ada-compatibility-guide/index.html)

On Ubuntu 24.04, do not assume the system-default GCC is supported by an old toolkit. Select a supported compiler explicitly for that environment, or use a local GPU development container with the older Ubuntu/CUDA userspace. That still runs on the workstation and uses the host GPU driver. This guide does not supply a tested container image or a certified modernized dependency lockfile. Any such adaptation belongs in the experiment record. Compare supported combinations in the [CUDA 11.6 Linux installation guide](https://docs.nvidia.com/cuda/archive/11.6.0/cuda-installation-guide-linux/index.html).

Run the [workspace and local environment-manager setup](pretrained-experiments.md#0-prepare-the-repository-workspace) first. From this repository root:

```bash
GS_ROOT="$(git rev-parse --show-toplevel)"
export GS_WORK="$GS_ROOT/.local"
mkdir -p "$GS_WORK/data" "$GS_WORK/runs"
```

The following commands assume these variables and the workspace cache settings remain set. Use a fresh output directory for each experiment. Environments and upstream checkouts stay inside `.local/`; our source, configurations, and result notes remain tracked.

## Experiment 1: HUST synthetic scene

### Install the reference environment

In a new checkout:

```bash
cd "$GS_WORK"
git clone https://github.com/hustvl/4DGaussians.git
cd 4DGaussians
git checkout --detach 843d5ac636c37e4b611242287754f3d4ed150144
git submodule update --init --recursive
git rev-parse HEAD
git submodule status --recursive
conda create -p "$GS_WORK/envs/gs-hust-reference" python=3.7
conda activate "$GS_WORK/envs/gs-hust-reference"
python -m pip install torch==1.13.1+cu116 torchvision==0.14.1+cu116 torchaudio==0.13.1 --extra-index-url https://download.pytorch.org/whl/cu116
python -m pip install -r requirements.txt
TORCH_CUDA_ARCH_LIST="8.6+PTX" python -m pip install -e submodules/depth-diff-gaussian-rasterization
TORCH_CUDA_ARCH_LIST="8.6+PTX" python -m pip install -e submodules/simple-knn
python -m pip check
python train.py --help
python render.py --help
```

The explicit wheel versions reproduce the upstream CUDA-runtime choice using [PyTorch's historical installation commands](https://pytorch.org/get-started/previous-versions/). The architecture setting is the proposed Ada adaptation described above. Use the matching `nvcc` and supported compiler before installing extensions. Package availability and unpinned transitive dependencies may still require resolution; record the resulting package versions rather than claiming a locked environment.

### Prepare and train

Download the D-NeRF dataset from the links in the [official D-NeRF repository](https://github.com/albertpumarola/D-NeRF). Extract `bouncingballs` into `$GS_WORK/data/dnerf/bouncingballs`, preserving its transforms and images. This is a benchmark sanity check; the [input guide](input-data.md) covers custom exports.

```bash
cd "$GS_WORK/4DGaussians"
test -f "$GS_WORK/data/dnerf/bouncingballs/transforms_train.json"
test -f "$GS_WORK/data/dnerf/bouncingballs/transforms_test.json"
python train.py \
  -s "$GS_WORK/data/dnerf/bouncingballs" \
  --model_path "$GS_WORK/runs/hust-bouncingballs" \
  --expname dnerf/bouncingballs \
  --configs arguments/dnerf/bouncingballs.py \
  --eval --port 6017 \
  --save_iterations 1000 20000 \
  --checkpoint_iterations 1000
```

The profile inherits a 3,000-iteration coarse stage and 20,000-iteration fine stage. The additional save/checkpoint at 1,000 gives an early artifact to inspect; it does not shorten the full run. `--eval` keeps the held-out data separate. Sources: [scene profile](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/arguments/dnerf/bouncingballs.py), [base profile](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/arguments/dnerf/dnerf_default.py), [training entry point](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/train.py).

Retain the complete run directory and the exact configuration. For final rendering, the `point_cloud/iteration_20000` directory contains the Gaussian PLY and deformation state, including `deformation.pth`, `deformation_table.pth`, and `deformation_accum.pth`. Keep `cfg_args` and the referenced dataset available. A training-resume `.pth` checkpoint and a renderable iteration directory serve different purposes. [Scene persistence](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scene/__init__.py), [deformation persistence](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scene/gaussian_model.py).

To resume an interrupted fine stage, repeat the training command with `--start_checkpoint "$GS_WORK/runs/hust-bouncingballs/chkpnt_fine_1000.pth"` after confirming that file exists. A coarse-stage interruption uses `chkpnt_coarse_1000.pth` instead. Preserve the same source, configuration, and output directory. This resume procedure is upstream-supported but untested here.

Render the saved scene using [the matching rendering procedure](rendering.md#hust-images-and-videos). Success means a fresh process can load the run and produce changing scene states over time, not merely that training exits successfully.

## Experiment 2: SpacetimeGaussians multi-view sequence

### Install isolated training and preprocessing environments

```bash
cd "$GS_WORK"
git clone https://github.com/oppo-us-research/SpacetimeGaussians.git
cd SpacetimeGaussians
git checkout --detach 427abfc
git submodule update --init --recursive
git rev-parse HEAD
git submodule status --recursive
```

Read `script/setup.sh` in this checkout. It contains legacy environment commands and a global Conda configuration change; the commands below select the relevant setup steps without applying that global setting. Environments use local prefixes. If an upstream script activates an environment by name internally, use a tracked local patch to point it at the corresponding prefix before execution.

```bash
conda create -p "$GS_WORK/envs/feature_splatting" python=3.7.13
conda activate "$GS_WORK/envs/feature_splatting"
conda install pytorch==1.12.1 torchvision==0.13.1 torchaudio==0.12.1 cudatoolkit=11.6 -c pytorch -c conda-forge
TORCH_CUDA_ARCH_LIST="8.6+PTX" python -m pip install \
  thirdparty/gaussian_splatting/submodules/gaussian_rasterization_ch9 \
  thirdparty/gaussian_splatting/submodules/gaussian_rasterization_ch3 \
  thirdparty/gaussian_splatting/submodules/forward_full \
  thirdparty/gaussian_splatting/submodules/forward_lite \
  thirdparty/gaussian_splatting/submodules/simple-knn
TORCH_CUDA_ARCH_LIST="8.6+PTX" python -m pip install -e thirdparty/mmcv -v
python -m pip install opencv-python natsort scipy kornia scikit-image plyfile tqdm Pillow
python -m pip check
python train.py --help
python test.py --help

conda create -p "$GS_WORK/envs/colmapenv" python=3.8
conda activate "$GS_WORK/envs/colmapenv"
python -m pip install opencv-python-headless tqdm natsort Pillow
conda install pytorch==1.12.1 -c pytorch -c conda-forge
conda install colmap -c conda-forge
colmap -h
```

Sources: [setup script](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/script/setup.sh), [test imports](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/test.py). `scikit-image` is included because the test entry point imports it. Check all imports and the GPU preflight before processing a dataset; this is not a complete transitive lockfile.

### Prepare Neural 3D data

Obtain `cook_spinach` and its calibration from the [official Neural 3D Video dataset repository](https://github.com/facebookresearch/Neural_3D_Video). Put a working copy at `$GS_WORK/data/n3v/cook_spinach`, keeping the archive/original capture separately. Upstream preprocessing creates and removes intermediate directories, so use the working copy.

From the SpacetimeGaussians checkout:

```bash
conda activate "$GS_WORK/envs/colmapenv"
python script/pre_n3d.py --videopath "$GS_WORK/data/n3v/cook_spinach"
```

This is the upstream benchmark-preprocessing entry point. It can process more frames than the short training window below. Inspect its frame loop before attempting a custom preprocessing subset. Expect per-frame `colmap_<index>` directories with images and sparse calibration/points. Training reads point data from each frame in its window, not only from `colmap_0`. [Preprocessing instructions](https://github.com/oppo-us-research/SpacetimeGaussians#processing-datasets), [point aggregation](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/thirdparty/gaussian_splatting/scene/dataset_readers.py).

### Start with a reduced smoke run

```bash
conda activate "$GS_WORK/envs/feature_splatting"
python train.py \
  --source_path "$GS_WORK/data/n3v/cook_spinach/colmap_0" \
  --model_path "$GS_WORK/runs/stg-spinach-smoke" \
  --configpath configs/n3d_lite/cook_spinach.json \
  --eval --duration 12 --resolution 4 --gtisint8 1 \
  --iterations 1000 --save_iterations 1000
```

These are deliberately reduced settings proposed for a first run, not paper-quality settings or a verified memory guarantee. The profile chooses the lite model; the overrides use 12 frames, stronger image downsampling, and integer ground-truth storage. Use the full `--configpath` spelling accepted by the [parser](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/thirdparty/gaussian_splatting/helper3dg.py), rather than relying on the README's abbreviated `--config`.

The parser uses equality with defaults to decide whether to apply JSON settings. An explicitly supplied value equal to a parser default can still be replaced by JSON. The overrides above differ from their conflicting defaults. For future profiles, inspect printed effective arguments; edit a copied config when you need an otherwise ambiguous value. [Argument definitions](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/thirdparty/gaussian_splatting/arguments/__init__.py).

After reloading and rendering the smoke run, start a separate longer run using the released 50-frame profile:

```bash
python train.py \
  --source_path "$GS_WORK/data/n3v/cook_spinach/colmap_0" \
  --model_path "$GS_WORK/runs/stg-spinach-lite" \
  --configpath configs/n3d_lite/cook_spinach.json \
  --eval --iterations 25000 --save_iterations 25000
```

The [profile](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/configs/n3d_lite/cook_spinach.json) uses `duration: 50`, `resolution: 2`, and `test_iteration: 25000`. Keep the final Gaussian iteration, `cfg_args`, configuration, and prepared-data metadata. Lite PLYs store temporal and motion parameters; full-model representations may also need an appearance-decoder checkpoint. Use the model-specific save/load implementation as the authority. [Lite persistence](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/thirdparty/gaussian_splatting/scene/ourslite.py).

Do not assume every exposed resume flag works for this variant: the inspected lite `capture()`/`restore()` tuple omits its motion and temporal parameters. Rendering a saved PLY is a different path. Treat exact interrupted-training recovery as unverified, and use fresh runs until a save/resume equivalence check establishes it. [Capture and restore source](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/thirdparty/gaussian_splatting/scene/ourslite.py).

## Memory and troubleshooting

For 24 GB-class experiments, increase one dimension at a time: frame count, image resolution, camera count, then model complexity. The SpacetimeGaussians reference reports 24 GB for Neural 3D and 48 GB for Technicolor; free memory on a display GPU can be smaller than its installed capacity. A short clip is a starting choice, not a proof that any world fits.

| Failure | Next diagnostic |
| --- | --- |
| `nvidia-smi` fails | Retry in an authorized host terminal to distinguish sandbox restrictions from a driver fault before investigating Python packages. |
| PyTorch works but rasterization fails | Check extension compiler, CUDA runtime, supported architecture, and rebuild logs |
| Missing `mmcv.Config` | HUST uses MMCV 1.x APIs; installing an unrelated current major release does not preserve them |
| Missing or incompatible COLMAP option | Compare the installed version with the preprocessing script; keep calibration/point outputs for inspection |
| CUDA out of memory | Reduce duration/resolution or supported batch/densification settings; inspect whether images or Gaussians dominate memory |
| HUST synthetic resolution does not shrink | Its reviewed loader forces 800×800; do not assume a generic resolution flag overrides it |
| HUST rendering runs out of memory | The renderer retains frame tensors; skip unneeded splits and use shorter rendering batches in any future adapter |
| SpacetimeGaussians metric failure | Inspect `scikit-image` compatibility: the test code uses the older `multichannel` SSIM argument |

For a longer world, independently trained time chunks require additional work to maintain continuity. This repository does not provide automatic chunk merging, streaming, or global scene composition.

## Acceptance procedure

These checks are to be run on the workstation; none is marked passed merely from reading source:

1. Confirm the GPU preflight, required imports, and an actual rasterization operation.
2. Train a small dynamic sequence into a new run directory and inspect effective configuration and loss behavior.
3. Reload the saved representation in a fresh process; render at least three scene times and an unseen viewpoint.
4. Inspect temporal flicker, geometry, background, and view-dependent artifacts. Compare against held-out images where available.
5. Load a compatible asset in a local viewer. Check camera motion, animation, and offline asset availability; record any missing time controls.
6. Record repeatability and memory before scaling up. Test resume separately from render reload.

Metrics such as PSNR/SSIM/LPIPS require matching held-out images and preprocessing. Perceptual metrics can download auxiliary weights on first use; cache them during setup before expecting network-free evaluation.

## Experiment record

Copy this template into your experiment notes; replace `not run` only with measured evidence:

```text
Experiment ID / date:
Method / repository URL / full commit / submodule commits:
Local patches / configuration / seed:
OS / GPU / driver / nvcc / host compiler:
Python / PyTorch / CUDA runtime / package inventory:
Dataset source / license / checksum or version:
Camera IDs / time range / frame count / image dimensions:
Training views / held-out views / temporal holdout:
Camera conventions / time normalization / scene scale:
Initialization / masks / preprocessing:
Exact creation and rendering commands:
Status: not run
Training wall time / preprocessing wall time:
Peak VRAM / sampling method / host RAM:
Gaussian count / complete model bytes / exported bytes:
Renderer / output resolution / warmup / timing boundaries / FPS:
Held-out metrics / temporal and visual observations:
Checkpoint reload / resume equivalence:
Viewer controls / export losses / local asset paths:
Failures and changes needed:
```

Useful inventory commands, executed in the upstream checkout and its environment:

```bash
git rev-parse HEAD
git submodule status --recursive
git diff --stat
python -m pip freeze
conda list
nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv
```

A single memory sample is not a peak measurement. For a measured run, sample throughout execution or add framework instrumentation and document what it includes. Count supporting networks and metadata when reporting model size, and distinguish pure render timing from data loading, metrics, and video encoding.
