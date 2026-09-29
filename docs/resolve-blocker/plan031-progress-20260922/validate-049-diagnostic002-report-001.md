# Plan049 diagnostic002 — independent runtime failure review

Reviewer: `/root/blocker_review`, independent reviewer assigned by Main. Initial findings were delivered in conversation on 2026-09-23 and are preserved here at Main's request. Review inspected saved artifacts/logs only, using standard-library structured JSON and traceback parsing. No project test, probe, source edit, session contact, launch, production/ledger access or git mutation was performed. This report is the only new artifact written by this review assignment before the separate correction010 plan assessment.

**Diagnostic002 completed as a failed test run, not an admission or timeout failure. Launch readiness for another invocation is false pending source/fixture corrections, permission-mode preparation and independent source recheck.** The report does not accept B1–B4 or recommend an unchanged speculative rerun.

## Outcome and count reconciliation

[execution.json](diagnostic-049-002/execution.json) records `execution_mode=no-timeout`, `timeout_seconds=null`, `returncode=1`, `timed_out=false`, `wait_completed=true` and **22.85966287899646 wall seconds**. Main reports the actual outer exit1 for session64795, retained in [Main outcome](main-diagnostic-outcome-049-diagnostic-002.json). The capture child PID3/start_ticks7596675 has matching wait return1 and `absent_after=true`. The recorded before/retired capture-root census is B1/H0/charge2; after creation it is B2/H0/charge3. These are narrow capture-edge observations, not proof of every scenario's descendant retirement. Execution source records before/after agree. Wall time is not whole-tree CPU usage.

[receipt.json](diagnostic-049-002/receipt.json) and [process-stderr.log](diagnostic-049-002/process-stderr.log) use different granularities:

| Unit | Total | Passed | Failed | Error | Skipped |
| --- | ---: | ---: | ---: | ---: | ---: |
| Method statuses | 73 | 43 | 11 | 19 | 0 |
| Logical callbacks | 334 | 87 | 11 | 236 | 0 |
| Unittest failure/error occurrences | 265 | — | 20 | 245 | 0 reported |

The 20 failure occurrences comprise 11 failed callbacks plus 9 direct method failures; the 245 error occurrences comprise 236 errored callbacks plus 9 direct method errors. A parent method containing failed/errored callbacks contributes one method status, not one status per callback. Thus the receipt's11/19 and unittest's20/245 reconcile; they are not evidence of a corrupted receipt. Discovery errors are0, `expected_exit_code=1`, `passed=false`. Expected failure exit means correct reporting, not acceptance. This is the focused HelperSessionTests collection, not the complete249-method/1028-callback aggregate.

## Exact failure groups

Locations below are the paths/line numbers captured in diagnostic002 tracebacks; they are not a claim about any subsequently edited source.

