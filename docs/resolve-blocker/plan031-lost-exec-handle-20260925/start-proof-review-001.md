# Independent review — candidate010 bootstrap return and start frame

**Verdict: PASS for sending only the exact matching `plan049-main-start-frame/v1` through returned session ID `87565`.** The frame must contain `schema: "plan049-main-start-frame/v1"`, `session_id: 87565`, and `event` equal to the **entire exact event000 object** reviewed here; it must be sent only through that same retained handle. This review authorizes no other send or poll, no identity proof/admission, `ADMIT`, test, diagnostic payload or aggregate. The start-frame result and later live same-handle proof require their own capture and independent review.

Main supplied the complete original visible `exec_command` return object in the review handoff and stated that it was emitted immediately after the call and matched the preserved `store()` value. I compared all five fields with event000's `result`: `chunk_id: "6565c3"`, `wall_time_seconds: 1.001101165`, `session_id: 87565`, `original_token_count: 117`, and the complete `output` string ending in CRLF. They match exactly as provided. This is a comparison against Main's first-party original-return handoff, not a new platform query by this reviewer. The saved event file SHA-256 is `9c0a454ecfc84f4ff95f159bb8a6e0c92f0d42a360ff91f738fe19511e5e24f6`, matching the requested target. No result field indicates exit, terminal state or error; absence of those fields means this is a live bootstrap return, not a terminal proof. Candidate010's new B/H ownership remains charged.

| Check | Result |
| --- | --- |
| Event/schema/handle | Exact 11-key `plan049-session-tool-event/v2`, `kind: diagnostic`, `index: 10`, `ordinal: 0`, `role: start`, `tool: exec_command`. The positive five-digit result `session_id` is **87565**, below the Plan054 handle-length bound, and equals Main's supplied original return. UTC `started` (`05:57:38.459Z`) precedes `returned` (`05:57:43.973Z`). |
| Command | `arguments.cmd` exactly equals shell quoting of the boundary's seven planned argv tokens: `exec`, the pinned environment Python, `-B`, the pinned driver, `diagnostic`, `10`, and the reviewed reason. `workdir` is this repository, `shell` is `/bin/bash`, `login: false`, `tty: true`, and `sandbox_permissions: require_escalated`; the prefix pins the executable and driver. The command is the bootstrap cleared by [launch-readiness review](launch-readiness-review-001.md). |
| Bootstrap line | The full result output is one complete JSON line with CRLF, which the driver permits. It reports `kind: diagnostic`, `index: 10`, and `awaiting_main_start_proof` with schema `registered-process-tree-job/v1`, `.job-ledger-diagnostic-049-010.jsonl` and its matching `.lock` path under the Plan049 run directory. `initial_sha256` is a 64-character hexadecimal digest. No extra output follows the line. |
| Output integrity | SHA-256 of the **exact output bytes**, including CRLF, is `f8bcfca7f591cab5fab8daa0e765dc4974090556f209bf0a4909a6b54b319bcd`, equal to event000's `output_sha256`. The result has `original_token_count: 117` under `max_output_tokens: 10000`; its JSON bootstrap line parses completely. |
| Terminal/noninteraction | `result` has only `chunk_id`, `wall_time_seconds`, `session_id`, `original_token_count` and `output`: no `exit_code`, `error` or `isError`. Main reports no same-handle interaction after this return. I made none. This does not establish terminal state, successful identity binding or admission. |

The nested call reports **1.001101165 wall seconds**; event000's two UTC stamps span about **5.514 seconds** at millisecond precision. Neither is CPU time, and their difference is not treated as a failure under the ordered-UTC trust contract. Candidate010 CPU, memory and process-tree use were not measured; both old native H charges remain unresolved as recorded at launch readiness. The reviewed handle `87565` is the only valid handle for this attempt; if Main cannot show the original return still retained and equal when sending, it must stop rather than reconstruct identity from this file.

## Exact input hashes

| Input | SHA-256 |
| --- | --- |
| [Event000](../plan031-progress-20260922/main-session-049-diagnostic-010-event-000.json) | `9c0a454ecfc84f4ff95f159bb8a6e0c92f0d42a360ff91f738fe19511e5e24f6` |
| [Launch boundary](../plan031-progress-20260922/main-preflight-049-diagnostic-010-launch-boundary-001.json) | `79a9bfec5c80ca83249a3102b1ab82cd42e3e489ac86336452d243b58ff3ce1c` |
| [Launch-readiness review](launch-readiness-review-001.md) | `2af9f6314ae97572a19e88f682e767fb367d7c0677412c0dfb5a4ca58defb2be` |
| [Raw-result-first correction](correction-001.md) | `a4b6c8ca291724ce79f4afedb0dbd4bbb0d6ce9e5664a1b7c5849a738615d447` |
| [Correction review](correction-review-001.md) | `a347d2701b7c5360cde0e46a9dab356b67d9ff39d3464d737a9861e24ae1612b` |
| [Plan049](../../../plans/plan_049.md) | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| [Plan054](../../../plans/plan_054.md) | `91d0ac7191d944b8cf2175b74c74aff3d70d4dba4a530431f223cb8aab2df62d` |
| [Plan055](../../../plans/plan_055.md) | `18506f655e7a2c95492fa88a038c869a4c993fa06d3ba628725158eaea77242f` |
| [Plan056](../../../plans/plan_056.md) | `b757b31e867b199f874ab55165717bbe26ef992b5a0d8ebc18060e05afcbf8b1` |

I read the saved files, compared the full original object supplied by Main with the saved result, recomputed SHA-256 and parsed the output with standard-library code. No project module was imported and no target process/session was polled, sent to, signaled, launched, admitted or tested. Individual review tool commands reported about 0.2 seconds of wall time; total reviewer wall, CPU and memory use were not measured. Historical and current workload resource use remain unknown unless separately measured.
