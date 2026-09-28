# S1 recovery review 019 — Codex host execution blocked before reservation

Date: 2026-09-28. Scope: Plan065 and the approved Plan064 host allocation.

## Outcome

The live GPU recovery did not start. S1-3 remains unmet. The ledger appended
exactly one admission (447, admission-040.json) and one matching registration
(448); it contains no recovery reservation, worker start, or finish event.
The 447-event prefix is byte-identical. The one allocated attempt is available.

The first controller invocation used E1 Python 3.11 and failed with
`S1 requires native joinable ownership thread`. The earlier import check and
CPU execution-mutation test did not establish this controller prerequisite.
Commit `6f65ff2` separates the existing Python 3.14 controller from the unchanged
E1 model-worker runtime and checks the native API before admission.

The corrected controller reused the existing registration and failed with
`S1 resource sample timeout`. GPU queries took 0.043710 s; the real storage
snapshot took 2.984283 s and 3.056955 s, exceeding the fixed one-second sample
deadline even without helper overhead. The gate now detects that condition
before invoking the controller. This is a runtime performance blocker, not
a Codex permission failure. Host execution was approved and launched normally.

## Evidence and preservation

- `s1-codex-host-audit-025.json`: validated ledger chain, passing registered but
  unconsumed binding, 78 unchanged source records, host resource measurement,
  no surviving helper/worker processes, and no GPU compute PIDs.
- `admission-040.json` and both `S1-pre-dispatch-block-*.json` receipts in the
  run's research directory preserve the observed lifecycle and failures.
- GPU accounting remains 30 historical attempts / 4374.044265462899 seconds /
  zero reserved seconds. No new GPU attempt, model forward, or reconstruction.
- No first-result qualification or raw model output exists for this recovery;
  the pre-dispatch failures do not satisfy the Plan064 terminal-result criterion.
- Bound Plan064, authorization, validation, baseline correction, and status
  are preserved. The current blocked state is recorded here and in Plan065.

## Next decision

Final validation: host launcher `--check` returned the expected NO-GO with a
2.923-second storage sample; all other checks passed, including binding and
GPU exclusivity. Shell/Python syntax, audit-record hashes, unchanged 449-event
ledger, and `git diff --check` passed.

Do not repeat dispatch. The next work must address the sampler's full-tree
accounting latency while preserving its guarantees, then requalify source
changes and explicitly amend the registered binding if needed. That exceeds
Plan065's unchanged-source execution scope. Do not extend the deadline, skip
accounting, delete retained evidence, or replace ledger/authorization bytes
as a shortcut.
