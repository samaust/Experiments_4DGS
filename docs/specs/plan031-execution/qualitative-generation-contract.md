# CPU qualitative artifact preparation

`scripts/basketball_vipe_qualitative.py generate REQUEST OUTPUT` takes an
immutable JSON request with schema `plan067-qualitative-generation/v1`, `id`,
`record_kind: actual`, absolute `local` run directory, `max_seconds` (at most
600), sorted unique `cameras`, `reconstruction_frames` (0–49), `motion_frames`
(0–49), `depth_frames` (150–199), and a shared `depth_range_metres`.

`bindings` contains verified file records for the run's `config`, accepted
`prepare/inputs.json`, qualitative `amendment`, and explicit `approval`.
The actual configuration must equal the ledger allocation. The generator checks
remaining cumulative CPU headroom and requires no active allocated job. The
controller serializes this preparation with live model admission.

Outputs are separate segmentation, motion, depth and neighbor package manifests.
All declared source frames are preserved. Available candidates require a complete
result resolved through the successful ledger outcome, and exact RGB/geometry
lineage. Missing arms and ungenerated final renders remain explicit. Neighbor
diagnostics display selected camera IDs; they do not depict inferred framewise
geometry. Depth uses one declared color range across candidates. Mask exclusions
use the same red overlay on accepted RGB.

Selected consecutive predictions produce a 25 fps clip. Sparse predictions
produce a labeled sequence with original timestamps. Two-frame clips cannot
establish sustained motion quality. Declare `motion_frames: [0, ..., 49]` for the
initial full two-second motion diagnostics. These are component diagnostics, not
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
`blank-review PACKAGE OUTPUT` produces a blank handoff, not performed review.
Import actual human feedback using `import-review SUBMISSION OUTPUT --package
PACKAGE`. Freeze decisions using `decision REVIEW OUTPUT --engineering FILE`
and optional `--choice FILE`. Build a report using `report REVIEW OUTPUT
--decision DECISION`. The CLI exposes actual review paths only.
