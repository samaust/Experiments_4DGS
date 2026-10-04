# Native interpreter invocation correction (#34)

Base: `b96e664e` on `plan069-native-execution-fix`.

The actual dispatcher previously resolved virtual environment interpreter symlinks
before launch. This selected host Python and lost the bound environment.

The DO envelope and worker invocation now carry `interpreter_invocation`: the
literal absolute environment `bin` path. `interpreter` still binds the exact
resolved executable bytes. Admission verifies both native and matcher environment
bindings, approved command spelling and executable identity. Control helpers use
that same launch path; registered workers verify `sys.executable` before entry.
No approval, runtime, fixture or source gate is relaxed.

## Validation

Focused CPU validation: **34 tests passed in 10.013 seconds** using the explicit
`stg-colmap/bin/python` interpreter and `PYTHONPATH=scripts:tests`:

```
/home/auss/git_repos/samaust/Experiments_4DGS/.local/envs/stg-colmap/bin/python -B -m unittest test_vipe_benchmark_actual_dispatch \
  test_vipe_benchmark_final_render_admission test_final_render_actual_control \
  test_final_render_actual_supervisor test_vipe_benchmark_final_render_actual_result \
  test_vipe_benchmark_final_render_matcher
```

The new fixture creates a disposable symlinked virtual environment, executes a
harmless worker and checks its actual `sys.prefix`. It checks launch path and
registration arguments, byte identity, rejection of the resolved host invocation
for a bound environment, rejection of different executable bytes, and the control
helper command spelling. It grants no actual DO authority.

Independent Spec and Standards reviews found no actionable findings.
`git diff --check` passed.

## Integration requirements

Integrate after the incoming native-execution commits through `b96e664e`.
Regenerate inventories, qualify combined sources and review fresh authority before
actual execution. Both matcher and trainer use the singular approved interpreter:
separate existing RoMa and FreeTimeGS environments cannot jointly satisfy that
contract. Prepare and qualify one environment with both dependency sets.

Actual native qualification, D* selection, final renders and human feedback remain
unfinished. No GPU, model execution, downloads, existing runtime modification or
shared production ledger mutation occurred. Keep #3, #34 and #35 open.
