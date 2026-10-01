## Parent

[#44](https://github.com/samaust/Experiments_4DGS/issues/44)

## What to build

The approved PointMap student produces metric comparisons using supplied FoV and the same accepted camera grid.

## Acceptance criteria

- [ ] Use the pinned MetricAnything Student PointMap release and exact weights, with supplied horizontal FoV; reject alternate checkpoint or predicted-camera modes.
- [ ] Reuse the established FoV/point-map path while preserving the release-specific inference, raw output and conversion semantics.
- [ ] Demonstrate worker result, frozen scale fit/check and frame-package consumption with independent CPU geometry and invalid-grid fixtures.
- [ ] Record exact required assets and dependencies, including bundled inference components, for commercial and runtime qualification.

## Blocked by

- [#48](https://github.com/samaust/Experiments_4DGS/issues/48)
