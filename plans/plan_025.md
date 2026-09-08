# Plan 025 — Execution specification for Plan 024

This implements the authorized [Plan 024](plan_024.md) campaign. It does not
resume the continuous improvement loop or authorize additional scientific
attempts. Artifacts live in `docs/research/basketball-sync-pivot/`; downloaded
sources, weights, datasets and containers live under `.local/sync-pivot/` or
Docker storage. Leave user-created `.codex/` configuration uncommitted.

## Order and limits

1. Finish the source, paper and benchmark audit. Inspect all 11 seed works from
   Plan 024, counting IFID/InSynFormer as one work and MultiViewUnsynch with its
   trajectory paper as one. Search each title for forward citations and inspect
   each seed's references once. Verify edges in the citing paper, retain exact
   versions/URLs and distinguish unsuccessful discovery from absent citations.
   Read at most 20 distinct papers in detail, publication cutoff 2026-09-08.
2. Pin sources and image digests before execution. Runtime setup has a two-hour
   active-work limit; each of VisualSync, Sync-NeRF and MultiViewUnsynch has a
   separate two-hour compatibility limit and at most two setup attempts. Count
   failed attempts. Pauses for user intervention do not authorize resetting
   consumed work. Record timing and commands in campaign artifacts.
3. Validate timing interfaces and independent analytic fixtures before processing
   real timing data. Integrate only released implementations. Preserve the
   original scripts and record hashes of adaptations separately.
4. Run available benchmark pilots, then Basketball fitting and development,
   then freeze final timing, then reconstruction controls/comparisons.

One GPU job at a time. All GPU process startup, checks, failed execution and
shutdown are charged. Record reservations before launching workloads; an
interrupted workload without confirmed elapsed accounting retains its entire
reservation. GPU jobs require a wall-clock watchdog and a recorded container
name/process identifier so interruption can stop the actual workload.

| Allocation | Ceiling | Execution limits |
| --- | ---: | --- |
| Checks, learned evidence, VisualSync | 14400 s | One preprocessing pass per fit/development/benchmark window, one pair-estimation pass and one preregistered repeatability pass; one final-window evaluation after freeze. CPU audits do not consume GPU time. |
| Sync-NeRF | 10800 s | Two benchmark runs (Box and Panoptic), maximum 1800 s each; three Basketball runs, seeds 0/1/2, maximum 2400 s each. Startup included. No replacement attempts for failed scientific runs. |
| STG Full | 7200 s | Three seeds × two conditions, at most 1200 s each. If no full-rig correction, run only the three zero controls. |
| FreeTimeGS reproduction | 7200 s | Same seed/condition/time limits as STG Full. |
| Rendering, metrics, reload | 3600 s | Evaluate the largest checkpoint common to compared runs, fresh offline reload, viewpoint/time renders and metrics. |

Total ceiling 43200 GPU seconds, no transfers between allocations. Reconstruction
also charges the existing `.local/runs/plan-004-training-budget.json`, respecting
its 86400-second global and 7200-second method/scene ceilings. Preserve historical
records and stop before launching an attempt whose reservation cannot fit both
applicable ledgers. Record unmeasured user-run GPU checks separately and reserve
their time conservatively before scientific workloads.

## Audit decisions and provenance

Use `source-pins.json` for the three initially downloaded revisions and the
VisualSync original scripts' hashes. Check the original archive's CoTracker and
MASt3R directories before deciding whether essential code is missing. Do not
infer missing algorithms solely from the incomplete GitHub README. Dependencies
and license identifiers must come from the actual source files; an absent
license is recorded as unspecified. Do not run the optional GPT preprocessing;
dynamic object names are people and basketball, supplied directly to segmentation.

Resolve the exact UDBD Box release and Panoptic basketball sequence, frame range,
camera split, native cadence and offset labels from original releases/papers.
An unresolved exact release is unavailable for reproduction, not a scientific
failure. Do not substitute similarly named scenes. Author schedules exceeding
the pilot caps are explicitly unreproduced; short runs establish feasibility only.

