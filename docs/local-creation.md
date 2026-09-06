# Creating 4DGS data locally

[Repository overview](../README.md) · [Pretrained experiments](pretrained-experiments.md) · [Research](research.md) · [Input data](input-data.md) · [Rendering](rendering.md)

Target: Ubuntu 24.04 LTS, RTX 4090. Historical upstream procedures below remain
conditional. The plan-004 STG integration commands have executed locally; see
the [growth and offline evaluation record](experiments/contender-growth-20260906.md)
for measured results and remaining limitations.

## Environment and workspace

For plan 004, prepare the shared SelfCap input with:

```bash
.local/envs/stg-colmap/bin/python scripts/prepare-selfcap.py \
  --videos .local/data/selfcap/hair-release/videos \
  --calibration .local/data/selfcap/hair-calib/optimized \
  --output .local/data/selfcap/dance1-processed-NEW
```

Install the tracked `stg-colmap.in` dependencies first. This route uses
pycolmap 4.2.0's native COLMAP undistortion with `blank_pixels=0`, followed by
OpenCV area resizing. The output manifest contains explicit camera transforms,
per-image hashes and corrected times. It retains all 60 source frame IDs per
camera, with a common normalized interval covering their corrected timestamps;
do not replace these times with the nominal frame index divided by 60.
The 20-pose sweep uses rotation SLERP and linear camera-center interpolation,
holding test-camera intrinsics fixed. Calibration-only mode is available for
checking geometry before decoding. Output directories must be new.

The STG SelfCap entry point now supports budget-counted integration runs and
resumption (commands below). Densification and EMS now have targeted validation;
the full two-hour training runs and comparison remain unfinished.
Do not launch the generic command wrapper as an unattended training scheduler.

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

## Training-only SelfCap initialization

After preparing and verifying the SelfCap manifest, generate a new sparse cloud
from training cameras only (CPU preprocessing, outside the training budget):

```bash
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python scripts/initialize-selfcap.py \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --output .local/data/selfcap/dance1-initialization-20260906
```

The output directory must not already exist. Source frame 4150 is selected by default from
each of the 23 training cameras; supplied intrinsics and poses remain fixed.
`inputs.json` records image and manifest hashes, and `result.json` records point
count and reprojection error. The sparse cloud still needs coverage inspection
before training; low reprojection error alone does not validate motion timing.

For an individual temporal-initialization frame, add `--frame-id 4120` (or another
frame in `[4120,4180)`) and use a separate output directory. This preserves fixed
calibration, held-out exclusion and image-hash evidence for that frame; it does
not estimate temporal correspondences by itself.

For the FreeTimeGS sparse reproduction initialization, prepare frame pairs at
keyframes 4120, 4125, ..., 4175 and their next frames using the command above.
Keep each cloud in `dance1-initialization-frameFRAME-20260906`; the existing
midpoint directory can be reused for frame 4150. Assemble the audited clouds:

```bash
FTGS_CLOUD_ARGS=()
for FTGS_KEYFRAME in {4120..4175..5}; do
  for FTGS_FRAME in "$FTGS_KEYFRAME" "$((FTGS_KEYFRAME + 1))"; do
    FTGS_CLOUD=".local/data/selfcap/dance1-initialization-frame${FTGS_FRAME}-20260906"
    if [ "$FTGS_FRAME" = 4150 ]; then
      FTGS_CLOUD=.local/data/selfcap/dance1-initialization-20260906
    fi
    FTGS_CLOUD_ARGS+=(--cloud "$FTGS_FRAME" "$FTGS_CLOUD")
  done
done
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/freetimegs/bin/python \
  scripts/prepare-freetimegs-initialization.py \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --output .local/data/selfcap/dance1-freetimegs-sparse-initialization-20260906 \
  "${FTGS_CLOUD_ARGS[@]}"
```

Use a new output directory for reruns. The result records sparse geometry,
nearest-neighbor motion-estimation and fractional synchronization limitations;
it must not be described as the reproduction's dense ROMA initialization.

Inspect the untrained initialization before training (GPU inference only):

```bash
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/freetimegs/bin/python \
  scripts/preview-freetimegs-initialization.py \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --initialization .local/data/selfcap/dance1-freetimegs-sparse-initialization-20260906 \
  --output .local/runs/freetimegs-initialization-preview-20260906
```

