# D9/D10 budget readiness, revision 002

Read-only follow-up for #57/#44 at canonical commit `23c468e3`. The retained
[assessment](assessment.json) binds twelve exact canonical input files. No
setup, install, package resolution, network request, model load, GPU or shared
ledger operation occurred. Previous readiness/source receipts remain immutable.

## Current limits and evidence

| Candidate | Total transfer cap, bytes | Checkpoint, bytes | Headroom after checkpoint and maximum 128 MiB source archive | Artifact cap |
|---|---:|---:|---:|---:|
| D9 | 2,263,924,404 | 116,440,756 | 2,013,265,920 (1.875 GiB) | 5 GiB |
| D10 | 2,263,927,711 | 116,444,063 | 2,013,265,920 (1.875 GiB) | 5 GiB |

The exact pinned runtime is Python 3.11, Torch **2.1.1+cu121**, Torchvision
**0.16.1+cu121**, NumPy **1.24.0** and the unchanged approved video recipe.
Xformers is absent; all three native attention fallback files must be bound.
Other direct requirements are partly unpinned. Existing local evidence contains
no resolved wheel closure or transfer sizes for this exact runtime. Other CUDA
versions are not compatible evidence for its allowance. The old cache snapshot
is historical and provides no present cache-reuse credit.

Each candidate retains 256 maps: 60 anchors plus four 50-frame clips minus four
shared check anchors. Two float32 planes and one bool plane at 960×540 give
**1,194,393,600 bytes (1.112 GiB)** of uncompressed map arrays, before NPZ headers
and compression overhead. This arithmetic does not forecast actual compressed
sizes. Artifact admission must include the complete installed runtime, retained
package cache, source archive and extraction, checkpoint, immutable captures,
clips, previews and diagnostics, including temporary peak growth. It cannot be
based on map arrays alone.

Inference consumes 4,500 distinct context frames across 60 camera/role
sequences. The approved 32-frame/10-overlap schedule has five fit windows and
three check windows per camera: 240 windows and 7,680 window input positions,
including overlap and padding. It does not process only the displayed maps.
The existing CPU 3,600 s, setup 2,400 s, GPU 12,000 s and one-attempt bounds are
unchanged.

## Decision and prerequisite order

**No numeric budget increase is proposed.** The evidence does not establish
that either existing cap fits, and does not justify a particular replacement.
The previous five-candidate 6 GiB scenario exceeded the historical global
caps; it cannot authorize these video runs. Root must obtain the following
before consuming either setup attempt:

1. Obtain a bounded, metered dependency metadata resolution for the exact
   recipe. This is a new preparation operation, not performed here. Retain
   the complete lock, exact compatible wheel URLs/hashes/sizes, metadata
   transfer accounting, and verified current reusable files. Respect any
   unresolved host-access denial; this packet grants no network permission.
2. Forecast unique new transfer bytes, including checkpoint/source and any
   retry/metadata margin, and installed/cache/archive/temporary peak artifact
   growth. D9 and D10 have separate isolated setup environments; do not assume
   that installing D9 makes D10's private cache or environment free.
3. Reconcile those forecasts with **current** measured global usage and
   outstanding allocations. Global download 110 GiB/artifact 210 GiB remain
   hard caps. If a candidate cap is insufficient, create a reviewed replacement
   proposal with exact candidate hashes and obtain approval before dispatch.
   Do not change DO001 or overwrite earlier receipts.
4. Refresh independent canonical source review, qualify combined sources and
   recheck ownership, active reservations, budgets and unused attempt slots.
   Run the stock setup dispatcher once per candidate, serially under root.
5. Verify acquired pinned native source/checkpoint and installed inventory;
   execute the retained CPU capture under a reviewed metered syscall wrapper
   that blocks network and CUDA, enforces disk/time bounds and confirms cleanup.
   Obtain independent commercial assessment of the exact full dependency
   inventory, including native inference and publication tools.
6. Refresh post-setup source review binding identical nonempty `source_archive`
   and `source_files`, then run retained CPU finalization. Admit with the **full
   qualification.json**, not its runtime receipt. Dispatch with explicit
   immutable `--source-review`, rechecking unchanged profile/assets/approval.
7. Root runs one admitted native GPU attempt at a time, retaining failures and
   cleanup. D9 remains relative. D10 requires unchanged metric fit/check gates;
   any qualitative-only authority must be separately evidenced.

## Commands for root, after prerequisites pass

Use the explicit approved interpreter. These are templates, not executions:

```bash
<interpreter> -B scripts/basketball_vipe_video_setup_dispatch.py \
  --candidate D9 --source-review <fresh-pre-setup-source-review>
# Repeat for D10 only after its own live admission checks.

# Run producer through the reviewed root syscall/metering wrapper:
<interpreter> -B docs/research/vipe-alternatives/plan031-execution/video-cpu-method-001/producer.py capture \
  --root <canonical-checkout> --candidate D9 \
  --setup <setup-result> --setup-request <setup-request> \
  --setup-dispatch <setup-dispatch> --output <fresh-capture-dir> \
  --seconds <approved-bound-at-most-180> --artifact-bytes <approved-capture-bound>

<interpreter> -B docs/research/vipe-alternatives/plan031-execution/video-cpu-method-001/producer.py finalize \
  --root <canonical-checkout> --candidate D9 --capture <capture-json> \
  --commercial-assessment <exact-installed-closure-assessment> \
  --source-review <fresh-post-setup-source-review> --output <fresh-qualification-dir>

<interpreter> -B scripts/basketball_vipe_video_actual_dispatch.py \
  --candidate D9 --admission <full-admission-result> --context <actual-context> \
  --source-review <same-post-setup-source-review>
```

D10 substitutes its candidate/evidence and supplies `--qualitative-admission`
only with valid separate authority. Source/qualification/admission preparation
must bind the complete qualification bundle before the last command.

Validation: exact bytes compared with canonical checkout for all twelve inputs;
approved allocation arithmetic and workload formulas checked without importing
NumPy, Torch or any native package. Measured evidence-construction CPU wall time
is recorded in `assessment.json`; worktree creation and human/agent reasoning
are outside that scope. No issue was closed. #57 remains blocked on the exact
closure and actual admitted execution evidence.
