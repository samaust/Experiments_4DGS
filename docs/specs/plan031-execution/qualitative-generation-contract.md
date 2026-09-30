# CPU qualitative artifact preparation

`scripts/basketball_vipe_qualitative.py generate REQUEST OUTPUT` takes an
immutable JSON request with schema `plan067-qualitative-generation/v1`, `id`,
`record_kind: actual`, absolute `local` run directory, `max_seconds` (at most
600), explicit `max_new_artifact_bytes` (at most 1 GiB), frozen named
`detail_regions` with shared `[x,y,width,height]` crops, sorted unique `cameras`, `reconstruction_frames` (0–49), `motion_frames`
(0–49), `depth_frames` (150–199), and a shared `depth_range_metres`.

`bindings` contains verified file records for the run's `config`, accepted
`prepare/inputs.json`, qualitative `amendment`, and explicit `approval`.
The actual configuration must equal the ledger allocation. The generator checks
remaining cumulative CPU headroom and requires no active allocated job. The
controller serializes this preparation with live model admission.
Actual preparation also verifies the explicit qualitative approval scope and
current amendment. Artifact admission checks allocated storage once; incremental
checks scan only the new output directory and preserve 64 KiB terminal receipt
headroom. No GPU probe is performed.

Outputs are separate segmentation, motion, depth and neighbor package manifests.
All declared source frames are preserved. Available candidates require a complete
result resolved through the successful ledger outcome, and exact RGB/geometry
lineage. Accepted RGB identities have no reconstruction pair context; model
identities retain their exact native `pair_start`. Where multiple pairs produce
the same camera/frame, choose the lowest `pair_start` before review and bind its
complete native row hash. Missing arms and ungenerated final renders remain explicit. Neighbor
diagnostics display selected camera IDs; they do not depict inferred framewise
geometry. Depth uses one declared color range across candidates. Mask exclusions
use the same red overlay on accepted RGB.

Selected consecutive predictions produce a 25 fps clip. Sparse predictions
produce a labeled sequence with original timestamps. Two-frame clips cannot
establish sustained motion quality. Existing M0–M2 camera 1 and 2 predictions
cover contiguous frames 20–26; declare that exact `motion_frames` range for
genuine 0.28-second initial diagnostics, with the short duration explicitly
disclosed. These are component diagnostics, not
trained renders or evidence of final rendered sharpness.

The output directory must not exist. Request, ledger prefix, selected successful
outcomes, images, videos, manifests and terminal receipt are immutable. Preparation
charges elapsed CPU time through `charge_cpu_preparation`, including failed
preparation; it does not reset consumed model, aggregate or report allocations.
FFmpeg encoding has a remaining-wall deadline and one thread.

Publish each emitted manifest using `publish MANIFEST NEW_PACKAGE_DIRECTORY`.
Publication binds the original generated manifest and complete, charged generation
receipt. Actual lineage validation checks the frozen ledger prefix, successful
native results and worker requests, exact accepted camera/frame/geometry records,
and recomputes each deterministic image recipe. Video source images must equal
the bound candidate frame records. Validation and publication receive a separate
bounded elapsed CPU preparation charge, including failures, in an immutable
`NEW_PACKAGE_DIRECTORY-cpu-receipt.json` sibling receipt.
The generation implementation is copied into immutable `source.py` and bound
through the charged result and recipe version. Later source edits therefore do
not invalidate a previously generated package or its human review.
`blank-review PACKAGE OUTPUT` produces a blank handoff, not performed review.
Import actual human feedback using `import-review SUBMISSION OUTPUT --package
PACKAGE`. Freeze decisions using `decision REVIEW OUTPUT --engineering FILE`
and optional `--choice FILE`. Build a report using `report REVIEW OUTPUT
--decision DECISION`. The CLI exposes actual review paths only.
