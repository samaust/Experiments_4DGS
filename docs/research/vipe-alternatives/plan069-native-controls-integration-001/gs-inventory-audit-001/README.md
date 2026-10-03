# GS runtime inventory regeneration audit

No actual `plan069-final-render-native-runtime/v1` inventory was found in canonical
`docs`/`configs` or the accepted run's `jobs`/`prepare` metadata. No actual
`plan069-depth-decision/v1` record was found in that scope either. Historical
training results, upstream model configuration files, source snapshots and CPU
fixtures are not a prepared inventory bound to the pending D* final-render run.

The exact new inventory cannot yet be regenerated: no previous inventory supplies
its environment/interpreter, native binary records, AlexNet checkpoint and
resolved configuration. The latter must bind the accepted D* scene normalization
and historical normalized scene scale, exact `native` configuration and typed
start/end 0/50. The generator must not evaluate native code or invent defaults to
fill these fields. Actual native `asdict(cfg)` comparison remains a later gate.

## Independently available now

`source-inventory.json` freezes all 14 files required by the current canonical
`final_render_inventory.required_sources(...)`, including the inventory validator,
current adapters and `.local/FreeTimeGsVanilla` trainer/utils. The trainer SHA256 is
`fc3e4320da73a470d0a16bcb5803f84d1bda5bdeafb000fcc39e022fbcfaaeb4`, matching the
existing audited source. This is source preparation only, not a native runtime
inventory or qualification receipt.

Historical documentation identifies `.local/envs/freetimegs` and the
FreeTimeGsVanilla checkout pinned to `911dcf4157a3ddf5c96d9147f97627480268fe0f`.
It does not provide the new complete file-bound dependency inventory. Once the
exact environment is selected, its eight required dependencies can be prepared
using explicit installed `METADATA` and `RECORD` files and their versions, without
importing Torch/CUDA/native libraries or waiting for D*. Those identities are
`torch`, `numpy`, `scipy`, `Pillow`, `torchvision`, `torchmetrics`, `gsplat`,
`fused-ssim`. Explicit interpreter/native binary/AlexNet records can be frozen
independently too, once their exact paths are supplied. Runtime/cache trees were
not searched or read in this audit.

After the resolved scene/configuration and all explicit runtime records exist,
call the canonical `prepare_inventory(checkout=..., environment_prefix=...,
interpreter=..., binaries=..., dependencies=..., resolved_config=...,
lpips_checkpoint=..., output=<new immutable revision>, source_files=...)`.
Use a fresh output path; preserve historical records. No exact executable full
regeneration command is claimed while these required inputs are missing.

References: `docs/specs/plan031-execution/qualitative-final-render-runtime-inventory.md`,
`docs/research/vipe-alternatives/plan069-native-controls-001/README.md`,
`docs/experiments/007-freetimegs.md`, and `scripts/build-freetimegs-native.sh`.

Only this isolated `.local` audit directory was written. No native package import,
GPU/model operation, network request, live ledger mutation or canonical write was
performed. #34/#35 remain open.
