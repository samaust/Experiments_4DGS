# Plan 069 depth execution review 001

**State: REVIEW.** This freezes proposed one-attempt slots; it approves no
transfer, environment setup, CPU preparation or GPU run. The machine-readable
[proposal](depth-execution-review-001.json), [required-only asset inventory](depth-required-assets-v1.json),
[native profiles](depth-runtime-profiles-v1.json) and [ledger snapshot](depth-live-review-snapshot-001.json)
are part of this review. Actual asset hashes, installed dependency closure,
source review, runtime qualification and an exact explicit DO approval remain
preconditions. The `depth_admission.review` check must pass against *fresh*
budget, ledger and GPU-owner samples immediately before each reservation.

## Exact commercial evidence

The existing [survey audit](../../research/depth-model-survey-data/licenses.csv)
separates code, weights and output terms. These exact pinned primary pages are
the baseline for a new assessment receipt; an installed native dependency may
still block commercial eligibility. No model grant conveys rights in input
footage or clears the complete 4DGS stack.

| Slot | Code | Exact weights | Output/use and required dependency disposition |
|---|---|---|---|
| D2 | [DA3 Apache-2.0](https://github.com/ByteDance-Seed/Depth-Anything-3/blob/3d835ec1a5802d64a8b8b15f817a1ab54809bfe4/LICENSE) | [DA3METRIC-LARGE Apache-2.0 card](https://huggingface.co/depth-anything/DA3METRIC-LARGE/blob/4010e39f3634a45bc60553321fb49fb760bd594e/README.md) | No additional output restriction found; historical E5 dependency/native-binary clearance remains unresolved. Historical D2 maps may be reused only with exact lineage. |
| D5, D6 | [MoGe MIT; bundled DINOv2 Apache-2.0](https://github.com/microsoft/MoGe/blob/74fbce054ebed49800de42d0ad0e83495065719a/LICENSE) | [D5 MIT card](https://huggingface.co/Ruicheng/moge-2-vitl/blob/39c4d5e957afe587e04eec59dc2bcc3be5ecd968/README.md), [D6 MIT card](https://huggingface.co/Ruicheng/moge-3-vitl/blob/184008f877d7ad1ad4c2cd2182a9bd1f63d0e5be/README.md) | No separate output restriction found. Retain MIT/Apache notices; audit D6 sparse-convolution native payload. |
| D7 | [DA V2 Apache-2.0 code](https://github.com/DepthAnything/Depth-Anything-V2/blob/a561b849ebae10a6f5ef49e26c83cbbcd36c71bf/LICENSE) | [Metric Hypersim Small Apache-2.0 card](https://huggingface.co/depth-anything/Depth-Anything-V2-Metric-Hypersim-Small/blob/3bc65d4e14a6786a61acec16453c50e12bf5f338/README.md) | Small-specific grant permits commercial inference; no separate output restriction found. Do not substitute larger noncommercial checkpoints. |
| D8 | [MetricAnything Apache-2.0](https://github.com/metric-anything/metric-anything/blob/616a5e6762f5fc40d1a4ef990fee04c800532f59/LICENSE) | [PointMap Apache-2.0 card](https://huggingface.co/yjh001/metricanything_student_pointmap/blob/8f1f08c53c683d4e19864601dfaf78515f29a63b/README.md) | No separate output restriction found. Bundled MoGe MIT/DINOv2 Apache notices and actual student dependency closure require inspection. |
| D9, D10 | [VDA Apache-2.0](https://github.com/DepthAnything/Video-Depth-Anything/blob/4f5ae23172ba60fd7bc11ef671cca678842c7072/LICENSE) | [D9 relative card](https://huggingface.co/depth-anything/Video-Depth-Anything-Small/blob/256875362cff76724b920335dfb4b29dd611f66e/README.md), [D10 metric card](https://huggingface.co/depth-anything/Metric-Video-Depth-Anything-Small/blob/273d090f2ce17df50c2872d82c8322c45da5b4dd/README.md) | Both Small releases declare Apache; no separate output restriction found. Audit actual video and DA V2 backbone dependencies. |
| D11 | [Marigold V2 Apache-2.0 with NOTICE](https://github.com/huawei-bayerlab/marigold-v2/blob/bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85/LICENSE) | [Log-stage2 Apache card](https://huggingface.co/huawei-bayerlab/marigold-v2-0/blob/cdf9810fb690886391a63aec012b5f501064fb0d/README.md); [required Qwen base Apache card](https://huggingface.co/Qwen/Qwen-Image-Edit-2509/blob/d3968ef930e841f4c73640fb8afa3b306a78167e/README.md) | No separate output restriction found. Qwen is required, DINOv3 training-loss weights are not. Preserve both projects' notices and inspect the installed bitsandbytes/CUDA dependency closure. |

The grants above support model-level commercial inference under their notices.
All eight slots currently have **unverified installed dependency closure**, so
the commercial admission gate remains closed until a hash-bound assessment
receipt cites the exact code, weight, base, inference/output and dependency
evidence. Missing or conflicting terms remain blocked.

## Bounded workload and live capacity

Each slot has one proposed attempt. D5–D8 and D11 cover 60 anchors plus 196
other selected clip frames, for at most 256 published maps each. D2 generates
only 196 missing control maps. D9/D10 process 4,500 native context frames each
(30 cameras × 100 fit and 50 check frames), plus their native overlap, padding
and resets, even though at most 256 maps are retained for review. Each candidate
publishes four 50-frame clips at 25 fps. The proposed per-slot maxima are in
the JSON; together they reserve 49,200 GPU seconds, 19,800 CPU seconds and
16,800 setup seconds. Every stage counts transfers, first load, quantization,
inference, packaging, retention and cleanup. Failure consumes its attempt and
charges actual work; correction follows AGENTS.md and any explicit attempt cap.

The snapshot at **2026-10-01 03:15 UTC** has an active
`S1-calibration-recovery-011` GPU reservation. It shows 24.735 GiB new-download
and 40.174 GiB new-artifact capacity left under the historical 60/150 GiB
caps. The seven D2/D5–D10 proposed transfer maxima total about 19.36 GiB and
their artifact maxima total 35 GiB, before future S1 or other charges. They
still need exact review, qualification, source/asset receipts and approval;
none may dispatch while another agent owns the GPU.

D11's proposed transfer maximum is about 48.04 GiB, including 40.04 GiB of
required model files and bounded environment/source overhead. Its 55 GiB
artifact maximum includes those assets, outputs and retention. **D11 fails both
current cumulative caps even if attempted first.** The full eight-slot maxima
require about 102.67 GiB cumulative downloads and 199.83 GiB cumulative
artifacts from this snapshot. A prospective cap amendment to **110 GiB new
downloads and 210 GiB new artifacts** would cover those maxima with limited
headroom, but only explicit user approval and a versioned admission amendment
can enact it. If the user declines, D11 remains unstarted and #58/#59/#44 stay
open; no omitted slot is called complete.

The current ledger's GPU/CPU/setup remaining seconds exceed the proposed sums,
but these figures are snapshots and S1 can consume them. Memory is limited to
22 GiB device peak; proposals cap model allocation at 21 GiB, subject to live
process and first-load measurements. The [Marigold release](https://github.com/huawei-bayerlab/marigold-v2/blob/bf21e4ad9fb0ae1376bbfb2ec79e999802f19a85/README.md)
reports about 17 GB at 1024² and minutes of first-load quantization, not proof
that this host passes 960×540. A failed qualification cannot be converted into
an approved model run.
