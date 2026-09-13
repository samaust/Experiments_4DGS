# Plan 031 implementation checkpoint

This checkpoint implements configuration derivation, diagnostic input preparation,
independent-annotation import, neutral numerical interfaces, selection primitives
and an append-only CPU/process-group supervisor. **Plan 031 is not fully
implemented or executed.** Model-specific S0–S4/D0–D4 inference, bounded environment
setup, the full diagnostic geometry worker, stage dispatch and staged end-to-end
aggregation/reporting remain unfinished. Admission deliberately reports these
gaps instead of launching placeholder model jobs.

The reference [plan](../../../plans/plan_031.md) and
[protocol](benchmark-protocol.md) remain unchanged. The checked JSON configuration
is extracted from the protocol; component settings, runtime targets and source/model
pins are extracted from its tables and the study. Run initialization verifies the
two SHA-256 values recorded in Plan 031.

## Controller and artifacts

Use the existing CPU-capable preparation environment, with NumPy, OpenCV and
PyCOLMAP. These commands do not qualify an E0–E8 model environment:

```bash
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id RUN_ID init
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id RUN_ID prepare
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id RUN_ID status
```

Initialization creates a fresh authorized run and exposure record. Preparation
consumes the single allocated preparation job. Repeating it after success or
failure is rejected. The worker verifies audited source videos, decodes only
calibration frames 50–199, hashes all 1,500 permitted reconstruction context RGBs,
exports the 232 selected annotation images, preserves the full SIFT pool and freezes
the 60 existing depth samples and accepted sparse map. Calibration SIFT uses the
existing frontend's `nfeatures=8192` setting, without a candidate mask. The decoder,
OpenCV build and all grids/transforms are recorded.

Large artifacts are under `.local/vipe-alternatives/RUN_ID/prepare/`. The
`annotation-template.json` contains exact RGB/K/footprint records, 232 unique image
entries, up to 768 static-feature audit locations and 112 separate pair records.
`annotation-images/` contains byte-verified PNG exports. Templates contain no truth
labels and never count as annotation evidence.

Preparation records existing scale RGB, static-mask parents, point IDs, UVs,
camera-z and source intrinsics without regeneration. Reconstruction K converts
the processed manifest's COLMAP centers to OpenCV centers once; scale K retains
the historical `(480,270)` principal point. Pair output identities preserve the
distinction between frame 21 in pair 20 and frame 21 in pair 21.

## External annotation handoff

The primary annotator and independent reviewer must be external human contributors.
Do not contact them without user authorization. They must annotate/review every
selected image while blinded to candidate outputs, methods and scores. Preserve
primary revisions, review records and final adjudication; retain the 72/24/8/8
person-hour allocations separately. No reduced annotation set is accepted.

Complete the template with numeric, non-pickled `final_layers` NPZ files containing
`instances` (int32), `changing`, `valid` and `ignored` (boolean), all `[540,960]`.
Use -1 outside valid pixels, 0 background and positive visible truth instance IDs.
There is no 255-instance cap on human truth. Each `instances` metadata entry records
`class` (`person` or `basketball`), person `role` (`player`, `other-person` or
`uncertain`), and `visibility`, `occlusion`, `blur`, `tiny_ball`, `role_uncertain`.
Image `tags` contain `stationary_people`, `spectators`, `shadows`,
`changing_displays`, `illumination_changes`, `uncertain_motion`.

All file references use `{ "path": "/absolute/path", "sha256": "...", "bytes": N }`.
Contributors use distinct IDs, `kind: "external_human"` and an attestation file
reference. Review JSON binds `reviewer_id`, `primary_revision_sha256` and
`blind_to_outputs_methods_scores: true`. Adjudication JSON binds `review_sha256`,
`final_layers_sha256` and `unresolved_disagreements: 0`. Accepted images use
`status: "reviewed-adjudicated"`. Static-feature review entries retain the selected
`index` and mark `suitable` as true, false or `"uncertain"`.

Each pair lists all visible truth identities as `{ "first_id": ID_OR_NULL,
"second_id": ID_OR_NULL }`; null marks a real appearance/disappearance. IDs in
each frame must occur exactly once. Candidate tracking IDs are separate.

```bash
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id RUN_ID annotations --bundle /absolute/path/reviewed-annotations.json
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id RUN_ID admit --validation /absolute/path/validation.json
```

Annotation import consumes its single allocation and must not be used as an
iterative labeling tool. Validate the external bundle before that final import.
The Python `annotations.validate` function is available for synthetic implementation
fixtures. Admission currently remains blocked on the unfinished implementation
and runtime qualification even if annotations pass.

After an explicit user resume, previously blocked **unstarted** slots can be
reopened with `resume --authorization 'EXACT USER INSTRUCTION' --jobs JOB_ID ...`.
The ledger retains their earlier blocked records. This launches nothing and
cannot reopen any consumed attempt or replenish time/attempt allocations.

## Implemented interfaces and limits

- Exact diagnostic membership, immutable file hashes and forbidden-directory guards.
- int32 instances with complete native/normalized semantics; 255 usable-static PNGs;
  float32 camera-z/NaN validity; overlap precedence; focal conversion and grid helpers.
- Role-bounded M0/M1, chronological cold-start MOG2, and pair-static unions.
- Unchanged scale estimator and gates, common native OpenCV invalid-support checks,
  retained failed-camera records and hash-bound frozen checks.
- Positive-support N0/N1 and all seven N2 tuple terms; deterministic finalist and
  combined eligibility functions, with only the prescribed missing-class S2 default.
- Pixel/boundary counts, Hungarian instance matching, conditional person-role
  domains, precision bounds, temporal associations and camera/group paired bootstrap.
- Reused crop/sampling helpers and consistent scene-scale/normalization transforms.
- Atomic process reservations, hash-chained ledger, cumulative wall scopes,
  timeout/interrupt handling, process-group cleanup and injected resource boundaries.

GPU probes/transfer monitors, complete runtime isolation and all scientific output
metrics still require integration/qualification. Python audit guards are not an OS
filesystem isolation proof. Synthetic passing tests are not real-model evidence.

## Validation

```bash
.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p 'test_vipe_benchmark_*.py' -v
.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p 'test_basketball_scale.py' -v
.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p 'test_basketball_temporal*.py' -v
.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p 'test_basketball_dense_fusion.py' -v
```

48 focused tests and 15 existing scale, temporal geometry/crop and dense-fusion
tests passed at this checkpoint. No real model, GPU smoke test, calibration
regeneration, training update or final-window evaluation was run.
