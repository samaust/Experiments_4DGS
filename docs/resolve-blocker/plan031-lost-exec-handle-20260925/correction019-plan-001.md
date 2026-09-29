# Correction019 plan 001 — use the pidfd signal API exposed by the active interpreter

## Finding

Candidate015's full unchanged CPU diagnostic reached its 73-test suite and recorded 81 failures and 47 errors. Its saved process ledger contains signal intents followed by `operation-uncertain` events whose reason is `AttributeError`; the production helper calls `os.pidfd_send_signal` in both the ledger and non-ledger branches. The selected Python 3.14 interpreter exposes `pidfd_send_signal` from `signal`, while `os` lacks that attribute. This leaves signal intents unresolved and cascades into cleanup, ownership, deadline, and fixture failures. Preserve Candidate015's failed result and its original assertions/deadlines.

## Authorized narrow correction proposal

Change only `scripts/vipe_benchmark/s1_helper_session.py::signal_job_pidfd`, replacing both calls to `os.pidfd_send_signal` with the already imported `signal.pidfd_send_signal`, preserving their exact descriptor, signal, `None` siginfo, and flags arguments. Do not change exception handling, signal ordering, pidfd validation, operation intent/result semantics, cleanup policy, assertions, behavioral deadlines, CPU settings, or resource caps. Add no test case and no other source path.

## Work sequence

1. Obtain independent review of this plan and exact two-call correction before editing.
2. After Candidate015's exact Main session terminal result and independent retirement audit, verify the active interpreter API against the recorded suite environment and verify the current source matches the reviewed baseline.
3. Apply only the two API substitutions. Obtain independent exact-source review.
4. Run the already authorized focused tests and unchanged full CPU diagnostic serially, each with fresh source-hash, artifact-capacity, process/thread-ownership/capacity, output-path and attempt-index preflight. Preserve every result, including failures.
5. Continue remaining Plan031 work in its existing serial order. This proposal authorizes no concurrent test/diagnostic, no new admission until fresh gate reviews pass, and no aggregate before the required diagnostic and audit steps.

## Constraints

Candidate015 remains historical failed evidence. Diagnostic005 and all earlier failures remain unchanged. Plan049 and Correction015 bounds remain in force, including CPU-only execution, `B+max(1,H)≤8`, the 150 GiB artifact cap, and original behavioral deadlines. This plan does not authorize signals to any self-reported PID or recovery action on a live/uncertain ownership record.
