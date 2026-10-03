# D8 and D11 readiness after resume

This is CPU preparation, not authorization, installation or successful native inference.
No setup attempt, asset transfer, GPU use or live-ledger write occurred in this preparation.

## D11

The reviewed model/source identities remain Marigold V2 Log-stage2 with its pinned
Qwen base. Their source and weight cards declare Apache-2.0; the installed
dependency closure still requires a separate commercial assessment. Output-specific
restrictions were not identified in those model/source terms. This finding does
not qualify dependencies, CUDA drivers or redistribution.

The dedicated worker now saves relative-log arrays under `relative`, matching the
shared clip reader. Correction `e88c6537` is integrated in the retained checkout as
`a90de456`. The source-review input captures the current canonical integration
paths, source hashes, native profile and retained Python/uv recipe. Its status is
`awaiting_independent_review`: it is deliberately not an admissible passing receipt.
The independent reviewer must rehash those sources and produce the dispatcher’s
required `depth-D11-source-review-001.json` under the run’s documentation directory.
Any source changes require a new review snapshot.

The isolated recipe selects Python 3.11, Torch 2.10.0/cu128 and torchvision 0.25.0,
plus the native Marigold pins. The shared E5 runtime is only a Python seed; it is
not the D11 inference environment. The exact approved asset inventory totals
42,988,352,806 bytes. The remaining package allowance is **8 GiB**, not 2 GiB.
Read-only cache estimates put direct/core uncached expanded data near 3.45 GB,
within that allowance; exact cp311 Torch size and transitive resolver choices
remain unknown. This is not proof that the closure fits.

Before setup: independent current source review, resolved wheel-host access,
fresh global/candidate storage and time bounds, and no active shared reservation
or GPU owner. The root coordinates the one approved setup attempt. During setup:
metered hash-locked installation, exact assets/source-manifest checks, offline
package qualification and retained runtime receipts. Before inference: independent
installed-dependency/commercial evidence, exact model/runtime qualification and
fresh admission/ledger checks. Native quantized loading, peak memory and restored
prediction shape remain unqualified; no CUDA qualification or output-quality claim
is made here.

CPU verification: 11 targeted tests passed in 38.814 seconds, covering native
package/recipe checks, D11 map validation and real shared clip publication. The
first command omitted `tests` from PYTHONPATH and had two import errors; the
corrected `PYTHONPATH=scripts:tests` command passed. Host Python without NumPy
could not construct the snapshot; the explicit Roma interpreter did. Neither
failure consumed a setup/GPU attempt.

## D8

The canonical Torch 2.4.1/cu124 cp311 wheel link is the previously reported
`download-r2.pytorch.org` URL. Its HEAD request returned HTTP 403 outside the
sandbox, including the root’s authorized retry after the new allow rule.
Affected network work is stopped; no setup attempt was consumed. Access must be
resolved before setup. No mirror, alternate wheel or unmetered install is selected.

D8’s package allowance is 2 GiB. Cached Torch 2.5.1 is incompatible with the
native Torch ceiling and cannot substitute for 2.4.1. A cached Torch proxy plus
exact Triton 3.0 and reference NCCL data exceeds that allowance, suggesting a
storage blocker; the native Torch wheel size/dependency metadata are still
unknown, so this is not an exact cap-failure proof. The cache preflight JSON
preserves the measured sizes, metadata-only probes and limits of these estimates.
