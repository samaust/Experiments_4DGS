# Prospective PyPI CUDA 13 video runtime budget

**REVIEW only.** This proposal concerns the distinct official PyPI distributions
Torch **2.14.1** / Torchvision **0.29.1**, with Python 3.11 Linux x86_64 wheels.
It does not approve a distribution change, budget increase, setup or native run.
The cu130 index wheel `.metadata` HTTP403 remains unresolved; no retry or alternate
route for that operation was used. Actual cu130 wheel GET was not tested.

## Exact prospective release closure

Primary PyPI release JSON and **49 wheel-specific METADATA files** verify the
proposed dependency constraints, platform/Python requirements and requested
extras. CUDA13.0 provenance comes from Torch's METADATA selecting
`cuda-toolkit[...] ==13.0.3`, CUDA13 bindings and cu13 runtime libraries. All
applicable wheel dependencies resolve to the selected versions. CUDA toolkit's
release version13.0.3 and wheel version13.0.3.0 are equal under PEP440; the
normalization is retained. Versions of other dependencies are deliberately
chosen compatible pins, including OpenCV4.11.0.86 and ContourPy1.3.2 for NumPy1.24
and Python3.11. They are not claimed to be the latest releases.

[closure.json](closure.json) lists all49 wheel URLs, bytes, SHA256 digests,
primary release metadata and self-reported license fields.
[wheel-metadata-verification.json](wheel-metadata-verification.json) binds each
wheel-specific METADATA file and verifies all applicable dependencies. Full
wheel digests are publisher declarations; actual artifact hash verification,
installed runtime/native compatibility and commercial clearance remain pending.
`prospective-constraints.txt` is a proposed version lock, not an acquired or
installed hash lock. These files do not change the executable v2 recipe.

## Measured archive size forecast

Bounded Range GETs read **only ZIP end/central-directory metadata** for all49
wheels, totaling **1,780,448 bytes**. No complete wheel was received, extracted
or installed. Exact responses bind wheel URL, total size and returned range;
retained directory bytes are independently hashed. Their file-size forecasts
remain publisher metadata until actual acquisition verifies the wheel digest.

| Quantity | Bytes | Meaning |
|---|---:|---|
| Selected compressed wheels | 3,168,800,452 | Actual new transfers if no cache exists |
| Expanded member payloads | 6,033,660,805 | Retained-cache logical footprint |
| Expanded members rounded to4096-byte blocks | 6,078,496,768 | Conservative cache artifact forecast |
| Members | 19,764 | All wheel archive entries |
| Largest compressed wheel | 554,581,699 | Conservative additional inflight storage |

Existing accounting charges `max(metered package transfer, retained expanded
cache)` plus direct acquisitions. Therefore a package allowance must cover
roughly6.03GB of expanded cache, rather than only3.17GB of compressed transfers.
The existing2GiB allowance and5GiB artifact cap are insufficient for this
specific proposed closure even before model outputs.

## Proposed per-candidate bounds

| Candidate | New dependency allowance | Total download/accounting cap | Artifact cap | Forecast artifact peak |
|---|---:|---:|---:|---:|
| D9 | 6GiB | 6,558,891,700 bytes | 9GiB | 9,525,165,431 bytes |
| D10 | 6GiB | 6,558,895,007 bytes | 9GiB | 9,525,168,738 bytes |

These changes add exactly4GiB to each existing total download cap and artifact
cap. They retain one attempt, CPU3,600s, setup2,400s, GPU12,000s, device21GiB and
all scientific/model/source/weight settings. Global110GiB/210GiB caps remain hard.
No prior consumption resets. No cache reuse credit is assumed.

The artifact forecast adds fully expanded cache, largest compressed inflight
wheel, source archive128MiB, guarded extracted-source maximum1GiB, checkpoint,
256 uncompressed map arrays, map/archive overhead64MiB, clips64MiB, previews100MiB
and supporting evidence128MiB. Complete components and headroom are in
[proposal.json](proposal.json). Clip/preview/evidence reserves are engineering
reserves, not established producer upper bounds; live whole-slot guards must
stop growth before the approved cap. No successful completion is guaranteed
merely by this forecast.

The forecast requires the existing UV hardlink mode on one filesystem so the
installed environment shares cache inodes. Root must verify this before setup
and inspect actual retained storage. Copy fallback or unexpectedly larger
outputs can exhaust9GiB; stop and retain evidence rather than assume free disk,
prune cache or exceed the cap. Python seed is already retained and pinned; no
new interpreter download is proposed.

## Root approval and execution prerequisites

1. Obtain explicit user choice of the distinct PyPI distribution. Do not use
   unsuffixed package metadata as evidence for indexed `+cu130` wheel sizes.
2. Obtain explicit approval of6GiB/9GiB bounds. Fresh root-owned global usage,
   outstanding allocations and ownership must be reconciled first. This packet
   does not guarantee both remaining full allocations fit concurrently.
3. Create a **new** PyPI recipe/profile, exact reviewed candidate proposal hashes
   and scoped DO. Existing authority validators must explicitly recognize that
   versioned distribution/budget amendment; do not relax checks or overwrite
   v1/v2 recipes, approvals, source receipts or this REVIEW packet.
4. Integrate, review and qualify combined sources; refresh independent source
   receipts. Keep all attempt counts and scientific gates unchanged.
5. Root performs the one admitted setup per candidate serially, freezes exact
   hashes/installed closure and obtains independent commercial/native runtime
   qualification before any GPU dispatch. D10 retains fit/check gates; D9 is
   relative. Human review and final renders remain separate unfinished work.

## Evidence and accounting

Evidence is retained under `evidence/`:49 release JSONs,49 METADATA files and
98 bounded ZIP response bodies with their response records. Self-reported license
fields do not constitute commercial permission clearance.

The initial draft resolver had three local errors: project JSON exceeded its
2MiB cap; the preferred ContourPy release lacked a compatible wheel; and extra
markers were re-filtered incorrectly. Successful metadata writes were preserved
and reused after relevant fixes. A fourth validation corrected PEP440 version
normalization. No failed host access was retried by these corrections.

All successful/partial response reads in this cu130 preparation total
**6,808,715 bytes**, below the16MiB research cap. Failed project JSON read used
2,097,153 bytes (including its one-byte over-limit sentinel) and is included.
No model transfers or setup reservations occurred. Successful final-phase elapsed
and failed normalization elapsed are recorded. The three failed draft resolver
phases lack terminal elapsed captures and are explicitly disclosed; root must
account them conservatively once. No shared ledger was modified by this agent.

Independent metadata/forecast review and hash/arithmetic validation are recorded
separately. Actual installed compatibility, global admission and issue completion
remain pending. #44/#57 stay open.

The three retained Python files are **historical producers**, not directly
runnable tools in this published folder. Their original layout was
`.local/video-cu130-metadata-001/` within the preparation worktree, with retained
`pypi-closure*`, `wheel-directory-metadata-001` and
`wheel-pep658-metadata-002` directories. The resolver used existing D5 package
version records only as candidate-version hints; it independently queried PyPI
and grants no reuse credit. The published packet contains the selected primary
release/metadata/directory evidence and verification results; future execution
requires a newly reviewed producer with explicit current bindings and bounds.
