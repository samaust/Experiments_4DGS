# Compare multi-view depth and geometric models

## Parent

[Issue #36 — Survey depth estimation models and compare published evidence](https://github.com/samaust/Experiments_4DGS/issues/36)

## What to build

Give the reader a complete comparison section for multi-view depth and
geometric foundation models, explaining their required views and cameras,
reported depth/geometry results, scene-motion assumptions, releases and
commercial terms. Assess how these requirements relate to the project's
calibrated multi-camera footage.

Use the parent contract and current source reconnaissance, including VGGT as a
lead. Different DA3 variants may be recorded when relevant, with exact identity
and input regime distinguished from D2. Deliver independently reviewable
findings and supporting evidence within the parent's literature-only scope.

## Acceptance criteria

- [ ] Category searches and two rounds of comparison-table/reference expansion are logged through the 2026-09-30 cutoff, including later/independent evaluations and exclusions of methods requiring unavailable inputs.
- [ ] Variant records specify number/type of views, known or inferred intrinsics/poses, metric or arbitrary scale, output meaning and documented static-scene, synchronization or motion assumptions.
- [ ] Depth, point-cloud/reconstruction and pose metrics are kept distinct, with dataset/split, masks, alignment or similarity transforms, view selection/count, training regime and exact source-table provenance recorded.
- [ ] Comparable tables do not credit extra input views, supplied camera information or ground-truth alignment as an unexplained like-for-like gain over a single-image method. Unknown protocol details remain comparison limits.
- [ ] Reported behavior on moving scenes and occlusions is distinguished from static-scene results and untested applicability to Basketball. Geometry or pose gains are not presented as measured final-render gains.
- [ ] Reported resource costs include hardware, image resolution, number of views, precision and other available conditions. Missing limits remain unknown.
- [ ] Official implementations and exact weights are verified, including paper/release differences, access conditions, four separate commercial-use findings and documented material dependency qualifications.
- [ ] A readable section and supporting search, model, benchmark and license records explain project fit and future-test questions. Every reported number and shortlist release/license claim is source-checked and limitations are recorded.

## Blocked by

None (can start immediately).
