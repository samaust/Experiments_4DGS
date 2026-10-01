## Parent

[#44](https://github.com/samaust/Experiments_4DGS/issues/44)

## What to build

Admitted D11 execution produces actual relative-depth anchors and independently inferred motion clips within its measured host limits.

## Acceptance criteria

- [ ] Independently review/qualify the current source and verify exact adapter/base assets, commercial permissions and runtime before inference under approved fresh allocations.
- [ ] Use native single-step four-bit inference with frozen seeds/settings; measure first-load quantization and all setup/load/inference/publication/storage costs within the existing device and CPU limits.
- [ ] Produce 60 anchors and four complete 50-frame clips with independent single-image inference and fixed per-clip relative-log display normalization.
- [ ] Keep D11 outside metric-scale/downstream eligibility, retain raw values and exact source/grid lineage, and publish actual results/counts/hash/resource/cleanup evidence.
- [ ] Preserve failed attempts and complete required slots only through accepted results or explicit authorized terminal dispositions; no unapproved fallback or extra attempt.

## Blocked by

- [#47](https://github.com/samaust/Experiments_4DGS/issues/47)
- [#54](https://github.com/samaust/Experiments_4DGS/issues/54)
- [#55](https://github.com/samaust/Experiments_4DGS/issues/55)
