# Experience pretrained 4DGS before training

[Repository overview](../README.md) · [Research](research.md) · [Input data](input-data.md) · [Rendering](rendering.md) · [Later training](local-creation.md)

Target: Ubuntu 24.04, RTX 4090. Procedure review: 2026-09-05. This guide supplies commands to execute locally; it does not report completed GPU experiments or a tested dependency lockfile. The first two experiments need a browser, not a CUDA research environment.

The question is whether the quality you can actually see justifies training and integration work. Stop after any stage to record your assessment. No command in this guide trains a model.

| Step | What you experience | What it establishes |
| --- | --- | --- |
| 1 | Bundled splaTV scene with time controls | Interactive playback works locally |
| 2 | Released STG lite `sear_steak` scene | A downloaded dynamic checkpoint can be explored |
| 3 | The same STG checkpoint in its original renderer | Original appearance versus browser conversion |
| 4 | Mango-GS `sear_steak` checkpoint | A second method on similar scene content |
| 5 | NoPo4D on bundled multi-view images | Pretrained reconstruction followed by rendering |
| 6 | Written comparison | Which training or rendering experiment is worth doing next |

## 0. Prepare the repository workspace

Run the blocks in order in Bash, stopping on an error before continuing. Use a separate terminal for long-running servers. Keep the root variables available in each terminal: run this block from the repository root again when opening a new one.

```bash
GS_ROOT="$(git rev-parse --show-toplevel)"
export GS_ROOT
export GS_WORK="$GS_ROOT/.local"
mkdir -p "$GS_WORK"/{envs,tools,cache,downloads,data,weights,runs}
export HF_HOME="$GS_WORK/cache/huggingface"
export TORCH_HOME="$GS_WORK/cache/torch"
export PIP_CACHE_DIR="$GS_WORK/cache/pip"
export UV_CACHE_DIR="$GS_WORK/cache/uv"
export XDG_CACHE_HOME="$GS_WORK/cache/xdg"
mkdir -p "$HF_HOME" "$TORCH_HOME" "$PIP_CACHE_DIR" "$UV_CACHE_DIR" "$XDG_CACHE_HOME"
git check-ignore .local/weights/example.ply .local/envs/example .local/runs/example.mp4
df -h "$GS_ROOT"
```

The root `.gitignore` excludes all of `.local/`. Keep our code, patches, environment specifications, and small reports tracked elsewhere. The intended layout is:

```text
.local/
  splaTV/ SpacetimeGaussians/ Mango-GS/ NoPo4D/  # independent upstream checkouts
  envs/ tools/ cache/                         # installed environments and compilers
  downloads/ data/ weights/ runs/             # originals, prepared data, outputs
patches/                                     # reproducible upstream modifications
scripts/                                     # our experiment helpers
docs/experiments/                            # small findings and provenance records
```

About 591 GB was available at planning time. Check `df -h` again before downloads and frame extraction; decoded multi-camera images can greatly exceed compressed video size. Keep original data separate from each method's preprocessing output. Use a new run directory for a repeated experiment.

### Host and GPU checks

```bash
/usr/bin/python3.14 --version
git --version
curl --version
unzip -v
ffmpeg -version
nvidia-smi --query-gpu=name,memory.total,memory.used,driver_version --format=csv
/usr/local/cuda-13.0/bin/nvcc --version
gcc --version
g++ --version
```

The workstation's `.bashrc` appends `/usr/local/cuda-13.0/bin` to PATH. A noninteractive shell may not read that file; the explicit path works independently of shell startup. Appending a path also does not override an earlier `nvcc`. Run `command -v nvcc` whenever selecting a research environment.

