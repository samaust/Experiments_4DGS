# Independent review — candidate010 preflight005

**Verdict: PASS as bounded prelaunch evidence only.** Preflight005 includes both separately unresolved native outer sessions in capacity, uses the correct candidate010 path set, and records no interaction or launch. It does not authorize a candidate010 launch; a distinct readiness decision and fresh final boundary checks are still required.

| Check | Result and limit |
| --- | --- |
| Source and authority | Independently rehashed all **78** listed source files and **42** authority/review inputs against recorded lengths and SHA-256: **zero mismatches**. The 14 fixed authority anchors match the original diagnostic009 boundary; all carried expected hashes match. The 42 include revised blocker status, Correction003 proposal, independent review and adoption, and the previous preflight review. The record reports all 78 Python/source checks clean and no AST errors; I did not run project code or tests. No `prompts` path was read. |
| Index and consumption | The unchanged driver is SHA-256 `e28b3874d1830c934fae624eee254a25d25517fcc22cb6fa41f4da5191d62af7`. A read-only direct-directory name audit matching its inspected high-water patterns found diagnostic high-water **9**; the only index-9 match is the legacy consumed-attempt marker, with none above 9. Thus index **10** is next. The marker hash matches the record. Diagnostic006's identity and candidate009's index/identity/paths remain consumed. |
| Paths | The broad set has **44 distinct candidate010 names**, including both `.job-ledger-diagnostic-049-010.{jsonl,lock}`, plus its directory: **45 exact paths**. There is no diagnostic009 name. The driver-specific 26 names are a subset, giving 27 paths with the directory. The record says all vacant with no collisions; an independent read-only file/symlink check at review time also found none of the 45 occupied. This is a time-bounded observation, not a reservation. |
| Artifact cap | The saved scan includes **eight** declared roots, now including `plan031-lost-exec-handle-20260925`; it reports no errors, no symlink following and no `prompts` content read. Its **67,614,668,863** unique-inode bytes plus a **65,536** byte allowance give **67,614,734,399**, which is **93,446,539,201** bytes below the 150-GiB cap of **161,061,273,600**. It reports 268,722 regular files. I checked the arithmetic and root list, not a second full filesystem scan. |
| Ownership and process scope | Correction002 retires only candidate009's local B; Correction003 independently retires only diagnostic006's local B. Each lost native session remains unknown and charged **H=1**, so `B_current=0`, `H_existing=2`. Reserving candidate010 root B=1 and outer session H=1 gives projected `B+max(1,H)=1+max(1,3)=4≤8`. The saved current process namespace has **three** entries/threads (`codex-linux-sandbox`, `/bin/bash`, `python3`), no census errors and zero matches under its stated exact-token driver/capture/pytest matcher. The record does not contain full argv or independently prove host-wide absence; its own observer shell is not counted as a workload match. Current ownership and any control-session charge must be reassessed at the final boundary. |
| Scope and no interaction | The saved Main flags say neither old lost handle was polled or signaled, neither old identity was admitted or reused, and candidate010 was not started. These are bounded action records, not proof of every future action. Plans049/054/055 retain serial CPU-only execution, exact same-handle proof, all behavior limits and resource caps. |

Preflight005 records `2026-09-25T05:49:58.062614Z` to `05:49:59.485114Z` and **1.4270217450002747 monotonic wall seconds**. That is not CPU time. Its three process/thread entries are a namespace snapshot, not measured full host ownership or terminal proof for either native session.

## Exact inputs and hashes

| Input | SHA-256 |
| --- | --- |
| [Preflight005](../plan031-progress-20260922/main-preflight-049-diagnostic-010-prelaunch-005.json) | `d70fda2bb73778e1a264015d53d28142642c8867ce4984e97fb89e9ee47d397b` |
| [009 consumed marker](../plan031-progress-20260922/main-launch-attempt-start-009.json) | `4badd51f6deebd9d7b5cd2453f2eec2655fb50f8afafad2794898553c1aeed6a` |
| [Original 009 authority/path boundary](../plan031-progress-20260922/main-preflight-049-diagnostic-009-launch-boundary-001.json) | `5f6803d850471d573af0a700f5bc86ea09aff588db6e84aa0c13c3a3d2f2f3ff` |
| [Current driver](../plan031-progress-20260922/launch-049-exec.py) | `e28b3874d1830c934fae624eee254a25d25517fcc22cb6fa41f4da5191d62af7` |
| [Blocker status](status.md) | `e7dd06885aed341594e1182c34cb538932817717a301b6a2e8c1667d202ebe9e` |
| [Correction003 proposal](correction-003-proposal.md) | `b3163aa43f0b839d4917bcdd3f9032b7c414e7fdeda6ecbf3192441af2120617` |
| [Correction003 review](correction-003-review-001.md) | `b0bce6127e1e6f2b24e1613940d92a7b9fda136650a4d062f90268c4f1cfac8c` |
| [Correction003 adoption](correction-003-adoption.md) | `3991cf4e3d3fb19168174bd690ea2c0586e1d9bde305021aeeab84363ad5a881` |
| [Prior preflight review](preflight-review-002.md) | `618f0ed06c0f57a93eecf1ce0487b0ee8681997a265cf4c8c0d8aa12f5f048c2` |
| [Plan049](../../../plans/plan_049.md) | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| [Plan054](../../../plans/plan_054.md) | `91d0ac7191d944b8cf2175b74c74aff3d70d4dba4a530431f223cb8aab2df62d` |
| [Plan055](../../../plans/plan_055.md) | `18506f655e7a2c95492fa88a038c869a4c993fa06d3ba628725158eaea77242f` |
| [Plan056](../../../plans/plan_056.md) | `b757b31e867b199f874ab55165717bbe26ef992b5a0d8ebc18060e05afcbf8b1` |

**Remaining boundary:** Main must perform a fresh exact source/authority/artifact/output-path/high-water/ownership check immediately before any proposed launch, preserve **both** old H charges and account for any live control/readback session, bind the new identity and serial CPU-only command, and obtain a separate independent launch-readiness PASS. No start frame, admission, diagnostic, test or aggregate follows from this review.

Review commands used read-only standard-library JSON/SHA-256, direct path/name checks and `sha256sum`; no project import, test, process/session contact, launch, admission or source edit occurred. Individual command returns reported about 0.2 seconds of wall time. Total reviewer wall, CPU and memory use were not measured; historical diagnostic006/candidate009 CPU, memory and native-session resource use remain unknown.
