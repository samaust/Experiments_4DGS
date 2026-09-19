# E4 fresh retry audit

Audited 2026-09-19 without setup, model execution, ledger mutation, or commits.
The requested `docs/continuous-improvement/plan031-20260913T032700Z/status.md`
does not exist at audit time. The authoritative existing status is
`docs/research/vipe-alternatives/plan031-20260913T032700Z/status.md`.
Its lines 1–17 record completed isolated geometry, C0, aggregate, and report;
lines 63–65 retain the E4 outside-sandbox network stop.

## Fresh authorization and identity

Use **E4-setup-recovery-002**, with a fresh compact artifact named
`docs/research/vipe-alternatives/plan031-20260913T032700Z/e4-recovery-authorization-003.json`.
Existing authorization files 001 and 002 both target recovery-001; file 002 only
superseded the earlier unregistered validation binding. Recovery-001 is consumed
and failed after 46.91368926002178 seconds with confirmed cleanup. Its command
failed fetching the PyTorch cu124 index with `client error (Connect): operation
timed out`; see `e4-recovery-results-001.json` in the research run directory.
The new explicit user request to retry E4 supplies the next single-attempt
authorization. Network restoration remains unverified until this bounded retry.

The controller accepts the following exact required fields. Additional narrative
fields are optional; neither `asset_preparation` nor a runtime change is required.
The authorization text below records the task as supplied to this auditor;
the orchestrator should preserve the exact original user wording if different.

```json
{
  "schema": "vipe-benchmark-setup-recovery/v1",
  "environment": "E4",
  "job_id": "E4-setup-recovery-002",
  "original_job_id": "E4-setup",
  "recovery_attempts_limit": 1,
  "setup_wall_seconds_limit": 57600,
  "reset_previous_consumption": false,
  "changes_to_prescribed_runtime": false,
  "unrelated_attempts_reopened": false,
  "authorization": "use gpt-5-6-luna-orchestrator to implement plan plans/plan_031.md, retry installation of environment E4, and continue",
  "original_failure_event_sha256": "ded1df4be1cf7d8513bdc880dcca02f79e2c05a28524f2663fd09be2a7bc2eea",
  "previous_recovery_failure_event_sha256": "a9a928256ea7c1954963c3db3ec6959a390b2897241fd46ddfbb4b51863c4f1f",
  "repair_validation": {
    "path": "/home/auss/git_repos/samaust/Experiments_4DGS/docs/research/vipe-alternatives/plan031-20260913T032700Z/implementation-validation-014.json",
    "sha256": "031fec5cf54713fc82b159ac6f3d7f0ee7f427e1d1396e6a06c5e994241a5e3f",
    "bytes": 30823
  }
}
```

All source records in validation014 verified against current bytes during this
audit. No implementation repair is needed merely to register the next retry.
If source changes before dispatch, bind fresh passing validation instead.
Evidence: `scripts/vipe_benchmark/ledger.py:349–362,398–439` enforces schema,
fixed scope, sequential identity, both cleaned-up failures, matching validation
sources, absence of active attempts, and remaining setup time.
`scripts/vipe_benchmark/setup_recipes.py:100–114` makes the fresh fixed-runtime
request. `scripts/basketball_vipe_benchmark.py:151–161` registers and dispatches it.

After saving the artifact, dispatch exactly once from the repository root with
host access (`sandbox_permissions: require_escalated`, scoped approval prefix
for this Python/controller invocation):

```bash
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z setup-recovery --authorization docs/research/vipe-alternatives/plan031-20260913T032700Z/e4-recovery-authorization-003.json
```

Do not redispatch an already reserved/failed recovery, overwrite old jobs, or
interpret command exit text alone as success: inspect ledger finish, result,
imports, hashes, and cleanup. A new outside-sandbox network/permission failure
stops affected work under `AGENTS.md:40–86`; it grants no automatic third retry.

## Preserved accounting and ceilings

Read-only ledger validation through `Ledger.events()/totals()/states()` found
405 records (last sequence 404), no active reservations, and:

