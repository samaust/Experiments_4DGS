# Rendering and viewing 4DGS data

[Repository overview](../README.md) · [Research](research.md) · [Input data](input-data.md) · [Local creation](local-creation.md)

Reviewed on 2026-09-05. All GPU and browser procedures here remain **runtime-unverified on the target workstation**. Source inspection establishes the documented entry points and limitations, not achieved performance.

## Representation and viewer compatibility

| Saved representation | Matching local route | Conversion limits |
| --- | --- | --- |
| HUST canonical Gaussians + deformation files | HUST `render.py`; Python renderer API | Canonical PLY alone does not reproduce motion. Per-time exports need a sequence-aware player for animation. |
| Fudan native 4D primitives | Fudan's own rendering pipeline | No general conversion to splaTV established here |
| SpacetimeGaussians lite PLY | Python `test.py`; splaTV's compatible PLY import | Browser format has quantized attributes and a simplified renderer; verify appearance and timing |
| SpacetimeGaussians full model | Matching full Python renderer and decoder | splaTV does not evaluate the full neural appearance decoder |
| Mango-GS PLY + deformation + configuration | Mango-GS render scripts | Retain all parts of the scene bundle |
| NoPo4D predicted Gaussians | Its `model.render(...)` API with target cameras and timestamps | Persistence and external-viewer conversion need method-specific work |
| 4DGT predictions | Its Python renderer and local web GUI | GUI includes time/frame sliders but requires its model/runtime |
| Ordered static 3DGS frames | A compatible sequence player, or rendering each frame with a static renderer | A single static viewer does not supply sequence timing or temporal interpolation |

