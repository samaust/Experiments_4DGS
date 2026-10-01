## Parent

[#44](https://github.com/samaust/Experiments_4DGS/issues/44)

## What to build

A CPU-tested path binds extra source frames to the accepted scale grid and produces synchronized clips with honest metric/relative displays, including D2 reuse.

## Acceptance criteria

- [ ] Prepare immutable context manifests linked to accepted source videos and the original scale-input manifest; use the same 960×540 remap, verify anchor bytes, retain all 30 training cameras and exclude cameras 0/10/20/30.
- [ ] Represent isolated video fit context 50–149 and check context 150–199, original timestamps and camera/role reset boundaries; reject changed or missing context and frames 200–249.
- [ ] Generate and validate four genuine 50-frame, 25-fps clips per available candidate for cameras 1/11/21/31, frames 150–199, with matched RGB, full/center/left/right views and synchronized playback.
- [ ] Keep the metric display at 0–20 m with invalid/out-of-range diagnostics. Label relative domain/direction and freeze deterministic normalization per clip without modifying raw values.
- [ ] Reuse only exact matching historical D2 outputs, including frame 175; enforce 60 anchors plus at most 196 extra published maps per addition and at most 196 newly generated D2 clip maps.
- [ ] Demonstrate the complete path with CPU fixtures; actual extraction, generation and publication remain charged to subsequently admitted allocations.

## Blocked by

- [#46](https://github.com/samaust/Experiments_4DGS/issues/46)
