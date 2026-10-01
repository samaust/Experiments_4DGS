## Parent

[#44](https://github.com/samaust/Experiments_4DGS/issues/44)

## What to build

The Hypersim Small checkpoint produces metric frames and scale diagnostics under its approved native processing settings.

## Acceptance criteria

- [ ] Pin the Depth Anything V2 Metric Hypersim Small source/checkpoint with native 518 processing and the 20 m indoor range.
- [ ] Restore native camera-z output and validity to the accepted grid, preserve clamps and preprocessing lineage, and avoid additional focal/scale multiplication.
- [ ] Exercise the worker-to-scale/package path with CPU fixtures covering known depth, resize restoration, invalid/nonfinite values and native range behavior.
- [ ] Freeze required assets, dependencies, precision and seeds for the commercial/admission inventory; actual compatibility and costs require the execution ticket.

## Blocked by

- [#46](https://github.com/samaust/Experiments_4DGS/issues/46)