Sources: [HUST scene loading](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scene/__init__.py), [Fudan implementation](https://github.com/fudan-zvg/4d-gaussian-splatting), [SpacetimeGaussians test pipeline](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/test.py), [Mango-GS release](https://github.com/htx0601/Mango-GS), [NoPo4D API](https://github.com/bralani/NoPo4D#python-api), [4DGT viewer](https://github.com/facebookresearch/4DGT#gui--interactive-viewer).

PLY is a container: inspect its properties, not just its extension. Renaming a static `.ply` or `.splat` to `.splatv` does not create time-dependent data. Preserve the original trained representation alongside any compressed or sampled export.

## HUST images and videos

Use the environment, checkout, `GS_WORK` variable, dataset, and completed run from the [creation guide](local-creation.md#experiment-1-hust-synthetic-scene):

```bash
conda activate gs-hust-reference
cd "$GS_WORK/4DGaussians"
python render.py \
  --model_path "$GS_WORK/runs/hust-bouncingballs" \
  --configs arguments/dnerf/bouncingballs.py \
  --iteration 20000 --skip_train
python metrics.py --model_path "$GS_WORK/runs/hust-bouncingballs"
```

The reviewed renderer writes numbered PNGs and `video_rgb.mp4` into split directories such as `test/ours_20000` and `video/ours_20000`. Test outputs have ground-truth counterparts; generated camera-path outputs do not. `--skip_test` and `--skip_video` select which splits to omit. MP4 output is encoded at 30 FPS by this script; that is playback timing, not measured rendering speed. [Renderer source](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/render.py)

Keep the source dataset accessible: loading a saved scene still reads its metadata and initialization information. After moving the dataset, supply the new `--source_path`. Use the exact saved iteration and matching deformation configuration. A coarse-only snapshot is not the fine-stage result used above.

### Control scene time independently from camera motion

| Desired output | Camera sequence | Scene time |
| --- | --- | --- |
| Fixed-camera animation | One camera repeated | Advances through the modeled interval |
| Frozen-time orbit | Camera moves | Constant |
| Animated camera path | Camera moves | Advances independently |
| Selected timestamp | One camera | One specified value |

HUST's CLI does not expose a general camera-path file or timestamp flag. Its renderer consumes camera objects with a `.time` value. The example below is an **untested local API adaptation** for the D-NeRF baseline, using the dataset's test camera or generated orbit. It writes one frame at a time to avoid accumulating rendered GPU tensors. Sources: [renderer API](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/gaussian_renderer/__init__.py), [camera wrapper](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/scene/dataset.py).

Run inside the HUST checkout after training. Change `--mode` to `fixed`, `freeze`, or `animated`, and choose a new output directory for each invocation:

```bash
python - \
  --model_path "$GS_WORK/runs/hust-bouncingballs" \
  --configs arguments/dnerf/bouncingballs.py \
  --mode fixed --output "$GS_WORK/runs/hust-fixed-preview" <<'PY'
from argparse import ArgumentParser
from pathlib import Path
import torch
from torchvision.utils import save_image
from mmcv import Config
from arguments import ModelParams, ModelHiddenParams, PipelineParams, get_combined_args
from utils.params_utils import merge_hparams
from scene import Scene
from gaussian_renderer import GaussianModel, render

parser = ArgumentParser()
mp = ModelParams(parser, sentinel=True)
hp = ModelHiddenParams(parser)
pp = PipelineParams(parser)
parser.add_argument("--configs", required=True)
parser.add_argument("--mode", choices=["fixed", "freeze", "animated"], default="fixed")
parser.add_argument("--output", required=True)
args = get_combined_args(parser)
args = merge_hparams(args, Config.fromfile(args.configs))
dataset = mp.extract(args)
gaussians = GaussianModel(dataset.sh_degree, hp.extract(args))
scene = Scene(dataset, gaussians, load_iteration=20000, shuffle=False)
assert scene.dataset_type == "blender", "This example targets the D-NeRF baseline"
test_views, path_views = scene.getTestCameras(), scene.getVideoCameras()
assert len(test_views) and len(path_views)
output = Path(args.output)
output.mkdir(parents=True, exist_ok=False)
background = torch.tensor([1.0 if dataset.white_background else 0.0] * 3, device="cuda")
frame_count = 60
with torch.no_grad():
    for i in range(frame_count):
        tau = i / (frame_count - 1)
        view = test_views[0] if args.mode == "fixed" else path_views[round(tau * (len(path_views) - 1))]
        view.time = 0.5 if args.mode == "freeze" else tau
        pixels = render(view, gaussians, pp.extract(args), background, cam_type=scene.dataset_type)["render"]
        save_image(pixels.clamp(0, 1).cpu(), str(output / f"{i:05d}.png"))
PY
```

This samples the built-in synthetic orbit; it does not invent unseen geometry or guarantee a smooth custom path. For one timestamp, evaluate one camera with the desired `.time` and save one image. For custom paths, construct camera objects using the loader's conventions and update their derived view/projection matrices; changing `R` and `T` alone on an already-built camera can leave cached transforms inconsistent. Keep camera travel within useful capture coverage.

### Export sampled 3D Gaussians

```bash
python export_perframe_3DGS.py \
  --model_path "$GS_WORK/runs/hust-bouncingballs" \
  --configs arguments/dnerf/bouncingballs.py --iteration 20000
```

The implementation writes `gaussian_pertimestamp/time_00000.ply` and subsequent files by iterating **test observations**. Its names are observation indices, not seconds. Multiple views at the same time may produce duplicate-time exports; an empty test set produces none. Preserve a separate index-to-time record when using these files as an animation sequence. They are sampled 3DGS states, not the original continuous deformation model. [Exporter source](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/export_perframe_3DGS.py)

## SpacetimeGaussians images and videos

Reload the 12-frame smoke run with its matching duration, resolution, and iteration:

```bash
conda activate feature_splatting
cd "$GS_WORK/SpacetimeGaussians"
python test.py \
  --source_path "$GS_WORK/data/n3v/cook_spinach/colmap_0" \
  --model_path "$GS_WORK/runs/stg-spinach-smoke" \
  --configpath configs/n3d_lite/cook_spinach.json \
  --eval --skip_train --valloader colmapvalid \
  --duration 12 --resolution 4 --test_iteration 1000
```

For the 50-frame run, use `--model_path "$GS_WORK/runs/stg-spinach-lite"`, `--duration 50`, `--resolution 2`, and `--test_iteration 25000`. The Python test pipeline writes `test/ours_<iteration>/renders`, corresponding ground truth, and metric JSON files. It evaluates an image sequence; video encoding is a separate step. [Test implementation](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/test.py)

Install FFmpeg separately if needed. After confirming that the 12 PNGs are a single held-out camera in time order, an example 30-FPS encoding is:

```bash
ffmpeg -n -framerate 30 \
  -i "$GS_WORK/runs/stg-spinach-smoke/test/ours_1000/renders/%05d.png" \
  -vf 'pad=ceil(iw/2)*2:ceil(ih/2)*2' \
  -c:v libx264 -pix_fmt yuv420p \
  "$GS_WORK/runs/stg-spinach-smoke/preview.mp4"
```

Use the source capture's frame rate for faithful playback; 12 frames at 30 FPS play for 0.4 seconds. Do not concatenate observations from different cameras and interpret them as a fixed-camera animation.

Custom camera paths are implementation-specific. SpacetimeGaussians exposes a no-ground-truth rendering branch selected through loaders ending in `mv`; the path is constructed by its loader, not by a universal path-file interface. Adapt its camera/time sequence for frozen-time or custom-path rendering, preserving the training window's time normalization. [Test parser](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/thirdparty/gaussian_splatting/helper3dg.py), [camera-path generation](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/thirdparty/gaussian_splatting/scene/dataset_readers.py)

## Local browser playback with splaTV

This route does not need a Python training environment. It needs Python 3 for a local file server and a browser with working WebGL2. Clone into the external workspace and use the included scene first:

```bash
cd "$GS_WORK"
git clone https://github.com/antimatter15/splaTV.git
cd splaTV
git checkout --detach 8b313fe
git rev-parse HEAD
test -s model.splatv
python3 -m http.server 8000 --bind 127.0.0.1
```

Open [the local viewer](http://127.0.0.1:8000/). Its default asset is local `model.splatv`. For another file under the served directory, use an absolute local URL, for example `http://127.0.0.1:8000/?url=http://127.0.0.1:8000/my-scene.splatv`; a relative `url` parameter is resolved against an upstream Hugging Face base. Mouse dragging orbits; arrow keys translate. Sources: [viewer code](https://github.com/antimatter15/splaTV/blob/main/hybrid.js), [HTML entry point](https://github.com/antimatter15/splaTV/blob/main/index.html).

### Import a trained lite scene

1. Render the original lite model with Python first, so there is a reference image.
2. In the browser, drop a compatible SpacetimeGaussians lite PLY. Optionally load the matching camera JSON before conversion so its cameras are embedded in the exported file.
3. The importer produces a `model.splatv` download. Store it under a new name in the local viewer directory and reopen using an absolute local URL.
4. Check beginning/middle/end states and camera alignment. Record any color, opacity, sorting, or quantization differences from the Python renderer.

The importer expects spatial attributes plus `motion_0`–`motion_8`, `omega_0`–`omega_3`, and temporal radial-basis fields. It treats the first three color features as RGB. It does not reproduce a full learned appearance decoder. Default playback oscillates time sinusoidally over 0–1; it is not faithful constant-speed capture playback. The reviewed UI lacks a timeline scrubber. [Importer and time loop](https://github.com/antimatter15/splaTV/blob/main/hybrid.js)

For a simple frozen-time inspection, an optional **untested local edit** is to replace the `gl.uniform1f(u_time, ...)` assignment with `gl.uniform1f(u_time, 0.5)`. A proper pause/scrub/loop control requires a local viewer modification and is not included here. For an existing GUI with time/frame sliders, investigate [4DGT's local viewer](https://github.com/facebookresearch/4DGT#gui--interactive-viewer); it uses a different representation and cannot directly open the HUST/STG checkpoints.

### Verify that playback is local

After assets are downloaded, reload with the browser's network inspector open and external network access disconnected while retaining loopback access. Confirm that model/script requests go to `127.0.0.1`, and that the scene still animates and responds to camera input. A hosted demo working is not evidence that a local export is complete.

## Native viewers and further integrations

HUST's documented SIBR remote viewer connects to an active training process on the selected port; it is not a standalone loader for its complete dynamic checkpoint. Its instructions use a Windows executable. SpacetimeGaussians also documents Windows-specific native viewer binaries/build steps. Neither is claimed as a validated Ubuntu native viewer in this repository. [HUST viewer instructions](https://github.com/hustvl/4DGaussians/blob/843d5ac636c37e4b611242287754f3d4ed150144/docs/viewer_usage.md), [SpacetimeGaussians viewer build](https://github.com/oppo-us-research/SpacetimeGaussians/blob/427abfc/script/setup.sh)

[Hugging Face gsplat.js](https://github.com/huggingface/gsplat.js) is another viewer-library candidate, but its static PLY/`.splat` support is not proof of compatibility with arbitrary dynamic models. Its README notes that basic `.splat` conversion loses spherical-harmonic coefficients. Validate the exact dynamic representation and example before adopting a viewer library.

For any future renderer integration, acceptance means: load the complete artifact in a new process, visit multiple scene times, move the camera independently, reproduce a reference view, and account for export losses. Record output resolution, GPU/browser, scene size, and timing boundaries using the [experiment record](local-creation.md#experiment-record). A rendered MP4 captures one camera/time path; it does not retain free-viewpoint navigation.
