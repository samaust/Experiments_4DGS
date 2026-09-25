# Candidate011 corrections — Main adoption as Plan049 Correction017

Main adopts the recommendation in [proposal 001](candidate011-correction-proposal-001.md), SHA-256 `794ffe897c608bd05a9200be6e8fd73a8c63b8b5531f7c3dfec10f4d04a2a415`, following independent PASS [review 003](candidate011-correction-review-003.md), SHA-256 `6b28016c2f35da98ef0a7575444204ee78851073973237924b873a47a4941e30`. Reviews 001 and 002 are preserved as history; review003 covers the corrected exact proposal and gate sequence.

This record is Plan049 Correction017's fixed authority identity for future candidates. It adds only the exact seven source portions in the adopted proposal. It does not alter the original or adopted Plan049 semantics, assertions, deadlines, dimensions, resource limits, source-member count, selection, or serial order. Candidate011 and all earlier attempts remain immutable failed/lost historical evidence.

## Adoption boundaries

Implementation may now edit only the seven source paths and exact portions listed in the adopted proposal. The future candidate's ordered authority list must contain this exact adoption record, byte count, and SHA-256 consistently in `launch-049-exec.py`, `s1_validation_contract.py`, `test_vipe_benchmark_s1_recovery.py`, and future launch artifacts. Existing dispatch/status/driver/launch-note/admission/ledger records remain untouched.

Independent exact-source review must PASS before any focused test or diagnostic. After that review, focused existing checks may run with fresh CPU-only/process/thread/artifact accounting and original deadlines intact. A full diagnostic still requires fresh source/authority, storage/artifact, ownership/capacity, output-vacancy and high-water/index checks, and an immediately persisted Main proof tied to the exact returned exec session handle. Candidate012 is merely the earliest possible index; no index is selected by this adoption record. If the Main handle cannot be retained or trusted retirement cannot be established, stop the affected launch.

No test, process launch, diagnostic, admission, or aggregate is authorized by this record alone. A successful complete diagnostic remains a prerequisite to the final aggregate; each runs CPU-only and serially, preserving `B+max(1,H)≤8`, the 150 GiB artifact cap, 64 MiB memo cap, whole-ledger 8,388,608-byte cap plus per-append guard, complete ownership accounting, no operational time ceiling, and all original behavioral deadlines and assertions.

## Frozen pre-edit sources

| Path | SHA-256 |
| --- | --- |
| `scripts/vipe_benchmark/s1_helper_session.py` | `bb6ea896a73ab3bbdf98e4ac4a9e15edf769a4484995dae44e2d4fca3e34f44d` |
| `scripts/vipe_benchmark/s1_progress.py` | `d53a203c64c1b78a19a720ba72aaa28efbe427333c704f81166a4151e485b89d` |
| `tests/test_vipe_benchmark_supervisor.py` | `03e41c199a63c21cf754f0ec3f571a85f79ac417457344d83220f31399b9ce36` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `faccb5561ad8373d6805b50b0326f0eff8d00e9c9d9760d5829096fca917732b` |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `e28b3874d1830c934fae624eee254a25d25517fcc22cb6fa41f4da5191d62af7` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | `860a18d066b8b13999f1cf21b6b89c1a1e9003ce06e00e6f013dbd3fca782a55` |
| `tests/test_vipe_benchmark_s1_recovery.py` | `205a76a29bf43b38d440638f4123a76509ed5003d3f77ae121d62fb50ffe430b` |
