# E1 compatibility implementation after exact-source review

The three incompatibilities in [the saved source review](actual-e1-source-review.md) are now addressed in future setup and the S1 adapter. The review remains unchanged. Existing downloaded source trees, failed E1 setup artifacts, attempts and ledger were not modified. E1 remains failed/consumed; these source fixes do not qualify or relaunch S1.

- `runtime._aot_link` preserves an existing populated vendored AOT tree at an unused sibling, retaining file bytes/modes and its SAM-Track revision in provenance. It then links the original namespace to the separately prescribed AOT source. Refreshed inventories record the original locations as removed and preserved locations as added; model/source pins remain unchanged. An unrelated existing link is rejected.
- `_s1_tracker` intercepts the pinned wrapper's one engine construction and removes only `max_len_long_term=9999`. It requires the exact eval/DeAOT engine, GPU 0, gap 9999 and short-term skip 1. Any argument drift fails before the native engine constructor. The returned `S1TrackerBridge` permits only reset singletons or adjacent reconstruction pairs, one reference at frame step 0, at most one successor, one memory update per reference and two resets. This keeps the source-proven unreachable memory-truncation branch unreachable.
- Before native memory update, the bridge invokes `torch.nn.functional.interpolate(..., size=engine.input_size_2d, mode='nearest')`, matching the vendored native operation. Original-grid labels remain the export. Output metadata records original/internal grids, engine arguments, reset/frame constraints and the bridge rationale.
- `_s1_aot_module` restores the caller's NumPy RNG state after successful or failed native import. Native config construction runs in a scoped directory within the required supervised `TMPDIR`; the prior cwd and builder are restored on success/failure. The bridge retains the temporary-directory lifetime and records its path. No upstream source is patched.

Validation used disposable CPU fixtures and fake native objects only. Every fixture setup/build command is mocked; no real model/GPU inference, import qualification, network transfer, install or build ran.

```
.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p test_vipe_benchmark_backends.py
# 30 tests passed (0.150 seconds in final run)
.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p test_vipe_benchmark_runtime.py
# 23 tests passed (0.155 seconds in final run)
git diff --check -- scripts/vipe_benchmark/backends.py scripts/vipe_benchmark/runtime.py tests/test_vipe_benchmark_backends.py tests/test_vipe_benchmark_runtime.py
# passed
```

The added fixtures cover argument forwarding/rejection, changed native-wrapper kwargs, exact nearest-grid values and unchanged export, extra frames/references/propagations, reset/singleton constraints, import RNG restoration, construction failure cleanup, populated-source preservation, modes/license records, JSON provenance, refreshed inventories and unrelated-link rejection. An initial `python -m pytest` invocation found pytest absent in the chosen environment; validation used its existing standard-library unittest runner without installing anything.

Runtime transfer/auth functions were left untouched and handed back to the parent for the independent gated-HF integration. Full-suite validation, source freeze and commit remain parent-owned. Complete native AOT checkpoint state coverage and actual first-forward compatibility remain unverified because E1 is blocked; no broader adaptation was introduced.

Implementation/preparation interval: 2026-09-13 05:48:57.715 UTC through 2026-09-13 05:58:43.412695 UTC; conservative elapsed charge **585.698 seconds**. This is separate from the already reported 434.715-second read-only review.
