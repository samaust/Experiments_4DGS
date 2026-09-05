# Pretrained experiment execution

Date: 2026-09-05. Ubuntu 24.04, RTX 4090 (24,564 MiB), driver 595.84.
Standard Python 3.14.6, Torch 2.13.0+cu130, torchvision 0.28.0+cu130,
CUDA toolkit 13.0 and GCC 13.3. No Conda or training was used.

Follow-up: all five experiments were freshly executed for section 6, including
hardware WebGL2 browser inspection and full NoPo4D reconstruction. See the
[per-experiment evidence and decisions](section6-evidence.md). The checks below
describe the earlier setup pass; its browser and NoPo4D limitations were resolved
by that follow-up. Remaining limitations are stated in the individual reports.

## Executed checks

- Authorized host GPU access works. The Mango environment passes synchronized
  CUDA tensor operations, PyTorch3D CUDA KNN forward/backward and point rasterization.
- splaTV's time-control patch applies to the pinned checkout. The STG conversion
  helper produced a 7,343,047-byte asset with 108,317 Gaussians and 1,052 camera
  entries. The local server returned HTTP 200 for it. Interactive WebGL playback,
  hardware acceleration and frozen-time camera controls still require browser acceptance.
- All five STG native extensions built. The native preview helper rendered three
  finite, nonconstant 1352×1014 images at normalized model times 0, 0.5 and 0.98.
  The inspected middle image shows coherent scene content and camera framing.
  Images and camera metadata are in `.local/runs/stg-native-preview/`.
  This is an original-renderer qualitative preview, not a held-out evaluation.
  A second run sampled 50 normalized timestamps and encoded
  `.local/runs/stg-native-sequence/preview.mp4`; ffprobe confirms 50 frames,
  1352×1014, at the selected 30 FPS playback rate.
- Mango's two extensions built. `simple-knn` must be installed as a normal wheel:
  the editable install had package metadata but an unimportable module.
  All 21 cameras have contiguous frames `00000.png` through `00299.png`.
  Upstream `scripts/tools/render_one_frame.py` successfully loaded the complete
  checkpoint and saved `.local/runs/mango-preview/first.png` (1352×1014).
  The image was inspected; visible edge streaking is not a controlled comparison
  with STG because training splits and model time differ. `render.py --help`
  also passed after its AlexNet/VGG16/LPIPS weights downloaded to the workspace cache.
  The full upstream sequence render subsequently completed with
  `--video_window_mode block --load2gpu_on_the_fly`: 300 renders, 300 ground-truth
  images and 300 depth maps, each numbered 00000–00299. Sampled beginning,
  middle and end states differ. The MP4 is
  `.local/runs/mango/n3v/sear_steak_mango_node/test/video_release/renders/cam00/test_cam00.mp4`.
  ffprobe confirms 300 frames at 30 FPS; upstream pads the 1352×1014 PNGs to
  1360×1024 for encoding. The first preview and sequence midpoint were inspected.
- The patched NoPo4D/backbone editable installation now resolves on Python
  3.14.6 with Torch 2.13.0+cu130, xFormers 0.0.35, gsplat 1.5.3 and NumPy 2.5.2.
  The patches update Python/NumPy metadata, declare the missing runtime
  dependency `addict`, and move Open3D to the backbone's optional `benchmark`
  extra because only benchmark modules import it. `uv pip check`, the package
  imports and `src/inference.py --help` pass. The smoke check
  `scripts/verify-nopo4d.py` passes image preprocessing, affine inversion, and
  attention forward/backward. These checks do not establish full pretrained
  reconstruction or GPU rendering compatibility; no model-weight download or
  full inference is claimed. Open3D benchmarks remain unavailable on Python 3.14.
  Reproduce with `bash scripts/setup-nopo4d.sh`; successful installation logs
  and package inventory are in `.local/runs/nopo4d-install-pPSccZ92/`.

The native STG preview does not require COLMAP. The full dataset evaluation
route remains unexecuted because the native COLMAP CLI is absent. The checkpoint
was trained on all cameras, so its camera views are not held-out evidence.
Its saved `source_path='xxx'` does not recover a physical capture window;
start 0 and profile duration 50 are explicit assumptions only.

## Revisions and artifacts

| Source | Full revision |
| --- | --- |
| splaTV | `8b313fea028d32f3c978f06b0a8bd2050b03ff28` |
| SpacetimeGaussians | `427abfc58309a4a5213843dd673fb22c4529306c` |
| Mango-GS | `2a7a9238c1518c5770dc2952464bc71a4d3dba75` |
| PyTorch3D | `0a7d4c1a171e8b768c63f15b17564f9ad495f49b` |
| NoPo4D | `cb54c9349792d474aa541274842e0fadf1d807c7` |
| Depth Anything 3 backbone | `41736238f5bced4debf3f2a12375d2466874866d` |

Downloads used the release URLs in the guide; hashes below identify the actual
bytes, not an inferred Hugging Face source revision.

| Artifact | SHA-256 |
| --- | --- |
| splaTV bundled model | `672fe189fc8e81e52bf0e1529993f95641ee54883391f5e5ea93badd130f10e9` |
| STG lite archive | `e017d214b6bc695d1a7da8c75598eab1393e1be9507d250976658bc66c31eca2` |
| Generated STG splatv | `60dcab6db3e1500faa8a136bb6a2b81afd2edcdf0270a70119815a7ea2528fba` |
| Neural 3D sear_steak archive | `b53d9c444ab23d468f9d5da0dcbc5ab68cb70702bb03f9664cd686e9efebc525` |
| Mango cfg_args | `b02bc9e2ec7c45e7c301f02f7551ee286d82f6da48d82fcb054d4c975de00f0f` |
| Mango point_cloud.ply | `b89b5d2d533bbb67e031b72aac31779524a13d601f1ae2cf662dda8d673d1c14` |
| Mango deform.pth | `82709ff8d270a063f33093f189814cd48115cb2dbe1a1d4af0530e81532e70b3` |

Native build logs are in `.local/runs/pretrained-validation/`, including
`stg-build-patched.log`, `mango-build-patched.log`, and `mango-knn-wheel.log`.
The patches and helpers are tracked; downloads, images, caches, environments
and build logs remain ignored. No comparative quality ranking or GPU throughput
benchmark is established by these smoke tests.

Mango's upstream console reported camera-00 metrics: PSNR 30.1609, SSIM 0.9554,
LPIPS 0.2401, MS-SSIM 0.9596, and AlexNet LPIPS 0.1189. These are results of this
specific loader/profile/metric stack, not independently reproduced paper metrics
or a cross-method ranking. Its synchronized deformation-plus-render timers summed
to 2.153 seconds for 300 frames (139.34 FPS). That excludes image loading,
metrics and encoding, has no controlled warm-up protocol, and the process
overlapped a separate STG preview run. Do not treat it as an isolated GPU benchmark.
Peak VRAM was not measured.

Validation: eight Python checkpoint-resolver tests and five JavaScript timeline
tests pass. All Bash blocks in the environment and pretrained guides pass
`bash -n`. The three native STG images differ (consecutive mean absolute RGB
differences of 2.856 and 2.583 on the 0–255 scale); this confirms changing output,
not temporal fidelity. Patch reverse-application checks identify the installed
changes without resetting the source checkouts.
