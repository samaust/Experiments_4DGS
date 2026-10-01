# D9 Video Depth Anything Small offline qualification

**Status:** CPU fake-runtime request→clip path qualified. Native checkpoint
bytes, installed dependencies, commercial inventory and host GPU cost remain
unverified until separately admitted setup and execution.

Pin [source `4f5ae23172ba60fd7bc11ef671cca678842c7072`](https://github.com/DepthAnything/Video-Depth-Anything/tree/4f5ae23172ba60fd7bc11ef671cca678842c7072)
and [relative Small checkpoint `256875362cff76724b920335dfb4b29dd611f66e`](https://huggingface.co/depth-anything/Video-Depth-Anything-Small/tree/256875362cff76724b920335dfb4b29dd611f66e),
file `video_depth_anything_vits.pth`. The official Small card and source README
identify Apache-2.0; Base/Large are separate noncommercial releases. Check
actual checkpoint bytes/SHA256 and all installed dependency terms in #55.
[Pinned README](https://raw.githubusercontent.com/DepthAnything/Video-Depth-Anything/4f5ae23172ba60fd7bc11ef671cca678842c7072/README.md),
[Small card](https://huggingface.co/depth-anything/Video-Depth-Anything-Small).

Use `VideoDepthAnything(encoder='vits', metric=False).eval()` and its **native
offline** `infer_video_depth(frames, 25, input_size=518, fp32=False)`. Frames
are accepted, undistorted 960×540 RGB at original 25-fps timestamps. The
native method owns 32-frame windows, 10-frame overlap, keyframes
`[0,12,24,25,26,27,28,29,30,31]`, eight interpolated overlap frames,
tail repetition and relative scale/shift alignment. Each camera has a fresh
100-frame fit call (50–149) and a separate 50-frame check call (150–199).
No streaming mode, framewise call, sparse-map alignment or metric-scale gate
is used. Raw nonnegative relative outputs remain arbitrary values; clip
normalization is display-only. [Pinned offline implementation](https://raw.githubusercontent.com/DepthAnything/Video-Depth-Anything/4f5ae23172ba60fd7bc11ef671cca678842c7072/video_depth_anything/video_depth.py).

Across 30 cameras, the full context is 4,500 distinct frames. Native work is
150 fit windows plus 90 check windows = **240 32-frame windows** and 7,680
window frame slots, including overlap and padded tails. Each fit call pads 20
frames; each check call pads 26. Only 60 anchors and at most 196 additional
clip maps are published. Every camera/role result records its entire source
context hash, reset boundary and exact window plan. The four selected check
cameras produce matched 50-frame clips.

The pinned requirements specify NumPy 1.24.0, torch 2.1.1, torchvision
0.16.1, xformers 0.0.23, imageio 2.37.0, imageio-ffmpeg 0.4.7, einops
0.4.1, OpenEXR 3.3.1, plus OpenCV, Matplotlib, Pillow, decord, easydict and
tqdm. Confirm an isolated compatible Python/CUDA environment before any
download or GPU setup. The official 28.4M-parameter Small profile reports
6.8 GB FP16 on an A100 for one 32×518×518 window; it does **not** bound this
host. Measure first load, 240-window runtime, peak memory, context decode,
CPU clip publication and artifacts under the one-GPU/22 GiB limits.
[Pinned requirements](https://raw.githubusercontent.com/DepthAnything/Video-Depth-Anything/4f5ae23172ba60fd7bc11ef671cca678842c7072/requirements.txt),
[published profile](https://raw.githubusercontent.com/DepthAnything/Video-Depth-Anything/4f5ae23172ba60fd7bc11ef671cca678842c7072/README.md).

CPU fixtures verify 22/32/50/100-frame window accounting, missing/cross-role
context rejection, source-context hash changes, role resets, and a four-camera
request→ledger→four synchronized clips path. They do not qualify native
weights or claim commercial execution authority.
