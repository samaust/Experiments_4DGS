# Iteration 7 REVIEW — Identity callback serialization

**Review complete; implementation acceptance incomplete; live S1 admission NOT
READY.** The immediate failure is a test-harness integration defect with a real
validation-coverage consequence. It is not evidence of a broken Identity guard
or S1 semantic algorithm, and cannot be dismissed as a harmless logging artifact.
No source was edited and no aggregate was rerun in this review.

Read objective, current status, assessment-011, validation-006,
implementation-review-005, preparation-006, Plan 037, AGENTS.md, current tracked
diff and relevant untracked implementation, and the production ledger. Exact
input records, diagnostic command/output, source records and preservation checks
are retained in assessment-012.json. This review grants no live authority.

**Exact diagnosis.** In
`tests/test_vipe_benchmark_contracts.py:47`,
`AccessTests.test_heldout_final_window_wrong_branch_and_pair_rejected` passes
`item=item` to `self.subTest`. Each item is the frozen dataclass
`vipe_benchmark.access.Identity`, with branch, camera, frame and pair_start fields.
At `scripts/vipe_benchmark/s1_validation_runner.py:55`, `Result.addSubTest`
converts the parameter mapping to a dict and immediately calls
`json.dumps(parameters, allow_nan=False)`. The nested Identity remains an object,
so JSON raises `TypeError: Object of type Identity is not JSON serializable`
(`when serializing dict item 'item'`). This happens before the callback is appended
and before `super().addSubTest` runs.

The retained traceback shows unittest calling `addSubTest(..., None)`: the first
guard raised its expected ValueError and its assertion had succeeded. The result
callback then raised while leaving the subtest context. Unittest recorded a
method error, aborting the remaining seven loop iterations; later methods and
suites continued. Consequently the failed aggregate contains zero callbacks for
this eight-case method, not eight successful callbacks or eight skipped tests.
Its 148-method count records methods started, not complete branch coverage.

The final iteration-6 aggregate remains **148 methods, 83 recorded callbacks,
zero failures, one error, zero skips, exit 1**, in 48.213986296 seconds. Its
sources-before, sources-after and all 72 current source/config/test records agree.
The 13 helper methods and 12 declared helper cases passed within that failed run;
this does not change its aggregate outcome.

A focused CPU diagnostic in this review executed the same unchanged method twice
using the prescribed environment, `-B` and one-thread limits. A standard unittest
result with observation-only callback capture passed all eight guard assertions
(one method, zero failures/errors/skips). The existing aggregate Result reproduced
one error and zero recorded subtests. No model, device, helper process, production
controller or ledger API was invoked. The diagnostic process exited zero because
it confirmed both expected observations; the current runner did not pass. This
control establishes that these eight guard cases work on current source. It does
not replace a complete final-source aggregate or certify untested guards.

**Smallest correction, for later implementation.** Change only the subtest
parameter at the existing test boundary:

```python
with self.subTest(item=item.record()), self.assertRaises(ValueError):
    guard(item, self.config)
```

`Identity.record()` already returns all four fields via dataclasses.asdict.
The guard still receives the original Identity, with the same invalid input and
assertion. This is a one-line test-harness change; neither Identity nor the guard,
scientific code, runner JSON strictness or acceptance policy needs modification
to eliminate this error. A general dataclass serializer is a larger alternative
and is unnecessary for this demonstrated case. Do not use `default=str`, repr,
field coercion, exception suppression, case removal or a skip: those lose typed
evidence or hide execution gaps. Preserve camera `True` as a boolean, not integer
1, and absent pair_start as JSON null.

The independent ordered callback expectation is the following eight records,
each nested under parameter key `item`, each with status `passed`:

