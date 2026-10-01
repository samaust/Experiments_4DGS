## Parent

[#44](https://github.com/samaust/Experiments_4DGS/issues/44)

## What to build

MoGe-3 produces comparable metric outputs using accepted camera calibration and exactly three refinement steps.

## Acceptance criteria

- [ ] Use the pinned MoGe-3 ViT-L release with supplied horizontal FoV and exactly three refinement steps; retain its required native dependencies and settings.
- [ ] Reuse the established FoV/grid behavior while preserving model-specific raw results, validity and camera-z conversion.
- [ ] Demonstrate immutable worker output, unchanged scale gates and frozen-frame package consumption through CPU fake-runtime fixtures.
- [ ] Reject predicted-camera substitutions, alternate refinement modes, wrong grids and invalid metric values; record the asset/dependency/runtime profile without claiming actual GPU qualification.

## Blocked by

- [#48](https://github.com/samaust/Experiments_4DGS/issues/48)
