# Independent review — candidate010 preflight002

**Verdict: NEEDS_REVISION of the saved preflight before it can support an exact 45-path clearance.** The record is otherwise internally consistent on source/authority bytes, index, artifact cap and charged capacity, and it grants no launch. Its `candidate_outputs.broad_names` contains the two **diagnostic009** ledger paths, `.job-ledger-diagnostic-049-009.{jsonl,lock}`, where the corresponding **diagnostic010** paths should be. It therefore checked 44 named paths plus the directory but did not check the claimed exact 45-path candidate010 broad set. The separate `driver_exclusive_names` list correctly contains both diagnostic010 ledger paths, and its recorded 27-path vacancy check covers them. The union of the two recorded lists covers all expected candidate010 paths, so this is a record/grammar integrity defect rather than evidence of a known collision. Keep preflight002 intact as discovery evidence; correct the substitution and produce a fresh, exact preflight before independent readiness review.

| Gate | Finding |
| --- | --- |
| Source and authority | All **78** recorded source members and **28** authority/input records still match their recorded byte lengths and SHA-256 values in a read-only rehash. The record marks all source members as matching the frozen source review, reports no AST errors, and reports no prior authority-anchor mismatch. I independently verified current bytes against this record, not every external frozen anchor. No `prompts` path was read. |
| Attempt identity | Driver high-water **9**, next index **10**, marker SHA-256 matches the saved legacy consumption marker. Candidate009 stays consumed. The prospective identity path is `launch-identity-049-diagnostic-010.json` and is recorded vacant; no identity reuse is proposed. |
| Output paths | Broad list: 44 names + directory = 45 claimed paths, but two names are for 009. Driver list: 26 correct 010 names + directory = 27 paths. Expected 010 broad set minus recorded broad set is exactly the two 010 ledger paths; the two 009 ledger paths are extraneous. The union includes all 44 expected 010 names. The record says `all_vacant: true` and `collisions: []`, but its broad-path claim needs correction. Vacancy is time-bounded and must be repeated at the final boundary. |
| Artifacts | Recorded unique inode bytes **67,614,363,478** versus cap **161,061,273,600** (150 GiB), margin **93,446,910,122** bytes. The record reports no scan errors, symlink following disabled, and `prompts_content_read: false`. This is a saved measurement, not a current rescan by this reviewer. |
| Ownership/capacity | Corrected local candidate009 B is **0**; its unknown native session remains charged as **H=1**. Reserving candidate010 root **B=1** and outer session **H=1** gives projected `B+max(1,H)=1+max(1,2)=3≤8`. The saved census reports three visible process/task entries, no matching launch driver and no errors. This small namespace is a bounded observation; it does not retire the unresolved H. |
| Scope/release | Governing Plans049/054/055 and adopted Correction002 retain serial CPU-only operation, behavioral deadlines and proof rules. Preflight002 is read-only evidence and does not independently demonstrate a future command's CPU-only/serial execution. Its own disposition grants no start, admission, test, diagnostic or aggregate. Fresh final source/authority/artifact/path/high-water/host ownership checks and a distinct independent readiness PASS remain required before any launch. |

The preflight ran from `2026-09-25T05:32:19.606184Z` to `05:32:21.027131Z` and records **1.420945121999921 monotonic wall seconds**. This is not CPU time. Candidate009 and reviewer CPU, memory and total resource use were not measured and remain unknown.

## Exact file hashes

| Input | SHA-256 |
| --- | --- |
| [Preflight002](../plan031-progress-20260922/main-preflight-049-diagnostic-010-prelaunch-002.json) | `27023008be87fa117dad3029ca73f5c248440dc2990b0a82db38dfaad2453229` |
| [Legacy 009 marker](../plan031-progress-20260922/main-launch-attempt-start-009.json) | `4badd51f6deebd9d7b5cd2453f2eec2655fb50f8afafad2794898553c1aeed6a` |
| [Original 009 boundary grammar](../plan031-progress-20260922/main-preflight-049-diagnostic-009-launch-boundary-001.json) | `5f6803d850471d573af0a700f5bc86ea09aff588db6e84aa0c13c3a3d2f2f3ff` |
| [Current driver](../plan031-progress-20260922/launch-049-exec.py) | `e28b3874d1830c934fae624eee254a25d25517fcc22cb6fa41f4da5191d62af7` |
| [Plan049](../../../plans/plan_049.md) | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| [Plan054](../../../plans/plan_054.md) | `91d0ac7191d944b8cf2175b74c74aff3d70d4dba4a530431f223cb8aab2df62d` |
| [Plan055](../../../plans/plan_055.md) | `18506f655e7a2c95492fa88a038c869a4c993fa06d3ba628725158eaea77242f` |
| [Plan056](../../../plans/plan_056.md) | `b757b31e867b199f874ab55165717bbe26ef992b5a0d8ebc18060e05afcbf8b1` |
| [Correction002 proposal](correction-002-proposal.md) | `c6559c57e0a88fda9b08ab8041aa1f55e873b083f85ecaa7cffa9c86c3f70af4` |
| [Correction002 review](correction-002-review-001.md) | `ae0d3f47ec537b6989d46037d0890d2dc0c48fcf913db015757d6e2d9aa0883f` |
| [Correction002 adoption](correction-002-adoption.md) | `3a004862eb45168830c9468f15d797a70a1fd54ba231bd9632c97d96effa3f96` |

The review read the saved preflight, used standard-library JSON and SHA-256 to check its listed file bytes and compare path sets, and ran `sha256sum` on the governing records above. No project code was imported, source was changed, or process/session was contacted, launched, admitted or tested. Reviewer tool commands returned in about 0.2 seconds each; total reviewer wall, CPU and memory use were not measured.
