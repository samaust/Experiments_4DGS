# D9 source009 independent review

Canonical HEAD: `980a1718408a4b4b00226a4867517a6bb8dd2678` (source bytes identical
to `d7f3b217`). Previous passing review: source008 at `afd0c096`. The D9 helper
closure and supplements did not change between `afd0c096` and `c3b1f2f4`, so the
complete D9 change since source008 is `c3b1f2f4...d7f3b217`: eight helpers
(`ledger.py`, `depth_admission.py`, `depth_map_allowance.py`,
`depth_recovery_lineage.py`, `video_depth.py`, `basketball_vipe_video_actual_dispatch.py`,
`basketball_vipe_video_publish.py`) plus the new `depth_d9_continuation.py`.
Native archive, 37 native files and accepted recovery002 setup are unchanged.

Two independent read-only review agents examined that diff against the grant851
continuation contract (`docs/specs/plan031-execution/depth-D9-unstarted-continuation-review-001.md`)
and issues #44/#57.

## Standards — PASS (no hard violations)

Judgement-call smells: duplicated dispatch closures and evidence dictionaries,
D9 special cases across five modules, hard-coded grant identity, a library module
importing a top-level script, and deferred circular imports. One reported risk,
an unguarded `state['monotonic_start']` read in the continued finish branch, was
checked by root and **does not apply**: both `reserve` (ledger.py:285) and
`resume_checkpoint` (ledger.py:793) always write `monotonic_start`.

## Spec — PASS (no existing guard weakened)

Duplicate continuation, continuation without fresh evidence and reserve after
30 seconds are each blocked; single-attempt and publication rules hold.
Disposition of remaining findings:

- *Fixture CPU captures are not structurally rejected.* Accepted as a residual
  risk: any marker the validator could check is equally writable by a fixture.
  The production continuation will bind only root-run actual captures; root
  verifies them before creating the event.
- *Validation time is charged only on complete finish; later phases use the
  stored admission sample time.* Accepted; the 30-second reserve window bounds
  freshness and failed finishes still charge measured elapsed time.
- *D6 qualification004 allocation code is outside this contract.* It requires its
  own explicit DO; nothing here authorizes it.

## CPU coverage

Passing full CPU capture018 at `d7f3b217` (2,017 unittest cases, 22 skips,
22 pytest tests, 1,070.1 s, unchanged bytes, confirmed cleanup) covers all D9
repository records, which are byte-identical at this HEAD. The external
`/usr/bin/strace` supplement is unchanged and bound by capture016. CPU tests do
not qualify native runtime or models.

This review grants no execution authority.
