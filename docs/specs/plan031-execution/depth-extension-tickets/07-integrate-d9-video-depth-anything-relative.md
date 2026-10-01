## Parent

[#44](https://github.com/samaust/Experiments_4DGS/issues/44)

## What to build

Native offline video inference produces labeled relative depth frames and stable-display clips while keeping camera and fit/check contexts isolated.

## Acceptance criteria

- [ ] Pin Video Depth Anything Small relative in native offline sequence mode; preserve native windowing, padding, overlap interpolation and relative scale/shift alignment.
- [ ] Reset at every camera/role boundary and bind all context frames and window work, including context that is not displayed.
- [ ] Publish relative inverse depth, validity and raw lineage; reject metric-scale/downstream admission and any sparse-map alignment presented as metric conversion.
- [ ] Exercise the complete request-to-clip path with CPU fake runtimes at 32-frame boundaries, short/padded tails, overlaps, timestamps, missing frames and context changes.
- [ ] Record exact assets/settings/runtime dependencies and all context accounting required for actual qualification.

## Blocked by

- [#47](https://github.com/samaust/Experiments_4DGS/issues/47)
