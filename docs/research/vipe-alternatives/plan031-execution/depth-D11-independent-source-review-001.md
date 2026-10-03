# D11 independent source review: partial

Reviewer: separate read-only Codex subagent `runtime_resume/d11_setup_source_review`.
Review input: `depth-D11-source-review-input-001.json`, SHA256
`81155b4820d50503c8268438b63878c9dae7ffd936b2688b04a4ff17b4a333f4`.

Local source safety review passed. All 42 snapshot file records match the
canonical integration files. The local profile and pinned identities match the
approved proposal. Setup enforces metered acquisition, asset headroom, disabled
automatic retries and the single-use ledger reservation. The worker uses one
256-image folder call with offline assets, the exact prepared interpreter and
the reserved process group. Relative arrays and provenance validation match the
real shared publisher; publication requires cleanup-confirmed completion and
CPU accounting. No actionable local source blockers were found.

Independent upstream verification is partial. At pinned revision
`bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85`, the official
[network_graph.py](https://raw.githubusercontent.com/huawei-bayerlab/marigold-v2/bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85/marigoldv2/experiments/20260316_qwen_depth/network_graph.py)
browser text confirms BF16 computation, precomputed prompts, timestep 499/1000,
one transformer step and mean-channel output. Browser text does not establish
a raw-byte source manifest.

The browser could not retrieve pinned `scripts/infer.py`, `component_loader.py`,
`pyproject.toml` or `setup/setup_env.sh`. Raw/blob/plain/tree variants returned
Cache miss; exact-ref GitHub API contents returned “not accessible via this tool.”
These are browser tool limitations, separate from the Torch host’s HTTP 403.
Native CLI, NF4, resize and dependency pins therefore retain the previous
documented findings but lack fresh independent upstream inspection.

No admissible `plan069-depth-source-review/v1` passing receipt is issued here.
Complete the remaining pinned upstream inspection before issuing it. This review
does not qualify installed dependency terms, native model loading, CUDA memory,
runtime success or output quality. The reviewer performed no writes, transfers,
installation, tests, GPU activity or ledger changes.
