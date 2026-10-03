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

## Execution and resource accounting

[bound evidence](</home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/review-downstream/docs/research/vipe-alternatives/plan069-review-downstream-001/assessment-001/accounting.json>)

Preserved ledger events: 619

| Attempt | Status | Consumed seconds | Cleanup |
| --- | --- | --- | --- |
| prepare | complete | 97.46733420493547 | True |
| annotations | complete | 2494.941006432986 | True |
| S0-calibration | complete | 266.00154498091433 | True |
| S0-reconstruction | complete | 240.48724780103657 | True |
| E1-setup | failed | 207.02063947997522 | True |
| E2-setup | failed | 767.6898049139418 | True |
| E3-setup | failed | 13.575414187973365 | True |
| E4-setup | failed | 2111.6620846109 | True |
| E3-setup-recovery-001 | complete | 362.38790283200797 | True |
| S3-calibration | complete | 129.21695817192085 | True |
| S3-reconstruction | failed | 11.236293156049214 | True |
| E1-setup-recovery-001 | failed | 255.64516464597546 | True |
| E1-setup-recovery-002 | complete | 442.6764838210074 | True |
| S3-reconstruction-recovery-001 | failed | 17.42091836396139 | True |
| S3-reconstruction-recovery-002 | failed | 124.82932935503777 | True |
| S3-memory-diagnostic-001 | complete | 163.13565481896512 | True |
| S3-reconstruction-recovery-003 | complete | 894.1075741910608 | True |
| E2-setup-recovery-001 | complete | 534.6751473740442 | True |
| E4-setup-recovery-001 | failed | 46.91368926002178 | True |
| S1-calibration | failed | 10.414188402937725 | True |
| S1-reconstruction | failed | 10.50047472200822 | True |
| S2-calibration | complete | 142.85742373997346 | True |
| S2-reconstruction | failed | 328.0620006190147 | True |
| S2-reconstruction-recovery-001 | complete | 334.396597760031 | True |
| S4-calibration | complete | 92.42379428597633 | True |
| S4-reconstruction | complete | 299.08294111897703 | True |
| M0 | complete | 24.822598707978614 | True |
| M1 | complete | 146.89640237600543 | True |
| M2 | complete | 82.79561714397278 | True |
| D0-fit | complete | 26.7861759129446 | True |
| D0-check | complete | 26.754226593999192 | True |
| N0 | complete | 12.020007696934044 | True |
| N1 | complete | 11.946572346962057 | True |
| N2 | complete | 12.130935690016486 | True |
| G-S0 | complete | 85.65207107609604 | True |
| R-G | complete | 27.902456604999315 | True |
| G-S2 | complete | 104.74721343499914 | True |
| G-S3 | complete | 103.32175846800055 | True |
| G-S4 | complete | 102.56877443799931 | True |
| G-M1 | complete | 102.5580591830003 | True |
| G-M2 | complete | 86.59422262099906 | True |
| G-N1 | complete | 100.82974762900085 | True |
| G-N2 | complete | 86.76845011499972 | True |
| C0 | complete | 396.7501372539991 | True |
| aggregate | complete | 12.544028549000359 | True |
| report | complete | 12.679579571999056 | True |
| E4-setup-recovery-002 | failed | 57.08332331299971 | True |
| E4-setup-recovery-003 | failed | 56.50527517199953 | True |
| E4-setup-recovery-004 | failed | 56.68333473900202 | True |
| E4-setup-recovery-005 | failed | 181.6153566130015 | True |
| E4-setup-recovery-006 | complete | 119.03856650500165 | True |
| D1-fit | complete | 22.853101759999845 | True |
| R-D | complete | 12.989089495997177 | True |
| D1-check | complete | 22.795839387999877 | True |
| S1-calibration-recovery-001 | failed | 2.6926045369764324 | True |
| S1-calibration-recovery-002 | failed | 10.94492926300154 | True |
| S1-calibration-recovery-003 | failed | 25.151324003003538 | True |
| S1-calibration-recovery-004 | failed | 1.0312923620222136 | True |
| E5-setup | failed | 109.46603674103972 | True |
| E6-setup | complete | 243.26923660101602 | True |
| E7-setup | complete | 73.4239962240099 | True |
| D3-fit | complete | 31.57062723999843 | True |
| D4-fit | complete | 48.2911062950152 | True |
| D3-check | complete | 28.831890020985156 | True |
| D4-check | complete | 48.533290898951236 | True |
| E5-setup-recovery-001 | failed | 74.80530964198988 | True |
| S1-calibration-recovery-005 | failed | 29.81751602998702 | True |
| E5-setup-recovery-002 | failed | 78.96719443995971 | True |
| S1-calibration-recovery-006 | failed | 35.018222475016955 | True |
| E5-setup-recovery-003 | failed | 75.79275078198407 | True |
| S1-calibration-recovery-007 | failed | 2024.6900698940153 | True |
| E5-setup-recovery-004 | complete | 83.50995497504482 | True |
| S1-calibration-recovery-008 | failed | 36.640664215025026 | True |
| D2-fit | complete | 18.50741288298741 | True |
| D2-check | complete | 14.601953361008782 | True |
| S1-calibration-recovery-009 | failed | 2209.4980646440526 | True |
| S1-calibration-recovery-010 | failed | 2201.8423373190453 | True |
| S1-calibration-recovery-011 | failed | 977.9256893300335 | True |
| S1-calibration-recovery-012 | complete | 2195.634838166996 | True |
| plan069-D7-setup-001 | complete | 22.228227209998295 | True |
| plan069-D7-maps-001 | complete | 52.25842975500018 | True |

Resource observation: [bound evidence](</home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/review-downstream/docs/research/vipe-alternatives/plan069-review-downstream-001/assessment-001/resource-observation.json>)

Budget authorization: [bound evidence](</home/auss/git_repos/samaust/Experiments_4DGS/.local/plan069-worktrees/review-downstream/docs/research/vipe-alternatives/plan031-execution/depth-approval-001.json>)

## Recursive issue completion snapshot

This saved snapshot does not close issues or prove current GitHub state.

Historical preparation references #4–17 are separate from the native child graph.
Unfinished historical preparation references: none

- #45: unfinished descendants #60, #61, #62
- #44: unfinished descendants #56, #57, #58, #59
- #23: unfinished descendants #34, #35, #45, #60, #61, #62
- #18: unfinished descendants #23, #34, #35, #44, #45, #56, #57, #58, #59, #60, #61, #62
