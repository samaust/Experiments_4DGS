# E4 cu130 migration audit — 2026-09-19

Prepared the E4-only runtime amendment without installation, network requests,
model imports/inference, staging, commits or edits to historical job evidence.

## Target and local evidence

- Python **3.11**, torch **2.13.0+cu130**, torchvision **0.28.0+cu130**,
  torchaudio **2.13.0+cu130**, NumPy **2.1.3**.
- Torch/torchvision match `environments/constraints-cu130.txt`, Plan 003 and
  the repository's E0/E8 targets. Torchaudio uses the matching Torch release
  convention also present in the prior E4 recipe (2.5.1 paired with 2.5.1).
  This is a target pin, not local proof that a Python 3.11 wheel exists.
- Pinned UniDepth source requirements at
  `.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E4-setup-recovery-002/sources/unidepth_source/requirements.txt`
  specify `torch>=2.4.0`, `torchvision>=0.19.0`, `torchaudio>=2.4.0`,
  `numpy>=2.0.0` and `xformers>=0.0.26`.
- Replace E4's old xFormers 0.0.28.post3 pin with that source floor. Resolve
  once under exact Torch constraints and freeze the resulting version and
  hashes in the existing lock pipeline. No exact cu130-compatible xFormers
  release is established by the inspected local evidence.
- Runtime setup derives the official index from Torch's suffix, so E4 now
  selects `https://download.pytorch.org/whl/cu130` automatically.

## Changed files and reference audit

- `scripts/vipe_benchmark/runtime.py`: E4 Torch/torchvision target.
- `scripts/vipe_benchmark/setup_recipes.py`: E4 torchaudio and xFormers requirements.
- `scripts/vipe_benchmark/config.py`: explicit E4-only amendment overlay after
  checking the original source hashes and deriving protocol configuration.
- `configs/vipe-alternatives/components-v1.json`: matching amended E4 description.
- `plans/plan_031.md`: dated amendment, exact targets, compatibility gates and
  preservation of allocation/recovery requirements.
- `native-runtime-recommendations.md` in this directory: current E4 index,
  dependency table and example recipe.
- This audit records the migration and its limits.

The remaining defining reference is the original E4 table row in
`docs/research/vipe-alternatives/benchmark-protocol.md`. Its bytes deliberately
remain unchanged: `config.SOURCE_HASHES`, Plan 031 and historical admission
records freeze that source. The dated Plan 031 amendment and configuration
overlay supersede only that E4 row; changing its hash would unnecessarily
invalidate original provenance. The study itself contains no cu124 E4 target.

Historical `E4-setup-failure.json`, recovery authorizations/results, matrix
accounting, report/status entries, the original source review, local job
requests/constraints/logs and ledger records retain their original contents.
Other environments' cu124 targets and toolkit references are unrelated and
remain unchanged. No previous failure is represented as a cu130 attempt.

## Validation

Passed `PYTHONDONTWRITEBYTECODE=1 python3` focused assertions covering:
`ast.parse` of runtime/setup_recipes/config, `config.load()`, exact equality of
`config.derive()[1]` and the checked components JSON, exact E4 base and audio
pins, xFormers floor, absence of cu124 in E4 requirements, and unchanged
E1/E2/E5/E7 Torch targets. `config.load()` also verifies the original study and
protocol hashes. `git diff --check` passed.

The first equivalent invocation used `python`, which is absent from PATH
(`/bin/bash: line 1: python: command not found`). Re-running with the available
`python3` succeeded; this was command availability, not a permission failure.

## Unresolved qualification

Python 3.11 wheel availability, torchaudio release availability, xFormers
resolution/native ABI compatibility, Triton compatibility and UniDepth behavior
on Torch 2.13 remain unverified. Existing exact-version constraints prevent a
resolver from satisfying xFormers by silently downgrading Torch. A successful
resolution must be hash-locked and import-qualified; CUDA execution belongs to
the allocated D1 job. Setup import success alone does not prove attention kernel
compatibility or numerical parity. No installation or extra smoke evaluation was
performed. Prior network-stop and setup-attempt accounting remain authoritative;
this amendment does not itself grant a retry or reset any allocation.
