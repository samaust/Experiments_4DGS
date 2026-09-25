# Independent exact-byte review — Plan056 Correction001

**Verdict: PASS for prospective correction only.** Reviewed [Correction001](correction-001.md) at 2026-09-25T04:44:29Z. This review clears **no live launch, candidate010, session contact, admission, diagnostic, test or aggregate**. Candidate009 remains unresolved and charged until authenticated exact-session/job and descendant evidence passes independent review.

| Input | Current SHA-256 |
| --- | --- |
| [Correction001](correction-001.md) | `a4b6c8ca291724ce79f4afedb0dbd4bbb0d6ce9e5664a1b7c5849a738615d447` |
| [Plan056](../../../plans/plan_056.md) | `b757b31e867b199f874ab55165717bbe26ef992b5a0d8ebc18060e05afcbf8b1` |
| [Objective](objective.md) | `27a894aea696cf0db0e15722b2503d5b522d6cb742c4e9cd593e1cb05a040af7` |
| [Lost-handle record](lost-handle-001.json) | `370e0797b56d5dfcbed96d7d58680c4a113f333c0175999320a50b53772e1386` |
| [Original host census](host-census-001.json) | `3bd9ae392a2a8923d2684dd31043acc96d707dce48bf697b48bd9ffc334cc5c6` |
| [Candidate009 vacancy observation](candidate009-partial-output-check-001.json) | `d98172668853c6c6e13db2e8f891c931668c9ea21a58c987b69021dd62671243` |
| [Initial review](review-001.md) | `0aaad98e174ddabbc45c5e109310ae016bed7aebfb7f93aa802d35477d115916` |
| [Plan056 review](plan-review-001.md) | `c3560442c40f684ce39c8a505527c6238d3f64b27cb19b6e804c7796ded9d18a` |
| [Fresh host census](host-census-002.json) | `c024f1dbb3b5098e5b81b8cc7c5dc0e8052cdf222bd25f8e49b91de9282593dd` |
| [Fresh census tool-return copy](host-census-002-tool-return.json) | `153777f5847740945b17bc097ee8e33ea62471ecd226ce721adff609e4a93977` |
| [Plan049](../../../plans/plan_049.md) | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| [Plan053](../../../plans/plan_053.md) | `33f7a8a1d292dade248295a3594b0d4bdff451f1685ad35bc104065be7178252` |
| [Plan054](../../../plans/plan_054.md) | `91d0ac7191d944b8cf2175b74c74aff3d70d4dba4a530431f223cb8aab2df62d` |
| [Plan055](../../../plans/plan_055.md) | `18506f655e7a2c95492fa88a038c869a4c993fa06d3ba628725158eaea77242f` |

The current user instruction, supplied in this conversation by Main, is: “I authorize a rerun to regenerate the missing data. But this means that you need to fix the bug beforehand so that the same issue does not happen again.” This is conversation-level authority, not an artifact in the reviewed repository. Correction001 interprets it narrowly: fix and review the return-capture ordering, first resolve candidate009 exact ownership and retirement, then recheck every fresh gate before any new serial CPU-only diagnostic. It neither reuses nor retrospectively validates diagnostic009.

The saved lost-handle record supports the specific orchestration failure: the nested `exec_command` returned to Main's JavaScript wrapper, which referenced unavailable `crypto` before saving or emitting its return, raising `ReferenceError: crypto is not defined`. This does not establish a Plan049 driver defect, nested-command failure or terminal state. Fresh census002 records a read-only PID/argv/state observation at `2026-09-25T04:40:20.361190Z`; its separate tool-return copy shows synchronous census exit 0. Neither establishes the original exec session identity or current liveness. The saved census copy by itself does not attest the wrapper's `store`/`text` ordering; Correction001 correctly treats that exercise as limited and not live-handle proof.

The proposed dedicated cell's order, `const r = await tools.exec_command(args); store(uniqueAttemptKey, r); text(r);`, is feasible under the current `functions.exec` helper behavior. In this review, a synthetic nested serializable object was stored and passed directly to `text(r)`; the outer cell completed and emitted its complete JSON value. A later cell loaded the same object and confirmed its nested fields. No `JSON.stringify` call is required between `store` and `text` for this helper. This check used no `exec_command`, process or live session and does not prove a future full tool return will fit the output budget. Correction001 requires successful outer completion, complete visible original return, exact positive bounded handle, and later copy/readback equality; truncation or any missing result stops the new attempt. `store` remains session-local and non-atomic, so the post-return/pre-store-or-emit failure window is honestly retained.

The correction preserves Plan049/053/054/055 scope and behavior: exact nine-path source ceiling, original assertions/declarations/selectors/order, W/C and protocol/scenario/setup deadlines, session-bound/v2 original-result trust, Plan055 PTY echo rule, serial CPU-only `B+max(1,H)≤8` with ambiguous ownership and control/readback charges, 150 GiB artifacts, one ≤64 MiB memo, hard 8,388,608-byte ledger and host/environment limits. It adds no operational time, attempt or correction ceiling. Fresh source/authority/artifact/output-path/high-water/vacancy/ownership/capacity preflight and distinct independent runtime review remain required. The new attempt must use a new index, identity request and paths only after exact retirement of diagnostic009's session/job and descendants. Unknown candidate009 resource use stays unknown. No source, repo test, session contact, launch, staging or commit was performed for this review.
