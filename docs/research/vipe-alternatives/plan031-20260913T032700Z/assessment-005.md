# Assessment005: stopped after the authorized S3 reconstruction recovery

The isolation repair and recovery allocation are committed as `9a9d0f7`. [Validation009](implementation-validation-009.json) passes 322 CPU fixtures plus host descendant-confinement and integrated audit fixtures. The one additional real attempt failed after **17.421 seconds**, before any of the 840 rows or first-pair qualification. No native helper launched. [Stop evidence](s3-reconstruction-recovery-results-001.json) verifies cleanup, no active GPU process, unchanged historical failures and completed manifests, all current source hashes and the immutable implementation archive.

| Criterion | Status | Evidence and remaining gap |
| --- | --- | --- |
| P31-1: Reproducibility | Unverified | The exact repair, authorization, request, environment, failure and original ledger prefix are preserved. Remaining matrix provenance is absent. |
| P31-2: Engineering | Unverified | CPU confinement checks pass, but the real S3 runtime introduced `LD_LIBRARY_PATH` after initialization and failed the environment guard. Native compilation and first-pair qualification remain unverified. |
| P31-3: Independent scoring | Not met | The frozen reviewed proxy bundle is unchanged. Independent truth/missing strata remain unavailable; formal staged scoring is unstarted. |
| P31-4: Controlled experiments | Not met | [Accounting005](matrix-accounting-005.json) retains all 57 identities: {'complete': 7, 'failed': 7, 'blocked': 40, 'skipped': 3}. The failed original and additional reconstruction attempts are separate. Remaining comparisons are incomplete. |
| P31-5: Accounting and integrity | Not met | Both reconstruction charges are preserved, the 90-minute cap was respected, and cleanup is confirmed. Historical review overruns documented in assessment004 remain unchanged; a successful new accounting check does not erase them. |
| P31-6: Supported conclusions | Not met | No comparative quality, physical accuracy, or complete runtime license conclusion can be added. Formal aggregation/reporting remain unstarted. |

Consumption after conservative preparation/stop charges: GPU 664.363 seconds / 5 attempts; setup 4264.035 seconds / 7 attempts; CPU preparation 9725.919 seconds. No motion, neighbor, aggregation or report attempt was started. No scope was reopened beyond this single S3 reconstruction recovery.

## Failure and next required work

The exact controller command was:

```sh
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z reconstruction-recovery --authorization docs/research/vipe-alternatives/plan031-20260913T032700Z/s3-reconstruction-recovery-authorization-001.json
```

The worker error is `ValueError: unadmitted native helper environment override: LD_LIBRARY_PATH`; the controller reports `SupervisionFailure: RuntimeError: worker exited 1`. This is a confirmed application-policy rejection, not a Codex denial, namespace failure, or missing allow rule. The host invocation was approved. No additional Codex rule is needed to fix this policy rejection.

The pinned OpenCV bootstrap writes `LD_LIBRARY_PATH` in `cv2/__init__.py:147`, using its `config.py` binary path and inherited value. Initialization passed before the later mutation. Source inspection supports OpenCV as the cause; the failed attempt did not capture the actual value. The implementation's CPU fixtures missed this real import lifecycle.

Before another model attempt, the next repair must capture and validate the exact pinned OpenCV import-induced library path, distinguish it from external overrides, and check its library identities and namespace visibility, including the trailing empty/current-directory entry. Add a CPU fixture that exercises the actual import order and resulting helper policy. Do not delete the variable, fabricate library discovery, remove the confinement boundary or grant general library-path access as a workaround.

The additional attempt is fully consumed even though 5,382.579 seconds of its time ceiling were unused. A further reconstruction requires a new explicit attempt allocation after that targeted repair. No further model process, native compilation probe or automatic retry was started. This run is **stopped, not achieved**.
