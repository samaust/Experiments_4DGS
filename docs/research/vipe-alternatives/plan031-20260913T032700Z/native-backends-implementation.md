# Plan 031 native backend implementation

Implemented [backends.py](../../../../scripts/vipe_benchmark/backends.py) and
[CPU fake-native tests](../../../../tests/test_vipe_benchmark_backends.py).
No model inference, checkpoint download, environment build, GPU probe, staging
or commit was performed by this implementation subtask.

The public factory is `build_backend(component, assets, device='cuda')`.
`REQUIRED_ASSETS`, `SOURCE_PINS` and `SNAPSHOT_PINS` expose the asset contract.
Every file has an explicit path and SHA-256. A directory also has its frozen
revision and a nonempty list of hashed files. HF snapshot symlinks must retain
their logical snapshot paths in those records; the hash follows the target
bytes. Source imports are checked against the declared source directory.
Runtime qualification, complete source/dependency inventories, licenses,
isolation and immutable file output remain responsibilities of the controller.

Segmentation uses `segment(images, valid, frame_ids=[...])` for one snapshot or
one adjacent reconstruction pair. Each `SegmentationResult` contains int32
`labels`, `semantics`, boolean `valid`, native `metadata`, and optional numeric
`diagnostics`. Its `static(changing)` method creates the uint8 0/255 static mask.
Depth uses `predict(rgb, K, valid)` and returns `DepthResult` with float32
`depth`, boolean `valid`, optional float32 `confidence`, `raw_depth` and metadata.
The controller supplies identity, RGB/config hashes and serializes the arrays.

| Arm | Implemented native boundary |
| --- | --- |
| S0 | Original ViPE tracker and frame type; fresh tracker per context, shared weight cache; exact local asset bindings. A forward hook retains actual detector scores before the historical uint8 merge. |
| S1 | Native upstream Grounding DINO, SAM-B predictor and SAM-Track `get_aot`; upstream two-pass box refinement, integer box truncation, later-mask overwrite, one successor, reset before and after each pair. No automatic-mask minimum-area filter is applied to box masks. |
| S2 / S4 | Native Grounding DINO or Transformers RT-DETRv2 processor/model; SAM 2 highest-IoU original-grid logits and fresh video state initialized from the selected masks; detector-score/index overlap ties. |
| S3 | Original SAM 3 image/video builders; separate person/basketball states, native births, score/semantic/native-ID overlap merge. Models load lazily by branch. |
| D0 / D1 | Original ViPE wrapper or official camera-aware UniDepth `infer`; native processed dimensions observed without another forward pass; D0's reconstructed centered K retained in metadata. |
| D2 | Official input processor, tensor preparation, forward and output processor. Actual processor K supplies one canonical focal conversion; no extrinsics, pose alignment or camera-dependent export. |
| D3 | Local native `metric3d_vit_large` hub builder with `pretrain=False`, exact local state dictionary, native fit/pad/normalization, resized-focal conversion and [0,300] metre clamp. |
| D4 | Native Depth Pro model/transform/infer with float32 device `f_px`. Exported native depth is not scaled again; observed canonical inverse depth supports clamp diagnostics. |

S0/S1 keyframe diagnostics contain `detector_rgb` (actual standardized CHW),
`detector_raw_token_logits`, `detector_raw_boxes_cxcywh`,
`detector_selected_boxes_xyxy` and `detector_selected_scores`. S1 retains all
detection phrases in metadata; S0 retains its native phrase map. Successors
reference the keyframe's `diagnostics_source_frame` without duplicating arrays.
These observations introduce no additional forward passes.

SAM 2's native loader discovers JPG filenames. Temporary JPG-named files contain
lossless PNG payloads, which PIL decodes to the exact admitted RGB before native
preprocessing. SAM 3 uses its native list-of-PIL-images resource loader.

Validation: `.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p
'test_vipe_benchmark_backends.py' -v` passed 21 tests. Tests use only CPU arrays,
OpenCV/Pillow and fake native objects. They check actual call arguments, byte
NCHW/K forwarding, factory local-only loading, extension requirements, pair
resets, tiny masks, overlap ties, missing successor failures, native scores,
processed-K scaling, invalid interpolation support and native clamp behavior.
This does not establish native installation compatibility, GPU runtime, output
quality, physical accuracy, or asset permissions.

Native source inspection used the exact source revisions listed in the
[study](../../vipe-alternatives.md#6-source-and-asset-pins), the existing ViPE
checkout, and exact pinned primary-source files. UniDepth's official `infer`
has an internal float16 autocast decorator despite a float32 invocation; that
behavior is preserved and disclosed. SAM-Track's AOT imports require the pinned
source subtree to be exposed under its original package layout. The adapters
reject missing native SAM 2/AOT extensions rather than allowing their native
silent fallbacks. See [runtime recommendations](native-runtime-recommendations.md)
for the unexecuted dependency/build handoff.
