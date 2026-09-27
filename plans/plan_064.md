# Plan064 — S1-3 live S1 calibration recovery (iteration 25)

## Status

Active. Implements the user-authorized S1-3 live S1 calibration recovery
(option 1; "I approve S1-3. Continue the implementation."). S1-1, S1-2 and
S1-4 are met; S1-3 is the only remaining objective criterion. This plan
repairs the bookkeeping chain and the restored environment, produces a
fail-closed authorization document that passes `validate_binding` on
first host-side admission, and defines the single host-run dispatch
protocol. No scientific source bytes change; the 78/78 source set stays
byte-identical.

## Context

- Original failure (bound in the amendment):
  `BackendError: unresolved native semantic phrase: ''` at
  `scripts/vipe_benchmark/backends.py:192` (`normalize_phrase`) via the
  GroundingDINO detector path (`stages.py:134 segment`). The semantic
  amendment `plan031-s1-s0-token-sum-v1`
  (`docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-semantic-assignment-amendment-001.json`)
  fixes the phrase mapping. Original finish event: seq 250,
  `102e7c7cc33e8a6d2b4107b69fad0ef577b36a901b59c133d99e811f36665d71`,
  cleanup confirmed, no surviving PIDs.
- Ledger baseline: 447 events, 332,437 bytes,
  sha256 `2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
  last event `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
  The ledger stays byte-identical until the host run appends.
- GPU budget: 30 recorded attempts, 4,374.044 s elapsed, 0 s reserved;
  recovery cap 1 attempt / 3,600 s; cumulative ceiling 93,600 s.
- E1 qualification (component `S1` only): python 3.11.15, torch
  2.5.1+cu124, torchvision 0.20.1+cu124, numpy 1.26.4, import-only
  qualification complete with 0 forwards and no CUDA context.

## Preflight audit findings (all repaired, read-only where possible)

1. **Broken bookkeeping chain.** The status.md history after
   `s1-recovery-status-implement-017.md` (a4d82fc8) was never recorded:
   14 committed states (iterations 18–24, commits 21e3d9e … f14bfc8)
   plus the current iteration-25 PLAN update are unrecorded. Repaired by
   `s1-recovery-baseline-correction-016.json`, which extends correction-015
   (34 transitions) with 15 new `plan034-s1-bookkeeping-transition/v1`
   documents and their preserved snapshots, so the chain ends at the new
   status.md record exactly.
2. **Missing frozen baseline file.** The pinned ViPE checkout
   `/home/auss/git_repos/samaust/Tridi/vipe` (branch `tridi`, pinned
   `de50e6ab1066e32c96d32499a282ecaa2fbf2d90`) had been removed from the
   machine, breaking two of the 38 frozen preservation records
   (`vipe/priors/track_anything/detector.py`,
   `.../groundingdino/util/utils.py`). Restored by cloning the user's
   public fork `github.com/samaust/vipe` at exactly the pinned commit
   (clean tree). Verification against
   `qualification/historical-assets.json` (266 listed files): 265 exact
   sha256/bytes matches; the single missing file is the local build
   artifact `vipe_ext.cpython-314-x86_64-linux-gnu.so` (compiled, not in
   git, not in the frozen records, and not an S1 required asset — S1
   forbids the ViPE root at runtime).
3. **Missing S1 model weights.** `~/.cache` had been cleaned; all S1
   weight assets were absent. Restored from the canonical sources and
   verified byte-exact against the E1 asset records
   (`jobs/E1-setup-recovery-002/assets.json`):
   - `groundingdino_swint_ogc.pth` (693,997,677 B) from
     HuggingFace `ShilongLiu/GroundingDINO` — sha256
     `3b3ca2563c77c69f651d7bd133e97139c186df06231157a64c507099c52bc799`.
   - `sam_vit_b_01ec64.pth` (375,042,383 B) from
     `dl.fbaipublicfiles.com/segment_anything` — sha256
     `ec2df62732614e57411cdcf32a23ffdf28910380d03139ee0f4fcbe91eb8c912`.
   - `R50_DeAOTL_PRE_YTB_DAV.pth` (236,513,959 B) from the R50-DeAOTL
     PRE_YTB_DAV row of the pinned SAM-Track README
     (`Segment-and-Track-Anything` @ 99ca4bd5, Google Drive
     `1QoChMkTVxdYZ_eBlZhK2acq9KMQZccPJ`) — sha256
     `7e8a8d83310739bac02817f6bf48b6bbe2bbd7d5325722f1084088eb3aee1e06`.
   - `bert-base-uncased` snapshot at revision
     `86b5e0934494bd15c9632b12f734a8a67f723594` (5 files) from HuggingFace —
     all five sha256/bytes exact.
   `AssetBundle('S1', assets)` now passes on all nine required S1 assets.
   These are environment restorations of the exact pinned bytes the E1
   qualification already bound; they are not a configuration change.

## Artifacts (this iteration, in dependency order)

