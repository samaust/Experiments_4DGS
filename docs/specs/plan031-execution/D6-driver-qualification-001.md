# Proposed D6 driver-aware qualification exception

Status: REVIEW; no GPU execution authorized. Parent #44; execution child #56.
Proposal: `D6-driver-qualification-review-001.json`.

Pinned MoGe-3/FlexGEMM uses real GPU driver metadata while importing its actual
model class. Supported Triton benchmark deferral alone does not permit a
zero-CUDA import: sparse convolution configuration selects a GPU device at
import time. Keep the accepted installed packages and pinned native source.

## Requirements

- Require an independent current source review, a passing combined CPU capture
  binding those exact helper bytes, the accepted D6 setup and a separate user DO
  binding the exact REVIEW/proposal hash before reserving a GPU.
- Allocate `plan069-D6-driver-qualification-001` once: 180 seconds including the
  stock supervisor's 30-second cleanup reserve, 2 GiB total device memory and
  64 MiB retained artifacts. Downloads are zero. Remaining global GPU budget
  must cover the full bound; global 110/210 GiB and CPU budgets remain unchanged.
- This is a separate qualification attempt. D6 native maps retain their existing
  single attempt and 3,600-second deadline. Do not reset or reuse either identity.
- Initialize the actual GPU driver for import, retain real name/capability
  metadata, and load the complete actual pinned model/state dictionary strictly
  twice on CPU. Every parameter and buffer must remain on CPU.
- Prohibit model forward/inference, GPU benchmarks and Triton kernel launches.
  Report zero calls and zero GPU tensor allocation; fail on any attempted call.
  GPU context memory is real GPU use and must be measured by the supervisor.
- Preserve full installed package/hash/notice evidence, accepted archive and
  123-source tree, scientific profile, current helper records and interpreter.
- Native admission and completed package eligibility must verify the separately
  approved request, unique reservation, accepted result, bounded clean finish
  and immutable lineage. Historical helper hashes remain retained metadata;
  these receipts grant no new execution or current-helper authorization.
- Finalize under the existing bounded CPU/offline wrapper with independently
  allowed commercial evidence for the exact installed closure. The runtime
  receipt explicitly states `gpu_aware_import_cpu_weights`, CUDA initialized,
  no GPU model load, no inference, and unmeasured scientific GPU numerical
  behavior. Do not call this a zero-CUDA CPU qualification.

## Acceptance at approved seams

CPU fixture requests exercise DO rejection, command/source/CPU qualification
bindings, active GPU/reservation rejection, one-use ledger allocation, untouched
native map identity, inference/benchmark/kernel rejection, immutable finish
proof and completed historical helper handling. Fixtures never execute GPU code.
Root separately qualifies the combined sources and obtains user DO before any
real driver-aware qualification. Human image quality review remains separate.