| Group | Occurrences | Observed cause and disposition |
| --- | ---: | --- |
| AF_UNIX datagram creation | **240 errors** | Every traceback terminates at `/usr/lib/python3.14/socket.py:236`, reached from `scripts/vipe_benchmark/s1_progress.py:611`, `mailbox`, at `socket.socket(socket.AF_UNIX,socket.SOCK_DGRAM)`, raising **`PermissionError: [Errno 1] Operation not permitted`**. An environment/access blocker, not240 distinct source defects. Preserve repository safe escalated-retry/stop rules; do not substitute transport or weaken guards. |
| P02–P05 | **4 failures** | Their assertion payloads explicitly contain EPERM, failed reconciliation, unavailable terminal publication and null verified-progress reference. Their intended interruption/death/final-sample/publisher boundaries are not established by this run. |
| P01/P06 classification | **2 failures** | `tests/test_vipe_benchmark_supervisor.py:1776` observes kind `supervisor` versus expected `job_deadline`; line1777 observes primary phase `supervisor` versus expected `acceptance`. A common EPERM cause is plausible, **not established**: these assertions interrupt the path before the complete outcome is recorded. |
| Ownership mutation masking | **8 failures** | At supervisor test line2803, `paired_env_foreign_output`, `stale_dispatch016`, `forged_dispatch_env`, `ancestor_empty`, `ancestor_truncated`, `ancestor_cycle`, `ancestor_terminal_changed`, `wrapper_unproven` all receive **`stale file record bytes or hash`** instead of their named rejection. This is fixture hash/binding/reachability failure. Rehash the full affected graph and preserve target-specific assertions; an unrelated rejection cannot satisfy these cases. |
| Scenario secondary-failure control | **1 failure** | `registry_worker_dispatch` calls `scenario_secondary_controls`, failing at `tests/test_vipe_benchmark_s1_helper_fixtures.py:959`: two `open` observations versus expected one. Evidence proves the mismatch; it does not distinguish redundant production acquisition from instrumentation observing an additional seam. Inspect/fix that distinction while preserving the original predicate. |
| Admission/launch deadline messages | **4 failures** | L25/L26 fail at supervisor test line1459: expected `setup admission deadline`, actual `S1 phase deadline reached`. Plan046 `equal`/`after` launch callbacks fail at line2126: expected `immediately before worker launch`, actual `TimeoutError: S1 original work deadline after progress installation; evidence publication failed: ValueError: S1 charged terminal publisher required`. Repair source/fixture boundary attribution, preserving original cutoffs, equality-is-late, injected values and assertions. Do not assume all are harmless wording changes. |
| L08 retained late owner | **1 failure** | At supervisor test line1314, `session.close(session.cleanup_deadline)` returns true where false is expected. [L08](diagnostic-049-002/scenario-L08.json) records startup `TimeoutError: progress original work deadline`; close returns true. The required retained-late-owner state was not established. Whether behavior or fixture construction requires correction remains for source diagnosis. |
| L24 summary reference | **1 error** | `tests/test_vipe_benchmark_supervisor.py:1429 → work → monitored_call → s1_helper_session.tick:1108` receives `RuntimeError: helper operation failed: {'error_class': 'ValueError', 'message': 'captured reserve event required'}`. Reservation-authority prerequisite is missing/inconsistent; restore the real fixture/production seam rather than manufacturing an event. |
| L35 child bootstrap | **1 error** | Child stderr before the unittest error sections shows `ModuleNotFoundError: No module named 'test_vipe_benchmark_s1_helper_fixtures'` at `<string>:3`. Parent line1625 subsequently reads the missing `/tmp/tmp_3ioyvnr/ready`, raising FileNotFoundError. The missing marker is a consequence of failed child import. A secondary assertion records **2.0016216569929384 > 2 seconds**. Preserve that timing failure; fixing import alone does not prove compliance. |
| L36 primary replaced during finalization | **1 error** | Initial `assertTrue(acquired)` at supervisor test line1653 fails with `[] is not true`. Handling then raises `UnboundLocalError: cannot access local variable 'production' where it is not associated with a value` at line1667. Definite primary-preservation/source defect. The original missing acquisition's cause remains unresolved. `scenario-L36.json` is absent. |
| Closed-inventory deadline case | **1 error** | Test line2012 calls `e.reconcile_rows(..., deadline=0)`; `s1_evidence.py:407 → operation → before:296` raises `TimeoutError: progress original work deadline` at entry before the expected result handling. Source/fixture contract mismatch requiring inspection; do not remove the entry deadline guard merely to obtain a result. |
| Full completion/final-sample fixture | **1 error** | Fixture line467 calls `first_record → verify_first → qualify_runtime:784 → checked_file_record:227 → read_bytes:175`. Opening the request interpreter leaf **`python`** with `O_NOFOLLOW` raises **`OSError: [Errno 40] Too many levels of symbolic links: 'python'`**. Interpreter-reference/symlink-policy integration defect. Preserve candidate/evidence no-follow and authority checks; establish legitimate interpreter provenance instead of globally following symlinks. |

These rows account for all **20 FAIL and245 ERROR sections**. They distinguish observed causes from hypotheses; they do not claim source inspection or repaired behavior.

## Socket-error distribution and masked coverage

