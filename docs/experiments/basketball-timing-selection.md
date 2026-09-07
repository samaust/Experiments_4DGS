# Basketball separately frozen timing selection

Status: the 72-edge fitting candidate was frozen before opening timing selection
frames 150–199. The measured outcome below records the completed reserved check.
Final timing validation and all downstream work remain gated.

## Fitting candidate and policy clarification

[Full-resolution refinement](basketball-cycle-refinement.md) produced eight passing
replacement edges and two failed replacements, 22–26 and 24–27. The resulting
72 independently passing edges connect all 34 cameras without bridges and have
maximum cycle closure 0.25 frames. Every retained edge passes its applicable
fitting checks; neither failed replacement is restored from the old graph.

The refinement attempt initially required all ten target replacements to pass.
That was an extra implementation restriction, not a requirement of Plan 005
revision 2. Under the user's instruction to continue, a new
[candidate/selection protocol](../../configs/basketball-rev2/timing-selection.json)
explicitly admits the independently passing full-rig graph. This policy was
frozen before any reserved timing image was decoded. It removes no camera,
changes no per-edge or cycle threshold, and does not choose edges by their cycle
residual. The failed all-target attempt remains historical evidence. Passing
fitting candidates are not accepted final timing.

## Reserved protocol

The [frozen record](basketball-timing-selection/frozen.json) contains all 72 edges,
their fitting lags, graph offsets, configuration and source hashes. A separate
[selection consumption marker](basketball-timing-selection/selection-consumed.json)
was written before extraction. It does not modify Plan 006's consumed static
validation marker or authorize final timing validation.

All 34 cameras get fresh native 1920×1080 dynamic-region SIFT/LK tracks from
frames 150–199, seeded at 150 and 160, with minimum track length 30. The nearest
frozen fitting mask at frame 149 supplies the seed region; no static calibration
selection is reopened. Using this fixed mask can miss newly occupied dynamic
regions, so support failures remain explicit. Appearance continuity, precise
radial undistortion, original IDs and integer-center resizing are preserved.

Each edge retains its frozen scoring family: 57 earlier temporal-bias edges,
four earlier absolute-epipolar edges and 11 native temporal-bias edges. Search
is ±1 frame around its fitting lag at 0.01-frame spacing. All hypotheses use the
same observations, with both interpolation endpoints inside the declared window.
The full-window minimum is 12 tracks with 15 samples, spatial bias ≤3 pixels,
distinct optimum and bootstrap halfwidth ≤0.25 frames. The optimum-gap exclusion
is 0.25 frames within this shorter search, with the same 0.05-pixel gap requirement.
This curve criterion was declared before selection, not tuned to its outcomes.

Separate half-window fits use frames 150–174 and 175–199, requiring 12 tracks
with eight supported samples per track and the same uncertainty/ambiguity gates.
Neither interpolation support nor score samples can cross a half-window boundary.
The halves must agree within 0.25 frames, and the full-window lag must agree with
the fitting lag within 0.25 frames. Every frozen edge must validate; reserved
results cannot select a smaller replacement graph. Accepted edges must also
retain full-rig connectivity, cycle support and closure ≤0.25 frames.

## Measured outcome

Fresh tracking yields **6,615 trajectories** across all 34 cameras. **36/72 frozen
edges pass all selection checks**. The passing-edge graph cannot reach cameras
12–33 from camera 1 (22 cameras), so full-rig validation fails.

Full-window rejection categories include nine ambiguous optima and nine timing
uncertainty failures. Thirty-four edges fail one or both temporal-half checks;
two have half-window point-estimate disagreement above 0.25 frames, and four
have full-window disagreement from the fitting lag above 0.25 frames. Categories
overlap. All full-window spatial-support checks pass. The complete result has
`status: blocked`, `offsets: null` and `selection_consumed: true`.

The [complete result](basketball-timing-selection/result.json) retains full-window
and temporal-half curves, support, bootstrap intervals, disagreements and graph
failures for every frozen edge. The [summary](basketball-timing-selection/summary.json)
counts failure categories separately; they can overlap. This diagnoses a failure
of the estimator to validate constant subframe timing on the reserved window,
not proof that particular cameras are physically drifting.

No timing offsets are accepted, and the separately reserved final timing frames
200–249 remain unopened. There is no new final-timing consumption marker. The
selection failure is the current evidenced blocker; no threshold relaxation,
reserved graph pruning, alternate final candidate or shared-trajectory fit is
silently substituted.

## Resources and verification

The selection worker uses **181.744905 CPU wall seconds**, following 70.731054
seconds for native fitting refinement: **252.475958 measured worker seconds**
combined. GPU charge is zero. The original GPU ledger remains 1,137.541712
seconds charged and 27,662.458288 seconds available. Its conditional extension
and all per-method two-hour Basketball training allocations remain unused.

**84 Basketball tests, seven budget tests and three SelfCap regressions pass**.
New tests verify finer fractional fitting, disjoint-group rejection, replacement
without fallback, role/interpolation boundaries, independent fitting-edge graph
admission and rejection of inconsistent or already-consumed candidates.
Calibration, profile, source-video and static-marker hashes are unchanged.
Saved source/output hashes, local documentation links and `git diff --check` pass.
The [evidence inventory](basketball-timing-selection/evidence.json) binds the run,
track files and test logs. The existing CPU OpenCV/NumPy environment is reused;
no dependency, model, asset or network access was added.

```bash
.local/envs/calibration-global/bin/python scripts/basketball_timing_reserved.py --protocol configs/basketball-rev2/timing-selection.json --audit .local/calibration/basketball-rev2/provenance/result.json --output .local/calibration/basketball-rev2/timing-selection/run
.local/envs/calibration-global/bin/python scripts/basketball_timing_selection_package.py --workspace .local/calibration/basketball-rev2/timing-selection --output docs/experiments/basketball-timing-selection
```

Fresh outputs are required. Exit code 1 denotes the recorded scientific gate
failure, not a permission failure. No downstream frames 0–49, shared input
preparation, Gaussian initialization, training or model evaluation were run.
All method allocations remain intact; MoE-GS and FreeTimeGS++ retain their
independent implementation blockers.
