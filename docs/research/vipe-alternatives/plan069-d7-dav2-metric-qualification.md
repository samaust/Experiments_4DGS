# D7 metric Depth Anything V2 Small qualification for Plan 069

**Status:** CPU fake-runtime qualified; actual checkpoint bytes, host runtime,
installed dependencies and GPU use remain subject to later admission.

The exact assets are [source commit `a561b849ebae10a6f5ef49e26c83cbbcd36c71bf`](https://github.com/DepthAnything/Depth-Anything-V2/tree/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf)
and [Hypersim Small checkpoint revision `3bc65d4e14a6786a61acec16453c50e12bf5f338`](https://huggingface.co/depth-anything/Depth-Anything-V2-Metric-Hypersim-Small/tree/3bc65d4e14a6786a61acec16453c50e12bf5f338),
file `depth_anything_v2_metric_hypersim_vits.pth`. Record its local SHA256 and
size at setup. The source license and exact model card identify Apache-2.0;
the separate #55 inventory must check installed dependencies and preserve
required notices. [Pinned source license](https://github.com/DepthAnything/Depth-Anything-V2/blob/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf/LICENSE),
[model card](https://huggingface.co/depth-anything/Depth-Anything-V2-Metric-Hypersim-Small).

The native model is `metric_depth/depth_anything_v2/dpt.py` with
`encoder='vits'`, `features=64`, `out_channels=[48,96,192,384]` and
`max_depth=20`. Use eval mode with float32 weights and
`infer_image(BGR, input_size=518)`. Its pinned preprocessing converts BGR to
RGB, applies lower-bound aspect-preserving cubic resize to **924×518** on the
accepted 960×540 frame, uses ImageNet mean/std, and restores the prediction
with bilinear interpolation (`align_corners=True`) to 960×540. The sigmoid
head multiplies by 20 m. D7 does no later clamp, FoV scaling or alignment;
it rejects nonfinite, nonpositive or >20 m output in the valid footprint and
stores the native restored depth separately from NaN-masked camera-z.
[Pinned model implementation](https://raw.githubusercontent.com/DepthAnything/Depth-Anything-V2/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf/metric_depth/depth_anything_v2/dpt.py),
[transform](https://raw.githubusercontent.com/DepthAnything/Depth-Anything-V2/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf/metric_depth/depth_anything_v2/util/transform.py),
[camera-z point-cloud convention](https://raw.githubusercontent.com/DepthAnything/Depth-Anything-V2/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf/metric_depth/depth_to_pointcloud.py).

The pinned `metric_depth/requirements.txt` lists Matplotlib, OpenCV, Open3D,
PyTorch and torchvision; NumPy is also imported. The official Small model is
24.8M parameters. D7 needs 60 anchor inferences and at most 196 additional
clip frames. The actual host must measure first load, per-image latency,
GPU peak and artifact/CPU packaging costs under the existing 22 GiB cap.
[Pinned requirements](https://raw.githubusercontent.com/DepthAnything/Depth-Anything-V2/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf/metric_depth/requirements.txt),
[metric model table](https://raw.githubusercontent.com/DepthAnything/Depth-Anything-V2/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf/metric_depth/README.md).

CPU tests verify BGR/native 518 invocation, restored grid, native range,
nonfinite rejection, exact Small configuration, and 30-camera worker→scale→
package behavior. These fixtures do not claim native GPU qualification.
