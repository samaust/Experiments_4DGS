# Basketball targeted motion and advertising recovery

Subsequent [clock diagnostic](basketball-clock-diagnostic.md): all ten connections
in the failed loops prefer zero whole-frame lag. This does not resolve their
subframe disagreement or identify a responsible camera. The native-motion
results below remain unchanged.

The targeted fit connects **all 34 cameras** and removes all four previously
unvalidated bridges. The full graph remains **blocked by two 0.30-frame cycle
closures**, above the unchanged 0.25-frame gate. Calibration and estimated scale
remain accepted. Timing selection/final validation and downstream work have not run.

## Frozen attempt and advertising observation

The user identified changing perimeter advertising as a potential timing cue.
The [declared protocol](../../configs/basketball-rev2/timing-advertising.json)
uses only fitting frames 50–149 and targets cameras 7, 8, 12, 14 and 15. The
[frozen record](basketball-advertising-recovery/frozen.json) precedes new track
extraction and fitting. Accepted calibration, source videos, profile and static
validation marker hashes were checked before and after the run. No manual
annotations or static recalibration were used.

[Fitting previews](basketball-advertising-recovery/fitting-preview.jpg) at frames
50, 100 and 149 show the same visible advertisement in these five cameras.
An automatic diagnostic compares three-frame median colors before and after
each candidate boundary, using 30-pixel tiles at 960×540. A tile requires a
25-level channel change on at least half its pixels; six changed tiles trigger
a candidate. This is a general image-change detector, not a panel classifier.
It scans boundaries 53–146 so all three-frame supports stay inside the fitting
window. It cannot establish absence of all advertising transitions.

There are 314 candidate boundaries across the five cameras, including overlapping
observations of the same motion. Inspection of the strongest candidate per camera
in the [automatic tile overlays](basketball-advertising-recovery/transition-preview.jpg)
shows player motion; it does not identify a shared advertising switch. No panel
event supplies a timing constraint, and no panel simultaneity is assumed. A future
event-based fit would need automatic physical-panel correspondence and evidence
that panel update delays do not masquerade as camera offsets.

The user observation also motivates an explicit appearance discontinuity check:
native 1920×1080 dynamic-mask SIFT tracks use forward/backward LK and normalized
15×15-pixel patch correlation between consecutive tracked locations. Correlation
below 0.7 ends the track. It rejects 2,157 continuations; these include motion,
occlusion and appearance failures and are not counted as advertising switches.
The method retains the existing moving-track, minimum-length, correspondence,
full-search support and spatial-consistency requirements. Native coordinates
convert to the accepted calibration by `(xy + 0.5) / 2 - 0.5` before undistortion.

## Targeted fit and complete graph

The new extraction retains 194, 161, 174, 113 and 131 tracks in cameras
7, 8, 12, 14 and 15 respectively. Other camera tracks remain hash-verified copies
of the prior fitting tracks. One temporal-bias fit uses the unchanged ±25 integer
search and 0.05-frame fractional grid, without using image-change candidates to
narrow the search or select the answer.

| New edge | Full-search tracks | Lag (frames) | Bootstrap 95% interval |
| --- | ---: | ---: | --- |
| 7–8 | 49 | 0.00 | [−0.10, 0.05] |
| 12–14 | 20 | −0.05 | [−0.05, 0.05] |
| 14–15 | 25 | 0.00 | [−0.05, 0.00] |

All three [edge fits](basketball-advertising-recovery/fit.json) pass the existing
support, ambiguity, uncertainty and spatial-bias gates. The lag convention is
`track_b(frame_a + lag_ab)` corresponding to `track_a(frame_a)`. Pointwise
bootstrap intervals remain fitting diagnostics; they do not replace independent
temporal subsets or reserved timing validation.

Adding these three edges to the previously frozen 71-edge complementary graph
produces 74 edges. The new cycles **7–8–9–7** and **12–13–15–14–12** close at
0.05 and 0.10 frames. Camera 14 is connected and every edge now belongs to a cycle.

The complete graph check now reaches its signed-cycle gate and exposes two
failures in other parts of the rig:

- **25–23–22–26–25:** 0.30 frames.
- **29–27–24–22–26–30–33–29:** 0.30 frames.

The [explicit cycle inventory](basketball-advertising-recovery/cycle-diagnostics.json)
uses the evaluator's deterministic breadth-first spanning tree. The maximum
least-squares edge residual is only 0.138274 frames, illustrating why the plan
also checks actual cycle closure: fitting can distribute a cycle disagreement
across edges. No edge is pruned or reweighted to manufacture a pass.

The [combined result](basketball-advertising-recovery/result.json) therefore has
`status: blocked` and `offsets: null`. Its diagnostic offsets are not accepted
camera timing. This meets the declared attempt's stopping rule. Further recovery
would need independent fitting evidence for these inconsistent cycles, followed
by the unchanged reserved timing checks. The original disconnected-camera and
bridge blockers are resolved, but synchronization acceptance is still incomplete.

## Resources, verification and reproduction

This is a CPU-only SIFT/LK and image-difference implementation; no GPU inference
was requested or substituted. The run took **39.737675 seconds**. GPU charge is
zero, within the proposed 1,800-second GPU cap. The historical ledger remains
1,137.541712 seconds charged and 27,662.458288 seconds available. The conditional
extension remains unused, and every method's two-hour Basketball training
allocation remains unchanged and uncharged.

**70 Basketball tests, seven budget tests and three SelfCap regressions pass**.
New tests cover native pixel centers, appearance changes, color-change tiles,
frame-role boundaries, explicit cycle closure and bridge diagnostics. Source and
artifact hashes, local documentation links and `git diff --check` pass. The
[evidence inventory](basketball-advertising-recovery/evidence.json) records logs,
resources and packaged artifacts. No new dependency or weight was introduced.

```bash
.local/envs/calibration-global/bin/python scripts/basketball_timing_advertising.py --protocol configs/basketball-rev2/timing-advertising.json --audit .local/calibration/basketball-rev2/provenance/result.json --output .local/calibration/basketball-rev2/advertising-recovery/native-fit
.local/envs/calibration-global/bin/python scripts/basketball_timing_advertising_package.py --workspace .local/calibration/basketball-rev2/advertising-recovery --output docs/experiments/basketball-advertising-recovery
```

The fit returns exit code 1 for the recorded cycle gate failure, not a permission
failure. Fresh output paths are required for reruns. The package copies the saved
fitting previews alongside numerical evidence. Prior recovery artifacts remain
historical evidence. Timing frames 150–199 and 200–249 were not opened in this
attempt; no downstream frames, image preparation, Gaussian initialization,
training or evaluation were run. MoE-GS and FreeTimeGS++ retain their independent
implementation blockers.
