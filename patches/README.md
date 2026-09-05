# Local upstream patches

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
