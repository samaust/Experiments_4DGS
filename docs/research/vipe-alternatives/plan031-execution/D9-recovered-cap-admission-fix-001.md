# D9 recovered map cap admission correction

The recovery002 DO intentionally contains its new setup approval and unchanged single-map grant, while cap authority remains in the original protected setup DO. Dispatcher admission previously indexed absent cap fields; locked allocation then received no cap approval. Neither failure required new authority or altered resource limits.

`recovery_cap_authorization` now checks the accepted recovery lineage, exact map proposal and recovery authorization. It reads and verifies cap records from that lineage's original protected setup authorization. The existing dispatcher and allocator use this shared boundary. Ordinary setups retain their existing cap selection. Missing or mismatched lineage fails before an admission write or allocation grant. No DO, setup result, request, attempt limit, asset credit or cap was modified.

## Validation

Two public regressions failed before the correction: the truthful recovery DO raised `KeyError: cap_amendment` at dispatch, and the allocator rejected absent cap approval. Both pass after the correction. Tests additionally reject wrong recovery authority, changed proposal, missing original caps and duplicate map allocation.

47 focused CPU tests passed, including existing recovery-lineage and ordinary allocation gates, in **1.157106977 seconds including imports**. Scoped mypy passed the three changed source files in **0.434299962 seconds**. Independent Standards and Spec reviews both passed without actionable findings.

The first mypy invocation found no installed module in the bootstrap environment. The supplied fixture overlay also lacked mypy; that failed invocation was preserved and measured at **0.011198690 seconds**. The corrected existing typecheck overlay succeeded; no package installation occurred. Earlier red/necessary correction tests reported a combined **1.073 seconds** in unittest execution, excluding interpreter startup; the final measured validation is a separate phase. No GPU, model or production ledger was used.

Private receipts: `/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/d9-cap-ancestry/.local/d9-cap-validation-001/`. Root owns settlement of this new CPU work; this agent made no live charge.

This source correction requires a fresh source/CPU freeze and actual runtime finalization before native dispatch. Historical source reviews and successful CPU-native captures remain preserved evidence. Parent issues remain open.
