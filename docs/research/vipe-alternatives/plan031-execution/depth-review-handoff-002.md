# Extended depth comparison: review handoff 002 (#59)

Status on 2026-10-05, branch `plan069-depth-extension`. This supersedes handoff 001. The formal immutable
#59 package is published: `jobs/plan069-depth-comparison-002` (`package.json`, `viewer.html`), readiness
`ready-for-human-review`. All twelve D0–D11 slots are available; none needed a terminal disposition.
Record: `depth-comparison-package-002.json`.

Private review page with synchronized clips (now including D6): https://claude.ai/artifact/Umq48M8AYkXTT5x46VpDek

| Candidate | Model | Domain | Maps / clips | Fit → frozen check | Metric D* | GPU s | Outcome record |
|---|---|---|---|---|---|---|---|
| D2 | Depth Anything 3 Metric Large (control) | camera-z m | 200 / 4 | historical anchors | control | 50.5 | `depth-D2-outcome-001.json` |
| D5 | MoGe-2 ViT-L | camera-z m | 256 / 4 | 1.5309 pass → pass | eligible | 129.6 | `depth-D5-outcome-001.json` |
| D6 | MoGe-3 ViT-L | camera-z m | 256 / 4 | 1.5350 pass → pass | eligible | 223.6 | `depth-D6-outcome-001.json` |
| D7 | Depth Anything V2 Metric Hypersim Small | camera-z m | 256 / 4 | 0.7052 pass → blocked | ineligible | 52.3 | `depth-D7-outcome-001.json` |
| D8 | MetricAnything Student PointMap | camera-z m | 256 / 4 | 1.4395 pass → pass | eligible | 111.7 | `depth-D8-outcome-001.json` |
| D9 | Video Depth Anything Small | relative inverse | 256 / 4 | not metric | visual only | 1747.7 | `depth-D9-outcome-001.json` |
| D10 | Metric Video Depth Anything Small | camera-z m | 256 / 4 | 0.8859 pass → pass | eligible | 1684.0 | `depth-D10-outcome-001.json` |
| D11 | Marigold V2 Log-stage2 | relative log | 256 / 4 | not metric | visual only | 361.9 | `depth-D11-outcome-001.json` |

D0–D4 remain historical references (60 anchor previews each). Physical accuracy is unverified for every
candidate. Package viewer: 60 matched frozen-frame selections (30 cameras × frames 100/175) and four
synchronized 50-frame clips (cameras 1/11/21/31, frames 150–199, 25 fps). Metric arms share the fixed
0–20 m camera-z ramp (invalid magenta, beyond 20 m red); D9/D11 are normalized per clip.

## How D6 got here

maps-001 failed in its worker at the first sparse-UNet Triton compile: flex_gemm 1.0.0 needs `dtype.itemsize`,
absent in the accepted Triton 3.2.0 (`depth-D6-maps-outcome-001.json`). The approved runtime replacement
`plan069-D6-setup-recovery-002` reused the accepted source, checkpoint and FlexGEMM derivation and provisioned
torch 2.14.1+cu130 / Triton 3.8.0 offline (zero transfers). Requalification: 009 failed cleanly before CUDA
(cached-wheel install left no owned FlexGEMM cache directory; fixed), 010 passed, 011 rebound the closure
with the approved maps retry. Commercial assessment 005/006 rechecked the new dependency closure
(independent licence delta review: NVIDIA texts byte-identical, new packages permissive). maps-002 then
completed 256 maps with both scale gates passing.

## Decision needed

**Human review (#62 → #45).** Record a visual favourite and, separately, a metric D* from the eligible set
(D5, D6, D8, D10), using the package viewer or the review page. Ties, "unclear" and "not applicable" are valid.
