# Plan 039 — Enforce S1 CPU receipt declarations and execution metadata

Iteration 9 PLAN, 2026-09-20. Implements **R9-1 only**. This is a CPU evidence
milestone supporting S1-2; overall implementation acceptance and live admission
remain incomplete. Plans 031–038 retain their unclosed requirements.

Authority and inputs: [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md),
[review-009](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-009.md),
[assessment-017-review](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-017-review.json),
[Plan 036](plan_036.md), [Plan 038](plan_038.md),
[validation-007](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-validation-007.json),
and [correction-006](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-baseline-correction-006.json).
The explicitly resumed continuous-improvement-loop skill supplies standing
approval for this new plan's finalized CPU allocation. Main orchestrates one
stage agent at a time and owns status changes and local commits; the stage agent
must not delegate or perform git writes. Follow AGENTS.md permission retry/stop
rules and never read `prompts` content.

## Allocation and boundaries

Capture UTC and monotonic start **before any implementation inspection**, in the
first implementation action. This new allocation is **1,800 wall seconds** for
inspection, edits, validation, audit and handoff; the final **180 seconds are
reserved for evidence**. Stop execution/refinement at elapsed 1,620 seconds.
Do not begin a test unless its entire timeout fits before that cutoff. This does
not reset any historical clock or consumed allocation.

Allow at most **three focused diagnostic invocations**, each at most **120
seconds**, and **two complete aggregates**, each at most **300 seconds**, all
inside the same 1,800 seconds. An invocation consumes an attempt when launched,
even if discovery fails or the child never starts tests. A second aggregate is
permitted only after a source change or a recorded concrete failure/concern
invalidates the first; no routine repetition. A permission retry consumes wall
time and a further attempt if a new test process actually launches. Never replay
a successful write or run after a permission failure. If the authorized safe
retry cannot fit, preserve the failure and leave execution incomplete.

Maximum **eight CPU workers including native/helper threads**; suites execute
serially, helper thread pools are one, and OMP, OpenBLAS, MKL and NumExpr thread
environment values are all `1`. Budget time for a full aggregate before optional
refinement. No model evaluations, GPU attempts/device probes, setup/download/
smoke jobs, production controller calls (including dry runs), production ledger
APIs/mutations, or production job directories. Use disposable fixtures only.
Read-only file/hash/AST and git diff checks are evidence work, not additional
permission to launch diagnostics. No historical scientific aggregate/report,
R-S, D1 fit/check or reconstruction rerun.

Preserve the semantic amendment, retained native boxes/phrases/scores, thresholds,
weights, precision, preprocessing, SAM refinement/tracking, pins, annotations,
scientific inputs and current substantive assertions. Do not repair R9-2–R9-6
within this plan. If a newly exposed unrelated failure prevents validation,
record the failed aggregate and hand off the exact finding rather than weakening
an assertion or expanding this implementation.

## Starting evidence and allowed files

Review-009 independently matched all **72 current source/config/test records**
to validation-007. Its saved aggregate passed **148 methods and 91 callbacks**.
These are historical observations, not hardcoded targets for new tests. Current
production `validation_record` ignores callback parameters and most metadata;
its fixture uses arbitrary `(synthetic)` IDs. The runner declares only two
methods/12 callbacks and compares values using Python equality. Validation-007
uses a different wrapper from the production admission contract (`aggregate`
rather than `tests`); changing only its status cannot make it usable.

Implement in `scripts/vipe_benchmark/s1_recovery.py`,
`scripts/vipe_benchmark/s1_validation_runner.py`, a new shared
`scripts/vipe_benchmark/s1_validation_contract.py`, and a small outer capture
module `scripts/vipe_benchmark/s1_validation_capture.py`. Keep the shared module
independent of runner execution and test imports; avoid import cycles by placing
suite/launcher constants and static collection there and retaining compatibility
wrappers in `s1_recovery` where existing callers need them. Update the nine
existing suite files for declarations; place new contract tests in
`tests/test_vipe_benchmark_s1_recovery.py` so the prescribed nine-suite aggregate
collects them. Add only new run artifacts under the existing recovery directory.
No supervisor, worker, ledger, model, semantic-algorithm or configuration change
is authorized by this receipt milestone.

