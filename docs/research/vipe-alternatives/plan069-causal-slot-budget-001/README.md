# Prospective causal whole-slot accounting

CPU preparation only. No installation, download, model load, GPU use or shared
production ledger mutation occurred in this worktree. Keep #3/#34/#35 open.

## Implemented boundary

D9/D10 setup dispatch opts into
`Ledger.authorize_depth_setup(..., prospective_byte_checkpoint=True)`. The checked
grant binds an immutable whole-run inode and download checkpoint, collected under
the existing ledger lock. Its original resource snapshot and all approved caps
remain unchanged. Old grants without this evidence retain conservative v1 checks.

After exact accepted setup completion and confirmed cleanup, a separately bounded
and charged CPU preparation may call `Ledger.reconcile_depth_setup_bytes(candidate)`.
It requires no active attempt, exact approved setup/request/asset lineage, unchanged
whole-setup/global byte bounds, and exact acquisition delta. It rehashes declared
accepted files once, including only the candidate runtime rather than the full run.
Generic notes cannot create the protected reconciliation event.

V2 whole-slot checks subtract only later accepted unrelated contributions:

- New retained declared inodes absent from the protected checkpoint. Storage uses
  `max(logical, allocated)` and deduplicates hardlinks.
- Newly retained cache inodes shared with accepted installed package inventory.
  Baseline inodes, non-package source/model aliases and unowned cache growth are
  not credited. Cache credit deduplicates inodes; duplicate logical aliases in the
  global cache metric can therefore leave a conservative residual.
- Actual UV commands' exact completed immutable transfer receipts, plus new direct
  receipts for accepted retained files.

Acquisition credit uses the existing metric:
`owned_direct + max(UV, cache) - max(UV-owned_UV, cache-owned_cache)`.
It is recomputed live; neither compressed transfer size nor a peak scalar replaces
expanded retained-cache accounting. Cumulative global totals are never reduced.
Unknown residual growth stays charged. No retrospective scalar-only credit exists.

Live checks rehash the small accepted setup/runtime/inventory/checkpoint/transfer
records and verify unchanged retained inode metadata. Changed, missing, preexisting,
duplicated or unbound evidence fails closed. A candidate's own reconciliation is
excluded from credits and retains its original charges.

## Validation and review

38 focused CPU tests passed in 0.991 seconds across causal reconciliation, existing
map allowances, setup authorization and protected notes. Seventeen new cases cover
expanded-cache versus compressed-UV accounting, baseline aliases, unowned growth,
changed metadata/content/evidence, own admission, active and unclean attempts,
protected checkpoint/notes and unchanged global caps. Four source files passed
`mypy --check-untyped-defs`. Both independent Standards and Spec reviewers found
initial ownership/evidence/own-admission gaps; these were fixed and both rechecks
reported no remaining actionable findings.

## Integration and actual work pending

Integrate reviewed UV receipts first (`cecc9a4f` → `e54683b7`; this branch's
cherry-picks are `4dc1a5b8` → `183b0265`), then the causal core. Preserve root's newer
protected diagnostic event and `_jobs` additions when merging ledger changes.
Add `depth_budget_reconciliation.py` to shared source inventory after the module
is integrated, regenerate source reviews and qualify combined sources before setup.

A follow-on bounded CPU producer must reserve remaining candidate/global CPU time,
preserve qualification/maps headroom, enforce its hash deadline while streaming,
preserve cleanup and success/failure receipts, and charge actual elapsed time.
The protected reconciliation is not automatically run after setup. No actual byte
headroom or full attribution has been measured yet. If retained cache entries lack
accepted installed-inode ownership, that residual remains a blocker rather than
receiving fabricated credit. Actual D9 setup, reconciliation and D6 maps need the
integration owner's checked execution path and applicable approvals.
