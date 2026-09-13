# Geometry diagnostics and aggregation implementation

Implemented for Plan 031 and the frozen
[automated-annotation amendment](annotation-amendment-001.json). This is source
and CPU fixture evidence. No model inference, GPU execution, setup build,
download, host probe, staging or commit was performed by this subtask.

Owned implementation files:

- `scripts/vipe_benchmark/diagnostics.py`
- `scripts/vipe_benchmark/aggregation.py`
- `tests/test_vipe_benchmark_diagnostics.py`
- `tests/test_vipe_benchmark_aggregation.py`

Historical geometry, triangulation, training membership guards, normalization
parents and component thresholds remain unchanged. The parent agent owns
controller/runtime integration, annotations and milestone commits.

## Diagnostic runner interface

`diagnostics.run(request, output, config)` creates a fresh output directory for
one reserved job. Requests carry `job_id`, explicit file records for `inputs`,
`segmentation`, `motion`, `neighbors`, and `roma: {checkout, weights}`. Combined
jobs additionally require `finalists`, `scale_fit` and `scale_check`. Their new
scene freeze verifies current matching fit/check component hashes and the exact
frozen-fit record. Distinct job configuration records may differ between fit
and check; their component identity and component hash must match.

The runner derives cameras/points from the frozen accepted map. It scales XYZ,
translations and centers consistently, rebases normalization, checks projection
invariance and records physical/normalized time and velocity conversions.
Intrinsics gain exactly one half-pixel correction at the RoMa boundary.

The nine isolated arms are explicit. Primary jobs process 64 contexts and 192
directed edges in pair/reference/neighbor order. Native execution calls the
existing pinned offline RoMa loader and local `triangulate_points` with
`device='cuda', dtype=torch.float32`; no CPU fallback is exposed. Sampling,
coarse person association, person crops, geometric acceptance, LK and multiview
velocity use the historical helpers. Static pair checks use the union of the
two motion masks. Unknown/invalid semantic labels cannot become static support.

Each edge saves attempted candidates, numerical and individual gate flags,
accepted support, semantic classes, positions/velocities, reference/candidate
coverage, parallax, shortages, crop evidence, timing and an immutable archive.
Context records retain union/marginal coverage and the sampling RNG state.
Summaries include equal-camera neighbor-selection evidence, reciprocal edges,
support/velocity counts, synchronized CUDA durations and allocator/reserved
peaks. Phase-boundary total-device observations are explicitly a lower bound;
the supervisor must supply its total-device monitoring and enforce exclusivity,
memory, attempt and wall limits.

R-G requires `repeat_source`, the completed G-S0 result record. It restores that
source's camera-1/pair-20 PCG64 state in the fresh worker, rather than comparing
a different sampling stream merely because both processes began with seed 0.
`compare_geometry(primary, repeat)` reports acceptance/count changes for the
three prescribed edges; pointwise disagreements are unavailable if sampled
reference coordinates differ. The repeat never contributes selection evidence.

## Aggregation interface and evidence limits

`aggregation.run(request, output, config)` implements three immutable checkpoints
inside the controller's one aggregate allocation:

1. `stage='masks'`: explicit `inputs`, `annotations`, `amendment`,
   `segmentation={S#: {calibration: record, reconstruction: record}}`, and
   `motion={M#: record}`. Produces `raw-counts.json`, `mask-metrics.json` and
   `segmentation-control.json`.
2. `stage='finalists'`: frozen `mask_metrics`, all nine `geometry` result records,
   `scales={D#: {fit: scale_record, check: scale_record}}`, component qualification
   evidence, and optional D0/D1 result records under
   `depth_controls={fit: {baseline, candidate}, check: {baseline, candidate}}`.
   Uses `inputs` for the existing depth sample lists. Saves
   `geometry-metrics.json`, `depth-control.json` and `finalists.json`.
3. `stage='final'`: frozen `finalists`, `combined` and `repeats`. Appends combined
   comparisons and repeat summaries without recomputing mask metrics. Saves
   `combined-geometry-metrics.json` and `aggregate-final.json`. Identical frozen
   combined compositions may reference the same result hash with reuse recorded.

Raw statistics cover semantic/role/static pixels, boundaries, instance matching,
tiny balls, reviewed temporal identity, static-feature and frozen-map observation
retention. Counts pool within camera before equal-camera averaging. The camera
and temporal-group bootstrap uses PCG64 seed 0, 10,000 common draws and linear
2.5/97.5 percentiles. The vectorized implementation is checked against the
existing bootstrap's estimates and paired intervals. Overlapping contexts stay
in their shared temporal group. Missing predictions generate explicit rows over
the entire required domain rather than silently reducing it. Missing strata and
undefined camera scores remain visible.

