# Final-render method coverage proposal 001 — REVIEW only

## Scope and authority

This proposal implements the user's clarification that motion and neighbor
methods must be compared through their effects on actual final renders, while
initial isolated review remains segmentation/depth only. Follow the
[scope amendment](qualitative-comparison-scope-amendment-001.md) and
[downstream specification](qualitative-downstream-generation.md). This is
**REVIEW**, not an executable authorization. Approval of S1 proposal003 does not
authorize these new geometry, training or render identities. No jobs, runtime
qualification, reservations or ledger writes were performed for this document.

The research component decisions select S2 and D4:

- `docs/research/vipe-alternatives/plan067-execution/human-review-001/segmentation-decision.json`,
  SHA256 `3d2ebe52be579b131a03c1aa14f388c91e05ef81a67708cbab4a62d9d3cad2f7`, 8,484 bytes.
- `docs/research/vipe-alternatives/plan067-execution/human-depth-review-001/depth-decision.json`,
  SHA256 `ab7c0808b5c5aaeb570dca1da4d16d84e1ccb580c2fe0cd01f01a53daf353c6d`, 8,825 bytes.

These decisions bind actual human reviews and package lineage. They establish
research preferences, not commercial license eligibility or final-render quality.
S1 calibration/reconstruction is not a prerequisite for this S2 comparison.

## Minimum controlled coverage

| Arm | Segmentation | Depth | Motion | Neighbors | Comparison |
| --- | --- | --- | --- | --- | --- |
| QF-B | S2 | D4 | M0 | N0 | Common reference |
| QF-M1 | S2 | D4 | M1 | N0 | M1 versus M0, neighbors held fixed |
| QF-M2 | S2 | D4 | M2 | N0 | M2 versus M0, neighbors held fixed |
| QF-N1 | S2 | D4 | M0 | N1 | N1 versus N0, motion held fixed |
| QF-N2 | S2 | D4 | M0 | N2 | N2 versus N0, motion held fixed |

Five unique trained arms share one reference; no duplicate reference training is
needed. All five retain identical source data, scene/time calibration, S2 masks,
D4 scale, reconstruction/fusion policy, renderer, seed and native training settings.
Only the declared M or N method changes in each contrast. M/N outputs change their
actual geometry/motion inputs; changing an output label alone is not a method
contrast. Point-count changes intrinsic to those methods are recorded, not hidden
by unapproved pruning/equalization. This design compares marginal effects under
M0/N0 reference settings; it does not establish interactions between arbitrary
M1/M2 and N1/N2 combinations or select a joint winner automatically.

## Existing allocations and evidence

Read-only live snapshot: 573 events, head
`1c4a11d7b2d40c8db890330d648e44d2f5e2a677043358272bc5c14f9c72eddc`.
Recheck live state after S1 work and again under reservation lock.

G-S0/S2/S3/S4, G-M1/M2, G-N1/N2, R-G and C0 are consumed diagnostic jobs.
G-S1 and C1–C3 were accounted blocked without reservation, but their identities
and historical compositions do not match these five S2/D4 arms. C1/C3 fix D1;
C2 fixes S4/D2 with additional license preferences. D4 fit/check and existing
S2/M0–M2/N0–N2 results may supply checked prerequisites; they cannot fund new
training attempts. Historical trained checkpoints consumed different initializers
and cannot be relabeled as QF arms. **All five geometry, initialization, training
and rendering identities proposed here are new allocations requiring authority.**

## Native viability and required contract

Existing G/C geometry is a diagnostic subset, not a full-rig training initializer.
Add a prospective checked initializer contract for the five QF compositions; do
not weaken `basketball_dense_fusion.load_frozen` or relabel its Plan027 artifacts.

Generation uses the 30 training cameras and nine retained training keyframes
0/5/10/15/25/30/35/40/45, each with its following frame, and three eligible
selected neighbors: 810 directed edges per arm, 4,050 across five arms. Exclude
held-out cameras and corrected-time holdout observations from initialization.
Check the actual manifest union exclusions before generating; any key failing
those exclusions blocks the frozen coverage rather than being silently dropped.
Require complete S2 reconstruction and motion rows for every consumed identity,
matching neighbor lists and current hash-bound passing D4 fit/check. Keep the
existing person-cropped RoMa recipe, 5,000 samples per edge, seed 0, camera
conventions, reprojection/parallax/support/LK gates and model/source pins.

The new adapter must bind all native result rows, source RGB, cameras, masks,
motion, neighbor membership, D4 scale, physical-to-normalized transforms, velocity
units and static/dynamic fusion rules. Reuse the audited pure fusion/native-array
validation where its contract matches; preserve view-local identity limitations.
Resolve actual coverage and scene-manifest normalization before training. Reject
missing/changed prerequisites and nonfinite or mismatched arrays. No fabricated
point, velocity or frame fills a missing result.

Use the existing FreeTimeGS native reproduction and `default_keyframe` preset,
source SHA256 `fc3e4320da73a470d0a16bcb5803f84d1bda5bdeafb000fcc39e022fbcfaaeb4`.
Freeze the complete resolved preset, optimizer/loss schedule, installed runtime,
native binaries, source checkout, initializer and manifest before execution.
Use seed 0 and target exactly 5,000 updates for every arm; this is a bounded
trained comparison endpoint, not a claim of full native convergence. If an arm
fails to reach it, retain its evidence and report that contrast unavailable;
do not compare unequal iteration counts or add a retry.

