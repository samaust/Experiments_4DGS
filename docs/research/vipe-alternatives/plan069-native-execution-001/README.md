# Issue #34 actual native execution wiring

Review base: `04318362bf78944dd6dbb13e82c2e922ae8d09ec`.
Validated source candidate: `1878407c`.
Branch: `plan069-native-execution`.
Worktree: `.local/plan069-worktrees/native-execution`.

## Delivered

- Pinned, offline, lazy native RoMa matching using the audited helpers; actual
  geometry requires the registered admission invocation, verified loaders,
  unchanged LK and the real monotonic clock.
- Immutable DO authority over the existing REVIEW request. A durable approved
  grant authorizes ordered consumption of its existing allocations; advancing
  the ledger alone does not require another human approval. Each reservation
  rechecks current sources, licenses, measured qualification, budgets, resources
  and the cleaned same-arm predecessor.
- Fixed actual geometry, initializer, 5,000-step training and fresh-process
  checkpoint reload/render factories. Actual candidates have a separate result
  and completion contract; fixture records and injected runtimes cannot acquire
  native authority. Initializers are replayed against all geometry/array evidence.
- Actual dispatch consumes a shared-ledger reservation once, registers the
  worker PID/PGID, then releases its exact invocation gate. Monitoring and
  acceptance use fixed, bounded CPU helper processes. Retained root identities,
  cleanup uncertainty, terminal publication time and partial failure evidence
  remain accounted. Final checks require idle GPU ownership and storage reserve.
- Seven native numerical workers reserve one slot for monitoring under the
  eight-worker ceiling. Critical ownership and budget sources are included in
  the immutable current source closure. Approved historical budget amendments
  use the shared validator rather than literal configuration equality.

## Validation

Final suite passed: 1,456 unittest cases (1,434 passed, 22 skipped), plus 22
separate pytest tests passed. The unittest retry took 947.485 seconds and pytest
took 2.418 seconds; neither timed out, and source hashes stayed unchanged.
Bound receipts and logs are indexed by [validation.json](validation.json).

Combined focused CPU validation passed 33 tests in 9.777 seconds. All 19 changed
Python files parse successfully. Independent Standards and Spec reviews have zero
remaining findings; three reported defects were corrected. Further corrections
cover helper uncertainty, final resource checks and source closure.
See [reviews.json](reviews.json).

The final suite uses CUDA visibility disabled, a private dependency overlay,
copied historical ledger evidence and fresh disposable output directories.
The initial sandbox capture under [full-suite-001](full-suite-001) is not a
passing unittest receipt: Unix-domain socket creation returned `EPERM`, producing
256 errors. Its separate pytest run passed 22 tests and is preserved. The single
outside-sandbox retry ran only unittest, in fresh outputs, under
[full-suite-outside-001](full-suite-outside-001).
No configured/installed static type checker exists; no typing pass is claimed.

## Integration and remaining work

The other agent owns `plan069-depth-extension` in
`.local/plan069-worktrees/depth-extension`. After its source freeze permits,
integrate the commits after `04318362` from this branch in their recorded order.
The exact source commit hashes are listed in [commits.json](commits.json); include
the following validation evidence commit from this branch as well.
The integration owner should then qualify the combined sources; this lane does
not modify its worktree or `main`.

1. Bind the human D* decision for an eligible metric-depth candidate and regenerate
   native and matcher runtime inventories against the combined source bytes.
2. Produce independent current source/commercial evidence and implement the
   independently allocated native qualification workflow. The new admission
   consumes measured per-phase qualification evidence; this milestone does not
   produce those native qualification runs or allocate their GPU jobs.
3. Freeze and approve the exact DO envelope, commands and existing phase scope;
   pass the live shared-ledger checks before serial actual dispatch. Changed
   sources, requests or extra allocations require fresh reviewed authority.
4. Execute and evaluate actual geometry/initialization, training, checkpoint
   reload and all matched held-out frames. Publish synchronized final clips using
   the reviewed publication workflow and collect human motion/neighbor feedback
   on final renders.

CPU fixtures establish neither native qualification nor successful production
execution. Actual final renders and human review remain unfinished. Keep #34,
#35 and their parent #3 open. No issue was closed, GitHub update published, model
download/setup performed, GPU used or live shared ledger mutated in this lane.