A sandbox can block NVIDIA devices even when the host works. Run these checks from an authorized host terminal before diagnosing a driver problem. A successful compiler version query does not establish GPU access. The CUDA version shown by `nvidia-smi` describes driver capability, not the installed toolkit. [NVIDIA compatibility documentation](https://docs.nvidia.com/deploy/cuda-compatibility/)

### Local environment manager — needed starting at step 3

Use the [shared environment guide](environments.md): existing uv and standard Python 3.14, Torch 2.13.0+cu130 / torchvision 0.28.0+cu130, and the system CUDA 13.0 toolkit. No environment installation is needed for steps 1–2. Follow that guide's workspace exports, per-method setup, compatibility gates, and GPU checks before native rendering. Do not run upstream setup scripts or silently downgrade dependencies.

## 1. View the bundled scene

### Download the viewer and apply the local patch

```bash
git clone https://github.com/antimatter15/splaTV.git "$GS_WORK/splaTV"
git -C "$GS_WORK/splaTV" checkout --detach 8b313fe
git -C "$GS_WORK/splaTV" rev-parse HEAD
test -s "$GS_WORK/splaTV/model.splatv"
git -C "$GS_WORK/splaTV" apply --check "$GS_ROOT/patches/splatv-time-controls.patch"
test ! -e "$GS_WORK/splaTV/time-controls.js"
cp -n "$GS_ROOT/patches/splatv/time-controls.js" "$GS_WORK/splaTV/time-controls.js"
git -C "$GS_WORK/splaTV" apply "$GS_ROOT/patches/splatv-time-controls.patch"
sha256sum "$GS_WORK/splaTV/model.splatv"
```

The bundled `.splatv` is an existing scene, not reconstruction weights. If a checkout already exists, inspect its revision and changes rather than cloning or applying the patch again. A failed patch check is a stop point; see [patch maintenance](../patches/README.md). If the model is only a Git LFS pointer, install Git LFS and run `git lfs pull` in that checkout before viewing. [Upstream viewer](https://github.com/antimatter15/splaTV)

### Start the local server

```bash
/usr/bin/python3.14 -m http.server 8000 --bind 127.0.0.1 --directory "$GS_WORK/splaTV"
```

Open [the local viewer](http://127.0.0.1:8000/) in a desktop browser. Keep the terminal running; Ctrl-C stops the server. If the port is occupied, use 8001 and adjust all URLs. Check the browser's graphics diagnostic page (`about:support` in Firefox, `chrome://gpu` in Chromium) for hardware-accelerated WebGL2.

The patch starts paused at time zero. Press Play, pause midway, move the camera while paused, and scrub to 0, 0.5, and 1. Restart resets to zero and pauses. The default five-second cycle is an inspection speed, not a claim about source capture timing. Scrubbing pauses; Play resumes from the chosen value. Switching tabs pauses playback. Mouse dragging orbits and arrow keys translate; interacting with timeline inputs must not move the camera.

**Pass:** the scene is visible, motion changes with time, and camera motion remains independent while paused. Record the browser/GPU backend, viewport, displayed frame rate, and visual artifacts. After the first successful load, disable external network access while retaining loopback, disable browser cache in developer tools, and reload. Model and script requests should stay on `127.0.0.1`.

## 2. Inspect the released STG lite scene

### Download one checkpoint

Use the author's `n3d_sear_steak_lite_allcam.zip` (about 16.1 MB), not the Windows viewer archives. This scene used all cameras during training. [Published assets](https://huggingface.co/stack93/spacetimegaussians/tree/main), [author's viewer/model description](https://github.com/oppo-us-research/SpacetimeGaussians#real-time-viewer)

```bash
mkdir -p "$GS_WORK/downloads/stg"
curl -fL --retry 3 \
  https://huggingface.co/stack93/spacetimegaussians/resolve/main/n3d_sear_steak_lite_allcam.zip \
  -o "$GS_WORK/downloads/stg/n3d_sear_steak_lite_allcam.zip"
sha256sum "$GS_WORK/downloads/stg/n3d_sear_steak_lite_allcam.zip"
unzip -l "$GS_WORK/downloads/stg/n3d_sear_steak_lite_allcam.zip"
unzip -t "$GS_WORK/downloads/stg/n3d_sear_steak_lite_allcam.zip"
mkdir "$GS_WORK/weights/stg-sear-steak"
unzip -n "$GS_WORK/downloads/stg/n3d_sear_steak_lite_allcam.zip" -d "$GS_WORK/weights/stg-sear-steak"
```

Record the model repository revision displayed on the download page and the archive SHA-256. For a repeat run, replace `main` in the URL with that recorded revision. List the actual files; do not assume the archive has no enclosing directory:

```bash
find "$GS_WORK/weights/stg-sear-steak" -type f \
  \( -name cfg_args -o -name cameras.json -o -name '*.ply' \) -print
```

Expect a complete run with `cfg_args`, `cameras.json`, and `point_cloud/iteration_<number>/point_cloud.ply`. If these are missing, stop the original-renderer route and record what the release actually contains. A PLY must include STG motion and temporal attributes; its extension alone does not establish compatibility.

### Explore and retain the conversion

1. With the local viewer open, drag the checkpoint's `cameras.json` onto it, then the Gaussian PLY. Import one file at a time.
2. Save the generated browser download as `.local/splaTV/sear-steak-lite.splatv`. Choose that destination explicitly in the browser so generated assets stay in the repository.
3. Reload using [the explicit local scene URL](http://127.0.0.1:8000/?url=http://127.0.0.1:8000/sear-steak-lite.splatv). The absolute URL matters: upstream resolves relative scene URL parameters against a remote base.
4. Pause and inspect early, middle, and late states; move sideways to expose occluded surfaces and look for floaters, edge duplication, changing opacity, and unstable backgrounds.

The upstream camera-JSON drop handler does not fully refresh its active camera/intrinsics. Reopening the converted `.splatv` and selecting a camera forces the model's embedded cameras through the normal load path; use that view for inspection. Verify alignment before attributing differences to model quality. The timeline patch does not change camera import or Gaussian conversion. [Camera import and conversion source](https://raw.githubusercontent.com/antimatter15/splaTV/main/hybrid.js)

**Pass:** reopening the local conversion reproduces an animated scene and its camera views. This is a browser preview; quantify conversion losses only after obtaining the original reference in step 3. Retain both artifacts and their byte sizes.

## 3. Render the STG checkpoint with its original renderer

### Create the reference checkout and resolve the downloaded run

```bash
git clone https://github.com/oppo-us-research/SpacetimeGaussians.git "$GS_WORK/SpacetimeGaussians"
git -C "$GS_WORK/SpacetimeGaussians" checkout --detach 427abfc
git -C "$GS_WORK/SpacetimeGaussians" submodule update --init --recursive
git -C "$GS_WORK/SpacetimeGaussians" rev-parse HEAD
git -C "$GS_WORK/SpacetimeGaussians" submodule status --recursive
/usr/bin/python3.14 "$GS_ROOT/scripts/resolve-stg-checkpoint.py" "$GS_WORK/weights/stg-sear-steak" \
  --profile "$GS_WORK/SpacetimeGaussians/configs/n3d_lite/sear_steak.json" \
  > "$GS_WORK/runs/stg-selection.sh"
```

Proceed only if the resolver exits successfully. It parses literal saved settings without executing `cfg_args`, selects the highest saved PLY iteration, verifies temporal fields, and resolves camera paths, window offset, duration, and resolution. Saved duration/resolution take precedence over profile defaults; `resolution=-1` retains upstream automatic sizing. If duration exists only in the profile, treat that window as a reference-profile assumption and confirm it against the checkpoint's release metadata before making time-matched comparisons. Missing or ambiguous paths/settings produce an explicit error.

```bash
source "$GS_WORK/runs/stg-selection.sh"
printf '%s\n' "$STG_MODEL" "$STG_PLY" "$STG_CAMERAS" \
  "iteration=$STG_ITERATION start=$STG_START end=$STG_END duration=$STG_DURATION resolution=$STG_RESOLUTION"
```

### Prepare the modern environment and port the renderer

Complete sections 1–3 of the [environment guide](environments.md) with `GS_ENV=stg-render`. The [STG candidate specification](../environments/stg-render.in) does not yet port bundled MMCV or its CUDA extensions. This stage is **adaptation pending**, not a working legacy environment reproduced with new version numbers. Audit configuration, SSIM/science APIs, checkpoint loading, and Torch/CUDA extension APIs before the conditional builds below. [Upstream setup provenance](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/script/setup.sh)

After recording and applying the necessary source patches:

```bash
cd "$GS_WORK/SpacetimeGaussians"
uv pip install --python "$GS_WORK/envs/stg-render/bin/python" --torch-backend cu130 \
  --constraint "$GS_ROOT/environments/constraints-cu130.txt" --no-build-isolation \
  thirdparty/gaussian_splatting/submodules/gaussian_rasterization_ch9 \
  thirdparty/gaussian_splatting/submodules/gaussian_rasterization_ch3 \
  thirdparty/gaussian_splatting/submodules/forward_full \
  thirdparty/gaussian_splatting/submodules/forward_lite \
  thirdparty/gaussian_splatting/submodules/simple-knn
uv pip install --python "$GS_WORK/envs/stg-render/bin/python" --torch-backend cu130 \
  --constraint "$GS_ROOT/environments/constraints-cu130.txt" --no-build-isolation -e thirdparty/mmcv
uv pip check --python "$GS_WORK/envs/stg-render/bin/python"
"$GS_WORK/envs/stg-render/bin/python" test.py --help
```

The MMCV command assumes the bundled implementation has been ported; if choosing a replacement config adapter, update the dependency spec and callers instead. Complete the shared GPU preflight and an actual extension rasterization before dataset preprocessing or checkpoint rendering. Stop on failures; the browser route remains useful.

### Obtain and prepare the matching capture

The original renderer uses dataset metadata and images even when loading an existing model. Download only the `sear_steak` asset from the official Neural 3D release; retain its original videos and calibration. [Dataset release](https://github.com/facebookresearch/Neural_3D_Video/releases/tag/v1.0)

```bash
curl -fL --retry 3 \
  https://github.com/facebookresearch/Neural_3D_Video/releases/download/v1.0/sear_steak.zip \
  -o "$GS_WORK/downloads/sear_steak.zip"
sha256sum "$GS_WORK/downloads/sear_steak.zip"
unzip -l "$GS_WORK/downloads/sear_steak.zip"
mkdir -p "$GS_WORK/data/n3v-original"
unzip -n "$GS_WORK/downloads/sear_steak.zip" -d "$GS_WORK/data/n3v-original"
test -f "$GS_WORK/data/n3v-original/sear_steak/poses_bounds.npy"
test -f "$GS_WORK/data/n3v-original/sear_steak/cam00.mp4"
ffprobe -v error -select_streams v:0 -show_entries stream=width,height,r_frame_rate,nb_frames \
  -of default=noprint_wrappers=1 "$GS_WORK/data/n3v-original/sear_steak/cam00.mp4"
mkdir -p "$GS_WORK/data/stg"
cp -a -n "$GS_WORK/data/n3v-original/sear_steak" "$GS_WORK/data/stg/"
```

If the archive layout differs, inspect it and put its scene directory at the stated path before proceeding. Do not treat camera-number gaps as missing observations: the release excludes invalid cameras, and poses follow sorted retained video order. [Dataset conventions](https://github.com/facebookresearch/Neural_3D_Video)

Create `GS_ENV=stg-colmap` using the shared guide and its [candidate dependencies](../environments/stg-colmap.in). Validate the system COLMAP CLI against this checkout first. This uses existing calibration rather than estimating new camera poses:

```bash
command -v colmap
colmap -h
cd "$GS_WORK/SpacetimeGaussians"
"$GS_WORK/envs/stg-colmap/bin/python" script/pre_n3d.py --help
"$GS_WORK/envs/stg-colmap/bin/python" script/pre_n3d.py --videopath "$GS_WORK/data/stg/sear_steak" \
  --startframe "$STG_START" --endframe "$STG_END"
```

Verify that this checkout's help exposes `--startframe` and `--endframe` before the second command. Stop and record a source mismatch if it does not. These options limit COLMAP work; the inspected implementation still decodes 300 frames per camera. It creates/removes intermediate directories, which is why the working copy is separate. Preserve the input capture scale and use `--downscale 1` if selecting that option explicitly. [Preprocessing source](https://github.com/oppo-us-research/SpacetimeGaussians/blob/main/script/pre_n3d.py)

### Render and compare

Copy the model run so upstream render outputs do not modify the original downloaded bundle. Match the checkpoint duration/resolution in both the copied JSON and explicit arguments to avoid upstream default-equality precedence surprises:

```bash
cp -a -n "$STG_MODEL" "$GS_WORK/runs/stg-sear-steak-reference"
/usr/bin/python3.14 - "$GS_WORK/SpacetimeGaussians/configs/n3d_lite/sear_steak.json" \
  "$GS_WORK/runs/stg-sear-steak-render.json" <<'PY'
import json, os, sys
from pathlib import Path
config = json.loads(Path(sys.argv[1]).read_text())
config.update(duration=int(os.environ['STG_DURATION']),
              resolution=int(os.environ['STG_RESOLUTION']),
              test_iteration=int(os.environ['STG_ITERATION']))
with open(sys.argv[2], 'x') as output:
    json.dump(config, output, indent=2)
PY
export CUDA_HOME=/usr/local/cuda-13.0
export PATH="$CUDA_HOME/bin:$PATH"
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions/stg-render-py314-torch213-cu130"
cd "$GS_WORK/SpacetimeGaussians"
"$GS_WORK/envs/stg-render/bin/python" test.py \
  --source_path "$GS_WORK/data/stg/sear_steak/colmap_$STG_START" \
  --model_path "$GS_WORK/runs/stg-sear-steak-reference" \
  --configpath "$GS_WORK/runs/stg-sear-steak-render.json" \
  --eval --skip_train --valloader colmapvalid \
  --duration "$STG_DURATION" --resolution "$STG_RESOLUTION" --test_iteration "$STG_ITERATION"
```

Inspect `test/ours_<iteration>/renders` inside the copied model directory. Keep the PNGs and ground-truth counterparts. The test entry point may also calculate metrics, so its entire wall time is not pure rasterizer throughput. [Testing implementation](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/test.py)

At window-relative frame `i`, STG time is `i / duration`; the final observed frame is `(duration - 1) / duration`, not 1. Set browser time accordingly. Use the corresponding camera, identical pixel dimensions/intrinsics, background, and pose. Browser viewport scaling and quantized color/opacity can alter appearance. Without a verified camera match, report a qualitative inspection rather than a pixel-level conversion comparison.

For a single time-ordered camera sequence, encode a separate video after confirming frame order. `-framerate 30` is an example; replace it with the recorded source frame rate:

```bash
ffmpeg -n -framerate 30 \
  -i "$GS_WORK/runs/stg-sear-steak-reference/test/ours_$STG_ITERATION/renders/%05d.png" \
  -vf 'pad=ceil(iw/2)*2:ceil(ih/2)*2' -c:v libx264 -pix_fmt yuv420p \
  "$GS_WORK/runs/stg-sear-steak-reference/preview.mp4"
```

**Pass:** a fresh Python process loads the downloaded checkpoint, renders multiple times, and produces a useful original-renderer reference. This all-camera checkpoint cannot establish held-out quality, even if the loader or output directory calls a split `test`.

## 4. Render the Mango-GS checkpoint

### Install a separate environment

The upstream setup is historical provenance, not the target stack. Clone and record the source, then use the shared guide with `GS_ENV=mango-render`. [Mango-GS setup](https://github.com/htx0601/Mango-GS#installation), [requirements](https://github.com/htx0601/Mango-GS/blob/main/requirements.txt)

```bash
git clone --recursive https://github.com/htx0601/Mango-GS.git "$GS_WORK/Mango-GS"
git -C "$GS_WORK/Mango-GS" checkout --detach
git -C "$GS_WORK/Mango-GS" rev-parse HEAD
git -C "$GS_WORK/Mango-GS" submodule status --recursive
```

**Adaptation pending:** resolve the [candidate dependencies](../environments/mango-render.in), audit all upstream imports, and select a full PyTorch3D revision compatible with the fixed stack. Clone that dependency under `.local/`, record its revision, and build it with the same interpreter, constraint and toolkit. Do not install upstream's moving Git URL as a reproducible pin. Keep successful patches and build logs before the conditional local builds:

```bash
cd "$GS_WORK/Mango-GS"
uv pip install --python "$GS_WORK/envs/mango-render/bin/python" --torch-backend cu130 \
  --constraint "$GS_ROOT/environments/constraints-cu130.txt" --no-build-isolation \
  -e submodules/diff-gaussian-rasterization -e submodules/simple-knn
uv pip check --python "$GS_WORK/envs/mango-render/bin/python"
"$GS_WORK/envs/mango-render/bin/python" render.py --help
```

Complete the shared base/extension checks before rendering. For repeat runs, check out recorded full commits and update submodules; record the PyTorch3D commit independently.

### Download the scene and prepare input frames

Use an independent Python 3.14 download environment without Torch:

```bash
uv venv --python /usr/bin/python3.14 "$GS_WORK/envs/downloads"
uv pip install --python "$GS_WORK/envs/downloads/bin/python" -r "$GS_ROOT/environments/downloads.in"
"$GS_WORK/envs/downloads/bin/hf" download htx0601/Mango-GS \
  --include 'n3v/sear_steak_mango_node/*' --local-dir "$GS_WORK/weights/mango"
test -s "$GS_WORK/weights/mango/n3v/sear_steak_mango_node/cfg_args"
test -s "$GS_WORK/weights/mango/n3v/sear_steak_mango_node/point_cloud.ply"
test -s "$GS_WORK/weights/mango/n3v/sear_steak_mango_node/deform.pth"
sha256sum "$GS_WORK/weights/mango/n3v/sear_steak_mango_node/"{cfg_args,point_cloud.ply,deform.pth}
```

Record the model revision; pass `--revision <recorded full revision>` on subsequent downloads. Keep all three files: the PLY alone omits deformation state. [Released N3V scene bundles](https://huggingface.co/htx0601/Mango-GS/tree/main/n3v)

Prepare a Mango-specific copy with full-resolution, time-ordered images. Retain gaps in source camera numbering:

```bash
mkdir -p "$GS_WORK/data/mango/sear_steak"
cp -n "$GS_WORK/data/n3v-original/sear_steak/poses_bounds.npy" "$GS_WORK/data/mango/sear_steak/"
for video in "$GS_WORK/data/n3v-original/sear_steak"/cam*.mp4; do
  camera="$(basename "$video" .mp4)"
  mkdir -p "$GS_WORK/data/mango/sear_steak/$camera/images"
  ffmpeg -n -i "$video" -vsync 0 -start_number 0 \
    "$GS_WORK/data/mango/sear_steak/$camera/images/%05d.png"
done
```

Do not crop, rescale, or renumber the cameras before checking the loader. The expected layout is `poses_bounds.npy` plus `camXX/images/`. Its saved configuration and release profile determine the modeled frame range; do not assume it equals STG's window. [Mango input/profile conventions](https://github.com/htx0601/Mango-GS#data-preparation)

### Render one preview, then a sequence

```bash
mkdir -p "$GS_WORK/runs/mango/n3v" "$GS_WORK/runs/mango/previews"
cp -a -n "$GS_WORK/weights/mango/n3v/sear_steak_mango_node" "$GS_WORK/runs/mango/n3v/"
export CUDA_HOME=/usr/local/cuda-13.0
export PATH="$CUDA_HOME/bin:$PATH"
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions/mango-render-py314-torch213-cu130"
cd "$GS_WORK/Mango-GS"
PATH="$GS_WORK/envs/mango-render/bin:$PATH" PYTHON="$GS_WORK/envs/mango-render/bin/python" bash scripts/render_one_frame.sh n3v sear_steak \
  "$GS_WORK/data/mango/sear_steak" "$GS_WORK/runs/mango/n3v/sear_steak" \
  0 "$GS_WORK/runs/mango/previews/sear-steak.png"
PATH="$GS_WORK/envs/mango-render/bin:$PATH" PYTHON="$GS_WORK/envs/mango-render/bin/python" bash scripts/render_scene.sh n3v sear_steak \
  "$GS_WORK/data/mango/sear_steak" "$GS_WORK/runs/mango/n3v/sear_steak" 0 30
```

The scripts resolve the base model path to its `_mango_node` directory. The last sequence argument is encoded video FPS, not GPU throughput. Inspect the preview before running the longer sequence. Expected outputs are beneath the resolved model's `test/video_<checkpoint>/`; inspect the command log and resulting tree for the actual checkpoint identifier. [Published render commands](https://github.com/htx0601/Mango-GS#render-and-validate-n3v)

**Pass:** the original renderer reloads the complete downloaded model and produces a preview plus changing temporal states. Compare PNGs at overlapping physical times and matching camera views with STG. Record unmatched training splits, durations, resolutions, and backgrounds instead of presenting an uncontrolled leaderboard.

## 5. Try NoPo4D reconstruction inference

This stage predicts a dynamic representation from example images using reusable weights. It is different from loading a scene already optimized for `sear_steak`. The bundled example supplies four fixed cameras and four frames in camera-major filename order. [NoPo4D quick start](https://github.com/bralani/NoPo4D#quick-start)

### Install the model and backbone

Clone and record the model and backbone sources:

```bash
git clone --recurse-submodules https://github.com/bralani/NoPo4D.git "$GS_WORK/NoPo4D"
git -C "$GS_WORK/NoPo4D" checkout --detach
git -C "$GS_WORK/NoPo4D" rev-parse HEAD
git -C "$GS_WORK/NoPo4D" submodule status --recursive
```

Use the shared guide with `GS_ENV=nopo4d`. The [candidate specification](../environments/nopo4d.in) probes xFormers and gsplat under fixed Torch/cu130 constraints; it does not contain the entire model/backbone dependency graph. **Adaptation pending:** audit upstream NumPy restrictions and compiled dependencies for Python 3.14. Resolve the full metadata, recording necessary source/metadata patches; never bypass conflicts with overrides or dependency suppression. [Model dependencies](https://github.com/bralani/NoPo4D/blob/main/pyproject.toml), [backbone dependencies](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/main/pyproject.toml)

After that audit, install both projects together under the fixed constraint:

```bash
cd "$GS_WORK/NoPo4D"
uv pip install --python "$GS_WORK/envs/nopo4d/bin/python" --torch-backend cu130 \
  --constraint "$GS_ROOT/environments/constraints-cu130.txt" \
  -e . -e src/model/encoder/backbone/Depth-Anything-3
uv pip check --python "$GS_WORK/envs/nopo4d/bin/python"
"$GS_WORK/envs/nopo4d/bin/python" -c 'import torch, xformers, gsplat; print(torch.__version__, xformers.__version__, gsplat.__version__)'
"$GS_WORK/envs/nopo4d/bin/python" src/inference.py --help
```

Repeat the shared base assertions and actual extension/kernel checks after installation. Optional `torch-scatter` voxelization is omitted for this first run. Backbone/model downloads use workspace caches; account for both their weights and the main checkpoint.

### Run the bundled example

Inspect the 16 example files before inference. Their camera-major ordering is part of the input, not an incidental filename convention:

```bash
cd "$GS_WORK/NoPo4D"
find assets/examples -maxdepth 1 -type f -name '*.png' -print | sort
"$GS_WORK/envs/nopo4d/bin/python" src/inference.py \
  --image_dir assets/examples --num_cameras 4 \
  --output_dir "$GS_WORK/runs/nopo4d-example" --render_timestamps 10
```

Expected output: `images/view_0000.png` through `view_0039.png`, ten timestamps for each of four predicted cameras. Optical-flow visualizations go under `optical_flow/` when produced. The source uses the first predicted pose of each camera repeatedly; this is input-camera replay, not a novel-view or held-out evaluation. [Inference implementation](https://raw.githubusercontent.com/bralani/NoPo4D/main/src/inference.py)

If rendering runs out of memory, retry into a fresh directory with `--render_timestamps 3`. This reduces rendered outputs, not the 16-image encoder input or backbone weight memory. An encoder OOM requires a separate input-resolution/view-count adaptation; do not drop arbitrary files and keep `--num_cameras 4` unchanged.

Encode each camera independently so the result does not jump between cameras. Ten frames at ten FPS below is a one-second inspection clip; its duration is not recovered source timing:

```bash
for camera in 0 1 2 3; do
  ffmpeg -n -framerate 10 -start_number "$((camera * 10))" \
    -i "$GS_WORK/runs/nopo4d-example/images/view_%04d.png" -frames:v 10 \
    -vf 'pad=ceil(iw/2)*2:ceil(ih/2)*2' -c:v libx264 -pix_fmt yuv420p \
    "$GS_WORK/runs/nopo4d-example/camera-$camera.mp4"
done
```

**Pass:** the encoder and renderer complete, all four camera sequences show temporal states, and their geometry/motion can be inspected against the input. Custom novel-view paths through `model.render(...)` and persistent external-viewer exports are later integrations; the stock command does not save a portable splaTV model. Record the downloaded model/backbone revisions from the local Hugging Face cache metadata before reproducing the run offline.

## 6. Record the evidence and choose the next experiment

Create a separate report per method/scene from the [experiment template](experiments/template.md). Keep large evidence in `.local/runs/` and reference its relative paths in the report:

```bash
cp -n "$GS_ROOT/docs/experiments/template.md" "$GS_ROOT/docs/experiments/001-splatv.md"
```

Record setup effort, model completeness, visual artifacts, viewpoint range, and repeatability before pursuing training. Useful inventories, run in the relevant upstream checkout; set `GS_ENV` to the method name from the shared guide:

```bash
git rev-parse HEAD
git submodule status --recursive
uv --version
uv pip freeze --python "$GS_WORK/envs/$GS_ENV/bin/python"
du -sh "$GS_WORK/data" "$GS_WORK/weights" "$GS_WORK/envs" "$GS_WORK/cache" "$GS_WORK/runs"
```

Save inventories into the run's log directory; copy small resolved specifications into the tracked report when useful. For GPU memory, run a sampler in a second authorized terminal for the entire experiment:

```bash
nvidia-smi --query-gpu=timestamp,memory.used,utilization.gpu --format=csv -lms 200 \
  > "$GS_WORK/runs/gpu-samples.csv"
```

Stop with Ctrl-C after the run; choose a new filename per experiment. This samples device-wide usage, including the desktop/browser, and can miss brief peaks. Measure a baseline before starting and document sampling boundaries. Framework peak allocated memory is a different measure. Do not label a single `nvidia-smi` snapshot as peak VRAM.

Use the same visual checklist for each method: fixed-camera animation, start/middle/end detail, temporal flicker, edges and transparency, newly exposed surfaces, and background stability. For splaTV also inspect a frozen-time orbit; for stock native scripts record if their camera path cannot be freely controlled. Compare original and exported representations separately.

Choose one conclusion per experiment: **investigate training**, **investigate rendering further**, or **defer**, with the observed reason. Browser FPS, warm CUDA rendering speed, end-to-end reconstruction time, and video playback rate answer different questions. A useful outcome can be deciding that an available viewer or representation does not fit your needs.

Once a method earns further effort, proceed to [input preparation](input-data.md) and the [later training experiments](local-creation.md). HUST `bouncingballs` remains a compact synthetic training option; it is not required for any step above.
