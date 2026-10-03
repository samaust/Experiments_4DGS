# D5/D6/D8 package budget proposal

**REVIEW only.** This changes no approval, attempt, code, asset, runtime or ledger.
The original REVIEW001 and DO001 remain immutable.

## Proposed bounds

| Candidate | Package allowance | Total download allowance | Retained artifacts |
|---|---:|---:|---:|
| D5 | 2 → 6 GiB | 3,452,514,348 → 7,747,481,644 bytes | 5 → 9 GiB |
| D6 | 2 → 6 GiB | 3,628,817,042 → 7,923,784,338 bytes | 5 → 9 GiB |
| D8 | 2 → 6 GiB | 3,452,481,328 → 7,747,448,624 bytes | 5 → 9 GiB |

Package allowance includes runtime dependency transfers and source archives beyond
the pinned required model assets. Transfer accounting can charge expanded cache
growth, which exceeds compressed wheel sizes. The artifact increase preserves the
previous 3 GiB difference between package and total artifact allowances; installed
runtime, cache growth, assets and outputs still require measured cap checks.

The MoGe proxy is 2,352,886,820 bytes (205,403,172 beyond 2 GiB), even before a
complete dependency closure. This is an agent-reported estimate using nearby
cached versions, not a measured Torch 2.6/Triton 3.2 installation. The retained D8
research estimates 2,566,011,011 bytes (418,527,363 beyond 2 GiB), using nearby Torch
and exact Triton metadata plus an NCCL reference. Required Torch 2.4.1 CUDA 12.4
size/dependency metadata remains unresolved. Neither estimate proves exact failure
or success. Six GiB provides room for these core packages, remaining dependencies,
source archives and accounting differences without claiming an exact resolved size.
D11's preliminary 3,452,511,054-byte estimate fits its existing 8 GiB allowance;
its ABI-specific and transitive closure remains unresolved, so no D11 increase is
proposed.

## Shared caps and limitations

Global download/artifact caps remain **110/210 GiB**. With the recorded D7 snapshot,
all remaining download upper bounds total 117,536,663,155 bytes including existing
usage, leaving 574,937,485 bytes below 110 GiB. This is a planning snapshot, not
fresh admission evidence. Actual live usage and pending reservations must be checked
again before every dispatch.

One revised 9 GiB artifact reservation fits that snapshot. However, adding **all**
remaining artifact upper bounds yields 232,833,523,712 bytes, exceeding 210 GiB by
7,347,740,672 bytes (6.843 GiB). The proposal therefore does **not** guarantee every
remaining candidate can retain its maximum simultaneously. Cache reuse and actual
footprints may reduce growth; neither is counted as guaranteed savings. If a later
reservation cannot fit, stop and review its disposition or a separate cap amendment.
This proposal authorizes neither artifact deletion nor a larger global cap.

## Approval and execution handoff

The accompanying `proposal.json` binds the baseline, source files, retained research,
revised allocations and canonical proposal hashes. The proposed
`depth-execution-review-002.json` retains every other candidate proposal unchanged.
After explicit approval, a new authorization must bind REVIEW002 and the revised
D5/D6/D8 hashes. DO001 cannot authorize those changed proposals. The integration
owner must preserve existing D2/D7/D9/D10/D11 approval lineage when choosing the
applicable review/authorization pair. Review and source qualification must match
that exact pair before execution.

One attempt per candidate, setup/CPU/GPU time budgets, device ceiling, model pins,
workloads, commercial qualification and single GPU ownership remain unchanged.
Host access must also work; a budget amendment cannot resolve an HTTP 403.
