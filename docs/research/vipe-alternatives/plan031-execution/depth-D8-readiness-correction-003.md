# D8 readiness correction and current source review

The earlier draft's claim that native D8 needs a production `runtime_directory`
field was incorrect. That explicit field is specific to the MoGe source-build
recipe. No concrete native D8 validator rejection was demonstrated. No production
schema or runtime implementation change is needed for that claim.

The existing D8 dispatcher creates its environment with the unchanged production
`depth_native_runtime.recipe('D8', run_root)`. Native preparation compares that
exact recipe, and `depth_environment._setup_deadline` requires the actual output
`run_root/jobs/plan069-D8-setup-001/runtime`, exact active setup reservation,
parent request and command binding. The shared cache is derived as
`run_root/setup-cache`. No prospective or actual `runtime_directory` key should
be added to native D8 requests. Preserve the earlier draft as historical
preparation; do not dispatch it.

The current approved profile remains Torch 2.14.1+cu130 / TorchVision0.29.1+cu130
on Python3.11, with explicit exception to the unchanged upstream torch<2.5.0
constraint. DO002 grants6GiB dependency allowance /9GiB artifacts; total candidate
transfer is7,747,448,624 bytes including frozen source/weights allowance. Attempts,
time and global limits remain unchanged.

A fresh exact production recipe and40-file source-review input were generated
from canonical integration commit57666472 into the isolated preparation directory
`.local/d8-source-review-003`. This preparation rehashes local metadata only;
its measurement receipt is distinct from a charged ledger event. Independent review passed for all40 canonical source records; see
[the review](../plan031-20260913T032700Z/depth-D8-source-review-001.json).
The measured review scope was57.907871975 seconds, excluding preliminary reads,
and the recipe/source preparation process was0.057431617 seconds. Both remain
uncharged until root records appropriate CPU accounting. No source edits or
extra model smoke were made. Actual installed dependencies,
commercial closure, checkpoint/native compatibility and model quality remain
pending, not inferred from source review.