The automated schema measures frozen teacher agreement, including uncertainty
about teacher nondetections. It cannot claim human ground truth. Proxy policy
hashes must match the annotations. Unknown motion/static/role/temporal layers
produce unverified scores; no all-false placeholder becomes static truth.
Only explicitly reviewed suitable features enter annotated feature retention;
the full unmasked SIFT pool remains a separate descriptive measurement.

The existing 12-decimal finalist rules remain in use. The annotation amendment
permits only the stated unverified S2/M0 baseline defaults when required proxy
terms are unavailable. N selection remains unchanged. Missing D1/D2 gates never
substitute D3/D4. Boundary tie evidence pools semantic-foreground boundaries;
complete misses have zero F1, and empty/empty boundaries are undefined. The
parent aligned the shared boundary helper with this empty-case handling.

S1/S0 control reports compare actual captured standardized RGB, native query
logits/normalized boxes and semantic output differences. Native selected
detections are shown without guessed cross-model box associations. Missing or
incompatible intermediate arrays are unverified. They use the worker's
`row.diagnostics` NPZ records; source S0 is a comparator, never annotation truth.

`compare_depth(first_row, second_row, sample_input_row)` supplies R-D image and
frozen sparse sample/per-camera scale-ratio differences. `compare_depth_control`
applies it to D0/D1 at the same prescribed fit/check frame. These are descriptive
comparisons, with zero extra full-rig scale evaluations or refits. Physical
accuracy remains unverified throughout.

## Validation

CPU checks use `.local/envs/stg-colmap/bin/python`; fixtures contain synthetic
arrays and explicit fake model/solver boundaries. No GPU probe or real matcher
was used. The native solver-call test verifies the CUDA float32 arguments by
mocking the solver, while independent float64 fixtures check accepted geometry.

Validated suites:

| Suite | Tests |
| --- | ---: |
| `test_vipe_benchmark_diagnostics.py` | 7 |
| `test_vipe_benchmark_aggregation.py` | 14 |
| `test_vipe_benchmark_metrics.py` | 12 |
| `test_vipe_benchmark_contracts.py` | 15 |
| `test_basketball_temporal_geometry.py` | 4 |

The new fixtures exercise separate numerical/depth/reprojection/parallax/support/
motion rejection stages; invalid reference masks; sampling shortages; grid-center
conventions; scene scaling; three-edge repeat serialization and RNG restoration;
proxy unknowns; missed tiny balls; role precision bounds; empty boundary F1;
paired bootstrap parity; crossing groups; full annotation-domain missing output
accounting; immutable selection checkpoints; source scale binding; sparse depth
ratio differences; and actual-versus-unavailable native intermediate comparisons.

These 52 CPU checks validate implementation behavior. Native runtime qualification,
measured model/geometry quality, actual resource peaks, the complete executed
matrix and final success-criteria assessment remain the parent workflow's work.

## Integration follow-up: final static artifacts and device admission

The parent authorized two follow-up changes after the bounded execution review.
Geometry now calls CUDA initialization explicitly and raises `PermissionError`
on absent device access or failed driver/device initialization, before loading
the matcher. This lets the controller apply the required access-failure stop
instead of consuming later candidates on the same unavailable device.

Final static PNG assembly now belongs to the existing masks aggregation stage.
It uses saved instance labels and changing masks; no motion algorithm runs again.
The full primary output domain is assembled independently of the annotated
subset: S0–S4 with M0, plus S0 with M1/M2, giving 9,450 PNGs when every prerequisite
is available. M0's S0 comparison aliases the one S0/M0 assembly. Reconstruction
unions the two changing masks from each exact tracker pair; calibration uses its
own changing mask. All outputs use `255` for valid, semantically unmasked,
unchanging pixels and `0` elsewhere.

`aggregate-masks/final-static-masks.json` records every expected method/identity,
the generated/unavailable counts and each actual PNG hash. Each generated row
binds source RGB, K, grid and validity; its segmentation result, instance artifact,
semantics hash and full source-row hash; and its motion result plus both exact
pair-changing source rows where applicable. Missing motion/pair counterparts
produce explicit unverified entries rather than static background. These are
derived component outputs and make no annotation/ground-truth claim.

The manifest file record appears as `final_static_masks` in both
`mask-metrics.json` and `aggregate-masks/result.json`. Component result indexing
also rejects a result assigned to another method. The root controller owns
segmentation-worker conversion to separately named `semantic_static` outputs.

Follow-up validation passed 17 aggregation and 8 diagnostics tests (25 total).
New CPU fixtures cover complete all-output static assembly, exact parent hashes,
pair-union behavior, M0 aliasing, missing pair evidence, changed motion RGB/grid,
all 9,450 unavailable outputs and pre-model CUDA access/init failure handling.
The first run exposed only a fixture glob that did not descend through the
explicit identity directories; the corrected fixture and implementation pass.
No native model, GPU, download or build was executed by this follow-up.
