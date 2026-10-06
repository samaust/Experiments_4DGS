# Joint FreeTimeGS/RoMa runtime setup (#34)

`build.sh` created `.local/envs/plan069-joint-native-001` (Python 3.14, torch
2.13.0+cu130) from `joint-pins.txt`: the FreeTimeGS environment's 77 pins minus
GUI OpenCV, plus the RoMa matcher closure with `opencv-python-headless` 5.0.0.93
only. gsplat (`b60e917`) and fused-ssim (`1272e21`) were rebuilt from their pinned
checkouts for sm_89. `uv pip check` passed for 110 packages.

- Attempt 001 (offline only) failed: `triton==3.7.1` was not in the uv cache
  (`build-attempt-001-offline-failed.log`). The partial environment was removed.
- Attempt 002 fetched cache misses only: 122.8 s, uv cache growth 784,327,737
  bytes (`setup-receipt.json`, `build.log`). Cache growth also includes the two
  locally built wheels, so it overstates transferred bytes.
