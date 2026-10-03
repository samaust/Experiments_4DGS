# D8 CUDA 13.0 runtime amendment

The user requested the latest stable PyTorch release supporting CUDA 13.0.
D8 now requests **PyTorch 2.14.1+cu130 / TorchVision 0.29.1+cu130** on the
existing Python 3.11 seed. NumPy remains 1.26.4. Model source, weights,
utils3d revision, cameras, frames, calibration and prediction workload remain
pinned. D11's independent recipe remains unchanged.

## Evidence and compatibility boundary

The [PyTorch 2.14.1 release](https://github.com/pytorch/pytorch/releases/tag/v2.14.1),
[official Torch CUDA 13.0 index](https://download.pytorch.org/whl/cu130/torch/) and
[official TorchVision CUDA 13.0 index](https://download.pytorch.org/whl/cu130/torchvision/)
list these stable versions, including Python 3.11 Linux x86_64 wheels.
The [TorchVision 0.29.1 release](https://github.com/pytorch/vision/releases/tag/v0.29.1)
is the matching release. These primary-source checks establish availability,
not successful transfer or installation on this host.

The pinned MetricAnything student [requirements file](https://github.com/metric-anything/metric-anything/blob/616a5e6762f5fc40d1a4ef990fee04c800532f59/models/student_pointmap/requirements.txt)
requires `torch<2.5.0`. This amendment is an explicit local compatibility
experiment outside that upstream constraint; upstream support is **not** claimed.
The extracted requirements file is preserved verbatim, hashed in runtime output
and rechecked at entry. Its original Torch constraint must match before any
runtime dependency acquisition. A changed or duplicated Torch constraint fails.

The exact `D8-torch-2.14.1-cu130` profile records the original constraint and
`upstream_supported=false`. Modern Torch is rejected without this explicit
profile; wrong Torch/TorchVision versions or CUDA build suffixes fail. Setup and
entry qualifications bind the selected profile alongside package metadata and
pinned local utils3d archive provenance. This profile is metadata policy, not a
claim of native inference compatibility.

The [pinned native model](https://github.com/metric-anything/metric-anything/blob/616a5e6762f5fc40d1a4ef990fee04c800532f59/models/student_pointmap/moge/model/v2.py)
uses Torch inference mode, autocast, interpolate and tensor operations; its
encoder and utils3d dependencies must also be tested in the actual prepared
runtime. The existing native loader still checks all source files, exact weights,
`weights_only=True`, strict state-dictionary loading and eval mode. The existing
PointMap adapter and original-grid validation are unchanged.

## Validation and remaining gates

Eight targeted CPU tests pass, covering explicit profile selection, exact CUDA versions,
changed original constraints, metered local dependency provenance, prepared
interpreter identity, strict checkpoint loading and source/weight mutation.
The PointMap adapter test uses real CPU Torch tensors with a fake inference
result, checking supplied-camera identity, camera-z consistency and invalid-mask
restoration. The available Torch 2.13.0+cu130 runtime is a proxy only.
Six existing MoGe geometry tests also pass. Mypy with `--check-untyped-defs` passes for both changed runtime modules.
These tests use fixtures and do not establish actual PyTorch 2.14.1 compatibility.
No package installation, model transfer, GPU attempt or ledger event was performed
for this amendment.

Before actual dispatch, refresh source review and runtime proposal lineage;
confirm dependency transfer and retained artifact headroom within approved caps;
use the one approved metered setup; inspect exact installed dependency/licence
closure; then qualify actual imports, strict checkpoint construction and native
inference with unchanged grid/mask/scale gates. Preserve failures as evidence.
The old Torch URL's HTTP 403 remains a failed access record; this requested
runtime change does not retrospectively turn that operation into a success.
The existing 110 GiB / 210 GiB aggregate caps and explicit attempt limits remain.