## 1. Literal case declarations and typed callback identity

Use exactly one module-level literal `SUBTEST_CASES = {...}` assignment in each
of the nine suite files, including `{}` in files with no parameterized methods.
Keys are full unittest method IDs; values are ordered nonempty tuples/lists of
parameter dictionaries. Each parameter dictionary has string keys and primitive
values only: exact `str`, `bool`, `int`, finite `float`, or `None`. Normalize
list/tuple *declaration sequences* to a list; preserve every parameter value's
type. Do not coerce boolean/integer/float/null values into each other. Dictionary
key order has no semantic role; callback list order and multiplicity do.

Move the existing loops onto these declared tables. Subtests pass the declared
primitive fields with `self.subTest(**case)`. For nonprimitive existing parameters,
represent the same input with primitive fields and reconstruct it locally:
`altered`/`changes` dictionaries become `field` plus `value`; frame lists become
`frame_0`, `frame_1`, and, where present, `frame_2`; Identity records become
`branch`, `camera`, `frame`, `pair_start`. Existing scientific operations and
assertions use the reconstructed original values. Mutation inputs such as NaN
arrays remain in local lookup tables keyed by declared primitive `field` labels;
do not turn nonfinite model test input into a nonfinite receipt parameter.

The following 18 current methods must retain their original cases and order.
Prefixes below are `test_vipe_benchmark_<suite>.`; inspect source for unchanged
input values and assertions. Additional parameterized tests need declarations
under the same contract.

| Suite | Class.method | Existing callbacks |
| --- | --- | ---: |
| s1_semantics | S1SemanticsTests.test_contract_rejects_missing_or_tampered_assignment | 6 |
| s1_recovery | S1RecoveryTests.test_typed_scope_schema_branch_and_second_identity | 9 |
| s1_recovery | S1RecoveryTests.test_validation_missing_extra_duplicate_aliased_stale_and_failed_receipts | 9 |
| s1_recovery | S1RecoveryTests.test_changed_prerequisite_records_rejected | 9 |
| s1_recovery | S1RecoveryTests.test_result_requires_supervised_cleanup_and_exact_membership | 4 |
| s1_recovery | FailureEvidenceTests.test_alignment_layout_pre_forward_and_no_stale_capture | 3 |
| s1_recovery | FailureEvidenceTests.test_first_result_failure_stops_before_second_input | 3 |
| backends | AssetAndDetectorTests.test_phrase_ambiguity_and_capacity_fail_before_casting | 4 |
| backends | SAM2Tests.test_native_postprocessing_skip_fails_pair_and_resets_before_export | 2 |
| backends | SAM2Tests.test_source_frames_not_internal_indices_or_cross_role_context | 4 |
| backends | S1NativeBridgeTests.test_constructor_rejects_changed_arguments_and_unsupervised_temporary_root | 4 |
| backends | S1NativeBridgeTests.test_native_wrapper_argument_drift_is_rejected_before_engine_construction | 4 |
| backends | S1NativeBridgeTests.test_pair_bridge_rejects_extra_frames_reference_and_propagation | 4 |
| backends | FactoryTests.test_sam3_unobserved_or_repeated_checkpoint_load_cannot_qualify | 2 |
| contracts | AccessTests.test_heldout_final_window_wrong_branch_and_pair_rejected | 8 |
| component_recovery | ComponentRecoveryTests.test_scope_validation_and_cumulative_cap_are_not_relaxed | 4 |
| supervisor | HelperIntegrationTests.test_cleanup_matrix | 6 |
| supervisor | HelperIntegrationTests.test_cleanup_failures | 6 |