For the released EDGS-based dense candidate, first prepare the pinned RoMa
checkout and hash-verified local weights as recorded in experiment 007. This
workflow requires EDGS's non-commercial terms; retain `docs/licenses/EDGS.txt`.
Generate each cloud sequentially on the GPU, using fresh output paths for reruns:

```bash
EDGS_CLOUD_ARGS=()
for EDGS_KEYFRAME in {4120..4175..5}; do
  for EDGS_FRAME in "$EDGS_KEYFRAME" "$((EDGS_KEYFRAME + 1))"; do
    EDGS_CLOUD=".local/data/selfcap/dance1-edgs-frame${EDGS_FRAME}-20260906"
    /home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/roma/bin/python \
      scripts/initialize-edgs-selfcap.py \
      --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
      --edgs .local/EDGS --roma .local/RoMa-edgs --weights .local/weights/roma-edgs \
      --frame-id "$EDGS_FRAME" --output "$EDGS_CLOUD" || break 2
    EDGS_CLOUD_ARGS+=(--cloud "$EDGS_FRAME" "$EDGS_CLOUD")
  done
done
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/freetimegs/bin/python \
  scripts/prepare-freetimegs-initialization.py --dense-edgs \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --output .local/data/selfcap/dance1-freetimegs-edgs-initialization-20260906 \
  "${EDGS_CLOUD_ARGS[@]}"
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/freetimegs/bin/python \
  scripts/preview-freetimegs-initialization.py \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --initialization .local/data/selfcap/dance1-freetimegs-edgs-initialization-20260906 \
  --output .local/runs/freetimegs-edgs-initialization-preview-20260906
```

Only run assembly after all 24 cloud commands succeed. It rejects incomplete
sets. The EDGS pipeline is an adapted geometry-only fast path, not a full EDGS
model, and these operations do not train FreeTimeGS.

Validate checkpoint groundwork separately from experiment training:

```bash
.local/envs/stg-render/bin/python -m unittest discover -s tests -v
.local/envs/stg-render/bin/python scripts/verify-stg-checkpoint.py \
  --checkout .local/SpacetimeGaussians
```

The second command uses the GPU and native STG model/optimizer classes with
synthetic parameters. Exact next-step equality is a serializer check, not a
substitute for scene-training resume and offline renderer reload validation.

Validate the manifest-native cameras with the actual training rasterizers:

```bash
.local/envs/stg-render/bin/python scripts/verify-stg-manifest-renderer.py \
  --checkout .local/SpacetimeGaussians \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --output .local/runs/stg-manifest-renderer-NEW
```

This uses synthetic Gaussians and a full-size processed camera for both Lite
and Full forward/backward checks; it does not optimize against SelfCap images.
The camera adapter preserves fractional timestamps and calibrated principal
points and loads RGB images on demand. The supervised STG entry point below
connects training, checkpoints and budget accounting.

## Budget-counted STG SelfCap integration

These commands train on real images and consume the method's two-hour SelfCap
allocation, including startup and failed attempts. Use a new output directory
for every attempt. Do not remove or replace the central ledger at
`.local/runs/plan-004-training-budget.json` to retry an experiment.

```bash
.local/envs/stg-render/bin/python scripts/train-stg-manifest.py \
  --checkout .local/SpacetimeGaussians \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --initialization .local/data/selfcap/dance1-initialization-20260906 \
  --output .local/runs/stg-full-selfcap-integration-NEW \
  --model full --max-steps 2
```

Use `--model lite` with its own output for the matched Lite baseline. To test
resumption, use a new output and add
`--resume .local/runs/stg-full-selfcap-integration-NEW/checkpoint.pt`.
`--max-steps 2` then executes two additional steps without changing the
30,000-step optimizer schedule. The supervisor launches the worker itself;
do not invoke `--worker` manually. Do not remove the short-run limit until
the densification/EMS and initialization-coverage gates in the
[integration record](experiments/contender-training-20260906.md) are resolved.

Render every held-out sample and the common sweep from that checkpoint:

```bash
.local/envs/stg-render/bin/python scripts/render-stg-manifest.py \
  --checkout .local/SpacetimeGaussians \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --checkpoint .local/runs/stg-full-selfcap-integration-NEW/checkpoint.pt \
  --output .local/runs/stg-full-selfcap-render-NEW --benchmark
```

Rendering is outside the training ledger. This command validates all pinned
checkpoint component hashes and refuses changed source/input files; it does
not establish network isolation or compare reload output automatically.
Short integration checkpoints are not suitable for quality rankings.

