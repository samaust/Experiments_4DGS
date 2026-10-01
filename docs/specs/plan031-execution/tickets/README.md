# Plan 031 execution tickets

**Historical publication snapshot:** the table and original frontier below
describe the earlier 12-ticket publication. Current work uses the
[execution index](../README.md) and [Plan 069](../../../../plans/plan_069.md).
#24–#33 retain their completed scopes; #34/#35 remain open with updated local
copies and GitHub acceptance criteria. New generation #44 and review #45 extend
the comparison, with #45 blocking #34. Annotation bundles are no longer required.
S1 follows its separately recorded standing fix-and-retry authority; the old
attempt/approval language below does not override that amendment.

The user approved this 12-ticket breakdown before publication. All tickets are open and carry `ready-for-agent`, with native parent and blocking links verified against their local copies. Existing spec bodies and parent states were not edited.

| Ticket | What it delivers | Parent | Blocked by |
| --- | --- | --- | --- |
| [#24](https://github.com/samaust/Experiments_4DGS/issues/24) | Qualify S1 recovery controls and produce a REVIEW proposal | #19 | None |
| [#25](https://github.com/samaust/Experiments_4DGS/issues/25) | Execute the explicitly approved S1 calibration attempt | #19 | #24 |
| [#26](https://github.com/samaust/Experiments_4DGS/issues/26) | Repair E5 packaging and produce a REVIEW proposal | #20 | None |
| [#27](https://github.com/samaust/Experiments_4DGS/issues/27) | Execute and qualify the approved E5 recovery | #20 | #26 |
| [#28](https://github.com/samaust/Experiments_4DGS/issues/28) | Complete D2 fit and check | #21 | #27 |
| [#29](https://github.com/samaust/Experiments_4DGS/issues/29) | Complete D3 and D4 checks using existing fits | #21 | None |
| [#30](https://github.com/samaust/Experiments_4DGS/issues/30) | Validate the independent annotation import workflow | #22 | None |
| [#31](https://github.com/samaust/Experiments_4DGS/issues/31) | Import the supplied independently reviewed annotations | #22 | #30 |
| [#32](https://github.com/samaust/Experiments_4DGS/issues/32) | Qualify scoring and eligibility through the aggregate interface | #23 | None |
| [#33](https://github.com/samaust/Experiments_4DGS/issues/33) | Score actual component evidence and freeze finalist decisions | #23 | #25, #28, #29, #31, #32 |
| [#34](https://github.com/samaust/Experiments_4DGS/issues/34) | Resolve downstream stages through checked admission | #23 | #33 |
| [#35](https://github.com/samaust/Experiments_4DGS/issues/35) | Produce and validate the final benchmark assessment | #23 | #34 |

The initial frontier is #24, #26, #29, #30 and #32. Start only work whose blocking tickets are complete. Extra S1/E5 attempts require separate explicit approval, and actual annotation import requires the human-reviewed bundle. Use one GPU worker at a time. No experiment was dispatched during ticket publication.
