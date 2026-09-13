# SAM3 memory diagnostic passed; conditional reconstruction admitted

The [approved diagnostic](sam3-memory-diagnostic-plan-001.md) completed all **48 pairs / 96 outputs** in **163.136 seconds**, including supervisor cleanup. All **82 overlapping instance arrays and masks are pixel-identical** to recovery002's preserved outputs. No model settings or native algorithms changed. [Review and validation gate](sam3-memory-diagnostic-review-001.json) verifies source hashes, output hashes, every snapshot, the prior ledger prefix and clean host/GPU shutdown.

## Measured behavior

Post-pair cleanup memory was identical across all 48 pairs: **4.716722 GiB live tensors**, **4.851562 GiB allocator-reserved memory**. The final seven pairs remained within the bounds of the first 41, covering the prior stopping point.

| Cleanup step | Measured memory reduction |
| --- | --- |
| Release semantic state and native output references | 0.0114–0.0117 GiB live tensor storage per semantic boundary |
| Garbage collection after reference release | 0 live tensor bytes in these observations |
| Release unused allocator blocks | Up to 6.5098 GiB per boundary; median 1.0781 GiB across semantic and pair cleanup calls |

The supervisor's sampled device peak was **9.635742 GiB**. More frequent in-worker CUDA total-minus-free observations peaked at **12.467529 GiB**. These measurements use different APIs/cadences and both stayed below 22 GiB; the supervisor sample is not an exact instantaneous hardware peak.

Unused allocator blocks are the dominant measured memory reduction. The successful cleanup sequence releases references, collects garbage and releases unused allocator blocks after each semantic prompt and pair. The full run retains that exact validated sequence rather than dropping steps without validation. Model weights and native kernel caches remain resident. The original failed run lacks per-phase allocator history, so its sole root cause cannot be proven from a counterfactual trace. This result demonstrates a bounded-memory repair for the diagnostic sequence, not a guarantee for all later pairs.

## Authorized continuation

The one 600-second diagnostic allocation is consumed at its actual elapsed time. Its unused time is not transferred. [Recovery003 authorization](s3-reconstruction-recovery-authorization-003.json) binds the passed diagnostic gate, original/recovery002 failures and validation011. It permits one full 840-output reconstruction of at most **5,400 seconds including cleanup**, as already approved by the user, within the unchanged 22-GiB and cumulative resource ceilings.

Diagnostic timing is excluded from benchmark timing. Full reconstruction includes lifecycle cleanup and lightweight memory observation in its own runtime. No model-selection scoring, new annotation truth, unrelated stage, or additional trial is introduced. The full attempt remains unstarted until this evidence checkpoint is committed, then dispatch proceeds automatically.
