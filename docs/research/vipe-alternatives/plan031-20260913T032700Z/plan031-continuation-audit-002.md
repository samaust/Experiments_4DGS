# Plan 031 continuation audit — 2026-09-19

Read-only audit of existing evidence; no setup, model, GPU probe, admission,
delegation or commit was performed. Only this audit was written.

## Finding

Manual E4 setup completion cannot be established. The requested directory
`.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E4-setup-recovery-004-manual`
does not exist. The latest ledger event is sequence **419**, SHA-256
`a8fafe42ccda1c3a4b11d32e0aa17bef42ec3adafe1ae4808e47c0de300184c3`:
`E4-setup-recovery-004` failed after **56.683334739 seconds**, with no result,
cleanup confirmed, and no surviving PIDs recorded. This is historical cleanup
evidence, not a fresh host process inspection.

The actual failure in
`.local/vipe-alternatives/plan031-20260913T032700Z/jobs/E4-setup-recovery-004/commands/01-base.log`
is:

```text
error: Failed to fetch: `https://download.pytorch.org/whl/cu130/torch/`
  Caused by: error sending request for url (https://download.pytorch.org/whl/cu130/torch/)
  Caused by: client error (Connect)
  Caused by: operation timed out
```

The exact failed install command is preserved in that directory's
`commands/01-base.json` and `failure.json`, and the enclosing worker traceback
in `jobs/E4-setup-recovery-004.log`. It invokes `/home/auss/.local/bin/uv pip
install` against the fresh Python 3.11 environment, PyPI and the official cu130
index, with exact torch 2.13.0+cu130, torchvision 0.28.0+cu130 and NumPy 2.1.3
constraints. Venv creation succeeded; base installation failed before import
qualification. This is a network timeout, not evidence that the target wheels
are unavailable or a confirmed Codex sandbox denial. Authorization005 explicitly
granted the outside-sandbox retry; that retry is consumed. No missing allow rule
is established, and adding a rule would not establish connectivity.

## Evidence and missing gates

- [Plan 031](../../../../plans/plan_031.md) requires the E4 cu130 lock, inventory,
  exact versions, successful UniDepthV2/xformers.ops imports and actual CUDA
  compatibility within the allocated D1 job. None of the completed E4 runtime
  evidence exists here; Python 3.11 venv creation alone is insufficient.
- [Authorization005](e4-recovery-authorization-005.json) grants exactly one
  recovery004 attempt, preserves previous charges, and does not reopen unrelated
  slots. Do not replay it or reuse its failed output directory.
- [Validation015](implementation-validation-015.json) binds current files and
  passes focused migration assertions, but uses `source_files`. The model-stage
  admission code requires nonempty `sources`, so it is not sufficient as a D1
  admission record. It also documents two historical annotation fixtures affected
  by the amended plan hash. Validate amendment-aware annotation provenance and
  preserve original evidence before claiming common admission is ready.
- Current authorization plan/configuration/protocol hashes match their files.
  This audit found no need to rewrite those records.
- `execution.setup_result_record()` accepts a completed, ledger-bound original
  or authorized recovery result, verifies inventory/imports/lock/build inputs,
  and requires zero setup forwards. A manually installed environment would not
  automatically be recognized. There is no manual-environment adoption CLI in
  `scripts/basketball_vipe_benchmark.py`.
- [Status](status.md) predates the later E4 recoveries: its leading paragraph
  records the bounded report completion. The append-only ledger is newer.
  Aggregate and report already completed at sequences 400 and 404. Their single
  allocations cannot be replayed to incorporate new depth evidence without an
  explicit reporting amendment.

## Next permitted stage and commands

**No setup/model stage is currently ready.** Stop affected network/setup work
under AGENTS.md: the explicitly authorized outside-sandbox retry timed out.
First resolve the network failure and obtain a new bounded recovery allocation
(or an explicitly authorized, validated adoption/accounting mechanism if manual
evidence is later supplied). Preserve all historical failures and charges.

The existing non-dispatch status command is:

```bash
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z status
```

After qualified E4 evidence, current source-bound implementation validation,
annotation provenance validation, and explicit reopening of unstarted slots,
the next scientific stage is **D1-fit**, then **R-D immediately after a complete
fit source**, then **D1-check only if the fit passes**. The existing CLI forms
below are conditional instructions, not commands ready to execute; replace the
authorization text and validation path with newly recorded real evidence:

```bash
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z resume --authorization '<exact explicit continuation instruction>' --jobs D1-fit R-D D1-check
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z stage --job D1-fit --validation '<current source-bound validation JSON>'
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z stage --job R-D --validation '<current source-bound validation JSON>'
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z stage --job D1-check --validation '<current source-bound validation JSON>'
```

D1-fit/check remain unconsumed but accounted blocked; R-D is accounted skipped.
The controller's `resume` only reopens unstarted accounted slots. C1 remains
dependent on D1 gates; C3 also lacks qualified S1 evidence. E5–E7 remain paused
by the unresolved network stop. Do not use broad `execute`, rerun aggregate or
report, add a model smoke test, change precision/model/versions, or infer new
attempts from unused elapsed time. Preserve the 900-second D1 stage ceilings,
600-second R-D ceiling, exclusive GPU group, 22-GiB device cap and cumulative
resource limits. Plan 031 ends after its report or a required stop; continuation
must retain explicit authorization and the already consumed report boundary.
