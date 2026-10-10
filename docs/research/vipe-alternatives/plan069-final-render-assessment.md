# Final qualitative assessment: motion and neighbor methods on 70k final renders (#35)

This closes the Plan 031/069 qualitative comparison (#18 → #23 → #34/#35). It
reports the final-render comparison of the motion (M) and neighbor (N) methods
and the reviewer's judgments. Results are research outputs under the
research-use licence decision of 2026-10-05; no commercial clearance is
claimed.

**Scope amendment (user, 2026-10-09).** The report does not re-cover the depth
candidates D0–D11, because the depth choice is already made and recorded.
Segmentation and depth were judged in the earlier isolated reviews (#33, #45).

## Fixed choices

- **Segmentation: S2.** See `plan067-execution/human-review-001/segmentation-decision.json`.
- **Depth: D8, MetricAnything Student PointMap.** Chosen 2026-10-05 in
  `reviews/plan069-depth-comparison-002/decision.json` (status `ready`).
  - D5, D6, D8 and D10 were the eligible metric candidates.
  - D8 was preferred for motion stability. The reviewer's reasons: less
    blurry and sharpest, no false floor depth at the painted logo, and low
    flicker behind transparent objects.
  - Accepted tradeoff: the ring is barely visible.

## Final-render comparison

There are five arms. Each shares S2 and D8, and each changes one method
relative to the baseline QF-B. Every arm was trained with the FreeTimeGS
`default_keyframe` preset for 70,000 steps.

- **Training data:** all 50 frames of the 30 training cameras, with repaired
  durations.
- **Rendering:** each model renders held-out cameras 0/10/20/30, which were
  never trained on, for frames 0–49 at 960×540.

| Arm | Motion mask (M) | Neighbor cameras (N) | Train time |
|---|---|---|---|
| QF-B (baseline) | M0: frame difference (t vs t+1) | N0: most shared feature tracks | 6,072 s |
| QF-M1 | M1: 9-frame median background | N0 | 6,072 s |
| QF-M2 | M2: MOG2 background subtraction | N0 | 5,382 s |
| QF-N1 | M0 | N1: highest Jaccard co-visibility | 6,600 s |
| QF-N2 | M0 | N2: greedy coverage/parallax | 5,897 s |

Evidence:

- Production request `plan069-final-render-review-006/production/request.json`
  (`plan069-final-render-D8-006`).
- Renders are under the run root, `final-render/plan069-final-render-D8-006/`.
- Review package `final-render/review-package-007/package.json` (sha256
  `db067b59…`).
- Human review `plan069-final-render-review-006/human-review-002.json`.
- Import record `review-import-002.json` (sha256 `9ab1b094…`).

## Human judgments (samaust, 2026-10-09)

**Motion: QF-B (M0) preferred.**

- M0 renders the fast-moving ball shape best. It is also best on the very thin
  black loop attached to the basket frame.
- M1 has the least blurry face but is missing some parts.
- M2's ball does not look circular.
- All three motion arms struggle with the green and white text on the game
  clock.
- The first note names camera 10, frame 3. The others are recorded without a
  camera or frame, as the reviewer accepted.

**Neighbors: QF-N1 (N1) preferred, a close match with N0.**

- Thin basket loop: N0 and N1 are very similar; N2 is worse.
- Player's ear: N0 and N1 show the ear close to the original; N2 is worse.
- N1 is slightly better than N0.

**Overall: QF-N1.** No tradeoffs were recorded.

**Practical reading.** M0 with N1 is the preferred combination.
- M0 is the baseline motion mask, and the alternatives brought no benefit.
- N1 is a marginal improvement over N0.
- N2 should be avoided.
- No arm renders the game-clock text well; this limit is shared by all arms.

## Pipeline findings that affect future training

1. **Crossing artifact fixed.** The documented repair is now the final-render
   default, `extended_final_render_contract.policies`:
   - all-times training keys;
   - duration target 0.2 with a 0.02 floor.

   Before the repair, frames 20–24 showed fragmented players, worst at
   frame 22. That was the known holdout/sentinel defect. After it, all arms
   are intact at frame 22.
2. **LPIPS history slowdown fixed.** torchmetrics 1.9.0's LPIPS metric clones
   its whole score history on every call. Each update got slower in
   proportion to the number of updates already done (0.09 → 0.29 s per
   update over 50k).
   - The fix resets the metric after each update; losses are unchanged.
   - A 70k training run now takes about 6,000 s instead of about 19,000 s.
   - Renders stay within run-to-run noise: 3.2/255 versus 7.3/255 between
     repeat runs.
3. **The 5k endpoint was too short to compare methods.** The 5k renders
   (review package 002) were blurry. The preset's 70k endpoint was needed.

Details: `docs/specs/plan031-execution/final-render-70k-endpoint.md`.

## Resources and attempts

Ledger head 1231:

| Resource | Used | Limit | Approval |
|---|---|---|---|
| GPU | 158,537 s | 288,000 s | user-approved raises 2026-10-07/08 |
| CPU preparation | 56,756 s | 66,000 s | |
| New artifacts | 343.8 GiB | 380 GiB | |

Completed runs (geometry, initializer, train, render):

- 5k production (`D8-002`) and its QUALIFY arm.
- 70k QUALIFY arms: 003 (original pipeline), 004 (crossing repair) and 005
  (LPIPS fix).
- 70k production `D8-006`: all five arms.

Failed or stopped attempts, all with cleanup confirmed in the ledger:

- QUALIFY 002 (14,400 s ceiling): timed out at update 60,074.
- Production `D8-004` QF-B: stopped at the user's request to add the crossing
  repair.

Refused admissions created no reservation. Their invocation files are under
`final-render/abandoned/`:

- a stale runtime inventory;
- live display memory exceeding the 21 GiB device allowance;
- host-library drift from unattended upgrades.

**Commits:** branch `plan069-depth-extension`, local only, from `2d8204c3`
(70k endpoint) to `2596708d` (review import).

## Limits

- The judgments are one reviewer's visual opinions, without statistical
  testing.
- Physical depth accuracy is unverified without independent metric
  references.
