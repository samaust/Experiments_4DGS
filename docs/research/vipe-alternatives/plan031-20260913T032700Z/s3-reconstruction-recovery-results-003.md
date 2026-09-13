# S3 reconstruction recovery completed

The approved memory repair and reconstruction recovery are complete. The full job `S3-reconstruction-recovery-003` produced all **420 pairs / 840 outputs** in **894.108 seconds (14 minutes 54 seconds)**, including supervisor cleanup, within its 5,400-second allocation. [Verified results](s3-reconstruction-recovery-results-003.json) bind the complete manifest, output hashes, memory measurements, native-helper receipts, unchanged validated sources and confirmed host/GPU cleanup.

The [48-pair diagnostic](sam3-memory-diagnostic-results-001.md) first reproduced all **82 overlapping instance arrays and masks exactly**. The repair releases semantic state/output references, collects garbage and releases unused allocator blocks at semantic and pair boundaries. The diagnostic measured cache release as the largest memory reduction; the original failed run lacks phase traces, so its sole root cause is not asserted. The full run preserved the tested cleanup sequence and native model settings.

| Full-run measurement | Result |
| --- | ---: |
| Outputs / pairs | 840 / 420 |
| Wall time including cleanup | 894.108 seconds |
| Supervisor sampled device peak | 11.782227 GiB |
| Phase-probe CUDA total-minus-free peak | 13.520935 GiB |
| Post-pair live allocations, all 420 pairs | 4.716722 GiB |
| Post-pair reserved memory, all 420 pairs | 4.851562 GiB |
| Native helper receipts verified | 139 (1 ldconfig, 1 file, 6 C compiler, 131 ptxas) |
| Surviving worker/GPU processes | 0 |

The two peak measurements use different APIs and cadences; neither is an exact instantaneous hardware peak. Both stayed below the unchanged 22-GiB cap. Post-pair live and reserved memory remained constant across the entire run. Full-run timing includes cleanup and lightweight observation. Diagnostic allocation-history snapshots were disabled for the full run, and diagnostic timing is excluded from benchmark timing.

Validation011 passed **331 CPU tests**; all **68 bound source/test files** still match their hashes, and the immutable archive was verified. Implementation is committed as `d747a16`, with the passed diagnostic evidence at `3ae5ec9`. Every native helper completed with zero exit status inside the established confinement and inherited the supervised process group. The original ledger prefix and all three prior failed reconstruction identities are preserved.

All **510 calibration outputs** remain available. Downstream reconstruction lookup now resolves the complete recovery003 manifest, and S3 is engineering-qualified. This does not establish comparative segmentation quality, geometry quality or physical accuracy. [Assessment007](assessment-007.md) records the remaining Plan 031 gaps.

The diagnostic and conditional full attempt are both consumed: **163.136 + 894.108 = 1057.243 seconds**, within their separate 600/5,400-second limits. No unused time funds another attempt. [Accounting007](matrix-accounting-007.json) retains historical failures and charges. No unrelated model, motion, neighbor, aggregation or reporting job was started. The requested recovery is complete; the broader benchmark remains incomplete.
