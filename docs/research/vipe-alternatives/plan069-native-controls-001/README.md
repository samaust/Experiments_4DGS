# Issue #34 verified inputs, runtime inventory and CPU dispatch handoff

Review base: `d23fc3463d3d8d97ae594b731233646eee01d1f8`.
Validated implementation: `d930f77e`.

## Delivered

- `65a4b548`: immutable native runtime inventory generation and shared validation;
  explicit dependency metadata, binaries, source files, interpreter/environment,
  offline checkpoint and resolved scene configuration.
- `0f89eb2e`: verified RGB, segmentation, motion and selected metric-depth readers;
  bounded decode and exact byte/array/unit checks; geometry defaults to the loader.
- `b6412ec3`: private CPU fixture dispatch using the existing ledger and process
  supervisor; serial reservations, deadlines, cleanup, source/parent lineage,
  resource simulation and cumulative accounting.
- `d930f77e`: apply CPU thread limits before process startup and numerical imports;
  preserve historical defaults and S1 behavior.

Specifications:
[verified loaders](../../../specs/plan031-execution/qualitative-final-render-verified-loaders.md),
[runtime inventory](../../../specs/plan031-execution/qualitative-final-render-runtime-inventory.md),
[fixture dispatch](../../../specs/plan031-execution/qualitative-final-render-fixture-dispatch.md).

## Validation and review

Final suite: 1423 unittest cases, 22 skips, zero failures/errors; 22 separate pytest tests passed. Both processes completed without timeout and all source hashes stayed unchanged. Bound receipts and raw logs are in [validation.json](validation.json).
Combined focused loader/inventory/worker/dispatch validation passed 44 cases before
the thread correction. The correction reproduces an eight-thread NumPy pool under
a one-CPU request, then observes one thread after the fix. Independent Spec review
confirmed the regression passes in 0.832 seconds. Correctly configured dispatch
and supervisor default checks passed 23 cases in 6.613 seconds.

The broader initial supervisor test launch omitted VIPE_CPU_VALIDATION and the
required precreated S1 output directory. Its setup failures are recorded in
`invalid-supervisor-test-launch.json`; that launch is not passing qualification.
The corrected focused launch is preserved in `focused-supervisor.log`.

Standards review: zero hard violations and zero actionable findings. Spec review:
one numerical thread initialization finding, corrected; zero unresolved findings.
All ten changed Python files pass AST validation. No configured/installed static
type checker exists; a static typing pass is not claimed. See `reviews.json`.

The final suite uses a private dependency overlay and historical ledger snapshot,
a fresh disposable output directory and CUDA visibility disabled. No model
setup/download, GPU operation or live ledger mutation occurs in this lane.
Current-source native execution qualification is not established by CPU fixtures.

## Integration and remaining work

The other agent owns `plan069-depth-extension` at
`.local/plan069-worktrees/depth-extension`. When its current source freeze permits,
integrate the earlier handoff through `d23fc346`, then these four implementation
commits in order, followed by this evidence commit. Regenerate runtime inventories
after merging: `dependencies` is now mandatory, and current adapter/loader/control
source hashes must be covered by the combined qualification freeze. Qualify the
combined sources before any new native run. Main and the owner worktree were not
modified; no issues were closed or GitHub updates published.

D* decision and actual native matcher qualification, measured viability,
compatibility/licenses, approved supervised DO transition, bounded live monitoring
and acceptance, shared-ledger accounting and GPU exclusivity remain prerequisites.
The delivered dispatcher rejects actual requests. Existing selected-depth anchors
can be read; reconstruction-window depth maps are not generated, and the unchanged
RoMa geometry uses D* through its frozen physical camera scale.

Actual 5,000-step training, fresh-process reload, matched final renders/clips and
separately bound human motion/neighbor feedback remain unfinished. Keep #34/#35
open until their actual evidence is complete; fixture success cannot close them.
