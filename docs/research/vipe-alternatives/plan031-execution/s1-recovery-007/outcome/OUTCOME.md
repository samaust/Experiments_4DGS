# S1 recovery007 acceptance failure

All510 calibration rows were produced and individually qualified:340 fit,170 selection. First-result provenance qualification passed. This is not an accepted successful calibration: final runtime validation failed, no acceptance was recorded, and terminal publication was unavailable.

Exactly one attempt consumed2024.6900698940153 seconds, below3600 seconds; no deadline exceeded. Finish sequence546/hash `dce4f9418bc8794715467ff24201f914682ef7c07294fbcea02be48d21fb8d6b`. Cleanup confirmed with no surviving processes. `stop_required=true` and `terminal_publication_block_reason=poisoned_helper` are preserved.

Exact outside-sandbox command (exit1):

```bash
env PYTHONPATH=scripts .local/envs/stg-colmap/bin/python -B scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z component-recovery --authorization docs/research/vipe-alternatives/plan031-execution/s1-recovery-007/do.json > /tmp/plan031-s1-recovery-007-controller.log 2>&1
```

Primary error: `RuntimeError: helper operation failed`, wrapping `FileNotFoundError: [Errno2] No such file or directory: tmp_ronuary`. The final runtime validator could not reopen the recorded job-temporary `tmp_ronuary/_remote_module_non_scriptable.py` (module `_remote_module_non_scriptable`,2355 bytes, SHA8205b16956fb264841ecd8644784a0d157f87df79b17c16825dc1163433ce5d8). Secondary error: `RuntimeError: retained helper unavailable for terminal publication`. This is an application artifact-lifetime/acceptance failure, not a Codex sandbox denial. The interpreter approval prefix already exists; a duplicate rule cannot restore the missing file.

Original local calibration media/evidence and unaccepted worker result remain preserved. Copies here capture exact failure/progress/runtime/worker-result evidence; they do not repair acceptance, manufacture a terminal receipt, or authorize another attempt/reconstruction. Affected S1 execution is stopped pending user resolution.
