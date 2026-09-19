# Plan 033 — S1 recovery CPU corrections and execution preparation

Iteration 2 PLAN, 2026-09-19. Prepared against HEAD
`0184cef74548261d4444ed9ee1e0464da1561b5e` and the existing uncommitted changes.
Status: planned; corrective implementation and fresh validation pending.

## Scope and authority

Continue the [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md)
and [Plan 032](plan_032.md), addressing
[review-002](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-002.md)
and [assessment-002](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-002.json).
This plan narrows the next implementation pass to the malformed-label fixture,
missing amendment-aware lifecycle/first-result CPU tests, the targeted guard and
evidence corrections those tests require, and validation/recovery preparation.
It supersedes Plan 032's immediate progression from implementation into execution.
Preserve Plans 031 and 032 unchanged.

The current PLAN stage creates only this plan and `plan-link-002.md`. No source
or test edits, test execution, GPU/device probes, live admission, authorization
registration, reservation, ledger writes, staging, commits or delegation occur
now. Never read `prompts`. The explicit stage restrictions override the general
AGENTS.md commit and objective delegation guidance.

The later implementation pass is CPU-only and ends with reviewable artifacts.
**Do not mutate the production ledger during implementation**, including via
admission, dry-run controller calls, registration, preflight accounting or test
fixtures. All simulated lifecycle writes must target disposable temporary roots.
Prepare a non-executable recovery handoff; do not create a production DO-stage
authorization or run the recovery. Passing CPU validation does not remove this
stop boundary. Applicable execution-stage authority and all live gates are still
required for the already bounded one calibration recovery.

No reconstruction or R-S, reconstruction/report/aggregate rerun, unrelated arm or
allocation, setup/build/download, smoke/model probe, training, quality scoring,
calibration regeneration, final-window evaluation or CPU fallback is included.
Do not change weights, precision, thresholds, resolution, preprocessing, SAM
refinement, DeAOT tracking, annotations, environment pins or scientific protocol
beyond the existing S1 semantic amendment. No historical accounting repair.

Directory abbreviations:

- `C = docs/continuous-improvement/plan031-s1-recovery-20260919`
- `D = docs/research/vipe-alternatives/plan031-20260913T032700Z`
- `L = .local/vipe-alternatives/plan031-20260913T032700Z`
- `J = L/jobs/S1-calibration-recovery-001` (future execution only)

## Reviewed starting evidence

The [failed validation](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-validation-001.json)
records 134 tests, zero failures, one error, zero skips and exit 1. Review-002
reproduced that error. Its 70 source/config/test records still match; do not
relabel the receipt or substitute the earlier unreceipted 122-test claim.
Five semantic tests passed, preserving S1-1 only within source/CPU scope.
S1-2 and S1-3 remain not met. S1-4 remains met within the review's preservation
scope; mutable loop bookkeeping and historical P31-5 limits remain explicit.

The PLAN-stage read-only audit parsed all 447 ledger events, sequences 0–446,
and verified the chain. Ledger bytes: 332,437; SHA-256:
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`.
Head event:
`00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
No active reservation or S1 recovery event exists. Original cleaned-up failures
at sequences 250/255 and R-S skipped at 256 remain unchanged. All assessment
current source/preservation/result records rehash correctly. No fresh device
availability or model outcome is established by this audit.

Retain the current dedicated S1 schema, exact typed flags, generic S1 rejection,
S2 behavior, E1/source/assets/request/annotation bindings, locked registration and
reservation, cumulative deadline narrowing, and 510-identity membership checks.
Limit edits to the existing S1 recovery/evidence modules and tests, with narrow
controller, worker, stage and supervisor corrections required by findings below.
Do not rewrite the semantic implementation merely to simplify fixtures.

## Ordered work and acceptance map

