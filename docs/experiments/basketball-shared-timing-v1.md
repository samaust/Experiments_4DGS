# Plan 007: short-window audit and shared-trajectory admission

Status: **blocked on inadequate multiview support before spline fitting**.
Sixteen of the fixed 72 edges have fewer than 12 eligible groups in at least one
deterministic half. The plan explicitly requires stopping here. No timing
candidate was selected; the spline optimizer, independent spline assessment and
selection reevaluation remain deferred. This is an adapted research investigation,
not a reproduction of an author's complete pipeline.

The [previous selection failure](basketball-timing-selection.md), including its
36/72 passing edges and consumed selection marker, remains unchanged. This
attempt uses fitting frames 50–149 only. Selection frames 150–199 were already
observed historically but were not reevaluated here. Final frames 200–249 remain
untouched, and no final consumption marker, initialization or training was created.
All 34 cameras, accepted calibration and scale, the 72-edge graph, held-outs
0/10/20/30 and the 0.25-frame requirement remain fixed.

## Estimator audit

The [frozen configuration](../../configs/basketball-rev2/timing-shared-v1.json)
binds calibration/profile/source-video/static-marker provenance, the prior graph,
scale evidence, historical estimators and the investigation deadline. Source
videos were hashed without decoding reserved frames. The audit uses the existing
hash-verified saved fitting tracks, including their historical mixed extraction
resolutions; the association experiment below freshly extracts all cameras at
the same native resolution.

Both historical score definitions were tested on fitting windows 50–99, 100–149,
50–74, 75–99, 100–124 and 125–149. For each matched track pair, inject
−0.75, −0.25, −0.10, 0, 0.10, 0.25 and 0.75 frames using
`B_new(f) = B_original(f − delta)`. Matching is held fixed across injections.
The expected lag change is **+delta**. Both interpolation endpoints remain
inside the current window, with identical support across injections and lag
hypotheses. No extrapolation is used.

All **6,048 unchanged full-search curves are unsupported**. A 50-frame window
spans only 49 frame intervals; supporting both −25 and +25 on the same reference
samples requires at least 50 intervals even before requiring 15 samples per
track. The 25-frame windows cannot satisfy this either. Missing lag estimates,
recovery errors and coverage are reported as null, not zero or synchronization.
This establishes a limitation of these estimators' support policy, not proof that
short-window timing is impossible with a different identifiable model.

A separately predeclared, **nonqualifying** local diagnostic searches ±2 frames
around each frozen fitting lag at 0.05-frame spacing. This adds 6,048 curves and
retains the existing score thresholds, 12-track minimum, 15 samples, 0.05-pixel
optimum gap, one-frame gap exclusion and 256 seed-0 track bootstrap resamples.
It cannot admit an edge or replace the ±25-frame fitting search. The following
errors summarize only identifiable relative comparisons, including zero-shift
controls; the seven injections reuse observations and are not independent trials.

| Window | Score | Score-gate passes / curves | Identifiable relative comparisons | Median / p95 absolute recovery error (frames) | Conditional interval coverage |
| --- | --- | ---: | ---: | ---: | ---: |
| 25 frames | Absolute epipolar | 323 / 2,016 | 1,815 | 0 / 0.20 | 99.72% |
| 25 frames | Temporal bias | 1,510 / 2,016 | 1,855 | 0 / 0.10 | 98.60% |
| 50 frames | Absolute epipolar | 198 / 1,008 | 951 | 0 / 0.15 | 99.47% |
| 50 frames | Temporal bias | 731 / 1,008 | 959 | 0 / 0.10 | 98.96% |

Coverage here asks whether an injected curve's interval covers the **estimated
unshifted lag plus delta**. It conditions on that baseline point estimate and is
not absolute-ground-truth coverage or coverage of a bootstrapped lag difference.
A score-gate pass also does not supply the independent spatial, graph or
multiview assessment needed for production acceptance. The
[audit summary](basketball-shared-timing-v1/audit-summary.json) preserves every
edge/window/score/search combination, support, ambiguity and uncertainty counts,
speed and acceleration summaries. The full local raw artifact retains all
curves, per-track sample counts, intervals and injection-level errors; its hash
and location are bound in the [evidence inventory](basketball-shared-timing-v1/evidence.json).

