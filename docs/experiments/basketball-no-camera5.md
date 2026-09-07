# Basketball calibration excluding camera 5

The user explicitly removed physical camera 5 after its intrinsic-prior spread
exceeded the authorized 25% limit. This creates the versioned
`basketball-no-camera5/v1` variant: **33 cameras, 29 training cameras and four
held-out cameras (0, 10, 20, 30)**. Source camera IDs are preserved. Camera 5's
video and historical evidence remain on disk but cannot enter subsequent
estimation, reconstruction, initialization, training or evaluation.

The prepared scene must contain **1,650 images: 1,450 training and 200 held-out**
for source frames 0–49 at 960×540. Camera 0 still starts the shared 20-pose sweep
at frame 25. Its nearest training endpoint must be selected from the retained
training rig after calibration. Frame windows, other acceptance gates, crop
policy, original per-method training allocations and cumulative eight-hour
calibration budget are unchanged. Results must name this 33-camera variant and
estimated calibration; they are not official 34-camera benchmark results.

## Retained priors

The 33 retained cameras already passed the 25% intrinsic-stability check.
The continuation reuses their 165 fitting-window intrinsic estimates from the
previous all-camera result, after checking video, source, model-weight and input
audit provenance. It regenerates fitting RGB/temporal differences directly from
the source videos, then runs UniDepth and TrackAnything for retained cameras.
The excluded camera is rejected by the frame-access guard in both pilot and
all-camera modes. Original failed attempts remain charged to the same ledger.

Protocol: `.local/calibration/basketball-v1/protocol-no-camera5.json`.
Prior output: `.local/calibration/basketball-v1/no-camera5-priors`.
GPU log: `.local/calibration/basketball-v1/no-camera5-priors.log`.

```bash
PYTHONDONTWRITEBYTECODE=1 python3 scripts/calibration_budget.py \
  --ledger .local/calibration/basketball-v1/gpu-ledger.json \
  --seconds 3600 --log .local/calibration/basketball-v1/no-camera5-priors.log \
  -- /home/auss/git_repos/samaust/Tridi/vipe/.venv/bin/python \
  scripts/basketball_vipe_pilot.py \
  --workspace .local/calibration/basketball-v1 \
  --vipe /home/auss/git_repos/samaust/Tridi/vipe \
  --output .local/calibration/basketball-v1/no-camera5-priors \
  --all-priors .local/calibration/basketball-v1/pilot-25/result.json \
  --intrinsics-from .local/calibration/basketball-v1/all-priors/result.json
```

## Static reconstruction design

`scripts/basketball_static_rig.py` uses pinned PyCOLMAP 4.2.0 CPU masked SIFT.
It extracts features from all five fitting timestamps for the 29 training
cameras, rejects features whose descriptor support intersects dynamic regions,
and combines them into one virtual image per physical camera. A two-pixel cell
keeps one feature observation per location to avoid counting repeated timestamps
as independent geometric support. Source frame/keypoint membership is retained.
Each physical camera has one PINHOLE calibration and one fixed pose throughout
reconstruction. GeoCalib uses integer-centered image coordinates; adding 0.5 to
the principal point converts to COLMAP's half-integer convention.

Exhaustive matching determines overlap without camera-ID adjacency assumptions.
Incremental reconstruction is bounded to ten minutes, followed by robust
SOFT_L1 bundle adjustment. The reconstruction is a calibration map only, never
Gaussian initialization. Held-out fitting images are reserved for localization
against a frozen accepted training map. A connected candidate does not by itself
pass planar-degeneracy, independent temporal-window, reprojection or timing gates.


## Retained-prior outcome

The 33-camera prior stage passed: 165 fitting observations, 33 representative
depth maps and 165 static masks. Every representative depth map has 100% finite
positive depth. Intrinsic estimates match the previous retained estimates;
there was no focal re-estimation or further threshold adjustment. The
[prior evidence](basketball-no-camera5-priors.json) records camera membership,
quality ranges, source/configuration bindings, runtime, peak memory and budget.
All generated image/mask/depth files are additionally bound by `artifacts.json`.
The stage took 373.5065 seconds inside the worker. This is a prior-quality pass,
not accepted shared calibration or proof of complete moving-region rejection.

Seventeen focused tests passed for camera exclusion, retained counts, frame
leakage, pose/pixel conventions and calibration accounting. Source-camera IDs
and original input audit remain unchanged. Static reconstruction continues.

## SIFT candidate and independent-window gate

The full PINHOLE SIFT run registered all 29 training cameras in one connected
candidate with 9,139 points and mean fitting reprojection error 0.4923 pixels.
A separate four-camera submodel was degenerate: bundle adjustment drove some
focals beyond ten image widths, so it is not a usable alternative rig.
Independent reconstructions from frames 50/75 and 125/149 both registered all
29 cameras. After a single global similarity alignment, their maximum
rotation disagreement was **7.6405°**, and camera-center disagreement was
**4.9614% of rig diameter**. This fails the fixed 0.5°/1% gate despite low
fitting error. These maps are not accepted calibration.

The single predefined distortion alternative is COLMAP `RADIAL`: one focal,
two radial coefficients and fixed zero tangential distortion. Independent early
and late reconstructions also failed (**177.6887°**, **80.7268%**). It was not
selected; neither selection-window improvement nor final acceptance is claimed.
No selection or final-validation frames were consumed. Reconstruction and
bundle adjustment ran on CPU; the GPU ledger remains reserved for GPU stages.

Diagnostics:
`.local/calibration/basketball-v1/no-camera5-pose-stability.json` and
`.local/calibration/basketball-v1/no-camera5-radial-pose-stability.json`.
The plan's single bounded RoMa fallback is the next permitted recovery step.
