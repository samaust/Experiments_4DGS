# Plan049 Correction015 source-scope addendum 007 — identity-bound cleanup signals

This plan-only proposal responds to the independent exact-source review of the adopted addendum006 implementation. It supplements addenda001–003/006 and does not authorize source changes or execution until it passes independent plan review, receives explicit user authorization, and Main adopts its exact hash.

## Concrete safety finding

The ledger-enabled `supervisor.stop_group` validates the root PID/boot/start/PGID, pins descendants, then calls `os.killpg(process.pid, SIGTERM/SIGKILL)`. Between validation and either numeric PGID signal, another caller could reap the root and allow the numeric group ID to be reused. Descendant pidfds do not establish the identity of the numeric process group at the later signal call. A final `/proc` recheck alone leaves a check-to-signal race. The legacy no-ledger path is outside this correction and keeps its existing process-group behavior.

## Bounded source change and signaling protocol

No source path is added: the already authorized nine paths remain the limit. This proposal narrowly changes the ledger-enabled cleanup signals in `scripts/vipe_benchmark/supervisor.py` and the corresponding root/descendant transition and helper predicates in `scripts/vipe_benchmark/s1_helper_session.py`, plus bounded assertions in the existing supervisor tests. No new method, callback, process, thread, observer, suite, script, scenario, selector, or source member is added.

Before pinning the cleanup set, append a durable `root-stopping` transition under the same interprocess ledger lock. It is idempotent for the exact root token/handle and remains capacity-charged. Descendant reservation may attach only to a live, identity-matched B root; once that root is stopping, waited, or retired, creation beneath it fails before the operating-system create call. A reservation racing with the stop transition is serialized by the ledger lock: it is either durably bound before the transition and included in cleanup, or refused before process creation.

Obtain pidfds for the exact live root and each acknowledged live descendant while each is still present, and immediately recheck boot ID, PID, start ticks, PPID/creator ancestry, and PGID against the durable ledger. A previously waited root is represented by its exact retained process handle and matching wait terminal; do not reopen or signal it. If any live task cannot be pinned or reconciled, keep the root tree charged and perform no ledger-mode signal.

Before signaling, require the current target process-group census to contain exactly the pinned, acknowledged members of that tree which are still in the target PGID, plus the exact root when it is still live. Any untracked, ambiguous, or newly joined member keeps the tree charged and prevents signaling. Never use `killpg` or a numeric PID/PGID signal in the ledger-enabled path.

Send SIGTERM to each still-live pinned process with the OS pidfd signaling operation, retaining all descriptors. Preserve the existing grace duration and absolute cleanup deadline. At the existing escalation point, send SIGKILL only through the same still-open pidfds whose exact targets have not reached terminal state. A terminal pidfd is skipped. Require each exact process handle/pidfd terminal condition, the matching waited root result, and the final existing group-empty census before descendant/root retirement. Append and read back ledger transitions in the existing descendant-before-root order, and close pidfds only after durable tree retirement. Signal errors, unsupported pidfd signaling, unexpected group members, deadline expiry, or incomplete terminal/readback evidence leave the whole tree charged; do not fall back to `killpg`.

If the root is already in the exact `waited` state, only permit the descendant cleanup sequence when every remaining descendant is independently pinned and the pre-signal group census exactly matches those pinned descendants. Do not signal a waited root or a numeric PGID. When no live descendant remains, an empty group plus the exact matching wait can complete only the missing root-retired append, without another root wait. Any other waited-root state remains unresolved.

Preserve the legacy no-ledger `stop_group` sequence byte-for-byte in behavior: TERM/KILL to the process group, original waits/deadlines, return values, and cleanup precedence. Keep the addendum006 exact same-handle already-retired path signal-free. Verify all existing call sites in both modes.

## Preserved constraints and authority

Preserve all original assertions and their order/multiplicity, deadlines, process/scenario semantics, 78 source members, 249 methods, 1,028 callbacks, selections, suites, serial aggregate, CPU-only authorization, `B+max(1,H)≤8`, 150 GiB artifact cap, and 64 MiB memo cap. The new ledger path makes no cgroup/kernel-task bound claim. Diagnostic005 remains failed; Diagnostic006 remains lost and unused; Diagnostic007 remains aborted before admission/tests.

If this proposal passes review and the user explicitly authorizes the signaling change, append it as authority record20 after unchanged Corrections001–015 and addenda001–003/006 records16–19. Rejected addenda004/005 are not authority. Driver, contract, recovery positive fixture, Main admission, launch note, source manifest and final report bind exact path, byte count and SHA-256 in order. Addenda001–003/006 remain unchanged. No previous pointer or record shifts.

## Gates

Obtain independent plan review against Plan049, Correction015, Correction014, and addenda001–003/006. If PASS, request explicit user authorization for this changed ledger-mode signaling behavior; plan review alone does not authorize it. After authorization and Main adoption, implement source-only within the nine exact paths, obtain a fresh distinct exact-source review, and then complete fresh source-hash, artifact-capacity, process/ownership/capacity, output-path and attempt-index/high-water preflight. No tests, fixtures, pidfd operations, diagnostics, admission, or aggregate are cleared by this proposal.
