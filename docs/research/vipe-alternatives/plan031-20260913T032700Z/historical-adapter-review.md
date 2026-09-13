# Historical adapter source review

Read-only review of S0/D0 before their first allocated model attempt. The reviewed
adapter was `scripts/vipe_benchmark/backends.py`; historical source came only from
files listed in
`.local/vipe-alternatives/plan031-20260913T032700Z/qualification/historical-assets.json`,
at ViPE revision `de50e6ab1066e32c96d32499a282ecaa2fbf2d90`. Every historical file
read was checked against its frozen SHA-256 first. No model imports, inference,
GPU operations, setup, downloads, source changes, or git operations occurred.

## Findings

1. **S0 cache lifetime blocker — root notified and fixing.** The reviewed factory
   in `backends.py:887` creates a different `TemporaryDirectory` on each
   snapshot/pair and supplies checkpoint symlinks under that directory to a
   shared `ModelCache`. Historical `segmentor.py:33` includes the full SAM
   checkpoint path in its cache key; `aot_tracker.py:40` includes the full AOT
   checkpoint path. `model_cache.py:55` retains each built model. Consequently,
   fresh paths retain fresh SAM and AOT weights on every call, risking memory
   exhaustion during a component job. Keep the verified checkpoint binding
   paths stable for the backend lifetime, while continuing to construct fresh
   SAM predictor and AOT engine state for each snapshot/pair. Grounding DINO's
   native cache key is already stable (`detector.py:40`). A CPU fixture should
   exercise multiple factory calls, assert unchanged paths/one build per weight
   key, and assert distinct predictor/tracker state. This note describes the
   reviewed version and does not certify a subsequent fix.

2. **D0 precision metadata should be explicit.** `backends.py:709` correctly
   describes the float32 invocation, but its `native_autocast='historical fork'`
   does not disclose the actual native policy. Historical
   `models/unidepthv2/unidepthv2.py:231` decorates `infer` with enabled CUDA
   float16 autocast. An outer disabled autocast context does not disable this
   nested native decorator. Record the native float16 policy explicitly;
   preserve native inference and the planned float32 invocation. The processed
   image tensor being float32 is not evidence that internal operators run in
   float32. This is a provenance correction, not a requested precision change.

3. **S0 selected-box diagnostics contain an adapter reconstruction.**
   `backends.py:637` reconstructs original-grid boxes in NumPy from the captured
   normalized native boxes. Multiplication by a Python dimension list promotes
   these calculations to float64, whereas historical `detector.py:147` performs
   the conversion using torch float32. Small reported S0/S1 box differences may
   therefore include adapter arithmetic. Retain the normalized raw tensors as
   primary evidence; record this diagnostic conversion or capture the actual
   native returned boxes if exact selected-box comparisons are intended. This
   does not change labels or tracking behavior.

## Source-visible checks that match

- **S0 checkpoint/text bindings:** the patched hub directory supplies the exact
  SAM and AOT filenames expected by `track_anything/__init__.py:27`; the patched
  URL matches the detector's checkpoint request. Native tokenizer and BERT
  constructors accept an existing local directory
  (`groundingdino/util/get_tokenlizer.py:19`, `:24`), so the verified snapshot
  substitution matches their interfaces.
- **S0 hook tensor and labels:** `detector.py:138` calls Grounding DINO with a
  positional BCHW tensor. The internal conversion to `NestedTensor` at
  `groundingdino.py:276` does not replace the original forward-hook argument.
  `_inputs[0][0]` therefore captures the actual standardized CHW detector input.
  The native model clears cached image features before returning (`:339`).
- **S0 phrase/score association:** native detection uses max sigmoid token score
  strictly above 0.35; native box filtering retains original query order and
  tests area against image area (`seg_tracker.py:177`). IDs are allocated in
  that order, including masks later overwritten by overlap. The returned
  phrase dictionary is restricted to IDs present in the tracked mask
  (`track_anything/__init__.py:135`). Mapping each surviving ID to its original
  score retains the native association. Native phrase choice uses the highest
  summed phrase-token score; the nominal text threshold is unused in this
  fork (`groundingdino/util/utils.py:516`).
- **S0 snapshot/pair state:** the native pipeline starts its own `frame_idx` at
  zero and detects on the first call regardless of `raw_frame_idx`; one
  successor takes the propagation branch, with no second detector call
  (`track_anything/__init__.py:113`). Fresh pipeline construction meets the
  intended pair reset once weight-cache paths are fixed. `VideoFrame` accepts
  the adapter's keyword-only frame index and HWC RGB tensor (`streams/base.py:56`).
- **D0 constructor and checkpoint:** the adapter's patched class method matches
  the exact `UniDepthV2.from_pretrained('lpiccinelli/unidepth-v2-vitl14')` call
  (`depth/unidepth/__init__.py:31`) and binds the existing verified snapshot with
  `local_files_only=True`. Its frozen `config.json` was separately SHA-verified:
  `model.pixel_encoder.pretrained` is null. The historical encoder therefore
  does not fetch separate pretrained backbone weights (`models/encoder.py:880`).
- **D0 intrinsics, output and observer:** the native input dataclass defaults to
  pinhole and accepts HWC float RGB and the four-element intrinsics vector
  (`depth/base.py:63`). The historical estimator intentionally reconstructs K
  using fx for both focal lengths and the image center
  (`depth/unidepth/__init__.py:44`); adapter metadata records that native K and
  the accepted source K separately. Native `infer` calls
  `encode_decode(inputs={...}, image_metas=[])` (`unidepthv2.py:288`), matching
  the observer, and restores confidence and camera-z depth to the original grid
  (`:292`, `:313`). The adapter consumes the correct fields and does not apply
  another focal conversion.

These checks establish source-level interface consistency only. Runtime imports,
checkpoint deserialization, native extension compatibility, device memory use,
and numeric/model quality remain to be established by authorized admission and
the allocated execution. No extra model smoke attempt is implied.
