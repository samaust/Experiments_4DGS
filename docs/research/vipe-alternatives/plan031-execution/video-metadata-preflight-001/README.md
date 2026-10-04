# D9/D10 bounded metadata preflight

Continuation of `video-budget-readiness-002`. No setup allocation or native
attempt was consumed. No wheel, model, install or GPU operation was performed.

## Retrieved primary metadata

The approved PyTorch cu121 index pages identify these exact Python 3.11 Linux
wheels and SHA256 digests; the index supplies no sizes:

- `torch-2.1.1+cu121-cp311-cp311-linux_x86_64.whl`:
  `83bfe1134dfa8ab86553c15da5dffa190a86d822afafe8ea6de1169c10d971aa`
- `torchvision-0.16.1+cu121-cp311-cp311-linux_x86_64.whl`:
  `b4eec1d9c04eb036b4e72aea5f43ae33c06414da9d36391bd04ffd31ad82fba9`

PyPI torch 2.1.1 release JSON and twelve exact Linux CUDA/Triton dependency
release JSONs were retrieved. The retained reference records list wheel URLs,
release sizes, SHA256 digests, dependency declarations and self-reported license
metadata. They are primary release metadata, not a completed commercial audit.
The public PyPI torch wheel is **not** the approved `+cu121` wheel. Its package
metadata does not establish equivalence to that wheel's dependency closure.

## Access blocker

The exact index-selected URL is:

`https://download-r2.pytorch.org/whl/cu121/torch-2.1.1%2Bcu121-cp311-cp311-linux_x86_64.whl`

A GET with `Range: bytes=-65536`, timeout 20 seconds and a strict 65,536-byte
response limit failed with **HTTP 403: Forbidden** inside the sandbox and on
its one outside-sandbox retry using existing `python3` approval. The failed
operation is retained in [range-command.py](range-command.py); failure records
retain exact URL/error/measured time. The two invocations differed only in
failure evidence filename and sandbox execution permission.

HTTP 403 for this operation is confirmed. Whether the denial comes from host
policy or the remote service is unknown. Existing execution approval did not
resolve it. No alternative domain, URL, cache, HTTP method or runtime was used
to evade the denial. Exact wheel metadata access is stopped pending resolution.

Suggested user clarification for root: **Can you resolve bounded Range GET
access to the exact URL above, or provide its trusted wheel METADATA and total
Content-Length with provenance?** Neither a browser's successful full GET nor a
changed allow rule alone proves this bounded request will succeed. Retain the
approved runtime until exact qualification evidence is available.

## Budget result

The public torch reference's twelve Linux CUDA/Triton wheels total
**1,978,278,957 bytes**. Adding its public PyPI torch wheel (670,196,704 bytes)
gives **2,648,475,661 bytes**, which exceeds candidate dependency/other-transfer
headroom of 2,013,265,920 bytes by **635,209,741 bytes**, before Torchvision,
NumPy, OpenCV, other dependencies or metadata.

This is a **conditional reference warning**, not a proven minimum for the
approved cu121 closure. Exact approved core wheel sizes and METADATA remain
inaccessible, unpinned direct packages are unresolved and installed/temporary
storage forecasts are incomplete. No numeric budget proposal or concrete
whole-slot forecast is justified yet. Do not consume either setup attempt or
change approvals based on this packet.

## Accounting and verification

- Successful response bodies: **237,960 bytes** of metadata/index HTML.
- Per-response limits: 1 MiB release JSON; 2 MiB index HTML. CUDA release JSON
  total was limited to 16 MiB. No artifact body was received for failed Range
  requests; HTTP error bodies were not read.
- Measured operation elapsed: see `assessment.json`; this includes network wall
  time and evidence publication, excludes reasoning/worktree creation.
- Root alone charges the shared ledger. This packet writes none.

Hash validation and aggregate arithmetic are retained in `validation.json`.
Raw release/index records are preserved under `evidence/`. No source code or
budget enforcement changed, no issue was closed, and #57 remains incomplete.
