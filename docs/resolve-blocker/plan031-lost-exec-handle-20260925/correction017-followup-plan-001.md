# Correction017 follow-up plan 001

## Finding

The reviewed focused run under Main session 76078 completed with exit 1 after 83.850 seconds. Of 114 deadline-step subcases, 111 passed. The `runtime_guard/before` control found that an injected child-descriptor close failure is treated as secondary merely because an unrelated caller `RuntimeError` is active. The owner then appears resolved even though the child descriptor is uncertain, and the original error receives no unresolved-owner evidence. The `runtime_guard/equal` and `runtime_guard/after` failures cascade because the before control was not recorded. Exact trace and terminal evidence are in `correction017-focused-002/stderr-001.log` and `main-exec-terminal-002.json`.

Independent reviewer `restart_retirement_review` confirmed that the fixture assertion is valid and recommended a narrowly scoped production fix in `scripts/vipe_benchmark/s1_progress.py`: in child traversal cleanup, suppress a close error only when that same child traversal has a locally active exception; otherwise propagate it into the outer cleanup failure path. Keep the one-attempt close rule, retain the uncertain descriptor, preserve any pre-existing primary exception, attach unresolved owner evidence, and do not extend original-work authority or alter deadline boundaries. This is adjacent to Correction017's already authorized temporary-directory retirement source portion but extends its stated iterator-specific local-error rule. No other source path, test assertion, deadline, resource cap, selector, or launch authority is changed.

## Work sequence

1. Obtain independent review of this exact follow-up scope before editing. Main must record adoption of the exact reviewed plan hash before editing.
2. Implement the minimal local-error distinction only in `OwnedTemporaryDirectory.cleanup` within `scripts/vipe_benchmark/s1_progress.py`. Reuse the already existing `backend_retirement_transition_controls` fixture unchanged; it reproduces an unrelated pending primary plus a child-close uncertainty. Retain its assertions that the primary survives, the owner remains unresolved, the descriptor close is attempted once, and the uncertain descriptor remains accounted for. Do not edit fixture or test files in this follow-up.
3. Obtain independent exact-source review before any further focused execution.
4. Run only the focused deadline-step method with a fresh source/hash, artifact, process/thread capacity and output-path preflight. Preserve the original deadline assertions and all failures. If it passes, record the method result; it is not full diagnostic clearance.
5. Continue remaining correction review and tests serially under Plan049. No diagnostic admission or aggregate is granted by this plan.

## Current evidence and limits

The exact tool session 76078 reached terminal exit 1; its output is preserved in the focused output directory. The initial in-sandbox retry 18746 failed before assertions because AF_UNIX socket creation was denied; the one required exact outside-sandbox retry succeeded in executing the full focused method, so no further permission retry is implicated. No project process from the completed focused run remains. Historical failures remain immutable. This plan does not authorize a diagnostic, aggregate, admission, launch, signal, resource-limit change, or behavior/deadline change.
