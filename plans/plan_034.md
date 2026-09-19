# Plan 034 — Repair S1 recovery fixtures and complete CPU validation

Iteration 3 PLAN, 2026-09-19. Status: planned; implementation remains incomplete
and is not ready for live admission.

## Scope and stage boundary

Continue the [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md)
and [Plan 033](plan_033.md), using
[review-003](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-003.md),
[assessment-004](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-004.json)
and the preserved
[failed validation-002](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-validation-002.json).
This plan specifies only the remaining shared fixture/evidence corrections,
CPU lifecycle/first-result tests, narrowly necessary guard fixes and source-bound
validation. Preserve Plans 031–033 and all prior evidence.

The present PLAN stage writes only this document and `plan-link-003.md`. No
implementation edits, tests, model/device probes, GPU execution, production
admission, ledger mutation, staging, commits or delegation. Never read `prompts`.
These explicit restrictions override the standing commit and delegation guidance.

The later implementation pass is CPU-only, capped at **1,800 wall seconds and
eight CPU workers**, serial where practical. All lifecycle writes use disposable
temporary roots. The production ledger must remain byte-identical, including
during tests, admission simulations and preparation. Do not invoke controller
commands against production, even as a dry run. Stop at evidence/preparation and
review; passing CPU tests does not authorize live admission or recovery execution.
No staging, commits or delegation are part of this plan.

Exclude reconstruction, R-S, scientific aggregate/report reruns, unrelated arms,
historical accounting repair, model construction/forwards, setup/build/downloads,
smoke runs, calibration regeneration, scoring, final-window evaluation and CPU
fallback for GPU work. The prescribed CPU test aggregate below remains required;
it is not a benchmark aggregate/report rerun. Preserve weights, precision,
thresholds, preprocessing, resolution, SAM refinement, tracking, annotation
policy, environment pins and the existing semantic amendment.

Abbreviations:

- `C = docs/continuous-improvement/plan031-s1-recovery-20260919`
- `D = docs/research/vipe-alternatives/plan031-20260913T032700Z`
- `L = .local/vipe-alternatives/plan031-20260913T032700Z`

## Audited starting point

Validation-002 and the independent review rerun both report **134 tests, zero
failures, 26 errors, zero skips, exit 1**. The 26 error entries comprise nine
errored methods, including 17 errored subtests; the other 125 methods pass.
They share `KeyError: 'baseline_correction'` in `preservation`, reached before
their intended assertions. This is a fixture integration defect, not a device,
dependency or sandbox failure. No tests were rerun during this PLAN stage.

The current shared fixture also lacks nonempty preservation categories and
`baseline.ledger_snapshot`, uses a one-test command-name receipt, omits the
correction from reservation evidence, appends unrelated historical charges after
its snapshot, and supplies abbreviated first-result/finish records. Adding the
missing key alone will not produce a valid positive fixture. F2-0's malformed
label/serialization correction is already verified; preserve it. Its qualification
subcase still fails on missing diagnostics rather than numerical corruption.

