# Final retained-evidence audit assessment

The [first audit](audit.json) hashed **1,440 processed inputs**, **640 reload PNGs**, all four final models (including ATGS’s 11 components), 24 dense initialization clouds, source/configuration records and installed indexed binaries. All those required file checks passed. No current source discrepancy was found.

The first invocation returned 1: its two stage predicates wrongly required the literal offline wrapper in FreeTimeGS/ATGS command arguments. Both renderers call `restrict_network` internally before model loading; their saved IPv4/IPv6 isolation probes passed. The corrected production predicate and focused tests establish completed commands separately from isolation. [The targeted recheck](audit-02.json) supersedes exactly those two failures; it retains the original report and embeds its reproducible stdlib-only recheck script.

Effective result: **{'passed': 6701, 'unavailable': 2}**. Two unavailable items remain: historical STG Lite/Full native-binary attestations were never recorded. This cannot establish a fully attested historical runtime or a new reload. No source restoration, dependency installation, training, numerical evaluation or GPU execution occurred.

All 60 held-out times and 20 common fixed-time poses agree across saved metadata; all a/b PNG bytes agree. FreeTimeGS/ATGS historical raw-float hashes also agree, but raw arrays were not recomputed. STG establishes PNG equality only. Model bytes and loader requirements support complete retained state, not a newly exercised restore.

Saved metric means and aggregate deltas reconcile at 1e-9 tolerance; benchmark FPS equals 100/sum(duration), with 10 warmups and 100 samples at camera 0015/frame 4150, 1890×1061. Loading, camera setup, image saving and encoding are excluded. The ledger remains 22,523.417254 charged seconds, zero overruns and no live reservations. Final continuation wall time, sampled device baseline/peak and allocator peaks remain distinct in the machine report. Source-video hashes are recorded provenance with presence checks only; source videos were not rehashed.

The [inspection report](inspection.md), [offline image selector](inspection.html) and [workflow guide](../../selfcap-workflow.md) interpret this retained evidence. Basketball and unsupported-method blockers remain; this milestone does not attain the two-profile objective.