| Step | Review finding | Objective mapping | Required evidence |
| --- | --- | --- | --- |
| 1. Correct the malformed fixture | F2-0 | S1-1, S1-3 | Exact contract failure at adapter return, one call, durable evidence, no next input |
| 2. Correct baseline interpretation and test admission lifecycle | F2-1, F2-6 | S1-2, S1-4 | Immutable correction manifest; real guards pass disposable admission through resolution and reject mutation/race/replay |
| 3. Complete real first-result qualification tests and guards | F2-2, F2-3, F2-6 | S1-1, S1-3 | Valid numerical/runtime/envelope fixtures pass; specific corruptions fail before next input |
| 4. Complete partial/terminal evidence and deadline tests | F2-4, F2-5, F2-6 | S1-2, S1-3, S1-4 | Durable partial outcomes, accurate phases, safe publication, bounded acceptance and cleanup |
| 5. Issue fresh CPU validation and implementation review | F2-0–F2-6 | S1-1–S1-4, CPU scope only | All nine suites and required cases pass without skips; current source and preservation bindings |
| 6. Prepare the single recovery handoff and stop | Remaining live gates | S1-2, S1-3, S1-4 preparation only | Non-executable readiness document; no production registration/reservation or recovery |

### 1. Put malformed labels at the boundary under test

In `FailureEvidenceTests.test_first_result_failure_stops_before_second_input`,
construct `SegmentationResult` with valid int32 labels. For `kind='contract'`,
convert `prediction.labels` to float32 inside mocked `predict` immediately before
returning it. Preserve constructor and production dtype validation unchanged.
Assert the exact `instances must be int32 on the image grid` error, exactly one
adapter call, `failure_stage='output_contract'`, persisted available raw evidence,
and no second input/result. Give serialization its own precise phase assertion.
Make qualification fail on deliberately corrupt numerical evidence in an otherwise
valid fixture, not a missing diagnostics key. Preserve the original exception.

### 2. Bind the baseline correctly throughout the lifecycle

Keep `C/s1-recovery-baseline-001.json` immutable. Create
`C/s1-recovery-baseline-correction-001.json` in the later implementation stage,
with an explicit versioned schema, source baseline record, Plan 033/review records,
exact frozen scientific records, baseline ledger snapshot and a narrowly defined
preservation policy. Bind the correction into validation and future authorization;
never silently infer it from a changed status file or an authorization-supplied
replacement snapshot.

Separate three categories: exact frozen scientific bytes; the original ledger
byte prefix and its chain; and mutable loop-status transitions recorded separately
with old/new hashes and reasons. Baseline-001 includes both ledger and loop status
in `preserved_records`, causing the present contradiction. Do not restore status
to old contents, rewrite the baseline, reset the ledger or broadly ignore changes.
Future authorized appends must preserve the exact prefix and valid chain and be
restricted to the permitted S1 lifecycle events and bindings. During this CPU
implementation, the entire production ledger remains byte-identical.

Apply this interpretation consistently at admission, registration, reservation,
prelaunch, result resolution and terminal preservation. Reject a different prefix,
modified prefix bytes, unrelated appended allocation, corrupt chain or replaced
frozen record. Tests must contain realistic nonempty baseline categories.

Exercise `common_admission` and `execute_s1_recovery` through the real registration,
reservation, supervisor acceptance, finish and `result_record`/`resolved_result`
path on disposable ledgers, using fake workers and device/resource readings.
Do not fabricate an admission event in place of testing admission or mock the
binding, numerical/runtime, membership or resolution guards under review.
Synthetic E1/input/annotation records must obey the real binding contracts.
No model construction, real forwards or device access is allowed.

Cover changed amendment/parents, configuration, E1 qualification/assets/runtime,
input/annotation policy/review, failure artifact/event/cleanup, source set and
historical-versus-canonical request relation. Cover schema/type/branch/identity
errors, duplicate or aliased records, stale/failed validation, mutations between
each lifecycle boundary, registration/reservation races, concurrent attempts,
second identity, consumed identity replay, and reduced/exhausted cumulative time.
An identical registered-but-unreserved identity may continue after a resolved
block; reservation consumes the attempt even if launch never occurs. No directory
deletion or automatic relaunch. Retain generic S2 regression coverage.

### 3. Exercise real numerical, runtime and first-result guards

Build a successful CPU fixture for real `qualify_row`, `qualify_runtime`,
`first_record` and `validate_result`, then mutate one bound fact per rejection
case. Keep model/device work fake, with valid numeric arrays and runtime files.

