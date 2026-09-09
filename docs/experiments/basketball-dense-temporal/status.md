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
no running compute job. No training or dense matching has started.

Validation: `python3 -m unittest discover -s tests -p test_basketball_study.py -v`
passed both split/provenance tests. The preflight CLI completed successfully.

Next: implement and validate the training-only segmentation/geometry pilot,
inspect the required pilot evidence, and freeze a qualifying dense recipe.
Then implement native continuation, validate resumes and fresh rendering, and
execute/evaluate the nine trajectories and produce the study report.

Production storage remains unverified until the pilot supplies a measured point
count and artifact sizes. No unrelated files will be removed. All nine 50,000
endpoints, curve evaluations, visual artifacts, and scientific conclusions remain
outstanding. There is no study time/GPU-hour ceiling; concurrency is one GPU job.