## EMS fix, offline reload, and evidence packaging

Apply the identity-quaternion EMS patch once to the pinned, compatibility-patched
STG checkout before training beyond EMS. Preserve existing checkout edits:

```bash
git -C .local/SpacetimeGaussians apply --unidiff-zero --check \
  ../../patches/stg-ems-quaternion.patch
git -C .local/SpacetimeGaussians apply --unidiff-zero \
  ../../patches/stg-ems-quaternion.patch
.local/envs/stg-render/bin/python scripts/verify-stg-growth.py \
  --checkout .local/SpacetimeGaussians \
  --output .local/runs/stg-growth-NEW.json --require-valid
```

The patch is already applied in the recorded local run. A reverse `--check`
identifies this state; do not apply it twice. Existing checkpoints retain strict
source hashes, so keep pre-patch checkpoints with their matching source.

Prefix rendering with the offline launcher, using a new output for each reload:

```bash
.local/envs/stg-render/bin/python scripts/offline-python.py \
  scripts/render-stg-manifest.py \
  --checkout .local/SpacetimeGaussians \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --checkpoint .local/runs/stg-lite-selfcap-ems-20260906/checkpoint.pt \
  --output .local/runs/stg-lite-offline-NEW --benchmark
```

The launcher requires Linux and `libseccomp.so.2`. It validates the intended
socket restrictions before executing the renderer; unexpected setup/device
failures must be reported, not bypassed. Local Unix-domain IPC remains allowed.
Repeat in a fresh process and use `analyze-sequence.py --previous-run` for both
the `images/0015` and `sweep` directories.

Package the shared fixed crops, contact sheets and videos:

```bash
.local/envs/stg-render/bin/python scripts/package-stg-evidence.py \
  --render-directory .local/runs/stg-lite-offline-NEW \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --crops configs/detail-crops.selfcap-dance1.json \
  --output .local/runs/stg-lite-evidence-NEW
```

Run `evaluate-reconstruction.py --lpips-alex` separately against the complete
processed `images/0015` directory. Set `TORCH_HOME` to the existing
`.local/cache/torch` when evaluating offline. Packaging uses CPU FFmpeg, retains
native PNG dimensions, and pads videos by one bottom row for H.264 4:2:0.

### Sequential evaluation pipeline

After training stops, run the complete evaluation workflow with no other GPU
experiment active. This command performs two fresh offline reloads, benchmarks
the first, validates complete frame sets, records byte/pixel equality and
numerical differences, computes all three metrics, and packages the fixed crops
and videos. It stops on the first subprocess failure and prints that command
and its log; it never installs dependencies or downloads missing weights.

```bash
.local/envs/stg-render/bin/python scripts/evaluate-stg-checkpoint.py \
  --checkout .local/SpacetimeGaussians \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --checkpoint .local/runs/stg-lite-selfcap-5000-20260906/checkpoint.pt \
  --crops configs/detail-crops.selfcap-dance1.json \
  --torch-cache .local/cache/torch \
  --output .local/runs/stg-lite-selfcap-5000-evaluation-20260906
```

Output directories must be new. `commands.json` records exact subprocess
commands, `evaluation.json` is written only after all stages succeed, and each
stage retains a separate log. Metrics/encoding use two CPU threads. This
adapter currently accepts only the SelfCap dance1 held-out profile. Evaluation
is outside the training ledger. PNG equality does not establish floating-point
model-state or next-training-step equality.

The pipeline now records each stage's UTC start/end, monotonic wall seconds,
exit code and status in `commands.json`, including failed launches. Successful
`evaluation.json` reports also include total evaluation wall time. Older Lite
evaluation reports predate these timing fields; do not infer their missing times.

After both evaluations finish, generate checked metric deltas:

```bash
.local/envs/stg-render/bin/python scripts/compare-stg-evaluations.py \
  --first .local/runs/stg-lite-selfcap-5000-evaluation-20260906 \
  --second .local/runs/stg-full-selfcap-5000-evaluation-20260906 \
  --output .local/runs/stg-selfcap-5000-comparison-20260906.json
```

This checks manifest hashes, metric definitions, rendered camera/time samples,
sweep identity, frame completeness and internal report consistency. Output
deltas are **second minus first**, including per-frame differences. It retains
both iteration counts and incomplete-training flags. Different iteration counts
are labeled, not silently equated; equal iterations do not establish equal
training time. Infinite-PSNR differences are recorded as JSON null.

