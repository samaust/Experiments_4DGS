# Plan 032 — S1 amendment-bound calibration recovery

Prepared 2026-09-19 against HEAD `0184cef74548261d4444ed9ee1e0464da1561b5e`
and the existing uncommitted S1 changes. Status: PLAN complete; implementation,
validation of the recovery path, live admission and recovery execution pending.

## Authority, objective and boundaries

Complete [the S1 recovery objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md)
using [review-001](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-001.md)
and [assessment-001](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-001.json).
This is a bounded continuation of [Plan 031](plan_031.md), not a replacement
benchmark allocation. Preserve Plan 031 byte for byte.

**The user's current instruction supplies authorization for the bounded task
specified here, but does not relax repository or scientific gates.** Its current
PLAN-stage restriction permits only this new plan and its plan-link artifact:
no implementation, GPU jobs, live admission/authorization registration, staging,
commits or delegation now. Execute the steps below only when the loop enters an
implementation/execution stage; carry forward the applicable user authorization
rather than asking for duplicate routine approval. Record the actual instruction
and its stage restriction faithfully. Neither the older REVIEW nor the semantic
amendment itself supplied execution authority. Never read `prompts` content.

The bounded task is completion and CPU validation of the existing admission and
failure-evidence work, followed by **one** additional
`S1-calibration-recovery-001` attempt, at most **3,600 GPU seconds**, and a terminal
evidence review. There is **no reconstruction authorization**. Reconstruction
requires separate later authorization after calibration review and an explicit
disposition of the skipped R-S immediate-repeat requirement. This plan cannot
allocate `S1-reconstruction-recovery-001`, R-S, another recovery identity, or a
second process attempt.

Do not rerun preparation, annotation import/review generation, setup, downloads,
S0/S2/S3/S4, motion, neighbors, depth (including completed D1-fit/R-D/D1-check),
geometry, finalists, combined arms, aggregate stages or the final report. No
calibration regeneration, training, final-window evaluation, production promotion,
new model probe, smoke job or quality-scoring pass. Preserve frozen study,
protocol, Plan 031, research status/report, prior failures, aggregate/finalist
artifacts, environment pins and all existing ledger events. New recovery evidence
lives in separate files. S1-4 does not repair historical P31-5 accounting failures.

## Evidence baseline and work already present

Use these directory abbreviations throughout this plan:

- `D = docs/research/vipe-alternatives/plan031-20260913T032700Z`
- `L = .local/vipe-alternatives/plan031-20260913T032700Z`
- `J = L/jobs/S1-calibration-recovery-001`

Read [the amendment](../docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-semantic-assignment-amendment-001.json),
[semantic validation](../docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-semantic-assignment-validation-001.json)
and [semantic review](../docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-semantic-assignment-review-001.md)
as immutable historical evidence. Amendment ID is `plan031-s1-s0-token-sum-v1`;
its SHA-256 is `67de90737094ec751d49036be5cef46ee6dea84d40a8ff2475fc79e1623bfb4a`.
It changes semantic protocol, covers S1 conceptually in both branches, and records
zero authorized attempts. Only this task's calibration scope may be admitted.

| Existing changed path | Work to retain and validate |
| --- | --- |
| `scripts/vipe_benchmark/backends.py` | Per-retained-query S0 token-sum assignment, native query alignment and successful raw diagnostics. Add only durable S1 failure-evidence handling. |
| `scripts/vipe_benchmark/contracts.py` | Explicit assignment-evidence contract permitting empty native text only with valid derived semantics. Preserve shared non-S1 behavior. |
| `tests/test_vipe_benchmark_s1_semantics.py` (new) | CPU semantic fixtures, native box/score preservation, SAM and pair propagation. Extend for early failures. |
| `scripts/vipe_benchmark/s1_recovery.py` (new) | Partial dedicated binding validator and dynamic `source_paths()` list. Finish its schema, provenance and lifecycle checks. |
| `scripts/basketball_vipe_benchmark.py` | Existing amendment-aware `component-recovery` admission hook. Complete single-attempt orchestration. |
| `scripts/vipe_benchmark/execution.py` | Existing admission and request binding hooks. Complete dispatch and terminal-result verification. |
| `scripts/vipe_benchmark/ledger.py` | Existing dedicated-S1 routing with generic S1 rejection. Complete locked checks and evidence bindings. |

