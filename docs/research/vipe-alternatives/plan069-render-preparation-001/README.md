# Issue #34 CPU preparation handoff

Review base: `251b3d03bb393fde7101946e9c0c02deabcbd6c7`.
Validated source: `f262bf3c640fecaa96e871f66b81f5ec9a31990d`.

## Delivered

- `3515a52b`: selected-depth D* initializer assembly across five fixed arms,
  paired provenance sidecars at the native input boundary, and fixture-only
  ordered worker outcomes with resource, endpoint, reload and coverage checks.
- `f262bf3c`: independently identified correction to rehash a consumed checkpoint
  when validating a render result through the standalone public worker seam.

The specification is
[extended-final-render-preparation.md](../../../specs/plan031-execution/extended-final-render-preparation.md).
No native worker, depth reconstruction producer or execution authority is claimed.

## Validation and review

- Focused pre-review: 62 unittest cases passed in 36.246 seconds.
- Regression reproduced the review finding before correction; all ten pipeline
  tests passed after correction in 3.344 seconds.
- Final full suite: 1,365 unittest cases, zero failures/errors, 22 skips;
  1,343 cases passed. Process elapsed 879.780 seconds; no timeout.
- Separate function tests: 22 pytest tests passed, process elapsed 2.219 seconds.
- All six changed Python files passed AST compilation. No configured or installed
  mypy/pyright; a static typing pass is not claimed.
- Standards review: no actionable findings, including correction follow-up.
- Spec review: one checkpoint rehash finding, corrected and independently confirmed;
  no unresolved findings. See [reviews.json](reviews.json).

[validation.json](validation.json) binds the preserved logs and raw receipts.
The raw launcher extracted an embedded one-test summary into its `tests_run` field;
the normalized summary uses the final anchored 1,365-case summary. The successful
capture was preserved; no tests were rerun to correct that reporting field.

Validation used the private hash-pinned CPU dependency overlay, a precreated fresh
disposable output directory, GPU visibility disabled and the worktree's private
historical ledger snapshot. No GPU, model setup/download or live ledger mutation
was performed. A current-source execution qualification receipt is not claimed.

## Integration and remaining work

The other agent owns `plan069-depth-extension` in
`.local/plan069-worktrees/depth-extension`. Integrate the two implementation commits
above after the earlier downstream changes (through `251b3d03`) are present, then
this evidence commit. The owner decides when its run/source freeze permits
integration and qualifies the combined sources before another model run. No owner
branch, main or GitHub issue state was changed by this milestone.

#45/#62 must supply the actual package-bound eligible metric D* decision. Actual
selected-depth geometry/physical-velocity production, qualified native 5,000-step
training, exact checkpoint reload, matched held-out final renders, current resource
and live admission checks remain required for #34. Actual render-bound human motion
and neighbor feedback and final accounting remain required for #35. Keep both open;
fixture outcomes cannot satisfy these gates or justify closure.
