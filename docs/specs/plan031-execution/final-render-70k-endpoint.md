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
