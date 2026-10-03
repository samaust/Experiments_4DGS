# Extended metric-depth downstream REVIEW contract

Issue #61 supplies `scripts/vipe_benchmark/extended_final_render_contract.py`.
Historical `plan067-final-render-request/v1`, its S2/D4 proposal and validators
retain their original behavior.

## Public boundaries

- `compositions(candidate)` returns the five fixed S2 arms with a single eligible
  metric D*: D2, D5, D6, D7, D8 or D10.
- `parse_request(request)` validates `plan069-final-render-request/v1` in REVIEW
  mode, exact immutable prerequisites and the real #60 decision validator.
- `admit_review(request, ledger, storage)` checks the ledger snapshot and
  cumulative budgets without modifying it. `execution_authorized` is false.
- `validate_scene_bindings(request)` checks the accepted processed manifest,
  exclusion union, exact passing fit/check, full positive isotropic similarity,
  camera calibration, physical scale, frame/50 time and two-second velocity map.
- `validate_initializer(request, arm, receipt, arrays)` checks the unchanged
  dense-fusion array seam and exact selected-depth provenance for reuse by #34.

## Immutable request

The request retains the original five arm names, seed 0, 5,000 iterations,
`default_keyframe` preset pin, nine keyframe pairs, 5,000 samples per edge, three
neighbors, and 200 held-out render frames at 960×540 and 25 fps. Its allocations
use the existing finite per-phase ceilings and a fresh identity prefix. REVIEW
passes establish consistency, never execution authority.

Required bindings are `proposal`, `source`, `preset`, `runtime`, `config`,
`qualification`, `scene_manifest`, `scene_freeze`, `inputs`,
`segmentation_decision`, `depth_decision`, `S2`, `D_fit`, `D_check`, `M0`, `M1`,
`M2`, `N0`, `N1`, `N2`. Every binding is an exact path/hash/size file record.
`D_fit` and `D_check` must equal #60's independently reconstructed eligibility
scale records, and `inputs` must equal its accepted scale-input manifest.

The separately published proposal is JSON with schema
`plan069-final-render-review-proposal/v1`, matching `record_kind`, `mode: REVIEW`,
`depth_candidate`, the exact request bindings excluding `proposal`, and
`settings_sha256 = object_hash(request excluding bindings)`. Publish it once;
changed inputs, choices or settings require a new proposal identity.

The initializer schema is `plan069-final-render-initializer/v1` with the full
normalization `transform`, `time_formula: frame/50` and
`velocity_units: normalized-scene/normalized-time`. An initializer receipt adds
its `arm`, exact `composition`, `arrays_sha256`, `scene_manifest`, and
`prerequisites`: S2, D_fit, D_check, depth_decision and that arm's M/N results.
Optional voxel basis files require complete immutable archive/receipt lineage.

The scene freeze uses `plan069-final-render-scene/v1`, status complete,
`depth_component: D*`, exact `scale_evidence: {fit, check}`, passing scale,
normalization, accepted `historical_reference`, map, exactly 30 training cameras,
and units from the existing diagnostic scene contract. The physical camera
rescaling must preserve historical normalized coordinates including rotation.

Actual requests require the frozen actual S2 decision, current CPU qualification
and this module's current source record. Fixture requests exercise real #60
import, freeze and validation with explicitly synthetic CPU evidence; they are
rejected when promoted to actual mode.

## Remaining execution work

#34 owns native geometry, initializer production, supervision, training,
rendering, qualification and actual final-render human review. #35 owns reporting.
A real #45 depth decision and separately approved DO admission remain necessary
for native work. This module performs no setup, download, GPU use or ledger write.

## Approved cumulative budget amendment

Historical `bindings.config` remains the original 60 GiB download / 150 GiB
artifact configuration used by S2, M/N results and qualification. To review
against the approved 110/210 ledger limits, supply request `budget_amendment`
with exact `amendment` and `authorization` file records. The proposal settings
hash binds these records.

`validate_budget_configuration(request, ledger.config)` accepts only
`plan069-depth-cap-amendment/v1` with status REVIEW, the historical configuration
hash/size and exactly 110/210 caps. Its authorization must have the recorded
`plan069-depth-user-authorization/v1` DO status, exact amendment record and
approved `plan069-depth-cap-approval/v1` object hash. Actual mode pins the
existing immutable user authorization bytes; fixture authorization must be
labeled fixture. No other ledger configuration field may differ. Missing
approval, changed amendment, configuration drift or forged actual authorization
is rejected. These approved resource caps grant no downstream DO authority.
