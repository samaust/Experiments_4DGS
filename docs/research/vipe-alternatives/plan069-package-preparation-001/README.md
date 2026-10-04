# Depth package preparation (#59)

The draft reconciles actual revision 002 preview receipts for **D0–D5, D7 and
D11**: 480 frozen frames. **D6, D8, D9 and D10 remain missing**, with no invented
terminal authorization. This does not complete #59/#44 or select D*.

## Aggregate correction

Actual preflight found that duplicated source videos prevented assembly: the
old comparison required identical paths and encoded bytes. D2/D7/D11 copies
have different paths; D5's separately encoded copies also have different bytes
and decoded pixels. No decoded equivalence is claimed.

The viewer now displays the earliest accepted source clip once per camera.
All candidate packages still pass their existing actual admission, input,
native-map and clip checks. Shared source clips must have identical accepted
source-image records, camera/frame/time membership and resolution. Candidate
entries retain each original immutable clip receipt. No original output,
receipt or history is rewritten.

## Commands after integration

Use the canonical checkout so immutable preview builder/renderer path checks
continue to match. Choose a fresh output directory; existing output is retained.

```bash
TASK_CHECKOUT=/home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/depth-extension
TASK_RUN=/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z
TASK_PYTHON=/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/roma/bin/python
cd "$TASK_CHECKOUT"
PYTHONPATH=scripts "$TASK_PYTHON" -B \
  docs/research/vipe-alternatives/plan069-package-preparation-001/prepare.py \
  --checkout "$TASK_CHECKOUT" --run "$TASK_RUN" \
  --output "$TASK_CHECKOUT/.local/depth-package-draft-003"
```

The builder writes only private request/summary/context-ledger copies. It does
not assemble or publish media, charge the shared ledger, run models, consume
attempts or choose a candidate. Missing future receipts stay pending; rerun in
a fresh directory after those executions finish. Final publication still
rejects missing slots. Publishing an interim viewer requires an explicit
partial-package mode; this change does not add one.

## Viewer handoff

The existing viewer offers 60 matched frozen-frame selections (30 cameras at
frames 100 and 175) and four continuous clip selections (cameras 1, 11, 21 and
31, frames 150–199, 25 fps). Play/pause/seek synchronize continuous clips only.
D0/D1/D3/D4 have frozen frames and no continuous clips. Full/center/left/right
views use shared crop/zoom; metric maps share 0–20 m, invalid magenta, out-of-range
red. D11 remains relative log depth. These are component diagnostics, not final
renders, and do not establish physical accuracy.

A human records visual preference separately from eligible metric D*. The
package includes explicit eligibility; D7's scale failure and D11's relative
domain cannot be promoted to eligible physical-scale choices.

## Validation

Regression tests first reproduced rejection of separately encoded clips. The
correction accepts differing movie records only with identical accepted input
lineage and rejects changed source-image lineage. Full actual aggregate
preflight must be rerun in the canonical checkout after integration; isolated
worktree preview-source path checks intentionally reject canonical receipts.

Private draft: `.local/depth-package-draft-002/request.json` in the
`plan069-package-preparation` worktree. Receipt reconciliation took
0.032102313 seconds. Canonical initial assembly failed after 5.275495189 seconds.
FFprobe diagnostics took 0.224824741 seconds; eight decoded movie comparisons took
1.234989264 seconds. Original failures and diagnostics are retained privately.
No GPU or production ledger writes occurred. No typechecker is installed in
the inspected CPU environments. **36 aggregate/package/review tests passed**
in 2.472 seconds with `PYTHONPATH=scripts:tests`; both independent Standards and
Spec reviews found no actionable issues. Retained private diagnostics total
792,511 bytes. The root owner must charge measured preparation time and run
the combined final qualification before actual publication.