| Method suffix | EPERM error occurrences |
| --- | ---: |
| `test_progress_metadata_mutations` | 1 |
| `test_progress_plan046_protocol` | 1 |
| `test_progress_plan046_publication_faults` | 20 |
| `test_progress_plan046_worker_authority` | 5 |
| `test_progress_plan047_alias_inventory` | 5 |
| `test_progress_plan047_cancellation` | 20 |
| `test_progress_plan047_deadline_steps` | 114 |
| `test_progress_plan047_limits` | 1 |
| `test_progress_plan047_nested` | 1 |
| `test_progress_plan047_publication_faults` | 22 |
| `test_progress_plan047_recovery` | 17 |
| `test_progress_plan047_result_summary` | 1 |
| `test_progress_plan047_state_authority` | 30 |
| `test_progress_plan048_pure_memo` | 2 |
| **Total /14 methods** | **240** |

All114 deadline callbacks fail during socket setup, so this invocation does not validate their named internal operations. Memo callbacks `context_changed` and `source_changed` fail at that prerequisite; its other14 callbacks pass narrowly. Whole-method prerequisite errors in limits/nested/result-summary cannot be counted as executions of their entire declared tables.

All six [P scenario files](diagnostic-049-002/scenario-P01.json) retain `plan047_production_cutoff` with null reference and `plan047_safety_retirement`, but lack the complete final progress outcome record. The P02–P05 EPERM detail survives in assertion payloads in stderr; P01/P06 fail earlier classification assertions without that detail. **Evidence ordering requires correction:** preserve genuine primary/outcome data through permitted bounded seams before an assertion can prevent its final record. Do not fabricate outcomes or do forbidden late production I/O. All six scenario wrappers record cleanup confirmed, which is narrower than proving their intended progress boundaries. L36's missing artifact further prevents full scenario/lifecycle acceptance.

## Next action and limits

Main owns the environment decision, permission handling and every subsequent launch. Restore supported socket access under repository rules without replaying successful partial writes or changing transport. Independently evidenced source/fixture problems above still require correction even if socket creation succeeds. Preserve all diagnostic002 artifacts and old failures; no result is promoted because a later run passes. Require an explicit reviewed permission-mode contract, source handoff, distinct independent source recheck and fresh admission before another collected run. No operational timeout is introduced; original W/C and scenario correctness deadlines remain binding.

After the initial independent findings, Main saved [the single permission retry](main-permission-retry-001.json): exact AF_UNIX datagram creation succeeded with `require_escalated` and closed the socket. This reviewer inspected that saved record while assessing correction010; it did not execute or independently witness the retry. The record supports a sandbox/access explanation for the observed EPERM, but proves neither bind/send/receive nor the suite. Its `.json` filename contains Markdown prose; hash actual bytes, do not reinterpret as JSON. It does not authorize further standalone probes or waive any source finding.

## Artifact bindings

All paths below resolve under `/home/auss/git_repos/samaust/Experiments_4DGS/docs/resolve-blocker/plan031-progress-20260922/`. Hashes were rechecked while saving this report. The receipt, execution and stderr hashes exactly match the initial independent conversation report.

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| [Diagnostic002 stderr](diagnostic-049-002/process-stderr.log) | 523889 | `5fc417373e37b5bbdf516f21fa72aa4bf0d86f3b3f2204208da9aa371afbd9bb` |
| [Diagnostic002 receipt](diagnostic-049-002/receipt.json) | 299791 | `037edb31baa726de6778ddd91c45204c899e99e4838dcd49ba2b64a238f7edd8` |
| [Diagnostic002 execution](diagnostic-049-002/execution.json) | 46407 | `8eb45c586dd0128ca366e93e22b6db09af54a5ee9d0d73927315349e7f0b9ca6` |
| [Main diagnostic outcome](main-diagnostic-outcome-049-diagnostic-002.json) | 7665 | `8d91ee7128c63f29fd341721d8693dbf68c507d08cc372adf97eb8193db94cf6` |
| [Main permission retry](main-permission-retry-001.json) | 1607 | `33455675c84fb4a33be28ed43f6efbbb12806f1b0e5921a0b30b154a571d059f` |

Review elapsed and whole-tree CPU time are not completely measured; no zero-consumption claim. No current source, frozen plan, prior receipt, failure artifact or execution record was modified.