Freeze the accepted 34-camera calibration and saved scale by content hash after
checking their evidence. Preserve camera IDs 0–33 and reference 1. Metric-scale
uncertainty must remain explicit if the saved scale does not establish metric
truth. Audit saved solver diagnosis against its referenced results without
restarting any historical solver allocation.

## Timing and evaluation contract

Versioned JSON uses seconds and `corrected = source - offset`. Include all camera
IDs, reference, nullable offsets/uncertainty, evidence window, connected coverage,
provenance and operational-assumption versus estimated status. Never substitute
zero for an unobserved disconnected offset. Sync-NeRF's additive offset requires
sign conversion and inversion of its time normalization on export.

Independent continuous 3D trajectories are evaluated at physical capture times
with fractional camera offsets, then projected through known cameras. Fixtures
cover stationary/ambiguous motion, occlusion, wrong matches, disconnected graphs,
dropped frames and rate mismatch. Linear interpolation of sampled video is
sensitivity evidence only. Test signs, gauge changes, round trips, support bounds,
bad-edge robustness and disconnected coverage using CPU fixtures.

Fit Basketball on source frames 50–149; development/repeatability is 150–199.
Audit cadence and existing scoreboard observations without opening final images.
For all 561 unordered pairs retain support or explicit rejection reasons. Supply
undistorted coordinates consistent with the frozen resized calibration. Compare
learned and existing SIFT/LK evidence with the same global estimator. Report
components, bridges, cycle residuals, uncertainty, window disagreement and
leave-one-edge-out sensitivity. Only the component containing reference 1 can
receive reference-relative synchronization claims.

Select eight Sync-NeRF training cameras by accepted-calibration overlap: begin
with 1, greedily maximize new shared static-track coverage, break ties by numeric
camera ID, and exclude held-outs 0/10/20/30. If overlap evidence cannot support
selection, report this prerequisite as unresolved rather than choosing manually.
Disable `--test_optim`; never fit offsets to reconstruction test images.

Before opening frames 200–249, save a content-hashed final protocol containing
actual method parameters, candidate offsets and reporting rules. Evaluate once;
no further tuning. A failed or incomplete full-rig result still permits the
explicitly authorized zero-offset reconstruction controls.

Basketball reconstruction uses frames 0–49 at 960×540; held-outs 0/10/20/30.
Both conditions use identical source images, initialization policy and optimizer
settings. Remove the union of training images falling in corrected interval
[0.8,1.0) seconds under either condition. Preserve source IDs and continuous times,
share normalization across conditions and reject unsupported extrapolation.
Save checkpoints at 1000/2000/5000 updates within each 1200-second limit including
saving. Match comparison checkpoints; incomplete schedules are budget-limited.

## Acceptance and reporting

Run meaningful tests for the timing contract, analytic controls and adapters.
Validate resizing/undistortion, splits, complete checkpoint contents, fresh offline
reload and rendering at different views/times. Report timing distributions where
truth exists; full-image and dynamic-region PSNR/SSIM/LPIPS; temporal observations;
rendering throughput, memory and charged compute. Use seed-paired comparisons and
temporal-block resampling, not independent-pixel statistical claims.

Deliver the cited report, verified citation map, evidence/code matrix, frozen
protocol, retained results and ranked recommendation. Recommend learned correction
only with full-rig support and repeatable held-out reconstruction benefit, stating
which reconstruction methods benefit. Without repeatable benefit prefer zero as
an operational assumption. Preserve unavailable, inconclusive and budget-limited
outcomes separately from scientific failure. Passing implementation tests or
finishing this specification alone does not complete Plan 024.

Commit validated task-related milestones locally, inspect staged diffs, and
continue to unfinished authorized work. Honor user interruption and the repository
permission-failure stop/retry rules throughout.