## ATGS Python environment gate

```bash
bash scripts/setup-environment.sh atgs
git -C .local/ATGS apply --check ../../patches/atgs-mmengine-config.patch
git -C .local/ATGS apply ../../patches/atgs-mmengine-config.patch
.local/envs/atgs/bin/python scripts/verify-atgs-config.py \
  --checkout .local/ATGS --output .local/runs/atgs-config-NEW.json
```

The patch is already applied in the recorded checkout; use a reverse `--check`
to identify that state rather than applying twice. These checks do not validate
GPU access, native extensions, complete model reload or training. See the
[ATGS report](experiments/009-atgs.md) for remaining integration gates.

### tiny-cuda-nn 1.7 dependency

The repository has no `v1.7` tag. The ATGS dependency choice is an explicit
pre-2.0/JIT commit declaring version 1.7; do not silently upgrade it to main.

```bash
git clone https://github.com/NVlabs/tiny-cuda-nn.git .local/tiny-cuda-nn-atgs
git -C .local/tiny-cuda-nn-atgs switch --detach 32507f059d7abc8c13f5df81ea9597b70923ee44
git -C .local/tiny-cuda-nn-atgs submodule update --init --recursive -- dependencies/cutlass dependencies/fmt
git -C .local/tiny-cuda-nn-atgs apply --check ../../patches/tcnn17-python314-cu130.patch
git -C .local/tiny-cuda-nn-atgs apply ../../patches/tcnn17-python314-cu130.patch
bash scripts/build-atgs-tcnn.sh
.local/envs/atgs/bin/python scripts/verify-atgs-tcnn.py --output .local/runs/atgs-tcnn-NEW.json
```

Use the existing clone when present; preserve local edits and do not reapply
patches. The build script checks all three source revisions and the applied
patch, uses two compiler jobs and explicit SM89, and installs offline without
changing dependencies. Compilation runs on CPU; the final verifier requires
GPU access and never falls back to CPU. It tests one ATGS-shaped encoder/MLP,
not the complete multi-encoder ATGS model or its renderer.

### Recovered ATGS rasterizer and KNN

ATGS omits its referenced native source directory. The same author's LocalDyGS
bundles a candidate rasterizer with the required two-output forward and
`visible_filter` interface, and `simple_knn`. This is an explicit dependency
choice, not a verified original ATGS pin. Preserve its research-only license.
Use existing clones when present and reverse-check already applied patches.

```bash
git clone https://github.com/WuJH2001/LocalDyGS.git .local/LocalDyGS
git -C .local/LocalDyGS switch --detach 39dacdcd8ef6d2b93824df79041713b4a29fb828
git -C .local/LocalDyGS apply --check ../../patches/localdygs-cstdint.patch
git -C .local/LocalDyGS apply ../../patches/localdygs-cstdint.patch
git -C .local/ATGS apply --check ../../patches/atgs-optional-imports.patch
git -C .local/ATGS apply ../../patches/atgs-optional-imports.patch
bash scripts/build-atgs-rasterizer.sh
.local/envs/atgs/bin/python scripts/verify-atgs-rasterizer.py --output .local/runs/atgs-rasterizer-NEW.json
```

The offline build targets SM89; it does not execute GPU kernels. The final
command requires GPU access and tests synthetic forward/backward, visibility,
and KNN distances against a brute-force reference. It is not a full ATGS
renderer, manifest-adapter, or checkpoint validation. Torch-scatter and the
complete model integration remain separate gates.

### ATGS scatter dependency and module-import gate

```bash
git clone --branch 2.1.2 --depth 1 https://github.com/rusty1s/pytorch_scatter.git .local/pytorch-scatter-atgs
bash scripts/build-atgs-scatter.sh
.local/envs/atgs/bin/python scripts/verify-atgs-imports.py --output .local/runs/atgs-imports-NEW.json
```

The build checks commit `140d3ad677aae615767412873b90982cbf97d35d` and requests
both CUDA and CPU extensions explicitly. The verifier requires GPU access,
checks scatter-max forward/backward and imports ATGS model/render modules.
It does not import `train_long`, which allocates LPIPS-VGG at module import,
or execute a full ATGS model. See the experiment report for observed status.

### ATGS full-model smoke test

```bash
git -C .local/ATGS apply --check ../../patches/atgs-render-eval-unpack.patch
git -C .local/ATGS apply ../../patches/atgs-render-eval-unpack.patch
.local/envs/atgs/bin/python scripts/verify-atgs-model.py --output .local/runs/atgs-model-NEW.json
```

