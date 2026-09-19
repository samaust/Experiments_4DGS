# Geometry continuation audit 001

Audited 2026-09-19 without running a model/GPU job or modifying source, tests,
the ledger, or bulky outputs. No substantive continuation defect was found.

G-S0 is correctly charged and complete in the live append-only ledger: finish
sequence 342, 85.65207107609604 GPU-job seconds, cleanup confirmed, no surviving
PIDs, no deadline overrun or stop requirement. Its 7,725,874-byte result matches
SHA-256 `1132853eca900fc0388c7078dfeb967d7b7ba0ab0a4385617d0cb1e890169ede`
and the compact G-S0.json receipt. All 64 contexts and 192 directed edges are
complete; there are no neighbor failures, no crop matches, and no cross-arm cache.
The saved configuration fixes S0/D0/M0/N0, seed 0, 5,000 samples per edge, the
historical reference scene, and the prescribed geometry gates.

The status heading and assessment-016.md still describe dispatch; accounting-011
predates this completion and contains no G-S0 entry. Preserve these historical
records and publish a new accounting/assessment checkpoint from the live ledger.
Do not re-account or relaunch G-S0. At audit time there were no active reservations;
R-G and the remaining geometry arms were unconsumed. Live consumption was:

| Resource | Attempts | Elapsed seconds |
| --- | ---: | ---: |
| GPU | 18 | 3203.3654150709044 |
| CPU preparation/scoring | 3 | 13715.769324336045 |
| Setup | 9 | 4845.623517405824 |
| Motion | 3 | 254.51461822795682 |
| Neighbor | 3 | 36.09751573391259 |

Next command, from the repository root, through the usual host approval path:

```bash
.local/envs/stg-colmap/bin/python scripts/basketball_vipe_benchmark.py --run-id plan031-20260913T032700Z stage --job R-G --validation docs/research/vipe-alternatives/plan031-20260913T032700Z/implementation-validation-014.json
```

This reserves the original 600-second repeat allocation and dispatches a fresh
geometry worker. R-G is fixed to reference camera 1, pair 20/21, and its three
N0 neighbors. The runner verifies primary parent records and restores the saved
primary context RNG state before comparing acceptance and coordinates.

After R-G is terminal with cleanup confirmed, use the same exact command with
`--job` replaced, one invocation at a time, in this order:
`G-S1`, `G-S2`, `G-S3`, `G-S4`, `G-M1`, `G-M2`, `G-N1`, `G-N2`.
G-S1 should be accounted blocked by the existing stage API because S1
reconstruction failed; it must not consume a GPU attempt or substitute masks.
The other coarse arms retain their original 1,800-second allocations. Recheck
current ledger state before dispatch, and stop on any supervision/access stop.
Use `execution.make_request`, `require_stage_order`, and `dispatch` through this
CLI rather than calling the worker directly. Combined arms require the existing
finalists aggregation checkpoint and their own scale eligibility afterward.

Review confirmed full `(branch,camera,pair_start,frame)` lookup, training-camera
membership, RGB hashes/grid checks, pair unions, exact three-neighbor checks,
and no cached matcher results across arms. Ledger reservations hold an exclusive
file lock, reject any active job and consumed identity, and cap reservations by
both job and remaining cumulative allowance. Supervisor fixtures cover deadlines,
memory/storage ceilings, foreign GPU processes, cleanup and concurrent admission.

Validation:

```bash
.local/envs/stg-colmap/bin/python -m unittest tests.test_vipe_benchmark_diagnostics tests.test_vipe_benchmark_contracts tests.test_vipe_benchmark_budgets tests.test_vipe_benchmark_supervisor tests.test_vipe_benchmark_execution
```

Passed 79 CPU tests in 2.543 seconds. The fixture message “R-G: completed pair”
belongs to a stubbed CPU test, not a new model run. A preliminary pytest command
could not run because this environment has no pytest module; the existing
unittest suite above passed. Read-only Python checks verified the live ledger
chain/result receipt, R-G stage order, and all 69 source and 69 immutable source
records in implementation-validation-014.json.

Remaining concerns are unchanged: host GPU availability is checked at dispatch,
network setup E4/E5–E7 stays paused, missing challenger depths constrain combined
eligibility, proxy labels do not establish independent truth, and historical
budget overruns still prevent claiming overall budget integrity. This bounded
audit neither resolves those issues nor constitutes final benchmark completion.
