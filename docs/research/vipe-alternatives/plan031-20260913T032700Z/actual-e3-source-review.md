# Actual E3 SAM3 source review

Reviewed the downloaded source at `sam3-access-resume-001/sources/sam3_source`, revision `660a5e9e1b8b4c02c0ad97229b88a09a6e4ff5b7`, against `SAM3Backend`, its image/video factories, E3 setup requirements and import qualification. AGENTS.md, Plan 031 and the frozen S3/E3 protocol rows were read. This is a new SAM3-only review, separate from the completed E4 review and SAM3 recovery review.

**Result:** no definite active-path signature or missing-default-dependency blocker was found. There is an image checkpoint qualification gap, and native backend/parallelism settings need explicit provenance. This establishes source compatibility only: checkpoint loading, native kernels, memory use and actual forwards remain unverified.

## 1. Preserve intended image checkpoint selection; reject an incomplete selected model

`sam3/model_builder.py:539–561` loads the verified local checkpoint with `weights_only=True`, unwraps its optional `model` dictionary, selects keys containing `detector`, and strips `detector.`. Tracker keys are remapped into `inst_interactive_predictor.model.*` only when that predictor is present. Our factory disables it, so excluding the full checkpoint's tracker state is intentional. The image builder invokes `model.load_state_dict(selected_detector_state, strict=False)`, prints missing keys, and discards unexpected keys. Our factory currently neither captures the incompatibility result nor rejects missing image-model weights.

Do not load the full video checkpoint with strict=True or add guessed key renames. Minimal guard: scope an observer around the selected image model's `load_state_dict` during the original `_load_checkpoint` call, leaving the upstream filter, remap, strict=False and single weight load unchanged. Require exactly the expected native load call and an empty missing_keys list; capture unexpected_keys and selected-key identity/count in provenance. Source declares no expected missing keys. Unexpected full-video tracker keys are excluded before this call, but source alone does not enumerate any legitimate unexpected detector keys. Therefore retain the native unexpected-key tolerance with disclosure rather than inventing an allowlist or falsely claiming an exact match. If unexpected keys affect confidence in qualification, fail explicitly for review; do not silently change the architecture. The first allocated load can provide actual key lists; this review did not read/unpickle weights and cannot prove that this pinned checkpoint currently has missing or unexpected keys.

The video path already supplies `strict_state_dict_loading=True`; native `model_builder.py:795–811` then rejects state-dict incompatibility. Both factories pass explicit local checkpoint/BPE paths and `load_from_HF=False`; original SAM3 builders are selected, not SAM3.1 multiplex builders.

## 2. API, state, grids and precision

- Image builder arguments match `model_builder.py:573–654`; processor arguments match `sam3_image_processor.py:17–39`. PIL input supplies correct original H/W (`set_image:42–73`). The processor resizes to 1008² with torchvision v2, normalizes float32 RGB by mean/std 0.5, applies the separate concept, thresholds returned instance probability strictly above 0.5, interpolates masks bilinearly to original H/W, and thresholds mask probability above 0.5 (`184–223`). Adapter conversion supports bfloat16 scores. It preserves the original-grid binary output and native returned score for deterministic merging.
- Video arguments match `model_builder.py:676–814`. `init_state:55–91` accepts a list of PIL images and all three supplied offload/async flags. `io_utils.py:31–96` resizes each PIL RGB to 1008², stores/normalizes it as float16, and moves it to CUDA. The adapter correctly discloses this native storage precision separately from bfloat16 autocast; it should also identify native PIL resize versus image-processor torchvision resize in provenance.
- Separate concept states are required because `add_prompt:839–906` resets the whole semantic state. Two-frame processing with start=0, max_frame_num_to_track=1, reverse=False yields indices 0 and 1 (`_get_processing_order:224–250`). The hotstart buffer is flushed at the end even for a pair shorter than the native 15-frame delay (`253–358`). Adapter finally resets each state and rejects missing, repeated or out-of-pair outputs. Its identity mapping retains concept namespaces and records births/disappearances.
- `out_obj_ids`, `out_probs`, and original-grid boolean `out_binary_masks` match `_postprocess_output:432–524`. Native within-concept overlap suppression uses tracker probabilities before the adapter merges concepts using returned instance scores. Preserve both stages; do not replace native overlap handling. Native video defaults include detection threshold 0.5, birth threshold 0.7, hole area 16 and temporal-disambiguation heuristics. These are retained, not tuning opportunities. Native max_num_objects defaults to 10000 (`sam3_video_base.py:349–355`); adapter's 255 checks are its contract capacity, not this native default.
- Native `_compile_model:573–579` returns immediately for compile_model=False; original builder attention defaults disable FA3. Native Triton kernel JIT/autotuning can still occur on first use: `compile=False` means no model torch.compile, not absence of native kernel compilation. No warm-up model call is authorized by this review. Native module import enables TF32 on supported CUDA hardware (`model_builder.py:54–64`); record actual flags without changing them.

An unused public-API edge case exists: `_setup_device_and_mode:564–570` calls model.cuda() only for the literal device `cuda`; our public backend also accepts `cuda:0`, which would leave the image model on CPU. The controller explicitly supplies `cuda`, so this does not block the planned job. A future narrow fix can normalize that spelling or explicitly move the built model; it needs a fixture, not a model probe.

