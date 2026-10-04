# Native full-rig matcher worker (#34)

`final_render_matcher.prepare_inventory` freezes explicit local checkout, weights,
interpreter, environment and dependency file records without importing Torch.
It requires the unchanged EDGS RoMa revision and the two exact historical weight
hashes. Tracked checkout files, audited geometry and loader sources and complete
installed dependency files are bound. Dependency records must include METADATA,
RECORD and every listed file except bytecode and forbidden `prompts` content.
Exactly one installed OpenCV provider, `opencv-python` or
`opencv-python-headless`, is required. Both supply the unchanged `cv2` matcher/LK
interface; inventories containing both providers are rejected because their files
overlap. All other required distributions and complete file bindings remain
mandatory. A headless custom recipe must document substitution of upstream
RoMa's `opencv-python` dependency spelling and satisfy its complete actual
inference dependency closure; this acceptance does not resolve/install packages.

Preparation is neither qualification nor execution permission. Regenerate the
inventory after integration changes any bound source.

`NativeGeometryBackend(inventory_record)` only verifies prepared bytes. The first
model operation requires a centrally validated `final_render_admission.worker_binding`
for the exact request, arm, geometry phase and matcher inventory. The inventory
is rehashed again immediately before loading, including the active interpreter,
environment and installed distribution identities. The unchanged
`diagnostics.NativeBackend` loads pinned offline CUDA RoMa, uses its original
sampling threshold, asymmetric coarse matching, person crop refinement and
float32 CUDA local triangulation solver. No CPU fallback or alternate SDK exists
in the actual path.

`final_render_geometry.run(..., invocation_record=...)` accepts actual requests
only through the exact native backend and central immutable worker invocation.
The actual path requires the verified observation loader and unchanged OpenCV LK.
The existing fixture seam remains injectable and cannot consume an actual
invocation. It computes the same 810 edges and retains all geometric gates,
physical velocities, normalization and immutable NPZ/source lineage.

Native geometry receipts bind the invocation and matcher inventory. Per-edge
resource checks enforce the request CPU/device ceilings; synchronized native
measurements retain actual CUDA timings. Internal geometry elapsed time includes
model loading. The supervised dispatcher independently accounts all preparation,
publication and cleanup time and samples the entire process tree/device, since
phase measurements alone are lower bounds. Worker cleanup releases the model
on success or failure; cleanup exceptions retain the original failure as primary.
The parent actual worker publishes and validates the common worker result after
cleanup. Partial geometry files are preserved when any phase fails.

CPU tests cover guard rejection and unchanged array geometry. They do not establish
native qualification, runtime performance, resource sufficiency or actual final
renders. Live execution needs the separately reviewed DO envelope, qualification,
started shared-ledger allocation and supervisor-controlled fresh process.
