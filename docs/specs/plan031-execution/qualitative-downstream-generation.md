# Qualitative downstream generation proposal

**Current scope:** [Scope amendment 001](qualitative-comparison-scope-amendment-001.md) takes precedence: isolated packages and initial review (#33) cover segmentation and depth only. Motion and neighbor method effects remain required comparisons on actual final renders (#34/#35); isolated M/N diagnostics are excluded from the current viewer. Applicable motion criteria and clip controls remain.

## Authority and readiness

Continuation of [Plan 067](../../../plans/plan_067.md), the
[qualitative amendment](qualitative-comparison-amendment.md), and issue #34.
The user approved the specific continuation approvals, including new generation
once a concrete budget proposal is prepared. This document specifies ceilings
and prerequisites; it does not reserve jobs, reset attempts, authorize retries,
or claim that a real human has selected components. **Execution remains blocked
on the actual initial human review and immutable decisions required by #33.**

## What the existing pipeline generates

`vipe_benchmark.diagnostics.run` produces RoMa matches, triangulated points,
colors, local velocities and support diagnostics. Its result explicitly records
`diagnostic_only: true` and `physical_accuracy: unverified`. G-S*, G-M*, G-N*,
R-G and C0–C3 produce geometric reconstruction diagnostics, not trained Gaussian
models or final rendered RGB. Depth colormaps and projected clouds cannot establish
photorealistic sharpness or trained motion quality.

Read-only ledger snapshot: run `plan031-20260913T032700Z`, 520 events, head
`0eb907e0a3e6509c6863309f289b35aff6d317d48553b1900f33d7f741f64a5f`.
Recheck live state before any reservation.

| Slots | Recorded state | Available action |
| --- | --- | --- |
| G-S0, G-S2–G-S4, G-M1–G-M2, G-N1–G-N2, R-G, C0 | Finished complete; attempts consumed | Publish existing diagnostics with their original provenance |
| G-S1 | Accounted blocked, never reserved | Resume original 1,800-second slot only after completed S1 reconstruction and checked admission |
| C1, C2, C3 | Accounted blocked, never reserved | Original 5,400-second slots remain conditional on their exact historical compositions and gates |

Historical C1 fixes depth D1; C2 fixes S4/D2 and verified commercial/non-AGPL
preferences; C3 fixes S1/D1/M0/N0. Human preference for D3 or D4 cannot silently
change these identities. C0 is already consumed. Saved automatic finalists and
annotation checkpoints remain immutable historical artifacts.

## Prospective qualitative geometry

After #33, a new request mode binds amendment, package, actual review, immutable
human decisions, exact S/M/D/N composition, engineering eligibility, input records,
current source qualification and live ledger prefix. Require completed segmentation
reconstruction, motion and neighbor results, passing current depth fit/check and
qualified runtime/assets. Preserve existing geometric gates, component thresholds,
precision, resolution, model pins and license eligibility.

Reuse existing successful geometry only when composition, inputs and generation
settings match exactly, retaining its original mode and limits. Resuming an
unstarted historical slot must retain its composition. A different composition
requires an explicit new identity and a saved authorization within the ceilings
below; never overwrite C0 or recycle its unused time. Optional reference versus
human-selected fresh geometry is capped at **two new jobs, 5,400 seconds each**,
serially, with the existing person-cropped policy, seed 0, 5,000 samples per selected
neighbor, three neighbors, reprojection 2 pixels, parallax 1 degree, foreground
support three cameras and LK roundtrip 1 pixel. Diagnostic camera/pair selections
remain those frozen in benchmark-v1.json. These are diagnostic outputs only.

## Trained RGB proposal and concrete limits

The two-arm pilot below does not establish all motion/neighbor method effects.
The latest scope requires a concrete final-render coverage/budget proposal for
M0–M2 and N0–N2, with matched settings and controlled component substitutions.
Do not expand this pilot's allocation implicitly or infer M/N winners from isolated
diagnostics; unresolved coverage remains open under #34/#35.

A matched trained comparison needs a separate adapter from accepted geometry to
training initialization. The existing diagnostic subset is not the full-rig
initializer expected by `basketball_dense_fusion.py`: that historical adapter checks
its own modes, nine non-reserved keyframes and provenance. Do not relabel diagnostic
rows as that initializer or weaken its validators. Until a prospectively frozen
initialization contract and coverage are implemented and tested, trained generation
is unavailable; the human may review diagnostic comparisons with this limitation.

The proposed bounded first comparison is **one reference and one human-selected
composition**, one seed each, using the same existing FreeTimeGS reproduction:

| New work | Maximum attempts | Seconds each | Total ceiling |
| --- | ---: | ---: | ---: |
| Optional fresh diagnostic geometry | 2 | 5,400 | 10,800 GPU seconds |
| Initialization preparation/validation | 2 | 900 | 1,800 CPU seconds |
| FreeTimeGS training | 2 | 3,600 | 7,200 GPU seconds |
| Fresh checkpoint rendering | 2 | 900 | 1,800 GPU seconds |
| Media encoding/package publication | 1 | 900 | 900 CPU seconds |

These are proposed maxima, not an obligation to spend them. Check original
cumulative limits before admission: 93,600 GPU seconds, 57,600 CPU preparation
seconds, 57,600 setup seconds, 60 GiB downloads, 150 GiB total new artifacts,
22 GiB total device memory, at most eight CPU workers and **one GPU process group**.
New preparation/training/render artifacts are additionally capped at **20 GiB**;
new downloads and environment builds are **zero**. Missing pinned dependencies
block execution. No deadline or failure grants another attempt. Training caps
include checkpoint publication and cleanup; incomplete checkpoints are labeled.

Training uses seed 0 for both arms, the same manifest/time normalization and
calibrated 960×540 cameras, original 25 fps, reconstruction frames 0–49 only,
held-out cameras 0/10/20/30, and the existing union of corrected-time exclusions
for interval [0.8, 1.0). No frame 50–199 becomes training input. Retain audited
`default_keyframe` preset/loss/optimization schedule from
`freetimegs_training.load_training`; source SHA256
`fc3e4320da73a470d0a16bcb5803f84d1bda5bdeafb000fcc39e022fbcfaaeb4`.
Target at most 5,000 updates per arm. Freeze the complete resolved configuration,
normalization, initializer, installed runtime/native binary inventory and checkout
revision before execution; the source hash alone does not qualify an environment.

Only initialization composition may differ. Select the largest **common** retained
1,000/2,000/5,000-update checkpoint for presentation; do not compare differing
iteration counts as an identical-training comparison. If no common checkpoint
exists, publish an unavailable disposition. Do not reuse a historical trained model
as if it consumed newly selected components.

Render matched held-out camera frames 0–49 (200 images per arm), with optional
training-camera temporal holdout views separately labeled. Use identical camera,
normalized time, exposure/color conversion, crop and image encoding. Encode each
complete 50-frame camera sequence at 25 fps without interpolation; incomplete or
sparse outputs are labeled sequences. Frozen frames use declared source IDs, not
post-review cherry-picked examples. Full-image and shared crop/zoom views, original
reference RGB and supporting diagnostics are available. Bind follow-up human
review to a new package hash; a component preference is not a review of these
trained outputs. This first comparison is a bounded pilot, not evidence of
convergence to the native preset's full schedule.

## Implementation seams and completion

1. Add a qualitative downstream request/result mode and checked admission seam,
   separate from the historical aggregate/finalists mode. Real human choices and
   engineering gates are mandatory; annotation presence and metric ranking are
   absent only in the new mode. Ties or unresolved choices block selection unless
   the human explicitly names a justified choice.
2. Add checked registration for fresh identities, exact allocations and immutable
   authorization. Test consumed-slot rejection, absent review, wrong hashes,
   ineligible composition and serial ownership with fake runtimes.
3. Implement the initialization contract and explicit geometry-to-training adapter,
   retaining source roles, coverage, units, provenance and static/dynamic rules.
   Freeze identical treatment for reference and selected arm before generation.
4. Wrap existing native training/reload-render functionality in the benchmark
   supervisor and ledger. Existing `basketball_study.supervise` has no total
   deadline and cannot enforce this proposal unchanged; do not invoke it directly.
   `basketball_native_train.py`, `basketball_dense_train.py` and
   `evaluate-basketball-sync.py` supply reusable native work, not automatic authority.
5. Publish actual output/disposition packages, then obtain actual follow-up human
   observations on appearance, motion, artifacts and sharpness. #34 closes only
   when authorized dispositions and its required follow-up review are complete.

No runtime was launched and no live ledger was changed to prepare this proposal.