Static collection reads AST only; never import test modules during admission.
Use the fixed suite order and unittest class/method lexicographic order. Inspect
raw `ast.Dict` keys before `literal_eval` so duplicate keys cannot disappear;
reject duplicate assignments, duplicate method keys across suites, nonliteral
expressions/unpacking, empty declarations, unknown/extraneous method IDs and
missing declarations for every collected method containing `subTest`. Reject
unsupported indirect/dynamic parameterization rather than silently omitting it.
Declaring a nonparameterized method is an error. Duplicate declared typed tuples
are rejected; preserve all existing distinct inputs. Flatten nested unittest
parameter maps to ordinary primitive dictionaries when recording callbacks.

Use one type-aware canonical comparison shared by admission and the runner.
A tagged identity such as `(type-name, value)` per sorted field is sufficient;
ordinary Python equality is not. Define callback `id` deterministically from
parent method ID plus this canonical typed identity, using the shared function;
retain raw unittest display ID in a separate diagnostic field if useful. No
production dependency on Python's mutable display formatting is necessary.
Require each callback identity, parameters and status to match the declaration
in order, with no missing/extra/repeated callback. Nonparameterized methods must
have exactly `subtests=[]`. Parent and callback statuses must both be `passed`.

## 2. One complete receipt contract, with an acyclic evidence chain

Use a new explicit inner schema `s1-cpu-aggregate/v2`, outer schema
`s1-cpu-execution/v1`, and wrapper schema
`plan031-s1-recovery-validation/v2`. Reject legacy/incomplete v1 evidence for
new admission; preserve all old files as history. The wrapper has exactly one
`tests` entry containing strict file records `receipt` and `execution` for the
inner and outer documents. It also binds semantic amendment, configuration,
plan, original baseline, successor correction and exact current `sources`.
Do not accept a second alternate embedded receipt as authoritative. Optional
human summaries must not replace or contradict the bound documents.

The inner document describes what the runner observed; it cannot know its own
final OS exit status. Replace the old ambiguous inner `exit_code` with
`expected_exit_code`. The outer capture describes the actual process completion.
The final wrapper binds both after completion. Dependencies must be only:

`source/stdin/closed inner logs -> inner receipt -> outer execution -> validation`

The outer execution additionally binds its own finalized source snapshot, exact
stdin and closed process logs. No document hashes itself, a future wrapper,
or a mutable file containing its own digest. Capture source belongs to
`source_paths()` before execution. Audit/correction and wrapper ordering must
also avoid mutual file-record references; use plain successor names for forward
navigation where needed.

Required inner fields and shared checks:

- Schema, `diagnostic=false`, exact nine-suite order, and unique collected method
  IDs exactly equal to static collection and ordered executed parent IDs.
  `discovery_errors=[]`; no unexpected skips, missing cases or extra suites.
- Complete literal declarations, exact callback parameters/IDs/statuses,
  per-suite collected IDs and outcomes. `tests_run`, `subtests_run`, failures,
  errors and skipped counters are exact nonnegative `int`, never `bool` or
  numerically equivalent floats. Derive totals from actual case statuses and
  callbacks, and reconcile suite and aggregate counters. Passing requires all
  failures/errors/skips zero, nonempty methods, `passed is True`, and exact-int
  `expected_exit_code == 0`. Failures remain truthful failed artifacts.
- `sources_before` and `sources_after` are identical ordered strict file-record
  lists, equal to the wrapper's current `source_paths()` membership and current
  bytes/hashes. Include new runner/contract/capture/test files; compute count,
  do not retain 72 as a constant. Reject duplicates, missing, extra, aliased,
  changed-byte and stale records. All record sizes are exact nonnegative ints,
  hashes are correctly formed, and paths are canonical resolved existing files.
- Strict records for the exact prescribed `stdin.py`, runner source snapshot,
  closed inner stdout/stderr logs; stdin bytes equal the shared four-line
  constant below, and runner snapshot bytes equal current runner source. File
  records must validate actual content, not just match other supplied records.
