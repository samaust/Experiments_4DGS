# Owned-environment strict-acceptance procedure (Plan060 §2.1)

This procedure is executable as-is in a Codex environment that provides real
`exec_command`/`write_stdin` PTY tool events. It requires no re-derivation:
every value below is bound to the recorded baseline.

## 0. Prerequisites

1. A Codex session with working `exec_command`/`write_stdin` PTY tools, so the
   Plan049 owned-root driver can produce genuine session-proof tool events.
   (The harness in which iterations 18–21 ran has only `read`/`bash`/`edit`/
   `write`; it cannot execute this procedure and no session-proof evidence may
   be synthesized to simulate it.)
2. Repository branch `qwen38` at (or ahead of) the iteration-21 commit with
   source baseline `f28d86cf9550068ee95a7e96ce3ad0850aceaf5d`. Verify with the
   78-member source manifest below; any changed member aborts the run.
3. GPU/model/production work is not part of this step (S1-3 remains a later,
   separately authorized gate).

## 1. Pre-flight source check

```
cd /home/auss/git_repos/samaust/Experiments_4DGS
git rev-parse --verify f28d86cf9550068ee95a7e96ce3ad0850aceaf5d   # must exist
# regenerate the 78-member manifest (paths from
# r18-1-implementation-evidence-020/source-manifest-020.json) and require
# changed == [] against the committed baseline_sha256.
```

## 2. Official no-timeout launch under the Plan049 owned-root driver

From the repository root, through the genuine Plan049 driver (which supplies
the `S1_OWNED_ROOT_NOTE` ownership and the PTY session-proof chain):

```
PYTHONPATH=scripts ./.local/envs/stg-colmap/bin/python -B -u -m \
  vipe_benchmark.s1_validation_capture \
  docs/continuous-improvement/plan031-s1-recovery-20260919/s1-recovery-strict-001 \
  --no-timeout
```

- Fresh run directory (`s1-recovery-strict-001`, committed by convention).
- No `--timeout` and no `--diagnostic`: this is the full no-timeout
  aggregate; the full suite is **249 tests**
  (`s1_semantics` 5, `s1_recovery` 41, `backends` 35, `contracts` 15,
  `component_recovery` 3, `execution` 10, `budgets` 31, `supervisor` 101,
  `review_annotations` 8).

## 3. Expected measured result

- `execution.json`: `returncode 0`, `timed_out false`,
  `sources_before == sources_after` (78 members, unchanged).
- Test stream (stderr): `OK (249 tests)` — **249 ok, 0 errors, 0 failures**.
  The 14 `S1_OWNED_ROOT_NOTE` tests that error in this harness
  (`s1_recovery`: `test_acceptance_and_historical_authority`,
  `test_result_requires_supervised_cleanup_and_exact_membership`,
  `test_terminal_and_resolver_numerical_mutations`;
  `supervisor`: `l01`, `l18`, `l31`, `l35`, `p01`–`p06`,
  `plan046_ownership`) pass through the owned fast-fail path instead of
  erroring.
- `boot_id` recorded from `/proc/sys/kernel/random/boot_id`.

## 4. Post-run verification

1. Receipt fields: `elapsed_seconds` (record the actual value; no cap
   applies), `wait_completed true`, `receipt` non-null.
2. Regenerate the 78-member source manifest against baseline
   `f28d86c`; require zero changed.
3. Commit the run directory and receipt by convention.
4. Record the result in the iteration evidence directory and `status.md`;
   S1-2 then proceeds only under its own separately authorized gates.

## 5. Integrity

No step of this procedure may be simulated, partially executed, or recorded
with synthetic tool events. If the environment check (§0.1) fails, the
procedure stops and the blocker is recorded unchanged.
