# Job-ledger cap increase study

## Scope and result

This is a read-only study of raising the existing per-attempt job-ledger limit. It does not amend Plan049, authorize source changes, or clear tests/diagnostics. The current 8 MiB cap is not explained by a design rationale in the reviewed plan text; it is an existing source constant that Plan049/Correction015 preserve. A higher finite cap could accommodate a numerically bounded journal that exceeds 8 MiB, but it cannot fix the current closure failure by itself: the candidate still lacks validated maximum command/environment descriptor lengths and a finite whole-journal byte bound. Any finite cap still needs those bounds and a fail-closed pre-create reservation check.

## Current behavior and cost

`scripts/vipe_benchmark/s1_helper_session.py` defines `JOB_LEDGER_LIMIT = 8 * 1024 * 1024`. `_job_read` rejects empty, unterminated, or larger input; `append_job_event` reads and validates the whole current chain, serializes the next event, checks `len(raw) + len(line)` against the limit, appends and fsyncs, then reads the whole file back for exact equality. Thus the cap bounds persistent per-attempt bytes and each full-file read/readback. Raising it also raises the maximum bytes parsed and held across raw bytes, decoded rows, and append/readback buffers. Since append repeatedly rereads and parses the growing journal, a larger usable journal may increase cumulative I/O and validation work as well as peak storage/memory. No benchmark or measured ledger-size distribution was run for this study.

The existing 150 GiB artifact cap does not make this cap redundant: the job ledger is a small integrity-critical control journal whose entire contents are repeatedly parsed and whose reservations must be durably read back before child creation. The 8 MiB value appears conservative, but the repository evidence reviewed here does not establish why that exact value was selected or how close valid attempts come to it.

## What a larger cap would and would not solve

A finite increase (for example, 16 MiB) would double the allowed journal file size and the maximum bytes in a full read/readback. The resulting peak Python memory could be several multiples of that limit because raw input, decoded rows, the new serialized line, and readback may coexist. An exact multiplier is not established by this static review. The larger cap would help only if a reviewed worst-case complete journal is greater than 8 MiB and no greater than the new value.

It would not:

- bound argv or environment descriptor sizes;
- prove which generated command and environment were actually passed to the OS creator;
- resolve the addendum013 conflict between repository-root paths allowed in §1 and every path slot being required under the attempt-local root in §2;
- establish that selected event counts or serialized sizes fit any finite cap; or
- authorize raising the cap under current Plan049/Correction015 wording.

The environment itself need not be copied into the journal: addendum013 §3 asks for a digest plus entry count and encoded-byte length. But the implementation still has to bound the effective environment size and ensure the same captured snapshot reaches the creator. The current audit finds no validated maximum. Likewise, rendered argv/inline code needs an explicit finite domain. Rejecting a single oversized event before child creation is a useful safety rule, but it is not a proof that the authorized attempt can complete within the cap.

## Plan and implementation implications

Plan049 preserves existing limits and Correction015 addendum013 explicitly requires proving the complete journal fits the unchanged 8 MiB limit “without raising it.” The nine-path correction scope does not include `s1_helper_session.py`, where the cap and checks live. Therefore raising the cap needs a separately reviewed plan amendment that (1) states the new exact limit and why that value is sufficient, (2) preserves the existing append/readback-before-create and failure-accounting behavior, (3) gives a complete numeric per-attempt journal bound including original events and new descriptors, and (4) assesses peak memory and repeated-read cost against current resource constraints. Only after independent plan review and explicit user authorization could implementation update the constant and any corresponding validation/fixture expectations; exact source review and fresh preflight would still precede diagnostics.

## Recommendation

Do not raise the cap yet. First bound command templates, slot domains, event counts, and the full environment descriptor numerically. Then compare that measured/proven maximum with 8 MiB. If it fits, retain the existing cap. If it does not, propose the smallest finite cap above the proven maximum with explicit headroom, and review its memory and I/O consequences. If inputs cannot be given finite bounds, a larger cap only postpones rejection and does not satisfy the ledger-integrity requirement.

## Evidence hashes

| Input | SHA-256 |
| --- | --- |
| `plans/plan_049.md` | `89d1f634ad2407b02558ff9c030d4a4f12f8f4ab010c93e2cf532876564afe7e` |
| `scripts/vipe_benchmark/s1_helper_session.py` | `c3326fe0c738e0180b42289f03c52ff8586e9eef86fd242dc3ea3a013a72e106` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-source-scope-addendum-013.md` | `14398e0974258104018a366f5d9d9a653e69c9efb894baefe73b498542b1c78c` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-002.md` | `bff30fce1eedaf7300ee7a43f9597ca7a4e47fc97230ad8914892de318707963` |
| `docs/resolve-blocker/plan031-progress-20260922/plan049-correction-015-transitive-source-closure-audit-002-independent-review.md` | `9d2b900e856e9ff00d0b0257b782adc18dc7a00a21e944914ce5b2a62ccb40b2` |