Additional expected edits are `scripts/vipe_benchmark/stages.py` and new
`tests/test_vipe_benchmark_s1_recovery.py`; extend existing execution tests as
needed. Change worker/supervisor code only if required to preserve evidence or
enforce the existing deadline; do not redesign unrelated execution paths.

Review-001 reports 68 passing CPU tests and S1-1/S1-4 met within their stated
limits. Those tests do not qualify S1 recovery admission or a real model result.
The old validation uses `amendment`, while the draft requires
`semantic_amendment`; it covers 45 files versus the current 68-file required set
and has stale controller/execution/ledger hashes. Preserve it and create new
validation after implementation. Recompute the source set after adding tests;
68 is not a permanent expected count.

The PLAN-stage read-only ledger audit verifies all 447 chained events, sequences
0–446, 332,437 bytes, SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`.
Last event hash is
`00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
There is no active reservation, S1 recovery authorization or recovery directory.
Original calibration failure: sequence 250, 10.414188402937725 seconds, confirmed
cleanup, event hash
`102e7c7cc33e8a6d2b4107b69fad0ef577b36a901b59c133d99e811f36665d71`;
`L/jobs/S1-calibration/failure.json` hash
`80b50f5414245d3e84d9da8dafdcbf323753e00f0675d8702bb990dacfe8c13a`.
Original reconstruction failure: sequence 255, 10.50047472200822 seconds,
confirmed cleanup, event hash
`2124a4c0c3a8439e697c04c293ef5f2dfe62cea0dd56a7f638e56f91cdad9b54`.
R-S remains skipped at sequence 256. Never reset these records or their charges.

## Ordered implementation and acceptance map

| Step | Objective mapping | Required result before continuing |
| --- | --- | --- |
| 1. Freeze baseline and complete binding | S1-1, S1-2, S1-4 | Exact amendment/current source/failure/E1/input/annotation/config/resource binding; immutable preservation manifest. |
| 2. Close admission-to-dispatch lifecycle | S1-2, S1-4 | One authorization and one reservation, state checked under locks, no mutation or replay bypass, generic recovery unchanged. |
| 3. Preserve failure evidence and qualify first result | S1-1, S1-3 | Raw evidence survives alignment/layout/contract errors; first result gates remaining inputs inside the same attempt. |
| 4. CPU tests and implementation review | S1-1, S1-2, S1-4 | New complete source-bound passing validation and review, no live ledger change during implementation/tests. |
| 5. Admit and supervise once | S1-2, S1-3, S1-4 | Applicable authority recorded, all gates pass, one bounded calibration attempt or explicit pre-dispatch blocker. |
| 6. Review terminal evidence and stop | S1-3, S1-4 | Complete validated 510-row result or accounted failure, compact receipt, cleanup and preservation verification; no automatic continuation. |

### 1. Freeze baseline and complete amendment binding

Before edits, snapshot source diff, untracked S1 files, index state, HEAD, all
amendment frozen parents, original failure/request artifacts, assessment
`preservation_checks` and `verified_result_records`, existing semantic bundle,
configuration, E1/input/annotation records and the ledger prefix/hash/head.
Store immutable `D/s1-recovery-baseline-001.json` with schema
`plan032-s1-recovery-baseline/v1`, `recorded_utc`, `head`, `plan`, `objective`,
`review`, `assessment`, `sources`, `tracked_diff_sha256`, `index_diff_sha256`,
`preserved_records` and `ledger_snapshot`. Each snapshot record must contain
absolute `path`, SHA-256 `sha256` and integer `bytes`; verify all three, resolved
path identity and forbidden-path guards. No writes to historical evidence.

