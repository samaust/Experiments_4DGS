# Final qualitative benchmark assessment

**Status: blocked**

Human observations concern only their bound outputs and named examples.
Physical depth accuracy: unverified.
Full reconstruction stack commercial clearance: unverified.
Component commercial permission does not establish full-stack clearance.
No annotation accuracy, statistical significance or unseen final-render quality is inferred.

## Remaining requirements

- missing extended-depth human review
- missing frozen metric-depth choice
- missing final-render human review
- missing execution/resource accounting
- missing tests/qualification/independent reviews
- unfinished required issues: 34, 44, 45, 60, 61, 62

## Historical component observations

### segmentation

[bound evidence](</home/auss/git_repos/samaust/Experiments_4DGS/docs/research/vipe-alternatives/plan067-execution/human-review-001/confirmed-import-result.json>)

Reviewer: samaust; 2026-09-30

historical component observation; not current metric-depth selection

| Criterion | Human observation | Preference | Named examples |
| --- | --- | --- | --- |
| frozen_frame | S0: missing parts of shoes of two players, incorrectly segmenting an object in front of player. S2: players are well segmented, only minimal wrong pixels, player correctly selected through a the basket mesh S3: missing a shoe, not selecting through the basket mesh, incorrectly selecting on object in front of a player, missing one shoe S4: missing part of the player moving the fastest and most blurry because of this movement, slight wrong selection of pixels near a person, player correctly selected through the basket mesh | {"outcome": "preferred", "candidate_ids": ["S2"]} | [{"candidate_id": "S2", "selection_id": "camera1-reconstruction-0", "frame_id": 0}] |
| motion | Could not compare. Playback does not work. | {"outcome": "unjudgeable", "candidate_ids": []} | [] |
| artifacts | Artifacts can happen when rendering after learning. The is only a segmentation test so it cannot produce artifacts. | {"outcome": "unjudgeable", "candidate_ids": []} | [] |
| sharpness | Sharpness needs to be evaluated on final rendering. | {"outcome": "unjudgeable", "candidate_ids": []} | [] |
| overall | The segmentation needs to be the best for the players close to the ball because it's what viewers will focus on. S2 seems the best overall. | {"outcome": "preferred", "candidate_ids": ["S2"]} | [{"candidate_id": "S2", "selection_id": "camera1-reconstruction-0", "frame_id": 0}] |

Tradeoffs: S3 is better at segmenting the crowd but this does not matter because it's not the focus of the video.

### depth

[bound evidence](</home/auss/git_repos/samaust/Experiments_4DGS/docs/research/vipe-alternatives/plan067-execution/human-depth-review-001/import-result.json>)

Reviewer: samaust; 2026-09-30

historical component observation; not current metric-depth selection

| Criterion | Human observation | Preference | Named examples |
| --- | --- | --- | --- |
| frozen_frame | D0, D1, D3: they have a depth artifact on edge of close object. D4: does not have this artifact on edge of close object. This probably works better. However, the farthest objects like the crown are not captured or they have depth values difficult to see for the naked eye. | {"outcome": "preferred", "candidate_ids": ["D4"]} | [{"candidate_id": "D4", "selection_id": "camera1-selection-175", "frame_id": 175}] |
| motion | Motion is irrelevant for this test. | {"outcome": "not_applicable", "candidate_ids": []} | [] |
| artifacts | Artifacts are irrelevant for this test. | {"outcome": "not_applicable", "candidate_ids": []} | [] |
| sharpness | As mentionned in frozen_frame, D0, D1, D3 have something that looks like sharpness cranked too high that causes artifacts on the edge of clone objects. D4 is less sharp but looks much better. | {"outcome": "preferred", "candidate_ids": ["D4"]} | [{"candidate_id": "D4", "selection_id": "camera1-selection-175", "frame_id": 175}] |
| overall | Prefer D4 | {"outcome": "preferred", "candidate_ids": ["D4"]} | [{"candidate_id": "D4", "selection_id": "camera1-selection-175", "frame_id": 175}] |

Tradeoffs: D4 is less sharp but looks much better.

### supplemental_d2

[bound evidence](</home/auss/git_repos/samaust/Experiments_4DGS/docs/research/vipe-alternatives/plan067-execution/human-depth-followup-002/observation-confirmed.json>)

Reviewer: samaust; 2026-09-30

historical component observation; not current metric-depth selection

D2 also has an issue with the depth on edges of close objects and it's much worse than D0 and D1. D2 also has difficulty capturing a far player compared to the other methods.

Examples: [{"candidate_id": "D2", "selection_id": "camera1-selection-175", "frame_id": 175}]

## Extended depth generation dispositions

| Candidate | Disposition | Reason | Evidence |
| --- | --- | --- | --- |
| D0 | missing | extended package not provided |  |
| D1 | missing | extended package not provided |  |
| D2 | missing | extended package not provided |  |
| D3 | missing | extended package not provided |  |
| D4 | missing | extended package not provided |  |
| D5 | missing | extended package not provided |  |
| D6 | missing | extended package not provided |  |
| D7 | missing | extended package not provided |  |
| D8 | missing | extended package not provided |  |
| D9 | missing | extended package not provided |  |
| D10 | missing | extended package not provided |  |
| D11 | missing | extended package not provided |  |

Frozen eligible metric D*: not established

## Final renders: motion and neighbor effects

Missing actual five-arm matched final renders and their human review.


## Recursive issue completion snapshot

This saved snapshot does not close issues or prove current GitHub state.

Historical preparation references #4–17 are separate from the native child graph.
Unfinished historical preparation references: none

- #45: unfinished descendants #60, #61, #62
- #44: unfinished descendants #56, #57, #58, #59
- #23: unfinished descendants #34, #35, #45, #60, #61, #62
- #18: unfinished descendants #23, #34, #35, #44, #45, #56, #57, #58, #59, #60, #61, #62