| Order | branch | camera | frame | pair_start | Guard being exercised |
| --- | --- | --- | --- | --- | --- |
| 1 | reconstruction | 0 (int) | 0 | 0 | Held-out reconstruction camera |
| 2 | calibration | 1 (int) | 200 | null | Final-window frame |
| 3 | depth | 0 (int) | 100 | null | Held-out depth camera |
| 4 | depth | 1 (int) | 176 | null | Wrong depth frame |
| 5 | reconstruction | 1 (int) | 21 | null | Missing pair context |
| 6 | reconstruction | 1 (int) | 22 | 20 | Wrong pair member |
| 7 | calibration | 1 (int) | 21 | null | Wrong branch/role |
| 8 | calibration | true (bool) | 100 | null | Boolean camera rejected |

Compare order, multiplicity, keys, values, types and outcomes against this
predeclared expectation, not against values generated from the new receipt.
Canonical strict JSON or recursive type-aware equality avoids Python's
`True == 1` trap. The existing declaration comparator uses ordinary equality;
that broader weakness remains an acceptance gate. With only the one-line label
change, the expected aggregate is 148 methods and 91 callbacks (83 + 8), with
contracts contributing 15 methods and eight callbacks. These are predictions
from current source, not executed results or permanent hardcoded targets. Added
tests/declarations require fresh independent collection and adjusted expectations.

**Exact required rerun.** After the correction and all changes intended for that
checkpoint are final, run one complete serial aggregate from the repository root:

```sh
OMP_NUM_THREADS=1 OPENBLAS_NUM_THREADS=1 .local/envs/stg-colmap/bin/python -B - <<'PY'
import runpy
import sys
sys.path.insert(0, "scripts")
runpy.run_module("vipe_benchmark.s1_validation_runner", run_name="__main__", alter_sys=True, init_globals={"STDIN_PYTHON_ARGV": tuple(sys.argv)})
PY
```

Ensure `S1_HELPER_DIAGNOSTIC` is unset; its value `1` selects only the helper
diagnostic. Keep the exact four stdin lines and final newline. Use the guarded
importable runner; a contracts-only command, ordinary unittest pass or module-file
launcher does not replace this invocation. Verify launcher argv
`['.local/envs/stg-colmap/bin/python', '-B', '-']`, original Python argv `['-']`,
runpy argv and resolved interpreter (currently `/usr/bin/python3.14`).

| Serial suite order | Current method count | Expected callbacks after only the correction |
| --- | ---: | ---: |
| s1_semantics | 5 | 6 |
| s1_recovery | 13 | 37 |
| backends | 35 | 24 |
| contracts | 15 | 8 |
| component_recovery | 3 | 4 |
| execution | 10 | 0 |
| budgets | 31 | 0 |
| supervisor | 28 | 12 |
| review_annotations | 8 | 0 |

Require zero discovery errors, failures, errors and skips, exit zero, all ordered
method IDs and typed callbacks accounted for, and agreement between logs,
per-suite totals and the aggregate. Retain exact stdin/runner bytes, stdout/stderr,
actual process status, argv/interpreter/thread environment, UTC and monotonic
timing, and source/config/test membership and hashes before and after. Reconcile
independently before calling the aggregate passed. Run the Plan 037 preservation
check `git diff --check -- . ':(exclude)prompts/**' ':(exclude)**/prompts/**'`.
Any later source/test/runner edit requires another full aggregate; do not splice
this review's diagnostic into acceptance evidence.

Preserve `s1-recovery-aggregate-006-001` and validation-006 as failed evidence.
Publish fresh immutable records under next unused names; the current runner
automatically advances its hardcoded `006` run suffix, so the immediate next
aggregate directory would be `s1-recovery-aggregate-006-002` if still unused.
Explain that provenance in the successor validation rather than renaming or
overwriting history. Recheck suffix availability. The later implementation
checkpoint retains Plan 037's 1,800-second inspection-inclusive wall cap, final
180-second evidence reserve, at most eight CPU workers including helper/native
threads, serial suites and one-thread helper pools. Capture the clock before
inspection; do not retrospectively repair earlier missing timing.

**Acceptance remains broader than this correction.** Static inspection finds
18 parameterized methods; only two have runner-loaded literal HELPER_CASES
declarations (12 cases). Restoring the missing eight callbacks will close this
immediate execution gap only. Complete literal declarations and strict production
receipt guards remain required; `s1_recovery.validation_record` currently checks
that parameterized methods have nonempty subtests, not exact typed tuples.