Keep S0's verified rule: caption `person.basketball.`, skip token IDs 101/102,
period ID 1012 delimits person/basketball spans, sum sigmoid token probabilities
per span, choose the first maximum, for **every** retained detection. Preserve
weights, precision, native preprocessing, strict box threshold `>0.35`, native
text threshold `>0.5`, native phrases/confidences/box order, SAM refinement/merge
and DeAOT tracking. No text-dependent fallback or ambiguity rejection threshold.
S1 workers remain isolated from ViPE; only admission hashes the amendment's S0
reference sources. Verify those records and the pinned native predictor source.

In `s1_recovery.validate_binding`, require the dedicated schema below and reject
unknown schema, wrong type (including booleans masquerading as integers), branch,
job, flags, amendment or budget. Validate current configuration against its exact
record and fixed ceilings, not merely against values supplied by an authorization.
Verify original failure artifact bytes and its failed/cleaned-up finish event
against the current ledger **before** reporting successful admission; amendment
claims alone are insufficient. Accept only the original calibration failure and
no prior S1 recovery allocation/consumption. Preserve generic
`vipe-benchmark-component-recovery/v1`'s fixed-configuration guard with
`changes_to_prescribed_configuration=false`; S1 cannot use it.

Resolve E1 only to successful `E1-setup-recovery-002`. Bind its result, assets,
runtime Python/version specification, inventory, imports, dependency lock and
build inputs, and verify the asset manifest's referenced source/weight/tokenizer/
configuration records through existing integrity checks. Existing result hash:
`d983f409c56f6d388fc09aab4be59d1257dc0a3a4da02d982d8b9b3b4d03565d`;
asset-manifest hash:
`9aa66c929cce4ece69d482022e3aeb02aad389435d379c7dc159b616f79063bf`.
Use E1's Python 3.11, torch 2.5.1+cu124, torchvision 0.20.1+cu124 and NumPy
1.26.4 unchanged. Import qualification had zero forwards and no initialized CUDA
context; runtime success remains to be established in the allocated job.

Bind the completed prepared input manifest (hash
`8bffd5ee620860dff0ded5bc5a5b70d1e424a5bc88d2bd8e937e70a94163466b`)
and annotation bundle (hash
`ece14f11d7c8f6df584cb6dcd74a600acc874d88ff1a0704b98aca89c98436bc`).
Bind annotation `policy` and review decision records and the ledger's
`annotation_amendment` event at sequence 57. Current policy hash is
`2c4d13ac57a2bed5daa1d15df3094d1bbc9017ce22c0ecf8ab9215684cc1bc30`.
Run the existing policy-appropriate annotation validator without regenerating
annotations. Preserve `evidence_kind=model-assisted-proxy` and
`human_ground_truth=false`; this task does not create independent truth or relax
annotation review gates. Missing/changed required records block admission.

### 2. Bind authorization through dispatch and result resolution

Use `make_request(L, 'S1-calibration', config)` to derive the original canonical
request. `original_request_sha256` means `object_hash` of this derived dictionary,
using repository canonical JSON (sorted keys, compact separators, no NaN). It
is **not** the hash of historical serialized `L/requests/S1-calibration.json`,
which has a dispatch-added `configuration` field. Bind that historical file
separately as `historical_request` and verify its original reserve-event record.
Build recovery request deterministically by replacing only `job_id`, adding
`recovery_authorization`, then dispatch's exact `configuration` record. Hash and
save the final serialized request at `L/requests/S1-calibration-recovery-001.json`.
Avoid circular hashes: authorization binds the original canonical request;
reservation binds the authorization and final dispatch request records.

Recheck source/config/artifact hashes and live attempt state at admission,
registration, request construction and immediately before reservation/launch.
Registration and reservation must validate relevant state under the existing
ledger locks using the locked event snapshot (avoid nested lock acquisition).
Reject concurrent active attempts, prior allocation under another authorization,
second identity, already consumed identity, mismatched authorization/validation,
changed dispatch request and insufficient resources. A repeated invocation with
an identical registered but unreserved authorization may continue only if all
checks still pass; an existing reservation consumes the attempt even if no
forward occurred. Terminal or unreconciled reserved identities never relaunch.
Do not delete request/job directories to make dispatch succeed.

