# Plan066 — exact resource sampling and append-only source requalification

The user approved expanding Plan065 to optimize and requalify the sampler and
revise its registered source binding. The existing authorization for one S1
calibration GPU attempt (3600 seconds, no reconstruction) remains in force.

1. Profile the real storage snapshot and preserve exact accounting semantics.
   Replace per-file Path construction and repeated classification with a fresh
   string-keyed inventory and indexes collected in the same traversal. Keep
   inode deduplication, all receipt/progress charges, concurrent-change retries,
   symlink/prompts exclusion, and fresh metadata on every request.
2. Validate accounting fixtures and equivalence against preserved old code.
   Measure the actual host helper path, including startup, resource queries,
   IPC, ownership and cleanup, against the unchanged one-second sample deadline.
3. Add a single append-only source-requalification event after the existing
   registration and before any reservation. Preserve the original authorization,
   admission, registration and request. Bind old/new validation, changed source
   records and old source snapshots, explicit user approval, and registration
   identity. Reject duplicate, late, unrelated or incomplete amendments. Bind
   the new event into reservation evidence and terminal receipts.
4. Run the complete timed source-validation aggregate and the owned no-timeout
   validation on final bytes. Preserve actual tool/session provenance; do not
   manufacture a pi-session or Codex-session receipt.
5. Commit validated implementation, append the requalification event only after
   all checks pass, then run the single approved allocation once. Audit its
   terminal evidence and cleanup and commit the observed result. Do not replay
   a consumed attempt or reset any historical budget.

The original 447-event ledger prefix and the existing 449-event admission/
registration history remain intact. The model algorithm, assets, inputs,
annotations, GPU limits, monitor deadlines and scientific recipe do not change.
This plan is the explicit source-change exception to Plan064/Plan065.

## Sampler validation milestone

The original snapshot took 2.98–3.06 seconds. Profiling identified Path
construction/hashing and repeated whole-inventory classification as avoidable
costs. Fresh string paths and traversal-time indexes reduce direct host resource
calls (including GPU queries) to 0.8595–0.8824 seconds with identical byte totals.
Five consecutive full supervised initial samples passed the unchanged request
deadline; total calls including setup/cleanup took 1.0525–1.0917 seconds.
All 32 accounting tests passed, including nested scopes and fresh mutation
charges. The host timed aggregate passed 252 tests in 209.96 seconds at a
240-second cap; the preceding sandbox run is preserved as a socket-denial
failure, not treated as validation.

## Codex validation compatibility correction

The original Codex owned-session driver was invoked with real bootstrap,
readiness, and same-handle tool observations. Its first owned aggregate exposed
an existing rejection of `subprocess.PIPE`/`DEVNULL`/`STDOUT` sentinels as negative
file descriptors and a byte-versus-text argv assertion inconsistent with the
owned launcher's intentional byte normalization. Correcting this descriptor
boundary and its tests is necessary for the requested Codex requalification.
The additional changed source is `s1_helper_session.py`; retain real-FD identity
checks and rejection of arbitrary negative descriptors. No process ownership,
resource ceiling, session provenance, or deadline checks may be weakened.
