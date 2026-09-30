# Qualitative package interface (#30)

`scripts/vipe_benchmark/qualitative_package.py` exposes `validate(manifest)` (also `validate_package`) and `publish(manifest, new_directory)` (both accept the optional monotonic `deadline` keyword). Publication refuses an existing directory and emits immutable `package.json`, `viewer.html`, and `result.json`. Assets remain at their hash-bound local paths; keep those paths available while reviewing. Open `viewer.html` directly in a browser. No service or network access is required. Export downloads a human review JSON; it does not change the package or mark a review complete.

## Manifest v1

- `schema`: `plan067-qualitative-package/v1`; `mode`: `qualitative`; `id`: unique frozen package identity; `record_kind`: `actual` or `fixture`.
- `bindings`: source, config, inputs and amendment, each a canonical `{path, sha256, bytes}` file record.
- `settings`: `fps:25`, `resolution:[width,height]`, named `color_handling`, frozen `crop:[x,y,width,height]`, `detail_regions:[{id,crop}]`.
- `selections`: `{id,kind:frame|clip,role:reconstruction|calibration|selection,camera_id,frame_ids,timestamps}`. Frame IDs retain accepted role ranges (0–49, 50–149, 150–199), ordered unique membership and original `frame/25` timestamps.
- `candidates`: `{id,label,is_control,stage,output_type:reference|component|final-render,status:available|failed|blocked|missing|unavailable,reason,provenance,media}`. Available provenance contains source_result, ledger_outcome and configuration file records. Actual mode additionally requires request, generation_result and generation_manifest bindings and delegates semantic receipt validation to qualitative_generation.validate_actual_package: successful source outcomes, accepted input/camera/result row bindings and deterministic generated-media lineage must agree. Fixture provenance cannot be promoted by changing record_kind. Missing/failed arms need reasons. Failed partial media can only be diagnostic.
- `media`: `{selection_id,kind:frame|clip|sequence|diagnostic,record,frame_ids,timestamps,resolution}`. Frame and diagnostic media must be fully decodable PNGs. Video must fully decode with exact declared frame count/resolution and 25 fps. Nonconsecutive source frames require `sequence`; the viewer labels their slideshow and excludes them from common motion playback.

Validation rejects substituted hashes/sizes, frame/time/resolution mismatches, corrupt assets, duplicate identities and out-of-bounds crops. A shared non-diagnostic selection for available control and candidate produces `ready-for-human-review`; otherwise the package is a `readiness-inventory`. Neither state means a human has reviewed it.

The viewer provides matched selection, shared crop/zoom, original media access, synchronized continuous clips, explicit unavailable states, artifact hashes, stage/output labels and a blank human observation form. The exported review schema is `plan067-qualitative-review/v1` and is separately validated by the review module. No opinion is prefilled. Sparse sequences and component visualizations do not establish continuous motion or final-render quality.

## Validation

Public package publication tests use small synthetic PNG/MP4 assets and fake provenance records marked `fixture`. Nine tests cover exclusive publication, readiness, changed hashes, invalid crop/roles/metadata, absent arms, corrupt PNG, complete video decoding/frame counts sparse sequence handling refusal to promote fixture bytes to actual packages, expired publication deadlines and subprocess thread/deadline bounds. These fixtures are engineering evidence only. AST parsing and generated JavaScript syntax checks supplement the tests; no configured static typechecker was available in this lane.

Publication shares its caller's monotonic deadline: each media check runs before/after validation, and ffprobe/ffmpeg decode receive at most the remaining time or 30 seconds. Decoding uses one worker thread. Standalone fixture validation retains the per-subprocess 30-second bound.