- Invocation has exact launcher argv, saved pre-runpy Python argv `['-']`, and
  runpy argv `[str(current_runner_path.resolve())]`; `sys.executable` and its
  resolved path agree with the specified environment's Python, whose strict
  executable record is bound. Check requested invocation and observed argv
  coherently, including `-B -`, no extra flag/module/file and repository cwd.
  `launcher_argv` comes from actual process command line; expected argv is
  `[ '.local/envs/stg-colmap/bin/python', '-B', '-' ]` with repo cwd. The outer
  driver must launch that exact relative executable argv. Require all four
  thread variables `1`, `VIPE_CPU_VALIDATION='1'`, and diagnostic mode unset.
- UTC timestamps are timezone-aware UTC ISO-8601 strings; monotonic values and
  elapsed values are finite nonnegative exact int/float, excluding bool. Require
  start <= end, elapsed equal monotonic difference (absolute tolerance 1e-6),
  suite intervals serial/nonoverlapping and contained in the runner interval,
  and each suite elapsed consistent. UTC order must also be nondecreasing;
  do not equate UTC duration with monotonic duration. Record boot identity for
  inner/outer clock comparison. A clock anomaly invalidates evidence rather
  than inventing timestamps.

Outer capture writes an immutable execution document only after `wait` obtains
actual return code. It records requested argv/cwd/env, launch and wait-completed
UTC/monotonic timestamps, elapsed, child PID, boot ID, exact-int `returncode`,
`timed_out` bool, strict inner receipt/stdin/runner/capture/interpreter records,
and complete raw process stdout/stderr records. Require returncode zero,
`timed_out is False`, inner/outer boot IDs identical, inner timing contained in
outer timing, and outer elapsed at most the allocated invocation cap. Process
returncode must equal inner expected exit code. No numeric alias is accepted.

Choose the run directory before launch and pass it to the runner through an
explicit environment variable; both sides record and agree on it. Keep each
attempt in a new directory (`s1-recovery-aggregate-009-001`, next unused suffix).
The capture submits the exact four stdin lines, redirects complete output to
files and enforces the invocation timeout, preserving timeout/failure evidence.
Successful runner output is fully inside its tee capture: remove/move the
post-receipt `RECEIPT ...` print so inner and outer stdout/stderr bytes can be
required equal. Bootstrap errors or trailing process output then cannot be
silently hidden by the runner's captured subset. Raw logs may legitimately be
empty; do not invent a minimum stdout length or use `OK` text as the proof.

The runner uses the shared **inner** validator after closing its logs; admission
uses that same validator and validates the outer/wrapper links. The runner must
not require the outer record before its own completion. External capture cannot
be inferred from an inner self-reported zero. The implementation stage's final
review independently reads actual capture command completion from the execution
tool/session, verifies the driver observed/propagated the child's returncode,
and reconciles every bound raw file. Save that observation separately and bind
it in the audit. The outer document is unsigned evidence, not cryptographic
attestation; structural coherence does not alone prove a real run occurred.

Wrapper `diff_check.exit_code` is exact int zero, with recorded stdout/stderr
and exact command `git diff --check`. Its `status='passed'` means the CPU
aggregate passed. Carry distinct booleans `aggregate_passed`,
`receipt_milestone_complete`, `implementation_acceptance_complete`,
`ready_for_live_admission`, and `objective_complete`. The last three remain false
here; do not imply that this CPU subvalidator closes unrelated readiness gates.

## 3. Truthful fixture and targeted mutation coverage

Replace the incomplete `S1RecoveryTests.setUp` receipt with a complete disposable
v2 graph. Build its expected methods and parameter tuples from source declarations,
never observed callbacks. Create matching temporary stdin/runner/log/inner/outer
files, coherent finite timings/argv/environment, strict current source records,
and all wrapper parents. Give the fixture an explicit annotation such as
`provenance='synthetic fixture; no execution performed'` and truthful test-only
log content. Admission uses exactly the same schema/guards for these bytes;
there is no fixture flag that skips validation and no fabricated tool-session
claim. Such a graph proves structural checks in a temporary root only. All live
execution conclusions come from fresh captured execution plus independent audit.