Verify processed RGB shape, finiteness and relationship to the frozen native
resize/normalization; query selection/order, raw normalized-to-pixel box conversion,
detection id/index, scores and independently captured native phrase consistency.
Check every retained query, including skipped/overwritten detections, and accept
valid zero detections. Reject the review's NaN shape-[1] processed RGB and altered
pixel-box examples. Keep native thresholds `>0.35` and `>0.5` and first-max S0
period-delimited sigmoid-token sums for every retained query; valid empty native
text, ties and ambiguity remain acceptable. Labels/static and footprint/provenance
contracts remain unchanged.

Validate the loaded-runtime schema, interpreter, required module/native records,
their current hashes, admitted E1 identity and forbidden roots/modules. An empty
manifest, changed nested file or wrong interpreter must fail even when its outer
file hash is valid. Bind first-result job, explicit identity, amendment,
authorization, request, runtime, checks, raw evidence and reservation-relative
timing to the result envelope. Reject missing, changed or inconsistent fields.

Only an identical, fully reverified passed first-result record is reusable for
advancement. Existing failed/not-reached/conflicting records block advancement.
A later failure preserves a verified earlier pass. Test publication conflicts
and timing inconsistencies. First input is camera 0/frame 50/pair_start null;
the pass must be durable before frame 62 is loaded. A failed check stops there
with one adapter invocation, available evidence and no diagnostic extra forward.

### 4. Finish evidence lifecycle and bounded acceptance

Persist immutable completed-row metadata and runtime records incrementally so
later failure retains identities, semantics, hashes and available outputs. Distinguish
produced, qualified and complete counts, including fitting/selection counts, and
retain runtime even when no final `result.json` exists. Capture failure phase
before each serialization/qualification operation; prevent stale prior-frame
capture and preserve the primary exception if evidence writing also fails.

Use separate immutable pre-dispatch block records, including initial binding
failure, without occupying the fixed consumed-attempt terminal receipt name.
Later continuation of an unreserved identity must remain possible. Publish one
terminal receipt for the consumed attempt; reuse only identical verified evidence,
and report publication conflicts without replacing the original failure. Derive
completion from qualified evidence, exact membership, supervised finish, cleanup,
resource compliance and preservation checks, never just `finish.status`.

Test clean failure, failure after several completed rows, missing result, abrupt
worker/controller death, cleanup uncertainty, pre-reservation block/continuation,
first-result conflict and terminal publication failure. Never manufacture a pass,
cleanup confirmation or zero output count when evidence proves otherwise.

Check remaining time immediately after prelaunch binding and before `Popen`.
Make full-result validation and evidence publication bounded and interruptible,
with resource/deadline checkpoints through acceptance; avoid repeatedly loading
the same input manifest. Test slow hashing/decompression/validation/publication,
expired prelaunch time, cap breaches and cleanup reserve using fake clocks,
resources and workers. An after-the-fact overrun flag alone is insufficient.
Do not weaken exact 510-row membership/order at worker, acceptance or resolution.

### 5. Publish complete CPU evidence

Timebox the subsequent corrective implementation/validation pass to 1,800 wall
seconds and at most eight CPU workers, serial where practical, as specified by
review-002. Record actual start/end/elapsed time, retaining the prior pass's
642.618033546998-second receipt and its excluded-inspection caveat. No benchmark
budget reset or uncharged live preflight is implied. On timeout or failing checks,
save truthful incomplete/failed evidence and stop before recovery preparation is
declared ready; do not extend the pass silently.

Run the nine Plan 032 suites with `.local/envs/stg-colmap/bin/python -B`:
`s1_semantics`, `s1_recovery`, `backends`, `contracts`, `component_recovery`,
`execution`, `budgets`, `supervisor`, `review_annotations`, using patterns
`tests/test_vipe_benchmark_<name>.py`. Preserve the prescribed aggregate run and
record per-suite collection/results and required test/subtest identifiers from
that run. No required case may be skipped, missing or collected as zero. Replace
suite-name substring acceptance with verification of actual collected/executed
suite/case receipts and matching totals. Test rejection of a one-test receipt
whose command merely names all suites. Do not hardcode 134 as the new test count.