Use the existing `component-recovery` controller and supervisor exclusively.
Keep generic S2 recovery behavior and other allocations unchanged. Full membership
validation must occur at worker completion, supervisor acceptance and recovered
result resolution, not just `len(rows)==510`. Recovery lookup requires a unique
registered authorization plus matching supervised successful finish, confirmed
cleanup, unchanged result/output hashes, first-result pass and all 510 exact
identities. Failed/partial/unfinished outputs cannot shadow the original failure.
Do not call `execute_matrix`, aggregation or reporting as a follow-up.

### 3. First-result qualification and durable failure evidence

Implement an S1-only structured exception evidence payload in `backends.py` and
serialize it at the `stages.segment` boundary. Capture each available array and
native return value before the next potentially failing check. Reset per-image
capture state so a failure cannot reuse previous-frame diagnostics. Preserve the
original exception/traceback; serialization failure is additional evidence, not a
reason to swallow the original error or continue. Cover adapter exceptions and
post-return shape/semantics/static/serialization contract failures. A pre-forward
failure explicitly records unavailable evidence; never invent original scores or
run another forward to obtain them.

The **first actual input is calibration camera 0, frame 50, pair_start null** in
the existing camera-major order. Process that one singleton, persist its raw
intermediates, and write an immutable passed qualification record before frame
62 or any other input begins. All these operations are inside the one job timer.
The qualification must establish:

1. Request/amendment/runtime/input identity matches admission; distorted RGB is
   960×540 with original camera/frame identity, K and footprint provenance.
   Capture actual loaded runtime/native files and ViPE isolation evidence.
2. Raw query logits/boxes align with the single native forward; probabilities are
   finite in [0,1], native selected indices are exactly max-token score `>0.35`,
   and selected normalized boxes/order and native max-token scores match exactly.
   Verify token layout and both class spans against the frozen caption.
3. Every retained query has the independently checked sums, first-max winner,
   derived class, native phrase/score, token spans/scores, margin, tie policy and
   complete ambiguity reasons, including detections later overwritten/skipped by
   SAM. Empty native text, ties and disagreement are allowed when evidence is
   valid; zero detections is valid and records zero assignments explicitly.
4. Labels are int32 540×960, -1 outside valid footprint, nonnegative inside,
   positive IDs at most 255, and surviving-ID metadata matches exactly with only
   person/basketball derived classes. Semantic static is uint8 0/255, zero outside
   validity, calculated using the existing zero-changing-mask contract. It is
   not a newly aggregated M0 final-static result. Preserve SAM and tracker behavior.
5. Numeric intermediates are saved without pickles; output/config/runtime/input
   records rehash correctly. No object arrays, missing required evidence or
   isolation violations. Resource monitoring remains within all caps.

**Stop immediately on any failed first-result check**: do not advance the next
input, change settings, fall back, retry the query or start another process.
Persist available evidence and let the supervisor terminate/clean up and charge
the attempt. A passed first result permits the remaining 509 inputs, each under
the same applicable output/semantic contracts. Stop at any subsequent contract,
resource or runtime failure. First-result success establishes engineering
qualification only; it is not measured quality improvement or S1/S0 equivalence.

### 4. CPU validation and implementation review

Timebox this implementation/validation pass to 1,800 wall seconds, with at most
eight CPU workers, serial where practical. Record elapsed time; expiration stops
before live admission with the remaining gap recorded. Synthetic CPU fixtures
are not model evaluations. Any actual benchmark preparation/preflight work must
be charged to the existing CPU allowance without reopening consumed jobs.

Add `tests/test_vipe_benchmark_s1_recovery.py` using temporary ledgers, fake
workers and injected GPU/resource readings only. Required cases:

