# Plan 060 — Disposition and stop: owned-environment strict-acceptance procedure, measured residual gap, and the exact user decision points

Iteration 21 closes the R18-1 continuation. The [iteration-20 implement milestone](docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-050-implement.json) verified that every R18-1 item (F3, F4.1–F4.5, F6.1–F6.4) was already present in the post-review source at baseline `f28d86c`, and measured the focused diagnostic and final aggregate on that unchanged source with results identical to iterations 18/19. The [iteration-21 review](docs/continuous-improvement/plan031-s1-recovery-20260919/assessment-051-review.json) (R18-2) disposes the remaining gap. Plan 060 records the stop; it performs **no test execution, no source edit, no GPU work, and no launch**.

## 1. Scope and preserved baseline

- Source baseline: `f28d86cf9550068ee95a7e96ce3ad0850aceaf5d` (78-member manifest, zero changed in all three whole aggregates).
- Full suite: 249 tests across the nine modules (`s1_semantics` 5, `s1_recovery` 41, `backends` 35, `contracts` 15, `component_recovery` 3, `execution` 10, `budgets` 31, `supervisor` 101, `review_annotations` 8).
- Preserved invariants (unchanged): the full 510/340/170 acceptance guard, the full parser acceptance case, all 114 `deadline_steps` callbacks, no suite/fixture/gate shrink, no stale mutable authority cache, no timeout/cap change.

## 2. What this plan does (documentation only)

1. **Owned-environment strict-acceptance procedure** — written into the iteration-21 evidence directory so a genuine Plan049 driver launch can be executed and verified without re-derivation:
   - Required environment: a Codex session with `exec_command`/`write_stdin` PTY tool events (this harness has only `read`/`bash`/`edit`/`write`; the Plan049 session-proof chain requires real PTY tool events and will not be synthesized).
   - Exact official invocation (from the repository root): `PYTHONPATH=scripts ./.local/envs/stg-colmap/bin/python -B -u -m vipe_benchmark.s1_validation_capture <fresh-run-directory> --no-timeout` under the owned-root driver, with the run directory committed by convention and the boot id recorded.
   - Expected measured result: 249 ok, 0 errors, 0 failures, 78/78 sources unchanged; the 14 `S1_OWNED_ROOT_NOTE` tests (`test_acceptance_and_historical_authority`, `test_result_requires_supervised_cleanup_and_exact_membership`, `test_terminal_and_resolver_numerical_mutations` in `s1_recovery`; `l01`, `l18`, `l31`, `l35`, `p01`–`p06`, `plan046_ownership` in `supervisor`) pass through the owned fast-fail path instead of erroring.
   - Verification steps: receipt `execution.json` fields (`returncode`, `timed_out=false`, `sources_before==sources_after`), stderr stream `OK (249 tests)`, and a fresh 78-member source manifest against the same baseline.
2. **Measured residual gap record** — the three whole aggregates (018-001, 019-001, 020-001) capped at 300.0 s with 199 ok, 0 FAIL, kill inside `complete_final_sample`; the residual supervisor wall time is mandated full-510 real guard work plus `deadline_steps`' 114 mandated monotone re-qualifications, environment-independent and outside R18-1 scope. This is recorded as the final measured state of the R18-1 continuation.
3. **Status and stop** — `status.md` records the loop halt at the environment/authorization gate with the exact user decision points below.

## 3. User decision points (each requires new authorization; none is taken by this plan)

- **A. Scope amendment for the timeout-mode gap** — authorize a new plan/review that reduces the mandated full-510 guard work in the four slow supervisor tests (would change the R18-1 invariant "no suite/fixture/gate shrink"). Without this, the 300 s timeout-mode cap remains the recorded measurement in every environment.
- **B. One additional no-timeout whole-suite measurement** — beyond the 2-recorded aggregate allocation, a single `--no-timeout` run in this environment to pin the exact total wall time and the complete 14-error set (owned tests erroring at their owned prerequisite). Requires an explicit allocation amendment.
- **C. Plan049 owned-environment strict acceptance** — execute the §2.1 procedure in a Codex PTY environment. Requires that environment, not new authorization text.
- **D. S1-2/S1-3 calibration recovery** — separate later GPU authorization after strict acceptance (per the objective: one calibration attempt, capped 3,600 GPU seconds; reconstruction separate).

## 4. Resource and execution limits

- Zero test executions, zero launches, zero GPU/model/production work, zero source changes.
- Documentation-only wall time within the iteration allocation; no focused or aggregate attempts are consumed.

## 5. Acceptance

- [ ] Owned-environment strict-acceptance procedure written and committed (iteration-21 IMPLEMENT).
- [ ] Residual-gap record and user decision points written into `status.md` (iteration-21 IMPLEMENT).
- [ ] Commit contains only plan/evidence/status paths; no source, no execution directories, no session-proof fabrication.
- [ ] Loop halts; no iteration 22 is started without a user decision on A/B/C/D.

## 6. Integrity and continuation

No session-proof, tool-event, or owned-root evidence is fabricated, weakened, or approximated. No owned-path assertion is altered. No prior failure, aggregate, report, or allocation is rewritten or rerun (S1-4). After the iteration-21 IMPLEMENT commit the continuous-improvement loop stops at the recorded gate; continuation requires one of the §3 decisions.