The read-only PLAN audit rehashed all **70 source/config/test records** and
**38 frozen scientific records**, read the tracked source diff and untracked
S1 recovery/evidence/tests, and verified all **447 ledger events** and their chain.
The ledger remains 332,437 bytes, SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
with head
`00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
No active reservation or S1 recovery event exists. Original cleaned-up failures
at 250/255 and R-S skipped at 256 remain intact. Historical GPU use remains
4,374.044265462899 seconds across 30 attempts, zero reserved. This establishes
no fresh device availability. The current tracked source diff hash is
`d4236bc0aa7df24029fe50aba130f4073dea742af95cfa4c48a135951f7508b1`.

S1-1 remains supported only in the prior semantic/source CPU scope. S1-2 and
S1-3 are not met. S1-4 remains met within audited scientific preservation scope,
with separate mutable loop bookkeeping and historical P31-5 limitations retained.

## Ordered work and acceptance

| Step | Review findings | Objective | Evidence needed |
| --- | --- | --- | --- |
| 1. Repair the shared fixture and binding chain | F3-0, F3-7 | S1-2, S1-4 | Passing coherent baseline/correction/receipt fixture; intended negative guards reached |
| 2. Complete disposable lifecycle and preservation tests | F3-1 | S1-2, S1-4 | Real admission through resolution, mutation/race/continuation/replay outcomes |
| 3. Complete first-result and E1 evidence tests | F3-2, F3-6 | S1-1, S1-3 | Successful numerical/runtime/envelope fixtures and specific adversarial cases |
| 4. Complete failure, publication and budget tests | F3-3, F3-4, F3-5 | S1-2, S1-3, S1-4 | Accurate durable outcomes and bounded charged acceptance/cleanup |
| 5. Reconcile receipts and publish fresh validation | F3-7 and all above | S1-1–S1-4, CPU scope | Prescribed aggregate, exact sources, preservation audit and finding dispositions |

Limit later edits to the existing recovery/evidence modules and relevant tests,
plus narrow controller, ledger, worker, stage, supervisor or backend corrections
demonstrably required by these cases. Do not refactor unrelated infrastructure
or weaken scientific guards to accommodate a fixture.

### 1. Repair the shared fixture before interpreting negative cases

Update `S1RecoveryTests.setUp` and dependent helpers as one coherent contract:

1. Create real temporary frozen scientific and loop-status files. Capture the
   disposable ledger's exact path/bytes/hash/event count/head after establishing
   its historical prerequisites. Put the snapshot in `baseline.ledger_snapshot`
   and its exact file record, one status record and nonempty scientific records
   in `preserved_records`.
2. Create a matching `plan033-s1-baseline-correction/v1` fixture with baseline,
   plan/review, exact frozen records, ledger snapshot and bookkeeping baseline/
   policy. Bind the same `baseline_correction` into authorization, validation,
   registration and reservation evidence. Update `register` to copy all required
   file bindings, including this correction; retain the canonical request hash
   and event references in their prescribed locations.
3. Replace the positive one-test receipt with contract-shaped required method
   identities, ordered collection, case outcomes and coherent aggregate/per-suite/
   subtest accounting. Use the real current source membership in integration
   coverage. Synthetic receipt data is explicitly test-only, never evidence of
   an actual successful execution. Keep the old command-string receipt as an
   explicit rejection case. Published validation later uses actual execution.
4. Build separate historical fixture states for active/exhausted/reduced-budget
   cases before taking each immutable snapshot. Do not append unrelated charges
   after a snapshot or rebaseline a consumed lifecycle to hide mutations.
5. Supply the complete first-result request/runtime/checks/raw/identity/timing
   envelope and supervised finish `peak` readings. Use real qualification in the
   integration fixture; a fabricated successful finish is insufficient.

First prove a valid binding passes without changing ledger bytes. Every mutation
case must start from that known-good state and assert its intended exception,
phase and rejected operation. Do not catch arbitrary exceptions, permit empty
categories, accept this unrelated `KeyError`, or remove preservation checks.

Keep production baseline-001, correction-001 and failed validations-001/002
immutable. Correction-001 is already bound to Plan 033/review-002; do not silently
claim it binds Plan 034. For fresh Plan 034 validation, publish a successor
`s1-recovery-baseline-correction-002.json` during implementation, retaining the
versioned correction schema and original baseline/snapshot/scientific records,
referencing correction-001, and binding this plan/review-003. Include verified
immutable bookkeeping transition records with old/new hashes and reasons. The
validation and any later authorization must bind that same correction and plan.
Use an unused suffix if necessary; never overwrite an existing record. Do not
restore old status bytes or reset ledger history to manufacture preservation.

### 2. Complete the lifecycle with real guards

Exercise `execute_s1_recovery` calling `common_admission`, then registration,
request construction, reservation, prelaunch, supervisor acceptance, finish,
terminal publication and `result_record`/`resolved_result` on temporary roots.
Fake workers, clocks and device/resource readings only at external boundaries.
Use realistic synthetic E1 assets, input and annotation evidence. Do not mock
`AssetBundle`, source membership, binding, numerical/runtime qualification,
membership or resolution in the acceptance integration path; lower-level unit
fixtures do not substitute for this path.

Enforce three separate preservation categories at each boundary: exact frozen
scientific bytes; exact original ledger prefix and valid chain with only bound,
ordered S1 lifecycle appends; and verified bookkeeping transitions ending at the
current status hash. A matching bookkeeping policy string or event-type filter
alone is insufficient. Reject changed prefix bytes/head, chain corruption,
snapshot substitution, unrelated appends, invalid lifecycle ordering/bindings,
changed scientific files, missing/broken transitions and unrecorded status edits.

Test changes to amendment/parents, configuration, source set, validation,
correction, E1 qualification/assets/runtime, inputs, annotation policy/review,
original failure artifact/event/cleanup, historical and canonical request, and
authorization at the relevant admission/registration/reservation/prelaunch/
resolution boundaries. Include locked concurrent registration/reservation races,
an unrelated active attempt, reduced/exhausted cumulative time, wrong typed scope,
second identity, and replay of consumed identity. Retain generic S1 rejection and
S2 regression behavior. A registered but unreserved identical authorization can
continue after a resolved block; reservation consumes the sole identity even
when no process launches. No deletion/relaunch workaround.

### 3. Prove numerical, runtime and first-result qualification

Create a successful fixture for actual `qualify_row`, `qualify_runtime`,
`verify_first`, `first_record` and `validate_result` before adding corruptions.
Use valid numeric files and hashes without model imports, native builds or extra
forwards. Preserve exact 510 calibration identities and order in successful
worker/acceptance/resolution coverage: 340 fitting and 170 selection rows.

Cover processed RGB shape/finiteness and native resize/normalization, logits to
sigmoid scores, retained query order, normalized-to-pixel boxes, native phrase
bytes, detection index/id and all retained assignments. Include valid zero
detections, ties, ambiguity, empty native phrases, skipped and overwritten
detections. Reject negative/out-of-range semantic indices and changed surviving
id/box/class mappings using the actual native mapping; do not assume surviving
object IDs always equal query indices. Preserve `>0.35` box and `>0.5` text
thresholds and first-max S0 period-delimited token sums, SAM and tracking behavior.
Replace the missing-diagnostics qualification subcase with an otherwise valid
fixture containing a deliberate numerical corruption, asserting the exact guard.

Bind loaded GroundingDINO/SAM source files to admitted asset trees, package files
to the installed inventory, and required native import/build identities to E1
imports/build-input evidence. Self-consistent new file hashes or any file merely
flagged as a mapped native library must not satisfy admission. Test changed
source/native identities with recomputed outer hashes, nested mutations, missing
required files, wrong interpreter, duplicate/aliased paths, empty manifests and
forbidden roots/modules. Qualification uses recorded files; no import probes.

Bind first-result job, camera 0/frame 50/pair_start null, amendment, authorization,
request, runtime, checks, raw evidence and reservation-relative time to the result.
Test each missing/changed field and timing/resource inconsistency. Assert the pass
is durable before frame 62 is loaded. Failure must stop after one adapter call,
retain available raw evidence and prevent the next input. Only an identical,
fully reverified pass allows advancement; failed/not-reached/conflicting records
cannot advance, and a later failure preserves a verified earlier pass.

### 4. Complete durable failure handling and charged publication

Reconcile existing verified worker `failed`/`not_reached` first-result evidence
during supervisor cleanup instead of generating a conflicting replacement with
new phase/error/elapsed fields. Retain immutable originals and reference them.
Test normal early failure separately from actual publication corruption/conflict.
Keep the ledger's `stop_required` and failure classification consistent with the
local values used by `SupervisionFailure` when publication fails.

Make minimal pre-reservation block evidence possible even when authorization is
missing, unreadable, malformed or changed. It must report verification failure
without trusting failed bindings and use a separate immutable block filename.
Do not occupy the consumed-attempt terminal path. Cover block then continuation
of the identical registered-but-unreserved identity.

Preserve runtime as soon as available, including before the first qualified row.
Reconcile produced and qualified partial rows through actual guards; filenames
alone do not establish qualification. Retain identities, semantics, hashes, raw
evidence and accurate produced/qualified/complete and fitting/selection counts.
Handle malformed partial/result/runtime records without aborting minimal terminal
publication or relabeling unverified rows. Test missing result, later-row failure,
abrupt worker/controller death, cleanup uncertainty and all publication failure
boundaries. Preserve the primary exception if raw, first-result, `failure.json`
or terminal writing also fails; attach secondary errors. No absent evidence may
be interpreted as confirmed cleanup, completion or zero produced output.

Include full acceptance, terminal validation/publication and cleanup within the
same charged reservation. Remove the current unbounded 510-row revalidation in
controller terminal publication after supervisor finish. Use bounded validation
and monitoring that cannot re-enter its resource sampler; repeating signal
callbacks alone do not bound blocking native operations. Keep ownership and
resource checks active during prelaunch and acceptance/publication, including
slow hashing, decompression and writes. Recheck time immediately before `Popen`.
Test expiration before launch, slow/blocking operations, ownership change,
memory/disk/download cap breaches and cleanup reserve with fake resources and
controllable workers/clocks. Require timely interruption/cleanup and accurate
charged elapsed time, not only an after-the-fact overrun flag. Retain all 510-row
membership checks; reuse evidence only with current verified bindings.

### 5. Issue fresh source-bound CPU evidence and stop

Record start/end/elapsed time for the entire subsequent implementation pass,
including inspection, fixture work and validation. Preserve prior elapsed values
642.618033546998 and 518.3559243239979 seconds with their original excluded-
inspection caveats; do not reset benchmark budgets. On the 1,800-second limit or
failed/incomplete checks, save truthful partial evidence and stop. No silent
time extension or declaration of readiness.

Run the prescribed nine-suite aggregate with `.local/envs/stg-colmap/bin/python
-B -`, discovering `tests/test_vipe_benchmark_<name>.py` for `s1_semantics`,
`s1_recovery`, `backends`, `contracts`, `component_recovery`, `execution`, `budgets`,
`supervisor`, and `review_annotations`. Focused iterations may precede the final
aggregate, but cannot replace it. Record actual command/argv, stdin, stdout,
stderr, exit code, elapsed time, collection, methods and named/parameterized
subtest outcomes. Reconcile aggregate, per-suite and per-method/subtest accounting
against actual discovery and required cases; do not hardcode 134 or mistake error
entries for independent errored methods.

Reject zero collection, missing/extra/duplicate/aliased/stale sources or cases,
failed/skipped required cases, contradictory method/subtest outcomes, missing
required subtests, inconsistent totals, and disjoint receipts offered instead of
the prescribed aggregate. In particular, passing method counters with failed
subtest records and a one-test command naming all suites must fail. Exercise
receipt rejection using a known-good receipt first; collect these adversarial
tests as part of the same final aggregate.

Recompute the exact resolved duplicate-free `source_paths()` set after all source
and test edits. Bind current source/config/test hashes, amendment and parents,
baseline/successor correction, original failure, historical/canonical request,
E1/input/annotation records and protected scientific outputs. Record a clean
`git diff --check` excluding every `prompts` path; audit ledger full bytes, prefix,
chain, consumption and no new recovery events. Source changes invalidate the
associated validation until checks rerun and a new immutable receipt is issued.

Create only the needed fresh evidence under `C`, taking the next unused suffix:

| Artifact | Required content |
| --- | --- |
| `s1-recovery-baseline-correction-002.json` | Unchanged original baseline/prefix/scientific bindings, predecessor, Plan 034/review-003, verified separate bookkeeping transitions |
| `s1-recovery-validation-003.json` | Existing validation schema, truthful status, Plan 034/Plan 033/review-003/assessment-004 provenance, matching correction, exact sources, actual aggregate and reconciled case/subtest receipts, preservation/diff/time checks, zero GPU jobs and production ledger mutations |
| `s1-recovery-implementation-review-002.md` | Changed paths, validation record/hash, F3-0–F3-7 and inherited F2 dispositions tied to specific tests, scope/limits, elapsed budget, unresolved gates and readiness decision |
| `s1-recovery-preparation-003.md` | Non-executable handoff with actual artifact bindings and pending live gates, or explicit not-ready status when checks remain incomplete |

File records use absolute resolved paths, SHA-256 and integer bytes; event records
use sequence and event hash. Reject forbidden paths, publication conflicts and
JSON NaN/Infinity; preserve nonfinite raw numeric failure arrays without pickles
and describe invalidity separately. Avoid circular hashes: correction precedes
validation, review binds validation, preparation binds both. Test-only synthetic
authorizations never become production approval. Do not create a production
DO-stage authorization, register it, or write into the future job directory.

## Preserved future recovery allocation

The only future identity remains `S1-calibration-recovery-001`, **one attempt of
at most 3,600 GPU seconds**, within the unchanged 93,600-second cumulative ceiling.
Under the reservation lock:

`effective_seconds = min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)`

Reject nonpositive time. Cleanup reserve is `min(30, effective_seconds / 4)` inside
that same allocation. Loading, first-result qualification, serialization, complete
acceptance, terminal publication and cleanup all count. No extra attempt, smoke
process, renamed identity or budget increase.

Retain one exclusive GPU process group, total device memory at most 22 GiB,
eight CPU workers, 150 GiB artifacts, 60 GiB cumulative new downloads, CPU
preparation/scoring/report and setup ceilings of 57,600 seconds each, and zero new
setup attempts/downloads. Fresh resource/ownership and scientific/runtime checks
belong only to a later authorized execution stage. Reconstruction requires
separate later authorization after calibration review; no aggregate/report rerun.

CPU completion requires the successful real-guard lifecycle and first-result
fixtures, intended adversarial failures, bounded cleanup/publication tests, a
passing reconciled nine-suite aggregate, current source bindings and unchanged
production ledger/scientific evidence. It establishes implementation readiness
only. S1-2's production admission and S1-3's actual calibration outcome remain
pending. **Stop after preparation/review; do not execute recovery.**
