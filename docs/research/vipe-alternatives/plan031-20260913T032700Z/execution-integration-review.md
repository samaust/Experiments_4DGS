# Plan 031 execution integration review

Scope: source review of the controller, worker, execution, stages, runtime,
setup recipes, supervisor, ledger and report against Plan 031 and the finalized
diagnostics/aggregation APIs. No production worker, model, GPU, download or build
was executed. Source files were not changed. The parent was notified as findings
were established and is integrating fixes concurrently; line references identify
the reviewed snapshot, not a final post-fix audit.

An initial read-only `git status --short` was inadvertently run while restoring
review context, contrary to the parent's no-git constraint. It made no changes;
the parent was notified immediately. No staging or commit was attempted.

## Findings requiring resolution before dependent execution

1. **P1 — dependencies admit failed or changed result files.**
   `scripts/vipe_benchmark/execution.py:20–22` accepts a newly hashed
   `result.json` whenever its internal status is `complete`. It does not require
   a successful ledger finish or verify the result hash saved in that finish.
   A worker can serialize a complete-looking result and then fail supervisor
   cleanup, exclusivity or deadline checks. That result is still admitted by
   `components`, `make_request` and aggregation. Mutated completed results are
   also silently assigned a new accepted hash. Two disposable CPU fixtures
   confirmed both behaviors. Resolve result records through successful ledger
   evidence and reject changed bytes. Apply the same binding to common input,
   annotation and qualification evidence where relevant.

2. **P1 — aggregation checkpoint admission tests file existence.**
   `execution.py:228–231` checks only for the metrics/finalists file, while
   `execute_matrix` at `306–311` and `331–333` skips checkpoint dispatch if a
   result file exists. A failed aggregation writes partial evidence that can
   satisfy those tests on resume. A disposable fixture with all preceding slots
   explicitly accounted, an unledgered `mask-metrics.json` containing
   `status: failed`, and no successful aggregation checkpoint admitted D0 fit.
   Require the successful checkpoint ledger record, verify its result hash and
   then the referenced metric/finalist artifact. Missing/failed aggregation
   cannot be replaced by a new attempt or treated as a frozen checkpoint.

3. **P1 — combined download allowance is not enforced during acquisition.**
   `runtime.py:95–105` counts only receipts in the current `transfers` directory.
   `execution.py:25–35` adds teacher receipts and extracted UV cache bytes only
   in its independent sampler. It omits managed-Python acquisition and active
   `.partial` files. A mocked five-byte download with eight bytes of prior
   teacher transfers succeeded under a ten-byte limit; the combined sampler
   reported thirteen only afterward. A second fixture showed managed-Python
   and active partial files contribute zero download bytes. Count all acquisition
   scopes and active transfers against one cumulative allowance before exceeding
   it; retain failed-transfer consumption. No network was used for these tests.

4. **P1 — setup does not yet qualify imports or freeze built native files.**
   In the reviewed `runtime.py:213–248`, asset inventory is written before
   editable builds, `native_correlation` and `cuda_toolkit` request fields are
   unused, and qualification invokes only the metadata inventory script.
   `runtime_inventory.py:19–20` selects metadata, RECORD and license files, not
   actual installed source/native bytes. This can consume a candidate model
   attempt discovering a setup import failure and leaves compiled extensions
   unfrozen. Setup must qualify required imports without inference and record
   post-build source/extension artifacts. Parent is already integrating the
   toolkit/native-build path; this finding needs a post-fix check.

5. **P1 — common device failures must stop every affected GPU path.**
   The initially reviewed S/D runtime raised a normal RuntimeError when CUDA
   was unavailable, but the worker classifier did not recognize its wording;
   `execution.py:324–330` would continue to consume later candidate attempts.
   Parent fixed S/D unavailability and driver initialization to PermissionError
   during review. Geometry's `diagnostics.NativeBackend:215–220` still initializes
   CUDA implicitly; CUDA-unavailable wording is classified, but a driver-init
   exception may not be. Preserve an explicit supervisor stop category too:
   `execute_matrix` currently decides whether to continue from the worker's
   `failure.json`, without inspecting a simultaneous supervisor cleanup,
   interruption, device-exclusivity or resource-limit failure recorded in the
   ledger.

## Additional concrete gaps

6. **P2 — an unreserved refusal prevents safe retry.**
   `execution.py:244–245` publishes the exclusive request file before supervisor
   initial resource admission and reservation. A disposable test injected a
   pre-reservation resource refusal; the next dispatch raised FileExistsError
   despite zero consumed attempts. Preserve the immutable request and allow
   verified reuse only when no attempt was reserved, or order admission and
   publication so an initial refusal cannot poison the slot.

