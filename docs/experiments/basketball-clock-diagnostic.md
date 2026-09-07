# Basketball clock synchronization diagnostic

The visible green game-clock display independently prefers **zero whole-frame
lag on all ten connections** in the two failing timing loops. It does **not**
identify a camera responsible for the subframe disagreement. The existing
0.30-frame cycle failures remain above the unchanged 0.25-frame gate, so timing
selection/final validation and downstream experiments remain blocked.

## Automatic clock extraction

The user identified the clock's tenths display as a possible independent timing
cue. We inspect only original fitting frames 50–149 for cameras
22, 23, 24, 25, 26, 27, 29, 30 and 33. These are the cameras in the two failed
cycles recorded by the [native-track recovery](basketball-advertising-recovery.md).
The green game-clock row includes tenths; the red shot-clock row displays whole
seconds in the inspected window. The diagnostic uses green emission, not red digits.

The first [color-only locator](../../configs/basketball-rev2/timing-clock.json)
selected a green court logo. Visual inspection of its
[automatic boxes](basketball-clock-diagnostic/rejected-regions.jpg) exposed the
mistake. This run is explicitly [rejected](basketball-clock-diagnostic/rejected-locator.json),
and none of its lag estimates counts as clock evidence. Its initial source,
protocol, outputs and resource accounting remain preserved locally.

The [corrected locator policy](../../configs/basketball-rev2/timing-clock-display.json)
was frozen before re-extraction. At fitting frame 100 it requires bright green
emission on a dark background (at least 40% of the region has all channels below
100), selects the rightmost main component with at least 500 green pixels, and
extends 40 native pixels rightward to include the separated tenths digit. It
uses no manually annotated coordinates. The region stays fixed over frames
50–149. [Region previews](basketball-clock-diagnostic/regions.jpg) confirm the
corrected boxes cover the green clock row in all nine cameras.

[Camera 25](basketball-clock-diagnostic/camera25-clock.jpg) and
[camera 33](basketball-clock-diagnostic/camera33-clock.jpg) contact sheets preserve
every observed digit state with its original frame ID. Equivalent sheets for
all nine cameras are saved locally and hash-bound. The software measures content
changes; it does not claim OCR readings or assign exact physical transition times.
The boxes appear to cover the corresponding clock face, but physical-face identity
and face-specific refresh delays have not been geometrically or electronically
validated.

## Timing comparison and limits

For each crop, the signal is the RMS consecutive-frame change of positive green
chroma `max(G - max(R, B), 0)`, normalized by its fitting-window 90th percentile.
Each edge compares the same reference transition labels 76–124 over the full
integer lag search −25…25. At the extremes, both images supporting every signal
sample remain within frames 50–149. Five-frame block resampling gives 1,000
bootstrap integer estimates with seed 0. The sign convention matches motion
timing: camera B at `frame_A + lag` corresponds to camera A.

All ten comparisons choose lag **0 frames**, and every integer bootstrap interval
is **[0, 0]**. The gap to the next integer candidate ranges from 0.0601 to 0.1031
in normalized mean absolute signal difference. These are diagnostic results,
not a newly defined timing acceptance threshold. Full signals, candidate curves,
region boxes and normalization scales are in the
[result](basketball-clock-diagnostic/result.json); the
[comparison](basketball-clock-diagnostic/comparison.json) includes the previous
motion lag for every edge.

This result does not flag a whole-frame discrepancy in a particular camera. It
does not prove exact synchronization or validate zero subframe offsets. A display
change observed between adjacent source images is interval-censored: equal
transition-frame labels can still permit nearly one frame of relative phase
without an exposure/refresh model. A bootstrap restricted to integer candidates
cannot measure that uncertainty. Repeated transitions are not independent
subframe phase measurements, and display-face delays remain uncalibrated.

Consequently, these observations cannot determine whether the following failures
come from a particular camera, motion correspondence errors, or smaller systematic
timing biases:

- **25–23–22–26–25:** 0.30 frames.
- **29–27–24–22–26–30–33–29:** 0.30 frames.

The implementation exports neither accepted clock offsets nor camera blame. It
does not replace motion edges with zero or change the gate. The current scientific
blocker is insufficient independent subframe evidence to resolve these loops.
Further recovery would require stronger motion evidence on the loops or a
validated display/exposure timing model; whole-frame clock agreement alone is
insufficient. This is the declared diagnostic stopping condition.

## Resources and verification

The rejected locator run used 8.186714 seconds and the corrected run used
8.288856 seconds. After adding an explicit detection-frame role guard, a fresh
verified run used 8.226229 seconds and reproduced the corrected signals and
curves exactly. Total: **24.701799 measured worker seconds**, all CPU. All three
runs and both earlier source snapshots are retained. Preview creation and review
are separate from these worker measurements. No GPU job was requested;
GPU and training charges remain unchanged. The original ledger still has
1,137.541712 seconds charged and 27,662.458288 seconds available. The conditional
extension and all per-method two-hour Basketball training budgets remain unused.

**77 Basketball tests, seven budget tests and three SelfCap regressions pass**.
New tests cover green-emission isolation, automatic display filtering, known
integer-lag sign, periodic ambiguity, weak signals and role boundaries. The
[evidence inventory](basketball-clock-diagnostic/evidence.json) records source,
output, preview and test-log hashes. Accepted calibration, source videos, profile
and static validation marker were hash-checked; calibration and estimated scale
remain unchanged. Local Markdown links and `git diff --check` pass. No new
dependency, model, weight or network access was needed.

```bash
.local/envs/calibration-global/bin/python scripts/basketball_timing_clock.py --protocol configs/basketball-rev2/timing-clock-display.json --audit .local/calibration/basketball-rev2/provenance/result.json --output .local/calibration/basketball-rev2/clock-diagnostic/display-verified
.local/envs/calibration-global/bin/python scripts/basketball_timing_clock_package.py --workspace .local/calibration/basketball-rev2/clock-diagnostic --output docs/experiments/basketball-clock-diagnostic
```

Fresh output paths are required for reruns. Exit code 1 denotes the diagnostic's
inability to validate subframe timing, not a permission failure. Frames 150–199,
200–249 and downstream frames 0–49 were not opened. Shared inputs, Gaussian
initialization, training and evaluation remain unrun; MoE-GS and FreeTimeGS++
retain their independent implementation blockers.