- Valid binding and admission → authorization → reservation → dispatch → finish
  → result resolution, plus preserved generic S2 recovery behavior.
- Wrong schema/amendment/job/branch/typed flags; changed frozen parents/S0/native
  sources; stale, missing, extra, duplicate or aliased source records; failed or
  missing test receipts; old semantic validation rejected.
- Changed E1 qualification/assets/runtime, configuration, input or annotation
  bundle/policy/review evidence; wrong failure artifact/event, unconfirmed
  cleanup; historical-versus-derived request hash distinction.
- Active attempt, duplicate registration/reservation, second recovery identity,
  repeated controller invocation, exhausted/reduced cumulative time, changed
  authorization/validation/request between lifecycle steps and lock-bound races.
- Incomplete/duplicate/wrong identities even at 510 rows; failed, unqualified or
  unsupervised results; altered outputs; cleanup failure cannot resolve success.
- Alignment, token-layout and output-contract exceptions preserve available
  logits/boxes/probabilities/native metadata with one forward and original error;
  pre-forward unavailability, no stale prior-image evidence; first-result failure
  prevents the second input, including serialization failure.

Run the following command after final source edits; save exact command, stdout,
stderr, exit code, test count, failures/errors/skips and elapsed time:

```sh
.local/envs/stg-colmap/bin/python -B - <<'PY'
import sys, unittest
suite = unittest.TestSuite()
for name in ('s1_semantics', 's1_recovery', 'backends', 'contracts',
             'component_recovery', 'execution', 'budgets', 'supervisor',
             'review_annotations'):
    suite.addTests(unittest.defaultTestLoader.discover(
        'tests', pattern='test_vipe_benchmark_' + name + '.py'))
result = unittest.TextTestRunner(verbosity=2).run(suite)
sys.exit(not result.wasSuccessful())
PY
```

Also run `git diff --check` and baseline preservation/hash-chain checks. Required
new cases cannot be skipped or collected as zero tests. Test failures block live
admission. Save new validation and implementation review with all uncertainty
explicit. No production ledger mutation or device probing during CPU validation.
Any source/config/test change after validation invalidates admission until the
affected checks are rerun and fresh immutable validation is issued.

## Exact artifact and ledger contracts

New filenames below are reserved for later stages, not created by this PLAN.
Use immutable exclusive creation. If a filename already exists unexpectedly,
verify its provenance; stop on conflict rather than overwrite. File records are
`{path, sha256, bytes}`. An event reference is `{sequence, event_sha256}` and must
resolve within a valid chain. JSON must not contain NaN/Infinity; keep nonfinite
raw failure values in numeric arrays and describe their invalidity in JSON.

