# Plan066 source requalification review

Status: source qualification passed; eligible for the single append-only source
amendment and original approved attempt. This does not certify GPU calibration.

Final evidence:
- `aggregate-timed-006`: 258 tests, zero failures/errors/skips, 218.019 seconds
  within 240 seconds; validate_inner and validate_execution passed on final bytes.
- Codex-owned `aggregate-049-016`: 258 tests in 357.242 seconds, both validators
  passed, all payload roots/descendants retired and all bound PIDs absent.
- The subsequent non-owned exit-path correction extends the same WNOWAIT path
  already exercised by aggregate016. Both post-exit regressions passed in actual
  Codex-owned diagnostic032 and a non-owned host invocation. The complete final
  timed006 suite covers the changed non-owned path. The full runner is restored.
- `sampler-audit.json`: three complete old/current snapshot comparisons exactly
  equal; five direct reads 0.793–0.804 seconds; five supervised calls each met the
  one-second request deadline (0.989–1.011 seconds including setup and cleanup).
- `job-line-audit.json`: old/current readers and states matched for five preserved
  aggregates; all 1,449 prefixes of aggregate007 matched full replay. Exact-prefix
  state reads measured 1.51 ms versus 17.33 ms for full replay.

The sampler and replay implementations are unchanged since those audits. Failed
and superseded evidence remains preserved; only timed006 binds the final wrapper.

The host launcher uses the Python 3.14 controller required by its native
joinable-thread ownership API. The authorized model worker continues to use
the qualified E1 Python 3.11 environment. Codex must invoke the launcher with
host execution so systemd, process identities and GPU compute PIDs are visible.

The sampler builds a fresh stat inventory on every request while avoiding
repeated path construction and classification. Accounting semantics retain
inode deduplication, receipts, partial/progress charges, concurrent-change
retries, and symlink/prompts exclusion.

Codex's actual owned-session path exposed descriptor-sentinel, nested-creator,
native non-start, wait/retirement ordering, interruption, and replay-latency
defects. The corrections retain exact handles and incarnation-bound pidfds,
conservative ambiguous-start accounting, unchanged deadlines and CPU capacity.
Only an explicitly known native thread non-start releases an unbound H slot.
Non-S1 owned exit polling preserves the unreaped parent until tree cleanup.
The supervisor retains the created handle before delivering a deferred signal.
Non-S1 exit observation now uses WNOWAIT in both owned and non-owned modes.
Completion requires a post-exit resource sample, closing the race where
final files were written between the preceding sample and exit observation.
A deterministic real-child regression exercises that exact ordering.

Ownership replay caches successful exact line validation and a private encoded
state only for a byte-identical freshly read prefix. New suffixes still pass
schema, canonical JSON, checksum, sequence and transition checks. Callers get
fresh states; private binary state is never read from external input. Appends
retain exclusive locking, exact readback, rollback and poison handling.

Diagnostic030 reproduced a 191.72 ms generation-2 collection of 717,359
unreachable objects in the helper-owner thread, matching a 192.27 ms monitor
gap. Receipt mutation tests now collect their discarded cyclic graphs after
fixture cleanup. Runtime GC and the 100 ms guard are unchanged. Progress
fixtures start their cleanup timer at the first actual Session.close, so both
supervisor retirement and final safety cleanup share the unchanged one-second
cleanup cap; action remains at most two seconds and total at most three.

Fixture corrections isolate fake syscalls from the real kernel-handle ledger,
use native byte argv consistently, and measure injected-block retirement under
the existing cleanup budget. Original full test collection is restored. The
capture candidate hash is required and must equal the durable runner candidate.

The append-only source amendment binds ten changed source records and their
hash-identical old snapshots, all 78 current source records, the original
validation and registration, explicit approval, this review and Plan066. It
does not replace the authorization, request, admission, registration, baseline,
scientific recipe, assets, inputs, annotations, or budget. Duplicate, late,
unrelated, incomplete and incorrectly bound amendments fail closed.

The original 449-event live ledger remains byte-identical before registration:
`1710e2388c6398a5093e75d71a42c75adf4c0ef5817d0ac6de3709f48c56a13a`.
Its original 447-event prefix is also preserved. No S1 recovery GPU reservation
has been made during this work. Registration and the one approved GPU execution
will be recorded separately after this source review becomes immutable.

Failed owned aggregates001–009 and 011–015, and all diagnostics remain preserved with their
actual tool observations and cleanup audits. Aggregate010 passed 258 tests and
retired all payloads, but exposed the capture/validator candidate-field mismatch;
it does not qualify the corrected final validator. Failed logical sidecars were
never rewritten to claim successful retirement.

The performance qualification is a measurement under the observed host load.
The unchanged runtime deadlines and foreign-GPU-PID checks remain enforced
during the actual attempt. A successful source qualification is not a successful
calibration result and does not authorize reconstruction or an extra attempt.
