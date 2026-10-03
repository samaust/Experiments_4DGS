# Issue #34 CPU geometry and native-worker preparation

Review base: `8f15b32d609ac6409ce026089d8a4f127087a4c4`.
Validated implementation: `e9212cb8`.

## Delivered

- `60276b41`: full-rig geometry worker over CPU fixtures, all 810 edges,
  audited sampling/support gates, physical velocities and immutable source lineage.
- `727cfe76`: bounded fixture training/reload/render workers and lazy native
  FreeTimeGS adapters, full similarity camera normalization and exact checkpoint
  provenance/restoration checks.
- `e9212cb8`: final publication deadline/failure handling, immutable completion
  receipts, post-cleanup proof checks and shared pipeline completion validation.

The workers exercise 5,000 updates and 200 held-out RGB PNGs through fake runtimes.
They grant no actual execution authority. Native GPU paths remain unexecuted and
unqualified. See the
[geometry specification](../../../specs/plan031-execution/qualitative-final-render-geometry-worker.md)
and [native-worker specification](../../../specs/plan031-execution/qualitative-final-render-native-workers.md).

## Validation and review

Final suite: 1397 unittest cases, 22 skips, zero errors/failures; 22 separate pytest tests passed. Both processes completed without timeout and source hashes remained unchanged. Bound receipts and logs are recorded in [validation.json](validation.json).
The worker/pipeline focused run passed 29 tests in 19.165 seconds.
Independent Spec review found terminal publication handling and its downstream
completion gate needed correction; both are resolved. Standards review identified
duplicated completion validation, now consolidated in the shared pipeline helper.
Both reviews have no remaining actionable findings. See `reviews.json`.

Validation uses a private CPU dependency overlay, fresh disposable output directory,
GPU visibility disabled and a private historical ledger snapshot. No GPU operation,
model setup/download or live ledger mutation occurred. This suite does not establish
current-source native execution qualification. No static type checker is installed
or configured; a static typing pass is not claimed.

## Integration and remaining work

The integration owner retains `plan069-depth-extension` at
`.local/plan069-worktrees/depth-extension`. After the earlier handoff through
`8f15b32d` is integrated and its source freeze permits changes, cherry-pick the three
implementation commits above in order, followed by this evidence commit. Qualify
the combined sources before another model run. This milestone modifies neither
the owner's worktree nor main and closes no issues.

#45/#62 must supply an actual package-bound eligible metric D* decision. Actual
verified geometry loaders/backend qualification, native runtime inventory and
compatibility/license checks, measured viability and approved supervised DO
admission remain required. Actual training, fresh-process checkpoint reload,
held-out final renders/clips and bound human motion/neighbor feedback remain
unfinished. Keep #34/#35 open; fixture results cannot establish their completion.
