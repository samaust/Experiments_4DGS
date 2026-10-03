# Final-render native model input adapter

`vipe_benchmark.final_render_adapter.prepare_model_input(request, arm,
initializer_receipt, arrays)` implements the CPU initializer-to-native-model data
boundary for issue #34. The worker request/result seams were agreed previously.

It snapshots the exact seven-field initializer, validates the complete request,
array hash, composition, units and prerequisite receipt, then returns independently
owned contiguous arrays for `NativeFreeTimeModel`: `positions`, `colors`,
`velocities`, `times`, `durations`. Values, float32 dtype and normalized units stay
unchanged; conversion to Torch tensors belongs to a future admitted native worker.
`region` and `velocity_valid` remain provenance sidecars in the original bound
initializer. Native and sidecar CPU array byte counts are recorded separately;
these are not GPU, optimizer, checkpoint or total storage estimates.

Historical `plan067-final-render-request/v1` uses its unchanged S2/D4 validator.
New `plan069-final-render-request/v1` routes through
`extended_final_render_contract.validate_initializer` from #61; it cannot silently
fall back to the historical validator. Unsupported schemas, extra fields,
substituted arrays, incorrect arms and modified units are rejected.

The returned `plan069-final-render-native-input/v1` receipt binds the request,
initializer receipt, full and native-only array hashes, five-arm composition and validation result.
`validate_model_input(data, receipt)` checks the prepared native payload hash,
point count, shapes, float32 dtype and finiteness before later tensor conversion.
It does not validate execution authority; a caller must separately bind the
admitted original initializer and all live gates.
It always reports `execution_authorized: false` and
`native_adapter_qualified: false`. Preparation creates no files or ledger events,
loads no model, imports no Torch and makes no network/GPU calls. A prepared data
payload is not an execution authorization.

## Remaining native work

Issue #45's actual package-bound eligible metric D* is still required for new
geometry, initialization, training and rendering. Full-rig native geometry and
physical velocity evidence, the selected-depth initializer assembly, scene/model
binding, measured memory/storage viability, supervised training/checkpoint reload,
matched final renders, fresh qualification/allocations/live admission and actual
human M/N review remain unfinished. Existing Plan027 training CLI arm constants
and `load_frozen` cannot be bypassed or relabeled as a new five-arm executor.
CPU fixture success does not complete #34 or satisfy these gates.
