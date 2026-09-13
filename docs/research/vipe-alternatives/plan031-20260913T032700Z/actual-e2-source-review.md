# Exact E2 source review

Review of S2/S4 against E2's exact downloaded assets and the validation004 adapter baseline (`6cebada`, 254 CPU tests). **One concrete failure-handling gap was found; no additional inspected API, config or grid mismatch was identified.** E2 subsequently failed during source extraction and was cleaned up, consuming its sole setup attempt. S2/S4 remain blocked under that allocation. This review did not rerun or repair E2.

## Finding: native postprocessing fallback can be mislabeled as success

`sam2/utils/misc.py:312–338` catches any exception from connected-components hole filling, warns that it is skipping postprocessing, and returns the original unfilled logits. `sam2/sam2_video_predictor.py:783–788` invokes this function whenever `fill_hole_area>0`; the exact video builder sets that area to **8**. Importing `sam2._C` successfully in our `_sam2` factory is insufficient to prove the CUDA kernel subsequently runs. Therefore an unavailable kernel/device implementation or runtime kernel error can return masks as success while our output metadata still advertises the prescribed hole filling. This is a confirmed source-level fallback path, **not an observed CUDA failure**; no native model or kernel was executed.

A narrow future adapter fix is to turn only the native `UserWarning` containing `Skipping the post-processing step due to the error above` into a failure within S2/S4 native inference. Its message begins with the original exception and may contain newlines, so matching must account for that prefix. Preserve other warnings, thresholds and native postprocessing. A fake video predictor should emit that exact warning and verify failure plus pair-state reset and no successful result; normal warning-free inference should remain unchanged. The image transform contains the same catch/warn pattern, but its default hole/sprinkle areas are both zero in the selected image predictor, so the configured video path is the relevant active case. No code was changed during this review.

## Exact API/config checks

- `build_sam2` and `build_sam2_video_predictor` accept every supplied keyword, including `mode='eval'`, `apply_postprocessing=True`, Hydra overrides and `vos_optimized=False`. The selected config path resolves to the regular member `sam2/configs/sam2.1/sam2.1_hiera_l.yaml`; it does not require the aliases that caused the extraction failure. Hiera-L has the expected [2,6,36,4] stages and `image_size=1024`. Both the native config and adapter disable image-encoder compilation, and the ordinary video predictor is selected. Native preprocessing internally scripts its resize/normalize transform; no alternate model compilation path is requested.
- The exact builders apply the recorded stability settings (enabled, delta 0.05, threshold 0.98), video mask-memory binarization and fill-hole area 8. Native state loading is strict and uses the explicit `sam2.1_hiera_large.pt` checkpoint. Weights were not opened or unpickled, so successful loading remains unverified.
- `SAM2ImagePredictor.set_image` resets the prior image state. Its default coordinate normalization accepts original-pixel XYXY boxes, rescales them to the 1024 grid, and with `multimask_output=True, return_logits=True` returns CxHxW **original-grid** logits plus IoU scores. Our highest-IoU selection and threshold-after-restoration agree with this API. Image hole/sprinkle defaults are zero.
- `init_state(video_path=folder, async_loading_frames=False)` creates fresh dictionaries and warms only frame 0. Native folder discovery sorts numeric JPG filenames; decoding uses Pillow's content-based `Image.open(...).convert('RGB')`. Thus the adapter's lossless PNG payloads in its two numerically named JPG files are supported by the exact loader. The loader uses native square resizing and ImageNet normalization; it retains the original height/width for export.
- `add_new_mask` accepts the supplied two-dimensional NumPy boolean masks and stable IDs. Native mask initialization performs its own bilinear/antialiased resize and >=0.5 binarization. All initial objects are added at frame 0. Propagation preflight consolidates their conditioning outputs and encodes each object's memory with batch size one.
- For `start_frame_idx=0, max_frame_num_to_track=1, reverse=False`, the exact inclusive range is **[0,1]**. The return order is `(frame_idx, obj_ids, video_res_masks)`, with N x 1 x original-H x original-W logits restored by native bilinear interpolation. The adapter correctly selects/reorders frame 1 by IDs. Native output non-overlap enforcement defaults false, leaving the preregistered greatest-logit merge to the adapter. `reset_state` clears object IDs and tracking state; each pair gets a new state object. Empty detector results avoid the native zero-object preflight error without rerunning the successor detector.
- Detector inference is enclosed in float32 invocation; SAM image setup/prediction and video initialization/mask addition/propagation are enclosed in the existing bfloat16 autocast context. Native video memory storage explicitly uses bfloat16. No extra precision conversion, image grid or propagation step is introduced by the adapter.

## Grounding DINO and RT-DETR metadata checks

