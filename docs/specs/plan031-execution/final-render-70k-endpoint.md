# Final renders at the 70,000-step endpoint (#34)

The five 5,000-step D8 final renders (review package 002) were too blurry to
compare. The FreeTimeGS `default_keyframe` preset is built for 70,000 steps:
`max_steps`, the learning-rate schedules, relocation until 63k (0.9 × max_steps) and pruning until
20k. On 2026-10-07 the user chose to retrain all five arms to 70k, one at a time.

## Endpoint

- `extended_final_render_contract.parse_request` accepts `iterations` of 5,000
  or 70,000 (`final_render_contract.ENDPOINTS`). Every other setting is
  unchanged, and the five arms still share one endpoint.
- The train-phase GPU ceiling follows the endpoint: 3,600 s at 5k and
  25,200 s at 70k. Updates slow down as training proceeds. The 5k runs measured
  0.14 s per update, but the first 70k QUALIFY attempt averaged 0.237 s over
  60,074 updates and hit the original 14,400 s ceiling. A linear slowdown puts a
  full 70k run at about 17,700 s. `allocation_specs(identity, iterations)` writes the
  ceiling into the allocations. Workers, result validators and the reserve gate
  read it through `phase_seconds(request, phase)`.
- Workers train for `request['iterations']` updates and publish
  `checkpoint-070000.pt`. Render reloads that endpoint, and the native runtime
  renders with the SH degree reached at that endpoint.
- Geometry and initializer run again for each arm (about 2,150 s per arm).
  Reusing the 5k request's initializers would need a cross-request lineage
  seam. That seam doesn't exist, and the rerun costs about 12% of the GPU time.
- No resume checkpoint. The publication chain has no seam that can resume a
  consumed allocation, so a failed train phase needs a new request either way.
  The train ceiling is the protection against slow runs.

## Budget: cap extension v2

`plan069-final-render-cap-amendment/v2`
(`final-render-cap-amendment-review-002.json`) chains onto the exact v1
extension and the 110/210 base amendment. It sets:

| Cap | Before | After |
|---|---|---|
| Cumulative new artifacts | 260 GiB | 380 GiB |
| Cumulative GPU | 93,600 s | 252,000 s |

The pinned user authorization is `final-render-cap-approval-003.json`
(2026-10-08). It supersedes `-002`, whose 172,800 s limit was sized for the
14,400 s train ceiling.

- **Artifacts.** 250.9 GiB were in use at ledger head 1103, and each arm retains
  about 11.6 GiB. The last of six arms (QUALIFY plus five production arms)
  reserves at about 309 GiB + 12 GiB = 321 GiB. That leaves about 59 GiB for
  leftovers from failed attempts. The disk had 442 GiB free.
- **GPU.** After the timed-out QUALIFY attempt, 53,470 GPU-s were used.
  Admission counts each request's whole ceiling (5 × 31,500 s = 157,500 s).
  Production DO admission after a QUALIFY arm therefore counts at most about
  85,000 + 157,500 = 242,500 s. The expected actual total is about 177,000 s.

## Requests

Review folder `plan069-final-render-review-004`:

- production `plan069-final-render-D8-004`;
- QUALIFY `plan069-final-render-D8-qualification-003`.

They reuse review-002's scene freeze and voxel basis. They use a 20 GiB device
limit, which leaves 2 GiB for desktop display memory, and runtime inventory
`plan069-final-render-runtime-002`. The authority scripts are in
`plan069-final-render-authority-003`.

## Attempt history

- Review-003 (14,400 s ceiling): the first two QUALIFY envelopes were refused
  before reservation. The runtime inventory still pinned the 5k native source,
  and desktop display memory exceeded the 21 GiB limit's 1 GiB allowance.
- QUALIFY envelope `authority-002/qualify-20261008T014510Z`: geometry took
  2,006 s and the initializer 176 s. Training stopped at its deadline reserve
  after 60,074 updates and 14,250 s (ledger 1115; cleanup confirmed; no
  checkpoint).