Create a lightweight fixture builder for direct receipt tests to avoid repeatedly
constructing heavyweight image/controller assets. Keep existing admission tests
using their actual disposable ledger/binding path. Every negative case must
start from a fresh **demonstrably passing** fixture, make one named mutation,
update legitimate enclosing file hashes as needed to reach the intended guard,
and assert a focused rejection message/class. Do not blanket-mock the validator.
For negative file hash cases, intentionally leave the target record stale.

Required mutation groups (parameterize with literal tables; keep runtime bounded):

1. Declaration parsing: missing/dynamic/duplicate assignment or method key,
   extraneous/nonparameterized declaration, duplicate tuple, nonprimitive or
   nonfinite value. Test parser input via disposable source text; never mutate
   real test files during an aggregate.
2. Callback integrity: missing/substituted/reordered/duplicated tuple, removed
   parameter field, extra field, changed typed value, `True` versus `1`, `1`
   versus `1.0`, null versus a string/value, wrong callback ID, extra callback
   on an ordinary method, passed parent with failed/error/skipped callback.
3. Collection/accounting: missing/extra/reordered/duplicated method/suite,
   discovery error, nonzero or inconsistent aggregate/suite/callback counts,
   bool and equivalent-float counts, bool/float diff exit, incomplete schema.
4. Binding: missing/stale/aliased bytes for stdin/runner/log/executable/source,
   duplicate/missing/extra source membership, unequal before/after lists;
   inner/outer records from distinct otherwise passing fixtures. Rehash enclosing
   containers to demonstrate link/identity checks rather than only stale hashes.
5. Execution: wrong argv/flag/interpreter/cwd/env/diagnostic mode, malformed UTC,
   nonfinite/negative/reversed/inconsistent/out-of-envelope times, boot mismatch,
   missing wait evidence, nonzero/bool/float returncode, timeout true, process
   logs differing from runner logs, source changed after the captured run.

Run both direct shared-validator tests and production `validation_record` tests
for representative callback and metadata mutations. Include one test establishing
that the old incomplete synthetic receipt and validation-007-style wrapper are
rejected without relabeling history. New tests must be collected by the fixed
nine-suite aggregate; do not satisfy the requirement with manual probes alone.
Keep all original assertions, including eight contracts callbacks and helper
bootstrap/cleanup tests. Their counts are derived anew after source finalization.

## 4. Exact execution and independent reconciliation

Finalize every source/test/declaration change before the aggregate. The child
process must be exactly the existing stdin/runpy launch form, from repository
cwd, with the four thread variables `1`, `VIPE_CPU_VALIDATION=1`, diagnostic mode
unset, and `.local/envs/stg-colmap/bin/python -B -` receiving these exact bytes:

```python
import runpy
import sys
sys.path.insert(0, "scripts")
runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})
```

The file ends in one newline. Run suites in exactly this serial order:
`s1_semantics`, `s1_recovery`, `backends`, `contracts`, `component_recovery`,
`execution`, `budgets`, `supervisor`, `review_annotations`. Preserve existing
CPU guards that reject real GPU probing. Focused invocations may select only
receipt/declaration tests through explicit focus configuration recorded as a
diagnostic; they never qualify as the aggregate and consume the diagnostic cap.
Add no import-time runner behavior that breaks spawned helper bootstrap.

Independently reconcile final static collection, complete typed declarations,
every callback/order/status, suite and total counts, no skips/discovery errors,
exact stdin, argv, interpreter, environment, source membership/bytes before and
after, runner/capture snapshots, raw logs, timings, and observed actual process
completion. Calling the same shared validator alone is not an independent audit;
use a separate read-only reconciliation script plus direct file/command review.
A newly edited source invalidates an earlier pass and requires the permitted
second aggregate; never patch the saved receipt to current hashes. At exhaustion,
save partial/failure evidence and identify exactly which acceptance items remain.

## 5. Immutable bookkeeping and handoff

