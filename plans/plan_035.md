# Plan 035 — Close S1 recovery admission and bounded-publication gates

Iteration 4 PLAN, 2026-09-19. Status: planned; CPU implementation acceptance
incomplete; live admission closed.

## Scope and authority

Continue the [objective](../docs/continuous-improvement/plan031-s1-recovery-20260919/objective.md)
and [Plan 034](plan_034.md), using
[review-004](../docs/continuous-improvement/plan031-s1-recovery-20260919/review-004.md),
[assessment-006](../docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-006.json),
[validation-003](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-validation-003.json)
and [implementation-review-002](../docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-implementation-review-002.md).
This plan replaces only the unfinished implementation sequence; Plans 031–034
and all earlier evidence remain immutable.

The present PLAN stage creates only this document and `plan-link-004.md`. It
does not edit source, run tests or GPU work, stage, commit, delegate, or mutate
the production ledger. Never read `prompts`, including through aliases. These
explicit restrictions override standing commit/delegation guidance.

The subsequent implementation is **CPU-only, at most 1,800 wall seconds and eight
CPU workers**. Start timing before inspection, reserve time to save evidence,
and stop with truthful partial results on exhaustion or an explicit stop. Use
only disposable ledgers and job roots for tests. Keep the production ledger
byte-identical throughout implementation and preparation; do not call production
controller commands even as a dry run. No staging, commits or delegation are
included. CPU completion ends with validation, review and a non-executable
preparation record. A later authorized execution stage may admit the single
calibration recovery only when every gate below passes. This PLAN is not a
production DO authorization.

Exclude reconstruction, R-S, scientific aggregation/report reruns, scoring,
final-window evaluation, other arms, historical accounting repair, input or
annotation regeneration, calibration regeneration, model construction/forwards,
setup/build/downloads and smoke jobs. The required CPU unittest aggregate is
distinct from scientific aggregation. Preserve the amendment, S0 token-sum
policy, native boxes/phrases/scores, `>0.35` box and `>0.5` text thresholds,
precision, weights, preprocessing, resolution, SAM refinement, tracking,
annotation policy, environment pins and existing budgets.

Paths used below:

- `C = docs/continuous-improvement/plan031-s1-recovery-20260919`
- `D = docs/research/vipe-alternatives/plan031-20260913T032700Z`
- `L = .local/vipe-alternatives/plan031-20260913T032700Z`
- `J = S1-calibration-recovery-001`

## Audited starting point

Validation-003 records a passing nine-suite aggregate: **135 methods and 79
subtests, zero failures/errors/skips, exit 0**. Its status correctly remains
`incomplete`; required behaviors were not all collected. No tests were rerun
in this PLAN stage. F3-0's shared-fixture correction and F2-0's malformed-label/
serialization fix remain credited; the latter's numerical-corruption subcase
is still missing. Retain the existing positive AssetBundle, row/runtime and
510-row resolution fixture and lower-level semantic/native-refinement tests.

Current source confirms the remaining defects: `common_admission` omits
`baseline_correction`; the fixture fabricates admission and finish and patches
source membership; preservation permits orphan lifecycle events; CLI parsing
precedes protected block publication; consumed terminal parsing can abort the
receipt; partial counts trust filenames; terminal runtime omits initial runtime;
controller terminal publication repeats full validation after supervisor finish;
the repeating signal sampler is reentrant and lacks continuous ownership checks;
required subtest membership is only checked for nonempty presence.

