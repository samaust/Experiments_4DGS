# Plan 017 — Audit retained SelfCap evidence and publish a qualified workflow

## Objective, scope and authority

This is iteration 001's implementation milestone for the
[continuous-improvement objective](../docs/continuous-improvement/20260908-plan016/objective.md),
following [R1–R4 of the review](../docs/continuous-improvement/20260908-plan016/iteration-001-recommendations.md)
and the [post-review assessment](../docs/continuous-improvement/20260908-plan016/iteration-001-assessment-01-review.md).
The main objective includes both SelfCap and Basketball. Completing this plan
does not establish that objective: Basketball accepted timing and reconstruction
remain absent.

Implement R1–R3 using retained local evidence and document R4's authorization
boundary. No optimization, training, GPU execution, fresh rendering, metric
inference, download, dependency installation, online source refresh, numerical
experiment or budget reset is authorized. Hashing files, reconciling recorded
numbers and presenting saved images are permitted evidence work. Preserve
historical runs, checkpoints, source checkouts, ledgers and v10 evidence.

Read AGENTS.md, the objective and latest assessment/status before implementation
and after context loss. Never read `prompts`. No further subagents. Follow the
single escalated retry and stop rules for suspected permission failures; stop
on staging/commit failure. Parent owns loop assessments and status. Implementation
records results and commits completed, validated task-only milestones.

## Fixed inputs and outputs

Use these four method keys and final paths; do not search for a newer or easier
checkpoint or feed the old hardcoded `inventory-experiments.py` another scene.

| Key | Run below `.local/runs/` | Complete model within run | Evaluation below `.local/runs/` |
| --- | --- | --- | --- |
| stg-lite | stg-lite-selfcap-final-20260906 | checkpoint.pt | stg-lite-selfcap-final-evaluation-20260906 |
| stg-full | stg-full-selfcap-final-20260906 | checkpoint.pt | stg-full-selfcap-final-evaluation-20260906 |
| freetimegs | freetimegs-selfcap-final-20260906 | checkpoint-042061.pt | freetimegs-selfcap-final-evaluation-20260906 |
| atgs | atgs-selfcap-final-20260906 | checkpoint-061008-011/bundle.json and all 11 indexed components | atgs-selfcap-final-evaluation-20260906 |

Shared inputs are
`.local/data/selfcap/dance1-processed-20260906/manifest.json`,
`.local/data/selfcap/dance1-initialization-20260906/{initialization.ply,result.json,inputs.json}`,
`.local/data/selfcap/dance1-freetimegs-edgs-initialization-20260906/`
and `configs/detail-crops.selfcap-dance1.json`. Budget evidence is
`.local/runs/plan-004-training-budget.json`; measurements are
`.local/runs/<method>-selfcap-final-measurement-20260906/`.

Create only this bounded implementation surface, plus the required run results:

- `scripts/audit-selfcap-evidence.py`: explicit final-profile auditor and saved-image presentation.
- `tests/test_selfcap_evidence_audit.py`: small synthetic fixtures for consequential failure handling.
- `docs/experiments/selfcap-evidence-20260908/audit.json` and `audit.md`.
- `docs/experiments/selfcap-evidence-20260908/inspection.json`, `inspection.md`,
  and `inspection.html`; generated inspection PNG sheets go under the Git-ignored
  `.local/runs/selfcap-evidence-20260908/sheets/`, linked from the tracked index.
- `docs/selfcap-workflow.md`: practical recommendation and reproduction/reload guide.
- Update current overviews in `docs/contender-experiments.md`,
  `docs/experiments/contender-summary.md`, and add a brief current-workflow link
  to `docs/local-creation.md`. Do not rewrite historical experiment reports.
- `docs/continuous-improvement/20260908-plan016/iteration-001-implementation.md`
  and `iteration-001-validation.md`, including remaining gaps and commit IDs.

If an output already exists, preserve it and use a numbered sibling; record the
chosen path. Do not overwrite prior evidence to make a check pass.

## Work 1 — Bind the saved evidence (R1; SC-01, SC-02, SC-03, SC-05)

Implement a CPU-only CLI using the standard library and the already-installed
Pillow in `.local/envs/stg-render`; do not import model modules, torch or CUDA.
Interface:

```bash
.local/envs/stg-render/bin/python scripts/audit-selfcap-evidence.py \
  --root . --output docs/experiments/selfcap-evidence-20260908 \
  --assets-output .local/runs/selfcap-evidence-20260908
```

