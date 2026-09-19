# D1 readiness after E4 recovery-006 — 2026-09-19

**Verdict: ready for a future live admission check, not ready for direct stage
dispatch now.** A minimal historical-provenance repair is implemented and tested.
No admission, resume, stage, execute, setup or model/GPU job was invoked. The
present instruction authorizes review/repair only; the commands below are a
handoff, not an execution instruction or new authorization.

Evidence: [current source hashes and focused validation](d1-readiness-validation-001.json),
[ledger, budgets and preserved-file hashes](d1-readiness-evidence-001.json),
[existing proxy bundle validation](d1-readiness-proxy-check-001.json).

## Findings and repair

- `check_run()` passes with the current configuration and saved authorization.
  The immutable 33,102-byte plan remains SHA-256
  `5b2c3eec431337e720cad0dae60738b4040045d25815a790f8534e79eaa6dcd8`.
  Study/protocol hashes and allocations remain unchanged. The audio 2.11
  follow-up is recorded outside the frozen plan, whose amendment still says 2.13.
- `setup_result_record(local, 'E4')` resolves recovery-006 and verifies its
  authorization, result, runtime target, inventory, imports, dependency lock and
  build-input records. Result SHA-256 is
  `f2c95988151e276cd7a1182c989c7e6efbb8fae016e20d6c8bf14e341e996937`.
  Saved qualification reports Torch 2.13.0+cu130, torchvision 0.28.0+cu130,
  torchaudio 2.11.0+cu130, NumPy 2.1.3, xformers 0.0.35 and import-only success.
  This does not establish model inference or native CUDA compatibility.
- Common admission previously raised `changed file` for the annotation policy's
  original plan: expected `27f3f284886f1af7e19602d0b21a2494ac1c5cbab1878b8e73b25874d43db74b`,
  got the current plan hash above. Its historical authorization also changed:
  expected `8979aa131a3677d85890da2291bf0866d38e417720d159458ede84a8dc1b00cf`.
  Both exact originals were recovered from Git, with digest and size checked;
  [archive provenance](annotation-policy-parents/provenance.json) records commits
  and paths. `check_policy()` now permits exact hash-named copies only for these
  historical parent fields. Protocol, policy, proposal, review and bundle checks
  remain strict; live `check_run()` is unchanged. No old record was rewritten.
- Read-only validation of the real frozen bundle now passes: 232 images,
  112 pairs, `human_ground_truth=false`, annotation object hash
  `8385e618e8b22c5ce96a24f12e8981e9a88ab976d2e381873a2814c8d55c29d1`.
  The existing amendment permits proxy evidence, not fabricated human truth.
- Recent E4 validation receipts lack the `sources` array required by common
  admission. Validation014 has nine stale source/test records. The new
  `d1-readiness-validation-001.json` supplies verified current source records and
  21 passing focused CPU tests (11 annotation, 10 execution). It is a focused
  validation receipt, not a claim that the full implementation suite was rerun.

## Remaining gates and command safety

`require_stage_order(local, 'D1-fit', config)` passes. Read-only
`make_request(local, 'D1-fit', config)` returns no reasons: D1, role fit, frozen
input record, pinned source/snapshot assets, recovery-006 environment interpreter
and forbidden ViPE roots. It does not itself admit, resume or reserve the stage.
The camera-aware adapter uses supplied K, local-only weights, float32 invocation
and upstream autocast, checkpoint resolution bounds, bilinear restoration and
camera-z metres without another focal multiplier. First-result qualification
belongs inside the allocated fit job.

Ledger sequence 429 is the cleaned-up E4 completion. D1-fit and D1-check remain
blocked account events (309/310); R-D remains skipped (311). None has a reserve.
The unchanged resume guard accepts only unique, unconsumed, accounted slots and
rejects consumed attempts. E4 success does not automatically reopen these slots.
Existing authorization is recorded in `resume-004.json`; do not manufacture a
new user statement or reopen unrelated slots. No resume transition was recorded
by this review.

