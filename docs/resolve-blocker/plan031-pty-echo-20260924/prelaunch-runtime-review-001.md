# Independent prelaunch runtime-readiness review 001 — diagnostic009

**Verdict: PASS for a new pre-admission proof capture only.** Main may begin one fresh serial CPU-only same-handle pre-admission proof capture at diagnostic candidate009 under the existing Plan049/Plan054/Plan055 authorization. This review grants no `ADMIT`, payload/diagnostic execution, aggregate, or acceptance of a live proof. A distinct independent review must compare every newly captured original Main tool argument/result object with its checked copy, output hash, exact handle, complete session proof, terminal and retirement evidence before any admission decision. Fresh occupancy, ownership and capacity still apply at the actual launch boundary.

## Exact evidence and source gate

Reviewed `main-preflight-049-diagnostic-009-prelaunch.json` SHA-256 `e9933d367cdcd33be8870b8c188267bc4df371dbd8e18c169ce4cec2d7f3c3e9`, recorded 2026-09-24 23:48:03.587–23:48:07.691 UTC. Its saved tool return exited 0; the embedded JSON output agrees with every corresponding top-level field (its additional `kind: diagnostic` is not repeated at the top level). Current `HEAD` is commit `653f51bb1c28d42541ce1876f1316dedf912f8f1` (`653f51b`). I read Plan049, Plan054, adopted Plan055 SHA-256 `18506f655e7a2c95492fa88a038c869a4c993fa06d3ba628725158eaea77242f`, Correction001 `89271f7ee1156326a4edce7079ad812ecb93f7674b9522d1233f6e7927d20136`, plan PASS `9f454e6468f53770ed3702eaa889b5f204e93f941aeecb5518034daa8ad26949`, and exact-source PASS `dac8b9fbef2fb4ec272a204f7edacbabcbd96c3b55c63f52ccd3e32cc1550551`.

I independently enumerated and hashed all **78** current source members plus the separate driver record; all 79 byte counts and hashes match the artifact and all reviewed Python parsed as AST. I independently rehashed its nine selected paths, matching both the preflight and source review:

| Path | SHA-256 |
| --- | --- |
| `docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py` | `e28b3874d1830c934fae624eee254a25d25517fcc22cb6fa41f4da5191d62af7` |
| `scripts/vipe_benchmark/s1_validation_capture.py` | `62359a258543731b96690d3abc7bd3ddede4809ae76ae4ec2ff83e5c4ce95fd7` |
| `scripts/vipe_benchmark/s1_validation_contract.py` | `860a18d066b8b13999f1cf21b6b89c1a1e9003ce06e00e6f013dbd3fca782a55` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `bb6ea896a73ab3bbdf98e4ac4a9e15edf769a4484995dae44e2d4fca3e34f44d` |
| `scripts/vipe_benchmark/supervisor.py` | `1f8fb109c48ab121a232d3348ecaec1644b651119742c1d6339c6ce87faf2878` |
| `tests/test_vipe_benchmark_s1_helper_fixtures.py` | `faccb5561ad8373d6805b50b0326f0eff8d00e9c9d9760d5829096fca917732b` |
| `tests/test_vipe_benchmark_supervisor.py` | `03e41c199a63c21cf754f0ec3f571a85f79ac417457344d83220f31399b9ce36` |
| `tests/test_vipe_benchmark_s1_recovery.py` | `205a76a29bf43b38d440638f4123a76509ed5003d3f77ae121d62fb50ffe430b` |
| `tests/test_vipe_benchmark_budgets.py` | `6bac13ad5582f4bd28a86ea5c42989d08d8932f236e3797a288807100edcefa6` |

All 14 listed authority records independently match current exact bytes and their expected SHA-256, including Plan049/053/054/055, the adopted Correction008 trust amendment, session authorization, Addendum021 authorization, prior Correction008 source review, Correction001, its plan review, implementation report and source review001. No mismatch or source-review gate gap was found.

## Candidate, storage and ownership

I evaluated the reviewed driver's pure `attempt_high_water` and `attempt_evidence_names` functions against current evidence without launching it: diagnostic high-water is **8**, so candidate **9** is the next index. The proposed directory is `diagnostic-049-009`. Its 26 driver-generated names are included in the artifact's 44 distinct basename-only output names; the other 18 are Main's bounded session/event/terminal records. I independently checked the proposed directory and every one of those 44 files (45 paths total): none exists or is a symlink. The candidate008 identity, proof, event files and handle-based abort remain historical; this check neither rewrites nor reuses them.

The artifact's seven artifact roots include the prior six roots and this PTY-correction root. Its no-follow, unique-inode scan records **67,614,234,142** bytes across **268,684 regular files**, no errors, and no `prompts` content read. `67,614,234,142 < 161,061,273,600` (150 GiB); headroom is **93,447,039,458** bytes, and reported free space is **467,030,917,120** bytes. I independently rescanned those same seven roots read-only without following symlinks or entering `prompts`: **67,614,289,134** unique regular-file bytes, **268,685 regular files**, zero scan errors, still under the cap. The 54,992-byte increase reflects post-snapshot files/edits; it does not change the capacity decision. All seven roots exist, and the candidate directory is inside the scanned progress root.

The included sandbox census saw only three namespace entries and was explicitly rejected as namespace limited. The saved fresh host census exited 0, scanned **488** entries, and reports no scan errors or matching Plan049/test workload. No new process census was run for this review. With prior sessions reported terminal, the evidence supports **B=0, H=0**, with the required charge floor `B+max(1,H)=1≤8`; CPU-only and serial restrictions remain binding. A later ambiguous or live session must be charged until exact retirement.

This PASS is limited to readiness to capture a new prospective proof. Main must retain the actual returned handle, use it for the structured start frame and mandatory same-handle live polls, keep its original visible tool objects, rehash the checked copies, and obtain a **separate independent review of the new originals versus copies and all proof/terminal evidence before `ADMIT`**. Attempt008 remains terminal and unadmitted; diagnostic005 remains a historical failure. No test, process signal, admission, payload, diagnostic or aggregate was launched here. Reviewer CPU time, token use and other resource overhead were not directly measured and are **unknown**.
