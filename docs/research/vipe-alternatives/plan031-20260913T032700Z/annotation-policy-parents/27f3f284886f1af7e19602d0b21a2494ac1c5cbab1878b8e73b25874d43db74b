# Plan 031 — Benchmark ViPE replacements for Basketball

Prepared 2026-09-12 against repository commit
`a0c74140c0ba5b9d7cc3dfb9d1a3b6e64a3a0909`.
Status: plan prepared; implementation and experiment execution have not begun.
The present request is to create this plan. It does not start model jobs or a
continuous-improvement loop.

## Objective and specification

Implement and execute the bounded Basketball comparison specified by the
[ViPE alternatives study](../docs/research/vipe-alternatives.md) and its
[benchmark protocol v1](../docs/research/vipe-alternatives/benchmark-protocol.md).
Determine which standalone components can replace ViPE at workflow steps 2.1,
2.5 and 4.2, quantify their measured benefits and regressions, and report the
primary, commercial-use preference and fallback combinations.

The protocol is the source of experiment selections, model settings, scientific
gates, statistical methods and execution limits. This plan supplies implementation
milestones, dependency gates and evidence requirements. Preserve these source
hashes in the eventual run admission record:

| Document | SHA-256 |
| --- | --- |
| Study | `6fbb6e55dedf444766c75e946c3d5099426839e0df158706d98d28b635353e8e` |
| Protocol | `6d32683e3d351f8f19afffa11fe5664c5a15515f84a2b9380f86a39a757072f5` |

Pin source and model snapshots from study section 6. Translate the protocol's
embedded JSON into a checked configuration rather than maintaining a second
handwritten selection or budget list. Record any later user-directed amendment
before affected execution; do not silently resolve a mismatch by changing a run.

The allocation covers annotation, component inference, motion/neighbor
comparisons, diagnostic triangulation and reporting. It contains zero calibration
regeneration, training updates, fine-tuning, parameter searches, new evaluation
on frames 200–249, or trained-render scoring. Preserve the accepted static map,
camera calibration, source videos, RoMa weights, local numerical solver, sampling
and geometric acceptance rules. Retain historical manifests, freezes, reports,
validation-consumption markers and environments.

## Experiment matrix and dependencies

