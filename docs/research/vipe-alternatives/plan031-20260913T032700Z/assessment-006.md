# Assessment006: memory stop after recovery002

The user approved one more S3 reconstruction run after the targeted OpenCV repair. Commit `2661c92` preserves that repair and [validation010](implementation-validation-010.json): 325 CPU tests plus the actual E3 Torch/torchvision -> isolation -> cv2 import lifecycle. Both previous application isolation failures were resolved in the allocated run: [first-pair qualification](s3-reconstruction-recovery-first-pair-002.json) passed and all 85 recorded native helper invocations completed successfully inside confinement.

The supervisor stopped the process group after **124.829 seconds**, at **82 of 840 outputs**, because sampled total device memory reached **23.467773 GiB**, above the unchanged **22 GiB** cap. This is a device-memory stop, not an isolation exception, Codex denial or missing allow rule. No model settings, resolution, precision, GPU/CPU placement or limits were changed to continue. The authorized attempt is consumed; unused wall time does not grant another attempt.

[Corrected stop evidence](s3-reconstruction-recovery-results-002-corrected.json) verifies 82 instance arrays and 82 masks, first-pair qualification, helper receipts, all implementation source hashes, unchanged original/recovery001 failures and prior completed manifests, and confirmed host/GPU cleanup. The initial stop-verification inventory counted only job-root files; its zero-output count is explicitly superseded by the recursive corrected inventory. Both records are preserved. There is no complete result manifest, so partial files are not eligible downstream benchmark results.

| Criterion | Status | Evidence and remaining gap |
| --- | --- | --- |
| P31-1: Reproducibility | Unverified | Validation010, immutable source snapshot, exact request, original ledger prefix and partial-output hashes are preserved. Remaining matrix provenance is unavailable. |
| P31-2: Engineering | Unverified | Native-helper confinement and first-pair contracts passed in the actual allocated runtime; S3 full reconstruction stopped on memory use before completion. |
| P31-3: Independent scoring | Not met | Frozen reviewed proxy annotations remain unchanged. Independent truth/missing strata and staged scoring remain unavailable. |
| P31-4: Controlled experiments | Not met | Accounting006 covers 58 identities: 7 complete, 8 failed, 40 blocked and 3 skipped. Partial reconstruction does not complete the S3 arm. |
| P31-5: Accounting and integrity | Not met | All failed attempts and actual elapsed charges remain. Shutdown/cleanup occurred at the observed memory violation; the sampled peak exceeded 22 GiB. Historical review overruns also remain. |
| P31-6: Supported conclusions | Not met | No full reconstruction or comparative quality/physical-accuracy conclusion is established. Formal aggregation/reporting remain unstarted. |

[Accounting006](matrix-accounting-006.json) records GPU 789.192 seconds / 6 attempts, setup 4264.035 seconds / 7 attempts, and CPU preparation 10307.919 seconds. No motion, neighbor, aggregation or report attempt was started by this request. No process remains active.

The exact failed controller command was:

```sh
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z reconstruction-recovery --authorization docs/research/vipe-alternatives/plan031-20260913T032700Z/s3-reconstruction-recovery-authorization-002.json
```

It returned `SupervisionFailure: RuntimeError: total device memory ceiling exceeded`. The supervisor recorded `failure_kind=device_memory`, `stop_required=true`, `cleanup_confirmed=true` and no surviving PIDs. This host command was approved; no additional Codex allow rule is needed for this application resource stop.

Next required work is a bounded memory diagnosis of the pinned SAM3 pair lifecycle and native allocations, using these partial outputs and source evidence before proposing another model run. The adapter already calls `reset_state` in a `finally` block for each semantic state; that alone does not establish where the device memory went. No leak, allocator-cache cause or configuration remedy is asserted from the available peak-only evidence. Further model execution requires a new explicit attempt allocation; increasing the memory ceiling is not assumed. The benchmark remains **stopped and incomplete**.