`--root` resolves the repository and fixed relative input paths. `--output` and
`--assets-output` must both be new and outside all input runs; reject either
existing destination before writes. Keep large generated images out of Git.
Factor check functions so small temporary fixtures can exercise invariants
without reproducing the full scene. Report schema, command, auditor hash, input
paths/hashes/sizes, check IDs, criterion IDs, expected/observed values, status
(`passed`, `failed`, `unavailable`) and reason. Hash repeated paths once per
invocation. Write a readable summary and machine-readable per-file inventory.
Return nonzero for failed required checks; unavailable evidence must remain
explicit and must never become a passed claim. Save completed checks if a
required file is missing; permission failures follow repository retry/stop rules.

Perform exactly these substantive checks:

1. **Processed inputs and initialization.** Verify the manifest hash against
   all four evaluations and training provenance; require `[4120,4180)`, 60 FPS,
   24 unique cameras, held-out/test 0015 and 23 training cameras. Verify all
   1,440 manifest image hashes and each camera's recorded dimensions; camera
   dimensions vary, so only 0015 is fixed at 1890×1061. Check unique camera/frame
   membership, all 60 frame IDs, finite increasing timestamps and normalized
   times, and recorded normalization against `time.origin_seconds` and
   `time.duration_seconds`. Reconcile the camera-offset formula with saved
   calibration/sync provenance and preparation source; do not replace it with
   frame-offset/count. Verify the calibration/sync files indexed by the manifest
   at the source paths used by `prepare-selfcap.py`. Record source-video paths
   and recorded hashes/presence; rehashing all source videos is not required and
   must not be implied. Check sparse initialization hashes and its 23 midpoint
   input records against training membership and image/time hashes. Check dense
   initialization NPZ/result hashes and the recorded 24 keyframe/successor
   cloud provenance, training-camera exclusions and source-frame links; follow
   those explicitly indexed result/input files, without reopening training or
   auditing every RoMa weight/build artifact.
2. **Complete model and commands.** Verify Lite/Full and FreeTimeGS checkpoint
   hashes/sizes against saved evaluation/render records; verify ATGS marker and
   every component's bytes/hash and total. Retain training configuration,
   provenance, result, worker-result, checkpoint index where present and
   measurement command/result evidence. Check final progress 30,000/30,000,
   42,061/70,000 and 61,008/100,000 microsteps (20,336 ATGS updates). Describe
   complete-state requirements from the existing checkpoint loaders and saved
   evidence; do not deserialize or freshly restore the large models. A PLY alone
   is not the complete STG Full or ATGS model.
3. **Both saved reloads.** For every evaluation require the completed reload-a
   and reload-b stage records, commands, offline-isolation evidence, render.json,
   compare-heldout.json and compare-sweep.json. Verify exact filename sets:
   `images/0015/004120.png` through `004179.png` and
   `sweep/00000.png` through `00019.png`, in both reloads. Hash all 640 PNGs,
   check RGB dimensions and match both sides of comparison records. Bind every
   held-out record to the manifest camera/frame/time. Require shared sweep
   metadata/20 poses, midpoint frame 4150, start 0015/end 0014 and fixed time
   equal to the shared manifest. STG has no `sweep_frames`; its sweep hashes are
   in compare-sweep.json. FreeTimeGS/ATGS also bind `sweep_frames`. Compare their
   saved float hashes across reloads but label them historical raw-float
   evidence: raw arrays are not being recomputed. STG establishes PNG equality
   only. This audit is not a new offline reload or numerical validation.
4. **Source/runtime applicability.** Check each STG `provenance.files` and all
   six `evaluation.helpers_sha256` entries, preserving its saved adapted training
   file. Check FreeTimeGS bundle source/configuration identities using the
   same pure-file/AST hashing definitions in its existing source helpers;
   check its recorded gsplat/fused-SSIM binary hashes at installed paths.
   Check ATGS configuration `sources`, provenance revision/helper AST,
   renderer hash and the runtime's indexed extension files/package metadata.
   Compare available runtime records across saved reloads. Resolve the pinned
   revisions/environment setup references from existing local docs and lock
   records; do not run build scripts or import extensions. Record absent STG
   historical binary attestation as unavailable, without inventing it. For a
   changed source, report exact path and expected/current identities; identify
   matching retained source or a local git blob if available, recording the
   revision/path/hash. Never restore source in place or relabel current bytes as
   historical. A missing matching required source blocks the corresponding
   present-reproducibility claim, while original saved results remain historical.