| Artifact | Required fields and values |
| --- | --- |
| `D/s1-recovery-validation-001.json` | `schema=plan031-s1-recovery-validation/v1`, `status=passed`, `recorded_utc`, `head`, `plan`, `baseline`, `semantic_amendment`, `configuration`, `sources`, `tests`, `diff_check`, `preservation_checks`, `ledger_snapshot`, `gpu_jobs_run=0`. `sources` is the exact resolved duplicate-free current `source_paths()` set: controller, worker, benchmark config, every benchmark module and every `test_vipe_benchmark_*.py`. `tests` entries contain `command`, `stdin` if used, `stdout`, `stderr`, `exit_code`, `tests_run`, `failures`, `errors`, `skipped`, `elapsed_seconds`; receipts must pass with required cases exercised. Bind all source/config/test bytes at validation time. |
| `D/s1-recovery-implementation-review-001.md` | Changed paths, validation record/hash, each review-001 finding F1–F4 disposition, S1-1..S1-4 status/limits, preserved semantic rule, lifecycle tests, failure-evidence checks, implementation elapsed time, unresolved gates and execution readiness. No claim of real-model success. |
| `D/s1-calibration-recovery-authorization-001.json` | `schema=vipe-benchmark-s1-amendment-calibration-recovery/v1`, `job_id=S1-calibration-recovery-001`, `original_job_id=S1-calibration`, integer `attempts_limit=1`, `seconds_limit=3600`, `gpu_total_seconds_limit=93600`; exact booleans `reset_previous_consumption=false`, `changes_to_prescribed_configuration=true`, `unrelated_attempts_reopened=false`, `reconstruction_authorized=false`, `semantic_amendment_approved=true`, `additional_attempt_approved=true`. Nonempty `authorization` records actual applicable user instruction; `authorization_context` records request date, PLAN/DO distinction and scope. Required bindings: `plan`, `baseline`, `semantic_amendment`, `repair_validation`, `implementation_review`, `configuration`, `original_failure`, `original_failure_event_sha256`, `historical_request`, `original_request_sha256`, `e1_qualification`, `e1_assets`, `e1_runtime`, `inputs`, `annotations`, `annotation_policy`, `annotation_review`, `annotation_amendment_event`, `ledger_baseline`, `resource_limits`. |
| Authorization `resource_limits` | `gpu_concurrency=1`, `gpu_peak_device_gib_limit=22`, `gpu_total_seconds_limit=93600`, `cpu_max_workers=8`, `cpu_prepare_score_report_seconds_limit=57600`, `setup_wall_seconds_limit=57600`, `new_download_gib_limit=60`, `new_artifact_disk_gib_limit=150`, `new_setup_attempts=0`, `new_downloads=0`, `extra_smoke_jobs=0`, `reconstruction_attempts=0`, `cleanup_reserve_seconds_max=30`. Configuration equality and separate live consumption checks are mandatory. |
| `D/admission-NNN.json` | Next unused normal admission filename (currently 040; recompute). Preserve `status`, `reasons`, `evidence`, `gpu`, `resources`, `candidates`, `consumption`. `evidence` includes `s1_recovery_authorization`, `implementation_validation`, `semantic_amendment`, `configuration`, `original_failure`, `original_failure_event`, E1/input/annotation bindings and `ledger_before`. `gpu`/`resources` are fresh host measurements. A blocked record is not permission to reserve. |
| `L/requests/S1-calibration-recovery-001.json`, `J/config.json` | Exact deterministic recovery request and its dispatch `configuration`; `job_id`, `component=S1`, `branch=calibration`, `inputs`, `runtime`, `assets`, `forbidden_vipe_roots`, `recovery_authorization`. Both bytes and canonical request relation verified. |
| `J/first-result-qualification.json` | `schema=plan032-s1-first-result/v1`, `job_id`, `status` (`passed`, `failed`, `not_reached`), `identity`, `count`, `rows`, `runtime`, `semantic_amendment`, `authorization`, `request`, `checks`, `raw_evidence`, `error`, `failure_stage`, `elapsed_seconds_from_reservation`. Each check records `name`, `status`, evidence/reason. Pass requires the five qualification groups above; `count=1`. `not_reached` uses `count=0`, empty rows and the actual reason. A later failure never overwrites a passed first-result record. If abrupt death prevents worker publication, supervisor/controller writes a truthful not-reached/failed record from available artifacts after cleanup, never a reconstructed pass. |
| `J/<identity>-intermediates.npz`, `J/<identity>-failure-evidence.json` and numeric failure `.npz` | Available raw logits, raw normalized cxcywh boxes, token probabilities, native selected boxes/scores, selected query indices, processed RGB and token IDs as non-object arrays. JSON: `schema=plan032-s1-failure-evidence/v1`, `job_id`, `identity`, `failure_stage`, `error_type`, `error`, `traceback`, `native_phrases`, `assignments`, `array_records`, `available_fields`, `unavailable_fields` with reasons, `forward_count`, input/request/amendment records. Assignment entries contain `policy`, `phrase_classes`, `phrase_token_indices`, `phrase_token_scores`, `phrase_token_sums`, `winner_index`, `derived_class`, `margin`, `tie_break`, `ambiguous`, `ambiguity_reasons`. Persist SAM masks/overlap and other available normal diagnostics too. |
| `J/result.json` or `J/failure.json`, worker logs, `J/loaded-runtime.json` | Success retains normal `status`, `job_id`, `component`, `branch`, `rows`, `configuration`, `runtime`, `native_wall_seconds`, `peak_allocated_bytes`, `peak_reserved_bytes`, plus first-result/evidence records. Each row retains full identity, input/K/footprint provenance, labels/static records, native semantics, metadata and diagnostics hashes. Failure retains exact exception/traceback, failure stage, available partial/raw records and first-result status. Absence of a result never implies success. Preserve stdout/stderr at the supervisor's recorded paths. |
| `D/S1-calibration-recovery-001.json` | `schema=plan032-s1-calibration-recovery-receipt/v1`, `status` (`complete`, `failed`, `blocked`), `job_id`, `original_job_id`, `authorization`, `admission`, `semantic_amendment`, `repair_validation`, `request`, `result` or null, `failure` or null, `first_result` or null with reason, `raw_evidence`, `logs`, `runtime`, `ledger_events`, `counts` (`expected=510`, actual, fit=340/actual, selection=170/actual, membership status), `resources_before`, `resources_after`, `elapsed_seconds`, `seconds_limit_effective`, `attempt_consumed`, `cleanup_confirmed`, `surviving_pids`, `stop_required`, `stop_reason`, `preservation_checks`, `reconstruction_authorized=false`. A pre-reservation block has `attempt_consumed=false` and null run artifacts; it does not satisfy S1-3. Extend the S1-specific compact writer so it publishes this once rather than first creating the generic short success receipt at the same path. |
| `D/s1-calibration-recovery-review-001.md` | Receipt/hash, S1-1..S1-4 decisions, first-result and full membership outcome, resource/cleanup reconciliation, exact limitations, preserved history, terminal stop reason and statement that reconstruction/report/aggregate remain unauthorized. No quality scoring or replacement recommendation. |

