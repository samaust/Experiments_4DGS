# Candidate010 event-evidence correction001 — output hash quoting defect

Status: proposed for independent review. No further target-session interaction, admission, test, diagnostic payload, or aggregate is authorized by this proposal.

## Observed discrepancy

Candidate010's exact Main session handle is **87565**. Main saved the complete bootstrap return in [event000](../plan031-progress-20260922/main-session-049-diagnostic-010-event-000.json), then sent the independently reviewed start frame on that exact handle. Main saved the start-frame return and the two mandatory empty polls in [event001](../plan031-progress-20260922/main-session-049-diagnostic-010-event-001.json), [event002](../plan031-progress-20260922/main-session-049-diagnostic-010-event-002.json), and [event003](../plan031-progress-20260922/main-session-049-diagnostic-010-event-003.json). All three tool returns reported the same handle 87565. The driver returned the candidate010 identity request and `awaiting_main_admission`; no `ADMIT` has been sent and no tests have started.

Event001 preserves the exact tool result and echoed start frame, but its `output_sha256` field is incorrect. The saved file currently has SHA-256 `0210f36fc11d052ddf337ed747404098986f81246c1b1dcc886ada3758e758d2`, and its stored output digest is `15bcbf380b27e9ddcf3cb863495f7936daad2e0990acb01dd19b3205b48912ca`. A fresh read-only hash of the exact saved `result.output` bytes gives `4780a8b1d5dc604f7b58b3456c4bdab0c37629c097fcd87dfed90b51e0193921` over 2,336 UTF-8 bytes. The error came from placing dynamically URL-encoded output containing apostrophes inside a shell single-quoted Python command; JavaScript `encodeURIComponent` leaves apostrophes unescaped. This invalidated only the derived digest field, not the stored tool result or its original session handle.

The hash readback command itself completed synchronously with exit code 0. Its exact returned object is preserved in [hash-readback-return001](candidate010-hash-readback-return-001.json). That supporting record correctly leaves its invocation time unknown; its initially inserted `2026-09-25T05:59:00Z` was not measured and is retained only as `invalid_initial_started_utc`, while `started_utc` is now null. Do not infer any unrecorded time or handle from that value.

## Proposed bounded correction

After independent PASS on this exact proposal and the first-party original Main returns supplied to the reviewer, update only event001's `output_sha256` to the independently verified SHA-256 `4780a8b1d5dc604f7b58b3456c4bdab0c37629c097fcd87dfed90b51e0193921`. Preserve every other event001 field and the full original result object. Record the prior event file hash and incorrect digest in a separate correction receipt, then re-read event001 and verify that (a) the full result object still equals Main's retained original return, (b) the output hash equals a fresh digest of the exact UTF-8 result bytes, (c) event order and handle values remain correct, and (d) identity-request path/bytes/hash still match event001's readiness line.

For any later Main-return hash calculation in this attempt, use a fixed non-interpolating readback operation over saved bytes; if dynamic URL encoding is used, percent-escape apostrophes before passing the text through a shell. Capture, store, and emit each complete nested tool return before using it. A hash-control command that does not synchronously return exit code 0 and a checked digest must not be treated as evidence.

The three real `write_stdin` results remain saved as their own event records and must be independently rechecked against Main's original visible returns. Keep candidate010's B/H charge live throughout. This correction changes no source, behavior, deadlines, assertion, fixture, selector, process policy or acceptance criterion. It grants no `ADMIT`; admission remains blocked until independent review of the corrected complete session-bound proof and all fresh admission gates.

## Required independent review

Verify the exact event000–003 bytes and original Main returns, independently recompute event001's correct digest, confirm the identity request readback, inspect the corrected support receipt's explicit unknown start time, and assess whether changing only this digest is a valid evidentiary correction. Return PASS or NEEDS_REVISION. No session contact or admission is part of review.
