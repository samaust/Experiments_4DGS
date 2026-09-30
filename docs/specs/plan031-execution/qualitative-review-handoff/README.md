# Human qualitative review handoff

This is the review workflow specification. Package/viewer implementation and publication remain open in #30/#31.

Code generates the matched comparison package. Open its local viewer, compare the same frozen frames and synchronized clips across candidates, and use supporting diagnostics where relevant.

1. Check the package version, displayed candidate names and available/missing outputs.
2. Compare frozen-frame appearance and sharpness at the same zoom/crop.
3. Play synchronized clips to compare motion coherence, flicker, ghosting, popping and artifacts.
4. Record a short observation with the frame ID or clip/time, then choose a preferred candidate, tie, no clear preference, unable to judge or not applicable for each criterion.
5. Record an overall preference and the main tradeoffs. Include your name/handle and date. Save the review against the exact package version/hash.

One human reviewer is sufficient. No masks, labels, attestations, independent annotation reviewer, adjudication or external annotation files are required. Missing clips/outputs stay visible; an unfilled form is awaiting review. The code may validate and summarize your record, but cannot invent your opinions.

[Complete comparison contract](../qualitative-comparison-amendment.md). Actual result package publication belongs to #31, first human review/choice freeze to #33, and downstream review/final assessment to #34/#35.
