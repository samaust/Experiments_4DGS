# Extended depth comparison: review handoff 001 (#59)

Status on 2026-10-05, branch `plan069-depth-extension`. This is a review handoff, not the formal
immutable #59 package: `depth_aggregate` correctly refuses to publish while the D6 slot has neither output
nor an authorized terminal disposition.

Private review page with synchronized clips: https://claude.ai/artifact/Umq48M8AYkXTT5x46VpDek

| Candidate | Model | Domain | Maps / clips | Fit → frozen check | Metric D* | GPU s | Outcome record |
|---|---|---|---|---|---|---|---|
| D2 | Depth Anything 3 Metric Large (control) | camera-z m | 200 / 4 | not recorded in outcome | listed eligible; confirm gate | 50.5 | `depth-D2-outcome-001.json` |
| D5 | MoGe-2 ViT-L | camera-z m | 256 / 4 | 1.5309 pass → pass | eligible | 129.6 | `depth-D5-outcome-001.json` |
| D6 | MoGe-3 ViT-L | camera-z m | not run | — | blocked (artifact budget) | 32.1 (qualification) | `depth-D6-maps-blocker-001.json` |
| D7 | Depth Anything V2 Metric Hypersim Small | camera-z m | 256 / 4 | 0.7052 pass → blocked | ineligible | 52.3 | `depth-D7-outcome-001.json` |
| D8 | MetricAnything Student PointMap | camera-z m | 256 / 4 | 1.4395 pass → pass | eligible | 111.7 | `depth-D8-outcome-001.json` |
| D9 | Video Depth Anything Small | relative inverse | 256 / 4 | not metric | visual only | 1747.7 | `depth-D9-outcome-001.json` |
| D10 | Metric Video Depth Anything Small | camera-z m | 256 / 4 | 0.8859 pass → pass | eligible | 1684.0 | `depth-D10-outcome-001.json` |
| D11 | Marigold V2 Log-stage2 | relative log | 256 / 4 | not metric | visual only | 361.9 | `depth-D11-outcome-001.json` |

D0–D4 remain historical references (60 anchor previews each). Physical accuracy is unverified for every
candidate. Clips use the fixed 0–20 m camera-z ramp (blue near → red far; magenta invalid; beyond 20 m
red) for metric arms and per-clip normalization for D9/D11.

## Decisions needed

1. **D6 maps.** D6 is runtime-qualified (driver qualification006, native qualification002, source019),
   but its single maps-001 allocation was refused before any reservation because the D6 whole-slot
   artifact budget, measured as run-wide growth since its setup grant (ledger 708), is about 1.28 GiB over
   after later candidates' outputs. Options: an artifact-cap amendment for the D6 slot; a reviewed change
   to attribution of later candidates' owned outputs; or a terminal disposition.
2. **Human review (#62 → #45).** Record a visual favourite and, separately, a metric D* from the eligible
   set, using the page and each candidate's `jobs/plan069-<D>-clips-001/package/viewer.html`.
