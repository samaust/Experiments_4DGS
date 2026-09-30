# Prospective QF CPU contract

This implements the request/result and read-only ledger admission seams from
`qualitative-final-render-review-proposal-001.md`. It establishes CPU contract
behavior; it does not qualify geometry, training or rendered results.

## Public interface

`scripts/vipe_benchmark/final_render_contract.py` exposes:

- `allocation_specs(prefix)`: 21 distinct prospective identities: geometry,
  initializer, train and render for five QF arms, plus one media/package identity.
- `parse_request(value) -> Request`: frozen typed allocations and a copied request.
- `validate_scope_bindings(bindings)`: binds actual scope to proposal 001 and
  its exact original S2/D4 human decisions by repository path, SHA256 and size.
- `admit_review(value, ledger, storage) -> ReviewAdmission`: validates a ledger
  snapshot without writing, reserving or executing jobs. Its
  `execution_authorized` is always false and blockers remain explicit.
- `initializer_arrays_hash(arrays)`: hashes names, shapes, dtypes and values.
- `normalization_matrix(normalization, actual=False)`: validates a finite affine
  4×4 transform with positive isotropic scale and proper rotation. Actual
  contracts require the full bound transform; translate/radius compatibility
  remains available only to explicitly labeled legacy CPU fixtures.
- `validate_initializer(request, arm, receipt, arrays)`: validates native arrays
  through the existing `basketball_dense_fusion.validate`, binds their hash,
  composition, prerequisite records, physical normalization, time and velocity
  units. It does not call or weaken historical `load_frozen`.
- `validate_worker_result(request, arm, phase, result)`: validates explicitly
  labeled CPU fixture outcomes only. Actual outcomes are rejected while the
  native adapter is absent. Training requires exactly 5,000 updates; render
  success requires every held-out camera/frame identity.

## Request and admission

Schema `plan067-final-render-request/v1` is REVIEW only. Both `actual` and
explicitly labeled `fixture` records are supported for admission testing.
The exact fixed five compositions and allocations come from the proposal:
S2/D4 throughout; M0/N0 reference, M1/N0, M2/N0, M0/N1 and M0/N2.
The request fixes seed 0, `default_keyframe`, its source pin, 5,000 equal updates,
5,000 samples per directed edge, three neighbors, all nine retained keyframes,
and 960×540/25 fps held-out cameras 0/10/20/30 at frames 0–49.

Verified `bindings` cover proposal, contract source, preset, installed runtime,
original allocation config, current CPU qualification, scene manifest, accepted
inputs, actual S2/D4 human decisions, S2, D4 fit/check, all M and all N results.
Actual admission validates the existing qualification wrapper against current
source hashes and reconstructs the connection to actual human submissions.
It first pins proposal 001 and the 8,484-byte S2 and 8,825-byte D4 decisions
named there. A changed choice, eligibility statement or proposal, including a
hash-valid replacement at another path, cannot revise this scope. A later
decision requires a new explicit proposal contract. Fixture bindings remain
flexible and clearly labeled.
Fixture evidence cannot be promoted to actual human or native completion.

Admission requires both native rows of every pair for all 30 training cameras,
matching accepted RGB hashes/intrinsics/grids, three eligible neighbors, and
passing frozen D4 fit/check coverage and scale. An exclusion that intersects
the frozen initialization coverage blocks admission. Duplicate, missing or
substituted native identities and neighbor memberships are rejected.

Fresh identities may not appear in any previous reserve, finish, accounting or
checkpoint record, even if previously blocked. Active allocations block
admission. All 49,500 GPU and 5,400 CPU prospective seconds must fit cumulative
budgets, alongside original setup/download/artifact limits, free disk and the
50 GiB incremental artifact ceiling. Device and worker ceilings remain 22 GiB
and eight. No retry, setup, download or model smoke allocation is introduced.

Initializer receipts include the request's initializer contract, exact arm and
composition, `arrays_sha256`, `scene_manifest`, and exact prerequisite result
records for S2, D4 fit/check and that arm's M/N. Native array shape/dtype,
finite values, static/invalid velocities, durations and allowed times retain
the audited validation rules. A finite transform declared in a request is not
evidence that its physical interpretation has been qualified.
Actual normalization is `{"transform": [[...], [...], [...], [...]]}` so the
accepted scene's off-diagonal rotation is preserved. If the bound scene manifest
contains normalization, its complete transform must match exactly; additional
scene metadata does not replace that matrix. Optional `voxel_basis` and
`voxel_basis_source` (`archive` and `receipt`) file records are verified and
bound through the complete initializer receipt; their scientific interpretation
belongs to the checked initializer adapter.

## Remaining blockers

The actual adapter still must produce and bind full native geometry, RoMa
edges, static/dynamic fusion and normalized initializer arrays. Existing
diagnostic subsets and trained checkpoints cannot be relabeled as QF artifacts.
Scene-manifest exclusion unions, camera/time calibration, physical normalization
and velocity conversion need an independently checked adapter receipt. A bound
manifest normalization, when present, must match the initializer contract.

Native source, binaries, preset resolution and installed compatibility need
qualification. Initializer counts, optimizer/checkpoint retention and peak
memory/storage must be measured without an unallocated model attempt. Supervised
native train and fresh reload/render adapters must define finite deadline
reserves, checkpoint publication and cleanup accounting. Exact prospective
authority and locked fresh-allocation registration/admission remain to be
implemented before any DO proposal can execute.

This contract intentionally keeps those blockers visible. Issue #34 and final
follow-up human review remain incomplete; no GPU job or live ledger mutation was
performed for this CPU milestone.
