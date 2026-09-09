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
Next: execute the six sparse-arm continuations to 50,000 and their curve
evaluations, then retain the report and visual artifacts.

The sparse-arm production storage projection fits the available space.
No unrelated files will be removed. All nine 50,000
endpoints, curve evaluations, visual artifacts, and scientific conclusions remain
outstanding. There is no study time/GPU-hour ceiling; concurrency is one GPU job.
