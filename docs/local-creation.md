# Creating 4DGS data locally

[Repository overview](../README.md) · [Pretrained experiments](pretrained-experiments.md) · [Research](research.md) · [Input data](input-data.md) · [Rendering](rendering.md)

Target: Ubuntu 24.04 LTS, RTX 4090. Reviewed on 2026-09-05. The commands below are source-checked procedures, **not locally executed GPU results**. Older upstream environments are recorded explicitly; compatibility with this workstation still needs the checks below.

## Environment and workspace

First complete the [pretrained rendering experiments](pretrained-experiments.md). This guide is the later training phase; its training commands are not prerequisites for viewing downloaded models.

Use the [shared uv/Python 3.14/cu130 environment guide](environments.md) first. It selects Torch 2.13.0+cu130, torchvision 0.28.0+cu130 and the existing CUDA 13.0 toolkit, with one environment and extension cache per implementation. No older-toolkit or interpreter fallback is part of this workflow.

### Historical provenance and modern compatibility

| Route | Historical upstream stack (not installation instructions) | Current target status |
| --- | --- | --- |
| HUST | Python 3.7, PyTorch 1.13.1+cu116 | Adaptation pending: MMCV/config APIs and CUDA extensions |
| STG | Python 3.7.13, PyTorch 1.12.1/cu116; preprocessing Python 3.8 | Adaptation pending: bundled MMCV, science APIs, CUDA extensions and COLMAP CLI |
| Mango-GS | Python 3.8, PyTorch 2.4.1+cu121 | Adaptation pending: PyTorch3D and rasterizers |
| NoPo4D | Python ≥3.10 | Adaptation pending: complete backbone/model metadata, xFormers and gsplat |

Sources: [HUST requirements](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/requirements.txt), [STG setup](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/script/setup.sh), [Mango setup](https://github.com/htx0601/Mango-GS#installation), [NoPo4D setup](https://github.com/bralani/NoPo4D#installation).

The commands below depend on completing the selected method's compatibility gate; they are not validated ports. Keep the shared guide's `GS_ROOT`, `GS_WORK`, cache and compiler exports in each terminal. Use fresh output directories, keep originals separate from preprocessing, and retain reusable patches outside ignored upstream checkouts. Skip cloning an existing checkout after inspecting its revision and local changes.

## Experiment 1: HUST synthetic scene

### Prepare the modern environment

In a new checkout:

```bash
cd "$GS_WORK"
git clone https://github.com/hustvl/4DGaussians.git
cd 4DGaussians
git checkout --detach 843d5ac636c37e4b611242287754f3d4ed150144
git submodule update --init --recursive
git rev-parse HEAD
git submodule status --recursive
```

Use `GS_ENV=hust` in the shared guide to install the [candidate dependencies](../environments/hust.in). Audit upstream requirements and port MMCV/config and Torch/CUDA APIs before the following conditional builds. Do not run upstream legacy setup commands.

```bash
cd "$GS_WORK/4DGaussians"
uv pip install --python "$GS_WORK/envs/hust/bin/python" --torch-backend cu130 \
  --constraint "$GS_ROOT/environments/constraints-cu130.txt" --no-build-isolation \
  -e submodules/depth-diff-gaussian-rasterization -e submodules/simple-knn
uv pip check --python "$GS_WORK/envs/hust/bin/python"
"$GS_WORK/envs/hust/bin/python" train.py --help
"$GS_WORK/envs/hust/bin/python" render.py --help
```

Resolve the chosen configuration implementation as part of the port, then complete the shared base/import/build/rasterization checks. Successful help output alone does not establish training compatibility.

### Prepare and train

Download the D-NeRF dataset from the links in the [official D-NeRF repository](https://github.com/albertpumarola/D-NeRF). Extract `bouncingballs` into `$GS_WORK/data/dnerf/bouncingballs`, preserving its transforms and images. This is a benchmark sanity check; the [input guide](input-data.md) covers custom exports.

```bash
cd "$GS_WORK/4DGaussians"
test -f "$GS_WORK/data/dnerf/bouncingballs/transforms_train.json"
test -f "$GS_WORK/data/dnerf/bouncingballs/transforms_test.json"
"$GS_WORK/envs/hust/bin/python" train.py \
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

Reuse `stg-render` and `stg-colmap` from the [pretrained STG setup](pretrained-experiments.md#prepare-the-modern-environment-and-port-the-renderer), or create them using the shared guide. Do not run `script/setup.sh`: it describes the historical stack. Port and validate the renderer and preprocessing dependencies before training; native COLMAP is supplied separately from Python packages.

### Prepare Neural 3D data

Obtain `cook_spinach` and its calibration from the [official Neural 3D Video dataset repository](https://github.com/facebookresearch/Neural_3D_Video). Put a working copy at `$GS_WORK/data/n3v/cook_spinach`, keeping the archive/original capture separately. Upstream preprocessing creates and removes intermediate directories, so use the working copy.

From the SpacetimeGaussians checkout:

```bash
"$GS_WORK/envs/stg-colmap/bin/python" script/pre_n3d.py --videopath "$GS_WORK/data/n3v/cook_spinach"
```

This is the upstream benchmark-preprocessing entry point. It can process more frames than the short training window below. Inspect its frame loop before attempting a custom preprocessing subset. Expect per-frame `colmap_<index>` directories with images and sparse calibration/points. Training reads point data from each frame in its window, not only from `colmap_0`. [Preprocessing instructions](https://github.com/oppo-us-research/SpacetimeGaussians#processing-datasets), [point aggregation](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/thirdparty/gaussian_splatting/scene/dataset_readers.py).

### Start with a reduced smoke run

```bash
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions/stg-render-py314-torch213-cu130"
"$GS_WORK/envs/stg-render/bin/python" train.py \
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
"$GS_WORK/envs/stg-render/bin/python" train.py \
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
uv / Python executable and GIL build / PyTorch / CUDA runtime:
Candidate spec / constraints / resolved lock / package inventory:
Resolution / imports / extension build / real render validation stages:
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

Useful inventory commands, executed in the upstream checkout and with `GS_ENV` set to its shared-guide environment name:

```bash
git rev-parse HEAD
git submodule status --recursive
git diff --stat
uv --version
uv pip freeze --python "$GS_WORK/envs/$GS_ENV/bin/python"
nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv
```

A single memory sample is not a peak measurement. For a measured run, sample throughout execution or add framework instrumentation and document what it includes. Count supporting networks and metadata when reporting model size, and distinguish pure render timing from data loading, metrics, and video encoding.
