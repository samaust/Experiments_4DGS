# D1 acquired-asset license review

Independent review by Codex subagent `/root/geometry_scoring`, 2026-09-13.
Scope: only the two D1 asset subjects in the frozen E4 `assets-before-build.json`.
No installed E4 dependency inventory or whole-environment conclusion is included.

| Asset | Commercial permission | Non-AGPL open-source preference | Evidence |
| --- | --- | --- | --- |
| UniDepth source, `8d8cfe4c7ee15297099983607febf0d4f32eb3d6` | restricted | restricted | Exact LICENSE is CC BY-NC 4.0; README:293 and pyproject:14 explicitly apply it to the software. |
| UniDepth snapshot, `52b349b514bd8b47642f67ac78cb7b5dc5c51dd9` | unverified | unverified | Bound files are config and weights only; no model card or license grant is recorded. Config has no license declaration. |

The source restriction is not an AGPL finding. Its software license and model
repository link do not establish a separately recorded checkpoint grant. The
snapshot subject hash exactly matches the earlier D0 asset review; that
uncertainty is preserved. No model payload was read or deserialized.

[Per-asset findings](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/license-review-E4-assets-20260913T065749Z/asset-review.json),
[exact subjects](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/license-review-E4-assets-20260913T065749Z/asset-subjects.json),
[validation](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/license-review-E4-assets-20260913T065749Z/validation.json),
and [timing receipt](../../../../.local/vipe-alternatives/plan031-20260913T032700Z/license-review-E4-assets-20260913T065749Z/receipt.json)
are separate immutable local artifacts. Reuse entries only after exact asset
subject-hash comparison against the eventual qualification; installed packages
require their own review. This partial review must not be registered as a
whole-environment `license_assessment`.

No network, model/package imports beyond the Python standard library, builds,
mutable setup files, source edits, git, or ledger writes were used. No readiness
waits or idle periods occurred. Start/end and actual active preparation time are
recorded in the receipt within the 600-second cap. No research eligibility or
scientific criterion is changed.
