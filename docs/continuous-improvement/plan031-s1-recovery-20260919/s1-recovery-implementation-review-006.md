# Plan 038 implementation review — iteration 7

The one-line harness correction is complete. The exact fresh nine-suite aggregate passed: **148 methods, 91 callbacks, zero discovery errors, failures, errors and skips; actual exit 0**. Aggregate elapsed: 47.818170006 seconds. Overall acceptance and live admission remain incomplete.

Only `tests/test_vipe_benchmark_contracts.py` changed in the 72-record implementation set: `self.subTest(item=item)` became `self.subTest(item=item.record())`. Original eight Identity inputs, ordering, assertion and `guard(item, self.config)` are intact. Before/after SHA-256 records and exact diff are in [audit](s1-recovery-audit-007.json).

Independent static collection matched every ordered method ID. Logs, per-suite and aggregate counts, passed outcomes, process exit, launcher/Python/runpy argv, resolved interpreter, thread environment, exact stdin and unchanged runner bytes reconciled. Source membership and hashes agree before/after run and at review. All eight callbacks matched the following literal Plan 038 expectation through strict canonical JSON, preserving boolean and null types:

```json
[
  {
    "item": {
      "branch": "reconstruction",
      "camera": 0,
      "frame": 0,
      "pair_start": 0
    }
  },
  {
    "item": {
      "branch": "calibration",
      "camera": 1,
      "frame": 200,
      "pair_start": null
    }
  },
  {
    "item": {
      "branch": "depth",
      "camera": 0,
      "frame": 100,
      "pair_start": null
    }
  },
  {
    "item": {
      "branch": "depth",
      "camera": 1,
      "frame": 176,
      "pair_start": null
    }
  },
  {
    "item": {
      "branch": "reconstruction",
      "camera": 1,
      "frame": 21,
      "pair_start": null
    }
  },
  {
    "item": {
      "branch": "reconstruction",
      "camera": 1,
      "frame": 22,
      "pair_start": 20
    }
  },
  {
    "item": {
      "branch": "calibration",
      "camera": 1,
      "frame": 21,
      "pair_start": null
    }
  },
  {
    "item": {
      "branch": "calibration",
      "camera": true,
      "frame": 100,
      "pair_start": null
    }
  }
]
```

The new directory is `s1-recovery-aggregate-006-002`: iteration 7 evidence emitted by the unchanged runner's 006 label. The failed 006-001 directory and validation-006 remain unchanged. All 38 frozen records, 40 prior-loop records, six transitions, five old aggregate files, all 72 preexisting loop files, status, index and production ledger were rehashed successfully. The 447-event ledger chain and full resource totals were independently recomputed; GPU remains 30 attempts, 4374.044265462899 seconds, zero reserved. Old failure/skip event references 250/255/256 are preserved. Diff check passed.

Timing limitation: the monotonic/UTC start was captured after the initial AGENTS/Plan read, before source inspection. The full inspection-inclusive timing requirement is therefore not certified. Functional correction and aggregate requirements passed; full checkpoint compliance is false. Recorded elapsed remains within the 1800-second cap with the 180-second evidence reserve. Historical P31-5, older status-byte and timing limitations remain unresolved.

Inherited dispositions:

- **F7-1**: {"status": "closed", "finding": "Minimal label correction and exact fresh aggregate passed, including eight typed callbacks."}
- **F7-2**: {"severity": "high", "status": "open_inherited", "finding": "Only two of 18 parameterized methods have runner-loaded literal declarations; ordinary declaration equality conflates bool/int; production validation only requires nonempty callbacks, not exact typed tuples."}
- **F6-1**: Partial: exact stdin runner and guarded-file probe spawn real constants and confirm reaping; startup error and killed-child EOF typed regressions pass. Process.start and Connection.recv remain synchronously blocking; readiness/transport bounds and arbitrary direct stdin use without the runner are not closed.
- **F6-2**: Worker context and shared peak mapping passed into nested monitor. Real owned live/unreaped exited PID, foreign-only, mixed, empty-prelaunch cases pass. Disposable supervisor asserts shared mapping/context and consumed stop. Full subsequent-phase ownership matrix remains inherited work.
- **F6-3**: Partial: lifecycle retains unsettled helpers, retries false close, propagates uncertainty even with empty worker survivors, keeps primary monitor exception and secondary cleanup observations. New matrix passes. Exception labels in fake close are not real enumeration/kill/reap fault injection; real descendant test exercises worker stop_group, not spawned-helper descendants. Unknown ownership/start identity, bounded transport, complete finalization/publication failure paths remain open.
- **package_1**: Incomplete: applicable-boundary mutations, synchronized locked contenders, continuation and consumed replay matrix.
- **package_2**: Incomplete: trusted reservation clock/effective allocation, complete structured primary/secondary propagation and corruption/storage/death/CLI tables.
- **package_3**: Incomplete: exact unique produced/qualified lower bounds/category tables and incremental durable evidence surviving helper timeout.
- **package_4**: Incomplete: fixed ready helper pool, bounded readiness/transport/descendants, sample freshness, continuous cleanup/finalization monitoring, reserve subdivision, charged upper bound and durable acknowledgment.
- **package_5**: Harness serialization resolved; full declarations, strict metadata/typed tuple guards, numeric/runtime/envelope cases and real 510-row stages.segment progression remain incomplete.
- **V1**: Fresh exact aggregate passed; full CPU acceptance remains incomplete.

S1-1 retains partial semantic support; S1-2 and S1-3 remain unmet; S1-4 is preserved within this audit. No production API, GPU, authority, staging, commit, or scientific rerun occurred. See [validation](s1-recovery-validation-007.json) and [correction](s1-recovery-baseline-correction-006.json).
