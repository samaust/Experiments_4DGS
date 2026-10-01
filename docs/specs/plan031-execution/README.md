# Plan 031 execution specifications

**Current depth extension:** [Plan 069](../../../plans/plan_069.md) adds D5–D11.
Generation #44 is a new child of #18; human review #45 is a child of #23 blocked
by #44. #34 waits for #45's new eligible metric-depth choice before new
depth-dependent execution, while reusable preparation continues. #35 includes
the expanded comparison. This prospective amendment preserves earlier accepted
reviews, proposals and execution records.

**Current scope:** [Scope amendment 001](qualitative-comparison-scope-amendment-001.md) takes precedence: isolated packages and initial review (#33) cover segmentation and depth only. Motion and neighbor method effects remain required comparisons on actual final renders (#34/#35); isolated M/N diagnostics are excluded from the current viewer. Applicable motion criteria and clip controls remain.

The active evaluation is human qualitative comparison of code-generated matched frames, synchronized clips and supporting diagnostics. [The amendment](qualitative-comparison-amendment.md) and [Plan 067](../../../plans/plan_067.md) supersede annotation-based comparison requirements. The user does not need to supply an external annotation bundle.

| Spec | GitHub issue |
| --- | --- |
| [Execution parent](execution-parent.md) | #18 |
| [S1 bounded recovery](s1-calibration-recovery.md) | #19 (completed bounded failed outcome) |
| [E5 recovery](e5-da3-build-recovery.md) | #20 |
| [Depth fit/check](depth-fit-check-completion.md) | #21 |
| [Qualitative packages](qualitative-review-package.md) | #22; #30/#31 |
| [Qualitative review/report](benchmark-scoring-report.md) | #23; #32–#35 |
| [Human review handoff](qualitative-review-handoff/README.md) | #33 |
| [Extended depth generation](depth-comparison-extension.md) | [#44](https://github.com/samaust/Experiments_4DGS/issues/44); parent #18 |
| [Extended depth review and choice](depth-comparison-review.md) | [#45](https://github.com/samaust/Experiments_4DGS/issues/45); parent #23; blocked by #44 |

#3 is completed related preparation; #18 is the execution parent. At this
extension's publication, #20/#21/#22/#30/#31/#32/#33 and the survey work were
closed under their completed scopes. The open prior-version agent issues are
#18/#23/#34/#35; both new specs carry `ready-for-agent`. #34 retains its existing
#33 dependency and gains #45; #35 remains blocked by #34. Keep parents open until
every child is complete. Existing annotation templates, validators, reviews,
scores and run artifacts preserve their original meaning. S1 follows its
[standing retry amendment](s1-retry-policy-amendment-001.md). Specification
publication launches no jobs and grants no new allocations.

The [publication record](depth-extension-publication-001/README.md) records the
verified native issue relationships and protected historical hashes. The
[approved depth-extension tickets](depth-extension-tickets/README.md) publish
#46–#59 under #44 and #60–#62 under #45, with verified native blocking links.
Their initial frontier is #46; all parent issues remain open.

The [original ticket publication](tickets/README.md) is historical; current scope
comes from this index, the linked specs and live issues.
