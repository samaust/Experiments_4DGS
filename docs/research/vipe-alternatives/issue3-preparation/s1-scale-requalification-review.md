# S1 recovery 004 source refresh after scale input binding

The shared scale interface now records and verifies the immutable input-manifest file record for future fits and requires the same record at a frozen check. [ADR 0002](../../../adr/0002-bind-future-scale-checks-to-input-manifest.md) records the compatibility decision: the completed D0/D1 results remain historical and were separately checked against their equal request input-manifest hashes. This source change does not alter S1 scientific settings, allocation, prior attempts, or the process-file preservation amendment.

The [fresh CPU capture](s1-requalification-002/validation.json) binds all 79 current S1 source records to a passing receipt: 277 tests, 1,030 subtests, zero failures, errors, or skips. The child exited 0 without timeout after 215.729 seconds; source records before and after execution match. The earlier requalification-001 and its REVIEW proposal remain historical.

Before authorization, the live ledger still had 467 events with SHA-256 `d958d128e3b8c7a7263e0e07ba6d91e3c7ec5ae7ba855935895673fc69418f96`. Recovery 001–003 remain consumed. The revised 004 proposal stays at REVIEW until the separately recorded one-attempt user approval and live admission checks; S1 reconstruction remains outside this calibration authorization.