## Crossing repair (2026-10-08)

The 70k QUALIFY render (review-004) reproduced the known crossing artifact:
ghosted, fragmented players at frames 20–24, worst at frame 22
(`docs/experiments/basketball-dense-training/crossing-investigation-001`). The
final-render runtime still used the two documented causes:

- **Holdout training keys.** Frames 20–24 had no training observation in any
  camera.
- **The unrepaired `init_duration = -1` sentinel.** It reached the duration
  penalty and pushed temporal widths toward zero.

The user stopped production (QF-B train ended failed, cleanly, at ledger 1141)
and chose to rerun with the documented repair
(`docs/multicamera-freetimegs-workflow.md`, step 5.5):

- Requests may carry `training_policy: all-times` and `lifetime_policy:
  repaired`. Since 2026-10-09 these are the defaults
  (`extended_final_render_contract.policies`): an omitted field means the
  repaired value, and no other value is accepted. Requests 001–004 ran before
  the repair, with the holdout keys and the unrepaired sentinel. Requests 005
  and 006 set both fields explicitly.
- `final_render_native.training_keys` then uses all 50 frames of the 30
  training cameras (1,500 keys). Held-out cameras stay excluded.
- `duration_target` resolves the frozen initializer's uniform 0.2 width.
  `cfg.init_duration` is set to that width after the frozen-recipe check.
  `basketball_crossing_repair.project_duration_parameter_` (0.02 floor) runs
  once before training and after every update.
- Runtime inventory `plan069-final-render-runtime-003` pins the repair source.

Frames 20–24 are no longer an unseen time interval. Held-out cameras 0, 10, 20
and 30 remain the evaluation views.

The crossing study measured 0.128–0.129 s/update both with and without the
repair, so the 25,200 s train ceiling stands. In a single process, updates slow
from about 0.11 to 0.30 s between 5k and 50k. A fresh process resumed at 50k
runs at 0.128 s, so the slowdown builds up within the process rather than
coming from the model state. It is not yet diagnosed.

Requests: `plan069-final-render-review-005`, with production
`plan069-final-render-D8-005` and QUALIFY
`plan069-final-render-D8-qualification-004`. Authority:
`plan069-final-render-authority-004`. Caps: v2 amendment `-review-004` (GPU
288,000 s, CPU preparation 66,000 s, artifacts 380 GiB) with pinned approval
`final-render-cap-approval-004.json`.

## Crossing repair result and LPIPS history fix (2026-10-09)

The repaired QUALIFY arm (`qualification-004`, authority-004) completed:
geometry 1,991 s, initializer 177 s, train 19,005 s, render 306 s. At frame 22
its players are sharp and intact. Frame 20–24 temporal roughness (mean
absolute deviation from the neighbor average) matches the rest of the clip on
all four held-out cameras: 1.07–1.23 vs 1.09–1.24 elsewhere. The unrepaired
arm had dropped to 0.97–1.08 inside the gap.

The slowdown has a single cause. torchmetrics 1.9.0's LPIPS metric object
appends every score to its `all_scores` list state. Each forward call clones
the whole list (`_copy_state_dict`). That adds about 4.6 µs per past update to
every update, a perfectly linear 0.09 → 0.29 s/update ramp in all six 0→50k
dense runs. A CPU micro-benchmark gave 6.1 / 15.7 / 47.5 / 113.6 ms per call at
0 / 5k / 20k / 50k stored scores, and 9.6 ms with a reset after each call.
`NativeFreeTimeRuntime.training_step` now resets the metric after every update.
Losses use only the current batch, so they are unchanged. The 70k train
ceiling returns to 14,400 s; the expected train time is about 9,300 s.
Runtime inventory `plan069-final-render-runtime-004`. Requests
`plan069-final-render-review-006` (production `plan069-final-render-D8-006`,
QUALIFY `plan069-final-render-D8-qualification-005`), authority
`plan069-final-render-authority-005`.
