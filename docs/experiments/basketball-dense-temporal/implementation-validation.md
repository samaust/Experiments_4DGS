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
not a new point-count or quality constraint. Production results, curve reloads, evaluations, and the final report are now
complete for all six available sparse trajectories; the dense arm remains blocked.

The existing camera/timing/sampler/normalization suite also passed 21 tests in
the pinned CPU container. A first attempt in the RoMa environment could not
import pytest; no training environment was changed. The native normalization
projection/motion-invariance test passed separately in the RoMa environment.
Two matched-block reporting tests pass, including missing seed/block rejection.

Actual production evidence now supplements the optimizer-guard fixture:
[the 35,000 recovery](stg-production-post30000.json) has changed positions and
optimizer counters above 30,000. No schedule configuration was changed.

The baseline visual export contains 12 videos, each verified as exactly 50
frames at 25 fps. Fixed court/display/player crops use ground-truth-selected
rectangles in [visual protocol](visual-protocol.json). The retained first export
had overlapping crop headers; `visuals-005000-v2/` corrects only those labels.
Neither version interpolates source frames. Large exports stay under the study's
`.local` directory. The partial baseline statistics and plots in
`analysis-baseline/` validate the reporting pipeline and explicitly mark all new
curve results as missing.

The new reporting path reproduces all 32 historical full-image, motion-crop,
and motion-pixel bootstrap summaries exactly (means and both confidence limits):
[bootstrap validation](baseline-bootstrap-validation.json). The metric container
is pinned by immutable image ID and package versions in
[metric runtime](metric-runtime.json).


Final production validation covers all six 45,000-update continuations:
270,000 contiguous updates, finite losses and point counts, monotonic timings,
and all 24 required new checkpoint hashes in
[resource evidence](resources-final/trajectories.json). All new curve snapshots
have complete 350-target renders and 13 exact fresh-process PNG/raw-float
comparisons each, totaling 312 probes in
[render evidence](curve-render-validation.json).

[Final independent audit](final-validation.json) verifies all 30 available curve
results, 10,500 finite metric rows, exact target coverage, arm/seed/checkpoint
pairing, file hashes, and unchanged historical protocol sources. All 49 GPU
ledger segments have successful finishes and no overlap. The serial queue
completed all six trajectories and 24 new evaluations. No dense trajectory is
counted as complete.

An initial read-only final audit encountered `KeyError: 'method'`: historical
baseline index entries lack the optional method alias used by new entries.
The retained standalone audit derives that alias from the arm and verifies it
against the actual render and metric metadata. It then passed on all results;
no historical entry was modified and no GPU work was repeated.

Both endpoint visual bundles pass file-hash, count, and video-cadence checks:
48 comparison PNGs and 12 videos per endpoint, each video containing 50 frames
at 25 fps. [Visual assessment](visual-assessment.md) records the manual inspection
scope and remaining player failures. [Final statistics](analysis-final/statistics.json)
and [report](report.md) distinguish measured sparse duration effects from the
unavailable dense effects. Full Plan 026 attainment is not established.
