# CPU qualification harness preparation

Issue #44 preparation at source baseline `5df88912`. This is focused test
validation, not the final full-suite gate or a native model qualification.
No GPU, model transfer, setup attempt, actual ledger mutation, or environment
installation was performed.

## Historical fixture corrections

- The v6 inherited control-mutation test first hit its expired historical
  preparation deadline. Freeze its private clock at the configured start so it
  reaches the intended changed-control assertion. Separate deadline tests still
  require `TimeoutError`; production deadline code is unchanged.
- The Plan049 no-timeout cap fixture read an immutable dispatch whose paths
  referred to the original checkout. Route a disposable dispatch copy through
  the existing private file seam, relocating only plan/status/authorization
  paths. Keep the original frozen Plan049 digest and all production authority
  checks. Additional assertions reject substituted plan paths and digests.
  No actual historical authority document is edited.

Focused selectors passed: `V6InheritedTests.test_fresh_stage_and_deadline` and
`ReceiptContractTests.test_execution_mutations`: 2 tests, 37.802 seconds. The
latter includes its existing mutation cases and the new authority assertions.
The isolated worktree used read-only references to the existing local
calibration, environment, and historical benchmark artifacts; no model or
historical runtime was executed.

## Test dependencies and collection

Roma's explicit interpreter is Python 3.14.6, with NumPy 2.5.2, SciPy 1.18.1,
Matplotlib 3.11.1, and packaging 26.3 already installed. pytest, iniconfig,
pluggy, and Pygments are absent. Cached pytest 9.1.1 metadata explicitly lists
Python 3.14 and requires Python >=3.10; its Linux/Python 3.14 dependencies are
satisfied by the proposed pinned packages and existing packaging.

`offline-dependencies.json` records the proposed minimal offline installation
command and cache source/index hashes before installation. Its bounds are
120 seconds, zero network bytes, and 64 MiB additional artifacts. Only the
Roma test environment may receive these packages. Immutable actual E5 and
D11 runtime environments must remain untouched. Root owns any installation,
command receipt, and actual CPU accounting.

Using explicit cached package paths, pytest 9.1.1 ran these four modules:

- `tests/test_basketball_dense_report.py`
- `tests/test_basketball_scene.py`
- `tests/test_sync_pivot_budget.py`
- `tests/test_sync_timing.py`

Result: **24 passed in 5.16 seconds**. The rerun used `-B`,
`PYTHONDONTWRITEBYTECODE=1`, `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1`,
`VIPE_CPU_VALIDATION=1`, `MPLBACKEND=Agg`, and `-p no:cacheprovider`.
An initial dependency-path probe used cached pytest 8.4.2 and passed the same
24 tests in 5.55 seconds before the 9.1.1 rerun; it omitted bytecode suppression.
Neither probe installed packages or modified an actual model environment.

The three pytest modules define functions and fixtures: unittest discovery
only imports them and does not execute their tests. The final gate therefore
needs both the existing unittest aggregate and an explicit pytest invocation
for these modules. Do not claim their coverage from successful unittest
imports alone. Root will run the final gate once after integration and the
actual model milestones. These focused results do not claim a passing full
suite or current-source qualification receipt.
