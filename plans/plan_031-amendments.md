# Plan 031 amendments

`plan_031.md` is kept byte-identical to its 2026-09 revision because historical S1 recovery evidence binds
its exact bytes. Later amendments are recorded here instead. Each one applies to Plan 031 as if inserted after
its D1 runtime section.

### D8 runtime amendment — 2026-10-03

The user requested the latest stable PyTorch supporting CUDA 13.0 for D8 in
[Plan 069](plan_069.md): Python 3.11, **torch 2.14.1+cu130** and
**torchvision 0.29.1+cu130**. Preserve D8's original pinned `torch<2.5.0`
requirement verbatim and record this explicit local compatibility exception.
Actual native compatibility remains pending metered setup and qualification;
metadata checks alone do not establish it. Model/source/weight pins, input grids,
scale gates, workloads and approved resource/attempt limits remain unchanged.
See the [runtime amendment](../docs/research/vipe-alternatives/plan069-D8-cu130-runtime-amendment.md).
Preserve original REVIEW/approval records and create new affected lineage.
