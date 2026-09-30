# E5/S1 CPU corrections independent review

Fixed point128f6f5e; final integrated codef9541701, including E5 correction00c9c6ae and S1 correction3d081cb7.

## Standards

Zero documented violations or new optional smells. Exact Normalize preprocessing and supported generated-source capture preserve source/owner/byte checks, ordinary runtime validation, clocks, cleanup guards, historical outcomes and attempt limits.

## Spec

Zero blocking findings. The exact Normalize exception and execution prohibitions are preserved. S1 captures the supported generated source before cleanup, verifies admitted generators/templates and retained evidence afterward, and preserves strict ordinary-file checks. A minor contract wording mismatch was corrected from retained-directory identity to owned temporary-directory identity.

Both reviewers performed read-only review without tests, model imports, GPU use or writes.

## Focused validation

Root integrated run passed73 CPU tests in3.181 seconds across runtime, E5 recovery, FFmpeg binding, S1GeneratedSourceTests and existing S1 runtime provenance tests. Agent red/green validation passed58 E5 and15 S1/provenance tests. Pure static reconstruction of the actual admitted Torch template matched the original2355-byte source/hash. All54 benchmark modules passed AST syntax validation; no configured type checker exists.

Full-suite and current-source capture outcomes are recorded separately. No actual setup/calibration retry is granted by this review.

## Integration correction

The first full-suite capture exposed a missing literal five-case SUBTEST_CASES declaration. Root reproduced the collection error, fixed it without changing production collection, and validated306 collected methods/1035 declared subtests plus15 targeted generated-source/declaration tests in0.376 seconds. Failed full capture is preserved in cpu-corrections-fullsuite-001. A fresh CPU retry follows the relevant validated fix under the new AGENTS.md approval.

Both independent reviewers checked the fixture and wording correction through0835783b: zero Spec findings, zero Standards violations/new optional findings.

A later full-suite capture exposed three historical REVIEW fixtures reading today's edited AGENTS.md instead of amendment002's pinned bytes. Fixf9541701 freezes the exact historical8c98b25c bytes and checks their hash/size. Seven affected tests passed in8.368 seconds; production preservation checks and the live ledger were unchanged. Both independent reviews found zero new findings throughf9541701. Failed capture is preserved in cpu-corrections-fullsuite-002.

## Final validation

Full-suite capture003 ran1123 tests in329.324 seconds:zero failures,six known unrelated errors,five skips. No passing full-suite claim is made. Current-source qualification010 passed306 tests/1035 subtests in239.13751114800107 seconds, zero failures/errors/skips, no timeout under600 seconds; wrapper SHA87b4c89ae5b1a7dfd65e9e49f42e36361ce1237fc81a806954284fb21553d610. Source code and historical artifacts remained unchanged during capture.

Independent scope review of fresh-runtime-attempts-proposal-002 found zero blocking Standards or Spec findings. It requests exactly one E5-004 and one S1-008 attempt,3600 seconds each, serially with no reconstruction; CPU approval and standing bug-retry approval do not override the exhausted explicit GPU limits. New admission controls, operational stop resolution, review, current qualification, explicit DO binding and live checks remain prerequisites.