| Scope | Consumed attempts | Elapsed seconds | Remaining cumulative seconds |
| --- | ---: | ---: | ---: |
| Setup | 9 | 4845.623517405824 | 52754.376482594176 |
| GPU | 27 | 4315.406234818902 | 89284.5937651811 |
| CPU preparation/scoring/report | 4 | 13753.206793547044 | 43846.793206452956 |
| Motion | 3 | 254.51461822795682 | All three attempts consumed |
| Neighbors | 3 | 36.09751573391259 | All three attempts consumed |

The new E4 attempt is one explicit amendment, not a reset of the original seven
environment builds. Its inherited job ceiling is 57600 seconds, narrowed by
the remaining cumulative setup allowance to **52754.376482594176 seconds** at
this checkpoint (`config.py:117–119`, `ledger.py:113–140`). This is a finite
maximum, not an additional per-job allowance; unused time does not buy retries.
E5/E6/E7 have unconsumed original setup identities. D1–D4 fit/check (eight), R-D,
and C1/C2/C3 (three) have unconsumed original GPU identities, but dependencies
still apply. R-S and G-S1 also remain unconsumed yet blocked by consumed failed
S1 sources; they cannot become runnable from E4 success. Aggregate/report are
consumed, despite remaining CPU seconds.

The last recorded resource sample is ledger line 405: 20,704,732,181 downloaded
bytes and 56,727,359,488 artifact bytes, versus 60 GiB and 150 GiB caps. These
are historical observations, not a new disk inventory. Dispatch must keep live
monitoring. GPU still requires one exclusive process group and at most 22 GiB.
Preserve every prior event and failed output. Plan evidence: `plans/plan_031.md:391–410`;
accounting implementation: `ledger.py:93–111,216–226`.

## Safe continuation after E4 success

Do **not** use `execute` to resume: `execution.py:521–526` returns the already
completed historical report before processing reopened jobs. Do not reopen
aggregate/report: they are consumed, and `ledger.py:216–225` explicitly refuses
that. The frozen finalists still mark C1/C2/C3 ineligible; `execution.py:366–377`
uses that immutable decision. A later passing D1 alone cannot promote C1/C3.

After verified E4 completion, retain the user resume wording and reopen only
the original unconsumed depth slots needed next. For example:

```bash
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z resume --authorization 'use gpt-5-6-luna-orchestrator to implement plan plans/plan_031.md, retry installation of environment E4, and continue' --jobs D1-fit R-D D1-check
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z stage --job D1-fit --validation docs/research/vipe-alternatives/plan031-20260913T032700Z/implementation-validation-014.json
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z stage --job R-D --validation docs/research/vipe-alternatives/plan031-20260913T032700Z/implementation-validation-014.json
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z stage --job D1-check --validation docs/research/vipe-alternatives/plan031-20260913T032700Z/implementation-validation-014.json
```

Run these individually, inspect each result, and stop affected work on applicable
failures. R-D follows a completed D1-fit source immediately; D1-check needs a
passing scale fit. The stage controller accounts missing prerequisites as
blocked/skipped (`basketball_vipe_benchmark.py:197–209`, `execution.py:333–347`).
Each depth job is capped at 900 seconds, R-D at 600, within cumulative limits.
Recovery-aware qualification is resolved by `execution.py:221,245`.

The broad instruction to continue can separately reopen E5/E6/E7 original
setup slots after the shared network stop is resolved by E4 success:

```bash
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z resume --authorization 'use gpt-5-6-luna-orchestrator to implement plan plans/plan_031.md, retry installation of environment E4, and continue' --jobs E5-setup E6-setup E7-setup
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z setup --environment E5
```

Proceed serially with E6 then E7 only while no stop applies and all caps permit.
For each successfully qualified environment, reopen its original D2, D3, or D4
fit/check slots and use the same explicit `stage` commands in ascending depth
order. Keep fit/check failures and blocked dependencies accounted. Setup runs
zero model forwards; first-result qualification belongs to the original model
job. Do not change runtime versions, precision, masks, calibration, or thresholds.

Keep new result evidence and status as an append-only continuation supplement;
preserve the historical completed report and finalists. Finishing the remaining
depth jobs is possible without rerunning aggregate/report. Reassessing frozen
combined eligibility, rescoring, or producing a replacement final report would
require an explicit bounded amendment to the consumed aggregation/report scope,
plus controller support and validation. Do not spend remaining CPU time as if
it grants another pass. No such amendment or implementation is performed by
this audit.