Future main-agent commands, **not run here**, from the repository root:

```bash
PYTHONDONTWRITEBYTECODE=1 .local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z admit --validation docs/research/vipe-alternatives/plan031-20260913T032700Z/d1-readiness-validation-001.json
```

This is the next reasonable live check when execution continuation is active.
It probes GPU/resources and writes an admission receipt plus ledger event; it is
not read-only. Common admission checks annotations, input/runtime provenance,
bound validation, exclusive GPU access, device memory, storage and transfers.
Those live resource checks were not performed here. Use the repository's single
permission-retry rule if needed; do not bypass a denial.

Before any stage dispatch, the main agent must record the scoped resume for
`D1-fit R-D D1-check` using the exact existing authorization text from
`resume-004.json` via the controller's `resume --authorization ... --jobs ...`
interface. This review deliberately does not issue that state-changing command.
Once live admission and scoped resume succeed, the D1 command is:

```bash
PYTHONDONTWRITEBYTECODE=1 .local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z stage --job D1-fit --validation docs/research/vipe-alternatives/plan031-20260913T032700Z/d1-readiness-validation-001.json
```

That command is **not safe to launch now**: slots are still accounted and live
admission is unverified. Actual dispatch requires host PID visibility outside
the sandbox, one exclusive GPU process group and the existing supervisor.
After a complete fit source, R-D must run immediately (camera 1/frame 100,
600 seconds); D1-check is conditional on a passing fit (frame 175, 900 seconds).
Fit allows 900 seconds and 30 training-camera outputs, including qualification
and cleanup. A fit worker completing is distinct from its scale gates passing.

Do not use `execute` to continue: it returns the already-completed report.
Aggregate and report finished at sequences 400/404; neither may be rerun or
rewritten. Frozen finalists and C1–C3 remain as recorded. New isolated D1 evidence
would not retrospectively update that report or authorize another scoring pass.

## Scientific acceptance and limits

All 30 training cameras must remain in the scale evaluation. Preserve sparse
support ≥3 cameras/≥1° parallax, clearance ≥8 pixels, 2-pixel deduplication,
≥100 samples and ≥6/16 cells per camera, positive finite footprint fraction
≥0.99, log-ratio MAD ≤0.25, camera scale deviation ≤0.25, seed-0/10,000 camera
bootstrap relative halfwidth ≤0.10, and frame-175 disagreement ≤0.10 against
the frozen fit. No camera dropping, refitting at 175 or fallback model is allowed.

P31-1/2: restored historical provenance and synthetic checks support readiness;
actual D1 engineering qualification remains pending. P31-3: only the existing
amended proxy criterion is supported; roles, motion, negatives, temporal identity
and boundary truth remain unverified. P31-4: D1 fit/repeat/check remain unexecuted;
missing combined arms remain explicit. P31-5: no allocation or historical ledger
entry changed. P31-6: no quality improvement, physical accuracy, commercial-use
preference or production-readiness conclusion follows from imports or this repair.

Current elapsed consumption: GPU 27 attempts / 4315.406234818902 seconds; setup
14 attempts / 5316.549373747828 seconds; preparation/scoring/report CPU 4 attempts /
13753.206793547044 seconds. Recoveries remain separately authorized historical
charges, not reset original allocations. Last saved E4 resource sample reports
67,353,055,232 artifact bytes and 26,213,594,692 transfer bytes; these are historical
measurements, not a current resource guarantee. Preserve 93,600 GPU seconds,
57,600 setup seconds, 57,600 preparation/scoring/report CPU seconds, 22 GiB device,
60 GiB downloads and 150 GiB artifact ceilings. Saved time funds no new attempt.

All changes remain unstaged. No prompts content, delegation, native imports,
real model/GPU jobs, new authorization, admission/resume/stage/execute calls,
Git staging or commits were used in this review.
