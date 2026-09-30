# Actual D2 fit/check completion

Both original unconsumed900-second slots completed serially on the root-owned GPU using qualified E5 recovery004 and current qualification011. No repeat identity was used.

D2-fit: frame100,30inputs,18.50741288298741seconds, finish564/hash122b5ffb8238f8705e59f8e4183220e9d7b852087f1d969c8b3ddbaa2cd16d7c. Scale gate passed, no blockers, frozen scale1.0899176481863033. D2-check: frame175,30inputs,14.601953361008782seconds, finish570/hash9e810705ca49ffa729c58863e04ac20bf40f17272ec82507eca28ca47c74fb62. Bound to the successful frozen fit; check gate passed with identical scale, no blockers. Both cleanup confirmed, no surviving pids or stop requirements.571-event ledger is preserved.

Explicit resumes applied only to the next original slot after its prerequisites. Frozen DA3 conversion, precision, masks, intrinsics, protocol and input manifests remain unchanged; original D0/D1 evidence is preserved. Passing engineering consistency gates does not establish independent physical-depth accuracy. Raw predictions remain under the hash-bound local job paths; these copies preserve exact receipts and accounting.

Outside-sandbox stage commands, both exit0:

```bash
env PYTHONPATH=scripts .local/envs/stg-colmap/bin/python -B scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z stage --job D2-fit --validation docs/research/vipe-alternatives/plan031-execution/qualification-011/validation.json > /tmp/plan031-d2-fit-controller.log 2>&1
env PYTHONPATH=scripts .local/envs/stg-colmap/bin/python -B scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z stage --job D2-check --validation docs/research/vipe-alternatives/plan031-execution/qualification-011/validation.json > /tmp/plan031-d2-check-controller.log 2>&1
```
