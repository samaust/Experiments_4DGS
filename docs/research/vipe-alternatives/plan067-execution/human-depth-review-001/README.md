# Depth human review 001 — active comparison scope

The latest user correction is: **“I make a mistake. Remove Motion and Neighbors.
Keep segmentation and depth.”** This supersedes the earlier instruction to
remove depth and neighbors. The active qualitative comparison therefore covers
segmentation and depth only; motion and neighbors are excluded. Earlier scope
instructions remain history and are not active gates.

`depth-submitted.json` preserves the exact original depth review, including its
blank reviewer/date, empty examples, blank tradeoffs, observations and lexical
typos. The reviewer prefers D4's displayed close-object boundaries.

`depth-corrected.json` contains only these faithful metadata/reference changes:

- Reuse reviewer name `samaust` and review date `2026-09-30`.
- Bind preferred frozen-frame, sharpness and overall judgments to D4 at the
  explicitly confirmed `camera1-selection-175`, frame `175`.
- Populate tradeoffs with the verbatim sentence already supplied in the sharpness
  observation: “D4 is less sharp but looks much better.” The raw tradeoffs field
  stays blank; this extracts the reviewer's statement rather than inventing one.

The actual-review validator passed against the original immutable package and
its charged generation graph. `confirmation.json` binds both records, records
the normalization and exact camera confirmation, and preserves the latest and
superseded scope instructions. The root agent coordinates actual immutable import
and evidence-based engineering eligibility before freezing the research D4 choice.
This handoff launches no experiment and writes no live ledger event.

The reviewed package 001 still records D2 as missing. This review is not rebound
to the newer package containing D2 and cannot imply the reviewer compared D2.
Motion and artifacts retain the submitted `not_applicable` dispositions.
Colorized depth-map sharpness and boundary observations are human visual
preferences; they do not establish measured physical depth accuracy, final-render
sharpness or quality of an unseen combined pipeline. Historical excluded-group
results and engineering obligations remain preserved separately.
