# Actual E4 source review

Read-only review of D1 against UniDepth revision `8d8cfe4c7ee15297099983607febf0d4f32eb3d6` in the E4 setup source tree and historical snapshot `52b349b514bd8b47642f67ac78cb7b5dc5c51dd9`. AGENTS.md, Plan 031 and the frozen study/protocol were read. No models were imported, constructed or run; no weights were read/unpickled; no network, builds, extraction, active-tree changes or ledger edits occurred. Only this review document was written. No prompts content was read.

## Concrete findings

1. **Correct confidence metadata for both D1 and D0.** The official `assets/docs/V2_README.md:15–16` describes the output as estimated scale-invariant log error, relative within one input and without absolute calibration. Accordingly, lower means less predicted error. Current `UniDepthBackend` metadata says higher is more confident, which reverses the documented meaning. Official decoder `unidepth/models/unidepthv2/decoder.py:444–461` exponentiates the clipped logconfidence head. Historical decoder `models/unidepthv2/decoder.py:418–428` has the same output transformation; historical wrapper `__init__.py:62–71` passes that confidence through unchanged, using the same checkpoint. Recommended metadata: meaning `native estimated scale-invariant log error; within-image relative uncertainty`, direction `lower is more confident`, calibration `uncalibrated; never used to filter or weight scale support`. Preserve raw values. This is a source-based semantic conclusion, not an empirical calibration result. The snapshot names Regression for its confidence training loss; this review does not claim its training path was executed or validated.

2. **Describe the native rounded grid precisely; preserve its preprocessing.** Official `unidepthv2.py:61–77` chooses a pixel-bound scalar, then rounds each image dimension upward to a multiple of 14 without recomputing that scalar. `infer:239–340` resizes RGB to those rounded dimensions but resizes K using the original scalar. `utils/coordinate.py:4–10` samples half-integer pixel centers. For frozen 540×960 images, snapshot bounds 200000–600000 pixels and ratio 0.5–2.5 require no padding or scalar enlargement; native model RGB is nevertheless **546×966**, with scalar 1 applied to K. The existing encode_decode observer correctly captures actual processed shape. Recommended provenance: `native_pixel_centers: half-integer (0.5, 1.5, ...)`; `native_resize_policy: pixel-bound scalar followed by independent ceil-to-14 image dimensions; K uses the pre-rounding scalar`; retain actual shape and invocation/input K. Do not add a new coordinate conversion or assert K was scaled by the rounded dimension ratios. Native postprocess restores original image shape bilinearly. D0 retains its separate historical K reconstruction: wrapper `__init__.py:44–60` uses fx for both focal lengths and centers the principal point, ignoring supplied fy/cx/cy. Record that historical behavior explicitly, without changing it.

## Compatible source-level calls and setup scope

- Official `UniDepthV2` inherits PyTorchModelHubMixin. The selected factory class and `from_pretrained(local_snapshot, local_files_only=True)` match the documented API. Snapshot config selects the current UniDepthV2, DINOv2 ViT-L14, and `pretrained: null`; encoder/backbone source therefore does not fetch independent backbone weights. No resolution_level attribute is created by this revision, so the adapter's absence guard passes. Bilinear mode and default snapshot pixel bounds agree with Plan 031.
- infer accepts uint8 NCHW RGB and a batched 3×3 K tensor, wraps K as a Pinhole camera, normalizes RGB, and restores outputs to original dimensions. Decoder uses supplied camera rays when provided. Returned depth is the last coordinate of 3D points, so camera-z metres pass through without another focal scaling. The observed encode_decode input remains available for actual grid/dtype capture.
- Float32 invocation/parameters coexist with the native float16 CUDA autocast decorator (`unidepthv2.py:239–240`; historical fork:231–232). Preserve this distinction in provenance. Native camera inversion explicitly uses float32 outside autocast.
- E4 pinned torch/torchvision/xformers/NumPy and explicit recipe packages cover the source requirements inspected. DINOv2 attention uses xformers when imported successfully and CUDA is available; setup's native import qualification remains necessary. The optional random-patch CUDA extension is reached while constructing a training-loss helper, which explicitly has a scripted fallback; inference does not execute those losses. No source evidence requires building that training-only extension for this inference path.

## Limits

No claim of native build success, safetensors load success, forward success, numerical parity or confidence calibration follows from this review. The resolved environment's Hugging Face mixin file was not yet present at the single targeted readiness check, so its actual transitive safetensors loader was not examined. Snapshot metadata was read; weights were deliberately untouched. Source-level review found no additional definite D1 constructor/API blocker, but actual allocated setup/model qualification remains authoritative. The native half-pixel/rounding conventions are provenance differences, not changes authorized by this review.

## Fingerprints

Paths below are relative to the exact official source tree unless marked historical or snapshot. SHA-256 fingerprints cover only the selected regular files read, not a new whole-tree scan.

- `assets/docs/V2_README.md`: `3f36516a329812162ec1882daa13a84ee6ac86dfed96e9df5799fe4f926a2d1b`
- `unidepth/models/unidepthv2/unidepthv2.py`: `9a5ed0d0dd43baf3818a25bb8cccd04fc7938d896d63a9cddd7b86c96bc2ec59`
- `unidepth/models/unidepthv2/decoder.py`: `3ffdb4465da11ee7be427141d5766b8b472da96c940dfe991f018285a894b8e5`
- `unidepth/utils/coordinate.py`: `f4b69a01a20112613dffac4d8621a523b148f1253231118b6bbf09001e0a8f92`
- `unidepth/utils/camera.py`: `f402b67745c5b81b3491c383277677a64713e7805a73f87167bc998851cc567a`
- `unidepth/models/backbones/dinov2.py`: `7a9650c42f55036e09fdbddc40514ae10db6c272939ce4f3ce104be7ab01a3ae`
- `unidepth/models/backbones/metadinov2/attention.py`: `7eb749655e7fb4cbfcbc608c2e35efa12abf69a00bef127b809e6a370b224322`
- `unidepth/ops/losses/local_ssi.py`: `73d8e437566a214981b1683f1fb79a5cacde67279a87e69a8f0e39600c58909c`
- `requirements.txt`: `efa2ac530f88cef1d4fb73ab15d9a326ed66679857ccb01f4730636cb58d2402`
- `pyproject.toml`: `6e8bcbb97f9c17fc084052f4ee1e6af30445fca98674fe55f4b266c638a3910d`
- Historical `__init__.py`: `e4f7dffaed4c24a1d4211bfd86f34433452eb5e540fe959338e02e6eb2b84ddd`
- Historical `models/unidepthv2/decoder.py`: `2c7d55ff5c0f50d4baf7a868ac81fbf431ae35bc8556a340aefa7cbf2e8c54ef`
- Historical `models/unidepthv2/unidepthv2.py`: `efae1f89069a685d05f4fd7be762aaa67c21cfce189fe378a20000ab17927076`
- Snapshot `config.json`: `09eb0ea8de53a6c9a1d428ac98c79847fe2602ea417701261f3f628099a30816`

## Accounting

Review start: 2026-09-13T06:41:43+00:00. Review end: 2026-09-13T06:52:00.570263+00:00. Conservative active elapsed: 617.570 seconds, charged as the entire wall interval (including reasoning and report preparation). Idle: 0 seconds. Limit: 600 active seconds. Source was ready at the initial log read. Only targeted source/config reads and small-file hashing were performed.
