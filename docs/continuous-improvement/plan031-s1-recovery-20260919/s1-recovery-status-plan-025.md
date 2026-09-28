# S1 recovery status — iteration 25 PLAN: S1-3 live S1 calibration recovery authorized

## Current position

- **S1-3 authorized (option 1).** The user approved the bounded live S1
  calibration recovery: "I'm choosing option 1. I approve S1-3. Continue
  the implementation." Job `S1-calibration-recovery-001`, 1 attempt,
  3,600 GPU s, no reconstruction, no reset of prior consumption.
- **S1-1 / S1-2 / S1-4: met.** S1-2 re-met on the final source
  (aggregate-061-007 no-timeout pi; aggregate-063-004 timeout-mode gate at
  240 s cap, 199.74 s elapsed, 249 ok / 0 / 0). 78/78 sources
  byte-identical through the Plan049 chain and unchanged by this
  iteration.

## What this iteration does (Plan064)

1. **Repairs the broken bookkeeping chain** with
   `s1-recovery-baseline-correction-016.json`: correction-015's 34
   transitions extended by 15 recorded transitions (the 14 unrecorded
   committed status.md states of iterations 18–24 plus this PLAN update),
   each with preserved byte-exact snapshots, ending exactly at the new
   status.md record.
2. **Restores the environment** after machine-state loss (hash-verified,
   no scientific change):
   - pinned ViPE checkout `/home/auss/git_repos/samaust/Tridi/vipe` @
     `de50e6ab1066e32c96d32499a282ecaa2fbf2d90` (public fork clone, clean
     tree; 265/266 historical-asset files byte-exact, the missing one a
     non-restorable compiled `.so` outside the frozen records and outside
     S1's required assets);
   - the four absent S1 weight artifacts re-downloaded from canonical
     sources and verified byte-exact against the E1 asset records
     (GroundingDINO Swin-T OGC, SAM ViT-B, R50-DeAOTL PRE_YTB_DAV per the
     pinned SAM-Track README, bert-base-uncased snapshot at the pinned
     revision). `AssetBundle('S1', …)` passes on all nine required assets.
3. **Produces the fail-closed binding**: the first `passed`
   `plan031-s1-recovery-validation/v2` wrapper
   (`s1-recovery-validation-017.json`, bound to the aggregate-063-004
   receipt/execution pair) and the authorization document
   `s1-calibration-recovery-authorization-001.json` (447-event ledger
   snapshot, original cleaned failure, E1 qualification, frozen
   inputs/annotations, canonical request sha
   `d11f35b7…`). A dry-run `validate_binding` against the assembled
   documents passes end-to-end.
4. **Defines the single host-run protocol**: read-only launch gate
   (`s1-live-launch-gate-025.py`), GPU exclusivity precondition (the
   llama.cpp router must not hold the GPU during the run), no in-sandbox
   admission (the lifecycle tolerates exactly one `admitted` admission
   after the snapshot), one dispatch command on the host.

## Success-criteria position

- **S1-1**: met — additive pi-launch class; no owned-path assertion
  weakened.
- **S1-2**: met — both validation classes on the final source bytes.
- **S1-3**: in progress — binding complete, host dispatch pending
  (exclusivity precondition + user decision on router state).
- **S1-4**: met — Plan049 chain byte-identical; prior failures,
  aggregates and reports untouched; the 447-event ledger prefix stays
  byte-identical until the host run appends.

## Stop point

Host run pending. After dispatch: verify appended ledger events, the
compact receipt and detailed artifacts, record review-019, update status
to the observed outcome, and commit.
