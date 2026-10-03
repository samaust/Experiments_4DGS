# Verified final-render inputs (#34)

The geometry observation-loader seam now has a CPU implementation in
`scripts/vipe_benchmark/final_render_loaders.py`. Omitting `observation_loader`
from `final_render_geometry.run` selects this loader. Injected fixture loaders
remain available. The geometry worker verifies accepted request/manifest/native
row membership before loading any observation.

## Observations

`load_observation(source, S2_row, M_row)` checks exact source RGB identity,
OpenCV K, reconstruction grid, pair context and the shared footprint file record.
It hashes the same bytes that it decodes, verifies recorded size and refuses
changed files. Inputs are capped at 64 MiB per file; NPY headers must describe
exactly the accepted 540×960 grid and dtype before allocation.

Outputs are uint8 RGB, boolean footprint, int32 pair-local instances and boolean
changing regions. Native S2 instance semantics remain authoritative. Its static
PNG must be grayscale uint8 0/255, with 255 exactly where the footprint is valid
and the instance is zero. Motion may contain changing pixels outside the valid
footprint, matching the existing native motion contract; the loader preserves
those pixels. No cast, resize, RGB conversion, K adjustment, undistortion,
morphology or static/motion aggregation is performed.

## Selected depth

`load_selected_depth(request, camera, frame)` revalidates the frozen human D*
decision and engineering eligibility, then checks exact accepted inputs and
fit/check records. It reads only a unique anchor present in that accepted input
manifest and in D*'s frozen generation. D2 anchors outside its four published
clips can come only from the exact historical fit/check evidence bound by the
same decision. Missing predictions fail explicitly; another candidate, another
frame or cached map is never substituted.

`load_metric_depth(source, native_row)` validates source/inference RGB lineage,
scale grid, available K, camera/frame identity and camera-z metres. Video anchor
rows without a separate K or grid retain their frozen accepted-input calibration.
Their source RGB can reference the original accepted distorted RGB; their
published depth is already remapped by the producer. NPZ contents have a 64 MiB
expanded limit, at most 16 unique members and exact depth/valid/optional confidence
array headers. Depth remains float32 metres, valid positive finite camera-z;
invalid pixels remain NaN and validity cannot extend past the image footprint.
No focal conversion, fit-scale multiplication, interpolation or normalization is
applied a second time.

These depth readers expose existing fit/selection anchors for supporting
geometry inputs and diagnostics. The RoMa geometry algorithm uses D* through its
frozen physical camera scale and does not fuse depth pixels. Existing depth
comparison jobs do not generate reconstruction-window depth maps. This change
creates neither those maps nor a different initializer algorithm.

## Validation and execution limits

CPU tests exercise the existing observation loader/worker and review decision
boundaries with real PNG/NPY/NPZ fixtures: unchanged RGB/instance/motion values,
static polarity, file substitution, grid/K/footprint substitution, unsafe dtypes,
metric support/domain, frozen candidate choice, missing anchors, compressed
archive limits and NPY allocation bounds. No GPU or model setup is involved.

Readers confer no admission or execution authority. Actual geometry still needs
a qualified native matcher, current source qualification, supervised dispatch
and shared ledger/resource checks. The existing geometry worker remains fixture
only. #34 remains open for that work and actual final renders.
