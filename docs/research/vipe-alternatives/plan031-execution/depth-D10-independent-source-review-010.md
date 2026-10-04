# D10 source010 independent review

Canonical HEAD: `d7f3b2177227759abe7bb0508c795480ede2ad86`.
Previous passing review: source009 at `c3b1f2f4`. Seven D10 helper files changed
since source009 (`ledger.py`, `depth_admission.py`, `depth_map_allowance.py`,
`depth_recovery_lineage.py`, `video_depth.py`, `basketball_vipe_video_actual_dispatch.py`,
`basketball_vipe_video_publish.py`); the D10 helper list itself, 17 supplements,
the 37 acquired native source files and the native archive are unchanged.

Two independent read-only review agents examined
`git diff c3b1f2f4...d7f3b217` over those files plus `depth_d9_continuation.py`
and its tests, without running tests, models, GPU or ledger writes.

## Standards

PASS for D10. No hard violations (the repository documents no code-style rules
beyond AGENTS.md). Judgement-call smells are D9-specific: duplicated dispatch
closures, D9 special cases across five modules, hard-coded grant identity, a
library-to-script import and an unguarded `state['monotonic_start']` read in the
D9 continuation finish branch. Explicit finding: **no behaviour change on the D10
path** — every new branch is gated on candidate D9 or job `plan069-D9-maps-001`,
and new keyword arguments (`events=None`, `executable_record=None`) default to the
previous behaviour. `check_slot_byte_budget` now reuses its first event read
instead of rereading the ledger; this applies to all candidates and is read-only.

## Spec

PASS for D10. Explicit findings: the D10 maps path is unchanged, and no existing
admission or ledger guard is weakened. `Ledger.note` refuses the new protected
event names (tighter). D9-only findings retained for the separate D9 continuation:
fixture CPU captures are not structurally rejected by the continuation validator,
and later-phase admission freshness uses the stored sample time.

## CPU coverage

Passing full CPU capture018 (2,017 unittest cases with 22 skips, 22 pytest tests,
1,070.1 seconds, unchanged HEAD/source/environment bytes, confirmed cleanup)
covers all 66 current repository helper/supplement records at this HEAD. The
external hash-only tracer `/usr/bin/strace` is outside the tracked-file capture;
its bytes are verified unchanged from source009, where capture016 bound it. It was charged once
to D10 at ledger sequence 858. It qualifies CPU tests only; native runtime and
model qualification remain separate.

This review binds the existing D10 DO and grants no new authority.