Implement every configuration exactly as defined in
[protocol section 5](../docs/research/vipe-alternatives/benchmark-protocol.md#5-frozen-configurations),
including precision, processors, thresholds, merge rules and pair resets.

| Family | Arms | Question and control |
| --- | --- | --- |
| Segmentation | S0: historical ViPE; S1: standalone Grounding DINO/SAM-B/DeAOT; S2: Grounding DINO/SAM 2.1-L; S3: original SAM 3; S4: RT-DETRv2-L/SAM 2.1-L | Compare calibration exclusion and paired reconstruction masks. Hold M0 fixed; quantify S1/S0 preprocessing and output differences. |
| Changing regions | M0: adjacent difference; M1: nine-frame temporal median; M2: MOG2 | Hold S0 fixed. Compare foreground leakage and retained static evidence. Preserve role-bounded context and MOG2 cold start. |
| Metric depth | D0: historical ViPE UniDepth; D1: standalone UniDepth V2-L; D2: DA3METRIC-LARGE; D3: Metric3Dv2 ViT-L; D4: Depth Pro | Use identical frozen RGB, intrinsics, source masks and sparse sample locations. Fit at frame 100 and check the frozen estimate at 175. |
| Neighbors | N0: shared-track count; N1: Jaccard; N2: coverage/parallax greedy selection | Same training-only sparse map, exactly three positive-support neighbors or explicit failure. Use the protocol's full N2 tuple and deterministic ties. |

Run nine isolated **coarse** geometry arms: five `(S_i,D0,M0,N0)`, two additional
`(S0,D0,M_j,N0)` for M1/M2, and two `(S0,D0,M0,N_k)` for N1/N2. Reuse the
common S0/D0/M0/N0 result as the baseline. All use the same accepted geometry,
historical reference scale and normalization. The isolated depth comparison
does not change this geometry or regenerate its masks.

After isolated metrics are frozen, select S*, M* and N* using the exact
[protocol section 7 rules](../docs/research/vipe-alternatives/benchmark-protocol.md#7-comparison-order-geometry-and-finalist-selection).
In particular, S* ranks S1–S4 on calibration-selection annotations by minimum
person/ball Dice, then leakage, retained static-feature fraction, boundary F1
and ID. M* ranks usable-static Dice, leakage, retained feature fraction and ID.
N* ranks accepted-foreground reference-cell coverage, accepted foreground
fraction, matching wall time and ID. Preserve camera balancing and 12-decimal
tie handling. Missing semantic-class evidence invokes only the prescribed S2
default, with quality selection unverified. Missing eligible evidence otherwise
blocks dependent selection; it does not authorize a replacement rule.

| Combined slot | Composition | Eligibility |
| --- | --- | --- |
| C0 | S0 + D0 + M0 + N0 | Fresh reference results and valid scale provenance under the common diagnostic harness. |
| C1 | S* + D1 + M* + N* | Frozen finalists; D1 passes all frame-100 and frame-175 gates. S2/D1 is the initial hypothesis, not a guaranteed winner. |
| C2 | S4 + D2 + M* + N* | D2 passes both scale stages; exact code, weights and dependencies support the stated commercial-use/non-AGPL preferences. |
| C3 | S1 + D1 + M0 + N0 | Standalone control contracts/provenance and D1 scale gates pass. |

All four combined slots use the same person-cropped matching policy. D3/D4
remain descriptive challengers and cannot replace a failed D1/D2. A failed or
unavailable arm retains its slot and reason. Complete technically valid arms
within their caps regardless of intermediate visual quality.

## Fixed data and annotation workload

Use physical camera IDs, original 25-fps frame IDs and seed 0. Reconstruction
inputs exclude cameras `[0,10,20,30]`; calibration diagnostics may use all 34,
with held-out camera support labeled localization-only.

| Input | Selection | Required count |
| --- | --- | --- |
| Calibration fitting | All cameras; `[50,62,75,87,99,100,112,125,137,149]` | 340 distorted 960×540 snapshots |
| Calibration selection | All cameras; `[150,162,175,187,199]` | 170 distorted snapshots |
| Depth | All 30 training cameras; fit 100, frozen check 175 | 60 fixed inputs per passing depth arm |
| Reconstruction masks | Training cameras; pairs starting `[0,5,10,15,20,21,22,23,24,25,30,35,40,45]`, each with its successor | 420 pairs; 840 contexts; 690 distinct undistorted RGB images per S arm |
| Geometry | References `[1,6,11,16,21,26,31,33]`; starts `[0,20,21,22,23,24,25,45]`; three training neighbors | 64 reference/pair contexts; 192 directed edges per arm |
| Motion context | Calibration 50–149 and 150–199 separately; reconstruction 0–49 | At most 6,600 branch-specific RGB images |
| Calibration annotations | Cameras `[0,1,10,11,20,21,30,31]`; frames `[50,100,149,150,175,199]` | 48 images |
| Reconstruction annotations | All selected distinct images for the eight geometry references | 184 images; pair associations stored separately |

Prepare exactly **232 unique annotation images**. Reserve 72 person-hours for
primary annotation, 24 for independent review, 8 for adjudication and 8 for
static-feature review: **112 person-hours**. The primary annotator and independent
reviewer are required external contributors; an agent-created candidate mask is
not independent truth. Review every image without candidate outputs, method
identities or scores, retain revisions and adjudication, and freeze the final
annotation hash before comparing predictions. Missing contributors or incomplete
annotations block model/scored-comparison admission; preparing this plan does
not presume those contributors are available or contact them.

Import the layers and metadata in
[protocol section 3](../docs/research/vipe-alternatives/benchmark-protocol.md#3-independently-reviewed-annotation-protocol):
visible player/other-person/ball instances, role uncertainty, pair associations,
independent changing-background masks, valid footprint, ignored boundaries,
visibility, occlusion, blur and tiny-ball flags. Review at most 768 deterministic
SIFT locations, one per occupied 4×4 cell in annotated calibration images.
Do not shrink the annotation set or infer players from the model's person label.

Record previous calibration, scale, dense-pilot, final dense-report and crossing
exposure before new result inspection. Frames 20–24 are exploratory diagnostics;
frame 175 is an already used repeatability check. Final-window history is
report/marker access only. Neither reused scene images nor these diagnostic
camera samples establish an untouched or population-representative test set.

## Implementation milestones

### 1. Freeze configuration, provenance and input access

Add the planned entry points `scripts/basketball_vipe_benchmark.py` and
`scripts/basketball_vipe_worker.py`, with reusable modules under
`scripts/vipe_benchmark/`. Keep historical command entry points intact. Add
`configs/vipe-alternatives/benchmark-v1.json`, component settings and runtime
specifications derived from the two source documents.

The controller must support preparation, annotation import, setup, admission,
stage execution, status and final reporting. Workers take explicit immutable
input/configuration paths and a fresh output directory; they do not discover
the newest directory or inherit a historical passing status.

Implement role/membership guards, a diagnostic RGB loader and a shared data
manifest. Resolve videos through recorded audit paths/hashes and reconstruction
RGB through `.local/sync-pivot/basketball-zero/manifest.json`. Give each output
the full `(branch,camera,pair_start,frame)` identity where applicable. In
particular, frame 21 in pair 20 and frame 21 in pair 21 have different tracker
contexts. Do not weaken `training_key`, historical keyframe or fusion guards to
admit crossing frames into this study.

Build the immutable depth sample manifest from existing accepted preparation:
RGB, static-mask parents, point IDs, UVs, camera-z, K and valid footprints. Reuse
verified prepared samples; if derivation is needed, reproduce the existing
eligibility and deduplication without changing masks or support policy. Keep the
full frozen SIFT pool for automatic feature/track retention measurements.

**Acceptance:** synthetic membership/hash tests reject held-out reconstruction
cameras, final-window image access, wrong branch/K, duplicate/missing entries,
changed files, pair collisions and role-crossing motion contexts. Manifest counts
match the table and protocol JSON. No code path reads `prompts` content.

### 2. Implement component and geometry interfaces

Implement segmentation, depth, motion, neighbors and geometry modules with file
interfaces, component manifests and per-output validation. Preserve the
[protocol section 4 contracts](../docs/research/vipe-alternatives/benchmark-protocol.md#4-adapter-contracts-and-coordinate-validation):

- Static PNG: uint8 `[540,960]`, 0/255, with 255 meaning usable static evidence;
  valid footprint minus person, ball and changing regions, on distorted RGB.
- Instances: int32 on the matching image grid; 0 background, -1 invalid,
  positive pair-local IDs with complete native and normalized semantic metadata.
  Validate capacity before legacy calls; never wrap IDs through uint8.
- Changing regions: boolean arrays with explicit context frames and state hashes;
  retain MOG2 shadow/unknown evidence and use the prescribed pair unions.
- Depth: float32 camera-z metres, boolean validity, NaN invalid entries, optional
  documented confidence and preserved canonical/raw outputs. Confidence never
  changes scale support selection, camera weights or gates.

Separate the scale grid's `(480,270)` principal point from reconstruction OpenCV
K, typically `(479.5,269.5)`, and the renderer/RoMa half-pixel convention. Record
resize, crop, pad and undistortion transforms. Use the existing RGB remap,
nearest-neighbor labels/validity and validity-aware bilinear depth mapping.
Retain the existing `cv2.remap(..., INTER_LINEAR)` sparse-sampling kernel; reject
any sample with an invalid nonzero-weight contributor, including for D0.

Implement D1 camera-aware inference; D2 processed mean focal/300 conversion once;
D3 resized fx/1000 conversion once; D4 native inverse-depth conversion with
supplied input fx. Never estimate replacement cameras, fit per-image affine
depth, or apply an extra focal multiplier. Save native clamp/saturation evidence.

Wrap the pure estimator in
[basketball_scale.py](../scripts/basketball_scale.py) with explicit provenance
inputs rather than invoking its ViPE-bound inference/evaluation entry points.
Implement N0/N1/N2 from the same unique point-ID sets, including exact N2 support
eligibility, score tuple and failure when a reference has fewer than three
usable neighbors.

Add a diagnostic geometry worker using
[triangulation.py](../scripts/triangulation.py),
[basketball_temporal_geometry.py](../scripts/basketball_temporal_geometry.py)
and the current RoMa loader. The historical
[cloud entry point](../scripts/basketball_temporal_cloud.py) indexes masks by
camera/frame and binds production paths, so it is not the new runner.
Preserve rank screening, float32 CUDA triangulation, finite/positive depth,
≤2-pixel reprojection, ≥1° parallax, ≥3-camera foreground support, LK round-trip
≤1 pixel and three-camera velocity gates. Preserve unsupported-motion flags,
the existing time conversion and the multiview velocity solver.

Each directed edge receives 5,000 coarse samples, with the existing half-budget
person sampling policy, seed 0 and canonical loop order. Record shortages.
Combined arms use coarse votes to associate view-local people, then the existing
10%/minimum-two-pixel crop expansion and exact inverse crop mapping. Limit crop
refinement to one per reference person per edge, at most 255. Retain association
votes, rejected alternatives and crop coordinates; do not add ball crops/quotas
or use annotated roles to remove spectators.

**Acceptance:** independent float64 geometric fixtures cover nonuniform resizing,
off-center K, crop/pad restoration, radial remaps, both pixel-center conventions,
known-z planes, off-axis ray range and invalid interpolation borders. Use ≤1e-6
pixels for analytic transforms and ≤1e-3 for OpenCV float remap coordinates.
Test overlaps, missing semantics, >255 IDs, pair resets, identity switches,
hand-computable neighbor rankings, crop associations and consistent scene scaling.
Stubbed integration tests must pass with ViPE imports and source/extension access
deliberately denied for S1–S4/D1–D4; only S0/D0 may access the reference checkout.
No additional real-model or GPU smoke jobs are allocated for implementation.

### 3. Enforce budgets and qualify run admission

Implement an append-only ledger and supervisor before launching any experiment.
The existing [basketball_study.py](../scripts/basketball_study.py) supervisor has
no total deadline and cannot enforce this allocation unchanged. Record job IDs,
command arguments, process groups, environment/config hashes, monotonic timing,
attempt consumption, output status and resource measurements. Reserve each job
atomically; restarting the controller must not relaunch a consumed attempt.

Enforce the allocation below, one GPU process group at a time, with an exclusive
device check and total-device memory monitoring. Loading, qualification,
serialization and cleanup count against each job. Reserve up to 30 seconds
inside its deadline for graceful and forced child-process cleanup. Test timeout,
interruption, child survival, duplicate dispatch, incomplete results and simulated
resource exhaustion using disposable CPU workers and injected resource readings.
Do not charge these synthetic tests as model evaluations.

Use the exact E0–E8
[runtime targets](../docs/research/vipe-alternatives/benchmark-protocol.md#runtime-proposal-and-qualification-scope).
E0/E8 are existing hash-verified environments; E1–E7 are at most seven serial
new builds, one each. Freeze resolved dependencies, wheels, native extensions,
source files, weights, tokenizer/configuration assets and license evidence.
Verify the actual Ubuntu/RTX 4090 runtime during execution admission. The source
documents' runtime targets and 22-GiB ceiling are unqualified proposals, not
measurements or compatibility guarantees.

Setup contains resolution, asset verification and imports, with zero model
inference. A failed target build blocks its candidates; it does not authorize
another version combination. S2/S4 share E2, so an E2 failure affects both.
Missing gated access or unresolved required usage permission is recorded by
candidate; never accept asset terms on the user's behalf. Optional license
preferences do not exclude otherwise eligible research comparisons, but C2
requires evidence for its claimed preferences. Inventory actual transitive and
native dependencies, including the study's GPL/LGPL qualifications.

**Admission evidence:** controller/config/fixture checks, immutable input and
exposure manifests, fully reviewed annotation hashes, per-candidate asset/runtime
qualification, resource availability and a saved authorized allocation scope.
On an explicit implementation request, record its authorization and applicable
repository standing approval without seeking duplicate routine approval. This
plan does not reset older experiment ledgers or imply that a stopped loop resumed.
Missing common prerequisites block model execution; missing challenger-specific
prerequisites block only their dependent arms, subject to repository stop rules.

### 4. Execute isolated comparisons and freeze their evidence

Follow protocol section 7 in this order; initialize and validate each worker's
first result inside its one allocated job before continuing the remaining inputs.

1. Run S0–S4 calibration and reconstruction branches in ascending method order.
   Store intermediate resized RGB/K, boxes, phrases, masks, overlap decisions and
   propagation/birth evidence needed for the S1/S0 control comparison. Validate
   every result's shape, semantics, footprint, membership and hash.
2. Run M0–M2 once on CPU with S0 semantics. Score all S arms with M0 and all M
   arms with S0. Freeze metrics before downstream combination selection.
3. Run D0–D4 frame-100 fits, freeze passing estimates, then run frame-175 checks
   only for passing fits. Preserve every camera and the frozen estimator/gates
   listed below. Report D1/D0 depth and per-camera scale-ratio differences.
4. Compute N0–N2 once, then execute the nine coarse geometry arms in segmentation,
   additional-motion and additional-neighbor order, ascending IDs within each.
   Keep result caching across arms disabled for timing. Save attempted/accepted
   counts, semantic/support/rejection stages, coverage, parallax and cost.
5. Freeze `finalists.json`, including rankings, ineligibility reasons and all
   supporting hashes, before any combined-arm output is inspected.

Execute R-S immediately after its S1 reconstruction source is complete, R-D
after its D1 fit source, and R-G after the coarse reference source. Each is a
fresh process with the fixed subset and limit below. If its source is absent,
record the repeat as blocked/skipped; it cannot be reassigned.

Keep [scale.json](../configs/basketball-rev2/scale.json) values unchanged:

| Gate | Requirement |
| --- | --- |
| Sparse support / map parallax | ≥3 training cameras / ≥1° |
| Static clearance / spatial deduplication | ≥8 pixels / 2-pixel cells |
| Per-camera samples / occupied cells | ≥100 / ≥6 of 16 |
| Positive finite depth over valid footprint | ≥0.99 |
| Within-camera log-ratio MAD | ≤0.25 |
| Camera scale deviation from global/frozen estimate | ≤0.25 relative |
| Camera bootstrap | Seed 0; 10,000 resamples; 95% relative halfwidth ≤0.10 |
| Frame-175 diagnostic estimate vs frozen fit | ≤0.10 relative disagreement |

The global scale remains `exp(median_c(median(log(z_model/z_map))))` with one
vote per camera. Invalid depth reduces that candidate's support only. A failed
camera is not dropped and frame 175 never refits or selects a replacement depth
model. If already available independent measurements support two fitting
distances and a third checking distance, preregister their endpoints, uncertainty
and assignment before predictions and report the protocol's separate scale-anchor
test. No survey or inferred court/ball dimensions are allocated. Without such
references, physical accuracy remains unverified.

### 5. Run combined diagnostics and report

Create a fresh diagnostic scene freeze for each eligible combined scale, tied to
its passing depth fit/check and component results. C0 also needs current valid
D0 scale evidence for its new freeze; do not turn an old passing report into a
new D0 pass. Scale `XYZ`, camera translations and centers together, preserve R/K,
and derive a consistent normalization transform. Validate unchanged projections
and the common physical-to-normalized coordinate relationship. Store all unit
and velocity conversions. These freezes/clouds remain diagnostic artifacts.

Run C0–C3 once each with the common person-cropped policy. Identical combined
configurations may reuse a result only with the recorded hash and no extra
attempt; saved time cannot fund another run. Report component effects from the
isolated arms and label combined interactions separately.

Implement one staged aggregation pass that consumes each completed result set
once, freezes isolated/selection metrics before combined execution, and appends
combined/repeat summaries afterward. Produce one final report. This provides
the required selection checkpoints within the protocol's single aggregation
and single report allocations, without an unbudgeted rescore loop.

Report annotation metrics only where frozen reviewed truth exists; distinguish
6,750 generated primary mask rows from the annotated subset. Include class pixel
precision/recall, IoU, Dice, two-pixel boundary F1, IoU-0.5 instance matching,
tiny-ball recall/center/area, negative-image false positives, pair identity
switches/births/disappearances and all-successor recall. Preserve player/other-
person conditional scoring and unmatched-prediction precision bounds. Report
semantic masks separately from final static masks, including foreground leakage,
static area, SIFT/grid retention and accepted-map observation retention.

Use the protocol's equal-camera aggregation, raw numerators/denominators,
per-camera worst cases and paired camera/temporal-group bootstrap: PCG64 seed 0,
10,000 identical resamples across methods, 2.5/97.5 linear percentiles. Keep
overlapping crossing pairs in the shared 20–26 group. Separate calibration
fitting, selection and reconstruction reports; disclose undefined/missing strata.

For geometry, publish static/person/ball attempted and accepted triangulations,
distinct-camera support, velocity-valid fraction, spatial/marginal coverage,
parallax min/median/p95, neighbor failures, full-image/crop counts and reciprocal
duplication. Include synchronized CUDA and wall time, peak allocated/reserved/
device memory and input/output bytes. Repeats report pixel disagreements, depth
and scale-ratio differences, and geometry acceptance changes; they are not
additional model-selection evidence.

Conclude separately on dependency removal, engineering qualification, measured
quality, physical accuracy and license preferences. Claim improvement only for
named metrics supported by paired evidence, disclose regressions, and mark an
interval spanning zero inconclusive. A successful bounded comparison can find
no superior replacement. An interrupted or blocked study is not a successful
full benchmark, and engineering checks alone do not validate output quality.

## Execution allocation and stop rules

Carry forward the protocol v1 allocation without increases. Attempts are
process-level jobs, not images. The GPU limits include first-result qualification
and the three prescribed repeats; there is no separate smoke-test/retry pool.

| GPU job scope | Attempts | Wall seconds each | Maximum seconds |
| --- | ---: | ---: | ---: |
| S0–S4 calibration | 5 | 3,600 | 18,000 |
| S0–S4 reconstruction pairs | 5 | 5,400 | 27,000 |
| D0–D4 frame-100 fits | 5 | 900 | 4,500 |
| D0–D4 frame-175 checks, conditional on fit | 5 | 900 | 4,500 |
| Segmentation coarse geometry | 5 | 1,800 | 9,000 |
| Additional motion coarse geometry | 2 | 1,800 | 3,600 |
| Additional neighbor coarse geometry | 2 | 1,800 | 3,600 |
| C0–C3 combined cropped geometry | 4 | 5,400 | 21,600 |
| R-S, R-D, R-G | 3 | 600 | 1,800 |
| **Total** | **36** | — | **93,600 (26 hours)** |

R-S is S1 camera 1 pair 20/21; R-D is D1 camera 1 frame 100; R-G is coarse
S0/D0/M0/N0 camera 1 pair 20/21 with its three N0 neighbors.

| Other scope | Hard limit |
| --- | --- |
| GPU | One exclusive RTX 4090 process group; total device memory ≤22 GiB |
| New environments/setup | Seven builds, one per E1–E7; 57,600 seconds cumulative serial setup wall time |
| CPU motion | Three jobs, 1,800 seconds each |
| CPU neighbors | Three jobs, 300 seconds each |
| CPU preparation/import/scoring/report | 57,600 seconds cumulative wall time; one preparation, annotation import/check, staged aggregation and report pass |
| CPU concurrency | At most eight workers |
| Annotation/review | 112 person-hours, split 72/24/8/8 as above |
| New downloads | 60 GiB, including candidate assets and environment packages |
| New artifact/storage footprint | 150 GiB across candidate environments, assets and results |
| Calibration / training / new final-window evaluations | Zero each |

Maximum primary outputs: 6,750 mask rows, 300 depths and ten full-rig scale
evaluations; 1,728 isolated and 768 combined full-image matches, with at most
195,840 person-crop refinements. Repeats add two masks, one depth and three
full-image matches. The worst-case crop count does not override runtime or disk
caps. Do not treat unannotated outputs as additional reviewed truth.

Track elapsed consumption separately from attempts and reserved ceilings. A
failed attempt consumes its attempt and actual elapsed time; unused time,
skipped arms and identical-result reuse never fund new attempts. Keep setup,
CPU, annotation, GPU, transfer and storage scopes separate. Stop affected work
at the first applicable cap, retain partial evidence and account for unstarted
dependent arms. A smaller model, altered precision/resolution, CPU fallback,
threshold change or extra environment build is not an allowed recovery.

Apply repository interruption, permission retry/stop and staging/commit-failure
rules during every milestone. A sandbox-related failed operation receives only
the prescribed single safe retry of that operation outside the sandbox; preserve
attempt identity and elapsed accounting, and do not replay successful writes or
restart a model job to create another attempt. If that retry is denied or fails,
stop the affected work and report the exact command/error and approval-rule
status as required by `AGENTS.md`. Stop owned process groups on interruption,
OOM, memory excess, loss of exclusive GPU access or deadline; never evict other
users' jobs. Confirm child cleanup and record any process not confirmed stopped.

The run ends after the final report or a required stop. Exhaustion does not start
another allocation or continuous-improvement iteration. Preserve enough status
to resume only on explicit instruction and only within remaining authorization.

## Artifacts, validation and completion

Choose a fresh run ID when execution is requested. Store large immutable outputs
under `.local/vipe-alternatives/{run-id}/` and compact evidence under
`docs/research/vipe-alternatives/{run-id}/`. Required records are `admission.json`,
`inputs.json`, `exposure-history.json`, `components.json`, `annotations.json`,
append-only `ledger.jsonl`, per-arm `config.json`/`result.json`/logs/output hashes,
mask/motion/scale/neighbor/geometry metrics, repeat comparisons, `finalists.json`,
combined freezes, `assessment.md` and a readable `report.md`.

Maintain `status.md` with the plan/protocol hashes, completed milestones, current
stage, job identities, scoped consumption, result links and stop reason. Every
planned job/arm, including conditional checks and repeats, must end accounted
for as complete, failed, blocked or skipped with a reason. Never overwrite
incomplete output directories with passing results.

Add focused tests under `tests/test_vipe_benchmark_*.py` for the new access,
contracts, estimator adapter, rankings, annotation metrics, selection and budget
boundaries. Use independently calculated geometry/statistics and deterministic
fake workers. Run affected existing scale, temporal geometry/crops and dense
fusion tests where shared interfaces are exercised. Real runtime qualification
is evidenced by allocated model/geometry jobs, not synthetic stubs or skipped
CUDA checks.

| Criterion | Required outcome and evidence |
| --- | --- |
| P31-1: Reproducibility | Frozen selections/settings/pins, complete provenance and exposure history, matching counts and immutable historical parents; configuration/access tests pass. |
| P31-2: Engineering | Interface, geometry, metric and supervisor checks pass; per-candidate runtime/access failures are explicit; eligible standalone workers demonstrate no ViPE access. |
| P31-3: Independent scoring | All 232 annotations have review/adjudication evidence; paired metrics retain class/role/temporal grouping, raw counts and uncertainty. Missing annotations prevent this criterion passing. |
| P31-4: Controlled experiments | Every matrix and combined slot has results or a specific failure/ineligibility record; scientific gates and isolated controls remain unchanged. Report limits on conclusions from unavailable arms. |
| P31-5: Accounting and integrity | Ledger reconciles every attempt, output count and resource scope within limits; old freezes/consumption records are unchanged; owned processes are confirmed stopped. |
| P31-6: Supported conclusions | Report separately assesses dependency removal, measured quality, physical accuracy and both license preferences. Each claim links applicable evidence; unresolved outcomes remain unverified. |

Assess each criterion as met, not met or unverified in `assessment.md`, keeping
benchmark completion distinct from a component passing, a replacement improving
quality or a production migration being ready. Record blocked/interrupted runs
separately; report any incomplete matrix. This plan never promotes a new
production calibration, initializer or training configuration.

Commit completed, validated milestones locally: runner/configuration and focused
checks; admitted inputs/annotation/runtime evidence; isolated results and frozen
finalists; combined results and final assessment. Stage only task-related source
and compact evidence paths, never bulky `.local` assets. Follow `AGENTS.md`:
separate escalated `git add` and `git commit` calls, inspect the staged diff, use
a title and description, and do not push/amend/rewrite history. A commit is a
checkpoint; during an authorized execution continue to the next unfinished
milestone unless a stop condition applies.
