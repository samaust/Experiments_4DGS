# Plan 026 execution state

The fixed study is in progress; the continuous-improvement loop is inactive.
Authoritative specification: [plan 026](../../../plans/plan_026.md).

Completed preflight: all six historical 5,000-update checkpoints and their
recorded input/source hashes match. The training split contains exactly 1,350
unique allowed images. See [preflight evidence](preflight-001.json).
Historical scores have not been opened or reused for recipe selection.

ViPE's pinned environment imported successfully. CUDA availability was false
in the sandbox and true on the single required host retry. These two runtime
checks took 2.658 and 2.564 seconds, respectively; retain these startup costs
separately from subsequent ledger segments. `nvidia-smi` succeeded and showed
no running compute job. These checks preceded new initialization and training.

Validation: `python3 -m unittest discover -s tests -p test_basketball_study.py -v`
passed both split/provenance tests. The preflight CLI completed successfully.

Preflight milestone committed as `8657f61`.

The coarse and person-cropped initialization pilots have completed. The dense
arm is stopped because the cropped fallback still fails the foreground-floater
gate; see [pilot review](pilot-review.md) and [evidence](pilot-evidence.json).
No dense production initialization or training has started.

Native continuation and fresh reload validation are complete; see
[implementation validation](implementation-validation.md). Restored state is
exact, while both backends exhibit native GPU training variability in repeated
and split runs. All 13 raw-float/PNG repeat probes pass for both backends.
Adapter/pilot milestone committed as `94a498f`. STG Full seed 0 reached 50,000 updates; all four new curve snapshots are retained.
Sparse FreeTimeGS seed 0 also reached 50,000 updates. The serial queue is
training STG seed 2, followed by sparse FreeTimeGS seed 2.
Sparse FreeTimeGS seed 1 has also reached 50,000 updates.
STG seed 1 has also reached 50,000 updates. Current process and
handoff state are saved in `.local/basketball-dense-temporal/run-state.json`.
Next: complete the six sparse-arm continuations and their curve evaluations,
then retain the report and visual artifacts.

The sparse-arm production storage projection fits the available space.
No unrelated files will be removed. Four of the nine planned 50,000 endpoints are complete. Two sparse endpoints,
new curve evaluations, endpoint visuals, and final interpretation remain
outstanding; three dense trajectories are blocked by the initialization gate. There is no study time/GPU-hour ceiling; concurrency is one GPU job.

Evaluation/reporting milestone committed as `f55805d`. The first completed
trajectory passes the contiguous-update, finite-loss, timing, and checkpoint
audit in [resource evidence](resources-first-endpoint/trajectories.json).

Both seed-0 continuations pass the full trajectory audit: 45,000 contiguous
updates, finite losses and point counts, monotonic timings, and all four
retained checkpoint hashes. See [seed-0 resource evidence](resources-seed0/trajectories.json).
Their measured optimizer-loop times are 1,982.016 seconds (STG) and
5,835.064 seconds (sparse FreeTimeGS), excluding historical 5,000-update
training and this continuation segment's startup. Quality evaluation is pending.

All three completed endpoints pass the [trajectory audit](resources-three-endpoints/trajectories.json).
Seed-0 endpoint evidence was committed as `2400649`.

All four completed endpoints pass the [trajectory audit](resources-four-endpoints/trajectories.json).
STG seed-1 endpoint evidence was committed as `739c134`.
