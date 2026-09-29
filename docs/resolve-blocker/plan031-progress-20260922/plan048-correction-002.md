# Plan048 correction 002 — address independent source-predicted blockers

## Evidence and decision

The distinct Validate report [validate-048-report-001.md](validate-048-report-001.md) and machine assessment identify V1–V7. Main accepts the source-predicted defects as concrete correction targets; these are not claimed as runtime failures. The partial source is not launch-ready, and no focused or aggregate slot has been consumed.

## Required correction scope

Within Plan048's existing files, gates and preservation rules, the same implementer must address the following before any launch:

1. **V1 deadline boundaries:** make the allowed S1-specific serializers, RGB loader, parent/leaf file reads, decode/hash/parse operations, context setup and directory sync honor original W/C at each inner fallible operation. Recheck W immediately after the final fresh authority/ownership audit and before `Popen`. Preserve close/retirement behavior and the original primary error. No edits to frozen generic `files.py`, capture/runner/contract/cache or `s1_clock.py`.
2. **V2 historical checks:** when there is no live operation deadline, historical file verification must not sample `time.monotonic`; keep live W enforcement when an original deadline exists. Preserve the historical-authority test's exact no-live-clock contract.
3. **V5 optional successor:** repair only the fixture/construction and any source path proven incorrect so a genuinely trusted intended-successor uncertainty reaches the recovery logic. Do not downgrade an actual integrity failure or forge retained authority. Add the missing current-path/next-generation binding check if required by the Plan048 v2 contract.
4. **V3/V4/V6/V7 remaining relevance:** finish real acknowledged-fallback after-publication aliases; detached/fallback state; send-after-freeze; named creation/retirement paths; real numerical invalid, over-cap uncached and two-numerical-pair eviction cases; and complete bounded child/owner trace correlation, no-post-C truncation/primary preservation. If a full named case cannot be built in remaining limits, record it as unmet; do not rename or relabel a generic control.

Keep the sole previously approved late `elapsed==91` assertion correction from correction001. Preserve every other existing assertion, method and callback, the exact plan bounds, the16 new callbacks, all510/340/170 guards, all42 scenarios and six scripts. No stubs, smaller fixtures, skipped suites, timeout changes or cached authority.

## Allocation and checks

No fresh authorization or launch is added. Maximum correction time is **910 seconds** total: the approximately211 seconds of unused Plan048 implementation preparation plus the700-second correction reservation. Main starts/reconciles a correction clock and stops before this ceiling. The validator's first pass consumed542.937 seconds of its800-second reservation; at most257.063 seconds remains for independent recheck. The fresh focused allowance remains at most4×120 seconds; first aggregate optional300 seconds; final300-second aggregate remains reserved. The overall≤7,200-second authorization, source/test cutoff≤6,000 seconds, CPU≤8 and final≥1,200-second reserve remain binding. Main launches all checks only after correction handoff and an admission calculation; the implementer launches none.

Deliver an append-only correction source/assertion map, file/hash snapshot, case relevance map, implementation addendum, exact unlaunched commands and an updated remaining-budget record. No commit until independently validated acceptance. If the corrections do not fit910 seconds, or remaining gates cannot fit all independent validation and final aggregate reservations, stop incomplete before launching speculative tests and report exact residual criteria.

Main authorizes this correction as necessary to continue the already approved Plan048 blocker resolution. It narrows no criterion and does not accept any source-predicted finding without independent evidence.