1. `plans/plan_064.md` (this document).
2. `docs/continuous-improvement/plan031-s1-recovery-20260919/status.md`
   updated to iteration 25 PLAN.
3. 14 preserved status snapshots
   (`s1-recovery-status-{plan,implement}-018…024.md`, byte-exact from git
   blobs) plus `s1-recovery-status-plan-025.md`, and 15 transition
   documents (`s1-recovery-bookkeeping-transition-{plan,implement}-018…024.json`,
   `s1-recovery-bookkeeping-transition-plan-025.json`).
4. `assessment-060-plan.json`.
5. `s1-recovery-baseline-correction-016.json` (predecessor correction-015;
   same baseline, ledger snapshot, 38 frozen records and first 34
   transitions; 49 transitions total; plan bound to this plan; review
   review-018.md; successor validation `s1-recovery-validation-017.json`).
6. `s1-recovery-validation-017.json` — the first `passed`
   `plan031-s1-recovery-validation/v2` wrapper: exact current 78-source
   set, clean `git diff --check`, `aggregate_passed` true, and the single
   bound receipt/execution pair
   `timeout-gate-063/aggregate-063-004` (timed mode, 240 s cap, 199.74 s,
   249 ok / 0 / 0, sources byte-unchanged).
7. `docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-calibration-recovery-authorization-001.json`
   — the fail-closed authorization for job
   `S1-calibration-recovery-001` (1 attempt, 3,600 s, no reconstruction,
   no reset of prior consumption, amendment approved, additional attempt
   approved), binding the 447-event ledger snapshot, the original cleaned
   failure, the E1 qualification/assets/runtime, the frozen inputs and
   annotations (policy + independent review + seq-57 annotation-amendment
   event), the historical request and its canonical sha256
   `d11f35b7023270d1a35cb07bffbafbd1a9b8b0908e4ec0ba751c81aafeca4926`,
   the semantic amendment, and this wrapper/correction/plan triple.
8. `docs/continuous-improvement/plan031-s1-recovery-20260919/s1-live-launch-gate-025.py`
   — read-only host preflight (GPU exclusivity report, E1 interpreter and
   import check, asset presence, ledger byte check, `validate_binding`
   dry run) that prints GO/NO-GO and never writes the ledger.

## Host dispatch protocol (single execution)

- **No in-sandbox run.** The lifecycle tolerates at most one `admitted`
  admission after the snapshot; a sandbox preflight that writes
  admission+registration would make the host re-run raise
  `S1 lifecycle unrelated/duplicate admission`. Admission, registration
  and dispatch happen once, on the host, in one process.
- **Exclusivity precondition.** `common_admission` blocks while any GPU
  compute PID exists; the supervisor raises `exclusive GPU access lost`
  for foreign PIDs mid-run. The llama.cpp router serving this session
  holds the GPU. Before the host run the user must ensure the GPU is
  exclusive (stop the router, or run the session model on CPU), and the
  launch gate reports the current compute-apps table as evidence.
- **Command (host, repository root):**
  ```
  PYTHONPATH=scripts python -B -m basketball_vipe_benchmark \
    --run-id plan031-20260913T032700Z component-recovery \
    --job S1-calibration-recovery-001 \
    --authorization docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-calibration-recovery-authorization-001.json
  ```
- **Session model switch.** Switch the pi session to
  `qwen2.5-7b-instruct-q4_k_m` before the GPU run (frees ~16 GB so the 7B
  session model and the S1 worker fit under the 22 GiB peak device limit)
  and back to `Qwen3.8-27B-UD-Q4_K_M` after. If the router must stay up,
  the 7B model must be CPU-placed or the server stopped; the gate
  enforces the final state either way.
- **Failure handling.** One bounded attempt; on failure the run records a
  cleaned-up failure with first-result qualification and preserved raw
  evidence (receipt plus detailed run artifacts), and the allocation is
  terminal. No second S1 calibration allocation exists in this document.

## Explicitly not done

- No reconstruction (not authorized; `reconstruction_attempts=0`).
- No new environments, no new downloads, no extra smoke jobs, no setup
  attempts (`new_setup_attempts=0`, `new_downloads=0`,
  `extra_smoke_jobs=0`).
- No changes to the frozen configuration
  (`configs/vipe-alternatives/benchmark-v1.json`, sha256
  `298e0a3a6c6c30b92dbfd7c8fa55a3dfbca1dff801a67c0830cf47db0bd9f823`) or
  to any scientific source; the 78/78 source set remains byte-identical.
- No mutation of prior failures, aggregates, reports or the 447-event
  ledger prefix.

## Stop point

After the host run: verify the appended ledger events (admission,
registration, reserve, finish or cleaned failure), the compact receipt
and the detailed artifacts, update the status to the observed outcome,
record the review, and commit. The objective is met when the bounded S1
calibration recovery completes or records a cleaned-up failure with
first-result qualification and preserved raw evidence.
