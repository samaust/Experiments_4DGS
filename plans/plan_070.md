# Plan 070 — Recover D8 setup and finish the D8 depth slot

## Authority and objective

Plan 069 / [#44](https://github.com/samaust/Experiments_4DGS/issues/44) child
[#56](https://github.com/samaust/Experiments_4DGS/issues/56) still needs D8
(MetricAnything Student PointMap). Its single approved setup under DO002
(`depth-approval-002.json`) failed at the strict dependency check: pinned
`utils3d` declares `moderngl`, which the approved lock omits
([outcome](../docs/research/vipe-alternatives/plan031-execution/depth-D8-setup-failure-001.json),
ledger 897). The attempt is consumed; 3.4 GB of acquired assets and the runtime
are preserved. On 2026-10-04 the user chose **add `moderngl` to the lock** over
an exception, and asked for this plan before implementation.

Objective: one reviewed D8 setup recovery that reuses preserved assets, then the
existing D8 qualification chain and its single approved maps attempt, producing
60 anchors, frozen frame-100 fit / frame-175 check and four matched clips.

## Decisions requiring user approval (this plan)

1. **Recipe amendment:** add `moderngl==<exact version>` to `D8_REQUIREMENTS`
   (and constraints). The exact version and wheel hashes are resolved and bound
   during preparation; license (expected MIT) is confirmed from wheel metadata
   and recorded in the commercial findings.
2. **One D8 setup recovery attempt:** job `plan069-D8-setup-recovery-001`,
   offline reuse of the preserved source/utils3d archives and checkpoint; the only
   new transfer is the `moderngl` wheel (bounded by the remaining DO002 download
   allowance). Proposed bound: 1,200 setup-seconds including cleanup (D9's
   recovery precedent), one attempt, no automatic retry.
3. **D8 CPU allowance:** unchanged 1,800 s (7.6 s used). If the qualification
   chain approaches it, stop and ask, as with D9.

Unchanged: DO002 maps attempt (3,600 GPU-s, 22 GiB device ceiling), global caps,
scientific settings, supplied-FoV mode, D8 cu130 profile.

## Implementation milestones (test-first at existing seams)

1. **Generalize setup-recovery lineage to D8.** Parameterize the D9-only
   constants in `depth_setup_recovery.py` and `depth_recovery_lineage.py`
   (`CANDIDATE`, original/recovery job IDs, result schemas) behind a per-candidate
   table; D9 behaviour and its committed fixtures must stay byte-for-byte
   equivalent. RED/GREEN fixtures: D8 recovery accepted only with the exact
   failed `plan069-D8-setup-001` ancestry, rejected without explicit recovery DO,
   rejected on reuse of a consumed job.
2. **Recovery-aware D8 consumers.** Replace hard-coded
   `plan069-{candidate}-setup-001` in `basketball_vipe_depth_single_dispatch.py`,
   `depth_single_run.py`, `depth_map_allowance.py`,
   `depth_budget_reconciliation.py` and `depth_environment.py` with the accepted
   lineage selector already used for D9 (`accepted_setup_lineage`). Fixtures:
   maps admission accepts the recovered setup and still rejects the failed one.
3. **Offline recovery runner for native D8.** Extend `depth_setup_other.py` /
   its dispatcher with a recovery mode that verifies and reuses preserved
   archives and checkpoint by hash, installs the amended lock, runs strict
   `uv pip check`, and refuses any non-allowlisted network acquisition.
4. **Recipe amendment + review records.** Amended `D8_REQUIREMENTS`, recovery
   REVIEW proposal (job, bounds, failed ancestry, map-proposal hash) and a DO
   record citing the user's approval; fresh D8 source review.
5. **Review-feedback cleanup from the Plan 069 session review** (same modules):
   extract one `_live_events()` used by `protected_successor` and
   `validate_recovery_qualification_lineage` (keeps the disk-consistency check),
   tidy `protected_successor` naming, fix the module docstring; and add an
   **outcome addendum** for D9/D10 binding the D10 camera-z convention evidence,
   per-sequence reset/window records and the frame-175 vs frame-100 scale shift.

Each milestone: focused unittest + scoped mypy, independent Standards and Spec
review, commit. Stop and report on any confirmed blocker.

## Execution (after code milestones)

1. Combined CPU qualification (delta capture with mypy), D8 source review.
2. Recovery setup (approved single attempt) → preserve outcome either way.
3. Native D8 CPU capture, commercial assessment (incl. `moderngl`), finalize.
4. D8 maps dispatch under DO002 (single attempt, VRAM headroom checked first).
5. Clip publication, outcome record, #56 update.

## Out of scope

- D6 qualification004 (needs its own explicit DO; tracked separately).
- #59 aggregate package and #45 human review (after D6/D8 dispositions).
- Any change to D9/D10 results, historical receipts or approved budgets.

## Validation and completion

Full CPU suite once at the end of the code milestones; `/code-review` over the
plan's commits. Completion = D8 recovered setup + maps outcome (accepted or
preserved terminal failure) recorded and #56 updated; D6 and #59 remain open
unless separately completed.
