# Basketball full-resolution cycle refinement

Eight of ten newly measured connections pass. **22–26 fails full-pair timing
uncertainty and disjoint-track agreement; 24–27 fails disjoint-track agreement.**
The initial attempt's extra all-target rule records a failed replacement attempt.
The 72 independently passing edges nevertheless form a connected, bridge-free
34-camera graph with maximum signed cycle closure **0.25 frames**.

Before accessing reserved data, a [separate selection policy](../../configs/basketball-rev2/timing-selection.json)
admitted those 72 passing edges using Plan 005 revision 2's actual graph criteria.
The all-target rule was an implementation choice stricter than the plan; it was
explicitly superseded for fitting-candidate admission. Failed edges remain failed,
no old-target fallback is used, and no per-edge uncertainty or cycle threshold
changes. This uses fitting outcomes to freeze a candidate, not reserved outcomes
to choose a graph. [Reserved selection results](basketball-timing-selection.md)
record the subsequent gate. Calibration and estimated scale remain accepted.

## Frozen method

The user authorized full-resolution tracking and finer fractional refinement
without changing the 0.25-frame gate. The
[protocol](../../configs/basketball-rev2/timing-cycle-refinement.json) was frozen
before new extraction and fitting. It targets all ten distinct edges in the two
previously failing loops, using cameras 22, 23, 24, 25, 26, 27, 29, 30 and 33.
No edge is selected for replacement by its new lag or cycle residual.

Native 1920×1080 SIFT/LK tracking reuses the successful appearance-discontinuity
policy from the [earlier targeted recovery](basketball-advertising-recovery.md).
It yields 167, 201, 193, 179, 178, 163, 151, 152 and 156 retained trajectories in
the nine target cameras, respectively. All observations remain in frames 50–149.
Other camera tracks are hash-verified copies of the previous tracks. Dynamic
masks, moving-track support, precise radial undistortion and the integer-center
conversion `(xy + 0.5) / 2 - 0.5` remain unchanged.

The full integer search remains −25…25 frames. The local fractional grid changes
from 0.05 to **0.01 frames**, while retaining every integer hypothesis. Every
hypothesis uses the same full-search-supported observations. Minimum full-pair
support remains 12 tracks and 15 samples per track; original spatial bias,
distinct-optimum and bootstrap halfwidth ≤0.25-frame gates remain unchanged.
Finer sampling is numerical refinement, not a claim of 0.01-frame accuracy.

For an additional consistency check, the full-search correspondences are split
into two disjoint groups using seed 0. Each needs at least six tracks and an
identifiable, nonboundary optimum; their point estimates must agree within
0.25 frames. The groups' own bootstrap intervals are retained, but their reduced
sample size does not replace the full-pair uncertainty requirement. These groups
contain different correspondences, not necessarily independent physical objects,
and do not replace the later independent temporal validation.

All ten target entries are replaced by the new measurements, including failures.
There is no old-target fallback and no pruning chosen by cycle closure. Requiring
every target replacement to pass was declared in this attempt's protocol; it is
an additional attempt-level requirement, distinct from the graph check in Plan
005 revision 2. It was not introduced after observing the two failures.

## Results

| Edge | Supported tracks | New lag | Full-pair bootstrap 95% interval | Group disagreement | Result |
| --- | ---: | ---: | --- | ---: | --- |
| 22–23 | 54 | 0.00 | [−0.06625, 0.03] | 0.00 | Pass |
| 22–24 | 36 | 0.08 | [−0.12, 0.13] | 0.02 | Pass |
| 22–26 | 35 | −0.23 | [−0.45, 0.22] | 0.32 | Fail |
| 23–25 | 41 | 0.09 | [−0.09, 0.13] | 0.04 | Pass |
| 24–27 | 30 | −0.15 | [−0.33, 0.05] | 0.29 | Fail |
| 25–26 | 41 | −0.01 | [−0.08625, 0.10] | 0.13 | Pass |
| 26–30 | 31 | 0.11 | [−0.34625, 0.14] | 0.15 | Pass |
| 27–29 | 38 | 0.05 | [−0.22625, 0.11] | 0.08 | Pass |
| 29–33 | 29 | −0.10 | [−0.31625, 0.13625] | 0.19 | Pass |
| 30–33 | 32 | −0.07 | [−0.23625, 0.14] | 0.18 | Pass |

All timing quantities are source frames, with `track_b(frame_a + lag_ab)`
corresponding to `track_a(frame_a)`. Complete search curves, group membership,
bootstrap intervals and spatial residuals are in the
[fit evidence](basketball-cycle-refinement/fit.json). The
[comparison](basketball-cycle-refinement/comparison.json) retains previous and new
estimates rather than selecting whichever closes a loop better.

For 22–26, the full-pair bootstrap halfwidth is **0.335 frames**, exceeding 0.25;
the two groups estimate −0.42 and −0.10 frames. For 24–27, the full-pair halfwidth
is 0.19 frames, but the groups estimate −0.17 and 0.12 frames. These failures
identify unreliable connections under this estimator, not a uniquely faulty camera.

The [combined result](basketball-cycle-refinement/result.json) has 72 passing
edges, all 34 cameras connected, no bridges, maximum cycle closure 0.25 frames
and maximum least-squares edge residual 0.138274 frames. The
[cycle inventory](basketball-cycle-refinement/cycle-diagnostics.json) records that
diagnostic graph. `status` remains `blocked` and `offsets` remains null because
the two target replacements fail. Diagnostic global offsets are not a validated
timing export. This file preserves the initial all-target outcome; the subsequent
72-edge fitting candidate is separately frozen in the reserved-selection record.

## Resources, verification and continuation

The worker used **70.731054 CPU wall seconds** and zero GPU seconds. The historical
GPU ledger remains 1,137.541712 seconds charged and 27,662.458288 seconds available;
the conditional extension and every method's two-hour Basketball training
allocation remain unused. No new dependency, model or weight was introduced.

**81 Basketball tests, seven budget tests and three SelfCap regressions pass**.
New tests cover the finer full-search grid, replacement without fallback, known
fractional recovery in disjoint groups and rejection of group disagreement.
Immutable calibration/profile/source-video/static-marker hashes, saved source and
artifact hashes, local Markdown links and `git diff --check` pass. The
[evidence inventory](basketball-cycle-refinement/evidence.json) records per-camera
track counts, run resources and test logs.

```bash
.local/envs/calibration-global/bin/python scripts/basketball_timing_cycle_refinement.py --protocol configs/basketball-rev2/timing-cycle-refinement.json --audit .local/calibration/basketball-rev2/provenance/result.json --output .local/calibration/basketball-rev2/cycle-refinement/run
.local/envs/calibration-global/bin/python scripts/basketball_timing_cycle_package.py --workspace .local/calibration/basketball-rev2/cycle-refinement --output docs/experiments/basketball-cycle-refinement
```

Exit code 1 records the declared fitting failure, not a sandbox or permission
failure. Runs require fresh output paths. The next scientific recovery option
depends on the separately frozen reserved-selection result. The explicit
fitting-candidate policy revision above permits that evaluation without lowering
the 0.25-frame gate. This refinement worker reads no frames 150–199, 200–249 or
downstream frames 0–49. The subsequent selection worker reads only 150–199.
Shared inputs,
initialization, training and evaluation remain unrun. MoE-GS and FreeTimeGS++
retain their independent implementation blockers.