## Synthetic safeguards and identifiability

The [378 synthetic curves](basketball-shared-timing-v1/synthetic-audit.json) use
explicit calibrated rectified cameras, fixed-depth 3D trajectories, constant
velocity, acceleration and sinusoidal direction changes. Known offsets are
applied in continuous trajectory time before projection, with observation noise
of 0, 0.25 or 0.5 pixels in the 960×540 convention. This supplies absolute timing
truth independently of the real-data resampling test. Lengths 25 and 50 retain
the same unsupported full search; length 100 supplies supported positive and
negative controls. Calibration-cloud points are never dynamic observations.

For rectified cameras at constant depth Z and constant vertical velocity vy,
the signed Sampson residual is, up to essential-matrix sign,
`e(f, lag) = focal * vy * (lag − delta) / (sqrt(2) * Z)`.
It is independent of frame f. Subtracting a per-track constant removes all timing
information. A degenerate bootstrap interval at an arbitrary minimizer does not
rescue the flat curve; its ambiguity gate must reject it.

All **42 noiseless safeguards pass**: identifiable positive controls recover the
correct offset sign within 0.05 frames, and every constant-velocity temporal-bias
negative control is rejected as ambiguous. Noise results retain actual errors,
interval coverage and failures; no thresholds were tuned to improve them.
Additional tests exercise noisy fractional recovery, corrupted tracks, exact
agreement with historical score functions, and distortion/pose round trips using
the accepted calibration.

## Multiview admission result

Fresh fitting extraction uses native 1920×1080 masked SIFT and forward/backward
LK, seeds 50/60/70/80, the existing adjacent-patch correlation threshold 0.7,
60-frame minimum track length and unchanged motion gates. Coordinates convert
through `(xy + 0.5) / 2 − 0.5`, followed by the existing radial undistortion.
Original frame IDs and camera IDs are preserved. All **5,785 tracks** meet this
same extraction policy across the 34 cameras.

Before association, overlapping same-camera duplicates are merged when at least
eight shared frames remain within one calibration pixel throughout their overlap.
Merged observations average shared pixels and retain all source track IDs; the
longest member supplies the descriptor. No duplicates met this rule in this run.
The policy was frozen before extraction and was not adjusted after seeing support.

Matching uses mutual nearest RootSIFT descriptors with the 0.8 ratio test in
both directions along the fixed graph. Connected components with more than one
trajectory from a camera are rejected wholesale, independent of timing. Groups
require at least three **training** cameras; held-out observations cannot satisfy
that count. Sixteen conflicting components and 3,240 components with fewer than
three training cameras were rejected. There are **351 eligible groups**.

A seed-0 permutation assigns whole groups, including all their camera observations,
alternately to optimization and assessment. No group is split or reassigned to
repair edge support. **56/72 edges pass admission; 16 fail**:

| Edge | Optimization groups | Assessment groups |
| --- | ---: | ---: |
| 0–1 | 11 | 17 |
| 9–10 | 6 | 16 |
| 9–11 | 11 | 18 |
| 10–11 | 5 | 13 |
| 10–12 | 3 | 11 |
| 11–12 | 8 | 16 |
| 12–13 | 6 | 15 |
| 12–14 | 5 | 8 |
| 13–15 | 10 | 13 |
| 14–15 | 8 | 6 |
| 15–19 | 14 | 11 |
| 16–17 | 15 | 11 |
| 16–20 | 14 | 9 |
| 26–30 | 11 | 17 |
| 26–31 | 8 | 16 |
| 29–33 | 13 | 10 |

[All-edge/per-camera support](basketball-shared-timing-v1/support.json),
[group membership and rejected associations](basketball-shared-timing-v1/groups.json)
and the [terminal result](basketball-shared-timing-v1/result.json) are published.
Raw and merged pixel observations, descriptors, original IDs and hashes remain
in the inventoried local association directory. These are group-presence counts
before geometric/spatial trajectory validation, so they are upper bounds on
support that could survive subsequent fitting checks. Even these counts fail.
No graph pruning, alternate split seed, support reduction or additional
configuration search was attempted after this mandatory stopping condition.

