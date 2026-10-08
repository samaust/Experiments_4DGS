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
  14,400 s at 70k. The 5k runs measured 0.125–0.15 s per update, so 70k needs
  about 8,750–10,500 s. `allocation_specs(identity, iterations)` writes the
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
  The 14,400 s ceiling is the protection against slow runs.

## Budget: cap extension v2

`plan069-final-render-cap-amendment/v2`
(`final-render-cap-amendment-review-002.json`) chains onto the exact v1
extension and the 110/210 base amendment. It sets:

| Cap | Before | After |
|---|---|---|
| Cumulative new artifacts | 260 GiB | 380 GiB |
| Cumulative GPU | 93,600 s | 172,800 s |

The pinned user authorization is `final-render-cap-approval-002.json`.

- **Artifacts.** 250.9 GiB were in use at ledger head 1103, and each arm retains
  about 11.6 GiB. The last of six arms (QUALIFY plus five production arms)
  reserves at about 309 GiB + 12 GiB = 321 GiB. That leaves about 59 GiB for
  leftovers from failed attempts. The disk had 442 GiB free.
- **GPU.** 37,181 GPU-s were used. Admission counts each request's whole
  ceiling (5 × 20,700 s = 103,500 s). Production DO admission after a QUALIFY
  arm therefore counts at most 37,181 + 20,700 + 103,500 = 161,381 s. The
  expected actual spend is about 78,000 s.

## Requests

Review folder `plan069-final-render-review-003`:

- production `plan069-final-render-D8-003`;
- QUALIFY `plan069-final-render-D8-qualification-002`.

They reuse review-002's scene freeze and voxel basis. The authority scripts are
in `plan069-final-render-authority-002`.
