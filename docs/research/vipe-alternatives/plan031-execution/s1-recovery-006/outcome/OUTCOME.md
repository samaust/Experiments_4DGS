# S1 recovery 006 failed runtime provenance qualification

The single approved calibration attempt was consumed and charged
**35.018222475016955 seconds**. The exact outside-sandbox command exited 1:

```bash
env PYTHONPATH=scripts .local/envs/stg-colmap/bin/python -B scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z component-recovery --authorization docs/research/vipe-alternatives/plan031-execution/s1-recovery-006/do.json > /tmp/plan031-s1-recovery-006-controller.log 2>&1
```

Controller error: `SupervisionFailure: RuntimeError: worker exited 1`.
Underlying worker error: **`ValueError: S1 E1 import differs from admitted source
tree`**. This is definitely an application/provenance contract failure, not a
Codex permission or sandbox denial. The environment/interpreter approval prefix
already exists; no duplicate allow rule fixes this error.

The first native row was produced and qualified; this is one of 510 required
rows and does not constitute successful calibration. First-result runtime
qualification then failed. Initial diagnosis found source tree file records
have an additional `mode` field, whereas import file records have only path,
hash and bytes; whole-record comparison falsely rejects otherwise identical
files. Independent permission checks must remain enforced in any correction.

Cleanup and terminal publication succeeded, with no surviving processes. Finish
sequence 535 has SHA-256
`ca7f1cc0fbdeb0b065b5bc059b6f9901dd41ada81d1a7172aba819c7fe82f915`.
The terminal receipt was published at
`docs/research/vipe-alternatives/plan031-20260913T032700Z/S1-calibration-recovery-006.json`.

Preserve the failure, progress, evidence and consumed identity. No reconstruction
or additional calibration attempt is authorized. CPU correction and review are
separate from a fresh actual attempt.