Main supplies IMPLEMENT status before dispatch, first preserving PLAN status
as `s1-recovery-status-before-implement-009.md`, then freezes those status bytes
during this stage. Preserve correction-006 and all prior transitions verbatim.
Extend its last observed status (`7ff80bbe...`, 1,872 bytes) through actual saved
successors: `s1-recovery-status-before-008.md` preserves that endpoint;
`...before-009.md` preserves the subsequent blocked status;
`...before-plan-009.md` preserves resumed-review status; the new
`...before-implement-009.md` preserves PLAN status; current `status.md` is the
IMPLEMENT endpoint. Verify each old/new hash from the actual saved bytes, and
append one new immutable transition per change, carrying snapshot file records
and accurate reasons. Do not invent unavailable older bytes or modify history.

Create next-unused successor correction (currently `...correction-007.json`),
validation (currently `...validation-008.json`), independent audit, implementation
review, preparation note and stage assessment. Use numbered immutable files and
retain attempts, timing consumption, input/output hashes, failure logs and exact
remaining gates. Successor correction preserves original baseline, frozen
records, ledger snapshot, bookkeeping baseline and prior transition prefix,
adds actual transitions, and binds the current plan/review. Final validation
binds that correction. Keep the dependency graph acyclic; neither correction nor
its predecessors need to bind the future final validation.

Audit the original 38 frozen records, prior failures/scientific aggregates/report,
amendment/S0 sources and production ledger using read-only bytes. Ledger remains
**447 events, 332,437 bytes**, SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`, chain head
`00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
Preserve historical 30 GPU attempts, 4,374.044265462899 seconds, zero reserved,
failed finishes 250/255 and R-S skip 256. Git index changes from authorized
commits are bookkeeping; do not label them scientific corruption. Historical
P31-5 and unavailable older status/timing evidence remain explicit limitations.

Report the fixed status hash to main before correction finalization. Main owns
any later status update, preserving old bytes and issuing a new transition and
correction successor if a new current binding is required. Do not rewrite a
finalized correction or validation to follow mutable status. Main inspects the
staged task-only diff and creates the required local milestone commit after
validation; no push/amend/history rewrite. A checkpoint does not end the active
loop: main proceeds to fresh review of remaining work under the skill.

## Acceptance and remaining objective

Plan acceptance requires all five: complete source-driven literal declarations;
strict shared typed receipt/metadata enforcement; truthful positive fixtures and
collected targeted mutations; fresh successful exact aggregate with independent
execution reconciliation; and immutable correction/preservation/timing handoff.
A partial milestone or aggregate pass is reported separately from plan acceptance.

| Criterion | Effect and required evidence |
| --- | --- |
| S1-1 | Retain met within its saved amendment/source/CPU definition; semantic assertions and inputs preserved, semantic suite passes in new aggregate. No live-output claim. |
| S1-2 | Advance R9-1 via strict production receipt guard and fresh bound evidence; remains not met overall while other guards and production authorization/registration are absent. |
| S1-3 | Remains not met; no recovery attempt/result in this plan. |
| S1-4 | Verify preservation audit and exact unchanged ledger; bookkeeping uses immutable transitions. |

Retain later R9-2 helper startup/transport/sample-freshness bounds; R9-3 trusted
reservation clock/effective allocation and first-result timing; R9-4 durable
incremental evidence surviving interruption; R9-5 primary/secondary failures,
cleanup/finalization observation, charge and acknowledgment; R9-6 result/row
numerical envelope and genuine CPU segment progression. Full applicable-boundary,
contender, continuation/replay and typed lifecycle matrices remain open coverage.
A later review/plan selects the next bounded milestone; this plan grants no
execution allocation for those repairs and no live recovery authority.

Only a later authorized DO stage after **all** CPU gates close may consider the
single `S1-calibration-recovery-001` attempt. Preserve positive effective seconds
`min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)`, all preparation,
loading, qualification, publication, cleanup and finalization charged, and
cleanup reserve `min(30, effective_seconds/4)` inside the cap. Reservation consumes
the attempt even without launch. Keep one exclusive GPU group, 22 GiB memory,
eight CPU workers, 150 GiB artifacts, 60 GiB downloads and existing 57,600-second
preparation/setup ceilings. No new setup/download/smoke allocation; reconstruction
requires separate later authorization after calibration review.