| Gate | Disposition after this review |
| --- | --- |
| F6-1 | Partial: actual stdin spawn and guarded-file control passed in iteration 6; synchronous Process.start and Connection.recv still lack proven bounds/readiness coverage. |
| F6-2 | Narrow worker context/shared-peak correction supported by recorded owned-live, unreaped-exited, foreign, mixed and prelaunch cases. Later-phase ownership coverage remains open. |
| F6-3 | Partial: retained helper ownership and consumed cleanup stop supported; fake exception labels do not inject real enumeration/kill/reap failures, and the real descendant case exercises worker stop_group, not spawned-helper descendants. |
| Plan 036 package 1 | Applicable-boundary mutations, synchronized locked contenders, continuation and consumed replay matrix remain incomplete. |
| Package 2 | Trusted reservation clock/allocation, structured primary/secondary failures, corruption/storage/death/CLI tables remain incomplete. |
| Package 3 | Exact unique produced/qualified partial counts, 340/170 categories and durable incremental evidence surviving helper timeout remain incomplete. |
| Package 4 | Ready helper set, bounded transport/descendants, sample freshness, monitoring through cleanup/finalization, reserve subdivision, conservative charge and durable acknowledgment remain incomplete. |
| Package 5 | Full literal declarations, strict receipt metadata guards, numerical/runtime/envelope cases and real stages.segment progression through all 510 rows remain incomplete. |
| V1 | Required aggregate executed and failed in iteration 6; new final-source aggregate required after the smallest correction. |

| Objective criterion | Assessment |
| --- | --- |
| S1-1 | Partial; prior semantic support retained. Source-bound S0 token sums, first-phrase tie rule and native evidence preservation remain supported by unchanged amendment/source records and the five semantic methods in the aggregate. Identity reporting failure does not refute them; broader acceptance matrices remain incomplete and no repaired live output is established. |
| S1-2 | Not met. Admission code is partial, CPU acceptance failed, inherited binding/resource gates remain open, and no production S1 recovery authorization/registration exists. |
| S1-3 | Not met. No bounded recovery was attempted; the original cleaned-up failure is historical evidence, not a new recovery outcome. |
| S1-4 | Preserved within audited scope. Frozen records, historical outcomes, production ledger, status and index are unchanged; no scientific rerun or unrelated allocation occurred. |

The read-only audit matched all 72 sources, 38 frozen records, 40 recorded prior
loop records, six bookkeeping transitions and five aggregate evidence files.
All 69 preexisting files under this loop directory are recorded for preservation.
The current tracked diff is 79,284 bytes, SHA-256
`d08127f2dc779e89a31343514c1eef797f171f326cecde20fc03eb6d957459a5`.
The production ledger has 447 valid chained events, 332,437 bytes, SHA-256
`2a0f66e38911b0ed029eb9dd0cf4bbd5da4a3b67abb577fbfe9ad67e6a888990`,
head `00cab019d73b6a3205f676b54cfb2f745f492fa5cca5c69b4567087cea62172b`.
It is byte-identical to assessment-011 and the original baseline: no active
reservation or S1 recovery event; failures 250/255 and R-S skip 256 remain.
Recomputed GPU totals remain 30 attempts, 4,374.044265462899 seconds elapsed,
zero reserved; all other resource totals also match.

Only review-007.md and assessment-012.json are added to the repository. Existing
status and all prior evidence stay unchanged. No GPU/model/device operation,
production ledger mutation, authorization, registration, staging, commit,
delegation, scientific rerun or prompts read occurred. Historical P31-5,
unavailable older status bytes and inspection-inclusive timing caveats remain;
this review does not certify missing historical timing. One later calibration
attempt, at most 3,600 GPU seconds inside the existing cumulative ceiling, still
requires all gates and separate DO authority. Reconstruction remains separately
authorized later work. A passing repaired aggregate alone grants neither.