5. **Metrics and resources.** Require the same saved metric protocol and unique
   60-frame membership for all four `metrics.json` files. Recompute only their
   per-frame arithmetic means and published method deltas, agreeing with saved
   aggregates/evaluation values within floating arithmetic tolerance (1e-9 for
   full-precision values; published decimals within their rounding precision).
   Reconcile saved benchmark FPS as 100/sum(durations), 10 warmups, 100 samples,
   camera 0015/frame 4150 and 1890×1061. Preserve its exclusions of load/setup/
   save/encoding. Reconcile ledger reservations, per-method/global charges,
   no live reservations and zero overruns; distinguish reservation completion
   from native schedule completion. Expected global charge is 22,523.417254 s;
   preserve individual 7,200 s allocations, failures and unused allocations.
   Link measured continuation wall, sampled device baseline/peak and allocator
   peaks; do not equate those measurements or complete-state size with an
   inference-only payload. No new perceptual/temporal metrics or performance run.

Keep the audit claim-specific. A unavailable historical runtime detail is a
reported limitation, not authority for broader forensic work. If a required
current artifact differs, record it, finish unaffected checks and qualify the
decision; do not start recovery, retraining or environment changes.

## Work 2 — Inspect shared temporal evidence (R2; SC-03, SC-04)

After successful frame/hash binding, generate presentation from those saved
images. Use actual image compositing/resizing in Pillow; never generative image
editing. Provide an offline HTML page with reference plus all four methods,
a synchronized frame selector covering all 60 frames, exact source frame ID,
timestamp_seconds and normalized_time, image links and named crop views. Use
relative local asset references; no external scripts, fetching or server is
required. Display original images/crops with optional zoom, and disclose any
sheet-only downsampling. Include a separate shared sweep selector.

The implementer must actually inspect, via image viewing tools, these bounded
comparison sheets and record what was viewed:

- Full-frame reference/method comparisons at 4120, 4150 and 4179.
- Adjacent windows 4120–4122, 4148–4152 and 4177–4179, every adjacent transition
  within each window, for all four methods and reference. These cover the
  previously documented early/midpoint failures and slower ending pose.
- At those same windows use the existing fixed crops:
  `hair_motion=[330,300,1020,820]`,
  `face_hair_boundary=[620,470,900,750]`,
  `hands_body_boundary=[610,830,1030,1061]`,
  `static_book_text=[850,350,1030,515]` (exclusive right/bottom).
  Verify crop selection frame 4150/hash against the crop config. Do not move
  crops to favor a method; note when a feature leaves the fixed region.
- Frozen-time sweep poses 0, 10 and 19 for every method, with exact pose index,
  shared time and source image links. Interior novel poses lack ground truth;
  judge visible view consistency only, not held-out fidelity there.

Use manageable sheets per crop/window rather than shrinking all comparisons
onto one unreadable sheet. `inspection.json` indexes sheet hashes, source hashes,
frames/timestamps, crop bounds, methods and sweep poses; `inspection.md` records
the actual inspection and observations. Providing a player alone is not visual
inspection. Do not claim full-sequence playback was inspected unless it was.
Distinguish reference motion blur from excess predicted blur, persistence of
ghosting across adjacent frames, changing boundary errors and static-detail
behavior. State uncertainty where a cause or ordering cannot be established.
The existing analyzer's adjacent MAE includes real motion and cannot rank
flicker; its blinds crop is inapplicable. Do not create a combined score or
quantitative flicker ranking.

## Work 3 — Decide and make the supported workflow usable (R3/R4; SC-02–SC-05)

Publish a direct practical recommendation for this 60-frame SelfCap profile,
supported by audit and actual visual findings. Assess STG Full as the default
compact, completed-schedule workflow; FreeTimeGS as the measured aggregate
quality option with dense initialization, incomplete schedule and large resume
state; Lite as the fastest measured renderer; and whether ATGS offers a reason
to choose it on this profile. State the final choice and tradeoffs explicitly.
If evidence invalidates a prospective recommendation, narrow or withhold that
claim with its exact cause instead of forcing a winner. Do not claim equal
compute, full-paper convergence, long-sequence fidelity or a six-method ranking.

The guide must include repository-relative input/model/config paths, complete
checkpoint hashes, pinned source/environment references, preparation and
training-only initialization procedures, saved training commands and gates,
and copyable exact-model offline reload/evaluation commands. Prefer the existing
STG Full route when justified; its command interface is:

```bash
.local/envs/stg-render/bin/python scripts/offline-python.py \
  scripts/render-stg-manifest.py --checkout .local/SpacetimeGaussians \
  --manifest .local/data/selfcap/dance1-processed-20260906/manifest.json \
  --checkpoint .local/runs/stg-full-selfcap-final-20260906/checkpoint.pt \
  --output .local/runs/stg-full-selfcap-user-reload-NEW
```

Explain that this renders all 60 held-out times and the shared 20-pose midpoint
sweep. Include the matching second-reload/comparison and evaluation commands
from saved evaluation stages, with genuinely new output directories. Link the
exact FreeTimeGS and ATGS commands/config/provenance arguments as alternatives.
Verify syntax by reading the argument parsers and `bash -n` on extracted shell
examples; do not execute these GPU/training commands during this milestone.
Training examples are reproduction procedures subject to the unchanged ledger,
not instructions to reset it. Lite/Full completed their schedules; FreeTimeGS
and ATGS remaining time is below the existing 185 s restart/reserve threshold.

Replace stale current statuses in the two contender overviews. Cover all six
candidates and both scene profiles, four evaluated SelfCap pairs and eight
blocked pairs. Date the retained MoE-GS and FreeTimeGS++ availability audits
2026-09-06; there was no online refresh. State their exact standalone-expert
route/matching-state and author fixed-B implementation blockers. Lead Basketball
with Plan 016/v10 scientific rejection and null accepted timing. Preserve the
accepted 34-camera static calibration, estimated scale 1.31506947 metres per
calibration unit and held-outs 0/10/20/30; mark old 23-camera/v4/v5/v6 statuses
as historical, keeping their links. Distinguish result-or-blocker coverage from
achievement of the reconstruction objective.

Record the remaining dependency explicitly: a new Basketball numerical phase
needs user-approved concrete scope, elapsed-time and attempt caps. Plan 016's
five 81-attempt policies and six preflight allocations are consumed; its
90-minute window cannot restart. Do not propose a numerical total for an
unspecified solver or use unspent training/calibration allocations as authority.
Full screens and final validation still require their scientific gates. Once
this evidence milestone is finished, the parent must assess every SC and stop
at this authorization boundary if it remains the next necessary work.

## Acceptance and validation

| Acceptance ID | Required milestone outcome | Criterion advanced | Validation |
| --- | --- | --- | --- |
| A1 | Four final model inventories, 1,440 processed input records and 640 reload PNGs checked; commands, source/runtime scope, metrics and resources bound with explicit failed/unavailable checks | SC-01, SC-02, SC-03, SC-05 | Auditor report, current hashes and per-check evidence; no failed claim presented as verified |
| A2 | Actual shared adjacent-frame/crop and pose inspection saved with image/time links and qualified motion observations | SC-03, SC-04 | View required sheets, inspect index and report, verify frame/crop/source bindings |
| A3 | Evidence-backed supported-profile choice, exact complete-model reload route, dated candidate blockers and current Basketball status | SC-02, SC-04, SC-05 | Read guide against A1/A2, verify local links and parser/shell syntax |
| A4 | Historical evidence/budgets preserved and remaining authorization dependency recorded | SC-01–SC-05 | Git diff/status, ledger hash before/after, v10 terminal record links, implementation/validation reports and local commit IDs |

Use focused fixture tests for: (1) a valid tiny evidence graph; (2) changed PNG
bytes or a missing ATGS component; (3) duplicate/missing camera-frame membership
and incorrect frame time; (4) changed sweep pose or a/b hash disagreement;
(5) metric aggregate mismatch; (6) unavailable historical runtime distinguished
from a failed current source hash and output-directory overwrite refusal.
Assertions must establish that false evidence cannot pass, not merely mirror
helper implementation. Fixtures are temporary and cannot modify real runs.
Use the existing interpreter with `python -m unittest discover -s tests -p
test_selfcap_evidence_audit.py -v`; run no broad solver/GPU suite.

Run the auditor once on retained artifacts after focused tests; repeat only
affected checks if a failure requires an implementation correction. Check new
HTML/image links and touched Markdown local links with a bounded local checker,
not a network crawler. Run `git diff --check`, inspect task-only diffs and verify
historical inputs/ledger were not modified. Stage explicit task paths with an
escalated `git add`, inspect the staged diff, then use a separate escalated
`git commit` with title and description, per AGENTS.md. Do not push or amend.

Record commands/outcomes, evidence links, remaining gaps, any unavailable checks
and commits in the iteration result/validation files. Report A1–A4 separately
from the unchanged SC definitions. Implementation can proceed without input
within this scope; another Basketball experiment cannot.
