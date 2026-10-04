# Explicit D9/D10 latest PyTorch CUDA 13 runtime amendment

User requested latest stable PyTorch supporting CUDA 13.0 for D9/D10. Primary
[PyTorch 2.14.1 release](https://github.com/pytorch/pytorch/releases/tag/v2.14.1)
and [Torchvision 0.29.1 release](https://github.com/pytorch/vision/releases/tag/v0.29.1)
are dated 2026-09-30. Official cu130 indexes list matching Python 3.11
manylinux_2_28 x86_64 wheels. Index evidence and digests are retained here.

## Implemented preparation

- New `video-environment-v2.json` pins Torch 2.14.1+cu130 and Torchvision
  0.29.1+cu130. NumPy 1.24.0, other dependencies, model/checkpoint/source pins,
  native camera-role reset/windowing, precision and output contracts remain.
- New `depth-runtime-profiles-video-v2.json` adds the exact D9/D10 runtime
  exception. Native upstream requirements are preserved and rehashed, including
  original Torch 2.1.1 / Torchvision 0.16.1. No upstream support is claimed.
- Explicit `--authorization` selects a reviewed new DO for setup/native dispatch
  and new CPU method002. Defaults continue selecting immutable DO001 and the
  original recipe. Method001 and all historical approvals/failure receipts are
  unchanged. New DO validation requires immutable prior authority, identical
  scientific settings/budgets/workloads, no consumption reset and exactly
  D9/D10 grants. New profile inventory is rejected for other candidates.
- Setup binds recipe/profile to the approved proposal before acquisition.
  Native dependency inventory/model entry check exact versions/CUDA suffixes
  and forbid Xformers. Removing the runtime profile from setup evidence fails.
  Completed D10 eligibility accepts only the profile bound to its completed
  reviewed proposal; current execution checks remain separate.
- `depth-video-runtime-review-001.json` is a prospective REVIEW with unchanged
  allocations. Its new records bind the existing preparation worktree. After integration,
  create a fresh versioned REVIEW against the intended execution checkout; do
  not overwrite this preparation artifact. It grants no DO or execution
  authority. Root must finalize
  authorization only after review, exact closure/budget evidence and user
  distribution selection. Fresh source reviews are required after integration.

## Access and distinct distribution evidence

The exact new metadata URL is:

`https://download-r2.pytorch.org/whl/cu130/torch-2.14.1%2Bcu130-cp311-cp311-manylinux_2_28_x86_64.whl.metadata`

Its bounded GET failed with HTTP403 both sandboxed and on its one outside
retry. Sidecar access is stopped; the actual wheel GET was **not tested**.
This does not prove wheel downloads fail. Old cu121 blocked receipts remain.
No alternate URL was used to evade this failed operation.

Primary PyPI torch2.14.1 release metadata is separately retained for a possible
**distinct distribution** proposal. Its unsuffixed cp311 Linux wheel is
554,581,699 bytes, SHA256
`305a61f61f35f128579f299c5bd33d475f6a01c6307336139632e30856c4854d`.
`Requires-Dist` explicitly selects cuda-toolkit13.0.3 plus CUDA13 bindings and
libraries. It is not the indexed `+cu130` wheel and its size/digest/closure must
not be attributed to that wheel. Switching to this distribution requires
explicit user authorization and a separate versioned recipe/profile; no
artifact was downloaded or installed for either distribution.

NVIDIA skill discovery: `npx skills add nvidia/skills --list` failed on read-only
npm cache, then its one outside retry successfully listed 398 catalog entries.
No skills were installed. Catalog discovery supplied no native model/runtime
qualification or additional execution authority.

## Validation and remaining gates

46 targeted CPU cases pass: video setup/dispatch, relative/metric adapters,
new explicit runtime/version/profile/DO checks and depth review. All fake
runtimes use agreed seams; no native model or GPU was loaded. Exact installed
compatibility is still unqualified. Mypy was requested but unavailable in the
specified existing interpreter/overlay; this limitation is retained. AST
checks cover all changed Python files and the new retained producer. Root's
full combined suite and independent Standards/Spec review remain required.

Root must qualify combined sources, resolve selected-distribution dependency
closure and commercial permissions, reconcile current global110/210GiB caps,
finalize reviewed DO, refresh independent source receipts and use the one
approved metered setup per candidate. Then actual CPU/native qualification and
one admitted serial GPU attempt can proceed under unchanged limits. #57/#44
remain open.

### Independent review follow-up

Two independent axes are clear after scientific-profile and historical-authority
lineage corrections. **49 targeted CPU cases pass; mypy with
`--check-untyped-defs` passes all nine changed source files.** The private
typechecking tool does not alter model environments. Original failed/missing
tool captures remain; follow-up002 retains passing output and measured scope.
The full combined checkout must still be qualified by root.
