# Plan 061 — Pi-launch owned mode: make the owned suite runnable when launched by pi, without the Codex session chain

## 0. Authorization

The user directed (2026-09-26, this session): *"I want to change the tests so they don't need to be launched from Codex. I want them to work when launched by pi."* Recorded verbatim with decision semantics in [`pi-launch-authorization.md`](../docs/continuous-improvement/plan031-s1-recovery-20260919/pi-launch/pi-launch-authorization.md). This is the authorized scope amendment that decision point C (Plan049 owned-environment acceptance) previously required; the Plan049 chain is preserved untouched, and a new **pi-launch** provenance class is added alongside it.

## 1. What blocks pi launch today (measured, from source)

- `owned_workload` (`s1_helper_session.py:1776`) — the function every owned test calls — re-verifies at each call: the kernel launch anchor (`_launch_anchor`), the live owned closure, thread identities, and then the **full Plan049 authority chain** (`no_timeout_launch`), which requires the dispatch file, fixed `plan_049.md` digests, the Main admission, and the `plan049-session-proof/v2` record of **verbatim Codex `exec_command`/`write_stdin` PTY tool events**. That chain is structurally impossible under pi (no PTY session tools), and synthesizing it is forbidden.
- The capture's no-timeout entry (`s1_validation_capture.py:27-53`) calls the same chain and binds `creation['authority']` to `note['admission']` (plan049-only field).
- The run layout is hard-bound to the Plan049 run directory and `-049-` naming in `_launch_anchor` and `launch_output_paths`.
- The 14 `S1_OWNED_ROOT_NOTE` tests read the environment variable directly and therefore error in any non-owned launch. They **already** support both modes; no test code change is required.

## 2. Design: additive pi-launch provenance class

**No existing guarantee is weakened.** Every check that is launch-method-independent (live census, owned closure, per-thread identities, identity stability, note digest vs kernel anchor, layout/fd identity, CPU bound, ancestry liveness) stays exactly as-is. Only the Codex-session-specific provenance (dispatch/admission/session-proof) is replaced, for the new note schema, by the pi-launch authority chain (launcher + authorization + plan records, all file-verified) plus the live ancestry walk that already binds the driver to pid 0.

### 2.1 New note schema `plan061-pi-launch/v1`
Fields: `schema`, `execution_mode='no-timeout'`, `timeout_seconds=None`, `driver` (file record of the pi driver), `authorization` (file record of `pi-launch-authorization.md`), `plan` (file record of `plans/plan_061.md`), `bindings` (those three records), `sources` (live 78-member records), `kind`, `attempt_index`, `reason`, `command` (exact capture argv), `cwd`, `run_directory`, `environment` (exact thread/validation settings, no job ledger), `unset_environment`, `stdin_identity`, `ownership_root` (full stable identity of the driver process, which execs into the capture — same pid/start_ticks as the Plan049 driver), `preexisting_ancestors` (live, to pid 0), `ancestry_terminal`, `retained_wrappers=[]`, `output_paths`, `job_ledger=None`, `observed`, `cpu_bound='B+max(1,H)≤8'`, `provenance='pi-launch'`.

### 2.2 Pi driver (new, outside the source set)
`docs/continuous-improvement/plan031-s1-recovery-20260919/pi-launch/pi_launch_driver.py` — mirrors `launch-049-exec.py` minus the session protocol: argv `kind index reason`; run directory `…/pi-launch/`, attempt directory `<kind>-061-<NNN>`; preflight (vacant paths, next high-water index, 78 source records all parse, exact command/settings/stdin from the contract AST); single-threaded identity sampling of root + ancestors; writes the note; opens driver logs, publishes exec-start (note correlation + log inodes); dup2's fds 1/2; re-verifies identity immediately pre-exec; `os.execve`s the exact capture command (`…/python -B -m vipe_benchmark.s1_validation_capture <dir> --no-timeout [--diagnostic]`), setting `S1_OWNED_ROOT_NOTE`/`S1_OWNED_ROOT_SHA256`. No job ledger, no bootstrap/ADMIT, no session proof. Kept outside `scripts/vipe_benchmark/` so the 78-member source set is unchanged.

### 2.3 Source changes (three files)
- `s1_validation_contract.py`: new `pi_launch(reference, directory, *, diagnostic)` verifying the pi chain; `no_timeout_launch` dispatches on the note schema at the top (plan049 body untouched); `validate_execution`'s v2 branch dispatches (pi: `job_ledger is None`, `runner_job is None`, no session-proof/job-ledger checks, `validate_creation` still required); `validate_creation` dispatches the `authority` field check (plan049 `admission` vs pi `authorization`); new `pi_launch_output_paths` for the pi layout.
- `s1_helper_session.py`: `_launch_anchor` accepts both layouts (plan049 run dir + `-049-`, pi run dir + `-061-`; layout selected by the live stdin directory name/parent; all other anchor checks unchanged); `owned_workload` makes the plan049 dispatch/plan/driver-path block conditional on the note schema (pi path still: root binding, environment locator, live ancestry walk, retained-wrapper rejection, `no_timeout_launch` dispatch, source membership, fresh byte re-verification of bindings+sources+driver).
- `s1_validation_capture.py`: `creation['authority']` binds `note['admission']` (plan049) or `note['authorization']` (pi); everything else in the no-timeout branch is already generic (`reserve_job_root`/`wait_job_root`/`register_owned` are no-ops without `S1_JOB_LEDGER`, which the pi mode never sets).

### 2.4 No test changes
The 14 owned tests call `owned_workload(os.environ['S1_OWNED_ROOT_NOTE'])`; with a pi note in the environment and the pi process tree live, they pass. All other suite behavior is unchanged.

## 3. Acceptance run (this harness)

From the pi bash tool: `PYTHONPATH=scripts ./.local/envs/stg-colmap/bin/python -B docs/continuous-improvement/plan031-s1-recovery-20260919/pi-launch/pi_launch_driver.py aggregate 1 "pi-launch strict acceptance (Plan061)"`.

Expected: `execution.json` with `returncode 0`, `timed_out false` (no cap — pi mode is no-timeout by construction), 78/78 sources unchanged; stderr stream `OK (249 tests)` with **0 errors** (the 14 owned tests now pass through the live owned path). Wall time measured and recorded (no 300 s cap applies; prior timeout-mode measurements estimated ~365 s). A focused 120 s diagnostic is not part of this plan; the single aggregate is the acceptance.

Failure policy: if any owned-branch defect surfaces (this is the first real end-to-end exercise of the owned machinery), fix the defect in source or test per the R18-1 invariants (no gate shrink, no assertion weakening, no synthetic evidence) and rerun under the next high-water index. Each launch consumes one attempt; budget at most 3 aggregate attempts (wall 7200 s, no timeout cap, CPU bound B+max(1,H)≤8, zero GPU/model/production work).

## 4. Documentation updates

- Supersede the owned-environment procedure doc with the pi-launch procedure (executable here); keep the Plan049 procedure text as the preserved Codex-path record.
- `status.md`: iteration-22 record with the run receipt.

## 5. Integrity

- The Plan049 chain (dispatch, admission, session proof, frozen digests) is byte-identical and remains the authority for `plan049-prospective-launch/v1` notes.
- No session-proof, tool-event, or owned-root evidence is fabricated; the pi note binds only records that exist and are live-verifiable.
- No timeout/cap, suite, fixture, or gate shrink; no owned-path assertion weakened; no prior failure/aggregate/report/allocation rewritten or rerun (S1-4).
- The user's decision is recorded verbatim; pi-launch receipts carry `provenance='pi-launch'` and are never presented as Plan049 session-bound evidence.
