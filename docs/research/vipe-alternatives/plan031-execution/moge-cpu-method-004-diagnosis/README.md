# D6 CPU import qualification blocker

The approved CPU method requires importing the unchanged actual v3 model class,
strictly loading its weights twice on CPU, and no CUDA initialization. That
contract is blocked before model construction by pinned FlexGEMM import code.
No passing method004 or CPU qualification receipt was produced.

## Reproduction

The bounded import-only `probe.py` reproduced the exact zero-active-driver
exception in 3.313686648 seconds. It reads no checkpoint and constructs no model.
Triton 3.2's Autotuner constructor chooses an active GPU driver immediately when
`do_bench` is omitted. FlexGEMM's decorator omits the supported callback parameter.

A scoped callback supplied through the supported constructor parameter avoided
that first driver lookup, but import then reached sparse convolution config.
`get_autotune_config(device=..., platform=...)` calls `get_gpu_name()` when a device table is supplied, as it is here, which unconditionally calls `torch.cuda.get_device_name()`.
FlexGEMM's environment/cache/autotune controls do not defer that device lookup.

The first callback probe omitted an explicit CUDA initialization guard. Its GPU
was masked; attempted initialization failed with “No CUDA GPUs are available.”
This failed probe is preserved for accountability and must not be rerun.

The corrected `guarded_lazy_probe.py` installs the same fail-closed CUDA guard
as actual CPU qualification. It adapted two real autotuner constructors without
calling a benchmark, then rejected GPU initialization in 3.230959074 seconds.
CUDA remained uninitialized and the original constructor was restored. This is
a red-capable feedback loop for the remaining blocker.

## Required contract change

The current exact class cannot be imported under the zero-CUDA CPU contract
without changing its GPU configuration selection. Replacing the model, kernels,
or device detection with fixtures would not qualify the actual runtime.

Choose and review one explicit amendment before further actual qualification:

1. Derive an approved CPU-import-safe dependency implementation with lazy
   benchmark and GPU configuration selection. Preserve pinned original inputs,
   review the derivation, and refresh runtime recipe/source/inventory gates.
2. Permit a bounded GPU-aware import and actual strict model loading under an
   approved GPU reservation. Clearly replace the zero-CUDA CPU claim and define
   how this qualification fits the one native-attempt limit and existing budgets.

Standing CPU retries after bug fixes do not authorize either amendment's GPU
execution or changes to pinned runtime/source acceptance. Actual checkpoint
serialization or AST-only inspection cannot substitute for two strict actual
class loads without an explicit specification change.

## Evidence and accounting

`diagnosis.json` binds five unchanged installed source files. The two timed
probes total 6.544645722 seconds. The first callback probe has no elapsed receipt;
its command had a 30-second limit. Root owns accounting and may conservatively
charge that full bound. Interactive analysis/review time is unmeasured.
No installed package or production source bytes changed, model/weights were not
loaded, no inference occurred, and no shared ledger writes were made.

Independent Standards and Spec reviews passed. Both verified the five exact
installed source records and honest blocked scope; no probe was rerun in review.
