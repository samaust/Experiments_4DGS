# Independent review — corrected candidate010 preflight004

**Verdict: PASS as bounded prospective preflight evidence; no launch clearance.** Preflight004 corrects the path error in preflight002 and the observer self-match reported for preflight003. Its saved claims are internally consistent and its 78 source and 31 authority/review file records match current bytes. This review does not replace the required fresh final boundary preflight or a distinct launch-readiness decision.

| Check | Independent finding and limit |
| --- | --- |
| Source/authority bytes | Rehashed all **78** listed source members and **31** authority/review inputs: zero byte-length or SHA-256 mismatches. All 14 records marked as fixed anchors match the original diagnostic009 boundary's authority hashes; the other 17 are current review/adoption inputs, and every carried `expected_sha256` matches. The saved record reports 78 AST parses and no errors; I did not run a project import or test. No `prompts` path was read. |
| Index/high-water | The unchanged driver hash matches the earlier reviewed scanner. A read-only direct-directory name audit using its inspected patterns found diagnostic high-water **9**, with the regular legacy `main-launch-attempt-start-009.json` as the only index-9 match and none above. The marker hash matches, its `kind/index` are diagnostic/9, and the proposed next index is **10**. Candidate009's identity and paths remain consumed. |
| Output paths | The broad set has **44 distinct candidate010 names**, including both `.job-ledger-diagnostic-049-010.{jsonl,lock}`, plus `diagnostic-049-010`: exactly **45** paths. It matches the original 009 broad grammar with the candidate number changed and contains no 009 names. The driver's 26-name subset plus directory is **27** paths and is contained in the broad set. The record reports no collisions and a vacant new identity path; a separate read-only current path check also found no file or symlink at any of the 45 paths. This vacancy is not a reservation. |
| Artifact cap | The saved scan covers seven declared roots, skips symlinks and `prompts` content, deduplicates inode bytes, reports **268,692** regular files and no errors. It records **67,614,509,545** unique-inode bytes and a **67,614,575,081** byte upper bound including 65,536 bytes for this record; the latter is **93,446,698,519** bytes below the 150-GiB cap of **161,061,273,600**. I checked its arithmetic and assumptions, not a second full artifact scan. |
| Process/thread and capacity | At `2026-09-25T05:39:16.737394Z`, the saved **current process namespace** shows three entries and three threads: `codex-linux-sandbox`, `/bin/bash`, and `python3`, with no census errors. Its exact-token matcher reports **zero** owned workloads despite the shell/Python observer entries; this demonstrates that this observation did not match the shell's embedded preflight command text. The record stores a matcher description and summary rows, not its executable matcher code or full argv, so I cannot attest arbitrary future matcher behavior or a host-wide census from this file. Candidate009's local B is retired under adopted Correction002, while its unknown native session remains **H=1**. Reserving candidate010 B=1 and H=1 gives projected `B+max(1,H)=1+max(1,2)=3≤8`. |
| Scope/noninteraction | The saved record says candidate009 was not contacted, admitted or reused and candidate010 was not started. It is a bounded Main report, not proof of every later action. Plans049/054/055 keep serial CPU-only work, exact session proof, behavior limits and all other caps; this read-only preflight does not execute or clear a diagnostic. |

Preflight004 records `2026-09-25T05:39:15.318869Z` to `05:39:16.737394Z` and **1.4185181650000231 monotonic wall seconds**. This is not CPU time. The process/thread counts are a three-entry namespace snapshot, not a measured full host process tree or a terminal proof for the old native H.

## Exact file hashes

| Input | SHA-256 |
| --- | --- |
| [Preflight004](../plan031-progress-20260922/main-preflight-049-diagnostic-010-prelaunch-004.json) | `6ddefea83d735d611bbd8e915e9213e6037166d8487c8c1a810308522767b72a` |
| [009 legacy marker](../plan031-progress-20260922/main-launch-attempt-start-009.json) | `4badd51f6deebd9d7b5cd2453f2eec2655fb50f8afafad2794898553c1aeed6a` |
| [Original 009 boundary](../plan031-progress-20260922/main-preflight-049-diagnostic-009-launch-boundary-001.json) | `5f6803d850471d573af0a700f5bc86ea09aff588db6e84aa0c13c3a3d2f2f3ff` |
| [Driver](../plan031-progress-20260922/launch-049-exec.py) | `e28b3874d1830c934fae624eee254a25d25517fcc22cb6fa41f4da5191d62af7` |
| [Previous preflight review](preflight-review-001.md) | `7b53dd8a3fed85b539bc1e55dfff5bf329a9e2a252e1e7062e16736e2fcbc6ca` |
| [High-water review](high-water-review-001.md) | `afb08a43eb8e828e6cb08911308a28e141809a6439a46b113ef025cb578a80f5` |
| [Plan049](../../../plans/plan_049.md) | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| [Plan054](../../../plans/plan_054.md) | `91d0ac7191d944b8cf2175b74c74aff3d70d4dba4a530431f223cb8aab2df62d` |
| [Plan055](../../../plans/plan_055.md) | `18506f655e7a2c95492fa88a038c869a4c993fa06d3ba628725158eaea77242f` |
| [Plan056](../../../plans/plan_056.md) | `b757b31e867b199f874ab55165717bbe26ef992b5a0d8ebc18060e05afcbf8b1` |
| [Correction002 adoption](correction-002-adoption.md) | `3a004862eb45168830c9468f15d797a70a1fd54ba231bd9632c97d96effa3f96` |

**Remaining boundary:** Main must perform and save fresh exact source/authority/artifact/path/high-water/ownership checks at the launch boundary, retain candidate009 H=1 in capacity, use a new identity request and paths, bind a serial CPU-only command, and obtain the required independent launch-readiness PASS. This report authorizes no candidate010 launch, start frame, admission, test or aggregate.

Review commands used standard-library JSON/SHA-256 and read-only path/name checks plus `sha256sum`; no project module was imported. No target process/session was contacted, and no test, diagnostic, launch, admission or source edit occurred. Individual review tool commands reported about 0.2 seconds of wall time; total reviewer wall time, CPU time and memory use were not measured. Candidate009's historical CPU/memory use remains unknown.