This requires GPU access and performs no optimizer steps. It tests the full
representation on synthetic 64×64 views, not the matched evaluation resolution.
The upstream automatic encoder count becomes three for the 60-frame profile;
the configured optimizer schedule is not shortened. The shared-profile config
loader disables duplicate resizing/synchronization and records ignored legacy
config keys. No training entry-point LPIPS download occurs.
Apply the inference unpacking patch only once; reverse-check if already applied.
The verifier compares training-mode and inference-mode images at all three
synthetic timestamps. This does not test offline checkpoint reload.

To probe native directory save/reload, use new report and checkpoint paths:

```bash
.local/envs/atgs/bin/python scripts/verify-atgs-model.py --output .local/runs/atgs-native-reload-NEW.json --native-checkpoint .local/runs/atgs-native-checkpoint-NEW
```

This retains the synthetic native checkpoint and records component sizes and
hashes. It only checks in-process inference reload, using a supplied lifetime
cloud; it does not claim optimizer, RNG, sampler, or offline fresh-process
resumption. Both destination paths must be unused.

Add `--restore-auxiliary` to the probe with new destination paths to save and
restore supplemental model tensors and rebuild the native optimizers. This
also checks tensor values and gradient flags, but only empty Adam states are
exercised because the smoke test takes no optimizer steps. It is not yet a
complete resumable checkpoint adapter.

For populated Adam-state validation, add `--populate-optimizer-state` alongside
`--restore-auxiliary`, again using unused report/checkpoint paths. This performs
three synthetic updates (one per encoder), then verifies both restored optimizer
state dictionaries exactly. It does not exercise the matched training loop's
gradient accumulation, warmup, RNG/sampler continuation or next-update equality.

Apply the scheduler compatibility patch before creating populated optimizer
checkpoints (only once; reverse-check if already applied):

```bash
git -C .local/ATGS apply --check ../../patches/atgs-lr-python-float.patch
git -C .local/ATGS apply ../../patches/atgs-lr-python-float.patch
```

This prevents NumPy learning-rate scalars from entering new optimizer files.
It does not rewrite existing checkpoints or disable restricted Torch loading.

Add `--check-next-update` to the populated-state probe to compare a fourth
synthetic update on both the original and restored model. Choose unused report
and checkpoint paths. The report distinguishes successful finite execution from
exact equality and includes parameter/image differences and optimizer-state
equality. It is still an in-process check, not offline training resumption.

The next-update check also runs a same-model repeated-backward control with no
optimizer updates and restored Torch RNG state. It records per-parameter
gradient differences and per-group post-update parameter differences, helping
distinguish backward variability from checkpoint-specific effects. CPU copies
of gradients add host memory overhead; the diagnostic is not a throughput test.

### ATGS fresh-process offline inference

```bash
.local/envs/atgs/bin/python scripts/verify-atgs-offline.py --checkpoint .local/runs/atgs-backward-control-checkpoint-20260906 --evidence .local/runs/atgs-backward-control-cuda-20260906.json --output .local/runs/atgs-offline-a-NEW.json
.local/envs/atgs/bin/python scripts/verify-atgs-offline.py --checkpoint .local/runs/atgs-backward-control-checkpoint-20260906 --evidence .local/runs/atgs-backward-control-cuda-20260906.json --reference .local/runs/atgs-offline-a-NEW.json --output .local/runs/atgs-offline-b-NEW.json
```

Both runs require GPU access. The verifier installs the existing seccomp network
guard before Torch import; its socket-denial self-tests are intentional. It
requires checkpoint hashes to match the successful evidence and reconstructs
lifetimes from the supplemental file, without the original cloud. The second
process checks exact float-image hashes against the first, at all three
synthetic timestamps. This is inference-only, not sampler/optimizer resumption.

### Training RNG validation

```bash
.local/envs/atgs/bin/python scripts/verify-training-rng.py --output .local/runs/training-rng-cuda-NEW.json
```

This requires GPU access and verifies exact Python, NumPy (including cached
Gaussian), Torch CPU and all visible Torch CUDA sample sequences after a
weights-only checkpoint round trip. It performs no model training and does not
validate the sampler cursor or gradient-accumulation state.

