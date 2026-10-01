## Parent

[#44](https://github.com/samaust/Experiments_4DGS/issues/44)

## What to build

A pinned MoGe-2 worker carries supplied camera information through native inference, restored metric outputs, scale diagnostics and a frozen-frame comparison.

## Acceptance criteria

- [ ] Use the approved original MoGe-2 ViT-L source/checkpoint and supplied horizontal FoV derived from accepted intrinsics and width; freeze native preprocessing, precision and seed policy.
- [ ] Prefactor the shared supplied-FoV and point-map restoration behavior needed by D6/D8 within this working D5 path; reject incompatible centered-pinhole geometry.
- [ ] Preserve native points/depth, validity and resize/pad/crop lineage, restore float32 camera-z metres with NaN invalid pixels and avoid extra focal multiplication.
- [ ] Verify the request-to-output/scale/package path with independent CPU fake-runtime cases for known z, off-axis points, invalid contributors and conversion errors.
- [ ] Provide the exact required asset/dependency inventory and runtime profile for commercial review and fresh execution admission; do not claim native qualification from CPU fixtures.

## Blocked by

- [#46](https://github.com/samaust/Experiments_4DGS/issues/46)
