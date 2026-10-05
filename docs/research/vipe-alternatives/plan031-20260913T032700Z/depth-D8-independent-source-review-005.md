# D8 source005 independent pre-setup review

Canonical commit: `4c2fe61b`. Previous passing review: source004 at `76b0b9a0`.
Since then 11 D8 closure helpers changed (about 1,740 lines, all made for D6,
D9 and D10), and `LOCAL_COMMON` gained `depth_budget_reconciliation.py`,
`depth_setup_recovery.py` and `depth_recovery_lineage.py` (40 → 43 records).
Two independent read-only agents reviewed `76b0b9a0...HEAD` for its effect on
the D8 setup and single-image maps paths.

## Standards — PASS

No hard violations. Every new branch is keyed to D6/D9/D10 job identities or is
default-off (`prospective_byte_checkpoint`, `cleanup_reserve_seconds`, optional
`deadline_check`, `recovery_cap_authorization` returning None for non-D9).
Stricter generic behaviour: an actual uv command now also requires a complete,
error-free transfer-proxy receipt. Judgement-call smells (duplicated D6
qualification authorizers, a long `note()` tuple, a default `Ledger(load())`
inside `check_slot_byte_budget` on v2/recovery paths) are non-blocking.

## Spec — PASS

No D8 budget, attempt-limit, admission or authorization change: DO002 still
selects setup 1,800 s, 6 GiB dependencies / 9 GiB artifacts and one 3,600 GPU-s
maps attempt. No guard is weakened for non-video candidates (`note()` blocks
more names; supervisor keeps its old cleanup reserve). Causal byte credits only
apply to other candidates' reconciliations after D8's own setup grant and need
no D8 checkpoint. The added uv receipt requirement can fail an otherwise
working setup only when the proxy receipt is incomplete, which is intended.

This pre-setup review establishes no installed runtime, archive or CUDA
compatibility, and grants no new authority.
