# D5 MoGe-2 adapter qualification for Plan 069

**Status:** CPU fake-runtime and accepted-grid contract qualified. Native model
execution, checkpoint bytes, dependency installation, commercial inventory and
GPU profile remain unverified until the separately admitted setup and run.

## Exact release and mode

| Asset | Frozen identity | Admission check |
| --- | --- | --- |
| Source | [microsoft/MoGe](https://github.com/microsoft/MoGe/tree/74fbce054ebed49800de42d0ad0e83495065719a) at `74fbce054ebed49800de42d0ad0e83495065719a` | Check checkout commit and record source files/dependencies. |
| Model | [Ruicheng/moge-2-vitl](https://huggingface.co/Ruicheng/moge-2-vitl/tree/39c4d5e957afe587e04eec59dc2bcc3be5ecd968) at `39c4d5e957afe587e04eec59dc2bcc3be5ecd968`, original `model.pt` | Record downloaded bytes/SHA256 and exact card before use. The model page lists 1.31 GB; this is metadata, not a local asset receipt. |
| Native API | [`moge.model.v2.MoGeModel.infer`](https://github.com/microsoft/MoGe/blob/74fbce054ebed49800de42d0ad0e83495065719a/moge/model/v2.py) | Load the pinned local checkpoint, call `eval()`, and use the adapter in `scripts/vipe_benchmark/moge_metric.py`. |

The native call receives RGB float32 in `[0,1]`, CHW, the horizontal FoV
derived from accepted 960×540 centered pinhole `K`, `resolution_level=9`,
`force_projection=True`, `apply_mask=True`, and `use_fp16=True`. It runs once
per image; no stochastic sampling or pose alignment is used. The release
returns camera-space points and z-depth on the input grid, applies its learned
metric scale inside `infer`, and marks masked pixels with infinity. D5 preserves
both native arrays, marks invalid pixels with NaN in the restored map, and does
not multiply by focal length or convert point norm into z-depth. Internal
token/image interpolation is part of the native method; the adapter adds no
padding or crop. It rejects a changed output grid. [Pinned native source](https://raw.githubusercontent.com/microsoft/MoGe/74fbce054ebed49800de42d0ad0e83495065719a/moge/model/v2.py).

## Dependency and runtime inventory for #55

The exact [pinned `pyproject.toml`](https://raw.githubusercontent.com/microsoft/MoGe/74fbce054ebed49800de42d0ad0e83495065719a/pyproject.toml)
declares Python ≥3.10, NumPy ≥2, PyTorch ≥2.4, torchvision ≥0.19,
OpenCV headless, SciPy ≥1.8, Pillow, Matplotlib, Trimesh ≥4.11,
Hugging Face Hub, requests, tqdm, click, Gradio and Starlette. It also pins
`utils3d_moge` to `62f09d58509485564e24d5d9f6aac9ee9ebc0c37`,
`pipeline` to `1c511390d90226c00c101f34b84df26a0f8789b4`, and FlexGEMM
to `b2fadb29d41846c7981ade6801ffc689fae119cf`. The project `uv`
configuration points PyTorch wheels to the CUDA 13.0 index; actual host wheel,
driver and third-party license compatibility require separate qualification.

The model card labels the original checkpoint MIT and the source declares MIT.
This does not settle transitive dependency or installed-wheel terms. [Pinned
model page](https://huggingface.co/Ruicheng/moge-2-vitl/tree/39c4d5e957afe587e04eec59dc2bcc3be5ecd968),
[source metadata](https://raw.githubusercontent.com/microsoft/MoGe/74fbce054ebed49800de42d0ad0e83495065719a/pyproject.toml).

D5 needs **60 anchor inferences** (30 fit plus 30 check) and at most **196
additional clip-frame inferences**; the four frame-175 clip maps are reused.
The source model is listed as 326M parameters. Its README quotes 60 ms per
image on A100 or RTX 3090 with FP16, which is not a host-specific estimate.
The admitted run must measure this host's first load, per-frame latency, peak
GPU allocation/reservation, CPU packaging, artifact bytes and transfer cost
before using a bound. One GPU process group and the existing 22 GiB device
ceiling apply. [Pinned README](https://github.com/microsoft/MoGe/tree/74fbce054ebed49800de42d0ad0e83495065719a).

CPU tests cover known z with off-axis points, supplied FoV, rejected off-center
intrinsics, inconsistent radial-versus-z depth, invalid interpolation
contributors, and the 30-camera worker→scale→package path. These tests use a
fake native runtime and do not establish native model accuracy or runtime fit.