The completed Grounding DINO source supports the native predict signature, normalized cxcywh boxes/scores/phrases, 800/max-1333 preprocessing and local BERT loading used by S2. Thresholds remain box 0.35 / text 0.25. The exact RT-DETR config maps `person=0` and `sports ball=32`, specifies float32, disables custom kernels and pretrained-backbone loading; its processor metadata specifies 640x640, rescale 1/255, no normalization and no padding, matching S4. The model class is chosen explicitly rather than relying on metadata architecture-name capitalization. SAM2 checkpoint-repository processor sidecars do not control this native SAM2 adapter.

E2 failed before its dependency environment was qualified. Actual installed Transformers 4.51.3 API/postprocessing and Grounding's transitive BERT compatibility were not established by this source/metadata review. Complete checkpoint compatibility, compiled kernels, peak memory, numerical results and first-forward behavior remain **unverified**. No model/native package imports, weights reads, inference, builds, installs, downloads, source/tests changes, active-tree mutations or ledger changes were performed. The retained archive was read only for explicitly selected regular source/config members; no file was extracted to disk. All prompts directories were excluded without reading their contents.

## File fingerprints

Existing completed files, relative to `.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E2-setup/`:

- `sources/grounding_source/groundingdino/util/inference.py`: `0c06c5dd2fa46ae89a9fa376c0eaa383d12e7fc21aa65d662bcf3e758d26b598`
- `sources/grounding_source/groundingdino/util/get_tokenlizer.py`: `bedc47db390249eb2230c2031b114d1d5f470ed6dbc1d3905e97e742289cb3b3`
- `sources/grounding_source/groundingdino/models/GroundingDINO/bertwarper.py`: `7cbd090859e211a42763d34d1a9ae54378a2d0f3c59065717b90e814b672b917`
- `sources/grounding_source/groundingdino/config/GroundingDINO_SwinT_OGC.py`: `172e80017f9395668a9cb5d1b8bd9d061c0e360471c6ed673c83b69bb14399f1`
- `snapshots/rtdetr_snapshot/config.json`: `d754c04c9a4c6d015d8393fa2dae4c63f4a9f0ba173c3d1a66e55cff59d8f060`
- `snapshots/rtdetr_snapshot/preprocessor_config.json`: `cd38cd59999e7a95d68e487fbe5132df3d4e5c32a0836add57e6126ba0c4eaf1`
- `snapshots/sam2_checkpoint/preprocessor_config.json`: `6ebf229ee259368ce4a8d4f2fe893a72b053023710853e257253939e601f583d`

Selected regular members of retained `archives/sam2_source-2b90b9f5ceec907a1c18123530e92e794ad901a4.tar.gz` (one pinned archive-root prefix omitted):

- `sam2/__init__.py` (395 bytes): `b87ca1e95cd54b81766e8c74acf0e937952639529e40d2b4088693286f49419e`
- `sam2/build_sam.py` (6405 bytes): `856d64d71e44407401297b551884fb4cd1aba8082de0ff5fc60fac3dd42f094d`
- `sam2/configs/sam2.1/sam2.1_hiera_l.yaml` (3798 bytes): `1dbd6cb6dfebeaf588c7006ee222c6efbfa9049a7ad472a3cdfb2f5d919e8107`
- `sam2/modeling/sam2_base.py` (46983 bytes): `69a46b44e8625f509791352bd09beaafe589cd7d872721384e63d37f9fdc6e41`
- `sam2/sam2_image_predictor.py` (19937 bytes): `f13e5f9d94e5c8d9d2c3622dab20c8f334c089ef2ee5ea8e199da7d332b029ba`
- `sam2/sam2_video_predictor.py` (58921 bytes): `912555920a77f72ded07839efa33fcceecc79f3523abbec783f0be46ee2c55c2`
- `sam2/utils/misc.py` (13090 bytes): `01600c01c161cd079d7106fb1d4da845cf91aa31ab2bcecaf8cb151b6d6d20a2`
- `sam2/utils/transforms.py` (4885 bytes): `ba3a64f4600c62f209206a6df3b40e3fcf133edae32fad658831bb0c2a6d1146`

## Preparation accounting

- Initial review began **2026-09-13 06:11:35 UTC**; the intermediate handoff conservatively charged **295.760 active seconds** through 06:18:16.759764 UTC, including handoff preparation.
- Completed initial idle intervals: 06:13:10–06:14:02 UTC (52 seconds), and 06:14:58–06:15:52 UTC (54 seconds).
- Waiting for acquisition/source review authorization: **06:18:16.759764–06:34:59 UTC** (1002.240236 seconds). No active inspection was charged during that pause.
- Resumed read-only review: **06:34:59 UTC–06:39:00.454023 UTC**, **241.454 active seconds**.
- Total conservative active preparation: **537.214 seconds**, below the **600-second** cap. Total recorded idle: **1108.240236 seconds**. No extra model/setup attempt was consumed by this review.
