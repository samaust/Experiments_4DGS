# S1 recovery008 first-result failure

One approved attempt consumed36.640664215025026 seconds, finish558/hash518054576325370a9bbfb13ab662f1e0d116a9990cf1a1edc30e6fe83b038514. First-result qualification failed at25.187057116010692 seconds with `ValueError: S1 generated source temporary ownership required`; zero rows qualified. This is an application ownership-contract failure, not a timeout or sandbox denial.

Cleanup confirmed, no surviving pids, stop_required=false and actual terminal receipt published. No retained generated-source file or accepted result exists. Consumed559-event finish prefix is preserved exactly from live ledger bytes; subsequent D2 resume lies after this prefix. Historical007 is unchanged.

Exact outside-sandbox command (exit1):

```bash
env PYTHONPATH=scripts .local/envs/stg-colmap/bin/python -B scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z component-recovery --authorization docs/research/vipe-alternatives/plan031-execution/s1-recovery-008/do.json > /tmp/plan031-s1-recovery-008-controller.log 2>&1
```

The existing interpreter approval rule applies; another permission rule cannot fix this error. CPU diagnosis/correction proceeds under the revised AGENTS standing approval. No unchanged replay or fresh GPU allocation is authorized.