The PLAN read-only audit rehashed all **70 source/config/test records** and
**38 frozen scientific records**, reviewed the tracked diff and untracked S1
implementation/tests, and verified all **447 ledger events**, their chain and
current bookkeeping transitions. The ledger is 332,437 bytes, SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
head `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
No active reservation or S1 recovery event exists. Original cleaned-up failures
250/255 and R-S skip 256 remain intact. Historical GPU use is 4,374.044265462899
seconds across 30 attempts, zero reserved. This is not a device-availability
claim. Current tracked diff SHA-256, excluding forbidden paths, is
`d0022638529f8b162f77f75930751b3f4e66c1d056af92bd8f99b48940dd9bb9`;
the staged diff is empty.

S1-1 is supported within semantic/source CPU scope; S1-2 and S1-3 are not met.
S1-4 retains its audited scientific-preservation scope. Historical P31-5
limitations and unavailable older status bytes are not repaired or relabeled.

## Minimum implementation sequence

| Order | Review criterion | Required completion |
| --- | --- | --- |
| 1 | F4-1 / L1 | Bind correction everywhere; execute real disposable controller lifecycle |
| 2 | F4-2 / L2 | Enforce ordered, evidence-bound lifecycle at locks and boundaries; test races/replay |
| 3 | F4-3 / P1 | Durable minimal failure/block evidence and verified partial accounting |
| 4 | F4-5 / P2 | Acceptance, cleanup and publication inside a hard-bounded charged reservation |
| 5 | F4-4, F4-6 / A1–A4 | Complete numerical/runtime/envelope/receipt cases and corresponding guards |
| 6 | F4-7 / V1 | Fresh source-bound CPU aggregate, preservation audit, review and preparation |

Limit edits to `s1_recovery.py`, `s1_evidence.py`, their existing tests and narrow
changes in `execution.py`, `ledger.py`, `supervisor.py`, `stages.py`, the benchmark
CLI and worker needed by these cases. Touch backend/contracts only for a
demonstrated guard gap. Do not rebuild credited work or refactor unrelated paths.
Keep generic S1 recovery rejection and S2 recovery regression coverage.

### 1. Bind the correction and prove real admission (L1)

Copy the exact `baseline_correction` file record into `common_admission` evidence.
Require equality through authorization, validation, admission, registration,
reservation, prelaunch and terminal acceptance/resolution. Keep it in `BINDINGS`;
do not silently infer it from another document or accept a missing/default value.
The authorization's plan and baseline must equal those in its correction and
validation. Verify predecessor and review records in a successor correction,
not merely the top-level file hash.

Keep baseline-001, corrections-001/002 and validations-001/002/003 unchanged.
During implementation create `C/s1-recovery-baseline-correction-003.json`, using
the existing correction schema, predecessor correction-002, Plan 035, review-004
and assessment-006 provenance. Retain the original ledger snapshot, scientific
records and bookkeeping baseline. Carry forward all verified transition records.
Prefer leaving status unchanged until an explicit final bookkeeping transition;
if status changes, preserve its prior bytes and append an immutable old/new
hash/byte/reason transition before finalizing the successor correction. Never
rebaseline the ledger, restore old status to manufacture preservation, or claim
the unavailable historical status bytes were independently reconstructed.

Promote the existing synthetic evidence helpers into a disposable integration
fixture that calls `execute_s1_recovery` -> real `common_admission` -> locked
registration -> canonical request -> reservation -> prelaunch -> supervisor ->
worker evidence -> acceptance/cleanup/publication -> finish -> `result_record`/
`resolved_result`. Use actual `source_paths()` membership, real AssetBundle,
input/annotation admission, binding, row/runtime qualification and resolution.
Supply complete synthetic qualification and annotation records to those guards.
Fake only external model/worker/device/resource/clock boundaries. Do not fake
admission, manually append the recovery finish, or patch a scientific guard.
Historical synthetic prerequisites may be constructed before their snapshot.

The positive path must accept exactly 510 ordered identities: 340 fitting and
170 selection rows. Assert the correction's exact file record at every boundary
and resolve the supervised recovery without altering the original failed arm.
First prove this fixture succeeds; all negative cases start from this valid
state and assert the intended exception/phase and prevented operation. A missing
fixture key, unrelated early failure or catch-all exception is not acceptance.

### 2. Validate the lifecycle, preservation and consumption (L2)

Add one read-only lifecycle validator that accepts the caller's locked event
snapshot. Reuse it in binding, registration, reservation, prelaunch and terminal
resolution without recursive ledger locks or recovered-result lookup.

After the exact baseline prefix, allow only this evidence-bound progression:

1. Zero or more immutable blocked admissions for this exact authorization,
   followed by one successful admission with all required evidence.
2. One registration referencing that admission, authorization, original failure
   and all `BINDINGS`; continuation reuses it without another registration.
3. One reservation referencing that registration event, admission, canonical
   request and current worker. It consumes J even if `Popen` never occurs.
4. At most one temporary-directory event and one start, in that order after
   reservation. An ownership-failure event is allowed only in the active
   reservation, with its phase and evidence. A failed finish can follow a
   prelaunch failure with no start. Success requires a start and accepted result.
5. One finish bound to the reservation and durable terminal receipt. No further
   recovery start/reserve/finish or unrelated append is permitted.

Reject orphan starts/finishes, duplicates, out-of-order events, changed references,
wrong job/authorization and unrelated appends even when their hashes form a valid
chain. Repeated observations of ownership failure may be recorded only as
phase-bound diagnostics within the same active reservation, never as a new
lifecycle. Serialize admission/registration decisions and recheck under the
existing ledger lock so competing controllers cannot create duplicate successful
admissions. A losing registration/reservation race must not launch a worker.

Keep three distinct preservation checks: exact frozen scientific bytes; exact
original ledger prefix/hash/head and valid append chain; verified bookkeeping
transitions ending at current status. Test byte/head/chain/snapshot substitution,
scientific mutation, unrelated appends, missing/broken transitions and unrecorded
status edits. Never append historical test charges after a snapshot; create
separate historical fixtures for active/reduced/exhausted budget cases.

Parameterize boundary mutations at admission, registration, reservation,
prelaunch and resolution for each applicable dependency: amendment and parents,
config, source membership/hashes, validation, correction/predecessor, authorization,
E1 qualification/assets/runtime, inputs, annotation policy/review/amendment event,
original failure artifact/event/cleanup, historical request, canonical request,
worker and event references. Recompute outer hashes where needed to reach the
inner guard. Record any genuinely inapplicable boundary explicitly in the matrix.

Use synchronized disposable contenders to test simultaneous registrations and
reservations with real locks. Assert one registration/reservation/launch at most,
no deadlock and intended loser rejection. Cover unrelated active attempts,
reduced/exhausted cumulative time, wrong typed scope, a second identity, block
then continuation of the identical registered-but-unreserved authorization, and
replay after consumption. A consumed identity never resumes, retries or changes
its name; registration without reservation can continue only after revalidation.

### 3. Publish durable failures independently of optional evidence (P1)

Make S1 selection possible before decoding authorization: add an optional fixed
`--job S1-calibration-recovery-001` selector to `component-recovery`. Route this
explicit selection through the protected S1 entry before file hashing/parsing;
validate any decoded document against that identity. Preserve existing generic
dispatch and rejection behavior. A malformed untyped document must never imply
S1 authority; reject it with an immutable unverified block record. The later S1
handoff uses the explicit selector. Test the CLI entry, not only its helper.

Separate minimal outcome construction/publication from guarded evidence parsing.
Before reservation, missing/unreadable/malformed/changed authorization produces
an immutable block receipt with supplied path, available verified record,
verification errors, `attempt_consumed=false` and observed ledger head. It does
not occupy J's consumed terminal path or append a fabricated authorization.
After reservation, use trusted reservation/registration identity to record
consumption even when authorization, result, partials or runtime become corrupt.
Optional parse/hash failures must not abort construction of the minimal outcome.
Remove eager partial parsing through `dict.get` defaults.

Reconcile readable evidence inside the reservation: reference initial, partial
and final runtime independently with verification state; qualify each readable
partial through the actual row guard; retain identity/order, semantics and raw
records. Separate produced, qualified and complete counts and fitting/selection
counts. Use verified counts/lower bounds and explicit `unknown` for missing or
unverifiable totals. Filenames and missing files never prove qualification or
zero production. Completion requires all 510 identities and all guards.

Retain verified worker `failed`/`not_reached` first-result records during cleanup;
do not rewrite their phase/time/error. An earlier verified pass survives later
failure. Test real conflicts/corruption separately. Guard directory creation,
serialization, write, hash and immutable-publication conflict at raw evidence,
first result, `failure.json` and terminal boundaries. Preserve the primary
exception, attach secondary publication errors and keep local and ledger
`failure_kind`/`stop_required` consistent. No successfully resolvable finish may
follow a publication failure.

Required cases include first adapter failure, numerical first-result failure,
later-row failure, missing/corrupt result/partial/runtime, abrupt worker death,
controller death/missing finish and cleanup uncertainty. If storage is wholly
unwritable, retain the primary error in available logs/ledger evidence and report
publication unavailable; do not claim a durable receipt exists. If the controller
or supervisor dies before finish, leave the identity consumed and unresolved,
never infer cleanup or launch again. A surviving supervisor performs bounded
cleanup; an unresolved reservation requires later explicit reconciliation, not
an automatic recovery attempt.

### 4. Charge and bound acceptance, cleanup and publication (P2)

Keep the single reservation open until full acceptance, cleanup and durable
terminal publication have completed. Split pre-finish acceptance from historical
`resolved_result`; terminal publication consumes verified acceptance evidence
and must not call the post-finish resolver or repeat the unbounded 510-row pass.
Acceptance still verifies every row, exact order, first-result/runtime and all
current source/request/preservation bindings. Later read-only resolution verifies
the finish/receipt/acceptance bindings and current referenced bytes; it must reject
mutation, not silently trust a cached status or launch recovery work.

Use a supervisor monitor outside the terminable acceptance/publication worker.
Do not run slow hashing, decompression, parsing or writes on the monitor thread,
and do not use repeating SIGALRM callbacks to invoke sampling. Sampling runs
serially in a bounded helper with at most one request in flight. A missed or
failed sample is a stop condition, never an assumed healthy reading. Use a
monotonic monitor tick no longer than 100 ms and sample timeout no longer than
one second or remaining phase time, whichever is smaller. Helpers are CPU-only,
remain within eight workers, and join the supervised cleanup set; they do not
create a second GPU job or model process. The monitor can terminate blocked
acceptance/publication and sampler helpers independently of Python/native work.

Recheck deadline, ownership and resource caps after slow prelaunch checks and
immediately before `Popen`. Continue checks after worker exit, during acceptance,
publication and cleanup. Detect foreign GPU PIDs without signaling unrelated
processes; terminate only owned work and report ownership/cleanup uncertainty.
Stop accepting new expensive work at the work deadline; use the in-allocation
cleanup reserve for termination and minimal failure publication. Reduced budgets
shorten helper timeouts and cleanup waits rather than extending the deadline.

Publish an immutable terminal receipt before finish, binding reservation/event
references, acceptance/result/first-result records, observed resources, cleanup
and outcome. Avoid circular hashes: the receipt references preceding events;
the finish references the receipt hash and records the final measured elapsed
charge. Receipt timing is explicitly measured through its preparation; the finish
is authoritative for elapsed time including publication/cleanup. A receipt alone
cannot establish completion without the matching finish. Keep final ledger write
within the deadline allowance and account for its finalization scope explicitly;
an incomplete write/finish cannot be resolved as success. Do not hash/write a
second terminal receipt or repeat acceptance in controller `finally` after finish.

Use real controllable CPU children for blocking-work tests, with fake resource
readings and short budgets. Test expiration immediately before launch; blocking
hash/decompression/sample/write; no sampler reentry; foreign PID before launch,
after worker exit and during acceptance/publication; memory/artifact/download
cap changes in monitored phases; reduced effective time and cleanup reserve;
failed terminal publication and worker/controller death. Assert timely termination,
no leaked owned processes, consumption, accurate elapsed charge and failure
classification. An after-the-fact overrun field alone does not pass.

### 5. Close adversarial coverage and its source guards (A1–A4)

Use the existing valid numeric/runtime helpers. Each table entry becomes a stable
named case or `subTest(case=<stable id>, boundary=<phase>)` with expected guard
and outcome. Keep exact required identities in literal source-bound case tables
alongside test data; `required_cases` reads their declarations without importing
tests, models or native libraries. Compare the exact expected parameter tuples
and method order, not merely nonempty or unique subtests. Include every collected
parameterized method in this contract; aliases and substituted identities fail.

| ID | Required cases and assertions |
| --- | --- |
| A1 numerical | Valid zero detections, ties, ambiguity, empty phrases, skipped oversized detections and overwritten survivors through real row qualification. Corrupt processed RGB shape/finiteness/resize/normalization; raw logits/sigmoid probabilities/nonfinite arrays; retained query order/threshold alignment; normalized-to-pixel boxes; native UTF-8 bytes/offsets; detection index/id/score and every retained assignment; negative/out-of-range semantic index and surviving id/box/class. Rehash outer records to reach intended numeric/native mapping guards. |
| A2 runtime | Changed loaded GroundingDINO/SAM files outside admitted trees; missing/changed E1 import file/symbol/source; inventory mismatch; wrong correlation build identity; unrelated mapped native library and missing admitted `groundingdino._C` mapping; nested mutations, missing required files, wrong interpreter, duplicate/aliased paths/modules, empty manifest and forbidden roots/modules. Verify actual admitted-to-loaded relationships with recomputed outer hashes, without imports/builds/forwards. |
| A3 envelope/worker | Missing/changed schema/status/job, camera 0/frame 50/pair_start null, count/row identity, amendment, authorization, request, runtime, checks and raw evidence; nonfinite/negative/out-of-effective-reservation time and inconsistent resource/timing records. Run real `segment` with fake backend and valid evidence. Assert durable pass before loading frame 62, exact 510 order and 340/170 split, one adapter call on first failure and no second input, identical fully reverified pass reuse only, stale/conflicting/failed/not-reached records preventing advancement, and later failure preserving the earlier pass/raw evidence. |
| A4 receipts | Known-good contract-shaped fixture first; reject zero collection; missing/extra/duplicate/aliased/stale sources or cases; failed/error/skipped methods or subtests; passing method with failed subtest; missing/substituted/duplicate required parameter tuple; wrong order, counts, totals or aggregate metadata; one-test command naming all suites; multiple disjoint receipts. Include these rejection tests in the final aggregate itself. |

Replace the worker test's missing-`diagnostics` qualification subcase with an
otherwise valid serialized fixture containing actual numerical corruption;
assert the exact numerical guard, failure phase, preserved raw evidence and one
adapter call. Exercise `zero=True` and `skip=True` helpers in collected cases.
Preserve native surviving-ID remapping; do not equate object IDs to query indices.
Add only source guard corrections exposed by these intended cases.

Fixture receipts are labeled synthetic and exist only in disposable roots. They
may obey the receipt contract to exercise admission but never count as actual
validation or production authority. Execution evidence must record actual argv,
stdin, collection and outcomes; a command string containing suite names is not
proof of their execution.

### 6. Rerun source-bound CPU validation and issue the handoff (V1)

After final source/test edits, run one prescribed ordered aggregate using
`OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .local/envs/stg-colmap/bin/python -B -`.
Its recorded stdin discovers `tests/test_vipe_benchmark_<name>.py` in this order:
`s1_semantics`, `s1_recovery`, `backends`, `contracts`, `component_recovery`,
`execution`, `budgets`, `supervisor`, `review_annotations`. Focused iteration
runs may precede it; they cannot substitute for the aggregate. CPU fakes ensure
no models, device probes, downloads or production controller writes occur.

Capture actual command/argv, full runner stdin, stdout/stderr, process exit,
UTC/monotonic start/end/elapsed, ordered discovered IDs, per-method and exact
subtest outcomes, per-suite and aggregate counters. Reconcile actual unittest
discovery with static required membership and the emitted receipt. Require zero
failures/errors/skips and no missing case. Do not hardcode 135/79 or confuse
errored subtest entries with errored methods. Source guards must enforce A4's
metadata, membership and outcome rules; independently reconcile the actual
execution artifacts in review rather than trusting synthetic fixture receipts.

Recompute the exact resolved, duplicate-free `source_paths()` set after edits,
including any new helper/table files if introduced. Bind current source/config/
test hashes, amendment and parents, baseline/correction, original failure/event,
historical/canonical request, E1/runtime/assets, inputs and annotation records.
Run `git diff --check -- . ':(exclude)prompts/**' ':(exclude)**/prompts/**'` and
audit all frozen records, full ledger bytes/prefix/chain/head/consumption, no
new production recovery events and unchanged index. Any source/test/required-case
change invalidates its validation and requires a fresh aggregate/immutable receipt.

Record whole implementation timing from inspection, capped at 1,800 seconds.
Preserve prior 642.618033546998 and 518.3559243239979-second measurements with
their excluded-inspection caveats, and the 848.010818-second conservative bound
with its unknown exact start. Do not reset benchmark counters or write CPU
charges to the production ledger in this implementation stage. If budget or
checks fail, issue `incomplete` evidence and stop; no silent extension or readiness.

Create fresh records under C, using the next unused suffix on collision:

| Artifact | Required content |
| --- | --- |
| `s1-recovery-baseline-correction-003.json` | Predecessor correction-002, unchanged original baseline/prefix/scientific bindings, Plan 035/review-004/assessment-006, verified bookkeeping chain |
| `s1-recovery-validation-004.json` | Existing validation schema; truthful status and coverage completion; Plan 035/Plan 034/review-004/assessment-006 provenance; matching correction; exact sources and executed aggregate/cases; preservation/diff/timing checks; zero production ledger mutations/GPU jobs |
| `s1-recovery-implementation-review-003.md` | Validation hash, changed paths, disposition of F4-1–F4-7 and L1/L2/A1–A4/P1/P2/V1 tied to exact tests, inherited findings, timing and limitations, explicit readiness decision |
| `s1-recovery-preparation-004.md` | Non-executable handoff with actual artifact bindings, sole identity and effective-budget formula, tested CLI selection, remaining live gates; explicit NOT READY if any criterion remains open |

Use absolute resolved paths, SHA-256 and integer byte counts for files; sequence
and event hash for events. Reject forbidden paths, publication conflicts and
JSON NaN/Infinity. Preserve invalid nonfinite raw arrays without pickles and
describe invalidity separately. Finalize correction before validation; review
binds validation; preparation binds both. Preserve all old receipts even when
superseded. Do not create/register production DO authorization or create J's
production job directory during implementation.

## Conditional admission of the one calibration recovery

The later execution stage can proceed only if all L1/L2/A1–A4/P1/P2/V1 criteria
are closed by current-source evidence and review, explicit applicable DO-stage
authority exists, and fresh scientific/runtime/resource/ownership checks pass.
A passed test counter or edited validation status is insufficient. Admission
must reject stale source/correction/status bindings and any consumed identity.

Create the production authorization only in that later stage, using the existing
`vipe-benchmark-s1-amendment-calibration-recovery/v1` schema. Bind Plan 035,
baseline and successor `baseline_correction`, amendment, final validation/review,
configuration, original cleaned-up failure and event, E1 qualification/assets/
runtime, inputs/annotations/policy/review/amendment event, historical request,
canonical request hash and ledger baseline. Retain typed one-attempt/calibration
scope and all `LIMITS`; record the actual execution-stage authority. Rehash before
admission and again under registration/reservation locks. No synthetic fixture
or preparation document substitutes for this authority.

Only **J, one attempt, at most 3,600 GPU seconds** is available. Under the lock:

`effective_seconds = min(3600, 93600 - gpu_elapsed_seconds - gpu_reserved_seconds)`

Reject nonpositive time or any unrelated active attempt. Cleanup reserve is
`min(30, effective_seconds / 4)` inside that same allocation. Loading, inference,
first-result qualification, serialization, full acceptance, evidence hashing,
terminal publication and cleanup are charged. Reservation consumes the sole
identity even if prelaunch fails; no renamed allocation, smoke process or retry.
If blocked before reservation, continuation is allowed only for the identical
unconsumed registered authorization after the blocking condition resolves.

Retain one exclusive GPU process group, at most 22 GiB total device memory,
eight CPU workers, 150 GiB artifacts, 60 GiB cumulative new downloads, and
57,600-second preparation/scoring/report and setup ceilings. New setup attempts,
downloads and extra smoke jobs remain zero. Fresh resource checks occur in the
later execution stage and continuously within its monitored reservation.

The execution outcome must be either a fully qualified 510-row calibration with
durable first result/raw/runtime evidence and matching charged finish/receipt,
or a truthfully recorded failure/block with consumption, partial/unknown counts,
primary/secondary errors and cleanup state. Cleanup uncertainty or publication
failure is a stop, never a successful cleaned-up result. Keep original failures,
scientific artifacts and prior accounting intact; only the bound lifecycle may
append to the ledger in this later execution stage.

Stop after that single calibration outcome and its review. Reconstruction needs
separate later authorization after calibration review. Do not run R-S, scientific
aggregation or reports. CPU readiness alone does not complete S1-2's production
admission or S1-3's live outcome; report those separately and truthfully.
