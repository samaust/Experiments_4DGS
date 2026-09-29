# Plan 031 execution specifications

The specs use the worker request/result contract, admission/ledger transitions and annotation import boundary approved by the user. Issue #3 is related preparation context, not their parent.

| Spec | GitHub issue |
| --- | --- |
| [Execution parent](execution-parent.md) | [#18](https://github.com/samaust/Experiments_4DGS/issues/18) |
| [S1 calibration recovery](s1-calibration-recovery.md) | [#19](https://github.com/samaust/Experiments_4DGS/issues/19) |
| [E5 DA3 build recovery](e5-da3-build-recovery.md) | [#20](https://github.com/samaust/Experiments_4DGS/issues/20) |
| [D2–D4 fit/check completion](depth-fit-check-completion.md) | [#21](https://github.com/samaust/Experiments_4DGS/issues/21) |
| [Independent annotations](independent-annotation-import.md) | [#22](https://github.com/samaust/Experiments_4DGS/issues/22) |
| [Scoring and reporting](benchmark-scoring-report.md) | [#23](https://github.com/samaust/Experiments_4DGS/issues/23) |

All specs carry `ready-for-agent`. Children #19–#23 belong to #18 through the native issue hierarchy. Parent closure requires all five children complete with verified acceptance evidence.

The first child creation partially succeeded before GitHub returned a GraphQL server error while attaching its parent. A read-only check located #19; the user authorized retry, and only the failed attachment was retried. No duplicate issue was created.

Publishing these specs grants no additional experiment attempts. S1/E5 recoveries still require their explicit approvals; independent scoring still requires reviewed human evidence.
