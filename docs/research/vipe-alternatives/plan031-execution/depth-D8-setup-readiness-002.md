# D8 setup readiness after the CUDA 13.0 amendment

Status: **draft; not an admissible source, runtime or commercial receipt**.
No setup, asset transfer, GPU work or ledger write occurred in this preparation.

## Recipe

[Environment draft](depth-D8-environment-draft-002.json) binds the retained E5
Python 3.11 seed, its completed setup result and the existing uv binary by hash.
It targets Torch 2.14.1+cu130 / TorchVision 0.29.1+cu130, NumPy 1.26.4 and the
explicit D8 compatibility profile. The intended output is:

`/home/auss/git_repos/samaust/Experiments_4DGS/.local/vipe-alternatives/plan031-20260913T032700Z/jobs/plan069-D8-setup-001/runtime`

The draft includes that directory, which must also be bound by the production
recipe before actual preparation. Regenerate the recipe after the pending
production fix; do not dispatch this draft wrapper.
The parent confirmed DO002 approval for a **6 GiB dependency transfer allowance**
and **9 GiB candidate artifact cap**. These are candidate bounds, subject to the
shared 110 GiB / 210 GiB caps and original attempt/time limits.

The pinned model requirements file has not been acquired locally in this
preparation. Its previously checked primary source declares `torch<2.5.0` and
utils3d revision `3fab839f0be9931dac7c8488eb0e1600c236e183`. Preserve the original
file from the pinned source archive and hash it during setup. Recipe selection
and explicit exception checks are ready; actual extracted-source identity and
package resolution are pending. No raw research text was substituted for an
accepted archive or installed package.

## Source closure

[Source readiness snapshot](depth-D8-source-readiness-draft-002.json) records
38 unique files at canonical integration paths: common ledger/admission,
resources/supervision, transfer and runtime helpers; D8 native loader, dependency
profile/environment, PointMap/grid/scale logic; setup, map, dispatch and publication
entrypoints. This is a read-only hash snapshot, not an independent passing review.
Pending production changes invalidate it; refresh all records and independent
source review after those changes settle. Final review must additionally bind
configuration/runtime profiles, approved proposal/DO002 lineage and extracted
native/dependency source manifests. Runtime package inventory and native-source
closure cannot be completed before metered setup.

## Commercial evidence

- Pinned [MetricAnything source license](https://github.com/metric-anything/metric-anything/blob/616a5e6762f5fc40d1a4ef990fee04c800532f59/LICENSE): Apache-2.0, freshly verified through the primary GitHub file view.
- Pinned [utils3d license](https://raw.githubusercontent.com/EasternJournalist/utils3d/3fab839f0be9931dac7c8488eb0e1600c236e183/LICENSE): MIT, freshly verified through the primary raw file.
- Exact [weight snapshot](https://huggingface.co/yjh001/metricanything_student_pointmap/tree/8f1f08c53c683d4e19864601dfaf78515f29a63b): previous source audit records Apache-2.0. Fresh Hugging Face tree/raw/card checks through the browser tool were unavailable, so this preparation does not claim a fresh independently captured weight-card receipt.

These source findings support commercial assessment preparation. They do not
qualify the installed Torch/CUDA/transitive dependency closure or establish an
unconditional output-rights guarantee. Capture exact weight-card/license bytes
and installed dependency terms during the accepted setup/qualification workflow;
record inference/output restrictions separately. Commercial admission remains
pending that evidence.

## Remaining actual gates

1. Production recipe/admission correction, refreshed exact source review and DO002 lineage.
2. Fresh shared resource/ledger state and exclusive GPU ownership; root dispatches the one approved metered setup.
3. Hash-locked resolution/installation and asset/source integrity within all approved limits.
4. Exact prepared-interpreter metadata, installed native import closure and independent commercial review.
5. Strict checkpoint/native inference and original-grid, supplied-camera, mask, scale and cleanup qualification in the authorized workload.

The earlier failed Torch 2.4.1 HEAD request remains preserved. This new runtime
recipe has not made a successful wheel request or native compatibility claim.
Draft JSON structure checks passed; existing code milestone validation remains
14 CPU tests plus mypy, with Torch 2.13 CPU tensors serving only as a proxy.