Record exact command/argv, stdin, stdout, stderr, exit code, counts, individual
outcomes and elapsed time. Run `git diff --check` with `prompts` excluded. Rehash
the dynamically recomputed exact, resolved, duplicate-free `source_paths()` set,
amendment/parents, configuration, baseline/correction, input/annotation/E1 records,
protected scientific outputs and ledger prefix/full ledger; verify its chain and
absence of new recovery events. Source/config/test edits invalidate the associated
validation until relevant checks rerun and fresh immutable evidence is issued.

Create these artifacts exclusively under `C`, using the next unused suffix if a
proposed name has since been occupied; preserve all older receipts and bind actual
paths and hashes, never assume Plan 032's proposed `D` locations exist:

| Artifact | Required content |
| --- | --- |
| `s1-recovery-baseline-correction-001.json` | Step 2's immutable policy, original baseline and prefix bindings, exact scientific records, separate bookkeeping transition evidence |
| `s1-recovery-validation-002.json` | `plan031-s1-recovery-validation/v1`, truthful status, Plan 033 and Plan 032 provenance, baseline/correction, semantic amendment, configuration, complete current sources, exact aggregate/per-suite/case receipts, diff/preservation/ledger checks, elapsed scope, zero GPU jobs and production ledger mutations |
| `s1-recovery-implementation-review-001.md` | Changed paths, validation record/hash, F2-0 through F2-6 dispositions tied to actual tests, inherited review-001 obligations, S1-1..S1-4 scope/limits, budget use, unresolved gates and readiness decision |
| `s1-recovery-preparation-002.md` | Step 6's non-executable handoff, exact artifact bindings and outstanding live gates; no claim of execution authority or model success |

File records contain absolute resolved `path`, `sha256` and integer `bytes`;
event references contain `sequence` and `event_sha256`. Reject forbidden paths,
conflicting immutable publication and JSON NaN/Infinity. Preserve nonfinite raw
failure arrays without pickles and explain invalidity separately in JSON.
Prevent circular artifact hashes: validation binds source/tests and correction;
implementation review binds validation; preparation binds both. Future
authorization binds the finished chain, never an unfinished review.

### 6. Prepare recovery only, then stop

Document how a later execution stage will assemble the dedicated calibration
authorization from the actual passing validation/review/correction, semantic
amendment, original cleaned-up calibration failure, historical and canonical
requests, E1 runtime/assets, inputs, annotations and baseline prefix. List the
normal controller entrypoint and immutable artifact/ledger contracts from Plan
032, amended by steps 2–4. Do not invoke it, register authorization, write into
`J`, or claim the current PLAN/CPU stage is a DO instruction. A draft must be
visibly non-executable and must not carry live approval flags as granted.

The sole later identity remains `S1-calibration-recovery-001`: one attempt, at most
3,600 GPU seconds within the unchanged cumulative 93,600-second ceiling.
Under the reservation lock:

`effective_seconds = min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)`

Reject nonpositive time and reserve `min(30, effective_seconds / 4)` for cleanup
inside that bound. Loading, qualification, serialization, full validation,
publication and cleanup are charged within the same allocation. No second
process attempt, new identity, smoke run or resource-ceiling increase.

Retain one exclusive GPU process group, total device memory ≤22 GiB, ≤8 CPU
workers, ≤150 GiB artifacts, ≤60 GiB cumulative new downloads, CPU preparation/
scoring/report and setup ceilings of 57,600 seconds each, and zero new setup
attempts/downloads. Historical GPU use is 4,374.044265462899 seconds across 30
attempts with none reserved. That accounting establishes no fresh host capacity.
Refresh ownership, resources, chain/consumption and all scientific/annotation/
runtime gates only at a later authorized execution stage.

Future acceptance requires the first-result gate and all 510 exact calibration
identities in order (340 fitting, 170 selection), validated hashes, supervised
finish and confirmed cleanup, or truthful preserved evidence of a cleaned-up
failure. Blocks or unresolved cleanup cannot satisfy S1-3. Preserve original
failures/charges and all frozen outputs. Stop after that sole future terminal
review; reconstruction requires separate later authority and R-S disposition.

The implementation handoff must explicitly leave S1-2's production admission
and S1-3's actual outcome pending. CPU success can establish implementation
readiness only. **This plan ends at preparation and review, without execution.**
The present PLAN stage ends after writing its two requested documents and
verifying unchanged source, index, ledger and existing protected records.