The checkpointable manifest sampler is `atgs_sampler.ManifestBalancedSampler`.
Construct it with the validated `ATGSSelfCapScene`, effective encoder count and
seed; `next(sampler)` returns a training `(camera_id, frame_id)` key. Save its
`state_dict()` alongside the training state and restore with `load_state_dict()`.
Its dedicated generator and saved cursor support mid-batch and cross-epoch
continuation. Do not attach a prefetched DataLoader: the cursor records keys
already handed to the synchronous loop, not completed background loads.
Full accumulation/model checkpoint integration remains pending.

`atgs_loop_state.capture_loop_state(model, sampler, loop)` captures the
supplemental gradient/RNG/sampler state after a completed microstep. The loop
dictionary contains `iteration`, `micro_steps`, `encoder_visits`, `update_count`,
`last_update_iteration` and `ema_loss`. Gradients must still be unaveraged;
at a completed optimizer-update boundary they must be cleared with zero visits.
Serialize this supplement together with the corresponding model checkpoint.

Call `restore_loop_state` only after restoring the model and both optimizers;
use its returned loop dictionary to resume bookkeeping. CUDA state is required
by default; `include_cuda=False` is solely for explicit CPU fixtures. This API
is a tested component, not an executable ATGS training adapter or an atomic
checkpoint bundle writer.

### ATGS partial-accumulation validation

```bash
.local/envs/atgs/bin/python scripts/verify-atgs-accumulation.py --checkpoint .local/runs/atgs-backward-control-checkpoint-20260906 --evidence .local/runs/atgs-backward-control-cuda-20260906.json --output .local/runs/atgs-accumulation-cuda-20260906.json
```

This GPU probe requires the hash-verified three-update synthetic checkpoint and
an unused output path. It saves pending gradients, sampler cursor and RNG after
one microstep, then compares uninterrupted and restored completion of the
three-encoder accumulation cycle. Sample keys, random targets and warmup factors
must match exactly; finite parameter differences are reported separately and
are not required to be zero. A passing report does not establish bit-exact
training resumption.

`atgs_update.load_update_helpers` extracts only the five upstream accumulation
helpers from `train_long.py`, avoiding its module-level LPIPS initialization.
The report records their AST hash. A CPU regression checks gradient averaging,
warmup, learning-rate restoration and gradient clearing. The GPU probe uses the
native model and optimizers in one process; it is not a fresh-process resume
test, an atomic checkpoint bundle, or SelfCap scene training.

### ATGS commit-marked checkpoint bundles

`atgs_bundle.save_bundle(directory, model, sampler, loop, provenance)` saves
native model files, both optimizers, auxiliary tensors and the loop supplement
in one exclusively created directory. The parent must exist. Call it
synchronously after a completed microstep, keeping training paused until it
returns; pending gradients must not yet have been averaged. CUDA capture is
required by default.

Supply `manifest_sha256`, `source_revision`, `config_sha256` and
`helper_ast_sha256` in `provenance`, computed from the actual shared manifest,
source revision, resolved configuration and selected upstream helper AST.
The writer hashes every component, fsyncs the files and atomically publishes
`bundle.json` last, then syncs the checkpoint and parent directories. This is
a completion-marker protocol, not an atomic directory replacement. Interrupted
directories are retained for diagnosis and existing destinations are never
overwritten. There is no automatic latest-checkpoint pointer.

Use `load_bundle_supplements(directory, expected_provenance=provenance)` to
verify completion, all component hashes and expected provenance before
weights-only loading the auxiliary and loop supplements on CPU. It returns
`(auxiliary, loop_state, record)`. Restore native files and auxiliary state
before constructing/loading both optimizers; restore loop state last. Bundles
must remain immutable while loading. These hashes detect accidental mismatch,
not maliciously replaced data, and native model restoration remains the
caller's responsibility. CPU fixture tests cover publication, interruption,
overwrite refusal, corruption, counter mismatch and provenance checks; native
GPU bundle round-trip and production training integration remain pending.

To exercise the bundle with the native GPU accumulation probe, use a new
report and bundle directory (allow several GB of additional disk space):

```bash
.local/envs/atgs/bin/python scripts/verify-atgs-accumulation.py --checkpoint .local/runs/atgs-backward-control-checkpoint-20260906 --evidence .local/runs/atgs-backward-control-cuda-20260906.json --output .local/runs/atgs-bundle-cuda-20260906.json --bundle .local/runs/atgs-accumulation-bundle-20260906
```

