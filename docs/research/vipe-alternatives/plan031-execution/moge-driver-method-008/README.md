# D6 driver method 008 (qualification005)

Method 007 plus a prebuilt, hash-bound Triton helper cache. Qualification004
(`depth-D6-driver-outcome-004.json`) showed guard007 resolves CUDA error 304,
but importing `moge.model.v3` pulls in `flex_gemm`, whose Triton autotuners
initialize the Triton CUDA driver at import. On a cache miss Triton 3.2 compiles
its `cuda_utils` helper with `/sbin/ldconfig -p` and gcc, which the worker's
no-child-process audit guard correctly denies.

- `scripts/basketball_vipe_triton_helper_cache.py` builds the helper once, CPU
  only (`CUDA_VISIBLE_DEVICES=''`), with Triton's own `compile_module_from_src`
  and the qualification interpreter, into a fresh run-owned cache. Its binding
  records the driver source, Triton version, key directory and the single `.so`.
- The worker accepts only the supervisor's four per-attempt `TRITON_*` paths,
  verifies the binding against the installed Triton, then points
  `TRITON_CACHE_DIR` at the bound cache before importing torch or Triton. After
  the two strict CPU loads it re-verifies the cache unchanged; the dispatcher
  re-verifies it again before publishing a result.
- `network_guard.py` is byte-identical to method 007; `startup.py` differs only
  in labels. The worker keeps all method 007 limits: no child processes, no
  inference, forward, benchmark or kernel launch, two strict CPU loads.

Guard tests remain in `moge-driver-method-007/test_guard.py` (same guard bytes).
