# Plan 026 implementation validation

The dense pilot is scientifically rejected, as documented in
[pilot review](pilot-review.md). This does not invalidate the measured source
and geometry checks, and it does not establish a trained dense result.

The new initialization adapters preserve all historical Plan 024 source files.
They use training-only processed images, the accepted map's static-track overlap,
pinned ViPE masks/tracking, and pinned offline RoMa/EDGS geometry. Executed pilot
source copies remain beside their outputs. [Source audit](pilot-source-audit.json)
confirms the geometry helper matches the clean pinned EDGS checkout.

Targeted tests passed: three study split/provenance/supervisor tests, four
geometry/LK tests, one production crop-mapping test, four STG schedule/adapter
tests, and the two existing checkpoint tests for each backend. Tests cover
rejected cameras and adjacent frames, negative depth/nonfinite geometry,
incorrect correspondences, missing/disconnected support, local identity changes,
pixel-center mappings, physical/normalized velocity units, native optimizer
execution at 30,001, and unchanged final position learning rate after 30,000.

Both native backends resumed the verified seed-0 5,000 checkpoint. Saved state
immediately after restoration is bitwise identical to the parent, including
optimizer, RNG, method-specific state, and FreeTimeGS's sampler:
[STG restoration](stg-restore-validation.json),
[FreeTimeGS restoration](freetimegs-restore-validation.json).
The existing synthetic CPU next-update/relocation-state tests pass exactly.

GPU training is not bitwise repeatable. A two-update uninterrupted run and a
one-update/save/reload/one-update run differ numerically for both methods. The
strict endpoint comparisons are retained as failed checks:
[STG](stg-resume-validation.json), [FreeTimeGS](freetimegs-resume-validation.json).
Independent uninterrupted repeats show differences of a similar scale, while
restored state is exact. This supports native numerical variability, rather than
demonstrating state loss. No tolerance was invented to relabel the bitwise checks
as passed. See [STG repeat differences](stg-numerical-repeat.json) and
[FreeTimeGS repeat differences](freetimegs-numerical-repeat.json); FreeTimeGS's
actual sample sequence and endpoint RNG/sampler state are identical.

The continued 5,002 checkpoints were rendered in fresh processes over all 350
targets and repeated at the 13 required camera/time probes. Both raw-float and
PNG hashes match on every repeat:
[STG reload](stg-reload-validation.json),
[FreeTimeGS reload](free-reload-validation.json).

[Baseline reuse verification](baseline-reuse.json) checks all six historical
checkpoint hashes, all 2,100 historical render/target pairs, all 350 masks, and
finite/complete metric coverage before allowing 5,000-update reuse. The final
Plan 024 protocol is `evaluation-protocol-v3.json`, hash
`cc247ce12b119993daae16cc346d07c23cbccbfcf048ae31ef72b80efd7faa3d`.
Earlier protocol revisions are retained history and have different renderer
hashes. V3 and the actually executed historical render/metric hashes match the
current untouched sources.

The runner accepts absolute target updates and retains native schedule settings.
Intermediate curve files contain complete renderable models plus extra training
state, and are labeled separately from required resumable endpoints. Recovery
saves occur every 1,000 updates or five minutes. Atomic replacement preserves
the previous recovery until the new state is validated; only superseded study
recoveries are removed. Pre-save disk checks reserve both generations.

[Storage projection](storage-001.json) reserves about 28 GiB for the six sparse
trajectories and their evaluation/visual artifacts. This is a resource estimate,
not a new point-count or quality constraint. Production results, their complete
curve reloads and evaluations, and the final report remain outstanding.
