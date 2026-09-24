# Plan053 correction 001 implementation

Source scope: the existing nine authorized Plan053 Python paths. This correction changed only `scripts/vipe_benchmark/s1_helper_session.py` and `tests/test_vipe_benchmark_s1_recovery.py` relative to post-edit review 001. No diagnostic or aggregate was launched; no source path, selector, deadline, assertion, cap or suite member was added or changed.

The current source now records each `WNOHANG` intent/result, accepts only `(0, 0)` as a nonterminal result, requires the terminal PID to equal the owned child, advances a unique poll sequence and forbids another poll after terminal observation. Direct descendant retirement permits the current claimed wait while other unresolved operations and open pins still block it. Cap rejection and verified rollback put a nonempty marker in the locked sidecar; readers and appenders consult it independently of the process-local flag. Signal/pidfd target and result objects use closed field/type checks; uncertain pidfd close emits `operation-uncertain`, with no success receipt. Prepared Popen/spawn/exec candidates freeze argv, effective environment and options, then rerender before OS create. The source edits in this correction tightened the poll edge cases; the other items were already in Main's initial post-review patch and gained focused coverage here.

The existing `ReceiptContractTests.test_execution_mutations` method now checks two nonblocking polls and terminal retirement through `wait_owned_pid`, wrong PID and nonzero no-result rejection, direct descendant wait replay, open-pin obstruction, cap/rollback marker refusal after resetting process-local state, exact nested schema rejection, uncertain pidfd close, and mutation of frozen `posix_spawn` argv/file actions. It creates no new test method or selected scenario. The reset test exercises the on-disk marker read path used by a fresh process, but does not itself launch a second process; a distinct source review should assess the cross-process claim.

Validation commands and results:

- `PYTHONPATH=scripts .local/plan053-correction001/bin/python -B -m unittest tests.test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_execution_mutations`: **PASS**, 1 test in 13.095 seconds after the final edit.
- `PYTHONPATH=scripts .local/plan053-correction001/bin/python -B -m unittest tests.test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_positive_complete_fixture tests.test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_accounting_mutations tests.test_vipe_benchmark_s1_recovery.ReceiptContractTests.test_execution_mutations`: **PASS**, 3 tests in 17.590 seconds before the final uncertain-close test addition. The changed method was rerun afterward as above.
- `git diff --check --` followed by the nine paths listed in the manifest below: **PASS**, empty output.
- `python3 -B -` with `ast.parse(Path(name).read_bytes(), filename=name)` for the same nine paths: **PASS**, `AST parse OK: 9 authorized Python paths`.
- `sha256sum` on the same nine paths produced the manifest below. The exact path arguments for these three checks were:

```text
docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py
scripts/vipe_benchmark/s1_helper_session.py
scripts/vipe_benchmark/s1_validation_capture.py
scripts/vipe_benchmark/s1_validation_contract.py
scripts/vipe_benchmark/supervisor.py
tests/test_vipe_benchmark_budgets.py
tests/test_vipe_benchmark_s1_helper_fixtures.py
tests/test_vipe_benchmark_s1_recovery.py
tests/test_vipe_benchmark_supervisor.py
```

The system `python3` cannot import the suite because NumPy is absent. The earlier outside-workspace interpreter probe was denied and was not repeated. `uv venv --python python3 .local/plan053-correction001` failed before creating a venv because uv's default cache attempted `/home/auss/.cache/uv/.tmpcatBwD`: `Read-only file system (os error 30)`. A subsequent user-authorized repo-local setup, `UV_CACHE_DIR=.local/uv-cache uv venv --python python3 .local/plan053-correction001`, succeeded using `/usr/bin/python3` (CPython 3.12.3). `UV_CACHE_DIR=.local/uv-cache uv pip install --python .local/plan053-correction001/bin/python numpy==2.1.3` succeeded. The ignored `.local` venv/cache was not staged. No other package was installed.

Exact nine-path post-correction SHA-256 manifest:

```text
ae8468db5e808609c152739480548520b608f2011dbd5a53d1ad0642d1d8bb94  docs/resolve-blocker/plan031-progress-20260922/launch-049-exec.py
b5a0ef11728468b085eb472e2160f5ead057560725aed7c93949b2869f824af3  scripts/vipe_benchmark/s1_helper_session.py
62359a258543731b96690d3abc7bd3ddede4809ae76ae4ec2ff83e5c4ce95fd7  scripts/vipe_benchmark/s1_validation_capture.py
07a397a90aaee7c5951f2f1e2dfb8f50251503ca93fe092d328056373cb57fea  scripts/vipe_benchmark/s1_validation_contract.py
1f8fb109c48ab121a232d3348ecaec1644b651119742c1d6339c6ce87faf2878  scripts/vipe_benchmark/supervisor.py
6bac13ad5582f4bd28a86ea5c42989d08d8932f236e3797a288807100edcefa6  tests/test_vipe_benchmark_budgets.py
faccb5561ad8373d6805b50b0326f0eff8d00e9c9d9760d5829096fca917732b  tests/test_vipe_benchmark_s1_helper_fixtures.py
3a636c657725b137cd63eee7ecf5f65a5633ebb559a57e1e9c6bf577df97e2af  tests/test_vipe_benchmark_s1_recovery.py
03e41c199a63c21cf754f0ec3f571a85f79ac417457344d83220f31399b9ce36  tests/test_vipe_benchmark_supervisor.py
```

Remaining gate: independent exact-hash source review and fresh Main preflight are required before any diagnostic. Environment-bound supervisor ownership regressions and a live cross-process marker check were not launched in this bounded correction; the corresponding source and focused synthetic paths were checked as stated above.
