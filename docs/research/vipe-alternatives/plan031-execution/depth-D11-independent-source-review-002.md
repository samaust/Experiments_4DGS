# D11 independent upstream review completed

This supersedes the upstream inspection limitation in review 001. A bounded
primary-source research fetch retained eight files from exact revision
`bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85`, totaling 48,085 bytes.
`depth-D11-pinned-source-research-001.json` records HTTP 200 responses, exact
URLs, raw byte counts, SHA256 hashes and local research paths. One sandbox
allowlist failure was followed by the authorized successful outside retry.
No model assets, packages or setup were transferred.

Independent reviewer `runtime_resume/d11_setup_source_review` rehashed and read
all eight files. Native CLI and local checkpoint paths, seed 2025, batch one,
multiple-of-16 Lanczos resize, float32 restored output with OpenCV linear
interpolation, effective NF4 transformer and BF16 compute/VAE defaults,
precomputed prompt, one transformer step, timestep 0.499 and decoded-channel
mean match the approved profile. The inherited dataset configuration does not
override quantization. Every upstream direct dependency is included in the
environment recipe, with the native Torch/torchvision/cu128 pins; Python 3.11
satisfies upstream `>=3.10`.

No actionable source blocker was found. The reviewer checked the changed
`depth_admission.py` at integration commit `7e465e9f`: it adds D9/D10 source
bindings and leaves D11 behavior unchanged. Other snapshot records matched.
Final admission receipt remains pending the downstream source integration and
an updated canonical source snapshot/review; this document is not that receipt.

Actual setup must independently verify extracted source/archive and asset
identities. Installed dependency terms, runtime/model-load success, GPU peak
memory and output quality remain unqualified. No setup attempt, GPU use or
actual ledger mutation occurred in this source qualification.