## Implementation boundary and prospective model

The versioned [stage CLI](../../scripts/basketball_shared_timing_v1.py) implements
`audit`, `associate` and `package`, each with a frozen configuration, hashed
predecessors where applicable and fresh output directories. The native extractor
is separately versioned. The CLI exposes `fit`, `assess` and `select` as guards:
they reject blocked predecessors and have no production implementation. They do
not write success-shaped placeholders. The
[report packager](../../scripts/basketball_shared_report_v1.py) verifies the
completed chain and exports compact evidence.

The six prospective cubic B-spline configurations are frozen: knot spacing 5 or
10 frames crossed with acceleration weights 0.1, 1 or 10. The intended solver
uses sparse SciPy least squares, fixed calibration/scale, source seconds, rig
diameter normalization, one-pixel soft-L1 reprojection loss and separately
sample-normalized mean squared acceleration. Starts would be current fitting
offsets, zero offsets and seed-0 ±0.5-frame perturbations, anchored at camera 1
and bounded by ±25 frames. Held-out offsets would use frozen training trajectories.
**Zero configurations were fitted.** No spline parameters, optimization traces,
independent nuisance-fit edge curves or group-bootstrap intervals exist, because
admission failed first. Tests of the future spline optimizer and held-out fitting
isolation are consequently deferred; the present isolation test concerns the
training-camera support requirement only.

Continuing to those stages requires a new authorized investigation that resolves
the evidenced association/support problem while retaining independent assessment.
Under this plan the completion boundary is the documented blocker. No candidate
or one-use final-validation protocol can be frozen from this evidence.

## Resources, commands and verification

The existing CPU calibration environment was reused without downloads or new
dependencies. Audit, association and package workers used **127.860076 wall
seconds** in total (59.014083 + 67.600420 + 1.245573). The report snapshot records
573.960630 seconds since configuration freeze, including implementation, tests
and a repaired 0.465799-second startup error, well below four hours. Initial
read-only repository inspection preceded that freeze. The
[resource record](basketball-shared-timing-v1/resources.json) preserves the failed
attempt and accounting distinction. GPU and Basketball training charges are zero;
the historical GPU ledger hash matches the prior selection evidence.

**97 Basketball tests, seven budget tests and three SelfCap regressions pass**.
The Basketball total includes 13 new tests for sign/recovery, constant-velocity
ambiguity, noisy data/outliers, association conflicts, duplicate leakage,
training-camera admission, pose/distortion, interpolation boundaries, independent
cycle inconsistency and hash/role tampering. Exact score comparisons also verify
the vectorized audit against the historical implementation. Source and output
hashes, local links in the changed documentation, and `git diff --check` pass.
Test logs and exact stage commands are in the evidence inventory.

```bash
.local/envs/calibration-global/bin/python scripts/basketball_shared_timing_v1.py audit --config configs/basketball-rev2/timing-shared-v1.json --output .local/calibration/basketball-rev2/shared-v1/audit
.local/envs/calibration-global/bin/python scripts/basketball_shared_timing_v1.py associate --config configs/basketball-rev2/timing-shared-v1.json --predecessor .local/calibration/basketball-rev2/shared-v1/audit --output .local/calibration/basketball-rev2/shared-v1/associate
.local/envs/calibration-global/bin/python scripts/basketball_shared_timing_v1.py package --config configs/basketball-rev2/timing-shared-v1.json --predecessor .local/calibration/basketball-rev2/shared-v1/associate --output .local/calibration/basketball-rev2/shared-v1/package
```

These are the executed commands, not instructions to overwrite the frozen run.
Fresh outputs are mandatory and the configuration retains its original deadline;
reproduction after expiry needs a separately versioned investigation. Exit code
1 from association/package denotes the scientific blocker, not a permission error.
