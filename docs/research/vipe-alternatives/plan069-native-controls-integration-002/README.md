# Refreshed GS and RoMa preparation after native-control integration

This is **partial metadata preparation**, not a runtime qualification or execution approval. The canonical source snapshot is `23c468e3`; 95 exact source records cover native adapters, matcher code, control/monitoring, ownership and budgets, plus statically visible local imports. No source imports were executed.

| Existing invocation | GS dependency metadata | RoMa dependency metadata |
|---|---|---|
| `.local/envs/freetimegs/bin/python` | All eight required distributions present | Missing einops, kornia, albumentations, loguru, h5py, wandb, timm, poselib |
| `.local/envs/roma/bin/python` | Missing torchmetrics, gsplat, fused-ssim | All 15 required distributions present |

Both explicit virtual environment invocation paths are recorded separately from their resolved interpreter binary hashes. They are separate environments even when their interpreter binary matches. Neither environment currently supplies the complete joint GS/RoMa dependency metadata. No combined environment was selected or installed.

The pinned RoMa checkout is at `370117431ffc5dc000fb46f6e581b74bdb2c3ff8`, with no tracked worktree changes. The two expected weights exist; only paths and sizes were inspected. Expected hashes come from canonical `edgs_source.py`; their current bytes were not rehashed. Prior GS native binary and AlexNet checkpoint records are retained as cached evidence, not newly verified compatibility.

## Remaining gates

1. Actual D* selection and scene-bound resolved configuration: similarity normalization, historical normalized scene scale, native keyframes and typed frame interval 0/50.
2. One explicitly selected invocation/environment containing both complete runtimes.
3. Complete installed distribution file hashes from RECORD, exact matcher checkout source inventory and fresh verified weight bytes for that environment. METADATA/RECORD hashes alone do not meet the production inventory contracts.
4. Independent current source/request review and measured native qualification for every required phase.
5. Applicable reviewed execution proposal and DO allocation, current serial ownership, ledger/live resources and budgets.

The previous partial README's “sole missing assembly input” statement is superseded by these joint runtime requirements. Issues #34/#35 remain open. No model, GPU, installation, download, full runtime tree walk or ledger modification occurred. `audit-002.json` records measured preparation phases, including a corrected metadata filename prefilter; existing successful source writes were preserved.
