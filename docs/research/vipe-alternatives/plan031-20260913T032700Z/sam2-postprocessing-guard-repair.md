SAM2 postprocessing warning guard repair

The [exact E2 source review](actual-e2-source-review.md) identified a native
fallback: connected-components hole filling catches an exception, emits a
multiline `UserWarning`, and returns unfilled logits. The selected video builder
requires fill-hole area 8, so silently accepting that result would misstate the
prescribed processing. This is source evidence, not an observed kernel failure.

Only the already-reviewed regular archive members `sam2/utils/misc.py` and
`sam2/utils/transforms.py` were read into memory to verify the exact warning and
hashes. Neither member was extracted to disk. Both warning sites use
`stacklevel=2`; their attributed modules are `sam2.sam2_video_predictor` and
`sam2.sam2_image_predictor`, respectively.

The new [helper](../../../../scripts/vipe_benchmark/sam2_postprocessing.py)
exports `require_sam2_postprocessing()`. Within this context, only the exact
pinned notice, following an arbitrary multiline exception prefix and two
newlines, is promoted from `UserWarning` to an exception. The filter matches
only the two attributed predictor modules, with exact notice capitalization.
It leaves thresholds, precision, native processing, unrelated warnings, and
existing error policies unchanged. `warnings.catch_warnings()` restores filters
on normal exit, nested exit, and exceptions. Caller-owned `finally` cleanup
continues to run.

Integration must enclose native calls and iteration of lazy video propagation,
not merely generator construction. Root will integrate the helper after the
active setup stops; this repair does not edit `backends.py`, `runtime.py`, or any
existing execution source. The selected image path normally has zero hole and
sprinkle areas; its identical warning is guarded if it nevertheless occurs.

Validation: `.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p test_vipe_benchmark_sam2_postprocessing.py -v`
passed all **12 tests** in **0.001 seconds**. Fixtures include the actual
`stacklevel=2` call arrangement, multiline exception text, lazy propagation
failure before any successful result, caller pair-state cleanup, warning-free
behavior, exact-module/category/message boundaries, unchanged unrelated warning
policies, and filter restoration. Native/model imports are prohibited in a
fixture. The root agent confirmed E4 was downloading its base wheel and had no
native build active before this single-process test run.

| Evidence/source | SHA-256 |
| --- | --- |
| `actual-e2-source-review.md` | `7bfff7f85fed97d3fd2fd538ec8038955f5239afc8b72410dc6136a7a00487e6` |
| Pinned archive member `sam2/utils/misc.py` | `01600c01c161cd079d7106fb1d4da845cf91aa31ab2bcecaf8cb151b6d6d20a2` |
| Pinned archive member `sam2/utils/transforms.py` | `ba3a64f4600c62f209206a6df3b40e3fcf133edae32fad658831bb0c2a6d1146` |
| `scripts/vipe_benchmark/sam2_postprocessing.py` | `e2bdf1e49fd5bb47145dcbab8f789c9e56fb6a078cd58b9bd53e2dc4b1a841d6` |
| `tests/test_vipe_benchmark_sam2_postprocessing.py` | `ee455d901c1cefe0b5327f92e4fade6d931732c08e3b008f87af2d8ecaa7d87b` |

No native import, build, kernel, model inference, or network request ran for
this repair. E2 remains failed with its setup attempt consumed. This helper is
validated only against fixtures and exact pinned source text; integrated backend
cleanup, successful native hole filling, masks, and runtime compatibility remain
unverified until separately authorized validation. A changed upstream warning
or caller module requires a new source review.

Preparation accounting: start **2026-09-13 06:40:29 UTC**; report publication **2026-09-13 06:47:56.395604 UTC**. Conservative active elapsed **448 seconds**, rounding up the full elapsed interval with no idle deduction, below the **600-second** subcap.
