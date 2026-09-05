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
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions"
export PIP_CACHE_DIR="$GS_WORK/cache/pip"
export CONDA_PKGS_DIRS="$GS_WORK/cache/conda/pkgs"
export XDG_CACHE_HOME="$GS_WORK/cache/xdg"
mkdir -p "$HF_HOME" "$TORCH_HOME" "$TORCH_EXTENSIONS_DIR" "$PIP_CACHE_DIR" "$CONDA_PKGS_DIRS" "$XDG_CACHE_HOME"
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
python3 --version
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

Skip this installation until reaching the CUDA experiments. Miniforge supports a noninteractive prefix installation. These commands install beneath `.local/tools` and activate only the current shell. [Miniforge installation](https://github.com/conda-forge/miniforge#install)

```bash
curl -fL --retry 3 \
  https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh \
  -o "$GS_WORK/downloads/Miniforge3-Linux-x86_64.sh"
sha256sum "$GS_WORK/downloads/Miniforge3-Linux-x86_64.sh"
bash "$GS_WORK/downloads/Miniforge3-Linux-x86_64.sh" -b -p "$GS_WORK/tools/miniforge"
source "$GS_WORK/tools/miniforge/etc/profile.d/conda.sh"
conda --version
```

Record the installer hash and release used. If that prefix already exists, source its `conda.sh` instead of reinstalling. Do not run `conda init` or alter global channels. The guide uses `--override-channels` to keep channel choices explicit. Each new shell needs the workspace exports and `source` command again.

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
python3 -m http.server 8000 --bind 127.0.0.1 --directory "$GS_WORK/splaTV"
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
python3 "$GS_ROOT/scripts/resolve-stg-checkpoint.py" "$GS_WORK/weights/stg-sear-steak" \
  --profile "$GS_WORK/SpacetimeGaussians/configs/n3d_lite/sear_steak.json" \
  > "$GS_WORK/runs/stg-selection.sh"
```

Proceed only if the resolver exits successfully. It parses literal saved settings without executing `cfg_args`, selects the highest saved PLY iteration, verifies temporal fields, and resolves camera paths, window offset, duration, and resolution. Saved duration/resolution take precedence over profile defaults; `resolution=-1` retains upstream automatic sizing. If duration exists only in the profile, treat that window as a reference-profile assumption and confirm it against the checkpoint's release metadata before making time-matched comparisons. Missing or ambiguous paths/settings produce an explicit error.

```bash
source "$GS_WORK/runs/stg-selection.sh"
printf '%s\n' "$STG_MODEL" "$STG_PLY" "$STG_CAMERAS" \
  "iteration=$STG_ITERATION start=$STG_START end=$STG_END duration=$STG_DURATION resolution=$STG_RESOLUTION"
```

### Install the legacy environment and compiler

Run the local Miniforge setup from step 0 if needed. The baseline follows upstream Python 3.7.13 / PyTorch 1.12.1 / CUDA 11.6. Its original tested host was Ubuntu 20.04. The prefix compiler installation below is a proposed Ubuntu 24.04 adaptation, not an already validated environment. [STG setup](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/script/setup.sh)

```bash
conda create -y -p "$GS_WORK/envs/stg-render" --override-channels -c conda-forge \
  python=3.7.13 pip gcc_linux-64=10 gxx_linux-64=10 ninja
conda create -y -p "$GS_WORK/tools/cuda-11.6" --override-channels \
  -c nvidia/label/cuda-11.6.2 -c conda-forge cuda-toolkit
conda activate "$GS_WORK/envs/stg-render"
export CUDA_HOME="$GS_WORK/tools/cuda-11.6"
export PATH="$CUDA_HOME/bin:$PATH"
export CC="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-cc"
export CXX="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"
export CUDAHOSTCXX="$CXX"
export TORCH_CUDA_ARCH_LIST="8.6+PTX"
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions/stg"
nvcc --version
"$CXX" --version
python -m pip install torch==1.12.1+cu116 torchvision==0.13.1+cu116 torchaudio==0.12.1 \
  --extra-index-url https://download.pytorch.org/whl/cu116
python -m pip install 'numpy==1.21.6' 'scipy==1.7.3' 'scikit-image==0.19.3' \
  'opencv-python==4.8.1.78' 'Pillow==9.5.0' 'plyfile==0.7.4' \
  'kornia==0.6.12' natsort tqdm 'yapf==0.40.1'
cd "$GS_WORK/SpacetimeGaussians"
python -m pip install --no-build-isolation \
  thirdparty/gaussian_splatting/submodules/gaussian_rasterization_ch9 \
  thirdparty/gaussian_splatting/submodules/gaussian_rasterization_ch3 \
  thirdparty/gaussian_splatting/submodules/forward_full \
  thirdparty/gaussian_splatting/submodules/forward_lite \
  thirdparty/gaussian_splatting/submodules/simple-knn
python -m pip install --no-build-isolation -e thirdparty/mmcv
python -m pip check
python test.py --help
```

The Python-library pins are compatibility starting points for the old interpreter and SSIM API. Record solver/build failures and the resolved package inventory. CUDA 11.6 cannot compile `sm_89`; `8.6+PTX` is the proposed Ada compatibility setting. Keep this environment separate from newer experiments. [PyTorch historical wheels](https://pytorch.org/get-started/previous-versions/), [Ada compiler compatibility](https://docs.nvidia.com/cuda/ada-compatibility-guide/), [CUDA Conda installation](https://docs.nvidia.com/cuda/cuda-installation-guide-linux/#conda-installation)

Before rendering in **each** environment:

```bash
python -c 'import torch; print(torch.__version__, torch.version.cuda); assert torch.cuda.is_available(); print(torch.cuda.get_device_name(0)); print(torch.ones(1, device="cuda").sum().item())'
```

If the compiler/runtime versions are wrong, reselect the explicit toolkit and compiler before rebuilding. If GPU access fails in the host terminal, stop CUDA steps. Browser inspection remains independently useful.

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

Create a separate preprocessing environment; this uses existing calibration rather than estimating new camera poses:

```bash
conda create -y -p "$GS_WORK/envs/stg-colmap" --override-channels -c conda-forge \
  python=3.8 pip colmap=3.8
conda activate "$GS_WORK/envs/stg-colmap"
python -m pip install torch==1.12.1+cpu --extra-index-url https://download.pytorch.org/whl/cpu
python -m pip install 'numpy<1.25' opencv-python-headless tqdm natsort Pillow
cd "$GS_WORK/SpacetimeGaussians"
python script/pre_n3d.py --help
python script/pre_n3d.py --videopath "$GS_WORK/data/stg/sear_steak" \
  --startframe "$STG_START" --endframe "$STG_END"
```

Verify that this checkout's help exposes `--startframe` and `--endframe` before the second command. Stop and record a source mismatch if it does not. These options limit COLMAP work; the inspected implementation still decodes 300 frames per camera. It creates/removes intermediate directories, which is why the working copy is separate. Preserve the input capture scale and use `--downscale 1` if selecting that option explicitly. [Preprocessing source](https://github.com/oppo-us-research/SpacetimeGaussians/blob/main/script/pre_n3d.py)

### Render and compare

Copy the model run so upstream render outputs do not modify the original downloaded bundle. Match the checkpoint duration/resolution in both the copied JSON and explicit arguments to avoid upstream default-equality precedence surprises:

```bash
cp -a -n "$STG_MODEL" "$GS_WORK/runs/stg-sear-steak-reference"
python3 - "$GS_WORK/SpacetimeGaussians/configs/n3d_lite/sear_steak.json" \
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
conda activate "$GS_WORK/envs/stg-render"
export CUDA_HOME="$GS_WORK/tools/cuda-11.6"
export PATH="$CUDA_HOME/bin:$PATH"
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions/stg"
cd "$GS_WORK/SpacetimeGaussians"
python test.py \
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

The released setup reports Python 3.8 and PyTorch 2.4.1+cu121. Use a separate CUDA 12.1 compiler prefix. The following dependency selection needs runtime validation; it is not a tested upgrade of the STG stack. [Mango-GS setup](https://github.com/htx0601/Mango-GS#installation), [requirements](https://github.com/htx0601/Mango-GS/blob/main/requirements.txt)

```bash
git clone --recursive https://github.com/htx0601/Mango-GS.git "$GS_WORK/Mango-GS"
git -C "$GS_WORK/Mango-GS" checkout --detach
git -C "$GS_WORK/Mango-GS" rev-parse HEAD
git -C "$GS_WORK/Mango-GS" submodule status --recursive
conda create -y -p "$GS_WORK/envs/mango-render" --override-channels -c conda-forge \
  python=3.8 pip gcc_linux-64=11 gxx_linux-64=11 ninja
conda create -y -p "$GS_WORK/tools/cuda-12.1" --override-channels \
  -c nvidia/label/cuda-12.1.1 -c conda-forge cuda-toolkit
conda activate "$GS_WORK/envs/mango-render"
export CUDA_HOME="$GS_WORK/tools/cuda-12.1"
export PATH="$CUDA_HOME/bin:$PATH"
export CC="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-cc"
export CXX="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"
export CUDAHOSTCXX="$CXX"
export TORCH_CUDA_ARCH_LIST="8.9"
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions/mango"
nvcc --version
"$CXX" --version
python -m pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 \
  --index-url https://download.pytorch.org/whl/cu121
cd "$GS_WORK/Mango-GS"
python -m pip install -r requirements.txt
python -m pip install --no-build-isolation -e submodules/diff-gaussian-rasterization
python -m pip install --no-build-isolation -e submodules/simple-knn
python -m pip check
python render.py --help
```

Record the full checkout revision before proceeding; the original release documentation does not pin this newer comparison. For repeat runs, check out that recorded commit and update its submodules. `requirements.txt` includes a PyTorch3D source dependency. If its current revision fails on Python 3.8/PyTorch 2.4.1, record the failure and resolve a matching PyTorch3D build before proceeding; do not silently change the whole environment. Capture the successful dependency revision and package inventory for reuse.

### Download the scene and prepare input frames

Use an independent download environment so the current Hugging Face CLI is not constrained by research Python 3.8:

```bash
conda create -y -p "$GS_WORK/envs/downloads" --override-channels -c conda-forge python=3.11 pip
conda run -p "$GS_WORK/envs/downloads" python -m pip install huggingface_hub
conda run -p "$GS_WORK/envs/downloads" hf download htx0601/Mango-GS \
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
conda activate "$GS_WORK/envs/mango-render"
export CUDA_HOME="$GS_WORK/tools/cuda-12.1"
export PATH="$CUDA_HOME/bin:$PATH"
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions/mango"
cd "$GS_WORK/Mango-GS"
bash scripts/render_one_frame.sh n3v sear_steak \
  "$GS_WORK/data/mango/sear_steak" "$GS_WORK/runs/mango/n3v/sear_steak" \
  0 "$GS_WORK/runs/mango/previews/sear-steak.png"
bash scripts/render_scene.sh n3v sear_steak \
  "$GS_WORK/data/mango/sear_steak" "$GS_WORK/runs/mango/n3v/sear_steak" 0 30
```

The scripts resolve the base model path to its `_mango_node` directory. The last sequence argument is encoded video FPS, not GPU throughput. Inspect the preview before running the longer sequence. Expected outputs are beneath the resolved model's `test/video_<checkpoint>/`; inspect the command log and resulting tree for the actual checkpoint identifier. [Published render commands](https://github.com/htx0601/Mango-GS#render-and-validate-n3v)

**Pass:** the original renderer reloads the complete downloaded model and produces a preview plus changing temporal states. Compare PNGs at overlapping physical times and matching camera views with STG. Record unmatched training splits, durations, resolutions, and backgrounds instead of presenting an uncontrolled leaderboard.

## 5. Try NoPo4D reconstruction inference

This stage predicts a dynamic representation from example images using reusable weights. It is different from loading a scene already optimized for `sear_steak`. The bundled example supplies four fixed cameras and four frames in camera-major filename order. [NoPo4D quick start](https://github.com/bralani/NoPo4D#quick-start)

### Install the model and backbone

Use another environment. PyTorch 2.4.1/cu121 with xFormers 0.0.28.post1 is a proposed compatible starting pair; the package declares `torch==2.4.1`. Upstream NoPo4D itself only specifies broader minimums. [xFormers package metadata](https://pypi.org/pypi/xformers/0.0.28.post1/json), [NoPo4D dependencies](https://github.com/bralani/NoPo4D/blob/main/pyproject.toml)

```bash
git clone --recurse-submodules https://github.com/bralani/NoPo4D.git "$GS_WORK/NoPo4D"
git -C "$GS_WORK/NoPo4D" checkout --detach
git -C "$GS_WORK/NoPo4D" rev-parse HEAD
git -C "$GS_WORK/NoPo4D" submodule status --recursive
conda create -y -p "$GS_WORK/envs/nopo4d" --override-channels -c conda-forge \
  python=3.10 pip gcc_linux-64=11 gxx_linux-64=11 ninja
conda activate "$GS_WORK/envs/nopo4d"
export CUDA_HOME="$GS_WORK/tools/cuda-12.1"
export PATH="$CUDA_HOME/bin:$PATH"
export CC="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-cc"
export CXX="$CONDA_PREFIX/bin/x86_64-conda-linux-gnu-c++"
export CUDAHOSTCXX="$CXX"
export TORCH_CUDA_ARCH_LIST="8.9"
export TORCH_EXTENSIONS_DIR="$GS_WORK/cache/torch_extensions/nopo4d"
python -m pip install torch==2.4.1 torchvision==0.19.1 torchaudio==2.4.1 \
  --index-url https://download.pytorch.org/whl/cu121
python -m pip install xformers==0.0.28.post1 --index-url https://download.pytorch.org/whl/cu121
cd "$GS_WORK/NoPo4D"
python -m pip install -e .
python -m pip install -e src/model/encoder/backbone/Depth-Anything-3
python -m pip check
python -c 'import torch, xformers; print(torch.__version__, torch.version.cuda, xformers.__version__); assert torch.cuda.is_available()'
python src/inference.py --help
```

If a dependency installation changes PyTorch/xFormers, resolve that conflict before inference and record the final stack. Optional `torch-scatter` voxelization is omitted for this first run. Backbone and model downloads use the workspace cache settings; account for their installed size as well as the main checkpoint. [Backbone requirements](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/main/pyproject.toml)

### Run the bundled example

Inspect the 16 example files before inference. Their camera-major ordering is part of the input, not an incidental filename convention:

```bash
cd "$GS_WORK/NoPo4D"
find assets/examples -maxdepth 1 -type f -name '*.png' -print | sort
python src/inference.py \
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

Record setup effort, model completeness, visual artifacts, viewpoint range, and repeatability before pursuing training. Useful inventories, run in the relevant activated environment and upstream checkout:

```bash
git rev-parse HEAD
git submodule status --recursive
python -m pip freeze
conda list --explicit
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
