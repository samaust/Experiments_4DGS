# D10 Metric Video Depth Anything Small qualification

**Status:** exact-release camera-z convention established and CPU fake-runtime
fit/check/package path qualified. Native checkpoint bytes, installed
dependencies and GPU profile remain unverified until separate admission.

Pin [source `4f5ae23172ba60fd7bc11ef671cca678842c7072`](https://github.com/DepthAnything/Video-Depth-Anything/tree/4f5ae23172ba60fd7bc11ef671cca678842c7072)
and [Metric Small revision `273d090f2ce17df50c2872d82c8322c45da5b4dd`](https://huggingface.co/depth-anything/Metric-Video-Depth-Anything-Small/tree/273d090f2ce17df50c2872d82c8322c45da5b4dd),
file `metric_video_depth_anything_vits.pth`. The source and exact model page
identify Apache-2.0; dependency terms still need #55 review. Record actual
weight bytes and SHA256 before model load. [Pinned README](https://raw.githubusercontent.com/DepthAnything/Video-Depth-Anything/4f5ae23172ba60fd7bc11ef671cca678842c7072/README.md),
[model page](https://huggingface.co/depth-anything/Metric-Video-Depth-Anything-Small).

## Camera convention

The exact release's metric [`run.py`](https://raw.githubusercontent.com/DepthAnything/Video-Depth-Anything/4f5ae23172ba60fd7bc11ef671cca678842c7072/run.py)
forms metric point clouds by assigning predicted depth directly to `z` and
computing `x=(u-cx)z/fx`, `y=(v-cy)z/fy` (lines 76–86). The pinned
[`infer_video_depth`](https://raw.githubusercontent.com/DepthAnything/Video-Depth-Anything/4f5ae23172ba60fd7bc11ef671cca678842c7072/video_depth_anything/video_depth.py)
sets overlap scale/shift to `(1,0)` when `metric=True` (lines 121–126).
Thus this release's metric output is **camera-z metres** for this path; it is
not Euclidean ray range, and no radial or focal conversion is applied. An
off-axis CPU fixture keeps known z=4 m rather than turning it into 5 m. This
source-backed convention is recorded in the versioned D10 configuration.
The isolated per-frame worker still rejects D10, so it cannot bypass temporal
context or the 30-camera scale gate.

Use `VideoDepthAnything(encoder='vits', metric=True).eval()` in native offline
mode, input size 518, 25 fps and native FP16 autocast. Preserve 32-frame
windows, 10-frame overlap, keyframe reuse, eight-frame interpolation and tail
padding, with no relative scale/shift fit. Fit context 50–149 and check context
150–199 remain separate for every camera. The CPU fixture processes all 30
camera contexts for each role, publishes 60 anchors plus at most 196 extra
clip maps, fits scale at frame 100, checks at 175 with the immutable fit, and
creates four 50-frame metric clips. A failed fit remains blocked and requires
separate qualitative-only admission for visual maps.

D10 shares D9's 4,500 distinct context frames and 240 native windows, plus
the metric fit/check work. The same [pinned dependencies](https://raw.githubusercontent.com/DepthAnything/Video-Depth-Anything/4f5ae23172ba60fd7bc11ef671cca678842c7072/requirements.txt)
include Python-era NumPy 1.24, torch 2.1.1, torchvision 0.16.1 and xformers
0.0.23. Confirm an isolated compatible environment, checkpoint bytes and
third-party license inventory, then measure first load, 240-window runtime,
peak GPU memory, context decode, CPU package cost and artifacts against the
one-GPU and 22 GiB limits. The source's A100 timings do not establish a host
runtime bound.