Keep existing ledger event names and chained envelope fields `sequence`,
`previous_sha256`, `event_sha256`, `recorded_unix`. Do not rewrite the prefix.
For this S1 path require the following bindings (additive fields do not change
historical events or generic schemas):

| Event | Exact required payload |
| --- | --- |
| `admission` | `evidence` file record for the new admission. |
| `component_recovery_authorized` | `job_id`, `original_job_id`, `authorization`, `original_failure_event_sha256`, plus `semantic_amendment`, `repair_validation`, `configuration`, `original_request_sha256`, `admission` file record. These must agree with the authorization and admitted evidence. |
| `reserve` | `job_id`, `resource=gpu`, `seconds` equal to effective bound, `command`, `monotonic_start`, `boot_id`, `evidence` containing `request`, `worker`, `authorization`, `admission`, `semantic_amendment`, `repair_validation`, `configuration`, `authorization_event`. Reservation is atomic and consumes the sole attempt. |
| `temporary_directory` / `started` | Existing `job_id`, temporary `path`/`native_caches`; `job_id`, `pid`, `pgid` for launch. Retain isolated caches and ownership tracking. |
| `finish` | `job_id`, `resource=gpu`, `status`, `result` or null, `elapsed_seconds`, `peak` (`device_bytes`, `artifact_bytes`, `download_bytes`), `cleanup_confirmed`, `surviving_pids`, `deadline_exceeded`, `failure_kind`, `error`, `stop_required`; additionally link `first_result` and `failure_evidence` when available. Receipt links this event even when worker output is absent. |

If an abrupt interruption prevents a finish event, reconcile the existing owned
attempt under repository rules, preserve its original reservation/timing and
report uncertainty. Never manufacture cleanup, elapsed time or a new attempt.

## Resource admission, execution and terminal stop