With `--bundle`, the restored native model and both optimizers are loaded from
the newly written bundle, not the original fixture. The report includes the
verified bundle record and storage mode. Its manifest digest represents the
synthetic cameras/timestamps, not the SelfCap manifest; the configuration hash
covers resolved argparse settings, and the source revision and helper AST hash
are also recorded. This remains a same-process synthetic test. Omitting the
flag retains the earlier in-memory supplement check.

Fresh-process training-resume probes use only the bundle and its successful
report, without the original checkpoint or initialization fixture files:

```bash
.local/envs/atgs/bin/python scripts/verify-atgs-accumulation.py --resume-bundle .local/runs/atgs-accumulation-bundle-20260906 --reference .local/runs/atgs-bundle-cuda-20260906.json --output .local/runs/atgs-resume-offline-a-20260906.json
.local/envs/atgs/bin/python scripts/verify-atgs-accumulation.py --resume-bundle .local/runs/atgs-accumulation-bundle-20260906 --reference .local/runs/atgs-resume-offline-a-20260906.json --output .local/runs/atgs-resume-offline-b-20260906.json
```

This mode installs the seccomp network guard before Torch import; intentional
socket-denial self-tests are expected. GPU access is required. It restores both
optimizers and pending gradients, consumes the remaining two synthetic views,
and performs the upstream accumulation update. Sample keys, random targets,
discrete counters and warmup must match the reference. Loss differences and
post-update parameter hashes are recorded separately. A reference without
parameter hashes yields `reference_parameters_exact: null`, not an equality
claim; subsequent runs can compare parameter hashes but do not quantify their
numerical differences. This is a synthetic resume test, not scene training.

### ATGS deadline-aware loop controller

`atgs_train_control.run_training_segment` provides synchronous microstep,
balanced-update and checkpoint control. Bind `microstep` to the scene's native
forward/loss/backward operation, `update` to the extracted upstream accumulation
helper with resolved options, and `checkpoint` to a new bundle destination for
each save. Pass the full upstream iteration limit, not a shortened schedule.

The caller must hold an active `TrainingBudget` reservation, pass its
`remaining_seconds`, and run under the external hard-deadline supervisor.
Positive `checkpoint_reserve` and `step_reserve` estimates reserve time for
checkpoint I/O and a complete microstep plus possible update. They are estimates,
not enforced execution timeouts. Measured conservative values are required
before scene training; defaults are not validated for this model's I/O costs.

The controller saves only after completed microsteps (or before starting any),
and does not flush incomplete encoder accumulation merely because the deadline
or checkpoint interval was reached. The full schedule end does flush pending
gradients. Supply `force_update_due(iteration)` for native save/test/densification
boundaries. A forced partial update restarts the balanced sampler before the
optional `after_microstep(model, iteration, updated)` callback, which can perform
post-update densification and scheduled buffer cleanup. Failed callbacks propagate without checkpointing
partially executed work: discard the live state and reload a previously committed
bundle. Budget accounting must charge failures. Periodic saves and final/deadline
saves do not duplicate the same boundary. CPU tests cover balanced updates,
partial snapshots, continuation counters, callback failure and deadline overrun.
This controller is not yet wired to production ATGS scene loss/densification.

`atgs_native_step.NativeTrainingStep` supplies native hash/3DGS callbacks:
L1/SSIM/scaling loss, gradient sanitization, active densification statistics,
post-update anchor adjustment and scheduled buffer cleanup. Bind its callable,
`update`, `force_update_due` and `after_microstep` methods to the controller.
Loss helpers are extracted without importing the unused module-level CUDA
MS-SSIM metric. The native helper AST hash is recorded by this standalone probe:

```bash
.local/envs/atgs/bin/python scripts/verify-atgs-model.py --output .local/runs/atgs-native-statistics-cuda-20260906.json --native-training-step
```

This uses three synthetic views at iteration 1 with an explicitly recorded
diagnostic-only `start_stat=0` override to exercise the active statistics path,
without advancing a real scene schedule or stepping optimizers. Selected native
defaults have `start_stat=150000000`, `update_until=30000`, `iterations=100000`:
statistics and densification are inactive throughout that production schedule.
The diagnostic also explicitly allocates the normally inactive statistics
buffers on CUDA; ordinary native training setup leaves them empty on CPU.
It does not test actual anchor growth. CPU tests cover the loss combination,
statistics gating, post-update densification ordering, cleanup and bad targets.
Production scene construction, growth validation and budgeted execution remain
pending.

