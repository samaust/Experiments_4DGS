# Independent annotation handoff (#30)

This handoff is ready for external human work. **No independently reviewed human bundle has been supplied.** The JSON template is incomplete engineering material, not annotations or evidence of performed review. Synthetic test fixtures have no scientific status. Importing actual reviewed truth belongs to #31; #22 remains incomplete until that import succeeds.

## Frozen inputs and membership

[annotation-template.json](annotation-template.json) carries the exact accepted image records and source input-manifest record. Its manifest SHA-256 is `8bffd5ee620860dff0ded5bc5a5b70d1e424a5bc88d2bd8e937e70a94163466b` (11,597,582 bytes). File paths identify the existing accepted local files; transferring the handoff requires transferring those files without changing their bytes and rebuilding path-bearing file records consistently. Do not substitute new images, grids, intrinsics, validity masks, SIFT locations or annotation selection.

- 48 calibration images: cameras 0, 1, 10, 11, 20, 21, 30, 31; frames 50, 100, 149 (fit) and 150, 175, 199 (selection).
- 184 reconstruction images: cameras 1, 6, 11, 16, 21, 26, 31, 33; distinct endpoints of starts 0, 5, 10, 15, 20, 21, 22, 23, 24, 25, 30, 35, 40, 45. All lie in reconstruction frames 0–49.
- 112 reconstruction pair records, one per camera/start, including births and disappearances.
- 768 fixed calibration static-feature locations, each requiring review.

Keep all 232 image identities exactly once. The optional template `role` labels explain membership; the validator derives membership from identities and the frozen configuration. Preserve the original model-assisted proxy bundle and its review/policy history separately.

## Human work and evidence required

1. Assign actual external primary and independent-review contributors with distinct identities. Supply each contributor's `id`, `kind: external_human` and hashed `attestation` file record. Attestations should identify the contributor, assignment, independently performed human work, revision(s), date and blind-review conditions. File validation checks hashes and declared identities; it cannot establish honesty of human attestations.
2. The primary annotator labels every image. Retain their immutable `primary_revision` record (an archived revision with a verifiable path, SHA-256 and byte count). Do not derive player roles from candidate person labels. Include negative images and absent balls; do not hallucinate fully occluded objects.
3. The independent reviewer reviews every RGB image and primary annotation, blinded to candidate outputs, method identities and scores. Keep a separate immutable review record for every image. Its JSON must bind `reviewer_id`, `primary_revision_sha256`, and `blind_to_outputs_methods_scores: true`. Set bundle `blinded_to_candidate_outputs: true` only after actual blind review.
4. Adjudicate every disagreement and retain both primary and review evidence. Each immutable adjudication JSON binds `review_sha256` and `final_layers_sha256` and records `unresolved_disagreements: 0`. Retain the adjudicator's identity and decisions in that record. Every completed image has `status: reviewed-adjudicated`.
5. Freeze final layers, metadata, tags, reviewed features and temporal associations. Retain contributor person-hours under the separate caps: primary 72, independent review 24, adjudication 8, static-feature review 8. Stop incomplete if a cap is exhausted; never transfer hours between scopes or shrink membership.

A file record consists of `path`, `sha256` and `bytes`, generated from actual immutable bytes. A content hash alone cannot replace the underlying evidence file. Do not edit a file after its record is frozen. Avoid giving the blind reviewer the proxy annotations or benchmark candidate evidence.

## Layer and metadata contract

For each image, `final_layers` references a numeric, non-pickled NPZ archive:

| Layer | Type and shape | Meaning |
| --- | --- | --- |
| `instances` | int32, 540×960 | 0 for background; positive image-local IDs for visible instances; −1 outside the valid footprint |
| `changing` | bool, 540×960 | Independently judged changing background; may overlap semantics |
| `valid` | bool, 540×960 | Exact accepted valid footprint |
| `ignored` | bool, 540×960 | Uncertain/ignored boundary pixels |

`instances` metadata has exactly the string IDs of positive labels present in the mask. Each instance records `class` (`person` or `basketball`), `visibility`, `occlusion`, `blur`, `tiny_ball`, and `role_uncertain`. Persons additionally record independently judged `role` (`player`, `other-person`, or `uncertain`). Record visible surfaces only. Image `tags` declare stationary people, spectators, shadows, changing displays, illumination changes and uncertain motion using the template's required tag names. Usable static truth is derived from these layers by the frozen scoring protocol; do not supply model-predicted static masks as human truth.

For each static-feature location retain its frozen `index`, and record `suitable` as `true`, `false`, or `uncertain`, in the same order as the supplied locations. Empty lists are valid only for images with no selected locations.

For each pair, supply `associations` records with `first_id` and `second_id`. Every visible positive instance ID in each endpoint appears exactly once. Use null for a birth's first ID or a disappearance's second ID; both IDs cannot be null. Pair-local identity, not guessed model tracks, determines continuity.

## Validation and import

The public `vipe_benchmark.annotations.validate(bundle, inputs, config)` boundary checks the full bundle without ledger mutations. The `annotations` controller performs this preflight before writing a worker request or reserving CPU; its worker repeats validation against hash-verified request records and publishes to a fresh directory exclusively. Invalid evidence cannot publish qualified truth. A rejected preflight leaves existing proxy bytes and ledger events intact.

The human schema is `vipe-benchmark-annotations/v1`. A proxy schema, `human_ground_truth: false`, or a non-human `evidence_kind` is rejected even if copied human fields are supplied. Existing human bundles may omit the latter two optional fields; if supplied they must be `true` and `reviewed-human` respectively. Structural validation does not prove human authorship or independence; the actual contributors' evidence remains required.

**Before #31 can import:** supply the entire external bundle and its referenced files; validate frozen records and zero unresolved disagreements; check live authorization, ledger and CPU headroom; use a reviewed, explicitly authorized fresh import allocation/identity if the original import account was consumed. Current historical output cannot be overwritten and original allocations cannot be reset. This handoff creates no new allocation and makes no claim that an import has occurred. A consumed account or occupied output remains a blocker until the applicable recovery is authorized and implemented.

Reviewed segmentation/identity truth does not constitute independently measured metric-depth reference data. Physical depth accuracy remains unverified without separate reference evidence.

## Engineering validation

The CPU annotation tests cover all 232 synthetic fixture identities through the validator and worker contract, import success into a fresh directory, refusal to overwrite, proxy substitution, contributor/review failures, changed revision hashes, malformed layers, substituted/duplicate images, unresolved adjudication and invalid associations. These are engineering checks only; they cannot satisfy #31's human evidence requirement.
