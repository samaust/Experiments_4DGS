# E5 recovery 002 failed import-only qualification

The single approved attempt was consumed and charged **78.96719443995971
seconds**. The exact outside-sandbox command exited 1:

```bash
env PYTHONPATH=scripts .local/envs/stg-colmap/bin/python -B scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z setup-recovery --authorization docs/research/vipe-alternatives/plan031-execution/e5-recovery-002/do.json > /tmp/plan031-e5-recovery-002-controller.log 2>&1
```

Controller error: `SupervisionFailure: RuntimeError: worker exited 1`.
Underlying worker error: **`ValueError: E5 setup import qualification initialized
a CUDA context`**. This is definitely an application/runtime contract failure,
not a Codex permission or sandbox denial. The environment/interpreter approval
prefix already exists; no duplicate allow rule fixes this error.

Cleanup is confirmed, with no surviving processes. The finish is sequence 529,
SHA-256 `9a30adb4659d1d76b962a02e75662e13cd4fd44a16932c713259346e38263f30`.
The prior FFmpeg blocker was cleared. Both required imports completed, with zero
forwards and no model constructors, but CUDA initialization violated the setup
contract. Pinned xFormers' optional Triton availability check calls CUDA device
capability during import, which initializes CUDA.

Preserve the failure and consumed identity. D2 remains blocked without qualified
E5 setup. CPU preparation of a narrow fix is separate from another actual setup
attempt; no retry is authorized by this failed run.