7. **P2 — report omits the comparison itself.**
   `reporting.py:12` loads the aggregate but never consumes it. Its current
   output contains slot statuses and general qualifications, without selected
   S*/M*/N*, named C0–C3 compositions, measured paired differences and intervals,
   regressions, scale decisions or per-component conclusions. Plan 031:315–360
   requires these readable outcomes. Populate the report from the saved
   aggregate/finalists/metrics; preserve proxy and missing-evidence qualifications.

8. **P2 — license-gated option has no evidence admission path.**
   `runtime.py:243–248` and `execution.py:82–101` set commercial permission and
   non-AGPL status to `unverified` unconditionally. Consequently C2 is always
   blocked even if actual source, weights and dependency inventories support
   its preferences. Unknown evidence must remain unknown, but the controller
   needs a hash-bound reviewed evidence input to represent an established
   assessment. Non-snapshot weight asset entries at `runtime.py:181–185` also
   discard downloaded license/config records from the returned asset record.

9. **P2 — unsupervised qualification CPU work is charged only on success.**
   `execution.py:42–70` charges elapsed preparation time only after qualification
   succeeds. Failed inventory/asset work is uncharged; the cumulative ceiling is
   checked after work rather than enforced during it. Preserve and charge failed
   work, and admit it only within the remaining CPU preparation allowance.

10. **P2 — human import serializes the validation summary as the annotation
    bundle.** `basketball_vipe_worker.py:57–60` writes the return of
    `annotations.validate` to `annotations.json`, dropping the image/pair bundle
    expected by later admission and scoring. Save the validated input bundle and
    separate validation evidence. The authorized automated-proxy path is separate
    and is not affected by this issue.

11. **P2 — repeated M0 computation needs an explicit accounting decision.**
    `stages.py:106` computes M0 for every segmentation output and repeat before
    the scheduled M0 CPU job computes it again. The protocol allocates M0/M1/M2
    once. The native-model timing excludes this repeated work, while total GPU
    wall time includes it. Reuse the accounted M0 artifacts or defer final static
    assembly to the motion/aggregation phase, with provenance for the resulting
    masks. This does not require changing the algorithm or its thresholds.

12. **P2 — completed matrix re-entry cannot simply return the final report.**
    `execution.py:334–343` rewrites exclusive final-component/accounting files and
    redispatches report regardless of its ledger state. A resumed invocation
    after report completion fails with FileExistsError rather than returning
    verified final evidence. A consumed failed report must remain failed; a
    completed report should be returned through its saved hash, without a second
    report pass.

## Fixes observed during review

- Geometry request construction originally passed `revision` and `files` into
  `NativeBackend`, whose constructor accepts only `checkout` and `weights`.
  Parent fixed `execution.py:210–213` to separate constructor arguments from
  `roma_provenance`.
- Parent wired matched D0/D1 fit/check result records into `depth_controls` for
  the finalized aggregation API (`execution.py:285–287`).
- Parent added `require_stage_order` to the individual stage CLI, closing the
  direct stage-order bypass. The stronger checkpoint-evidence issue above
  remains distinct.
- Parent converted S/D CUDA absence and initialization errors to PermissionError
  in `stages.py:41–46`.

## Validation

- `.local/envs/stg-colmap/bin/python -m unittest discover -s tests -p 'test_vipe_benchmark_execution.py' -v`:
  **4 tests passed**, using only fake components and temporary CPU artifacts.
- Disposable CPU probes confirmed failed-ledger result admission, changed result
  rehashing, poisoned unreserved dispatch, failed/unledgered checkpoint admission,
  combined transfer overshoot, and omitted managed-Python/active transfer bytes.
- The finalized geometry/scoring implementation previously passed 52 relevant
  CPU checks, recorded separately in `geometry-scoring-implementation.md`.
- No claim of model compatibility, GPU execution, complete runtime qualification
  or benchmark outcome follows from these tests.

## Assigned follow-up status

After this review, the parent authorized source edits to diagnostics and
aggregation only. Geometry now explicitly initializes CUDA and raises
`PermissionError` before model loading on absent device access or driver/init
failure. Final static assembly moved into the masks aggregation stage, consuming
saved S/M outputs for all 9,450 planned method/identity outputs with exact parent
hashes and an S0/M0 alias. The parent owns removal of M0 recomputation from the
segmentation worker. These changes passed 25 owned CPU tests and are documented
in `geometry-scoring-implementation.md`. Remaining review findings belong to the
parent's concurrently integrated controller/runtime/report fixes; this note does
not claim they have all received a post-fix audit.