## 3. Setup dependencies and fallback guards

`pyproject.toml` core dependencies are covered by E3's recipe, with torch 2.10.0+cu128, torchvision 0.25.0+cu128, Python 3.12 and NumPy 1.26.4 unchanged. Extra core import/runtime dependencies einops, pycocotools, psutil and scipy are explicitly included. model_builder imports pkg_resources, provided by the existing setuptools 80.9.0 pin. No mandatory source CUDA extension build was found for this selected path. Hydra is inside an unselected multiplex constructor; decord/torchcodec video-file loaders and skimage CPU connected-components are not used by the selected two-PIL-frame CUDA path. No reason was found to install optional training/notebook/application extras or FA3.

Native `perflib/connected_components.py:73–87` selects cc_torch when available, otherwise bundled Triton for CUDA input; CPU input selects skimage. `perflib/nms.py:65–73` similarly selects torch_generic_nms or bundled Triton on CUDA. Neither catches a Triton execution error and returns unprocessed masks. `sam3_tracker_utils.py:372–444` invokes connected-components directly, unlike the reviewed SAM2 warning-and-skip path. These are native implementation selections, not evidence that the optional extensions must be installed. Current setup import qualification verifies builder/processor classes but does not import the lazy Triton kernels. Add import-only checks for the bundled connected_components_triton and nms_triton entry points to expose missing dependency/import problems inside setup, with no kernel launch or model construction.

Existing guards reject absent/changed assets, unavailable CUDA/bfloat16, network requests, missing APIs, malformed masks/IDs and too many returned objects. They do not currently record or reject inherited `USE_PERFLIB` changes, unexpected native rank/world_size, or a changed optional CC/NMS backend. Source reads `USE_PERFLIB` (default 1) and rank/world size (defaults 0/1); supervisor inherits the environment. For the intended serial original-builder path, record/check actual perflib state, model/detector rank=0 and world_size=1, compile flags, FA3 flags, and CC/NMS backend selection. Do not silently compensate with other versions, optional accelerator installation or altered thresholds. Current flash-attn package inventory rejection is useful but alone does not identify every selected native backend.

## Evidence limits and fingerprints

Only targeted source/config reads and stdlib AST inspection were used; the conservative local import graph included 63 Python files, including some unselected lazy branches, solely to identify dependencies. No SAM3 module import, builder, model operation, weight read, GPU probe, network, build, source edit, active-tree mutation, ledger edit, delegation or commit occurred. No prompts directory content was read. No tests were run. The sole output is this document. Native import success, exact checkpoint compatibility, numerical output, kernel success and memory ceilings remain for their allocated qualification/execution.

SHA-256 of selected exact source evidence (relative to source root):

- `sam3/model_builder.py`: `d71d6d3e485ec3eae48bbc2ba676f401b5853d65c4195a91d077b04da38121c2`
- `sam3/model/sam3_image_processor.py`: `d8738a0efb6138b01c0dc5deceffd29de9e675860a9a1ed3822b08766373333b`
- `sam3/model/sam3_video_inference.py`: `70d32ec094b3151aa5b5e73e1c0dd13bc5e7a06ab51fc6b1776909e9ad501aef`
- `sam3/model/sam3_video_base.py`: `7ffae0a8c15f17814ce438078b6a00cc052be21ad16c8a59205df859c3df52c4`
- `sam3/model/io_utils.py`: `8bf0d036bc616a2429a258fa3a91d733e7c64621fe1616fa0c129c29c0fca637`
- `sam3/model/sam3_tracker_utils.py`: `dc5fdeba2d4416f273394a9bd4450dff050608db6009a4546ca68adbaa24a640`
- `sam3/perflib/__init__.py`: `e25fa5fb31908e816f0ce0f55dae8715076f47ca9ffcbc34335e60cf74bfbd21`
- `sam3/perflib/connected_components.py`: `f09bb5b905a12e0aeb6e7f1096af839015230f007dc47c43a1de7893a355dbd1`
- `sam3/perflib/nms.py`: `21c5fd8c12f9a8bacf5b17be1c0a0027533f9f7dca31392a0c90fc0df2d25eb4`
- `sam3/perflib/triton/connected_components.py`: `4326366c3575aa29c23ea4c4060534361d2920492312a20ad5138ac3dcf45c48`
- `sam3/perflib/triton/nms.py`: `e9749ee2e49acf3665e7aade92acbdbff7e0685d2c1feae40f2c231a94e5c8c3`
- `pyproject.toml`: `255f5d8d1db011459878e3de296a6afc84e03a8dda2bfa756a4de304aaff6366`

Repository code fingerprints at review completion (parent may subsequently change these):

- `scripts/vipe_benchmark/backends.py`: `07950cc9a9019886d00a0eec2f34f2c5268558f52e93c2016042e42d8823800b`
- `scripts/vipe_benchmark/setup_recipes.py`: `fc56ac8cffc625c82251194d4578aa1f4ce9b1ffd90723792b53351fca6c027e`
- `scripts/vipe_benchmark/runtime.py`: `c2ccce3f4dac21440973b705b9358e35fd1e84243549527ec7f2dad92cfd7020`

Review start: 2026-09-13T08:29:41+00:00. End: 2026-09-13T08:36:37.550295+00:00. Conservative full wall elapsed **416.550 seconds**, idle 0, within the new 480-second allocation.