Historical consumption is 30 GPU attempts / 4,374.044265462899 seconds, zero
reserved; 89,225.9557345371 GPU seconds remain in time only. CPU preparation/
scoring/report consumed 13,753.206793547044 seconds of 57,600; setup consumed
5,316.549373747828 seconds across 14 historical original/recovery attempts.
Motion and neighbor allocations are already consumed. Latest artifact/download
readings are 67,755,470,848 / 26,213,724,097 bytes; these are historical, not fresh
availability measurements. No new builds or downloads are included.

Before dispatch, refresh the chain and consumption, verify immutable bindings,
measure storage/download accounting and host GPU ownership, and enforce all
common scientific/annotation/runtime gates. Require one exclusive RTX 4090 GPU
process group, no competing compute PIDs, total-device use ≤22 GiB (not merely
allocator memory), ≤8 CPU workers, ≤150 GiB artifact footprint and ≤60 GiB total
new downloads. Never evict another user's process. A missing prerequisite or
unresolved repository stop blocks execution; unused time is not authority.

Compute under reservation lock:

`effective_seconds = min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)`.

Reject nonpositive remainder. Enforce the smaller bound through supervisor
reservation and deadline without altering the frozen configuration or allocating
another attempt. Reserve `min(30, effective_seconds/4)` seconds **inside** that
bound for cleanup. Loading, first-result qualification, all forward/serialization
work, result verification and cleanup are charged; no external smoke timer or
unaccounted tail. Record actual elapsed time even on overrun and flag the breach.

At the later execution stage the sole controller command is:

```sh
.local/envs/stg-colmap/bin/python -B scripts/basketball_vipe_benchmark.py \
  --run-id plan031-20260913T032700Z component-recovery \
  --authorization docs/research/vipe-alternatives/plan031-20260913T032700Z/s1-calibration-recovery-authorization-001.json
```

Use host PID visibility as required by the existing dispatcher. Apply AGENTS.md's
single safe outside-sandbox retry for a suspected permission failure to the
failed operation only, after checking partial state. This is not a model retry:
a reserved/started job is never relaunched. If that retry is denied, unavailable
or fails, stop affected work, report exact command/error and definite versus
suspected sandbox cause, explain existing rule status (print a scoped rule only
if missing), and wait for resolution. Do not bypass denial or compensate with
configuration changes, cached substitutes or CPU fallback.

On interruption, OOM, cap/deadline, lost exclusivity, alignment/semantic/contract
failure or runtime error, stop the owned process group, terminate then force-kill
remaining owned children within the cleanup reserve, verify survivors and record
all partial evidence. Unconfirmed cleanup or a deadline breach requires an
unresolved-stop result; it cannot be labeled a cleaned-up failure or success.

Success requires all 510 exact distorted calibration identities in existing order:
34 cameras × fitting frames `[50,62,75,87,99,100,112,125,137,149]` (340) and
selection frames `[150,162,175,187,199]` (170), no duplicates/missing/extras,
validated hashes/contracts/assignment evidence, first-result pass, runtime and
resource evidence, a supervised successful finish and confirmed cleanup. Held-out
cameras remain localization-only; no new final-window exposure. Partial completion
is failure, even if the first result passed.

Review the terminal receipt, verify preservation of the baseline ledger prefix
and all frozen artifacts, and reconcile only the authorized appended events and
resource charges. Assess S1-1 as retained only if semantic/source/tests remain
valid; S1-2 requires actual validated authorization/admission/ledger binding;
S1-3 may be met by either full completion or a fully evidenced cleaned-up failure;
S1-4 requires unchanged protected bytes and no unrelated allocation. A blocked
pre-dispatch run or unresolved cleanup leaves S1-3 not met. Record uncertainty
rather than declaring the objective achieved without evidence.

**Stop this allocation after the single terminal result and its review, whether
successful or failed.** No automatic second try, reconstruction, report/aggregate
rerun or next improvement iteration. Calibration success alone creates no further
authority. The current PLAN stage ends after saving this file and
`docs/continuous-improvement/plan031-s1-recovery-20260919/plan-link-001.md` and
checking that source, index, ledger and protected artifacts remain unchanged.
