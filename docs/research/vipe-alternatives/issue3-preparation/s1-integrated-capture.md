# Integrated-source S1 CPU capture

The earlier requalification-070 remains historical evidence. Its source list is stale against the issue #3 integrated source in `backends.py`, `test_vipe_benchmark_backends.py`, `test_vipe_benchmark_execution.py`, and `test_vipe_benchmark_scale_motion.py`. Recovery 004 directly binds its `repair_validation`; the existing recovery-001-only source-requalification path cannot rebind 004.

After integration and the collected-test declaration correction, the S1 validation contract collected 276 tests. A bounded CPU capture used this command, without a benchmark admission, model job, setup, download, or GPU access:

```text
flock -x /tmp/issue3-cpu-test.lock env PYTHONPATH=scripts .local/envs/stg-colmap/bin/python -B -m vipe_benchmark.s1_validation_capture /tmp/issue3-s1-capture-002 --timeout 240
```

The first in-sandbox capture, in `/tmp/issue3-s1-capture-001`, exited after a Unix socket call received `PermissionError: [Errno 1] Operation not permitted`. It wrote no run-ledger event. The outside-sandbox retry used a fresh directory to avoid replacing partial capture evidence. Its child was waited, exited 1 after 213.054 seconds, and did not time out. The receipt reports 276 tests, 1,030 subtests, zero assertion failures, three errors, `passed=false`, and `contract_error="passing method required"`. The three errors are `S1NextIdentityTests.test_consumed_prefix_allows_only_bound_next_identity_read_only`, `test_fourth_identity_binds_consumed_467_event_prefix`, and `test_third_identity_binds_consumed_live_prefix_without_mutation`. Each stops at `ValueError: progress regular file capacity` in `s1_recovery.py:315` while checking the frozen baseline preservation record for the changed `AGENTS.md` bytes. The remaining collected suites, including the integrated backend and execution fixtures, passed in this capture.

The local capture files are under `/tmp/issue3-s1-capture-002`; their SHA-256 values are `68fbc4e51a5b058f5c8f36d19e9aedb14b84359d0ce74dfdf4a1a47c10022aad` for `execution.json`, `b3d118ca99be294864a6f90b948823047dd632a29c01b6b82668773e236eab83` for `receipt.json`, and `2a6fd93f0f616f701aa3bd15bdd441ddae3ab67d346c73e79ea997424e2d4ac0` for `process-stderr.log`. These files are local diagnostic evidence, not a passing qualification receipt. The successful outside-sandbox execution rules out a remaining Codex socket permission block for this check; the remaining failure is the frozen preservation contract. No missing Codex allow rule is indicated.

No refreshed REVIEW proposal was issued because the integrated source did not qualify. Resolving the frozen `AGENTS.md` authority mismatch requires a separate central contract decision that preserves the previous baseline, all prior attempts, and the 467-event ledger. Any later qualification must bind its exact passing source records to a newly reviewed 004 proposal; REVIEW itself cannot authorize an attempt.
