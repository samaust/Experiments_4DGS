## Parent

[#44](https://github.com/samaust/Experiments_4DGS/issues/44)

## What to build

The pinned Marigold adapter and Qwen base produce explicitly relative log-depth comparisons through the worker and package interfaces.

## Acceptance criteria

- [ ] Use the approved Log-stage2 adapter and required pinned Qwen base in native single-step four-bit mode; freeze preprocessing, seeds, precision and required inference dependencies.
- [ ] Preserve relative log values, validity, raw lineage and restored grid; reject metric-scale/downstream admission and unapproved model/precision substitutions.
- [ ] Demonstrate independent image inference, immutable worker results and labeled frozen-frame package consumption with CPU fake runtimes.
- [ ] Expose initialization/quantization, inference, publication, memory and retention costs for fresh admission; actual clips use the shared clip path and actual host qualification remains separate.

## Blocked by

- [#46](https://github.com/samaust/Experiments_4DGS/issues/46)
