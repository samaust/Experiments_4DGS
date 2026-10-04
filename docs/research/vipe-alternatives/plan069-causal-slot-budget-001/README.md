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

## Bounded CPU reconciliation producer

`run_reconciliation` and the same helper's module CLI now execute a fresh named
`plan069-root-cpu-fixture-admission/v1` record. The default limit is 120 seconds,
including five seconds for cleanup/receipt publication. A caller may select a
limit only within the admission's explicit bound, current candidate allowance and
global remainder, preserving 180 seconds for qualification and 160 for maps CPU.
The independently checked admission must name D9 and source review 004 for D9;
D6's capture admission is unsuitable. It binds the current ledger head, exact
effective configuration, passing current source closure and separately checked
candidate CPU totals. Prepare that fresh admission after the accepted setup finish;
its candidate allowance may conservatively narrow the approved 3,600-second cap.

The timer begins at entry. Admitted configuration/source preflight, hashes and
reconciliation are included in the immutable success/failure receipt and its exact
elapsed CPU charge. SHA checks enforce the deadline per 1 MiB, ownership inventory
checks it per entry, and final scan, proof publication and protected append recheck
it. No child process, model or GPU is created; cleanup receipts reflect that.
An invalid/stale admission is rejected before owned output creation. Once admitted,
failed preflight or reconciliation preserves its receipt and measured charge.

After integration and fresh qualification, the execution owner can invoke:

```sh
PYTHONPATH=scripts CUDA_VISIBLE_DEVICES='' \
  /home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python -B \
  -m vipe_benchmark.depth_budget_reconciliation \
  --candidate D9 \
  --ledger /home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/ledger.jsonl \
  --admission /ABSOLUTE/PATH/TO/FRESH-D9-RECONCILIATION-CPU-ADMISSION.json \
  --output /home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/prepare/plan069-D9-setup-byte-reconciliation-001 \
  --seconds-limit 120
```

The admission path is deliberately a placeholder; no actual accepted D9 setup or
fresh reconciliation admission exists yet. Source inventories bind the whole
module, including its CLI; no private execution code is hidden from that review.

Final focused validation: **81 CPU tests passed in 1.267 seconds**, including
existing budget/UV receipt regressions and new timeout/preflight/headroom/replay
cases. Four changed accounting/ledger/dispatch modules pass meaningful mypy.
Expanding that check to existing `budgets.py` exposed six preexisting untyped-body
errors (unannotated containers and an existing optional identity narrowing); the
new optional deadline callback introduces no new reported error. Both independent
wrapper reviewers found the timer/final-publication gap, then confirmed its fix
and reported no remaining actionable findings.

No actual byte headroom or full attribution has been measured yet. If retained
cache entries lack accepted installed-inode ownership, the residual remains a
blocker. Actual D9 setup, bounded reconciliation and D6 maps require the execution
owner's checked path, fresh source inventories/qualification and applicable
approvals. Keep #3/#34/#35 open.
