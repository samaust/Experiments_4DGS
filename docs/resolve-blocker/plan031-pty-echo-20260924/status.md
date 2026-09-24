# PTY echo blocker resolution status

Calling task: complete Plan031 under Plan049 and adopted Plan053, with reviewed Plan054 trust contract. Current blocker: exact PTY echo in the original Main `write_stdin` response causes the existing proof validator to reject the readiness response before admission.

## Criteria

| ID | Outcome | State |
| --- | --- | --- |
| C1 | Explain whether exact observed PTY echo can be recognized without weakening byte-for-byte transcript trust or changing unrelated behavior. | met; independent review supports an exact echo-only rule |
| C2 | Save reviewed plan for a narrowly scoped correction within the authorized nine paths; retain all other gates and caps. | met; exact reviewed bytes adopted |
| C3 | Implement exact echo recognition and synthetic regression coverage through existing test methods only. | met; focused test and static/collection checks pass |
| C4 | Independent source review passes exact nine-path hashes and behavioral preservation checks. | met; review001 PASS |
| C5 | Main's proof check accepts the exact captured event, rejects mismatched echo/unexplained output, and attempt008 remains unadmitted/terminal. | met for historical compatibility; attempt008 remains unusable |
| C6 | Fresh independent runtime clearance, preflight, and later authorized serial diagnostics/final aggregate. | preflight and independent runtime-readiness review PASS for proof capture only; diagnostic and aggregate remain pending |

## Stage and evidence

Stage: fresh prelaunch review passed; preserve the reviewed preflight as a local checkpoint, then capture a new candidate009 same-handle proof. Validated implementation milestone is committed as `653f51b` (`Accept exact Plan049 PTY start-frame echo`). Plan055 SHA-256 `18506f655e7a2c95492fa88a038c869a4c993fa06d3ba628725158eaea77242f` and Correction001 SHA-256 `89271f7ee1156326a4edce7079ad812ecb93f7674b9522d1233f6e7927d20136` are adopted after [independent plan review PASS](plan-review.md), SHA-256 `9f454e6468f53770ed3702eaa889b5f204e93f941aeecb5518034daa8ad26949`. [Implementation001](implementation-001.md) records the two-path delta and focused tests; [independent source review001](independent-source-review-001.md), SHA-256 `dac8b9fbef2fb4ec272a204f7edacbabcbd96c3b55c63f52ccd3e32cc1550551`, independently reran the test and passed all nine hashes. Main's historical proof compatibility check passed all four saved events; that does not make attempt008 reusable or provide live clearance.

Fresh candidate-009 preflight is [main-preflight-049-diagnostic-009-prelaunch.json](../plan031-progress-20260922/main-preflight-049-diagnostic-009-prelaunch.json): source members 78; all nine reviewed path hashes and 14 listed authorities match; all Python source AST parsed; high-water 8/candidate 9; 45 output paths vacant; artifact usage 67,614,234,142 / 161,061,273,600 bytes with zero scan errors; host process census 488 entries, no matching Plan049/test workloads or errors. The sandbox view showed only three namespace entries and was not accepted. Current owned workload count is B=0,H=0, charge floor 1. This artifact grants preflight PASS only. Attempt008 event files, proof, failure, identity request and handle-based terminal remain immutable historical records; no diagnostic payload ran. Diagnostic005 remains failed.

Independent [prelaunch runtime review001](prelaunch-runtime-review-001.md), SHA-256 `442677f16060be0a047f0969f171724513d0bf5bd6a0120bcec278116348929c`, passed for one fresh serial CPU-only **pre-admission proof capture only**. The reviewer independently checked source and authority hashes, candidate high-water, all 45 vacant output paths, the saved host census and artifact-cap scan; its rescan was 67,614,289,134 bytes / 268,685 files, zero errors, still below 150 GiB. It explicitly grants no ADMIT, payload, diagnostic, aggregate, or acceptance of a live proof. A fresh actual-launch-boundary occupancy/capacity check is still required. This evidence-only checkpoint records the preflight and its review.

## Allocation and restrictions

Use one distinct `gpt-6-sol` high-effort reviewer, then a distinct plan author/reviewer, implementer, and independent source validator sequentially; no nested delegation and at most one active subagent. No Plan049 payload, admission, tests, aggregate, or diagnostic launch until the corresponding review/preflight/runtime gates pass. CPU-only, serial `B+max(1,H)≤8`, 150 GiB artifact cap, 64 MiB memo cap, 8 MiB ledger cap, original behavioral deadlines/assertions/selectors/error precedence and authorized nine source paths remain binding. Operational duration has no cap. Agent CPU/token use is not directly measured. Main owns jobs, live evidence, preflight, integration, and commits.

## Next action

Commit the preflight and its independent review as an evidence-only checkpoint. Then repeat the fresh launch-boundary ownership/capacity, source/hash, artifact-cap, output-path and high-water checks and begin a new candidate009 same-handle pre-admission proof capture only if they still pass. Save each exact tool return and the returned handle immediately. A distinct independent reviewer must compare the new original tool objects, checked copies, hashes, complete proof, terminal, and retirement evidence before any ADMIT. Attempt008 is never resumed or reused. If exact handle retention or trusted session recovery fails, record the blocker and stop that launch work.