Existing native training and reload-render functions are reusable seams, not
qualified QF adapters. A CPU-tested checked controller must supply finite deadlines,
ledger accounting and cleanup; the unbounded historical study supervisor is
unsuitable unchanged. Offline existing environments/assets only: missing runtime
components or unverified source/native compatibility block launch. Research
license limitations remain explicit; no commercial/non-AGPL eligibility is implied.

## Proposed hard ceilings — not runtime estimates

| New scope | Identities | Hard seconds each | Maximum seconds |
| --- | ---: | ---: | ---: |
| Full-rig person-cropped geometry | 5 | 5,400 | 27,000 GPU |
| Initializer preparation/validation | 5 | 900 | 4,500 CPU |
| Native FreeTimeGS training to 5,000 updates | 5 | 3,600 | 18,000 GPU |
| Fresh checkpoint reload/render | 5 | 900 | 4,500 GPU |
| Media encoding/package publication | 1 | 900 | 900 CPU |
| **Total additional maxima** | — | — | **49,500 GPU + 5,400 CPU** |

The per-job ceilings reuse the earlier reviewed proposal's categories; multiplying
them by five is a new request, not an allocation already granted. These numbers
are stop limits, not predictions that dense jobs finish. No extra pilot/model smoke
job, setup build, download, retry or repeat-render allocation is included. CPU
implementation qualification remains separately accounted by its applicable scope.

Original cumulative ceilings remain 93,600 GPU seconds, 57,600 CPU preparation
seconds, 57,600 setup seconds, 60 GiB downloads and 150 GiB artifacts. Reserve
the full applicable maxima against actual remaining budgets before authority/DO.
If insufficient, return a smaller concrete proposal for review; do not borrow
unused time/attempts from consumed slots or silently change the comparison.
One exclusive GPU group, 22 GiB total device ceiling and at most eight CPU workers
remain mandatory. Training limits include loading, checkpoint publication and
cleanup, with deadline reserves defined in the concrete supervised request.

Proposed incremental artifact ceiling: **50 GiB**, also bounded by actual remaining
original artifact allowance and free disk. Current controller readings indicate
approximately 64 GiB of remaining artifact allowance before the approved S1
attempt's outputs; this is not a reservation and must be rechecked. The 50 GiB
proposal preserves headroom subject to those live readings. This replaces the prior pilot's 20 GiB
only if separately approved; it is not a measured footprint. The historical
`docs/experiments/basketball-dense-training/resources-qualified.json` reports
7,568,463/7,633,276 points with approximately 5.84/5.89 GB checkpoints and roughly
10.18/10.27 GB allocated GPU memory. These were different initializers and do not
qualify the new compositions. The sparse 5,000-update historical runs in
`baseline-reuse.json` took about 136–137 seconds; their timing is not a dense-arm
runtime estimate.

Measure actual QF initializer counts/bytes and derive native checkpoint/optimizer
retention estimates before any training reservation. Retain an immutable endpoint
per successful arm and explicitly bounded task-owned recovery storage; account
all geometry, initializers, checkpoints, images and encoding peaks. If verified
retention/memory cannot fit the ceiling, stop at REVIEW with the measured shortfall.
Do not prune/downsample/change precision to make the budget fit. Existing records
and checkpoint-size basis support conservative preflight, not a success promise.

## Render and human comparison deliverables

Render each completed endpoint at identical calibrated 960×540, native 25 fps,
held-out cameras 0/10/20/30 and frames 0–49: 200 images and four complete
50-frame/2-second clips per arm, 1,000 images and 20 clips total. Freeze PNG
conversion/color handling, video encoding, full-image/detail crops and selected
frozen-frame IDs before generation/review. Keep original accepted RGB controls.
Do not interpolate missing frames or treat sparse diagnostics as continuous
rendered motion. No optional extra render pass or throughput benchmark is included.

Publish a fresh final-render package with arm configurations, five matched
contrasts, exact result/checkpoint/media hashes, engineering eligibility, costs
and unavailable dispositions. The real human compares appearance, rendered motion,
artifacts and sharpness and records preferences/ties/uncertainty with exact examples.
S/D initial preferences do not substitute for this follow-up. #34/#35 remain open
until their actual authorized outcomes, follow-up review and report are complete.

## Minimum CPU work before a DO proposal

1. Freeze typed QF request/result and initializer contracts plus exact source/input
   records and allocation identities, with the five-arm coverage above.
2. Implement checked fresh allocation/admission, composition and prerequisite
   validation using fake CPU runtimes; reject consumed identities, scope changes,
   absent qualification, altered source rows and exceeding cumulative caps.
3. Adapt geometry-to-initializer/native train/reload-render through these seams;
   preserve historical validators and verify camera/time/normalization/fusion.
4. Independently review, qualify current sources, measure bounded storage/native
   prerequisites without an unallocated model job, then prepare exact REVIEW/DO
   commands, reserves, cleanup and live-state bindings for separate user approval.

This document requests review of a concrete five-arm scope and ceilings. It does
not establish native viability, claim generation completed or authorize execution.
