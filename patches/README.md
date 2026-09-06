# Local upstream patches

Native compatibility patches (apply once using `git apply --check`, then
`git apply`; preserve existing checkout edits):

- [stg-python314-cu130.patch](stg-python314-cu130.patch), STG revision
  `427abfc58309a4a5213843dd673fb22c4529306c`: CUDA 13 integer headers,
  NumPy/SSIM API updates, early missing-COLMAP failure, and lazy import of
  training-only MMCV KNN. It does not port MMCV training operations.
- [mango-cu130.patch](mango-cu130.patch), Mango revision
  `2a7a9238c1518c5770dc2952464bc71a4d3dba75`: explicit CUDA integer header.
- [stg-ems-quaternion.patch](stg-ems-quaternion.patch), STG revision
  `427abfc58309a4a5213843dd673fb22c4529306c`: initialize EMS-added Lite/Full
  quaternions to identity. Zero initialization produces nonfinite positions
  when those points are later split. This is a training bug fix, not a renderer
  or checkpoint format change. Its minimal one-line hunks require
  `git apply --unidiff-zero --check` followed by `git apply --unidiff-zero`.
  Apply after the STG compatibility patch; do not reapply to a patched checkout.
  Validate with `scripts/verify-stg-growth.py --require-valid`.
- [nopo4d-python314.patch](nopo4d-python314.patch), NoPo4D revision
  `cb54c9349792d474aa541274842e0fadf1d807c7`: NumPy 2 requirement.
- [da3-python314.patch](da3-python314.patch), Depth Anything 3 revision
  `41736238f5bced4debf3f2a12375d2466874866d`: Python 3.14 and NumPy 2
  metadata; the missing runtime dependency `addict` is declared and Open3D
  is in a `benchmark` extra. Open3D is imported only by `depth_anything_3/bench/` modules,
  outside the NoPo4D inference import path. The `all` extra still includes
  benchmarks and therefore cannot resolve on this Python version.
  Run `bash scripts/setup-nopo4d.sh` to apply these two patches to their
  respective checkouts and install with full dependency resolution.

Build and execution status is recorded in the
[pretrained experiment report](../docs/experiments/pretrained-validation.md).
The browser conversion helper verifies the pinned worker's hash before running
it. Compatibility patches do not change the renderer's math; the separately
identified EMS fix changes initialization of newly added training points.

The splaTV patch targets upstream revision `8b313fe`. Its bundle consists of
[splatv-time-controls.patch](splatv-time-controls.patch) and
[time-controls.js](splatv/time-controls.js). The JavaScript asset is our local
implementation; the patch wires it into the existing HTML and time uniform.
The Gaussian shader, sorting, PLY conversion, and file format remain upstream code.

Apply from the repository workspace described in the [experiment guide](../docs/pretrained-experiments.md):

```bash
git -C "$GS_WORK/splaTV" apply --check "$GS_ROOT/patches/splatv-time-controls.patch"
test ! -e "$GS_WORK/splaTV/time-controls.js"
cp -n "$GS_ROOT/patches/splatv/time-controls.js" "$GS_WORK/splaTV/time-controls.js"
git -C "$GS_WORK/splaTV" apply "$GS_ROOT/patches/splatv-time-controls.patch"
```

Run these steps once on the pinned checkout. If `--check` fails, stop: inspect
`git diff` and `git rev-parse HEAD` there. A reverse check with
`git apply --reverse --check` can identify an already applied patch; do not apply
it twice or reset a modified checkout. The copied asset must also match this bundle.

The viewer starts paused at zero. Play advances linearly through 0–1, wrapping at
one. Scrubbing pauses; Play resumes from that value. Restart returns to zero and
pauses. The default five-second viewing cycle is adjustable from 0.1 to 3,600
seconds; it does not establish the original capture duration. Hiding the browser
tab pauses playback. Camera navigation remains available while time is paused.

The panel consumes keyboard, mouse, touch, and wheel events so editing a time
value does not navigate the camera. Focusing the panel clears previously held
camera keys and stops the upstream automatic camera carousel.

Run deterministic clock checks from this repository:

```bash
node --test tests/splatv-time-controls.test.cjs
```

Manual acceptance: load a real scene, play/pause, scrub to 0/0.5/1, orbit while
paused, resume without a time jump, change cycle duration, restart, edit the
duration using number/arrow keys, and switch away from the tab. Check camera
alignment after loading a different camera JSON and converted model. A clock
unit test does not establish WebGL rendering quality or GPU performance.