### ATGS supervised SelfCap trainer

`train-atgs-manifest.py` connects native callbacks and bundle resumption to the
shared manifest and training-only initialization. The executable is ready for
GPU integration validation; do not treat its existence as a completed scene run.

```bash
.local/envs/atgs/bin/python scripts/train-atgs-manifest.py --check-gpu
.local/envs/atgs/bin/python scripts/train-atgs-manifest.py --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --initialization .local/data/selfcap/dance1-initialization-20260906 --output .local/runs/atgs-selfcap-integration-20260906 --max-steps 3
```

Every training attempt, including failed startup and integration runs, charges
the central ATGS/SelfCap ledger under the two-hour limit. `--max-steps` pauses at
a completed microstep without changing the full native schedule or flushing a
partial encoder batch. `--resume` accepts a committed bundle and requires matching
configuration/provenance. Choose a new output directory for every attempt.

The trainer preserves native no-growth defaults and refuses a configuration
that would activate unvalidated production densification. Initial midpoint
geometry gets ATGS's always-active frame-zero lifetime marker; that marker does
not assert reconstruction at frame zero. Input image hashes, manifest identity
and the exact training-camera set are checked. Patched Python source and adapter
hashes enter configuration provenance; native binary/dependency provenance and
device-wide GPU sampling still need integration before benchmark-quality runs.

Checkpoint and step reserves default to conservative 120/30 seconds, in addition
to the external supervisor's 30-second shutdown margin. Actual checkpoint times
are recorded. These defaults need validation against measured scene-run costs.
The parent stays free of Torch imports before launching the supervised worker.

### ATGS offline scene rendering

```bash
.local/envs/atgs/bin/python scripts/render-atgs-manifest.py --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --checkpoint .local/runs/atgs-selfcap-resumed-20260906/checkpoint-000006-000 --training-config .local/runs/atgs-selfcap-resumed-20260906/training-config.json --provenance .local/runs/atgs-selfcap-resumed-20260906/provenance.json --output .local/runs/atgs-selfcap-render-a-20260906 --benchmark
```

Choose unused output paths. This installs the network guard before Torch import,
verifies bundle/configuration/manifest and patched Python source hashes, and
restores the complete inference model without the original initialization cloud.
All 60 held-out frames and 20 shared sweep poses are saved with PNG and raw-float
hashes. Optional benchmarking uses ten warmups and 100 synchronized timed renders,
excluding validation, saving, encoding and camera setup. Repeat in a new process
and compare all PNGs with `compare-render-reloads.py`; raw-float hashes are in
`render.json`. The existing evaluator and evidence packager accept these outputs.

Rendering reports also fingerprint the installed rasterizer, KNN, tiny-cuda-nn
and scatter shared objects, selected package versions and renderer source bytes.
These describe the current rendering runtime, not a retroactive attestation of
the training environment or every dynamically linked system library. Missing
extension files are rejected. Use absolute interpreter paths with Codex rules
that name absolute paths, including for `measure-experiment.py`: its spawned
GPU sampler inherits the measurement process's sandbox/host access.

For a complete sequential ATGS evaluation, run the following with the STG
environment (shared CPU metrics/video tools). The driver uses the ATGS
interpreter for both GPU reloads and requires already-cached AlexNet weights:

```bash
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-render/bin/python scripts/evaluate-atgs-checkpoint.py --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json --checkpoint .local/runs/atgs-selfcap-5000-20260906/checkpoint-005000-004 --training-config .local/runs/atgs-selfcap-5000-20260906/training-config.json --provenance .local/runs/atgs-selfcap-5000-20260906/provenance.json --crops configs/detail-crops.selfcap-dance1.json --torch-cache .local/cache/torch --output .local/runs/atgs-selfcap-5000-evaluation-20260906
```

Check the actual final bundle path in the training run's `checkpoints.json`
before execution; the command above assumes saves at 2,000/3,000/4,000/5,000
plus the final pause snapshot. Output must be new. The driver stops on the first
failure and retains exact commands and per-stage logs. It checks all 80 raw-float
and PNG hashes, bundle/runtime identity, then runs the shared evaluator and fixed
crop/video packager. The completed `evaluation.json` is written only after every
stage succeeds. `compare-stg-evaluations.py` also accepts this ATGS evaluation
format alongside STG results, preserving the bundle inventory instead of
inventing a single checkpoint-file hash. Equal steps are not equal training time.
