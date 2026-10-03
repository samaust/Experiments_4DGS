# Selected-depth CPU pipeline preparation (#34)

This extends the agreed worker request/result and initializer-to-model seams for
Plan069. It does not execute native geometry, training, reload or rendering.

## Extended initializer assembly

`final_render_initializer.assemble(request, arm, geometry_record, width_record)`
accepts the existing `plan069-final-render-request/v1` REVIEW contract. It uses the
new request parser and scene validator, retaining the historical Plan067 route.

Future geometry records use `plan069-final-render-geometry/v1`; width records use
`plan069-final-render-voxel-width/v1`. Both bind the exact request and bound scene.
Geometry binds S2, D_fit, D_check, depth_decision and the arm's M/N results. It must
cover all 810 edges and accepted source-row identities. Historical schemas,
substituted scenes, incomplete/duplicate/held-out edges and stale D4 prerequisites
are rejected in the new mode. The width and static prior retain their source
archive/receipt lineage and historical scene scale.

The shared assembly keeps rotated physical positions and measured velocities,
the two-second velocity conversion, deterministic static fusion, nine static time
copies and every foreground observation. Its new result schema is
`plan069-final-render-assembly-result/v1`. The nested initializer receipt passes
the existing extended validator, including exact independently checked D* scale
and input evidence. All five arms share D* and the same width basis.

`prepare_model_input` now accepts either the seven native/region/validity fields,
or those fields plus both assembler-generated `physical_static_id` and
`foreground_observation_id`. It rejects a partial pair or arbitrary extra fields.
Signed per-point IDs must agree with static/foreground membership and foreground
IDs must be unique. The full source hash includes them; reported sidecar fields
and CPU byte counts retain them. Only the five native arrays reach the model data
boundary. These IDs identify fused static points and foreground observations;
they do not establish cross-camera person identity.

## Fixture worker outcome chain

`final_render_pipeline.validate_worker_result(request, arm, phase, result)` and
`validate_pipeline(request, arm, records)` implement the CPU fake-runtime result
seam. They accept fixtures only; actual requests/results are explicitly rejected.
The same existing phases and allocation ceilings apply: geometry, initializer,
train, render. Reload is part of render and gains no separate allocation.

`plan069-final-render-worker-result/v1` has exact common fields: schema,
record_kind, status, arm, phase, composition, request_sha256, allocation_id,
parent_result, elapsed_seconds, peak_device_bytes, artifact_bytes,
cpu_workers_used, execution_authorized, native_adapter_qualified and artifacts.
The authority/qualification flags must be false. Deadlines and resource fields
must have finite, correctly typed values within request limits. Published artifact
bytes must be covered by the storage claim. Artifact records are rehashed.

Each result consumes the exact complete predecessor record from the same arm,
request and composition. A missing tail is blocked; skipped stages, substituted
predecessors and continuation after failure/blocking are rejected. Failed/blocked
results add a substantive reason and retain their partial artifact records.

Complete training adds completed_iterations (exact integer 5000) and a published
checkpoint record. Complete render adds checkpoint, reload_validation, iteration,
render_settings and rendered_frames. It must consume that training checkpoint,
bind a `plan069-final-render-fixture-reload/v1` receipt for the exact checkpoint,
request, arm and 5000 endpoint, and bind exactly 200 unique camera/frame RGB
records under the unchanged resolution/fps/settings. The reload receipt remains
explicitly fixture; this validates the integration contract and performs no native
checkpoint inspection or media-quality validation.

The resulting `plan069-final-render-fixture-pipeline/v1` summary always declares
execution_authorized=false, native_adapter_qualified=false and
actual_final_renders=false, including a complete simulated chain. Fixture media
and checkpoint descriptors cannot satisfy human final-render review or #35's
actual publication gates.

## Remaining gates

#45/#62 must deliver actual package-bound eligible metric D* before new depth-
dependent execution. Actual selected-depth reconstruction outputs and full-rig
geometry/physical-velocity production, supervised native training and checkpoint
reload/render adapters, source/runtime/license qualification, measured viability,
approved DO allocations, live single-GPU admission and real matched final renders
remain unfinished. The human then compares motion and neighbor effects on those
renders. Existing Plan027 arm restrictions and `load_frozen` were not bypassed.

This preparation consumes no allocation or ledger identity and claims no measured
native runtime, actual output, quality winner or issue completion. #34/#35 remain
open. The other agent retains #44/#56–#59 execution and integration ownership.
