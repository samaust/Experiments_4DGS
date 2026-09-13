# Plan 031 implementation and preparation results

Implementation checkpoint `a6f24bd` adds the checked protocol configuration, source
and model snapshot settings, diagnostic data preparation, annotation import,
neutral array/geometry/scale interfaces, M0–M2 and N0–N2 primitives, annotation
statistics, finalist rules, and a hash-chained attempt ledger/process-group
supervisor. A following checkpoint records an explicit-resume transition for
unstarted blocked slots and this preparation evidence. The tested CPU interfaces
do not yet constitute the complete model/geometry execution pipeline.

## Completed preparation

The single preparation job completed in **97.46733420493547 supervised wall
seconds**; its worker body reported 96.4145889650099 seconds. Startup, serialization
and cleanup are included in the supervised measurement. The ledger records the
invocation, process-group identity and confirmed cleanup. No experiment process
remains reserved/running. PID values are those visible inside the execution
namespace, not a claim of stable host PIDs after its exit.

| Artifact | Verified count |
| --- | ---: |
| Calibration distorted RGB context images, frames 50–199 | 5,100 |
| Reconstruction training-camera RGB context records, frames 0–49 | 1,500 |
| Selected unique annotation PNGs | 232 |
| Deterministic calibration static-feature review locations | 768 |
| Immutable prepared depth RGB/sample inputs | 60 |
| Accepted static-map points | 5,294 |
| Historical input parent files reverified after preparation | 52 |

All 60 prepared-depth source RGB hashes match the freshly decoded calibration
RGB. Prepared static masks, sparse point IDs/UVs/camera-z, scale-grid K and eligibility
remain unchanged. Calibration and reconstruction grids are explicit; the processed
manifest's COLMAP K is converted to OpenCV K once. The historical scale and
normalization are retained as reference provenance, not reused as a new depth pass.

[Input index](inputs.json) points to the complete 11.6-MB immutable input manifest,
sample/map records, annotation template and exported-image directory. Bulky outputs
remain under `.local/vipe-alternatives/plan031-20260913T032700Z/prepare/`; no bulky
assets are staged in Git. The preparation environment reports OpenCV 5.0.0, whose
native interpolation can retain weights below 1/32 pixel. Depth validity uses the
same `INTER_LINEAR` kernel as depth sampling, rather than assuming a fixed
quantization table.

## Validation and accounting

[Initial validation](implementation-validation.json) and the
[updated validation](implementation-validation-002.json) retain source hashes,
commands and test logs. The complete initial focused suite passed 47 tests;
the added explicit-resume boundary passed together with its 10 neighboring
supervisor tests, giving 48 unique focused checks. The four existing scale,
five temporal geometry/crop and six dense-fusion tests also passed. Syntax and
whitespace checks passed. Disposable CPU fixtures do not consume model attempts.

[Matrix accounting](matrix-accounting.json) retains every slot and its reason:
one completed preparation, 49 unstarted blocked slots and three skipped fixed
repeats with absent sources. GPU attempts/time, environment builds, candidate asset
downloads, annotation work, motion/neighbor evaluations, final aggregation/report
passes, scale evaluations and matches are all zero. The CPU allocation has
57,502.532665795064 supervised seconds remaining; its **preparation attempt is
consumed**, regardless of unused time. No attempt/time allocation was transferred
or reset. All other historical ledgers and consumption records are retained.

No new calibration, training, frame-200–249 image access or trained-render scoring
occurred. Historical report/source/metadata access is separately recorded in
[exposure history](exposure-history.json) and its [addendum](exposure-addendum-001.json).
The addendum records completed dense training and subsequent user-assessed crossing
repairs, rather than generalizing the earlier stopped pilot to later results.

## Admission blocker and remaining work

[Admission](admission.json) is blocked. **No complete independent annotations or
external primary/reviewer records have been supplied.** The exported template has
zero truth masks. The importer rejects incomplete review, same-person review,
unbound revisions, changed RGB/K, missing image/pair identities and overspent
72/24/8/8 person-hour allocations. [Annotation handoff instructions](../implementation.md#external-annotation-handoff)
describe the exact file schema. No contributor was contacted.

Native S0–S4/D0–D4 model adapters, E0–E8 runtime/asset/license qualification,
the complete diagnostic geometry worker, bounded environment setup and transfer
monitoring, stage execution and staged end-to-end aggregation/reporting remain
unfinished. They require implementation and qualification before model admission,
in addition to the external annotation prerequisite. No placeholder backend was
dispatched to consume an experiment slot. No fresh finalists, combined freezes or
final metric report were fabricated.

Resume only on explicit user instruction, within remaining allocations. Reopen
only never-started slots using the checked `resume` transition; never repeat the
consumed preparation. Preserve the original admission and create subsequent
versioned evidence when completing the remaining controller integration.

## Conclusions supported at this stop

- **Dependency removal:** neutral CPU modules pass denied-ViPE import/source
  fixtures, including a symlink. Native S1–S4/D1–D4 isolation is unverified.
- **Engineering:** preparation and the named CPU fixtures pass; full candidate
  interfaces/runtime/execution qualification remains incomplete.
- **Measured quality:** unverified. No candidate predictions or reviewed truth were
  scored, and no primary/fallback stack was selected.
- **Physical accuracy:** unverified. No independent measured checking references
  or fresh candidate scale evidence were provided.
- **License preferences:** unverified for actual installed candidate environments
  and assets. Source/model metadata pins are not complete permission inventories;
  no gated terms were accepted and no commercial/non-AGPL stack is certified.

This is a stopped-stage implementation record, not the allocated final benchmark
metric report. [Assessment](assessment.md) retains every Plan 031 criterion.
